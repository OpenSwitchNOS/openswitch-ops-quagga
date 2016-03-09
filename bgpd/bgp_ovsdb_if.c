/* bgp daemon ovsdb integration.
 *
 * Hewlett-Packard Company Confidential (C)
 * Copyright 2015 Hewlett-Packard Development Company, L.P.
 *
 * (c) Copyright 2015 Hewlett Packard Enterprise Development LP.
 *
 * GNU Zebra is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2, or (at your option) any
 * later version.
 *
 * GNU Zebra is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with GNU Zebra; see the file COPYING.  If not, write to the Free
 * Software Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
 * 02111-1307, USA.
 *
 * File: bgp_ovsdb_if.c
 *
 * Purpose: Main file for integrating bgpd with ovsdb and ovs poll-loop.
 */

#include <zebra.h>

#include <lib/version.h>
#include "getopt.h"
#include "command.h"
#include "thread.h"
#include "memory.h"
#include "bgpd/bgpd.h"
#include "bgpd/bgp_debug.h"

/* OVS headers */
#include "config.h"
#include "command-line.h"
#include "daemon.h"
#include "dirs.h"
#include "dummy.h"
#include "fatal-signal.h"
#include "poll-loop.h"
#include "stream.h"
#include "timeval.h"
#include "unixctl.h"
#include "openvswitch/vlog.h"
#include "vswitch-idl.h"
#include "coverage.h"
#include "openswitch-idl.h"
#include "prefix.h"

#include "bgpd/bgp_ovsdb_if.h"
#include "bgpd/bgp_table.h"
#include "bgpd/bgp_route.h"
#include "linklist.h"

/*
 * Local structure to hold the master thread
 * and counters for read/write callbacks
 */
typedef struct bgp_ovsdb_t_ {
    int enabled;
    struct thread_master *master;
    unsigned int read_cb_count;
    unsigned int write_cb_count;
} bgp_ovsdb_t;

static bgp_ovsdb_t glob_bgp_ovs;

COVERAGE_DEFINE(bgp_ovsdb_cnt);
VLOG_DEFINE_THIS_MODULE(bgp_ovsdb_if);

struct ovsdb_idl *idl;
unsigned int idl_seqno;
static char *appctl_path = NULL;
static struct unixctl_server *appctl;
static int system_configured = false;
/*
 * Global System ECMP status affects maxpath config
 * Keep a local ECMP status to update when needed
 * Default ECMP status is true
 */
static boolean sys_ecmp_status = true;
boolean exiting = false;
static int bgp_ovspoll_enqueue (bgp_ovsdb_t *bovs_g);
static int bovs_read_cb (struct thread *thread);

/*
 * ovs appctl dump function for this daemon
 * This is useful for debugging
 */
static void
bgp_unixctl_dump (struct unixctl_conn *conn, int argc OVS_UNUSED,
    const char *argv[] OVS_UNUSED, void *aux OVS_UNUSED)
{
}
boolean get_global_ecmp_status()
{
   return sys_ecmp_status;
}

/*
 * From vrf row in db to get bgp router with a specific asn
 */
static const struct ovsrec_bgp_router *
get_bgp_router_with_asn ( char *vrf_name, int64_t asn)
{
    int i;
    const struct ovsrec_vrf *ovs_vrf;
    OVSREC_VRF_FOR_EACH(ovs_vrf, idl) {
        if (!strcmp(ovs_vrf->name, vrf_name)) {
            for (i = 0; i < ovs_vrf->n_bgp_routers; i++) {
                if (ovs_vrf->key_bgp_routers[i] == asn) {
                    return ovs_vrf->value_bgp_routers[i];
                }
            }
        }
    }
    return NULL;
}

/*
 * Update the bgp router id in the router_id column of
 * bgp router table in db
 */
void
update_bgp_router_id_in_ovsdb (int64_t asn, char *router_id)
{
    const struct ovsrec_bgp_router *bgp_router_row;
    const struct ovsrec_vrf *vrf_row;
    struct ovsdb_idl_txn *bgp_router_txn=NULL;
    bgp_router_txn = ovsdb_idl_txn_create(idl);
    bgp_router_row =
        get_bgp_router_with_asn(DEFAULT_VRF_NAME, asn);
    if (bgp_router_row == NULL) {
        VLOG_ERR("No BGP Router found in OVSDB");
    } else {
        ovsrec_bgp_router_set_router_id(bgp_router_row,
                                      router_id);
    }
    ovsdb_idl_txn_commit_block(bgp_router_txn);
    ovsdb_idl_txn_destroy(bgp_router_txn);
}

/*
 * From bgp router row in db to get bgp asn #
 */
static int
ovsdb_bgp_router_from_row_to_asn (struct ovsdb_idl *idl,
    const struct ovsrec_bgp_router *ovs_bgp)
{
    int j;
    const struct ovsrec_vrf *ovs_vrf;

    OVSREC_VRF_FOR_EACH(ovs_vrf, idl) {
        for (j = 0; j < ovs_vrf->n_bgp_routers; j++) {
            if (ovs_bgp == ovs_vrf->value_bgp_routers[j]) {
                return ovs_vrf->key_bgp_routers[j];
            }
        }
    }
    return -1;
}


/*
 * From bgp nbr row in db to get peer name, a by product is that
 * it also returns its bgp asn#
 */
static char *
ovsdb_nbr_from_row_to_peer_name (struct ovsdb_idl *idl,
    const struct ovsrec_bgp_neighbor *ovs_nbr, int *asn)
{
    int i, j;
    const struct ovsrec_vrf *ovs_vrf;
    const struct ovsrec_bgp_router *ovs_bgp;

    OVSREC_VRF_FOR_EACH(ovs_vrf, idl) {
        for (i = 0; i < ovs_vrf->n_bgp_routers; i++) {
            if (asn)
                *asn = ovs_vrf->key_bgp_routers[i];
            ovs_bgp = ovs_vrf->value_bgp_routers[i];
            for (j = 0; j < ovs_bgp->n_bgp_neighbors; j++) {
                if (ovs_nbr == ovs_bgp->value_bgp_neighbors[j]) {
                    return ovs_bgp->key_bgp_neighbors[j];
                }
            }
        }
    }
    return NULL;
}

static bool
object_is_peer (const struct ovsrec_bgp_neighbor *db_bgpn_p)
{
    return (db_bgpn_p->n_is_peer_group == 0) || !(db_bgpn_p->is_peer_group[0]);
}

static bool
object_is_peer_group (const struct ovsrec_bgp_neighbor *db_bgpn_p)
{
    return (db_bgpn_p->n_is_peer_group > 0) && db_bgpn_p->is_peer_group[0];
}

static void
bgp_policy_ovsdb_init (struct ovsdb_idl *idl)
{

    ovsdb_idl_add_table(idl, &ovsrec_table_bgp_community_filter);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_community_filter_col_name);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_community_filter_col_type);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_community_filter_col_permit);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_community_filter_col_deny);

    ovsdb_idl_add_table(idl, &ovsrec_table_prefix_list);
    ovsdb_idl_add_column(idl, &ovsrec_prefix_list_col_name);
    ovsdb_idl_add_column(idl, &ovsrec_prefix_list_col_prefix_list_entries);
    ovsdb_idl_add_column(idl, &ovsrec_prefix_list_col_description);

    ovsdb_idl_add_table(idl, &ovsrec_table_prefix_list_entry);
    ovsdb_idl_add_column(idl, &ovsrec_prefix_list_entry_col_action);
    ovsdb_idl_add_column(idl, &ovsrec_prefix_list_entry_col_prefix);
    ovsdb_idl_add_column(idl, &ovsrec_prefix_list_entry_col_le);
    ovsdb_idl_add_column(idl, &ovsrec_prefix_list_entry_col_ge);

    ovsdb_idl_add_table(idl, &ovsrec_table_route_map);
    ovsdb_idl_add_column(idl, &ovsrec_route_map_col_name);
    ovsdb_idl_add_column(idl, &ovsrec_route_map_col_route_map_entries);

    ovsdb_idl_add_table(idl, &ovsrec_table_route_map_entry);
    ovsdb_idl_add_column(idl, &ovsrec_route_map_entry_col_action);
    ovsdb_idl_add_column(idl, &ovsrec_route_map_entry_col_description);
    ovsdb_idl_add_column(idl, &ovsrec_route_map_entry_col_exitpolicy);
    ovsdb_idl_add_column(idl, &ovsrec_route_map_entry_col_goto_target);
    ovsdb_idl_add_column(idl, &ovsrec_route_map_entry_col_call);
    ovsdb_idl_add_column(idl, &ovsrec_route_map_entry_col_match);
    ovsdb_idl_add_column(idl, &ovsrec_route_map_entry_col_set);

    ovsdb_idl_add_table(idl, &ovsrec_table_bgp_aspath_filter);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_aspath_filter_col_name);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_aspath_filter_col_permit);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_aspath_filter_col_deny);
}

