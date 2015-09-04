/* bgp daemon ovsdb integration.
 *
 * Hewlett-Packard Company Confidential (C) Copyright 2015 Hewlett-Packard Development Company, L.P.
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
#include "openhalon-idl.h"
#include "prefix.h"

#include "bgpd/bgp_ovsdb_if.h"
#include "bgpd/bgp_table.h"
#include "bgpd/bgp_route.h"
#include "linklist.h"

/* Local structure to hold the master thread
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

boolean exiting = false;
static int bgp_ovspoll_enqueue (bgp_ovsdb_t *bovs_g);
static int bovs_read_cb (struct thread *thread);

/* ovs appctl dump function for this daemon
 * This is useful for debugging
 */
static void
bgp_unixctl_dump(struct unixctl_conn *conn, int argc OVS_UNUSED,
                          const char *argv[] OVS_UNUSED, void *aux OVS_UNUSED)
{
    //unixctl_command_reply_error(conn, "Nothing to dump :)");
#if 0
    #define BUF_LEN 4000
    #define REM_BUF_LEN (BUF_LEN - 1 - strlen(buf))
    struct shash_node *sh_node;
    char *buf = xcalloc(1, BUF_LEN);

    static struct shash bgp_all = SHASH_INITIALIZER(&bgp_all);

    SHASH_FOR_EACH(sh_node, &bgp_all) {
        struct bgp *bgp = sh_node->data;
        strncat(buf,"asn\t",REM_BUF_LEN);
        strncat(buf,bgp->as,REM_BUF_LEN);
        strncat(buf, "\n", REM_BUF_LEN);
    }
    unixctl_command_reply(conn, buf);
    free(buf);
#endif
}


static void
bgp_policy_ovsdb_init(struct ovsdb_idl *idl)
{
    ovsdb_idl_add_table(idl, &ovsrec_table_prefix_list);
    ovsdb_idl_add_column(idl, &ovsrec_prefix_list_col_name);
    ovsdb_idl_add_column(idl, &ovsrec_prefix_list_col_description);

    ovsdb_idl_add_table(idl, &ovsrec_table_prefix_list_entries);
    ovsdb_idl_add_column(idl, &ovsrec_prefix_list_entries_col_action);
    ovsdb_idl_add_column(idl, &ovsrec_prefix_list_entries_col_prefix);
    ovsdb_idl_add_column(idl, &ovsrec_prefix_list_entries_col_prefix_list);
    ovsdb_idl_add_column(idl, &ovsrec_prefix_list_entries_col_sequence);


    ovsdb_idl_add_table(idl, &ovsrec_table_route_map);
    ovsdb_idl_add_column(idl, &ovsrec_route_map_col_name);

    ovsdb_idl_add_table(idl, &ovsrec_table_route_map_entries);
    ovsdb_idl_add_column(idl, &ovsrec_route_map_entries_col_action);
    ovsdb_idl_add_column(idl, &ovsrec_route_map_entries_col_description);
    ovsdb_idl_add_column(idl, &ovsrec_route_map_entries_col_match);
    ovsdb_idl_add_column(idl, &ovsrec_route_map_entries_col_preference);
    ovsdb_idl_add_column(idl, &ovsrec_route_map_entries_col_route_map);
    ovsdb_idl_add_column(idl, &ovsrec_route_map_entries_col_set);
}


static void
bgp_ovsdb_tables_init (struct ovsdb_idl *idl)
{
    /* VRF Table */
    ovsdb_idl_add_table(idl, &ovsrec_table_vrf);
    ovsdb_idl_add_column(idl, &ovsrec_vrf_col_name);

    /* BGP router table */
    ovsdb_idl_add_table(idl, &ovsrec_table_bgp_router);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_asn);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_router_id);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_networks);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_vrf);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_maximum_paths);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_timers);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_redistribute);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_gr_stale_timer);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_always_compare_med);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_other_config);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_status);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_external_ids);

    /* BGP neighbor table */
    ovsdb_idl_add_table(idl, &ovsrec_table_bgp_neighbor);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_weight);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_is_peer_group);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_bgp_peer_group);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_bgp_router);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_strict_capability_match);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_tcp_port_number);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_inbound_soft_reconfiguration);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_statistics);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_remote_as);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_remove_private_as);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_shutdown);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_override_capability);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_passive);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_maximum_prefix_limit);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_name);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_status);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_description);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_local_as);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_advertisement_interval);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_local_interface);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_external_ids);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_password);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_other_config);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_capability);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_timers);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_route_maps);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_allow_as_in);

    /* BGP policy */
    bgp_policy_ovsdb_init(idl);

    /* RIB table */
    ovsdb_idl_add_table(idl, &ovsrec_table_route);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_prefix);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_from);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_nexthops);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_address_family);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_sub_address_family);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_protocol_specific);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_selected);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_protocol_private);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_distance);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_metric);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_vrf);

    /* nexthop table */
    ovsdb_idl_add_table(idl, &ovsrec_table_nexthop);
    ovsdb_idl_add_column(idl, &ovsrec_nexthop_col_ip_address);
    ovsdb_idl_add_column(idl, &ovsrec_nexthop_col_selected);
    ovsdb_idl_add_column(idl, &ovsrec_nexthop_col_weight);
    ovsdb_idl_add_column(idl, &ovsrec_nexthop_col_status);
    ovsdb_idl_add_column(idl, &ovsrec_nexthop_col_other_config);
    ovsdb_idl_add_column(idl, &ovsrec_nexthop_col_external_ids);
}

