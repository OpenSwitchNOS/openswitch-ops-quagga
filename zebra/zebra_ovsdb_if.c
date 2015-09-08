/* zebra daemon ovsdb integration.
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
 * File: zebra_ovsdb_if.c
 *
 * Purpose: Main file for integrating zebra with ovsdb and ovs poll-loop.
 */

#include <zebra.h>

#include <lib/version.h>
#include "getopt.h"
#include "command.h"
#include "thread.h"
#include "memory.h"
#include "zebra/zserv.h"
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
#include "hash.h"
#include "jhash.h"

#include "openhalon-idl.h"

#include "zebra/zebra_ovsdb_if.h"

/* Local structure to hold the master thread
 * and counters for read/write callbacks
 */
typedef struct zebra_ovsdb_t_ {
    int enabled;
    struct thread_master *master;

    unsigned int read_cb_count;
    unsigned int write_cb_count;
} zebra_ovsdb_t;

static zebra_ovsdb_t glob_zebra_ovs;

COVERAGE_DEFINE(zebra_ovsdb_cnt);
VLOG_DEFINE_THIS_MODULE(zebra_ovsdb_if);

static struct ovsdb_idl *idl;
static unsigned int idl_seqno;
static char *appctl_path = NULL;
static struct unixctl_server *appctl;
static int system_configured = false;
static struct ovsdb_idl_txn *rib_txn = NULL;
unsigned char rib_kernel_updates = false;
bool zebra_db_updates = false;

boolean exiting = false;
/* Hash for ovsdb route.*/
static struct hash *zebra_route_hash;

/* List of delete route */
struct list *zebra_route_del_list;

static int zebra_ovspoll_enqueue (zebra_ovsdb_t *zovs_g);
static int zovs_read_cb (struct thread *thread);
int zebra_add_route(bool is_ipv6, struct prefix *p, int type, safi_t safi,
                    const struct ovsrec_route *route);
#ifdef HAVE_IPV6
extern int
rib_add_ipv6_multipath (struct prefix_ipv6 *p, struct rib *rib, safi_t safi);
#endif

#define HASH_BUCKET_SIZE 32768

#define OVSDB_ROUTE_MIN     0
#define OVSDB_ROUTE_ADD     1
#define OVSDB_ROUTE_DELETE  2
#define OVSDB_ROUTE_IGNORE  3


/* ovs appctl dump function for this daemon
 * This is useful for debugging
 */
static void
zebra_unixctl_dump(struct unixctl_conn *conn, int argc OVS_UNUSED,
                          const char *argv[] OVS_UNUSED, void *aux OVS_UNUSED)
{
    unixctl_command_reply_error(conn, "Nothing to dump :)");
    //unixctl_command_reply(conn, buf);
}

/* Create a connection to the OVSDB at db_path and create a dB cache
 * for this daemon. */
static void
ovsdb_init (const char *db_path)
{
    /* Initialize IDL through a new connection to the dB. */
    idl = ovsdb_idl_create(db_path, &ovsrec_idl_class, false, true);
    idl_seqno = ovsdb_idl_get_seqno(idl);
    ovsdb_idl_set_lock(idl, "halon_zebra");
    ovsdb_idl_verify_write_only(idl);

    /* Cache OpenVSwitch table */
    ovsdb_idl_add_table(idl, &ovsrec_table_open_vswitch);

    ovsdb_idl_add_column(idl, &ovsrec_open_vswitch_col_cur_cfg);
    ovsdb_idl_add_column(idl, &ovsrec_open_vswitch_col_hostname);

    /* Register for ROUTE table */
    /* We need to register for columns to really get rows in the idl */
    ovsdb_idl_add_table(idl, &ovsrec_table_route);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_prefix);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_address_family);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_distance);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_metric);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_from);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_sub_address_family);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_nexthops);
    /*
     * Register to the "selected" column in the route table to write
     * to it. If selected is TRUE, this is a FIB entry
     */
    ovsdb_idl_add_column(idl, &ovsrec_route_col_selected);
    ovsdb_idl_omit_alert(idl, &ovsrec_route_col_selected);

    /* Register for NextHop table */
    ovsdb_idl_add_table(idl, &ovsrec_table_nexthop);
    ovsdb_idl_add_column(idl, &ovsrec_nexthop_col_ip_address);
    ovsdb_idl_add_column(idl, &ovsrec_nexthop_col_ports);
    ovsdb_idl_add_column(idl, &ovsrec_nexthop_col_status);

    /* Register for port table */
    ovsdb_idl_add_table(idl, &ovsrec_table_port);
    ovsdb_idl_add_column(idl, &ovsrec_port_col_name);

    /* Register ovs-appctl commands for this daemon. */
    unixctl_command_register("zebra/dump", "", 0, 0, zebra_unixctl_dump, NULL);
}

static void
halon_zebra_exit(struct unixctl_conn *conn, int argc OVS_UNUSED,
                  const char *argv[] OVS_UNUSED, void *exiting_)
{
    boolean *exiting = exiting_;
    *exiting = true;
    unixctl_command_reply(conn, NULL);
}