static void
bgp_ovsdb_tables_init (struct ovsdb_idl *idl)
{
    /* VRF Table */
    ovsdb_idl_add_table(idl, &ovsrec_table_vrf);
    ovsdb_idl_add_column(idl, &ovsrec_vrf_col_name);
    ovsdb_idl_add_column(idl, &ovsrec_vrf_col_bgp_routers);

    /* BGP router table */
    ovsdb_idl_add_table(idl, &ovsrec_table_bgp_router);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_router_id);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_networks);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_maximum_paths);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_timers);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_redistribute);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_always_compare_med);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_deterministic_med);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_gr_stale_timer);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_bgp_neighbors);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_other_config);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_status);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_external_ids);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_fast_external_failover);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_log_neighbor_changes);

    /* BGP neighbor table */
    ovsdb_idl_add_table(idl, &ovsrec_table_bgp_neighbor);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_is_peer_group);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_description);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_shutdown);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_bgp_peer_group);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_local_interface);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_remote_as);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_allow_as_in);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_local_as);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_weight);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_tcp_port_number);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_advertisement_interval);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_maximum_prefix_limit);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_inbound_soft_reconfiguration);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_remove_private_as);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_passive);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_password);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_timers);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_route_maps);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_prefix_lists);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_aspath_filters);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_statistics);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_status);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_external_ids);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_other_config);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_ebgp_multihop);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_ttl_security_hops);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_update_source);

    /* BGP policy */
    bgp_policy_ovsdb_init(idl);

    /* Global RIB table */
    ovsdb_idl_add_table(idl, &ovsrec_table_route);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_prefix);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_from);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_nexthops);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_address_family);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_sub_address_family);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_selected);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_distance);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_metric);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_vrf);

    /* Global nexthop table */
    ovsdb_idl_add_table(idl, &ovsrec_table_nexthop);
    ovsdb_idl_add_column(idl, &ovsrec_nexthop_col_ip_address);
    ovsdb_idl_add_column(idl, &ovsrec_nexthop_col_selected);
    ovsdb_idl_add_column(idl, &ovsrec_nexthop_col_weight);
    ovsdb_idl_add_column(idl, &ovsrec_nexthop_col_status);
    ovsdb_idl_add_column(idl, &ovsrec_nexthop_col_other_config);
    ovsdb_idl_add_column(idl, &ovsrec_nexthop_col_external_ids);

    /* BGP RIB table */
    ovsdb_idl_add_table(idl, &ovsrec_table_bgp_route);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_route_col_prefix);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_route_col_bgp_nexthops);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_route_col_address_family);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_route_col_sub_address_family);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_route_col_distance);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_route_col_metric);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_route_col_vrf);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_route_col_path_attributes);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_route_col_peer);

    /* BGP Nexthop table */
    ovsdb_idl_add_table(idl, &ovsrec_table_bgp_nexthop);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_nexthop_col_ip_address);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_nexthop_col_type);
}

/*
 * Create a connection to the OVSDB at db_path and create a dB cache
 * for this daemon.
 */
static void
ovsdb_init (const char *db_path)
{
    /* Initialize IDL through a new connection to the dB. */
    idl = ovsdb_idl_create(db_path, &ovsrec_idl_class, false, true);
    idl_seqno = ovsdb_idl_get_seqno(idl);
    ovsdb_idl_set_lock(idl, "OpenSwitch_bgp");

    /* Cache OpenVSwitch table */
    ovsdb_idl_add_table(idl, &ovsrec_table_system);

    ovsdb_idl_add_column(idl, &ovsrec_system_col_cur_cfg);
    ovsdb_idl_add_column(idl, &ovsrec_system_col_hostname);
    ovsdb_idl_add_column(idl, &ovsrec_system_col_ecmp_config);

    /* BGP tables */
    bgp_ovsdb_tables_init(idl);

    /* Register ovs-appctl commands for this daemon. */
    unixctl_command_register("bgpd/dump", "", 0, 0, bgp_unixctl_dump, NULL);
}

static void
ops_bgp_exit (struct unixctl_conn *conn, int argc OVS_UNUSED,
    const char *argv[] OVS_UNUSED, void *exiting_)
{
    boolean *exiting = exiting_;

    *exiting = true;
    unixctl_command_reply(conn, NULL);
}

static void
usage (void)
{
    printf("%s: OpenSwitch bgp daemon\n"
           "usage: %s [OPTIONS] [DATABASE]\n"
           "where DATABASE is a socket on which ovsdb-server is listening\n"
           "      (default: \"unix:%s/db.sock\").\n",
           program_name, program_name, ovs_rundir());
    stream_usage("DATABASE", true, false, true);
    daemon_usage();
    vlog_usage();
    printf("\nOther options:\n"
           "  --unixctl=SOCKET        override default control socket name\n"
           "  -h, --help              display this help message\n"
           "  -V, --version           display version information\n");

    exit(EXIT_SUCCESS);
}

/*
 * OPS_TODO: Need to merge this parse function with the main parse function
 * in bgp_main to avoid issues.
 */
static char *
bgp_ovsdb_parse_options (int argc, char *argv[], char **unixctl_pathp)
{
    enum {
        OPT_UNIXCTL = UCHAR_MAX + 1,
        VLOG_OPTION_ENUMS,
        DAEMON_OPTION_ENUMS,
        OVSDB_OPTIONS_END,
    };
    static const struct option long_options[] = {
        {"help",        no_argument, NULL, 'h'},
        {"unixctl",     required_argument, NULL, OPT_UNIXCTL},
        DAEMON_LONG_OPTIONS,
        VLOG_LONG_OPTIONS,
        {NULL, 0, NULL, 0},
    };
    char *short_options = long_options_to_short_options(long_options);

    for (;;) {
        int c;

        c = getopt_long(argc, argv, short_options, long_options, NULL);
        if (c == -1) {
            break;
        }

        switch (c) {
        case 'h':
            usage();

        case OPT_UNIXCTL:
            *unixctl_pathp = optarg;
            break;

        VLOG_OPTION_HANDLERS
        DAEMON_OPTION_HANDLERS

        case '?':
            exit(EXIT_FAILURE);

        default:
           abort();
        }
    }
    free(short_options);

    argc -= optind;
    argv += optind;

    return xasprintf("unix:%s/db.sock", ovs_rundir());
}

/*
 * Setup bgp to connect with ovsdb and daemonize. This daemonize is used
 * over the daemonize in the main function to keep the behavior consistent
 * with the other daemons in the OpenSwitch system
 */
void bgp_ovsdb_init (int argc, char *argv[])
{
    int retval;
    char *ovsdb_sock;

    memset(&glob_bgp_ovs, 0, sizeof(glob_bgp_ovs));

    set_program_name(argv[0]);
    proctitle_init(argc, argv);
    fatal_ignore_sigpipe();

    /* Parse commandline args and get the name of the OVSDB socket. */
    ovsdb_sock = bgp_ovsdb_parse_options(argc, argv, &appctl_path);

    /* Initialize the metadata for the IDL cache. */
    ovsrec_init();

    /*
     * Fork and return in child process; but don't notify parent of
     * startup completion yet.
     */
    daemonize_start();

    /* Create UDS connection for ovs-appctl. */
    retval = unixctl_server_create(appctl_path, &appctl);
    if (retval) {
       exit(EXIT_FAILURE);
    }

    /* Register the ovs-appctl "exit" command for this daemon. */
    unixctl_command_register("exit", "", 0, 0, ops_bgp_exit, &exiting);

   /* Create the IDL cache of the dB at ovsdb_sock. */
   ovsdb_init(ovsdb_sock);
   free(ovsdb_sock);

   /* Notify parent of startup completion. */
   daemonize_complete();

   /* Enable asynch log writes to disk. */
   vlog_enable_async();

   VLOG_INFO_ONCE("%s (OpenSwitch Bgpd Daemon) started", program_name);

   glob_bgp_ovs.enabled = 1;
}

static void
bgp_ovs_clear_fds (void)
{
    struct poll_loop *loop = poll_loop();
    free_poll_nodes(loop);
    loop->timeout_when = LLONG_MAX;
    loop->timeout_where = NULL;
}

/* Check if the system is already configured. The daemon should
 * not process any callbacks unless the system is configured.
 */
static inline void bgp_chk_for_system_configured(void)
{
    const struct ovsrec_system *sys = NULL;

    if (system_configured) {
        /* Nothing to do if we're already configured. */
        return;
    }

    sys = ovsrec_system_first(idl);

    if (sys && (sys->cur_cfg > (int64_t) 0)) {
        system_configured = true;
        VLOG_INFO("System is now configured (cur_cfg=%d).",
            (int)sys->cur_cfg);
    }
}

static void
bgp_set_hostname (char *hostname)
{
    if (host.name)
        XFREE (MTYPE_HOST, host.name);
    host.name = XSTRDUP(MTYPE_HOST, hostname);
}

static void
modify_bgp_neighbor_route_map (const struct ovsrec_bgp_neighbor *ovs_bgpn,
    struct bgp *bgp_instance,
    const char *direction,
    afi_t afi, safi_t safi)
{
    /*
     * If an entry for "direction" is not found in the record, NULL name
     * will trigger an unset
     */
    char *name = NULL;

    int i;
    char *direct;

    for (i = 0; i < ovs_bgpn->n_route_maps; i++) {
        direct = ovs_bgpn->key_route_maps[i];
        if (!strcmp(direct, direction)) {
            struct ovsrec_route_map *rm = ovs_bgpn->value_route_maps[i];
            name = rm->name;
            break;
        }
    }
    daemon_neighbor_route_map_cmd_execute(bgp_instance,
        ovsdb_nbr_from_row_to_peer_name(idl, ovs_bgpn, NULL),
        afi, safi, name, direction);
}

static void
modify_bgp_neighbor_prefix_list (const struct ovsrec_bgp_neighbor *ovs_bgpn,
    struct bgp *bgp_instance,
    const char *direction,
    afi_t afi, safi_t safi)
{
    /*
     * If an entry for "direction" is not found in the record, NULL name
     * will trigger an unset
     */
    char *name = NULL;
    char *direct;
    int i;

    for (i = 0; i < ovs_bgpn->n_prefix_lists; i++) {
        direct = ovs_bgpn->key_prefix_lists[i];
        if (!strcmp(direct, direction)) {
            struct ovsrec_prefix_list *plist = ovs_bgpn->value_prefix_lists[i];
            name = plist->name;
            break;
        }
    }
    daemon_neighbor_prefix_list_cmd_execute(bgp_instance,
                          ovsdb_nbr_from_row_to_peer_name(idl, ovs_bgpn, NULL),
                          afi, safi, name, direction);
}

static void
modify_bgp_neighbor_aspath_filter(const struct ovsrec_bgp_neighbor *ovs_bgpn,
                                  struct bgp *bgp_instance,
                                  const char *direction,
                                  afi_t afi, safi_t safi)
{
    /*
     * If an entry for "direction" is not found in the record, NULL name
     * will trigger an unset
     */
    char *name = NULL;
    char *direct;
    struct ovsrec_bgp_aspath_filter *flist;
    int i;

    for (i = 0; i < ovs_bgpn->n_aspath_filters; i++) {
        direct = ovs_bgpn->key_aspath_filters[i];
        if (!strcmp(direct, direction)) {
            flist = ovs_bgpn->value_aspath_filters[i];
            name = flist->name;
            break;
        }
    }
    daemon_neighbor_aspath_filter_cmd_execute(bgp_instance,
        ovsdb_nbr_from_row_to_peer_name(idl, ovs_bgpn, NULL),
            afi, safi, name, direction);
}