/* Create a connection to the OVSDB at db_path and create a dB cache
 * for this daemon. */
static void
ovsdb_init (const char *db_path)
{
    /* Initialize IDL through a new connection to the dB. */
    idl = ovsdb_idl_create(db_path, &ovsrec_idl_class, false, true);
    idl_seqno = ovsdb_idl_get_seqno(idl);
    ovsdb_idl_set_lock(idl, "halon_bgp");
    //ovsdb_idl_verify_write_only(idl);

    /* Cache OpenVSwitch table */
    ovsdb_idl_add_table(idl, &ovsrec_table_open_vswitch);

    ovsdb_idl_add_column(idl, &ovsrec_open_vswitch_col_cur_cfg);
    ovsdb_idl_add_column(idl, &ovsrec_open_vswitch_col_hostname);

    /* BGP tables */
    bgp_ovsdb_tables_init(idl);

    /* Register ovs-appctl commands for this daemon. */
    unixctl_command_register("bgpd/dump", "", 0, 0, bgp_unixctl_dump, NULL);
}

static void
halon_bgp_exit(struct unixctl_conn *conn, int argc OVS_UNUSED,
                  const char *argv[] OVS_UNUSED, void *exiting_)
{
    boolean *exiting = exiting_;
    *exiting = true;
    unixctl_command_reply(conn, NULL);
}

