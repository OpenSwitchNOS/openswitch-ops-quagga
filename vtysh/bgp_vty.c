/* BGP CLI implementation with Halon vtysh.
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
 * File: bgp_vty.c
 *
 * Purpose: This file contains implementation of all BGP related CLI commands.
 */

#include <stdio.h>
#include <sys/un.h>
#include <setjmp.h>
#include <sys/wait.h>
#include <sys/resource.h>
#include <sys/stat.h>

#include <readline/readline.h>
#include <readline/history.h>

#include <lib/version.h>
#include "getopt.h"
#include "memory.h"
#include "command.h"
#include "vtysh/vtysh.h"
#include "vtysh/vtysh_user.h"
#include "vswitch-idl.h"
#include "ovsdb-idl.h"
#include "log.h"
#include "bgpd/bgp_vty.h"
#include "smap.h"
#include "openvswitch/vlog.h"
#include "openhalon-idl.h"
#include "util.h"

extern struct ovsdb_idl *idl;

int bgp_router_set_asn(int64_t asn);

/* BGP Information flags taken from bgp_route.h
 * TODO: Remove this duplicate declaration. Need to separate 
 * these flags from bgp_route.h
 */
#define BGP_INFO_IGP_CHANGED    (1 << 0)
#define BGP_INFO_DAMPED         (1 << 1)
#define BGP_INFO_HISTORY        (1 << 2)
#define BGP_INFO_SELECTED       (1 << 3)
#define BGP_INFO_VALID          (1 << 4)
#define BGP_INFO_ATTR_CHANGED   (1 << 5)
#define BGP_INFO_DMED_CHECK     (1 << 6)
#define BGP_INFO_DMED_SELECTED  (1 << 7)
#define BGP_INFO_STALE          (1 << 8)
#define BGP_INFO_REMOVED        (1 << 9)
#define BGP_INFO_COUNTED        (1 << 10)
#define BGP_INFO_MULTIPATH      (1 << 11)
#define BGP_INFO_MULTIPATH_CHG  (1 << 12)

#define BGP_SHOW_SCODE_HEADER "Status codes: s suppressed, d damped, "\
                              "h history, * valid, > best, = multipath,%s"\
                              "i internal, r RIB-failure, S Stale, R Removed%s"
#define BGP_SHOW_OCODE_HEADER "Origin codes: i - IGP, e - EGP, ? - incomplete%s%s"
#define BGP_SHOW_HEADER       "Network          Next Hop            Metric LocPrf Weight Path%s"
VLOG_DEFINE_THIS_MODULE(bgp_vty);

static void
print_route_status(struct vty *vty, int64_t flags)
{
  /* Route status display. */
  if (flags & BGP_INFO_REMOVED)
    vty_out (vty, "R");
  else if (flags & BGP_INFO_STALE)
    vty_out (vty, "S");
/*else if (binfo->extra && binfo->extra->suppress)
  vty_out (vty, "s");*/
  else if (!(flags & BGP_INFO_HISTORY))
    vty_out (vty, "*");
  else
    vty_out (vty, " ");

  /* Selected */
  if (flags & BGP_INFO_HISTORY)
    vty_out (vty, "h");
  else if (flags & BGP_INFO_DAMPED)
    vty_out (vty, "d");
  else if (flags & BGP_INFO_SELECTED)
    vty_out (vty, ">");
  else if (flags & BGP_INFO_MULTIPATH)
    vty_out (vty, "=");
  else
    vty_out (vty, " ");

  /* Internal route. TODO */
  /*
    if ((binfo->peer->as) && (binfo->peer->as == binfo->peer->local_as))
      vty_out (vty, "i");
    else
    vty_out (vty, " "); */
}

/* Function to print route status code */
static void show_routes (struct vty *vty)
{
  const struct ovsrec_rib *ribRow = NULL;
  int ii;

  // Read RIB flags column from RIB table
  OVSREC_RIB_FOR_EACH(ribRow, idl) {
    if (!ribRow)
      continue;
    print_route_status(vty, ribRow->flags);
    if (ribRow->prefix) {
      char str[17] ;
      int len = 0;
      len = snprintf(str, sizeof(str), " %s/%d", ribRow->prefix, ribRow->prefix_len);
      vty_out(vty, "%s", str);
      if (len < 18)
	vty_out (vty, "%*s", 18-len, " ");

      // nexthop
      if (!strcmp(ribRow->address_family, OVSREC_RIB_ADDRESS_FAMILY_IPV4)) {
	if (ribRow->n_nexthop_list) {
	  // Get the nexthop list
	  //VLOG_INFO("No. of next hops : %d", ribRow->n_nexthop_list);
	  const struct ovsdb_datum *datum = NULL;
	  datum = ovsrec_rib_get_nexthop_list(ribRow, OVSDB_TYPE_STRING);
	  for (ii = 0; ii < ribRow->n_nexthop_list; ii++) {
	    vty_out (vty, "%-16s", datum->keys[ii].string);
	  }
	} else {
	  vty_out (vty, "%-16s", " ");
	  syslog(LOG_DEBUG, "%s:No next hops for this route\n", __FUNCTION__);
	} // if 'ribRow->n_nexthop_list'
	
      } else {
	// TODO ipv6
	VLOG_INFO("Address family not supported\n");
      }
      vty_out (vty, "%10d", ribRow->metric);
      // TODO weight, local pref, aspath
      vty_out (vty, "%7d", 0);
      vty_out (vty, "%7d ", 0);
      vty_out(vty, "%s", " ");
      // print origin
      if (ribRow->from_protocol)
	vty_out(vty, "%s", ribRow->from_protocol);
      vty_out (vty, VTY_NEWLINE);
    }

  }
}