afi_t
network2afi (const char *network)
{
    struct prefix p;
    afi_t afi;

    if (!str2prefix(network, &p)) {
        return 0;
    }

    afi = family2afi(p.family);
    return afi;
}

static void
apply_bgp_neighbor_route_map_changes(const struct ovsrec_bgp_neighbor *ovs_bgpn,
                                     struct bgp *bgp_instance)
{
    afi_t afi;
    safi_t safi = SAFI_UNICAST;

    /* Attempt to obtain the AFI. If it is a neighbor, then the AFI can be
     * obtained from the IP address.
     */
    if (object_is_peer(ovs_bgpn)) {
        afi = network2afi(ovsdb_nbr_from_row_to_peer_name(idl, ovs_bgpn, NULL));
    } else {
        /* OPS_TODO: For now, until IPv6 is supported, use AFI_IP by default
         * for peer-groups
         */
        afi = AFI_IP;
    }

    if (afi) {
        char *direct;
        direct = OVSREC_BGP_NEIGHBOR_ROUTE_MAPS_IN;
        modify_bgp_neighbor_route_map(ovs_bgpn, bgp_instance, direct,
                                      afi, safi);
        direct = OVSREC_BGP_NEIGHBOR_ROUTE_MAPS_OUT;
        modify_bgp_neighbor_route_map(ovs_bgpn, bgp_instance, direct,
                                      afi, safi);
    } else {
        VLOG_ERR("Invalid AFI");
    }
}

static void
apply_bgp_neighbor_prefix_list_changes(const struct ovsrec_bgp_neighbor *ovs_bgpn,
                                     struct bgp *bgp_instance)
{
    afi_t afi;
    safi_t safi = SAFI_UNICAST;
    char *direct;

    if (object_is_peer(ovs_bgpn)) {
        afi = network2afi(ovsdb_nbr_from_row_to_peer_name(idl, ovs_bgpn, NULL));
    } else {
        afi = AFI_IP;
    }

    if (afi) {
        direct = OVSREC_BGP_NEIGHBOR_PREFIX_LISTS_IN;
        modify_bgp_neighbor_prefix_list(ovs_bgpn, bgp_instance, direct,
                                      afi, safi);
        direct = OVSREC_BGP_NEIGHBOR_PREFIX_LISTS_OUT;
        modify_bgp_neighbor_prefix_list(ovs_bgpn, bgp_instance, direct,
                                      afi, safi);
    }
}

static void
apply_bgp_neighbor_aspath_filter_changes(const struct ovsrec_bgp_neighbor *ovs_bgpn,
                                         struct bgp *bgp_instance)
{
    afi_t afi;
    safi_t safi = SAFI_UNICAST;
    char *direct;

    /* Attempt to obtain the AFI. If it is a neighbor, then the AFI can be
     * obtained from the IP address.
     */
    if (object_is_peer(ovs_bgpn)) {
        afi = network2afi(ovsdb_nbr_from_row_to_peer_name(idl, ovs_bgpn, NULL));
    } else {
        afi = AFI_IP;
    }

    if (afi) {
        direct = OVSREC_BGP_NEIGHBOR_ASPATH_FILTERS_IN;
        modify_bgp_neighbor_aspath_filter(ovs_bgpn, bgp_instance, direct,
                                          afi, safi);
        direct = OVSREC_BGP_NEIGHBOR_ASPATH_FILTERS_OUT;
        modify_bgp_neighbor_aspath_filter(ovs_bgpn, bgp_instance, direct,
                                          afi, safi);
    } else {
        VLOG_ERR("Invalid AFI");
    }
}

static void
bgp_apply_global_changes (void)
{
    const struct ovsrec_system *sys;
    const struct ovsrec_vrf *ovs_vrf;
    const struct ovsrec_bgp_router *ovs_bgp;
    int64_t asn;
    int i;
    boolean ecmp_status;

    sys = ovsrec_system_first(idl);
    if (OVSREC_IDL_ANY_TABLE_ROWS_DELETED(sys, idl_seqno)) {
        VLOG_WARN("First Row deleted from System tbl\n");
        return;
    }
    if (!OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(sys, idl_seqno) &&
            !OVSREC_IDL_ANY_TABLE_ROWS_MODIFIED(sys, idl_seqno)) {
        VLOG_DBG("No System cfg changes");
        return;
    }

    if(OVSREC_IDL_IS_COLUMN_MODIFIED(ovsrec_system_col_ecmp_config, idl_seqno) ) {
        ecmp_status = smap_get_bool(&sys->ecmp_config, SYSTEM_ECMP_CONFIG_STATUS,
                SYSTEM_ECMP_CONFIG_ENABLE_DEFAULT);
        if(sys_ecmp_status != ecmp_status) {
            VLOG_INFO("ECMP changed compared to local cache!");
            sys_ecmp_status = ecmp_status;
            OVSREC_VRF_FOR_EACH(ovs_vrf, idl) {
                for (i = 0; i < ovs_vrf->n_bgp_routers; i++) {
                    asn = ovs_vrf->key_bgp_routers[i];
                    ovs_bgp = ovs_vrf->value_bgp_routers[i];
                    bgp_ovsdb_republish_route(ovs_bgp, asn);
                }
            }
        }
    }
    if (sys) {
        /* Update the hostname */
        bgp_set_hostname(sys->hostname);
    }
}

void
delete_bgp_router_config (struct ovsdb_idl *idl)
{
    struct ovsrec_bgp_router *bgp_del_row;
    const struct ovsrec_vrf *ovs_vrf;
    int64_t asn;
    struct bgp *bgp_cfg;
    int i;

    while (bgp_cfg = bgp_lookup_by_name(NULL)) {
        bool match_found = 0;

        OVSREC_VRF_FOR_EACH(ovs_vrf, idl) {
            for (i = 0; i < ovs_vrf->n_bgp_routers; i++) {
                if (bgp_cfg->as == ovs_vrf->key_bgp_routers[i]) {
                    match_found = 1;
                    break;
                }
            }
            if (!match_found) {
                VLOG_DBG("bgp_cfg->as: %d will be deleted from BGPD\n", bgp_cfg->as);
                bgp_delete(bgp_cfg);
            }
        }
    }
}

void
delete_redistribute_config(struct ovsdb_idl *idl,
                           const struct ovsrec_bgp_router *bgp_mod_row,
                           struct bgp *bgp)
{
    const struct ovsrec_bgp_router *ovs_first;
    int i,j,type;
    int ret;
    bool match_found = false;
    for (j = 0; j < ZEBRA_ROUTE_MAX; j++) {
        match_found = false;
        ret = 0;
        if (bgp->redist[AFI_IP][j] && j != ZEBRA_ROUTE_BGP) {
            OVSREC_BGP_ROUTER_FOR_EACH(bgp_mod_row, idl) {
                for (i=0; i< bgp_mod_row->n_redistribute; i++) {
                    if (strcmp(bgp_mod_row->key_redistribute[i],
                               zebra_route_string(j)) ==0 ) {
                        match_found = true;
                        break;
                    }
                }
                if (match_found == true) {
                    break;
                }
            }
            if ( match_found == false ) {
                    ret = bgp_redistribute_unset (bgp, AFI_IP, j);
                    if (!ret) {
                        VLOG_DBG("Deleted redistribute %s",
                                  zebra_route_string(j));
                    }
            }
        }
    }
    return;
}

void
modify_bgp_redistribute_config(struct ovsdb_idl *idl,struct bgp *bgp_cfg,
    const struct ovsrec_bgp_router *bgp_mod_row)
{
    int i=0;
    int type;
    int rmap;
    int ret_status = -1;

    /* Handle redistribute deletions. */
    delete_redistribute_config(idl,bgp_mod_row, bgp_cfg);

    VLOG_DBG("Setting  BGP Redistribute protocol configuration");
    OVSREC_BGP_ROUTER_FOR_EACH(bgp_mod_row, idl) {
        for (i = 0; i<bgp_mod_row->n_redistribute; i++) {
            if (strlen(bgp_mod_row->value_redistribute[i]->name) == 0) {
                type = proto_redistnum (AFI_IP, bgp_mod_row->
                                        key_redistribute[i]);
                if (type < 0 || type == ZEBRA_ROUTE_BGP) {
                    VLOG_DBG("Invalid route type");
                }
                ret_status = bgp_redistribute_set(bgp_cfg, AFI_IP, type);
                if (!ret_status) {
                    VLOG_DBG("redistribute %s is set",bgp_mod_row->
                             key_redistribute[i]);
                }
            } else {
                type = proto_redistnum (AFI_IP, bgp_mod_row->
                                        key_redistribute[i]);
                if (type < 0 || type == ZEBRA_ROUTE_BGP) {
                    VLOG_DBG("Invalid route type");
                }

                rmap=bgp_redistribute_rmap_set (bgp_cfg, AFI_IP, type,
                                      bgp_mod_row->value_redistribute[i]->name);
                ret_status = bgp_redistribute_set(bgp_cfg, AFI_IP, type);
                if (!rmap && !ret_status) {
                    VLOG_DBG("redistribute %s route-map %s is set",
                              bgp_mod_row->key_redistribute[i],
                              bgp_mod_row->value_redistribute[i]->name);
                }
            }
        }
    }
}

void
insert_bgp_router_config (struct ovsdb_idl *idl,
    const struct ovsrec_bgp_router *bgp_first, int asn)
{
    struct bgp *bgp_cfg;
    int ret_status;

    VLOG_DBG("New row insertion to BGP config\n");
    ret_status = bgp_get(&bgp_cfg, (as_t *)&asn, NULL);
    if (!ret_status) {
        VLOG_DBG("bgp_cfg->as: %d", bgp_cfg->as);
    }
}