static void
usage(void)
{
    printf("%s: Halon bgp daemon\n"
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

/* HALON_TODO: Need to merge this parse function with the main parse function
 * in bgp_main to avoid issues.
 */
static char *
bgp_ovsdb_parse_options(int argc, char *argv[], char **unixctl_pathp)
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

/* Setup bgp to connect with ovsdb and daemonize. This daemonize is used
 * over the daemonize in the main function to keep the behavior consistent
 * with the other daemons in the HALON system
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
    /* Fork and return in child process; but don't notify parent of
     * startup completion yet. */
    daemonize_start();

    /* Create UDS connection for ovs-appctl. */
    retval = unixctl_server_create(appctl_path, &appctl);
    if (retval) {
       exit(EXIT_FAILURE);
    }

    /* Register the ovs-appctl "exit" command for this daemon. */
    unixctl_command_register("exit", "", 0, 0, halon_bgp_exit, &exiting);

   /* Create the IDL cache of the dB at ovsdb_sock. */
   ovsdb_init(ovsdb_sock);
   free(ovsdb_sock);

   /* Notify parent of startup completion. */
   daemonize_complete();

   /* Enable asynch log writes to disk. */
   vlog_enable_async();

   VLOG_INFO_ONCE("%s (Halon Bgpd Daemon) started", program_name);

   glob_bgp_ovs.enabled = 1;
   return;
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
    const struct ovsrec_open_vswitch *ovs_vsw = NULL;

    if (system_configured) {
        /* Nothing to do if we're already configured. */
        return;
    }

    ovs_vsw = ovsrec_open_vswitch_first(idl);

    if (ovs_vsw && (ovs_vsw->cur_cfg > (int64_t) 0)) {
        system_configured = true;
        VLOG_INFO("System is now configured (cur_cfg=%d).",
                 (int)ovs_vsw->cur_cfg);
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
modify_bgp_neighbor_route_map(struct ovsrec_bgp_neighbor *ovs_bgpn,
                              struct bgp *bgp_instance,
                              const char *direction,
                              afi_t afi, safi_t safi)
{
    // If an entry for "direction" is not found in the record, NULL name
    // will trigger an unset
    char *name = NULL;

    int i;
    char *direct;

    for (i = 0; i < ovs_bgpn->n_route_maps; i++)
    {
        direct = ovs_bgpn->key_route_maps[i];

        if (!strcmp(direct, direction))
        {
            struct ovsrec_route_map *rm = ovs_bgpn->value_route_maps[i];
            name = rm->name;
            break;
        }
    }

    daemon_neighbor_route_map_cmd_execute(bgp_instance, ovs_bgpn->name,
                                          afi, safi, name, direction);
}

afi_t
network2afi(const char *network)
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
apply_bgp_neighbor_route_map_changes(struct ovsrec_bgp_neighbor *ovs_bgpn,
                                     struct bgp *bgp_instance)
{
    afi_t afi = network2afi(ovs_bgpn->name);
    safi_t safi = SAFI_UNICAST;

    if (afi)
    {
        char *direct;
        direct = OVSREC_BGP_NEIGHBOR_ROUTE_MAPS_IN;
        modify_bgp_neighbor_route_map(ovs_bgpn, bgp_instance, direct,
                                      afi, safi);

        direct = OVSREC_BGP_NEIGHBOR_ROUTE_MAPS_OUT;
        modify_bgp_neighbor_route_map(ovs_bgpn, bgp_instance, direct,
                                      afi, safi);
    }
    else
    {
        VLOG_ERR("Invalid AFI");
    }
}

static void
bgp_apply_global_changes (void)
{
    const struct ovsrec_open_vswitch *ovs;

    ovs = ovsrec_open_vswitch_first(idl);
    if (OVSREC_IDL_ANY_TABLE_ROWS_DELETED(ovs, idl_seqno)) {
        VLOG_WARN("First Row deleted from Open_vSwitch tbl\n");
        return;
    }
    if (!OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(ovs, idl_seqno) &&
            !OVSREC_IDL_ANY_TABLE_ROWS_MODIFIED(ovs, idl_seqno)) {
        VLOG_DBG("No Open_vSwitch cfg changes");
        return;
    }

    if (ovs) {
        /* Update the hostname */
        bgp_set_hostname(ovs->hostname);
    }
}

void
delete_bgp_router_config(struct ovsdb_idl *idl)
{
    const struct ovsrec_bgp_router *bgp_del_row;
    struct bgp *bgp_cfg;

    while(bgp_cfg = bgp_lookup_by_name(NULL)) {
        bool match_found = 0;
        OVSREC_BGP_ROUTER_FOR_EACH(bgp_del_row, idl) {
            if (bgp_cfg->as == bgp_del_row->asn) {
                match_found = 1;
                break;
            }
        }
        if (!match_found) {
            VLOG_DBG("bgp_cfg->as : %d will be deleted from BGPD\n",
                     (int)(bgp_cfg->as));
            bgp_delete(bgp_cfg);
        }
    }
}

void
insert_bgp_router_config(struct ovsdb_idl *idl, const struct ovsrec_bgp_router *bgp_first)
{
    const struct ovsrec_bgp_router *bgp_insert_row = bgp_first;
    struct bgp *bgp_cfg;
    int ret_status;

    OVSREC_BGP_ROUTER_FOR_EACH(bgp_insert_row, idl) {
        VLOG_INFO("New row insertion to BGP config\n");
        if (OVSREC_IDL_IS_ROW_INSERTED(bgp_insert_row, idl_seqno)) {
            ret_status = bgp_get(&bgp_cfg, (as_t *)&bgp_insert_row->asn, NULL);
            if (!ret_status) {
                VLOG_INFO("bgp_cfg->as : %d", (int)(bgp_cfg->as));
            }
        }
    }
}

void
modify_bgp_router_config(struct ovsdb_idl *idl, const struct ovsrec_bgp_router *bgp_first)
{
    const struct ovsrec_bgp_router *bgp_mod_row = bgp_first;
    const struct ovsdb_idl_column *column;
    struct bgp *bgp_cfg;
    as_t as;
    int ret_status;

    OVSREC_BGP_ROUTER_FOR_EACH(bgp_mod_row, idl) {
        if (OVSREC_IDL_IS_ROW_INSERTED(bgp_mod_row, idl_seqno) ||
             OVSREC_IDL_IS_ROW_MODIFIED(bgp_mod_row, idl_seqno)) {
            bgp_cfg = bgp_lookup((as_t)bgp_mod_row->asn, NULL);
	    /* Check if router_id is modified */
            if (OVSREC_IDL_IS_COLUMN_MODIFIED(ovsrec_bgp_router_col_router_id, idl_seqno)) {
                ret_status = modify_bgp_router_id_config(bgp_cfg,bgp_mod_row);
                if (!ret_status) {
                    VLOG_INFO("BGP router_id set to %s", inet_ntoa(bgp_cfg->router_id));
                }
            }

            /* Check if network is modified */
            if (OVSREC_IDL_IS_COLUMN_MODIFIED(ovsrec_bgp_router_col_networks, idl_seqno)) {
                modify_bgp_network_config(bgp_cfg,bgp_mod_row);
            }

	    /* Check if maximum_paths is modified */
            if (OVSREC_IDL_IS_COLUMN_MODIFIED(ovsrec_bgp_router_col_maximum_paths, idl_seqno)) {
                ret_status = modify_bgp_maxpaths_config(bgp_cfg,bgp_mod_row);
                if (!ret_status) {
                    VLOG_INFO("Maximum paths for BGP is set to %d",
                               bgp_cfg->maxpaths[AFI_IP][SAFI_UNICAST].maxpaths_ebgp);
                    }
                }

            /* Check if bgp timers are modified */
            if (OVSREC_IDL_IS_COLUMN_MODIFIED(ovsrec_bgp_router_col_timers, idl_seqno)) {
                ret_status = modify_bgp_timers_config(bgp_cfg,bgp_mod_row);
                if (!ret_status) {
                    VLOG_INFO("BGP timers set as : "
                              "bgp_cfg->default_keepalive : %d"
                              "bgp_cfg->default_holdtime : %d",
                               bgp_cfg->default_keepalive,
                               bgp_cfg->default_holdtime);
                }
            }
	}
    }
}

int
modify_bgp_router_id_config(struct bgp *bgp_cfg, const struct ovsrec_bgp_router *bgp_mod_row)
{
    const struct ovsdb_idl_column *column;
    struct in_addr addr;

    addr.s_addr = inet_addr(bgp_mod_row->router_id);
    return bgp_router_id_set(bgp_cfg, &addr.s_addr);
}

void
bgp_static_route_dump(struct bgp *bgp_cfg, struct bgp_node *rn)
{
    char prefix_str[256];
    for (rn = bgp_table_top (bgp_cfg->route[AFI_IP][SAFI_UNICAST]);rn;
         rn = bgp_route_next (rn)) {
        memset(prefix_str, 0 ,sizeof(prefix_str));
        int ret = prefix2str(&rn->p, prefix_str, sizeof(prefix_str));
        if (ret) {
            VLOG_ERR("Prefix to string conversion failed!");
        }
        else {
            if (!strcmp(prefix_str,"0.0.0.0/0"))
               continue;
            if (rn->info != NULL)
               VLOG_INFO("Static route : %s", prefix_str);
        }
    }
}

int
modify_bgp_network_config(struct bgp *bgp_cfg,
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
bgp_static_route_addition(struct bgp *bgp_cfg,
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
                                      bgp_mod_row->networks[i],
                                      afi, safi,
                                      NULL, 0);
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
bgp_static_route_deletion(struct bgp *bgp_cfg,
                          const struct ovsrec_bgp_router *bgp_mod_row)
{
    struct bgp_node *rn;
    afi_t afi;
    safi_t safi;
    int ret_status = -1;
    int i = 0;
    if (bgp_cfg = bgp_lookup((as_t)bgp_mod_row->asn, NULL)) {
        bool match_found = 0;
        char prefix_str[256];

        for (rn = bgp_table_top (bgp_cfg->route[AFI_IP][SAFI_UNICAST]);rn;
             rn = bgp_route_next (rn)) {
            memset(prefix_str, 0 ,sizeof(prefix_str));
            int ret = prefix2str(&rn->p, prefix_str, sizeof(prefix_str));
            if (ret) {
                VLOG_ERR("Prefix to string conversion failed!");
                return -1;
            }
            else {
                VLOG_DBG("Prefix to str : %s", prefix_str);
            }
            if (!strcmp(prefix_str,"0.0.0.0/0"))
                continue;
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
            }
            else {
                bool match_found = 0;
                for (i = 0; i < bgp_mod_row->n_networks; i++) {
                    if(!strcmp(prefix_str, bgp_mod_row->networks[i])) {
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
    return ret_status;
}

int
modify_bgp_maxpaths_config(struct bgp *bgp_cfg, const struct ovsrec_bgp_router *bgp_mod_row)
{
    bgp_flag_set(bgp_cfg, BGP_FLAG_ASPATH_MULTIPATH_RELAX);
    return bgp_maximum_paths_set(bgp_cfg, AFI_IP, SAFI_UNICAST,
                                 BGP_PEER_EBGP,
				 (u_int16_t)bgp_mod_row->maximum_paths[0]);
}

int
modify_bgp_timers_config(struct bgp *bgp_cfg, const struct ovsrec_bgp_router *bgp_mod_row)
{
    int64_t keepalive=0, holdtime=0;
    struct smap smap;
    struct ovsdb_datum *datum;
    int ret_status=0;

    datum = ovsrec_bgp_router_get_timers(bgp_mod_row,
        OVSDB_TYPE_STRING, OVSDB_TYPE_INTEGER);

    /* Can be seen on ovsdb restart */
    if (NULL == datum) {
        VLOG_DBG("No value found for given key");
        return -1;
    }
    else {
        ovsdb_datum_get_int64_value_given_string_key(datum,
                                                     bgp_mod_row->key_timers[1],
                                                     &keepalive);
        ovsdb_datum_get_int64_value_given_string_key(datum,
                                                     bgp_mod_row->key_timers[0],
                                                     &holdtime);
        ret_status = bgp_timers_set (bgp_cfg, keepalive, holdtime);
        return ret_status;
    }
}

/* Subscribe for changes in the BGP_Router table */
static void
bgp_apply_bgp_router_changes(struct ovsdb_idl *idl)
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
    }
    else {
        /* Check if any row deletion */
        if (OVSREC_IDL_ANY_TABLE_ROWS_DELETED(bgp_first, idl_seqno)) {
            delete_bgp_router_config(idl);
        }
        if (OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(bgp_first, idl_seqno) ||
            OVSREC_IDL_ANY_TABLE_ROWS_MODIFIED(bgp_first, idl_seqno)) {
            /* Check if any row insertion */
            if (OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(bgp_first, idl_seqno)) {
                insert_bgp_router_config(idl, bgp_first);
            }
            /* Check if any row modification */
            modify_bgp_router_config(idl, bgp_first);
        }
    }
}

static bool
object_is_peer (struct ovsrec_bgp_neighbor *db_bgpn_p)
{
    return
	(db_bgpn_p->n_is_peer_group == 0) ||
	!(*(db_bgpn_p->is_peer_group));
}

static bool
object_is_peer_group (struct ovsrec_bgp_neighbor *db_bgpn_p)
{
    return
	(db_bgpn_p->n_is_peer_group > 0) &&
	*(db_bgpn_p->is_peer_group);
}

/*
** Iterate through all the peers of the BGP and check against
** ovsdb to identify which neighbor has been deleted. If it doesn't exist
** in ovsdb then it is considered deleted.
*/
 static void
check_and_delete_bgp_neighbors (struct bgp *bgp, struct ovsdb_idl *idl)
{
    struct peer *peer;
    struct listnode *node, *nnode;
    struct ovsrec_bgp_neighbor *bgpn;
    bool deleted_from_database;

    for (ALL_LIST_ELEMENTS(bgp->peer, node, nnode, peer)) {
	deleted_from_database = true;
        OVSREC_BGP_NEIGHBOR_FOR_EACH(bgpn, idl) {
            if (object_is_peer(bgpn) &&
	        (0 == strcmp(bgpn->name, peer->host))) {
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
** same as above but for peer groups
*/
 static void
check_and_delete_bgp_neighbor_peer_groups (struct bgp *bgp,
    struct ovsdb_idl *idl)
{
    struct peer_group *peer_group;
    struct listnode *node, *nnode;
    struct ovsrec_bgp_neighbor *bgpn;
    bool deleted_from_database;

    for (ALL_LIST_ELEMENTS(bgp->group, node, nnode, peer_group)) {
        deleted_from_database = true;
        OVSREC_BGP_NEIGHBOR_FOR_EACH(bgpn, idl) {
            if (object_is_peer_group(bgpn) &&
	        (0 == strcmp(bgpn->name, peer_group->name))) {
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
** since we cannot possibly know in advance what is deleted
** from the database, we check for *ALL* bgps, all of their
** groups & all of their peers.
*/
static void
delete_bgp_neighbors_and_peer_groups (struct ovsdb_idl *idl)
{
    struct bgp *bgp;
    struct listnode *node, *nnode;

    for (ALL_LIST_ELEMENTS(bm->bgp, node, nnode, bgp)) {
	check_and_delete_bgp_neighbors(bgp, idl);
	check_and_delete_bgp_neighbor_peer_groups(bgp, idl);
    }
}

static const struct ovsrec_bgp_neighbor *
get_bgp_neighbor_with_VrfName_BgpRouterAsn_Ipaddr (struct ovsdb_idl *idl,
    char *vrf_name,
    int asn,
    char *ipaddr)
{
    const struct ovsrec_bgp_neighbor *nptr;

    if (NULL == vrf_name) {
	vrf_name = DEFAULT_VRF_NAME;
    }
    OVSREC_BGP_NEIGHBOR_FOR_EACH(nptr, idl) {
	if (!object_is_peer_group(nptr) &&
	    ipaddr && (0 == strcmp(ipaddr, nptr->name)) &&
	    nptr->bgp_router && (nptr->bgp_router->asn == asn) &&
	    nptr->bgp_router->vrf &&
		(0 == strcmp(nptr->bgp_router->vrf->name, vrf_name)))
		    return nptr;
    }
    return NULL;
}

struct ovsrec_bgp_neighbor *
get_bgp_neighbor_db_row (struct peer *peer)
{
    char *ipaddr;
    char ip_addr_string [64];

    ipaddr = sockunion2str(&peer->su, ip_addr_string, 63);
    return
	get_bgp_neighbor_with_VrfName_BgpRouterAsn_Ipaddr
	    (idl, NULL, peer->bgp->as, ipaddr);
}

void
bgp_daemon_ovsdb_neighbor_statistics_update (bool start_new_db_txn,
    struct ovsrec_bgp_neighbor *ovs_bgp_neighbor_ptr, struct peer *peer)
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
** update a bunch of BGP_Neighbor related info
** in the ovs database, from the daemon side
*/
void bgp_daemon_ovsdb_neighbor_update (struct peer *peer,
    bool update_stats_too)
{
    struct ovsrec_bgp_neighbor *ovs_bgp_neighbor_ptr;
    struct ovsdb_idl_txn *db_txn;
    enum ovsdb_idl_txn_status status;
    struct smap smap;

    ovs_bgp_neighbor_ptr = get_bgp_neighbor_db_row(peer);
    if (NULL == ovs_bgp_neighbor_ptr) {
	VLOG_ERR("%%bgp_daemon_ovsdb_neighbor_update cannot find db row\n");
	return;
    }
    VLOG_DBG("updating bgp neighbor %s remote-as %d in db\n",
	ovs_bgp_neighbor_ptr->name, *ovs_bgp_neighbor_ptr->remote_as);
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
    ovsrec_bgp_neighbor_set_tcp_port_number(ovs_bgp_neighbor_ptr, &peer->port, 1);

    VLOG_DBG("updating local_as to %d\n", peer->local_as);
    // This causes the entire transaction to be rejected, investigate later
    // ovsrec_bgp_neighbor_set_local_as(ovs_bgp_neighbor_ptr, &peer->local_as, 1);

    VLOG_DBG("updating weight to %d\n", peer->weight);
    ovsrec_bgp_neighbor_set_weight(ovs_bgp_neighbor_ptr, &peer->weight, 1);

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

/*
** Process potential changes in the BGP_Neighbor table
*/
static void
bgp_apply_bgp_neighbor_changes (struct ovsdb_idl *idl)
{
    struct ovsrec_bgp_neighbor *db_bgpn_p;
    struct bgp *bgp_instance;
    bool inserted = false;
    bool modified = false;
    bool deleted = false;
    u_int32_t keepalive;
    u_int32_t holdtimer;

    db_bgpn_p = ovsrec_bgp_neighbor_first(idl);

    /*
    ** if there are no bgp neighbor/peer-groups, all of
    ** them may have been deleted.  If that is the case,
    ** modified & inserted cannot possibly be true since
    ** there is nothing left to process in the db
    */
    if (NULL == db_bgpn_p) {
	deleted = true;		// possibility
    } else {
	if (ANY_ROW_DELETED(db_bgpn_p, idl_seqno)) {
	    deleted = true;
	}
	if (ANY_NEW_ROW(db_bgpn_p, idl_seqno)) {
	    inserted = true;
	}
	if (ANY_ROW_CHANGED(db_bgpn_p, idl_seqno)) {
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

    /* process all possible changes for each entry */
    OVSREC_BGP_NEIGHBOR_FOR_EACH(db_bgpn_p, idl) {

	/* find corresponding bgp router */
	if (!db_bgpn_p->bgp_router) {
	    VLOG_ERR("%%cannot find bgp router pointer in idl\n");
	    continue;
	}
	VLOG_DBG("looking up bgp %d\n", db_bgpn_p->bgp_router->asn);
	bgp_instance = bgp_lookup(db_bgpn_p->bgp_router->asn, NULL);
	if (!bgp_instance) {
	    VLOG_ERR("%%cannot find daemon bgp router instance %d\n",
		db_bgpn_p->bgp_router->asn);
	    continue;
	}

	VLOG_DBG("bgp router instance %d found\n",
	    db_bgpn_p->bgp_router->asn);

	/*
	** If this is a new row, call the appropriate
	** daemon function depending on whether the
	** created object is a bgp peer or a bgp peer
	** group and if remote-as has been specified.
	*/
	if (NEW_ROW(db_bgpn_p, idl_seqno)) {
	    if (db_bgpn_p->n_remote_as) {
		VLOG_DBG("creating a peer%s object %s with remote-as %d\n",
		    object_is_peer(db_bgpn_p) ? "" : "-group",
		    db_bgpn_p->name,
		    *db_bgpn_p->remote_as);
		daemon_neighbor_remote_as_cmd_execute
		    (bgp_instance, db_bgpn_p->name, db_bgpn_p->remote_as,
		    AFI_IP, SAFI_UNICAST);
	    } else {
		VLOG_DBG("creating a peer%s object %s without remote-as\n",
		    object_is_peer(db_bgpn_p) ? "" : "-group",
		    db_bgpn_p->name);
		daemon_neighbor_peer_group_cmd_execute
		    (bgp_instance, db_bgpn_p->name);
	    }
	}

	/* if we are here, an EXISTING entry must have been modified */

	/* remote-as */
	if (COL_CHANGED(db_bgpn_p, ovsrec_bgp_neighbor_col_remote_as, idl_seqno)) {
	    daemon_neighbor_remote_as_cmd_execute
		(bgp_instance, db_bgpn_p->name, db_bgpn_p->remote_as,
		 AFI_IP, SAFI_UNICAST);
	}

	/* peer group */
	if (COL_CHANGED(db_bgpn_p, ovsrec_bgp_neighbor_col_bgp_peer_group,
	    idl_seqno)) {
		const struct ovsrec_bgp_neighbor *peer_group =
		    db_bgpn_p->bgp_peer_group;
		if (peer_group) {
		    daemon_neighbor_set_peer_group_cmd_execute(bgp_instance,
			db_bgpn_p->name, peer_group->name, AFI_IP, SAFI_UNICAST);
		} else {
		    daemon_no_neighbor_set_peer_group_cmd_execute(bgp_instance,
			db_bgpn_p->name, AFI_IP, SAFI_UNICAST);
		}
	}

	/* description */
	if (COL_CHANGED(db_bgpn_p, ovsrec_bgp_neighbor_col_description,
	    idl_seqno)) {
		daemon_neighbor_description_cmd_execute
		    (bgp_instance, db_bgpn_p->name, db_bgpn_p->description);
	}

	/* passwd */
	if (COL_CHANGED(db_bgpn_p, ovsrec_bgp_neighbor_col_password,
	    idl_seqno)) {
		daemon_neighbor_password_cmd_execute
		    (bgp_instance, db_bgpn_p->name, db_bgpn_p->password);
	}

	/* shutdown */
	if (COL_CHANGED(db_bgpn_p, ovsrec_bgp_neighbor_col_shutdown,
	    idl_seqno)) {
		bool shut = db_bgpn_p->n_shutdown && db_bgpn_p->shutdown[0];
		daemon_neighbor_shutdown_cmd_execute
		    (bgp_instance, db_bgpn_p->name, shut);
	}

    /* remove_private_as */
    if (COL_CHANGED(db_bgpn_p,
                    ovsrec_bgp_neighbor_col_remove_private_as,
                    idl_seqno)) {
        if (db_bgpn_p->n_remove_private_as
            && db_bgpn_p->remove_private_as[0]) {
            daemon_neighbor_remove_private_as_cmd_execute(bgp_instance,
                                                          db_bgpn_p->name,
                                                          AFI_IP,
                                                          SAFI_UNICAST,
                                                          true);
        } else {
            daemon_neighbor_remove_private_as_cmd_execute(bgp_instance,
                                                          db_bgpn_p->name,
                                                          AFI_IP,
                                                          SAFI_UNICAST,
                                                          false);
        }
    }

	/* inbound_soft_reconfiguration */
	if (COL_CHANGED(db_bgpn_p,
	    ovsrec_bgp_neighbor_col_inbound_soft_reconfiguration, idl_seqno)) {
		bool enable =
		    db_bgpn_p->n_inbound_soft_reconfiguration &&
		    db_bgpn_p->inbound_soft_reconfiguration[0];
		daemon_neighbor_inbound_soft_reconfiguration_cmd_execute
		    (bgp_instance, db_bgpn_p->name, AFI_IP, SAFI_UNICAST, enable);
	}

	/* route map */
	if (COL_CHANGED(db_bgpn_p, ovsrec_bgp_neighbor_col_route_maps,
	    idl_seqno)) {
		apply_bgp_neighbor_route_map_changes(db_bgpn_p, bgp_instance);
	}

	/* timers */
	if (COL_CHANGED(db_bgpn_p, ovsrec_bgp_neighbor_col_timers,
	    idl_seqno)) {
		keepalive = fetch_key_value(db_bgpn_p->key_timers,
				db_bgpn_p->value_timers,
				db_bgpn_p->n_timers,
				OVSDB_BGP_TIMER_KEEPALIVE);
		holdtimer = fetch_key_value(db_bgpn_p->key_timers,
				db_bgpn_p->value_timers,
				db_bgpn_p->n_timers,
				OVSDB_BGP_TIMER_HOLDTIME);
		daemon_neighbor_timers_cmd_execute(bgp_instance,
			db_bgpn_p->name, keepalive, holdtimer);
	}

	/* allow_as_in */
	if (COL_CHANGED(db_bgpn_p, ovsrec_bgp_neighbor_col_allow_as_in,
	    idl_seqno)) {
		daemon_neighbor_allow_as_in_cmd_execute(bgp_instance,
		    db_bgpn_p->name, AFI_IP, SAFI_UNICAST,
		    db_bgpn_p->allow_as_in);
	}
    }
}

static void
bgp_reconfigure(struct ovsdb_idl *idl)
{
    unsigned int new_idl_seqno = ovsdb_idl_get_seqno(idl);
    COVERAGE_INC(bgp_ovsdb_cnt);

    if (new_idl_seqno == idl_seqno){
        VLOG_DBG("No config change for bgp in ovs\n");
        return;
    }

    /*
     * Apply route map changes
     */
    policy_ovsdb_prefix_list_get (idl);
    policy_ovsdb_rt_map(idl);

    /* Apply the changes */
    bgp_apply_global_changes();
    bgp_apply_bgp_router_changes(idl);
    bgp_apply_bgp_neighbor_changes(idl);

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
        VLOG_INFO_ONCE("%s (Halon bgpd) %s", program_name, VERSION);
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
        /*
         * Could not enqueue the events.
         * Retry in 1 sec
         */
        thread_add_timer(bovs_g->master,
                         bovs_read_cb, bovs_g, 1);
    }
    return 1;
}

/* Add the list of OVS poll fd to the master thread of the daemon
 */
static int
bgp_ovspoll_enqueue (bgp_ovsdb_t *bovs_g)
{
    struct poll_loop *loop = poll_loop();
    struct poll_node *node;
    long int timeout;
    int retval = -1;

    /* Populate with all the fds events. */
    HMAP_FOR_EACH (node, hmap_node, &loop->poll_nodes) {
        thread_add_read(bovs_g->master,
                                    bovs_read_cb,
                                    bovs_g, node->pollfd.fd);
        /*
         * If we successfully connected to OVS return 0.
         * Else return -1 so that we try to reconnect.
         * */
        retval = 0;
    }

    /* Populate the timeout event */
    timeout = loop->timeout_when - time_msec();
    if(timeout > 0 && loop->timeout_when > 0 &&
       loop->timeout_when < LLONG_MAX) {
        /* Convert msec to sec */
        timeout = (timeout + 999)/1000;

        thread_add_timer(bovs_g->master,
                                     bovs_read_cb, bovs_g,
                                     timeout);
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
ovsdb_exit(void)
{
    ovsdb_idl_destroy(idl);
}

/* When the daemon is ready to shut, delete the idl cache
 * This happens with the ovs-appctl exit command.
 */
void bgp_ovsdb_exit(void)
{
    ovsdb_exit();
}
