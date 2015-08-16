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
#include "policy_ovsdb.h"

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
static unsigned int idl_seqno;
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
bgp_ovsdb_tables_init (struct ovsdb_idl *idl)
{
    /* BGP router table */
    ovsdb_idl_add_table(idl, &ovsrec_table_bgp_router);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_asn);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_router_id);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_networks);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_vrf);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_redistribute);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_gr_stale_timer);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_always_compare_med);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_other_config);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_status);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_router_col_external_ids);

    /* BGP neighbor table */
    ovsdb_idl_add_table(idl, &ovsrec_table_bgp_neighbor);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_active);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_weight);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_bgp_peer_group);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_bgp_router);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_strict_capability_match);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_tcp_port_number);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_inbound_soft_reconfiguration);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_statistics);
    ovsdb_idl_add_column(idl, &ovsrec_bgp_neighbor_col_remote_as);
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
        VLOG_INFO("No BGP_Router changes");
        return;
    }

    if (bgp_first == NULL) {
        /* Check if it is a first row deletion */
        VLOG_INFO("BGP config empty!\n");
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
        /* Check if any row insertion */
        if (OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(bgp_first, idl_seqno)) {
	    insert_bgp_router_config(idl, bgp_first);
	}
	else {
            /* Check if any row modification */
	    if (OVSREC_IDL_ANY_TABLE_ROWS_MODIFIED(bgp_first, idl_seqno)) {
                modify_bgp_router_config(idl, bgp_first);
            }
        }
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
                VLOG_INFO("bgp_insert_row->asn : %d, bgp_cfg->as : %d",
                           bgp_insert_row->asn,(int)(bgp_cfg->as));
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
    struct in_addr addr;
    as_t as;
    int ret_status;
    int i = 0;

    OVSREC_BGP_ROUTER_FOR_EACH(bgp_mod_row, idl) {
        if (OVSREC_IDL_IS_ROW_MODIFIED(bgp_mod_row, idl_seqno)) {
            bgp_cfg = bgp_lookup((as_t)bgp_mod_row->asn, NULL);
            /* Check if router_id is modified */
            if (OVSREC_IDL_IS_COLUMN_MODIFIED(ovsrec_bgp_router_col_router_id, idl_seqno)) {
                addr.s_addr = inet_addr(bgp_mod_row->router_id);
                ret_status = bgp_router_id_set(bgp_cfg, &addr.s_addr);
                if (!ret_status) {
                    VLOG_INFO("BGP router_id set to %s",
                               inet_ntoa(bgp_cfg->router_id));
                }
            }
            if (OVSREC_IDL_IS_COLUMN_MODIFIED(ovsrec_bgp_router_col_networks, idl_seqno)) {
                struct bgp_static *bgp_static;
                struct prefix p;
                struct vty *vty;
                struct bgp_node *rn;
                afi_t afi;
                safi_t safi;
                for (i = 0; i < bgp_mod_row->n_networks; i++) {
                    VLOG_INFO("bgp_mod_row->networks[%d]: %s",
                   i, bgp_mod_row->networks[i]);
                    int ret = str2prefix(bgp_mod_row->networks[i], &p);
                    if (! ret) {
                        VLOG_ERR("Malformed prefix");
                    }
                    afi = family2afi(p.family);
                    safi = SAFI_UNICAST;
                    rn = bgp_node_lookup(bgp_cfg->route[afi][safi], &p);
                    if (!rn) {
                        VLOG_INFO("Can't find specified static "
                                  "route configuration..\n");
                        VLOG_INFO("Adding new static route\n");
                        ret_status = bgp_static_set(vty, bgp_cfg,
                                                    bgp_mod_row->networks[i],
                                                    afi, safi,
                                                    NULL, 0);
                        if (!ret_status) {
                            VLOG_INFO("New static route added to bgp routing table");
                        }
                    }
                }
            }
        }
    }
}

/*
** Process potential changes in the BGP_Neighbor table
*/
static void
bgp_apply_bgp_neighbor_changes (struct ovsdb_idl *idl)
{
    struct ovsrec_bgp_neighbor *ovs_bgpn;
    struct bgp *bgp_instance;
    bool modified = false;
    bool deleted = false;

    ovs_bgpn = ovsrec_bgp_neighbor_first(idl);

    /* try & find if any row got deleted or modified */
    if (!ovs_bgpn) {
	deleted = true;
    } else {
	if (OVSREC_IDL_ANY_TABLE_ROWS_DELETED(ovs_bgpn, idl_seqno)) {
	    deleted = true;
	}
	if (OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(ovs_bgpn, idl_seqno) ||
	    OVSREC_IDL_ANY_TABLE_ROWS_MODIFIED(ovs_bgpn, idl_seqno)) {
		modified = true;
	}
    }

    /* take care of deletions if any */
    if (deleted) {
	VLOG_INFO("bgp neighbor deletion occured\n");
    }

    /* take care of modifications if any */
    if (modified) {
	VLOG_INFO("bgp neighbor modification occured\n");
	OVSREC_BGP_NEIGHBOR_FOR_EACH(ovs_bgpn, idl) {
	    if (OVSREC_IDL_IS_ROW_INSERTED(ovs_bgpn, idl_seqno) ||
		OVSREC_IDL_IS_ROW_MODIFIED(ovs_bgpn, idl_seqno))
	    {
		if (!ovs_bgpn->bgp_router) {
		    VLOG_ERR("%%cannot find bgp router in idl\n");
		} else {
		    VLOG_INFO("looking up bgp %d\n", ovs_bgpn->bgp_router->asn);
		    bgp_instance = bgp_lookup(ovs_bgpn->bgp_router->asn, NULL);
		    if (bgp_instance) {
			VLOG_INFO("bgp router instance %d found\n",
			    ovs_bgpn->bgp_router->asn);
			daemon_neighbor_remote_as_cmd_execute
			    (bgp_instance, ovs_bgpn->name,
				ovs_bgpn->remote_as, AFI_IP, SAFI_UNICAST);
                       if (ovs_bgpn->description) {
                           daemon_neighbor_description_cmd_execute(bgp_instance,
                                ovs_bgpn->name, ovs_bgpn->description);
                       } else {
                           daemon_neighbor_description_cmd_execute(bgp_instance,
                                ovs_bgpn->name, NULL);
                       }
                       if (ovs_bgpn->password) {
                           daemon_neighbor_password_cmd_execute(bgp_instance,
                                ovs_bgpn->name, ovs_bgpn->password);
                       } else {
                           daemon_neighbor_password_cmd_execute(bgp_instance,
                                ovs_bgpn->name, NULL);
                       }
#if 0
                       if (ovs_bgpn->timers) {
                           u_int32_t keepalive = 0;
                           u_int32_t holdtime = 0;
                           keepalive = smap_get(&ovs_bgpn->timers, "Keepalive");
                           holdtime = smap_get(&ovs_bgpn->timers, "Holdtime");
                          daemon_neighbor_timers_cmd_execute(bgp_instance,
                                                            keepalive, holdtime);
                       }
#endif
                      if (ovs_bgpn->n_shutdown && ovs_bgpn->shutdown[0]) {
                          daemon_neighbor_shutdown_cmd_execute
                                       (bgp_instance, ovs_bgpn->name, true);
                      } else {
                         daemon_neighbor_shutdown_cmd_execute
                                       (bgp_instance, ovs_bgpn->name, false);
                      }
		    } else {
			VLOG_ERR("%%cannot find daemon bgp router instance %d %%\n",
			    ovs_bgpn->bgp_router->asn);
		    }
		}
	    }
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