DEFUN(vtysh_show_ip_bgp,
      vtysh_show_ip_bgp_cmd,
      "show ip bgp",
      SHOW_STR
      IP_STR
      BGP_STR)
{

  // TODO
  const struct ovsrec_bgp_router *bgpRow = NULL;
  ovsdb_idl_run(idl);
  ovsdb_idl_wait(idl);
  
  vty_out (vty, "BGP table version is 0\n", VTY_NEWLINE);
  vty_out (vty, BGP_SHOW_SCODE_HEADER, VTY_NEWLINE, VTY_NEWLINE);
  vty_out (vty, BGP_SHOW_OCODE_HEADER, VTY_NEWLINE, VTY_NEWLINE);
  
  OVSREC_BGP_ROUTER_FOR_EACH(bgpRow, idl) {
    if (!bgpRow) {
      vty_out(vty, "No bgp instance configured");
      continue;
    }
    char *id = bgpRow->router_id;
    if (id) {
      vty_out (vty, "Local router-id %s\n", id); 
    } else {
      vty_out (vty, "Router-id not configured");
    }
  }
  vty_out (vty, BGP_SHOW_HEADER, VTY_NEWLINE);
  show_routes(vty);
  return CMD_SUCCESS;
}

/* Installing command for "router bgp <asn>" */
DEFUN(cli_router_bgp,
      router_bgp_cmd,
      "router bgp " CMD_AS_RANGE,
      ROUTER_STR
      BGP_STR
      AS_STR)
{
  return bgp_router_set_asn(atoi(argv[0]));
}