/* To configure BGP fast-external-failover flag which allows to immediately
 * reset external BGP peering sessions if the link goes down.
 */
void
modify_bgp_fast_external_failover_config (struct bgp *bgp_cfg,
                                          const struct ovsrec_bgp_router *bgp_mod_row)
{
    if (bgp_mod_row->n_fast_external_failover && bgp_mod_row->fast_external_failover[0]) {
        VLOG_DBG("Setting BGP fast external failover flag");
        bgp_flag_unset (bgp_cfg, BGP_FLAG_NO_FAST_EXT_FAILOVER);
    } else {
        VLOG_DBG("Unsetting BGP fast external failover flag");
        bgp_flag_set (bgp_cfg, BGP_FLAG_NO_FAST_EXT_FAILOVER);
    }
}

/* To configure BGP log-neighbor-changes flag which enables the generation of
 * logging messages generated when the status of a BGP neighbor changes.
 */
void
modify_bgp_log_neighbor_changes_config (struct bgp *bgp_cfg,
                                        const struct ovsrec_bgp_router *bgp_mod_row)
{
    if (bgp_mod_row->n_log_neighbor_changes && bgp_mod_row->log_neighbor_changes[0]) {
        VLOG_DBG("Setting BGP log neighbor changes flag");
        bgp_flag_set(bgp_cfg, BGP_FLAG_LOG_NEIGHBOR_CHANGES);
    } else {
        VLOG_DBG("Unsetting BGP log neighbor changes flag");
        bgp_flag_unset(bgp_cfg, BGP_FLAG_LOG_NEIGHBOR_CHANGES);
    }
}

void
modify_bgp_router_config (struct ovsdb_idl *idl,
    const struct ovsrec_bgp_router *bgp_first, int asn)
{
    const struct ovsrec_bgp_router *bgp_mod_row = bgp_first;
    const struct ovsdb_idl_column *column;
    struct bgp *bgp_cfg;
    as_t as;
    int ret_status;

    bgp_cfg = bgp_lookup((as_t)asn, NULL);

    /* Check if router_id is modified */
    if (OVSREC_IDL_IS_COLUMN_MODIFIED(ovsrec_bgp_router_col_router_id, idl_seqno)) {
        ret_status = modify_bgp_router_id_config(bgp_cfg, bgp_mod_row);
        if (!ret_status) {
            VLOG_DBG("BGP router_id set to %s", inet_ntoa(bgp_cfg->router_id));
        }
    }

    /* Check if network is modified */
    if (OVSREC_IDL_IS_COLUMN_MODIFIED(ovsrec_bgp_router_col_networks, idl_seqno)) {
        ret_status = modify_bgp_network_config(bgp_cfg,bgp_mod_row);
        if (!ret_status) {
             VLOG_DBG("Static route added/deleted to bgp routing table");
        }
    }

    /* Check if maximum_paths is modified */
    if (OVSREC_IDL_IS_COLUMN_MODIFIED(ovsrec_bgp_router_col_maximum_paths, idl_seqno)) {
        ret_status = modify_bgp_maxpaths_config(bgp_cfg,bgp_mod_row);
        if (!ret_status) {
            VLOG_DBG("Maximum paths for BGP is set to %d",
                bgp_cfg->maxpaths[AFI_IP][SAFI_UNICAST].maxpaths_ebgp);
        }
    }

    /* Check if bgp timers are modified */
    if (OVSREC_IDL_IS_COLUMN_MODIFIED(ovsrec_bgp_router_col_timers, idl_seqno)) {
        modify_bgp_timers_config(bgp_cfg,bgp_mod_row);
    }

    /* Check if bgp fast external failover is set */
    if (OVSREC_IDL_IS_COLUMN_MODIFIED(ovsrec_bgp_router_col_fast_external_failover,
                                      idl_seqno)) {
        modify_bgp_fast_external_failover_config(bgp_cfg, bgp_mod_row);
    }

    /* Check if bgp log neighbor changes is set */
    if (OVSREC_IDL_IS_COLUMN_MODIFIED(ovsrec_bgp_router_col_log_neighbor_changes,
                                      idl_seqno)) {
        modify_bgp_log_neighbor_changes_config(bgp_cfg, bgp_mod_row);
    }

    /* Check redistribute configuration is modified*/
    if (OVSREC_IDL_IS_COLUMN_MODIFIED(ovsrec_bgp_router_col_redistribute, idl_seqno)) {
        VLOG_DBG("Redistribute configuration  modified");
        modify_bgp_redistribute_config(idl, bgp_cfg, bgp_mod_row);
    }
}


int
modify_bgp_router_id_config (struct bgp *bgp_cfg,
    const struct ovsrec_bgp_router *bgp_mod_row)
{
    const struct ovsdb_idl_column *column;
    struct in_addr addr;

    addr.s_addr = inet_addr(bgp_mod_row->router_id);
    if (addr.s_addr != 0)
        return bgp_router_id_set(bgp_cfg, &addr);
    else
        return bgp_router_id_unset(bgp_cfg, &addr);
}

void
bgp_static_route_dump (struct bgp *bgp_cfg, struct bgp_node *rn)
{
    char prefix_str[256];
    int ret;

    for (rn = bgp_table_top (bgp_cfg->route[AFI_IP][SAFI_UNICAST]); rn;
         rn = bgp_route_next (rn)) {
            memset(prefix_str, 0 ,sizeof(prefix_str));
            ret = prefix2str(&rn->p, prefix_str, sizeof(prefix_str));
            if (ret) {
                VLOG_ERR("Prefix to string conversion failed!");
            } else {
                if (!strcmp(prefix_str,"0.0.0.0/0"))
                   continue;
                if (rn->info != NULL)
                    VLOG_DBG("Static route : %s", prefix_str);
            }
    }
}

int
modify_bgp_network_config (struct bgp *bgp_cfg,
    const struct ovsrec_bgp_router *bgp_mod_row)
{
    int ret_status = 0;

    VLOG_DBG("bgp_mod_row->n_networks = %d", bgp_mod_row->n_networks);
    ret_status = bgp_static_route_addition(bgp_cfg, bgp_mod_row);
    if (ret_status == CMD_SUCCESS) {
        VLOG_DBG("Static route added.");
    }
    ret_status = bgp_static_route_deletion(bgp_cfg, bgp_mod_row);
    if (ret_status == CMD_SUCCESS) {
        VLOG_DBG("Static route deleted.");
    }
    return ret_status;
}

int
bgp_static_route_addition (struct bgp *bgp_cfg,
    const struct ovsrec_bgp_router *bgp_mod_row)
{
    struct prefix p;
    struct bgp_node *rn;
    afi_t afi;
    safi_t safi;
    int ret_status = -1;
    int i = 0;

    for (i = 0; i < bgp_mod_row->n_networks; i++) {
        VLOG_DBG("bgp_mod_row->networks[%d]: %s", i, bgp_mod_row->networks[i]);

        int ret = str2prefix(bgp_mod_row->networks[i], &p);
        if (! ret) {
            VLOG_ERR("Malformed prefix");
            return -1;
        }
        afi = family2afi(p.family);
        safi = SAFI_UNICAST;
        rn = bgp_node_lookup(bgp_cfg->route[afi][safi], &p);
        if (!rn) {
            VLOG_DBG("Can't find specified static route configuration..\n");
            ret_status = bgp_static_set(NULL, bgp_cfg,
                            bgp_mod_row->networks[i], afi, safi, NULL, 0);
            if (!ret_status)
                bgp_static_route_dump(bgp_cfg,rn);
            else
                VLOG_ERR("Static route addition failed!!");
        } else {
            VLOG_DBG("Network %s already exists. Skip adding.");
        }
    }
    return ret_status;
}

int
bgp_static_route_deletion (struct bgp *bgp_cfg,
                           const struct ovsrec_bgp_router *bgp_mod_row)
{
    struct bgp_node *rn;
    afi_t afi;
    safi_t safi;
    int ret_status = -1;
    int i = 0;
    int afi_type;

    if (bgp_cfg = bgp_lookup((as_t)ovsdb_bgp_router_from_row_to_asn(idl, bgp_mod_row),
        NULL))
    {
        bool match_found = 0;
        char prefix_str[256];

        for (afi_type = AFI_IP; afi_type < AFI_MAX; afi_type++) {
            for (rn = bgp_table_top (bgp_cfg->route[afi_type][SAFI_UNICAST]); rn;
                   rn = bgp_route_next (rn)) {
                memset(prefix_str, 0 ,sizeof(prefix_str));

                int ret = prefix2str(&rn->p, prefix_str, sizeof(prefix_str));
                if (ret) {
                    VLOG_ERR("Prefix to string conversion failed!");
                    return -1;
                } else {
                    VLOG_DBG("Prefix to str : %s", prefix_str);
                }

                afi = family2afi(rn->p.family);
                safi = SAFI_UNICAST;

                if ((bgp_mod_row->n_networks == 0)) {
                    VLOG_DBG("Last static route being deleted...");
                    ret_status = bgp_static_unset(NULL, bgp_cfg, prefix_str,
                                     afi, safi);
                    if (!ret_status)
                        bgp_static_route_dump(bgp_cfg,rn);
                    else
                        VLOG_ERR("Last static route deletion failed!!");
                } else {
                    bool match_found = 0;
                    for (i = 0; i < bgp_mod_row->n_networks; i++) {
                        if (!strcmp(prefix_str, bgp_mod_row->networks[i])) {
                            match_found = 1;
                            break;
                        }
                    }
                    if (!match_found) {
                        VLOG_DBG("Static route being deleted...");
                        ret_status = bgp_static_unset(NULL, bgp_cfg, prefix_str,
                                                      afi, safi);
                        if (!ret_status)
                            bgp_static_route_dump(bgp_cfg,rn);
                        else
                            VLOG_ERR("Static route deletion failed!!");
                    } else {
                        VLOG_DBG("Static route exists. Skip deleting.");
                    }
                }

            }
        }
    }
    return ret_status;
}