static void
usage(void)
{
    printf("%s: Halon zebra daemon\n"
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
 * in zebra to avoid issues.
 */
static char *
zebra_ovsdb_parse_options(int argc, char *argv[], char **unixctl_pathp)
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

/* Setup zebra to connect with ovsdb and daemonize. This daemonize is used
 * over the daemonize in the main function to keep the behavior consistent
 * with the other daemons in the HALON system
 */
void zebra_ovsdb_init (int argc, char *argv[])
{
    int retval;
    char *ovsdb_sock;

    memset(&glob_zebra_ovs, 0, sizeof(glob_zebra_ovs));

    set_program_name(argv[0]);
    proctitle_init(argc, argv);
    fatal_ignore_sigpipe();

    /* Parse commandline args and get the name of the OVSDB socket. */
    ovsdb_sock = zebra_ovsdb_parse_options(argc, argv, &appctl_path);

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
    unixctl_command_register("exit", "", 0, 0, halon_zebra_exit, &exiting);

   /* Create the IDL cache of the dB at ovsdb_sock. */
   ovsdb_init(ovsdb_sock);
   free(ovsdb_sock);

   /* Notify parent of startup completion. */
   daemonize_complete();

   /* Enable asynch log writes to disk. */
   vlog_enable_async();

   VLOG_INFO_ONCE("%s (Halon Zebra Daemon) started", program_name);

   glob_zebra_ovs.enabled = 1;
   return;
}

static void
zebra_ovs_clear_fds (void)
{
    struct poll_loop *loop = poll_loop();
    free_poll_nodes(loop);
    loop->timeout_when = LLONG_MAX;
    loop->timeout_where = NULL;
}

/* Check if the system is already configured. The daemon should
 * not process any callbacks unless the system is configured.
 */
static inline void zebra_chk_for_system_configured(void)
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

bool is_route_nh_rows_modified(const struct ovsrec_route *route)
{
    const struct ovsrec_nexthop *nexthop;
    int index;

    for(index=0; index < route->n_nexthops; index++)
    {
        nexthop = route->nexthops[index];
        if ( (OVSREC_IDL_IS_ROW_INSERTED(nexthop, idl_seqno)) ||
             (OVSREC_IDL_IS_ROW_MODIFIED(nexthop, idl_seqno)) )
        {
             return 1;
        }
    }

    return 0;
}

bool is_rib_nh_rows_deleted(const struct ovsrec_route *route)
{
    const struct ovsrec_nexthop *nexthop;

    nexthop = route->nexthops[0];
    if ( ( nexthop != NULL ) &&
         ( OVSREC_IDL_ANY_TABLE_ROWS_DELETED(nexthop, idl_seqno) ) )
    {
        return 1;
    }

    return 0;
}

static void
print_key(struct zebra_route_key *rkey)
{
    VLOG_DBG("prefix=0x%x", rkey->prefix.u.ipv4_addr.s_addr);
    VLOG_DBG("prefix len=%d", rkey->prefix_len);
    VLOG_DBG("nexthop=0x%x", rkey->nexthop.u.ipv4_addr.s_addr);
    if ( strlen(rkey->ifname) !=0 ) {
        VLOG_DBG("ifname=0x%s", rkey->ifname);
    }
}

/* Hash route key */
unsigned int
zebra_route_key_make(void *p)
{
    const struct zebra_route_key *rkey = (struct zebra_route_key *) p;
    unsigned int key = 0;

     key = jhash2((const uint32_t *)rkey,
                  (sizeof(struct zebra_route_key)) / sizeof(uint32_t), 0);

    return key;
}

/* Compare two keys */
static int
zebra_route_key_cmp(const void *arg1, const void *arg2)
{
    const struct zebra_route_key *rkey_1 = (struct zebra_route_key *) arg1;

    const struct zebra_route_key *rkey_2 = (struct zebra_route_key *) arg2;

    if (!memcmp(rkey_1, rkey_2, sizeof(struct zebra_route_key))) {
        return 1;
    } else {
       return 0;
    }
}

/* Init hash table and size of table */
static void
zebra_route_hash_init (void)
{
    zebra_route_hash = hash_create_size(HASH_BUCKET_SIZE, zebra_route_key_make,
                                        zebra_route_key_cmp);
}

/* Allocate route key */
static void *
zebra_route_hash_alloc (void *p)
{
    struct zebra_route_key *val = (struct zebra_route_key *) p;
    struct zebra_route_key *addr;

    addr = XMALLOC(MTYPE_TMP, sizeof (struct zebra_route_key));
    assert(addr);
    memcpy(addr, val, sizeof(struct zebra_route_key));

    return addr;
}

/* Add ovsdb routes to hash table */
static void
zebra_route_hash_add(const struct ovsrec_route *route)
{
    struct zebra_route_key tmp_key;
    struct zebra_route_key *add;
    int ret;
    size_t i;
    struct ovsrec_nexthop *nexthop;
    struct prefix p;
    int addr_family;

    if (!route || !route->prefix)
        return;

    ret = str2prefix(route->prefix, &p);
    if (ret <= 0) {
        VLOG_ERR("Malformed Dest address=%s", route->prefix);
        return;
    }

    memset(&tmp_key, 0, sizeof(struct zebra_route_key));
    if (strcmp(route->address_family,
               OVSREC_ROUTE_ADDRESS_FAMILY_IPV4) == 0) {
        addr_family = AF_INET;
        tmp_key.prefix.u.ipv4_addr = p.u.prefix4;
    } else if (strcmp(route->address_family,
               OVSREC_ROUTE_ADDRESS_FAMILY_IPV6) == 0) {
        addr_family = AF_INET6;
        tmp_key.prefix.u.ipv6_addr = p.u.prefix6;
    }

    tmp_key.prefix_len = p.prefixlen;

    for (i = 0; i < route->n_nexthops; i++) {
        nexthop = route->nexthops[i];
        if (nexthop) {
            if (nexthop->ip_address) {
                if(addr_family == AF_INET) {
                    inet_pton(AF_INET, nexthop->ip_address,
                              &tmp_key.nexthop.u.ipv4_addr);
                } else if (addr_family == AF_INET6) {
                    inet_pton(AF_INET6, nexthop->ip_address,
                              &tmp_key.nexthop.u.ipv6_addr);
                }
            }

            if (nexthop->ports) {
                strncpy(tmp_key.ifname, nexthop->ports[0]->name,
                        IF_NAMESIZE);
            }

            VLOG_DBG ("Hash insert prefix %s nexthop %s, interface %s",
                        route->prefix,
                        nexthop->ip_address ? nexthop->ip_address : "NONE",
                        tmp_key.ifname[0] ? tmp_key.ifname : "NONE");

            if (VLOG_IS_DBG_ENABLED()) {
                print_key(&tmp_key); /* For debugging. */
            }
            add = hash_get(zebra_route_hash, &tmp_key,
                           zebra_route_hash_alloc);
            assert(add);
        }
    }
}

/* Free hash key memory */
static void
zebra_route_hash_free(struct zebra_route_key *p)
{
    XFREE (MTYPE_TMP, p);
}

/* Free hash table memory */
static void
zebra_route_hash_finish (void)
{
    hash_clean(zebra_route_hash, (void (*) (void *)) zebra_route_hash_free);
    hash_free(zebra_route_hash);
    zebra_route_hash = NULL;
}

/* Free link list data memory */
static void
zebra_route_list_free_data(struct zebra_route_del_data *data)
{
    XFREE (MTYPE_TMP, data);
}

/* Add delated route to list */
static void
zebra_route_list_add_data(struct route_node *rnode, struct rib *rib_p,
                          struct nexthop *nhop)
{
    struct zebra_route_del_data *data;

    data = XCALLOC (MTYPE_TMP, sizeof (struct zebra_route_del_data));
    assert (data);

    data->rnode = rnode;
    data->rib = rib_p;
    data->nexthop = nhop;
    listnode_add(zebra_route_del_list, data);
}

/* Init link list and hash table */
static void
zebra_route_del_init(void)
{
    zebra_route_hash_init();
    zebra_route_del_list = list_new();
    zebra_route_del_list->del = (void (*) (void *)) zebra_route_list_free_data;
}

/* Run through list and call delete for each list route */
static void
zebra_route_del_process(void)
{
    struct listnode *node, *nnode;
    struct zebra_route_del_data *rdata;
    rib_table_info_t *info;
    struct prefix *pprefix;

    for (ALL_LIST_ELEMENTS (zebra_route_del_list, node, nnode, rdata)) {
        if (rdata->rnode && rdata->rib && rdata->nexthop) {
            info = rib_table_info (rdata->rnode->table);
            if (info->safi != SAFI_UNICAST){
                continue ;
            }
            pprefix = &rdata->rnode->p;

            if (pprefix->family == AF_INET) {
                if (rdata->rib->type == ZEBRA_ROUTE_STATIC) {
                    static_delete_ipv4_safi (info->safi, pprefix,
                                             (rdata->nexthop->ifname ?
                                              NULL : &rdata->nexthop->gate.ipv4),
                                             rdata->nexthop->ifname,
                                             rdata->rib->distance,
                                             info->vrf->id);
                } else {
                    rib_delete_ipv4(rdata->rib->type,              /*protocol*/
                                    0,                             /*flags*/
                                    (struct prefix_ipv4 *)pprefix, /*prefix*/
                                    (rdata->nexthop->ifname ?
                                     NULL : &rdata->nexthop->gate.ipv4),/*gate*/
                                    ifname2ifindex(rdata->nexthop->ifname),
                                                                   /* ifindex */
                                    0,                             /*vrf_id*/
                                    info->safi                     /*safi*/
                                    );
                }
#ifdef HAVE_IPV6
            } else if (pprefix->family == AF_INET6) {
                if (rdata->rib->type == ZEBRA_ROUTE_STATIC) {
                    static_delete_ipv6 (pprefix,
                                        (rdata->nexthop->ifname ?
                                                   STATIC_IPV6_IFNAME :
                                                   STATIC_IPV6_GATEWAY),
                                        &rdata->nexthop->gate.ipv6,
                                        rdata->nexthop->ifname,
                                        rdata->rib->distance,
                                        info->vrf->id);
                } else {
                    rib_delete_ipv6(rdata->rib->type,             /*protocol*/
                                    0,                            /*flags*/
                                    (struct prefix_ipv6 *)pprefix,/*prefix*/
                                    (rdata->nexthop->ifname ?
                                     NULL : &rdata->nexthop->gate.ipv4),/*gate*/
                                    ifname2ifindex(rdata->nexthop->ifname),
                                                                  /* ifindex */
                                    0,                            /*vrf_id*/
                                    info->safi                    /*safi*/
                                    );
                }
#endif
            }
        }
    }
}

/* Free hash and link list memory */
static
void zebra_route_del_finish(void) {
    list_free(zebra_route_del_list);
    zebra_route_hash_finish();
}

/* Find routes not in ovsdb and add it to list.
  List is used to delete routes from system*/
static void
zebra_find_ovsdb_deleted_routes(afi_t afi, safi_t safi, u_int32_t id)
{
    struct route_table *table;
    struct route_node *rn;
    struct rib *rib;
    struct nexthop *nexthop;
    struct zebra_route_key rkey;
    char prefix_str[256];
    char nexthop_str[256];

    VLOG_DBG("Walk RIB table to find deleted routes");
    table = vrf_table (afi, safi, id);
    if (!table)
        return;

    for (rn = route_top (table); rn; rn = route_next (rn)) {
        if (!rn) {
            continue;
        }

        RNODE_FOREACH_RIB (rn, rib) {
            if ((rib->type != ZEBRA_ROUTE_STATIC &&
                rib->type != ZEBRA_ROUTE_BGP) ||
                !rib->nexthop)
                continue;

            for (nexthop = rib->nexthop; nexthop; nexthop = nexthop->next) {
                memset(&rkey, 0, sizeof (struct zebra_route_key));
                memset(prefix_str, 0, sizeof(prefix_str));
                memset(nexthop_str, 0, sizeof(nexthop_str));

                if (afi == AFI_IP) {
                    rkey.prefix.u.ipv4_addr = rn->p.u.prefix4;
                    rkey.prefix_len = rn->p.prefixlen;
                    if (nexthop->type == NEXTHOP_TYPE_IPV4) {
                        rkey.nexthop.u.ipv4_addr = nexthop->gate.ipv4;
                        inet_ntop(AF_INET, &nexthop->gate.ipv4,
                                  nexthop_str, sizeof(nexthop_str));
                    }
                } else if (afi == AFI_IP6) {
                    rkey.prefix.u.ipv6_addr = rn->p.u.prefix6;
                    rkey.prefix_len = rn->p.prefixlen;
                    if (nexthop->type == NEXTHOP_TYPE_IPV6) {
                        rkey.nexthop.u.ipv6_addr = nexthop->gate.ipv6;
                        inet_ntop(AF_INET6, &nexthop->gate.ipv6,
                                  nexthop_str, sizeof(nexthop_str));
                    }
                }

                if ((nexthop->type == NEXTHOP_TYPE_IFNAME) ||
                    (nexthop->type == NEXTHOP_TYPE_IPV4_IFNAME) ||
                    (nexthop->type == NEXTHOP_TYPE_IPV6_IFNAME)) {
                        strncpy(rkey.ifname, nexthop->ifname, IF_NAMESIZE);
                }

                if (VLOG_IS_DBG_ENABLED()) {
                    print_key(&rkey); /* For debugging. */
                }

                if (!hash_get(zebra_route_hash, &rkey, NULL)){
                    zebra_route_list_add_data(rn, rib, nexthop);
                    prefix2str(&rn->p, prefix_str, sizeof(prefix_str));
                    VLOG_DBG ("Delete route, prefix %s, nexthop %s, interface %s",
                               prefix_str[0] ? prefix_str : "NONE",
                               nexthop_str[0] ? nexthop_str : "NONE",
                               nexthop->ifname ? nexthop->ifname : "NONE");
                }

            }
        } /* RNODE_FOREACH_RIB */
    }
}

/* Find deleted route in ovsdb and remove from route table */
static void
zebra_route_delete(void)
{
    const struct ovsrec_route *route_row;

    zebra_route_del_init();
    /* Add ovsdb route and nexthop in hash */
    OVSREC_ROUTE_FOR_EACH(route_row, idl) {
        /*
         * We are interested in the routes that are not private.
         */
        if (route_row->protocol_private == NULL ||
            route_row->protocol_private[0] == false) {
            zebra_route_hash_add(route_row);
        }
    }

    zebra_find_ovsdb_deleted_routes(AFI_IP, SAFI_UNICAST, 0);
    zebra_find_ovsdb_deleted_routes(AFI_IP6, SAFI_UNICAST, 0);

    zebra_route_del_process();
    zebra_route_del_finish();
}

static unsigned int
ovsdb_proto_to_zebra_proto (char *from_protocol)
{
    if (!strcmp(from_protocol, OVSREC_ROUTE_FROM_CONNECTED)) {
        return ZEBRA_ROUTE_CONNECT;
    } else if (!strcmp(from_protocol, OVSREC_ROUTE_FROM_STATIC)) {
        return ZEBRA_ROUTE_STATIC;
    } else if (!strcmp(from_protocol, OVSREC_ROUTE_FROM_BGP)) {
        return ZEBRA_ROUTE_BGP;
    } else {
        VLOG_ERR("Unknown protocol. Conversion failed");
        return ZEBRA_ROUTE_MAX;
    }
    return ZEBRA_ROUTE_MAX;
}

static unsigned int
ovsdb_safi_to_zebra_safi (char *safi_str)
{
    if (!strcmp(safi_str, OVSREC_ROUTE_SUB_ADDRESS_FAMILY_UNICAST)) {
        return SAFI_UNICAST;
    } else if (!strcmp(safi_str, OVSREC_ROUTE_SUB_ADDRESS_FAMILY_MULTICAST)) {
        return SAFI_MULTICAST;
    } else if (!strcmp(safi_str, OVSREC_ROUTE_SUB_ADDRESS_FAMILY_VPN)) {
        return SAFI_MPLS_VPN;
    } else {
        return SAFI_MAX;
    }
    return SAFI_MAX;
}

/*
** Function to handle static route add/delete.
*/
static void
zebra_handle_static_route_change (const struct ovsrec_route *route)
{
    const struct ovsrec_nexthop *nexthop;
    struct prefix p;
    struct in_addr gate;
    struct in6_addr ipv6_gate;
    const char *ifname = NULL;
    u_char flag = 0;
    u_char distance;
    safi_t safi = 0;
    u_char type = 0;
    int ipv6_addr_type = 0;
    int ret;

    VLOG_DBG("Rib prefix_str=%s", route->prefix);
    /* Convert the prefix/len */
    ret = str2prefix (route->prefix, &p);
    if (ret <= 0) {
        VLOG_ERR("Malformed Dest address=%s", route->prefix);
        return;
    }

    /* Apply mask for given prefix. */
    apply_mask(&p);

    /* Get Nexthop ip/interface */
    VLOG_DBG("Read nexthop %d", route->n_nexthops);
    nexthop = route->nexthops[0];
    if (nexthop == NULL) {
        VLOG_DBG ("Null next hop");
        return;
    }

    if (route->address_family) {
       VLOG_DBG("address_family %s", route->address_family);
       if (strcmp(route->address_family,
                  OVSREC_ROUTE_ADDRESS_FAMILY_IPV6) == 0) {
           ipv6_addr_type = true;
       }
    }

    if (nexthop->ports) {
        ifname = nexthop->ports[0]->name;
        VLOG_DBG("Rib nexthop ifname=%s", ifname);
        if (ipv6_addr_type) {
            type = STATIC_IPV6_IFNAME;
        }
    } else if (nexthop->ip_address) {
        if (ipv6_addr_type) {
            ret = inet_pton (AF_INET6, nexthop->ip_address, &ipv6_gate);
        } else {
            ret = inet_aton(nexthop->ip_address, &gate);
        }

        if (ret == 1) {
            type = STATIC_IPV6_GATEWAY;
            VLOG_DBG("Rib nexthop ip=%s", nexthop->ip_address);
        } else {
            VLOG_ERR("BAD! Rib nexthop ip=%s", nexthop->ip_address);
            return;
        }
    } else {
        VLOG_DBG("BAD! No nexthop ip or iface");
        return;
    }

    if (route->sub_address_family) {
        VLOG_DBG("Checking sub-address-family=%s", route->sub_address_family);
        if (strcmp(route->sub_address_family,
                   OVSREC_ROUTE_SUB_ADDRESS_FAMILY_UNICAST) == 0) {
            safi = SAFI_UNICAST;
        } else {
            VLOG_DBG("BAD! Not valid sub-address-family=%s",
                      route->sub_address_family);
            return;
        }
    } else {
        safi = SAFI_UNICAST;
    }

    if (route->distance != NULL) {
        distance = route->distance[0];
    } else {
        distance = ZEBRA_STATIC_DISTANCE_DEFAULT;
    }

    if (ipv6_addr_type) {
#ifdef HAVE_IPV6
       static_add_ipv6 (&p, type, &ipv6_gate, ifname, flag, distance, 0, route);
#endif
    } else {
       static_add_ipv4_safi (safi, &p, ifname ? NULL : &gate, ifname,
                             flag, distance, 0, route);
    }
    return;
}

/*
 * This function is called when a route is added/modified.
 * Determine the final action to take based on the current state
 * of the route
 */
static int
zebra_route_action_calculate (const struct ovsrec_route *route)
{
    /*
     * Logic:
     * If protocol_private is updated to TRUE, delete the route
     * If protocol_private is updated to FALSE, add the route
     * If public route inserted, add the route
     * If public row is modified, add the route
     * If private route is inserted, ignore
     * If private row is modified, ignore
     */
    if (OVSREC_IDL_IS_ROW_MODIFIED(route, idl_seqno)) {
        if (OVSREC_IDL_IS_COLUMN_MODIFIED(ovsrec_route_col_protocol_private,
                                          idl_seqno)) {
            if ((route->protocol_private != NULL) &&
                (route->protocol_private[0] == true)) {
                /* protocol_private converted to true */
                return OVSDB_ROUTE_DELETE;
            } else {
                /* protocol_private converted to false */
                return OVSDB_ROUTE_ADD;
            }
        } else {
            /* route column (not protocol_private) modified */
            if ((route->protocol_private != NULL) &&
                (route->protocol_private[0] == true)) {
                return OVSDB_ROUTE_IGNORE;
            } else {
                return OVSDB_ROUTE_ADD;
            }
        }
    } else if (OVSREC_IDL_IS_ROW_INSERTED(route, idl_seqno)) {
        if ((route->protocol_private == NULL) ||
            (route->protocol_private[0] == false)) {
            return OVSDB_ROUTE_ADD;
        } else {
            return OVSDB_ROUTE_IGNORE;
        }
    }
    return OVSDB_ROUTE_MIN;
}

/*
 * This function handles route update from routing protocols
 */
static void
zebra_handle_proto_route_change (const struct ovsrec_route *route,
                                 int from)
{
    int safi = ovsdb_safi_to_zebra_safi(route->sub_address_family);
    int ret;
    struct prefix p;
    bool is_ipv6 = false;

    VLOG_DBG("Route change for %s", route->prefix);
    ret = str2prefix (route->prefix, &p);
    if (ret <= 0)
    {
        VLOG_ERR("Malformed Dest address=%s", route->prefix);
        return;
    }
    apply_mask(&p);

    /*
     * Invoke internal zebra functions to add this route to RIB
     */
    if (!strcmp(route->address_family, OVSREC_ROUTE_ADDRESS_FAMILY_IPV4)) {
        /* This is a IPv4 route update */
        switch (zebra_route_action_calculate(route)) {
        case OVSDB_ROUTE_ADD:
            {
                VLOG_DBG("Got ipv4 add route");
                zebra_add_route(is_ipv6, &p, from, safi, route);
            }
            break;
        case OVSDB_ROUTE_DELETE:
            /* Delete is handled in process_delete */
            break;
        case OVSDB_ROUTE_IGNORE:
        default:
            break;
        }

#ifdef HAVE_IPV6
    } else if (!strcmp(route->address_family, OVSREC_ROUTE_ADDRESS_FAMILY_IPV6)) {
        is_ipv6 = true;
        /* This is a IPv6 route update */
        switch (zebra_route_action_calculate(route)) {
        case OVSDB_ROUTE_ADD:
            {
                /* Handle v6 single or multiple nexthop routes. */
                VLOG_DBG("Got ipv6 add route");
                zebra_add_route(is_ipv6, &p, from, safi, route);
            }
            break;
        case OVSDB_ROUTE_DELETE:
            /* Delete is handled in process_delete */
            break;
        case OVSDB_ROUTE_IGNORE:
        default:
            break;
        }
#endif
    }
}

/*
 * A route has been modified or added. Update the local RIB structures
 * accordingly.
 */
static void
zebra_handle_route_change(const struct ovsrec_route *route)
{
    int from_protocol = ovsdb_proto_to_zebra_proto(route->from);
    /*
     * OVSDB stores the almost everything as a string. Zebra uses integers.
     * If we convert the string to integer initially, we can avoid multiple
     * string operations further.
     */
    switch (from_protocol) {
    case ZEBRA_ROUTE_CONNECT:
        VLOG_DBG("Adding a connected route for prefix %s\n",route->prefix);
        /* This is a directly connected route */
        /* TBD */
        break;
    case ZEBRA_ROUTE_STATIC:
        VLOG_DBG("Adding a static route for prefix %s\n",route->prefix);
        /* This is a static route */
        zebra_handle_static_route_change(route);
        break;
    case ZEBRA_ROUTE_BGP:
        VLOG_DBG("Adding a Protocol route for prefix %s protocol %s\n",
                  route->prefix, route->from);
        /* This is a protocol route */
        zebra_handle_proto_route_change(route, from_protocol);
        break;
    case ZEBRA_ROUTE_MAX:
    default:
        VLOG_ERR("Unknown protocol");
        return;
    }
}

/* route add/delete in ovsdb */
static void
zebra_apply_route_changes (void)
{
    const struct ovsrec_route *route_first;
    const struct ovsrec_route *route_row;
    const struct ovsrec_nexthop *nh_row;

    route_first = ovsrec_route_first(idl);
    if (route_first == NULL)
    {
        VLOG_DBG("No rows in ROUTE table");
        /* Possible last row gets deleted */
        zebra_route_delete();
        return;
    }

    if ( (!OVSREC_IDL_ANY_TABLE_ROWS_MODIFIED(route_first, idl_seqno)) &&
       (!OVSREC_IDL_ANY_TABLE_ROWS_DELETED(route_first, idl_seqno))  &&
       (!OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(route_first, idl_seqno)) )
    {
        VLOG_DBG("No modification in ROUTE table");
        return;
    }

    if ( (OVSREC_IDL_ANY_TABLE_ROWS_MODIFIED(route_first, idl_seqno)) ||
       (OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(route_first, idl_seqno)) )
    {
        VLOG_DBG("Some modification or inserts in ROUTE table");

        OVSREC_ROUTE_FOR_EACH(route_row, idl)
        {
            nh_row = route_row->nexthops[0];
            if (nh_row == NULL)
            {
                VLOG_DBG ("Null next hop");
                continue;
            }

            if ( (OVSREC_IDL_IS_ROW_INSERTED(route_row, idl_seqno)) ||
                 (OVSREC_IDL_IS_ROW_MODIFIED(route_row, idl_seqno)) ||
                 (is_route_nh_rows_modified(route_row)) )
            {
                VLOG_DBG("Row modification or inserts in ROUTE table");
                zebra_handle_route_change(route_row);
            }
        }
    }

    if ( (OVSREC_IDL_ANY_TABLE_ROWS_DELETED(route_first, idl_seqno) ) ||
       ( is_rib_nh_rows_deleted( route_first ) ) )
    {
        VLOG_DBG("Deletes in RIB table");
        zebra_route_delete();
    }
}

/* Check if any changes are there to the idl and update
 * the local structures accordingly.
 */
static void
zebra_reconfigure(struct ovsdb_idl *idl)
{
    unsigned int new_idl_seqno = ovsdb_idl_get_seqno(idl);
    enum ovsdb_idl_txn_status status;
    struct ovsdb_idl_txn *txn = NULL;
    COVERAGE_INC(zebra_ovsdb_cnt);

    if (new_idl_seqno == idl_seqno){
        VLOG_DBG("No config change for zebra in ovs\n");
        return;
    }

    /* Create txn for any IDL updates */
    txn = ovsdb_idl_txn_create(idl);
    if (!txn) {
        VLOG_ERR("%s: Transaction creation failed" , __func__);
    }

    /* Apply all ovsdb notifications */
    zebra_apply_route_changes();

    /* Submit any modifications in IDl to DB */
    zebra_commit_txn(&txn, &zebra_db_updates);

    /* update the seq. number */
    idl_seqno = new_idl_seqno;
}

/* Wrapper function that checks for idl updates and reconfigures the daemon
 */
static void
zebra_ovs_run (void)
{
    ovsdb_idl_run(idl);
    unixctl_server_run(appctl);

    if (ovsdb_idl_is_lock_contended(idl)) {
        static struct vlog_rate_limit rl = VLOG_RATE_LIMIT_INIT(1, 1);

        VLOG_ERR_RL(&rl, "another zebra process is running, "
                    "disabling this process until it goes away");
        return;
    } else if (!ovsdb_idl_has_lock(idl)) {
        return;
    }

    zebra_chk_for_system_configured();

    if (system_configured) {
        zebra_reconfigure(idl);

        daemonize_complete();
        vlog_enable_async();
        VLOG_INFO_ONCE("%s (Halon zebra) %s", program_name, VERSION);
    }
}

static void
zebra_ovs_wait (void)
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
zovs_read_cb (struct thread *thread)
{
    zebra_ovsdb_t *zovs_g;
    if (!thread) {
        VLOG_ERR("NULL thread in read cb function\n");
        return -1;
    }
    zovs_g = THREAD_ARG(thread);
    if (!zovs_g) {
        VLOG_ERR("NULL args in read cb function\n");
        return -1;
    }

    zovs_g->read_cb_count++;

    zebra_ovs_clear_fds();
    zebra_ovs_run();
    zebra_ovs_wait();

    if (0 != zebra_ovspoll_enqueue(zovs_g)) {
        /*
         * Could not enqueue the events.
         * Retry in 1 sec
         */
        thread_add_timer(zovs_g->master,
                         zovs_read_cb, zovs_g, 1);
    }
    return 1;
}

/* Add the list of OVS poll fd to the master thread of the daemon
 */
static int
zebra_ovspoll_enqueue (zebra_ovsdb_t *zovs_g)
{
    struct poll_loop *loop = poll_loop();
    struct poll_node *node;
    long int timeout;
    int retval = -1;

    /* Populate with all the fds events. */
    HMAP_FOR_EACH (node, hmap_node, &loop->poll_nodes) {
        thread_add_read(zovs_g->master,
                                    zovs_read_cb,
                                    zovs_g, node->pollfd.fd);
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

        thread_add_timer(zovs_g->master,
                                     zovs_read_cb, zovs_g,
                                     timeout);
    }

    return retval;
}

/* Initialize and integrate the ovs poll loop with the daemon */
void zebra_ovsdb_init_poll_loop (struct zebra_t *zebrad)
{
    if (!glob_zebra_ovs.enabled) {
        VLOG_ERR("OVS not enabled for zebra. Return\n");
        return;
    }
    glob_zebra_ovs.master = zebrad->master;

    zebra_ovs_clear_fds();
    zebra_ovs_run();
    zebra_ovs_wait();
    zebra_ovspoll_enqueue(&glob_zebra_ovs);
}

static void
ovsdb_exit(void)
{
    ovsdb_idl_destroy(idl);
}

/* When the daemon is ready to shut, delete the idl cache
 * This happens with the ovs-appctl exit command.
 */
void zebra_ovsdb_exit(void)
{
    ovsdb_exit();
}

static int
zebra_ovs_update_selected_route (struct ovsrec_route *ovs_route,
                                 bool *selected)
{
    if (ovs_route) {
        /*
         * Found the route entry. Update the selected column.
         * ECMP: Update only if it is different.
         */
        VLOG_DBG("Updating selected flag for route %s", ovs_route->prefix);
        if( (ovs_route->selected != NULL) &&
            (ovs_route->selected[0] == *selected) )
        {
            VLOG_DBG("No change in selected flag");
            return 0;
        }

        /*
         * Update the selected bit, and mark it to commit into DB.
         */
        ovsrec_route_set_selected(ovs_route, selected, 1);
        rib_kernel_updates = true;
        VLOG_DBG("Route update successful");

    }
    return 0;
}

/*
 * When zebra is ready to update the kernel with the selected route,
 * update the DB with the same information. This function will take care
 * of updating the DB
 */
int
zebra_update_selected_route_to_db (struct route_node *rn, struct rib *route,
                                   int action)
{
    char prefix_str[256];
    struct ovsrec_route *ovs_route = NULL;
    bool selected = (action == ZEBRA_RT_INSTALL) ? true:false;
    struct prefix *p = NULL;
    rib_table_info_t *info = NULL;

    /*
     * Fetch the rib entry from the DB and update the selected field based
     * on action:
     * action == ZEBRA_RT_INSTALL => selected = 1
     * action == ZEBRA_RT_UNINSTALL => selected = 0
     *
     * If the 'route' has a valid 'ovsdb_route_row_ptr' pointer,
     * then reference the 'ovsrec_route' structure directly from
     * 'ovsdb_route_row_ptr' pointer. Otherwise iterate through the
     * OVSDB route to find out the relevant 'ovsrec_route' structure.
     */
    if (route && (route->ovsdb_route_row_ptr)) {

        ovs_route = (struct ovsrec_route *)(route->ovsdb_route_row_ptr);

        VLOG_DBG("Cached OVSDB Route Entry: Prefix %s family %s "
                 "from %s priv %p", ovs_route->prefix,
                 ovs_route->address_family, ovs_route->from,
                 ovs_route->protocol_private);
    } else {

        p = &rn->p;
        info = rib_table_info(rn->table);
        memset(prefix_str, 0, sizeof(prefix_str));
        prefix2str(p, prefix_str, sizeof(prefix_str));

        VLOG_DBG("Prefix %s Family %d\n",prefix_str, PREFIX_FAMILY(p));

        switch (PREFIX_FAMILY (p)) {
            case AF_INET:

                VLOG_DBG("Walk the OVSDB route DB to find the relevant row for"
                         " prefix %s\n", prefix_str);

                OVSREC_ROUTE_FOR_EACH(ovs_route, idl) {
                    /*
                     * HALON_TODO: Need to add support to check vrf
                     */
                    VLOG_DBG("DB Entry: Prefix %s family %s from %s priv %p",
                             ovs_route->prefix, ovs_route->address_family,
                             ovs_route->from, ovs_route->protocol_private);

                    if (!strcmp(ovs_route->address_family,
                                    OVSREC_ROUTE_ADDRESS_FAMILY_IPV4)) {
                        if (!strcmp(ovs_route->prefix, prefix_str)) {
                            if (route->type ==
                                    ovsdb_proto_to_zebra_proto(ovs_route->from)) {
                                if (info->safi ==
                                    ovsdb_safi_to_zebra_safi(
                                                ovs_route->sub_address_family)) {
                                    break;
                                }
                            }
                        }
                    }
                }
                break;
#ifdef HAVE_IPV6
            case AF_INET6:

                VLOG_DBG("Walk the OVSDB route DB to find the relevant row for"
                         " prefix %s\n", prefix_str);

                OVSREC_ROUTE_FOR_EACH(ovs_route, idl) {
                    /*
                     * HALON_TODO: Need to add support to check vrf
                     */
                    VLOG_DBG("DB Entry: Prefix %s family %s from %s priv %p",
                             ovs_route->prefix, ovs_route->address_family,
                             ovs_route->from, ovs_route->protocol_private);

                    if (!strcmp(ovs_route->address_family,
                                        OVSREC_ROUTE_ADDRESS_FAMILY_IPV6)) {
                        if (!strcmp(ovs_route->prefix, prefix_str)) {
                            if (route->type ==
                                    ovsdb_proto_to_zebra_proto(ovs_route->from)) {
                                if (info->safi ==
                                    ovsdb_safi_to_zebra_safi(
                                                    ovs_route->sub_address_family)) {
                                    break;
                                }
                            }
                        }
                    }
                }
                break;
#endif
            default:
            /* Unsupported protocol family! */
            VLOG_ERR("Unsupported protocol in route update");
            return 0;
        }
    }

    if (ovs_route) {

        /*
         * We should not be checking for protcol_private here The fact that zebra
         * has it, means that this is no longer private! Just blindly update.
         * We will take care of only allowing non private routes to zebra.
         */
        if (ovs_route->protocol_private == NULL ||
            ovs_route->protocol_private[0] == false) {

            VLOG_DBG("Updating the selected flag for the non-private routes");
            zebra_ovs_update_selected_route(ovs_route, &selected);
        }
    }
    return 0;
}

/*
 * Function to add ipv4/6 route from protocols, with one or multiple nexthops.
 */
int
zebra_add_route(bool is_ipv6, struct prefix *p, int type, safi_t safi,
                const struct ovsrec_route *route)
{
    struct rib *rib;
    int flags = 0;
    u_int32_t vrf_id = 0;
    struct ovsrec_nexthop *idl_nexthop;
    struct in_addr ipv4_dest_addr;
    struct in6_addr ipv6_dest_addr;
    int count;
    int rc = 1;

    /* Allocate new rib. */
    rib = XCALLOC (MTYPE_RIB, sizeof (struct rib));

    /* Type, flags, nexthop_num. */
    rib->type = type;
    rib->flags = flags;
    rib->uptime = time (NULL);
    rib->nexthop_num = 0; /* Start with zero */
    rib->ovsdb_route_row_ptr = route;

    VLOG_DBG("Going through %d next-hops", route->n_nexthops);
    for (count = 0; count < route->n_nexthops; count++) {
        idl_nexthop = route->nexthops[count];

        /* If valid and selected nexthop */
        if ( (idl_nexthop == NULL) ||
             ( (idl_nexthop->selected != NULL) &&
               (idl_nexthop->selected[0] != true) ) ) {
            continue;
        }

        /* If next hop is port */
        if(idl_nexthop->ports != NULL) {
            VLOG_DBG("Processing %d-next-hop %s", count,
                       idl_nexthop->ports[0]->name);
            nexthop_ifname_add(rib, idl_nexthop->ports[0]->name);
        } else {
            memset(&ipv4_dest_addr, 0, sizeof(struct in_addr));
            memset(&ipv6_dest_addr, 0, sizeof(struct in6_addr));
            /* Check if ipv4 or ipv6 */
            if (inet_pton(AF_INET, idl_nexthop->ip_address,
                          &ipv4_dest_addr) != 1) {
                 if (inet_pton(AF_INET6, idl_nexthop->ip_address,
                               &ipv6_dest_addr) != 1) {
                     VLOG_DBG("Invalid next-hop ip %s",idl_nexthop->ip_address);
                     continue;
                 } else {
                     VLOG_DBG("Processing %d-next-hop ipv6 %s",
                               count, idl_nexthop->ip_address);
                     nexthop_ipv6_add(rib, &ipv6_dest_addr);
                 }
            } else {
                VLOG_DBG("Processing ipv4 %d-next-hop ipv4 %s",
                           count, idl_nexthop->ip_address);
                nexthop_ipv4_add(rib, &ipv4_dest_addr, NULL);
            }
        }
    }

    /* Distance. */
    if (route->distance != NULL) {
        rib->distance = route->distance[0];
    } else {
        rib->distance = 0;
    }

    /* OPS TODO: What about weight in Nexthop, metric and weight are same?? */
    /* Metric. */
    if (route->metric != NULL) {
        rib->metric = route->metric[0];
    } else {
        rib->metric = 0;
    }

    /* Table */
    rib->table = vrf_id;

    if(is_ipv6) {
        /* Set rc, incase of no ipv6 */
#ifdef HAVE_IPV6
        rc = rib_add_ipv6_multipath((struct prefix_ipv6 *)p, rib, safi);
#endif
    } else {
        rc = rib_add_ipv4_multipath((struct prefix_ipv4 *)p, rib, safi);
    }

    return rc;
}

/*
** Function to create transaction for submitting rib updates to DB.
*/
int
zebra_create_rib_update_txn(void)
{
    rib_txn = ovsdb_idl_txn_create(idl);
    if (!rib_txn) {
        VLOG_ERR("%s: Transaction creation failed" , __func__);
        rib_txn = NULL;
    }
}

/*
** Function to commit the idl transaction if there are any updates to be
** submitted to DB.
*/
int
zebra_commit_txn(struct ovsdb_idl_txn **txn, bool *any_updates)
{
    enum ovsdb_idl_txn_status status;

    /* Commit txn if any updates to be submitted to DB */
    if (*any_updates) {
        if (*txn) {
            status = ovsdb_idl_txn_commit(*txn);
            if (!((status == TXN_SUCCESS) || (status == TXN_UNCHANGED)
                      || (status == TXN_INCOMPLETE))) {
                /*
                 * HALON_TODO: In case of commit failure, retry.
                 */
                VLOG_ERR("Route update failed. The transaction error is %s",
                         ovsdb_idl_txn_status_to_string(status));
            }
        }
    }

    /* Finally in any case destory */
    if (*txn) {
        ovsdb_idl_txn_destroy(*txn);
    }
    *txn = NULL;
    *any_updates = false;
}

/*
** Function to commit any rib kernel update to the DB.
*/
int
zebra_commit_rib_update_txn(void)
{
    return (zebra_commit_txn(&rib_txn, &rib_kernel_updates));
}