int
bgp_router_set_asn(int64_t asn)
{
    struct ovsrec_bgp_router *bgp_router_row = NULL;
    struct ovsrec_bgp_router **bgp_routers_list;
    const struct ovsrec_vrf *vrf_row = NULL;
    static struct ovsdb_idl_txn *bgp_router_txn=NULL;
    enum ovsdb_idl_txn_status status;
    bool vrf_row_found=0;
    int ret_status = 0;
    size_t i=0;

    ovsdb_idl_run(idl);

    if(!bgp_router_txn) {
         bgp_router_txn = ovsdb_idl_txn_create(idl);
         if (bgp_router_txn == NULL) {
             VLOG_ERR("Transaction creation failed");
             return TXN_ERROR;
         }

        vrf_row = ovsrec_vrf_first(idl);
        if (vrf_row == NULL) {
            VLOG_INFO("No VRF configured! Please configure it using"
                      " \"ovs-vsctl add-vrf <vrf-name>\" or \"vrf VRF_NAME\"");
            return -1;
        }
        else {
            vrf_row_found = 1;
#if 0
            /* TODO HALON: Later when we have multiple vrf's and user enters one */
            OVSREC_VRF_FOR_EACH(vrf_row, idl) {
                if (!strcmp(vrf_row->name, vrf_name) {
                    VLOG_INFO("VRF row found! Adding reference to BGP_Router table");
                    break;
                }
            }
#endif
        }
        if(vrf_row_found) {
            bgp_router_row = ovsrec_bgp_router_first(idl);
                if (bgp_router_row == NULL) {
                    /* Create a new row with given asn in bgp router table */
                    bgp_router_row = ovsrec_bgp_router_insert(bgp_router_txn);
                    /* Insert BGP_router table reference in VRF table */
                    ovsrec_vrf_set_bgp_routers(vrf_row, &bgp_router_row,
                                               vrf_row->n_bgp_routers + 1);
                    /* Set the asn column in the BGP_Router table */
                    ovsrec_bgp_router_set_asn(bgp_router_row,asn);
                }
                else {
                    bgp_router_row = NULL;
                    OVSREC_BGP_ROUTER_FOR_EACH(bgp_router_row,idl) {
                        if (bgp_router_row->asn==asn) {
                            VLOG_DBG("Row exists for given asn = %d",
                                bgp_router_row->asn);
                            break;
                        }
                        else {
                            /* Create a new row with given asn in bgp router table */
                            bgp_router_row = ovsrec_bgp_router_insert(bgp_router_txn);
                            /* Insert BGP_router table reference in VRF table */
                            bgp_routers_list = xmalloc(sizeof *vrf_row->bgp_routers *
                                                      (vrf_row->n_bgp_routers + 1));
                            for (i = 0; i < vrf_row->n_bgp_routers; i++) {
                                bgp_routers_list[i] = vrf_row->bgp_routers[i];
                            }
                            bgp_routers_list[vrf_row->n_bgp_routers] = bgp_router_row;
                            ovsrec_vrf_set_bgp_routers(vrf_row, bgp_routers_list,
                                                       (vrf_row->n_bgp_routers + 1));
                            free(bgp_routers_list);
                            /* Set the asn column in the BGP_Router table */
                            ovsrec_bgp_router_set_asn(bgp_router_row,asn);
                            break;
                        }
                        break;
                    }
               }
          }
     }
     status = ovsdb_idl_txn_commit_block(bgp_router_txn);
     ovsdb_idl_txn_destroy(bgp_router_txn);
     bgp_router_txn = NULL;
     VLOG_DBG("%s Commit Status : %s", __FUNCTION__,
               ovsdb_idl_txn_status_to_string(status));
     ret_status = ((status == TXN_SUCCESS) && (status == TXN_INCOMPLETE)
          && (status == TXN_UNCHANGED));
     return ret_status;
}

/* Installing command for "no router bgp <asn>" */
DEFUN(cli_no_router_bgp,
      no_router_bgp_cmd,
      "no router bgp " CMD_AS_RANGE,
      ROUTER_STR
      BGP_STR
      AS_STR)
{
  return no_bgp_router_asn(atoi(argv[0]));
}

int
no_bgp_router_asn(int64_t asn)
{
    struct ovsrec_bgp_router *bgp_router_row = NULL;
    struct ovsrec_bgp_router **bgp_routers_list;
    const struct ovsrec_vrf *vrf_row = NULL;
    static struct ovsdb_idl_txn *bgp_router_txn=NULL;
    enum ovsdb_idl_txn_status status;
    int ret_status = 0;
    size_t i=0;

    ovsdb_idl_run(idl);

    if(!bgp_router_txn) {
         bgp_router_txn = ovsdb_idl_txn_create(idl);
         if (bgp_router_txn == NULL) {
             VLOG_ERR("Transaction creation failed");
             return TXN_ERROR;
         }

        vrf_row = ovsrec_vrf_first(idl);
        if (vrf_row == NULL) {
            VLOG_ERR("No VRF configured! No entries in BGP_Router Table");
            return -1;
        }

        bgp_router_row = ovsrec_bgp_router_first(idl);
        if (bgp_router_row == NULL) {
            VLOG_ERR("Given asn doesn't exist! can't delete!!");
            return -1;
        }
        else {
            bgp_router_row = NULL;
            OVSREC_BGP_ROUTER_FOR_EACH(bgp_router_row,idl) {
                VLOG_DBG("Found the row!! "
                         "bgp_router_row->asn : %d  asn = %d",
                          bgp_router_row->asn, asn);
                if (bgp_router_row->asn == asn) {
                    /* Delete BGP_router table reference in VRF table */
                    bgp_routers_list = xmalloc(sizeof *vrf_row->bgp_routers *
                                              (vrf_row->n_bgp_routers - 1));
                    for (i = 0; i < vrf_row->n_bgp_routers; i++) {
                        if(bgp_router_row != vrf_row->bgp_routers[i]) {
                            /* Found reference from VRF table */
                            bgp_routers_list[i] = vrf_row->bgp_routers[i];
                        }
                        else {
                            continue;
                        }
                    }
                    bgp_routers_list[vrf_row->n_bgp_routers] = bgp_router_row;
                    ovsrec_vrf_set_bgp_routers(vrf_row, bgp_routers_list,
                                              (vrf_row->n_bgp_routers - 1));
                    free(bgp_routers_list);
                    /* Delete the bgp row for matching asn */
                    ovsrec_bgp_router_delete(bgp_router_row);
                    break;
               }
               else {
                    continue;
               }
            }
         }
     }
     status = ovsdb_idl_txn_commit_block(bgp_router_txn);
     ovsdb_idl_txn_destroy(bgp_router_txn);
     bgp_router_txn = NULL;
     VLOG_DBG("%s Commit Status : %s", __FUNCTION__,
               ovsdb_idl_txn_status_to_string(status));
     ret_status = ((status == TXN_SUCCESS) && (status == TXN_INCOMPLETE)
          && (status == TXN_UNCHANGED));
     return ret_status;
}

void bgp_vty_init(void)
{
    install_element (ENABLE_NODE, &vtysh_show_ip_bgp_cmd);
    install_element (CONFIG_NODE, &router_bgp_cmd);
    install_element (CONFIG_NODE, &no_router_bgp_cmd);
}