int
modify_bgp_maxpaths_config (struct bgp *bgp_cfg,
    const struct ovsrec_bgp_router *bgp_mod_row)
{
    if (bgp_mod_row->n_maximum_paths && bgp_mod_row->maximum_paths[0]) {
        VLOG_DBG("Setting max paths");
        bgp_flag_set(bgp_cfg, BGP_FLAG_ASPATH_MULTIPATH_RELAX);
        return
            bgp_maximum_paths_set(bgp_cfg, AFI_IP, SAFI_UNICAST,
                BGP_PEER_EBGP, (u_int16_t) bgp_mod_row->maximum_paths[0]);
    }

    VLOG_DBG("Unsetting max paths");
    bgp_flag_unset(bgp_cfg, BGP_FLAG_ASPATH_MULTIPATH_RELAX);
    return
        bgp_maximum_paths_unset(bgp_cfg, AFI_IP, SAFI_UNICAST, BGP_PEER_EBGP);
}

int
modify_bgp_timers_config (struct bgp *bgp_cfg,
    const struct ovsrec_bgp_router *bgp_mod_row)
{
    int64_t keepalive = 0, holdtime = 0, ret_status = 0;
    struct smap smap;
    const struct ovsdb_datum *datum;

    datum = ovsrec_bgp_router_get_timers(bgp_mod_row, OVSDB_TYPE_STRING,
                OVSDB_TYPE_INTEGER);

    /* Can be seen on ovsdb restart */
    if (NULL == datum) {
        VLOG_DBG("No value found for given key");
        ret_status = -1;
    } else {
        if (bgp_mod_row->n_timers) {
            ovsdb_datum_get_int64_value_given_string_key(datum,
                bgp_mod_row->key_timers[1], &keepalive);
            ovsdb_datum_get_int64_value_given_string_key(datum,
                bgp_mod_row->key_timers[0], &holdtime);

            ret_status = bgp_timers_set(bgp_cfg, keepalive, holdtime);
            VLOG_DBG("Set keepalive:%lld and holdtime:%lld timers",
                     keepalive, holdtime);
        } else {
            ret_status = bgp_timers_unset(bgp_cfg);
            VLOG_DBG("Timers have been unset");
        }
    }

    return ret_status;
}

static void
bgp_router_read_ovsdb_apply_changes (struct ovsdb_idl *idl)
{
    const struct ovsrec_vrf *ovs_vrf = NULL;
    const struct ovsrec_bgp_router *ovs_bgp;
    const struct ovsrec_bgp_neighbor *ovs_bgpnbr;
    struct smap_node *node;
    int asn;
    char peer[80];

    struct bgp *bgp_instance;
    bool modified = false;
    bool deleted = false;
    int i;

   /*
    * From each VRF table,
    *   for each row in bgp router table, inserted/modified ?
    *      for the changed row, any specific column ?
    */
    OVSREC_VRF_FOR_EACH(ovs_vrf, idl) {
        for (i = 0; i < ovs_vrf->n_bgp_routers; i++) {
            asn = ovs_vrf->key_bgp_routers[i];
            ovs_bgp = ovs_vrf->value_bgp_routers[i];
            if (OVSREC_IDL_IS_ROW_INSERTED(ovs_bgp, idl_seqno)) {
                insert_bgp_router_config(idl, ovs_bgp, asn);
            }
            if (OVSREC_IDL_IS_ROW_MODIFIED(ovs_bgp, idl_seqno) ||
                (OVSREC_IDL_IS_ROW_INSERTED(ovs_bgp, idl_seqno))) {
                    modify_bgp_router_config(idl, ovs_bgp, asn);
            }
        }
    }
}
/*
 * Subscribe for changes in the BGP_Router table
 */
static void
bgp_apply_bgp_router_changes (struct ovsdb_idl *idl)
{
    const struct ovsrec_bgp_router *bgp_first;
    struct bgp *bgp_cfg;

    bgp_first = ovsrec_bgp_router_first(idl);
    /*
     * Check if any table changes present.
     * If no change just return from here
     */
    if (bgp_first && !OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(bgp_first, idl_seqno)
        && !OVSREC_IDL_ANY_TABLE_ROWS_DELETED(bgp_first, idl_seqno)
        && !OVSREC_IDL_ANY_TABLE_ROWS_MODIFIED(bgp_first, idl_seqno)) {
        VLOG_DBG("No BGP_Router changes");
        return;
    }

    if (bgp_first == NULL) {
        /* Check if it is a first row deletion */
        VLOG_DBG("BGP config empty!\n");
        bgp_cfg = bgp_lookup_by_name(NULL);
        if (bgp_cfg) {
            bgp_delete(bgp_cfg);
        }
        return;
    }

    /* Check if any row deletion */
    if (OVSREC_IDL_ANY_TABLE_ROWS_DELETED(bgp_first, idl_seqno)) {
        delete_bgp_router_config(idl);
    }

    /* insert and modify cases */
    bgp_router_read_ovsdb_apply_changes(idl);
}

/*
 * Iterate through all the peers of the BGP and check against
 * ovsdb to identify which neighbor has been deleted. If it doesn't exist
 * in ovsdb then it is considered deleted.
 */
static void
check_and_delete_bgp_neighbors (struct bgp *bgp,
    const struct ovsrec_bgp_router *ovs_bgp,
    struct ovsdb_idl *idl)
{
    struct peer *peer;
    struct listnode *node, *nnode;
    struct ovsrec_bgp_neighbor *ovs_nbr;
    int i;
    bool deleted_from_database;

    for (ALL_LIST_ELEMENTS (bgp->peer, node, nnode, peer)) {
        deleted_from_database = true;
        for (i = 0; i < ovs_bgp->n_bgp_neighbors; i++) {
            ovs_nbr = ovs_bgp->value_bgp_neighbors[i];
            if (object_is_peer(ovs_nbr) &&
                !strcmp(ovs_bgp->key_bgp_neighbors[i], peer->host)) {
                    deleted_from_database = false;
                    break;
            }
        }

        if (deleted_from_database) {
            VLOG_DBG("bgp peer %s being deleted", peer->host);
            peer_delete(peer);
        }
    }
}

/*
 * same as above but for peer groups
 */
static void
check_and_delete_bgp_neighbor_peer_groups (struct bgp *bgp,
    const struct ovsrec_bgp_router *ovs_bgp,
    struct ovsdb_idl *idl)
{
    struct peer_group *peer_group;
    struct listnode *node, *nnode;
    struct ovsrec_bgp_neighbor *ovs_nbr;
    bool deleted_from_database;
    int i;

    for (ALL_LIST_ELEMENTS (bgp->group, node, nnode, peer_group)) {
        deleted_from_database = true;
        for (i = 0; i < ovs_bgp->n_bgp_neighbors; i++) {
            ovs_nbr = ovs_bgp->value_bgp_neighbors[i];
            if (object_is_peer_group(ovs_nbr) &&
                !strcmp(ovs_bgp->key_bgp_neighbors[i], peer_group->name)) {
                    deleted_from_database = false;
                    break;
            }
        }

        if (deleted_from_database) {
            VLOG_DBG("peer group %s being deleted", peer_group->name);
            peer_group_delete(peer_group);
        }
    }
}

/*
 * since we cannot possibly know in advance what is deleted
 * from the database, we check for *ALL* bgps, all of their
 * groups & all of their peers.
 */
static void
delete_bgp_neighbors_and_peer_groups (struct ovsdb_idl *idl)
{
    const struct ovsrec_vrf *ovs_vrf = NULL;
    const struct ovsrec_bgp_router *ovs_bgp;
    struct smap_node *node;
    int asn;
    int i;
    struct bgp *pbgp;

    OVSREC_VRF_FOR_EACH(ovs_vrf, idl) {
        for (i = 0; i < ovs_vrf->n_bgp_routers; i++) {
            asn = ovs_vrf->key_bgp_routers[i];
            ovs_bgp = ovs_vrf->value_bgp_routers[i];
            pbgp = bgp_lookup(asn, NULL);
            if (!pbgp) {
               VLOG_ERR("%%cannot find daemon bgp router instance %d %%\n", asn);
               continue;
            }
            VLOG_DBG("bgp router instance %d found\n", asn);
            check_and_delete_bgp_neighbors(pbgp, ovs_bgp, idl);
            check_and_delete_bgp_neighbor_peer_groups(pbgp, ovs_bgp, idl);
        }
    }
}

/*
 * vrf_name CAN be NULL but ipaddr should NOT be passed as NULL
 */
static const struct ovsrec_bgp_neighbor *
get_bgp_neighbor_with_VrfName_BgpRouterAsn_Ipaddr (struct ovsdb_idl *idl,
    char *vrf_name,
    int asn,
    const char *ipaddr)
{
    int i, j;
    const struct ovsrec_vrf *ovs_vrf;
    const struct ovsrec_bgp_router *ovs_bgp;

    if (NULL == vrf_name) {
	vrf_name = DEFAULT_VRF_NAME;
    }

    OVSREC_VRF_FOR_EACH(ovs_vrf, idl) {
        if (strcmp(ovs_vrf->name, vrf_name)) {
            continue;
        }
        for (i = 0; i < ovs_vrf->n_bgp_routers; i++) {
            if (asn != ovs_vrf->key_bgp_routers[i]) {
                continue;
            }
            ovs_bgp = ovs_vrf->value_bgp_routers[i];
            for (j = 0; j < ovs_bgp->n_bgp_neighbors; j++) {
                if (0 == strcmp(ipaddr, ovs_bgp->key_bgp_neighbors[j])) {
                    return ovs_bgp->value_bgp_neighbors[j];
                }
            }
        }
    }
    return NULL;
}

const struct ovsrec_bgp_neighbor *
get_bgp_neighbor_db_row (struct peer *peer)
{
    const char *ipaddr;
    char ip_addr_string [64];

    ipaddr = sockunion2str(&peer->su, ip_addr_string, 63);
    if (ipaddr) {
        return
            get_bgp_neighbor_with_VrfName_BgpRouterAsn_Ipaddr(idl, NULL,
                peer->bgp->as, ipaddr);
    }
    return NULL;
}

