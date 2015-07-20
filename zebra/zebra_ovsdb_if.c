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

boolean exiting = false;

static int zebra_ovspoll_enqueue (zebra_ovsdb_t *zovs_g);
static int zovs_read_cb (struct thread *thread);

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

    /* Register for NextHop table */
    ovsdb_idl_add_table(idl, &ovsrec_table_nexthop);
    ovsdb_idl_add_column(idl, &ovsrec_nexthop_col_ip_address);
    ovsdb_idl_add_column(idl, &ovsrec_nexthop_col_ports);
    ovsdb_idl_add_column(idl, &ovsrec_nexthop_col_status);

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

static void
zebra_set_hostname (char *hostname)
{
    if (host.name)
        XFREE (MTYPE_HOST, host.name);

    host.name = XSTRDUP(MTYPE_HOST, hostname);
}

static void
zebra_apply_global_changes (void)
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
        zebra_set_hostname(ovs->hostname);
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

bool is_route_nh_rows_deleted(const struct ovsrec_route *route)
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

/* static route. */
static void
zebra_handle_route_change(const struct ovsrec_route *route, int action)
{
  const struct ovsrec_nexthop *nexthop;
  struct prefix p;
  struct in_addr gate;
  struct in6_addr ipv6_gate;
  const char *ifname = NULL;
  char prefix_str[256];
  u_char flag = 0;
  u_char distance;
  safi_t safi = 0;
  u_char type = 0;
  int ipv6_addr_type = 0;
  int ret;

  VLOG_INFO("Rib prefix_str=%s len=%d", route->prefix);
  memset(prefix_str, 0, sizeof(prefix_str));
  snprintf(prefix_str, 255, "%s", route->prefix);

  VLOG_INFO("Rib prefix_str=%s", prefix_str);

  /* Convert the prefix/len */
  ret = str2prefix (prefix_str, &p);
  if (ret <= 0)
  {
      VLOG_INFO ("Malformed Dest address=%s", prefix_str);
      return;
  }

  /* Apply mask for given prefix. */
  VLOG_INFO("Applying Mask");
  apply_mask (&p);

  /* Get Nexthop ip/interface */
  VLOG_INFO("Read nexthop %d", route->n_nexthops);
  nexthop = route->nexthops[0];
  if (nexthop == NULL)
  {
      VLOG_INFO ("Null next hop");
      return;
  }

  VLOG_INFO("!!!!***address_family %s", route->address_family);
  if (strcmp(route->address_family, OVSREC_ROUTE_ADDRESS_FAMILY_IPV6) == 0)
  {
      ipv6_addr_type = 1;
  }

  if (nexthop->ports)
  {
      ifname = nexthop->ports;
      VLOG_INFO("Rib nexthop ifname=%s", ifname);
      if (ipv6_addr_type)
      {
          type = STATIC_IPV6_IFNAME;
      }
  }
  else if (nexthop->ip_address)
  {
      VLOG_INFO("Checking nexthop ip");
      if (ipv6_addr_type)
      {
          ret = inet_pton (AF_INET6, nexthop->ip_address, &ipv6_gate);
      }
      else
      {
          ret = inet_aton(nexthop->ip_address, &gate);
      }

      if (ret == 1)
      {
	  type = STATIC_IPV6_GATEWAY;
          VLOG_INFO("Rib nexthop ip=%s", nexthop->ip_address);
      }
      else
      {
          VLOG_INFO("BAD! Rib nexthop ip=%s", nexthop->ip_address);
          return;
      }
  }
  else
  {
      VLOG_INFO("BAD! No nexthop ip or iface");
      return;
  }

  VLOG_INFO("Checking sub-address-family=%s", route->sub_address_family);
  if (strcmp(route->sub_address_family,
             OVSREC_ROUTE_SUB_ADDRESS_FAMILY_UNICAST) == 0)
  {
      safi = SAFI_UNICAST;
  }
  else
  {
      VLOG_INFO("BAD! Not valid sub-address-family=%s",
                route->sub_address_family);
      return;
  }

  distance = route->distance;
  if (action)
  {
      VLOG_INFO("Calling add .....");
      if (ipv6_addr_type)
      {
          static_add_ipv6 (&p, type, &ipv6_gate, ifname, flag, distance, 0);
      }
      else
      {
          static_add_ipv4_safi (safi, &p, ifname ? NULL : &gate, ifname,
                                flag, distance, 0);
      }
  }
  else
  {
      VLOG_INFO("Calling delete .....");
      if (ipv6_addr_type)
      {
          static_delete_ipv6 (&p, type, &ipv6_gate, ifname, distance, 0);
      }
      else
      {
          static_delete_ipv4_safi (safi, &p, ifname ? NULL : &gate, ifname,
                               distance, 0);
      }
  }

  return;
}

static void
zebra_apply_route_changes (void)
{
    const struct ovsrec_route *route_first;

    VLOG_INFO("In zebra_apply_route_changes");
    route_first = ovsrec_route_first(idl);
    if (route_first == NULL)
    {
        VLOG_INFO("No rows in ROUTE table");
        return;
    }

    if ( (!OVSREC_IDL_ANY_TABLE_ROWS_MODIFIED(route_first, idl_seqno)) &&
       (!OVSREC_IDL_ANY_TABLE_ROWS_DELETED(route_first, idl_seqno))  &&
       (!OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(route_first, idl_seqno)) )
    {
        VLOG_INFO("No modification in ROUTE table");
        return;
    }

    if ( (OVSREC_IDL_ANY_TABLE_ROWS_MODIFIED(route_first, idl_seqno)) &&
       (OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(route_first, idl_seqno)) )
    {
        const struct ovsrec_route *route_row;
        const struct ovsrec_nexthop *nh_row;
        VLOG_INFO("Some modification or inserts in ROUTE table");
        OVSREC_ROUTE_FOR_EACH(route_row, idl)
        {
            nh_row = route_row->nexthops[0];
            if (nh_row == NULL)
            {
                VLOG_INFO ("Null next hop");
                continue;
            }

            if ( (OVSREC_IDL_IS_ROW_INSERTED(route_row, idl_seqno)) ||
                 (OVSREC_IDL_IS_ROW_MODIFIED(route_row, idl_seqno)) ||
                 (is_route_nh_rows_modified(route_row)) )
            {
                VLOG_INFO("Row modification or inserts in ROUTE table");
                zebra_handle_route_change(route_row, 1);
            }
        }
    }

    if ( (OVSREC_IDL_ANY_TABLE_ROWS_DELETED(route_first, idl_seqno) ) ||
       ( is_route_nh_rows_deleted( route_first ) ) )
    {
        VLOG_INFO("Some deletes in ROUTE table");
    }
}

/* Check if any changes are there to the idl and update
 * the local structures accordingly.
 */
static void
zebra_reconfigure(struct ovsdb_idl *idl)
{
    unsigned int new_idl_seqno = ovsdb_idl_get_seqno(idl);
    COVERAGE_INC(zebra_ovsdb_cnt);

    if (new_idl_seqno == idl_seqno){
        VLOG_DBG("No config change for zebra in ovs\n");
        return;
    }

    /* Apply the changes */
    zebra_apply_global_changes();

    zebra_apply_route_changes();

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