void
bgp_daemon_ovsdb_neighbor_statistics_update (bool start_new_db_txn,
    const struct ovsrec_bgp_neighbor *ovs_bgp_neighbor_ptr,
    struct peer *peer)
{

#define MAX_BGP_NEIGHBOR_STATS		64

    struct ovsdb_idl_txn *db_txn;
    char *keywords[MAX_BGP_NEIGHBOR_STATS];
    int64_t values [MAX_BGP_NEIGHBOR_STATS];
    int count;

#define ADD_BGPN_STAT(key, value) \
    keywords[count] = key; \
    values[count] = value; \
    count++

    /* if row is not given, find it */
    if (NULL == ovs_bgp_neighbor_ptr) {
	ovs_bgp_neighbor_ptr = get_bgp_neighbor_db_row(peer);

	/* it is possible to come here with no db entry, this is ok */
	if (NULL == ovs_bgp_neighbor_ptr) return;
    }

    /* is this an independent txn or piggybacked onto another txn */
    if (start_new_db_txn) {
	db_txn = ovsdb_idl_txn_create(idl);
	if (NULL == db_txn) {
	    VLOG_ERR("%%ovsdb_idl_txn_create failed in "
		"bgp_daemon_ovsdb_neighbor_statistics_update\n");
	    return;
	}
    }

    count = 0;

    ADD_BGPN_STAT(BGP_PEER_ESTABLISHED_COUNT,  peer->established);
    ADD_BGPN_STAT(BGP_PEER_DROPPED_COUNT,  peer->dropped);
    ADD_BGPN_STAT(BGP_PEER_OPEN_IN_COUNT,  peer->open_in);
    ADD_BGPN_STAT(BGP_PEER_OPEN_OUT_COUNT, peer->open_out);
    ADD_BGPN_STAT(BGP_PEER_UPDATE_IN_COUNT, peer->update_in);
    ADD_BGPN_STAT(BGP_PEER_UPDATE_OUT_COUNT, peer->update_out);
    ADD_BGPN_STAT(BGP_PEER_KEEPALIVE_IN_COUNT, peer->keepalive_in);
    ADD_BGPN_STAT(BGP_PEER_KEEPALIVE_OUT_COUNT, peer->keepalive_out);
    ADD_BGPN_STAT(BGP_PEER_NOTIFY_IN_COUNT, peer->notify_in);
    ADD_BGPN_STAT(BGP_PEER_NOTIFY_OUT_COUNT, peer->notify_out);
    ADD_BGPN_STAT(BGP_PEER_REFRESH_IN_COUNT, peer->refresh_in);
    ADD_BGPN_STAT(BGP_PEER_REFRESH_OUT_COUNT, peer->refresh_out);
    ADD_BGPN_STAT(BGP_PEER_DYNAMIC_CAP_IN_COUNT, peer->dynamic_cap_in);
    ADD_BGPN_STAT(BGP_PEER_DYNAMIC_CAP_OUT_COUNT, peer->dynamic_cap_out);

    ADD_BGPN_STAT(BGP_PEER_UPTIME, peer->uptime);
    ADD_BGPN_STAT(BGP_PEER_READTIME, peer->readtime);
    ADD_BGPN_STAT(BGP_PEER_RESETTIME, peer->resettime);

    ovsrec_bgp_neighbor_set_statistics(ovs_bgp_neighbor_ptr,
	keywords, values, count);

    if (start_new_db_txn) {
	ovsdb_idl_txn_commit_block(db_txn);
	ovsdb_idl_txn_destroy(db_txn);
    }
}

/*
 * update a bunch of BGP_Neighbor related info
 * in the ovs database, from the daemon side
 */
void bgp_daemon_ovsdb_neighbor_update (struct peer *peer,
    bool update_stats_too)
{
    const struct ovsrec_bgp_neighbor *ovs_bgp_neighbor_ptr;
    struct ovsdb_idl_txn *db_txn;
    enum ovsdb_idl_txn_status status;
    struct smap smap;

    ovs_bgp_neighbor_ptr = get_bgp_neighbor_db_row(peer);
    if (NULL == ovs_bgp_neighbor_ptr) {
        VLOG_DBG("bgp_daemon_ovsdb_neighbor_update cannot find db row or "
                 "returned neighbor was a peer-group");
        return;
    }

    VLOG_DBG("updating bgp neighbor %s remote-as %d in db\n",
           ovsdb_nbr_from_row_to_peer_name(idl, ovs_bgp_neighbor_ptr, NULL),
           *ovs_bgp_neighbor_ptr->remote_as);

    db_txn = ovsdb_idl_txn_create(idl);
    if (NULL == db_txn) {
	VLOG_ERR("%%ovsdb_idl_txn_create failed in "
	    "bgp_daemon_ovsdb_neighbor_update\n");
	return;
    }

    /* update fields of this peer/neighbor in the ovsdb */

    if (peer->group) {
	/* TO DO LATER */
    }

    VLOG_DBG("updating port to %d\n", peer->port);
    ovsrec_bgp_neighbor_set_tcp_port_number(ovs_bgp_neighbor_ptr,
        (int64_t*) &peer->port, 1);

    /*
     * OPS_TODO
    VLOG_DBG("updating local_as to %d\n", peer->local_as);
    This causes the entire transaction to be rejected, investigate later
    ovsrec_bgp_neighbor_set_local_as(ovs_bgp_neighbor_ptr,
        &peer->local_as, 1);
     */

    VLOG_DBG("updating weight to %d\n", peer->weight);
    ovsrec_bgp_neighbor_set_weight(ovs_bgp_neighbor_ptr,
        (int64_t*) &peer->weight, 1);

    smap_init(&smap);
    smap_add(&smap, BGP_PEER_STATE, bgp_peer_status_to_string(peer->status));
    VLOG_DBG("updating bgp neighbor status to %s\n",
	bgp_peer_status_to_string(peer->status));
    ovsrec_bgp_neighbor_set_status(ovs_bgp_neighbor_ptr, &smap);

    /* update statistics */
    if (update_stats_too) {
	bgp_daemon_ovsdb_neighbor_statistics_update(false,
	    ovs_bgp_neighbor_ptr, peer);
	VLOG_DBG("updated stats also\n");
    }

    status = ovsdb_idl_txn_commit_block(db_txn);
    ovsdb_idl_txn_destroy(db_txn);
    VLOG_DBG("txn result: %s\n", ovsdb_idl_txn_status_to_string(status));
}

static int
fetch_key_value (char **key, const int64_t *value,
    size_t n_elem, char *your_key)
{
    int i;

    for (i = 0; i < n_elem; i++) {
        if (strcmp(key[i], your_key) == 0) {
            return value[i];
        }
    }
    return -1;
}

static void
bgp_nbr_remote_as_ovsdb_apply_changes (const struct ovsrec_bgp_neighbor *ovs_nbr,
    char * name,
    struct bgp *bgp_instance)

{
    /* remote-as */
    if (COL_CHANGED(ovs_nbr, ovsrec_bgp_neighbor_col_remote_as, idl_seqno)) {
        VLOG_DBG("Setting remote-as %lld", *ovs_nbr->remote_as);
        daemon_neighbor_remote_as_cmd_execute(bgp_instance,
            name, ovs_nbr->remote_as, AFI_IP, SAFI_UNICAST);
    }
}

static void
bgp_nbr_peer_group_ovsdb_apply_changes (const struct ovsrec_bgp_neighbor *ovs_nbr,
    const struct ovsrec_bgp_router *ovs_bgp,
    char * name,
    struct bgp *bgp_instance)
{
    int j;

    /* peer group */
    if (COL_CHANGED(ovs_nbr, ovsrec_bgp_neighbor_col_bgp_peer_group, idl_seqno)) {
        VLOG_DBG("Setting for peer: %s", name);
        const struct ovsrec_bgp_neighbor *peer_group = ovs_nbr->bgp_peer_group;

        for (j = 0; j < ovs_bgp->n_bgp_neighbors; j++) {
            if (ovs_bgp->value_bgp_neighbors[j] == peer_group) {
                break;
            }
        }

        if (peer_group) {
            VLOG_DBG("Binding to peergroup: %s", ovs_bgp->key_bgp_neighbors[j]);
            daemon_neighbor_set_peer_group_cmd_execute(bgp_instance,
                name, ovs_bgp->key_bgp_neighbors[j], AFI_IP, SAFI_UNICAST);
        } else {
            VLOG_DBG("Unbinding peer from peergroup");
            daemon_no_neighbor_set_peer_group_cmd_execute(bgp_instance,
                name, AFI_IP, SAFI_UNICAST);
        }
    }
}

static void
bgp_nbr_description_ovsdb_apply_changes (const struct ovsrec_bgp_neighbor *ovs_nbr,
    const struct ovsrec_bgp_router *ovs_bgp,
    char * name,
    struct bgp *bgp_instance)
{
    if (COL_CHANGED(ovs_nbr, ovsrec_bgp_neighbor_col_description, idl_seqno)) {
        daemon_neighbor_description_cmd_execute(bgp_instance,
            name, ovs_nbr->description);
    }
}

static void
bgp_nbr_password_ovsdb_apply_changes (const struct ovsrec_bgp_neighbor *ovs_nbr,
    const struct ovsrec_bgp_router *ovs_bgp,
    char * name,
    struct bgp *bgp_instance)
{
    if (COL_CHANGED(ovs_nbr, ovsrec_bgp_neighbor_col_password, idl_seqno)) {
        daemon_neighbor_password_cmd_execute(bgp_instance,
            name, ovs_nbr->password);
    }
}

static void
bgp_nbr_advertisement_interval_ovsdb_apply_changes (const struct ovsrec_bgp_neighbor *ovs_nbr,
    const struct ovsrec_bgp_router *ovs_bgp,
    char * name,
    struct bgp *bgp_instance)
{
    if (COL_CHANGED(ovs_nbr, ovsrec_bgp_neighbor_col_advertisement_interval, idl_seqno)) {
        daemon_neighbor_advertisement_interval_cmd_execute(bgp_instance,
            name, ovs_nbr->advertisement_interval);
    }
}

static void
bgp_nbr_shutdown_ovsdb_apply_changes (const struct ovsrec_bgp_neighbor *ovs_nbr,
    const struct ovsrec_bgp_router *ovs_bgp,
    char * name,
    struct bgp *bgp_instance)
{
    if (COL_CHANGED(ovs_nbr, ovsrec_bgp_neighbor_col_shutdown, idl_seqno)) {
        bool shut = ovs_nbr->n_shutdown && ovs_nbr->shutdown[0];
        daemon_neighbor_shutdown_cmd_execute(bgp_instance, name, shut);
    }
}

static void
bgp_nbr_inbound_soft_reconfig_ovsdb_apply_changes
    (const struct ovsrec_bgp_neighbor *ovs_nbr,
     const struct ovsrec_bgp_router *ovs_bgp,
     char * name,
     struct bgp *bgp_instance)
{
    if (COL_CHANGED(ovs_nbr, ovsrec_bgp_neighbor_col_inbound_soft_reconfiguration,
        idl_seqno)) {
            bool enable =
                ovs_nbr->n_inbound_soft_reconfiguration &&
                ovs_nbr->inbound_soft_reconfiguration[0];
            daemon_neighbor_inbound_soft_reconfiguration_cmd_execute
                (bgp_instance, name, AFI_IP, SAFI_UNICAST, enable);
    }
}

static void
bgp_nbr_route_map_ovsdb_apply_changes (const struct ovsrec_bgp_neighbor *ovs_nbr,
    const struct ovsrec_bgp_router *ovs_bgp,
    char * name,
    struct bgp *bgp_instance)
{
    if (COL_CHANGED(ovs_nbr, ovsrec_bgp_neighbor_col_route_maps, idl_seqno)) {
        apply_bgp_neighbor_route_map_changes(ovs_nbr, bgp_instance);
    }
}


static void
bgp_nbr_prefix_list_ovsdb_apply_changes (const struct ovsrec_bgp_neighbor *ovs_nbr,
    const struct ovsrec_bgp_router *ovs_bgp,
    char * name,
    struct bgp *bgp_instance)
{
    if (COL_CHANGED(ovs_nbr, ovsrec_bgp_neighbor_col_prefix_lists, idl_seqno)) {
        apply_bgp_neighbor_prefix_list_changes(ovs_nbr, bgp_instance);
    }
}

static void
bgp_nbr_aspath_filter_ovsdb_apply_changes (const struct ovsrec_bgp_neighbor *ovs_nbr,
                                           const struct ovsrec_bgp_router *ovs_bgp,
                                           char * name,
                                           struct bgp *bgp_instance)
{
    if (COL_CHANGED(ovs_nbr, ovsrec_bgp_neighbor_col_aspath_filters, idl_seqno)) {
        apply_bgp_neighbor_aspath_filter_changes(ovs_nbr, bgp_instance);
    }
}

static void
bgp_nbr_timers_ovsdb_apply_changes(const struct ovsrec_bgp_neighbor *ovs_nbr,
                                   const struct ovsrec_bgp_router *ovs_bgp,
                                   char * name,
                                   struct bgp *bgp_instance)
{
    int keepalive = 0;
    int holdtimer = 0;
    bool set = true;

    if (COL_CHANGED(ovs_nbr, ovsrec_bgp_neighbor_col_timers, idl_seqno)) {
        if (ovs_nbr->n_timers) {
            keepalive = fetch_key_value(ovs_nbr->key_timers,
                                        ovs_nbr->value_timers,
                                        ovs_nbr->n_timers,
                                        OVSDB_BGP_TIMER_KEEPALIVE);
            holdtimer = fetch_key_value(ovs_nbr->key_timers,
                                        ovs_nbr->value_timers,
                                        ovs_nbr->n_timers,
                                        OVSDB_BGP_TIMER_HOLDTIME);
        } else {
            VLOG_DBG("Unsetting neighbor timers");
            set = false;
        }

        /* When !set, change is considered as unsetting. Keepalive and hold
         * timer values are not required/used in unsetting case. Only in
         * set case do we check for valid keepalive and hold timer values.
         */
        if (!set || ((keepalive > 0) && (holdtimer > 0))) {
            daemon_neighbor_timers_cmd_execute(bgp_instance, name,
                                               (u_int32_t)keepalive,
                                               (u_int32_t)holdtimer, set);
        } else {
            VLOG_ERR("Invalid neighbor keepalive/holdtimer");
        }
    }
}

static void
bgp_nbr_allow_as_in_ovsdb_apply_changes (const struct ovsrec_bgp_neighbor *ovs_nbr,
    const struct ovsrec_bgp_router *ovs_bgp,
    char * name,
    struct bgp *bgp_instance)
{
    if (COL_CHANGED(ovs_nbr, ovsrec_bgp_neighbor_col_allow_as_in, idl_seqno)) {
        daemon_neighbor_allow_as_in_cmd_execute(bgp_instance,
            name, AFI_IP, SAFI_UNICAST, ovs_nbr->allow_as_in);
    }
}

static void
bgp_nbr_remove_private_as_ovsdb_apply_changes(
    const struct ovsrec_bgp_neighbor *ovs_nbr,
    const struct ovsrec_bgp_router *ovs_bgp,
    char *name,
    struct bgp *bgp_instance)
{
    if (COL_CHANGED(ovs_nbr, ovsrec_bgp_neighbor_col_remove_private_as,
                    idl_seqno)) {
        bool doit = (ovs_nbr->n_remove_private_as &&
                     ovs_nbr->remove_private_as[0]);
        daemon_neighbor_remove_private_as_cmd_execute(bgp_instance,
                                                      name, AFI_IP,
                                                      SAFI_UNICAST, doit);
    }
}

static void
bgp_nbr_ebgp_multihop_ovsdb_apply_changes (const struct ovsrec_bgp_neighbor *ovs_nbr,
    const struct ovsrec_bgp_router *ovs_bgp,
    char * name,
    struct bgp *bgp_instance)

{
    /* ebgp-multihop */
    if (COL_CHANGED(ovs_nbr, ovsrec_bgp_neighbor_col_ebgp_multihop, idl_seqno)) {
        bool ebgp = ovs_nbr->n_ebgp_multihop && ovs_nbr->ebgp_multihop[0];
        daemon_neighbor_ebgp_multihop_cmd_execute(bgp_instance,
            name, ebgp);
    }
}

static void
bgp_nbr_ttl_security_hops_ovsdb_apply_changes (const struct ovsrec_bgp_neighbor *ovs_nbr,
    const struct ovsrec_bgp_router *ovs_bgp,
    char * name,
    struct bgp *bgp_instance)
{
    if (COL_CHANGED(ovs_nbr, ovsrec_bgp_neighbor_col_ttl_security_hops, idl_seqno)) {
        daemon_neighbor_ttl_security_hops_cmd_execute(bgp_instance,
            name, ovs_nbr->ttl_security_hops);
    }
}

static void
bgp_nbr_update_source_ovsdb_apply_changes (const struct ovsrec_bgp_neighbor *ovs_nbr,
    const struct ovsrec_bgp_router *ovs_bgp,
    char * name,
    struct bgp *bgp_instance)
{
    if (COL_CHANGED(ovs_nbr, ovsrec_bgp_neighbor_col_update_source, idl_seqno)) {
        daemon_neighbor_update_source_cmd_execute(bgp_instance,
            name, ovs_nbr->update_source);
    }
}

/*
 * Do bgp nbr changes according to ovsdb changes
 */
static void
bgp_nbr_read_ovsdb_apply_changes (struct ovsdb_idl *idl)
{
    const struct ovsrec_vrf *ovs_vrf = NULL;
    const struct ovsrec_bgp_router *ovs_bgp;
    const struct ovsrec_bgp_neighbor *ovs_nbr;
    struct smap_node *node;
    int asn;
    char peer[80];
    int i, j;
    struct bgp *bgp_instance;

    OVSREC_VRF_FOR_EACH(ovs_vrf, idl) {
      for (i = 0; i < ovs_vrf->n_bgp_routers; i++) {
        asn = ovs_vrf->key_bgp_routers[i];
        ovs_bgp = ovs_vrf->value_bgp_routers[i];

        bgp_instance = bgp_lookup(asn, NULL);
        if (!bgp_instance) {
            VLOG_ERR("%%cannot find daemon bgp router instance %d\n", asn);
            continue;
        }
        for (j = 0; j < ovs_bgp->n_bgp_neighbors; j++) {
            ovs_nbr = ovs_bgp->value_bgp_neighbors[j];
            if (!OVSREC_IDL_IS_ROW_INSERTED(ovs_nbr, idl_seqno) &&
                !OVSREC_IDL_IS_ROW_MODIFIED(ovs_nbr, idl_seqno)) {
                    continue;
            }

            /* If this is a new row, call the appropriate
             * daemon function depending on whether the
             * created object is a bgp peer or a bgp peer
             * group and if remote-as has been specified.
             */
            if (NEW_ROW(ovs_nbr, idl_seqno)) {
                /* Creating a peer requires that the AS be set. Only permit
                 * creating a peer if the AS is valid; otherwise, if it's
                 * a peer-group, then proceed with invoking the peer-group
                 * creation function. Once created, subsequent checks
                 * will occur for setting the AS if, in the same OVSDB
                 * transaction, the remote-as was also set.
                 */
                if (object_is_peer(ovs_nbr)) {
                    if (ovs_nbr->n_remote_as) {
                        VLOG_DBG("Creating a peer with remote-as %d",
                                 *ovs_nbr->remote_as);
                        daemon_neighbor_remote_as_cmd_execute(bgp_instance,
                            ovs_bgp->key_bgp_neighbors[j], ovs_nbr->remote_as,
                            AFI_IP, SAFI_UNICAST);
                    } else {
                        VLOG_ERR("Invalid remote-as for peer creation.");
                    }
                } else {
                    VLOG_DBG("Creating a peer-group");
                    daemon_neighbor_peer_group_cmd_execute(bgp_instance,
                        ovs_bgp->key_bgp_neighbors[j]);
                }
            }

	    /* remote-as */
            bgp_nbr_remote_as_ovsdb_apply_changes(ovs_nbr,
                ovs_bgp->key_bgp_neighbors[j], bgp_instance);

            /* peer group */
            bgp_nbr_peer_group_ovsdb_apply_changes(ovs_nbr, ovs_bgp,
                ovs_bgp->key_bgp_neighbors[j], bgp_instance);

	    /* description */
            bgp_nbr_description_ovsdb_apply_changes(ovs_nbr, ovs_bgp,
                ovs_bgp->key_bgp_neighbors[j], bgp_instance);

	    /* passwd */
            bgp_nbr_password_ovsdb_apply_changes(ovs_nbr, ovs_bgp,
                ovs_bgp->key_bgp_neighbors[j], bgp_instance);

            /* shutdown */
            bgp_nbr_shutdown_ovsdb_apply_changes(ovs_nbr, ovs_bgp,
                ovs_bgp->key_bgp_neighbors[j], bgp_instance);

	    /* inbound_soft_reconfiguration */
            bgp_nbr_inbound_soft_reconfig_ovsdb_apply_changes(ovs_nbr, ovs_bgp,
                ovs_bgp->key_bgp_neighbors[j], bgp_instance);

	    /* route map */
            bgp_nbr_route_map_ovsdb_apply_changes(ovs_nbr, ovs_bgp,
                ovs_bgp->key_bgp_neighbors[j], bgp_instance);

        /* prefix list */
            bgp_nbr_prefix_list_ovsdb_apply_changes(ovs_nbr, ovs_bgp,
                ovs_bgp->key_bgp_neighbors[j], bgp_instance);

        /* filter list */
            bgp_nbr_aspath_filter_ovsdb_apply_changes(ovs_nbr, ovs_bgp,
                ovs_bgp->key_bgp_neighbors[j], bgp_instance);

	    /* timers */
            bgp_nbr_timers_ovsdb_apply_changes(ovs_nbr, ovs_bgp,
                ovs_bgp->key_bgp_neighbors[j], bgp_instance);

	    /* allow_as_in */
            bgp_nbr_allow_as_in_ovsdb_apply_changes(ovs_nbr, ovs_bgp,
                ovs_bgp->key_bgp_neighbors[j], bgp_instance);

            /* remove_private_as */
            bgp_nbr_remove_private_as_ovsdb_apply_changes(ovs_nbr, ovs_bgp,
                ovs_bgp->key_bgp_neighbors[j], bgp_instance);

            /* advertisement_interval */
            bgp_nbr_advertisement_interval_ovsdb_apply_changes(ovs_nbr, ovs_bgp,
                ovs_bgp->key_bgp_neighbors[j], bgp_instance);

	    /* ebgp_multihop */
            bgp_nbr_ebgp_multihop_ovsdb_apply_changes(ovs_nbr, ovs_bgp,
                ovs_bgp->key_bgp_neighbors[j], bgp_instance);

	    /* ttl_security_hops */
            bgp_nbr_ttl_security_hops_ovsdb_apply_changes(ovs_nbr, ovs_bgp,
                ovs_bgp->key_bgp_neighbors[j], bgp_instance);

	    /* update_source */
            bgp_nbr_update_source_ovsdb_apply_changes(ovs_nbr, ovs_bgp,
                ovs_bgp->key_bgp_neighbors[j], bgp_instance);

         }
      }
   }
}

/*
 * Process potential changes in the BGP_Neighbor table
 */
static void
bgp_apply_bgp_neighbor_changes (struct ovsdb_idl *idl)
{
    const struct ovsrec_bgp_bgp *ovs_bgp;
    const struct ovsrec_bgp_neighbor *ovs_nbr;
    struct bgp *bgp_instance;
    bool inserted = false;
    bool modified = false;
    bool deleted = false;
    u_int32_t keepalive;
    u_int32_t holdtimer;

    ovs_nbr = ovsrec_bgp_neighbor_first(idl);

    /*
     * if there are no bgp neighbor/peer-groups, there
     * are two possibilities: either nothing has been
     * created or everything has been deleted.  We have
     * to assume everything may have been deleted and
     * process accordingly.  If we assume that, obviously
     * it follows that modified or inserted can NOT be true.
     */
    if (!ovs_nbr) {
	deleted = true;
    } else {
	if (ANY_ROW_DELETED(ovs_nbr, idl_seqno)) {
	    deleted = true;
	}
	if (ANY_NEW_ROW(ovs_nbr, idl_seqno)) {
	    inserted = true;
	}
	if (ANY_ROW_CHANGED(ovs_nbr, idl_seqno)) {
	    modified = true;
	}
    }

    /* deletions are handled differently, do them first */
    if (deleted) {
        VLOG_DBG("Checking for any bgp neighbor/peer-group deletions\n");
        delete_bgp_neighbors_and_peer_groups(idl);
    }

    /* nothing else changed ? */
    if (!modified && !inserted) {
	VLOG_DBG("no other changes occured in BGP Neighbor table\n");
	return;
    }

    VLOG_DBG("now processing bgp neighbor modifications\n");
    bgp_nbr_read_ovsdb_apply_changes(idl);
}

static void
bgp_reconfigure (struct ovsdb_idl *idl)
{
    unsigned int new_idl_seqno = ovsdb_idl_get_seqno(idl);
    COVERAGE_INC(bgp_ovsdb_cnt);

    if (new_idl_seqno == idl_seqno){
        VLOG_DBG("No config change for bgp in ovs\n");
        return;
    }

    /*
     * Apply prefix list, community filter and route map changes
     */
    policy_prefix_list_read_ovsdb_apply_changes(idl);
    policy_community_filter_read_ovsdb_apply_changes(idl);
    policy_rt_map_read_ovsdb_apply_changes(idl);
    policy_aspath_filter_read_ovsdb_apply_changes(idl);

    /* Apply the changes */
    bgp_apply_global_changes();
    bgp_apply_bgp_router_changes(idl);
    bgp_apply_bgp_neighbor_changes(idl);

    /* Scan active route transaction list and handle completions */
    bgp_txn_complete_processing();

    /* update the seq. number */
    idl_seqno = new_idl_seqno;
}

/* Wrapper function that checks for idl updates and reconfigures the daemon
 */
static void
bgp_ovs_run ()
{
    ovsdb_idl_run(idl);
    unixctl_server_run(appctl);

    if (ovsdb_idl_is_lock_contended(idl)) {
        static struct vlog_rate_limit rl = VLOG_RATE_LIMIT_INIT(1, 1);

        VLOG_ERR_RL(&rl, "another bgpd process is running, "
                    "disabling this process until it goes away");
        return;
    } else if (!ovsdb_idl_has_lock(idl)) {
        return;
    }

    bgp_chk_for_system_configured();
    if (system_configured) {
        bgp_reconfigure(idl);
        daemonize_complete();
        vlog_enable_async();
        VLOG_INFO_ONCE("%s (OpenSwitch bgpd) %s", program_name, VERSION);
    }
}

static void
bgp_ovs_wait (void)
{
    ovsdb_idl_wait(idl);
    unixctl_server_wait(appctl);
}

/* Callback function to handle read events
 * In the event of an update to the idl cache, this callback is triggered.
 * In this event, the changes are processed in the daemon and the cb
 * functions are re-registered.
 */
static int
bovs_read_cb (struct thread *thread)
{
    bgp_ovsdb_t *bovs_g;
    if (!thread) {
        VLOG_ERR("NULL thread in read cb function\n");
        return -1;
    }
    bovs_g = THREAD_ARG(thread);
    if (!bovs_g) {
        VLOG_ERR("NULL args in read cb function\n");
        return -1;
    }

    bovs_g->read_cb_count++;

    bgp_ovs_clear_fds();
    bgp_ovs_run();
    bgp_ovs_wait();

    if (0 != bgp_ovspoll_enqueue(bovs_g)) {
        /* Could not enqueue the events. Retry in 1 sec */
        thread_add_timer(bovs_g->master, bovs_read_cb, bovs_g, 1);
    }
    return 1;
}

/*
 * Add the list of OVS poll fd to the master thread of the daemon
 */
static int
bgp_ovspoll_enqueue (bgp_ovsdb_t *bovs_g)
{
    struct poll_loop *loop = poll_loop();
    struct poll_node *node;
    long int timeout;
    int retval = -1;

    /* Populate with all the fds events. */
    HMAP_FOR_EACH(node, hmap_node, &loop->poll_nodes) {
        thread_add_read(bovs_g->master, bovs_read_cb, bovs_g, node->pollfd.fd);
        /*
         * If we successfully connected to OVS return 0.
         * Else return -1 so that we try to reconnect.
         */
        retval = 0;
    }

    /* Populate the timeout event */
    timeout = loop->timeout_when - time_msec();
    if (timeout > 0 && loop->timeout_when > 0 &&
       loop->timeout_when < LLONG_MAX) {
        /* Convert msec to sec */
        timeout = (timeout + 999)/1000;
        thread_add_timer(bovs_g->master, bovs_read_cb, bovs_g, timeout);
    }

    return retval;
}

/* Initialize and integrate the ovs poll loop with the daemon */
void bgp_ovsdb_init_poll_loop (struct bgp_master *bm)
{
    if (!glob_bgp_ovs.enabled) {
        VLOG_ERR("OVS not enabled for bgp. Return\n");
        return;
    }
    glob_bgp_ovs.master = bm->master;

    bgp_ovs_clear_fds();
    bgp_ovs_run();
    bgp_ovs_wait();
    bgp_ovspoll_enqueue(&glob_bgp_ovs);
}

static void
ovsdb_exit (void)
{
    ovsdb_idl_destroy(idl);
}

/* When the daemon is ready to shut, delete the idl cache
 * This happens with the ovs-appctl exit command.
 */
void bgp_ovsdb_exit (void)
{
    ovsdb_exit();
}
