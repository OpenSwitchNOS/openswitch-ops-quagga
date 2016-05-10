/*
 * Copyright (C) 1997, 1998, 1999, 2000, 2001, 2002 Kunihiro Ishiguro
 * Copyright (C) 2015-2016 Hewlett Packard Enterprise Development LP
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
 */
/****************************************************************************
 * @ingroup zebra/cli
 *
 * @file vtysh_ovsdb_l3routes_context.c
 * Source for registering client callback with openvswitch table.
 *
 ***************************************************************************/

#include <zebra.h>
#include "vtysh/vty.h"
#include "vtysh/vector.h"
#include "vswitch-idl.h"
#include "openswitch-idl.h"
#include "vtysh/vtysh_ovsdb_if.h"
#include "vtysh/vtysh_ovsdb_config.h"
#include "openswitch-dflt.h"
#include "vtysh/vtysh_utils.h"
#include "vtysh/utils/system_vtysh_utils.h"
#include "vtysh/command.h"
#include "vtysh_ovsdb_l3routes_context.h"
#include "l3routes_vty.h"


/*-----------------------------------------------------------------------------
| Function : vtysh_config_context_staticroute_clientcallback
| Responsibility : client callback routine
| Parameters :
|     void *p_private: void type object typecast to required
| Return : void
-----------------------------------------------------------------------------*/
vtysh_ret_val
vtysh_config_context_static_routes_clientcallback(void *p_private)
{
  vtysh_ovsdb_cbmsg_ptr p_msg = (vtysh_ovsdb_cbmsg *)p_private;

  const struct ovsrec_route *row_route;
  char str_temp[80];
  int ipv4_flag = 0;
  int ipv6_flag = 0;
  char str[50];
  int i;
  extern struct ovsdb_idl_index_cursor route_cursor;
  extern is_route_cursor_initialized;

  vtysh_ovsdb_config_logmsg(VTYSH_OVSDB_CONFIG_DBG,
                           "vtysh_config_context_staticroute_clientcallback entered");
  if (is_route_cursor_initialized) {
      OVSREC_ROUTE_FOR_EACH_BYINDEX(row_route, &route_cursor) {
          ipv4_flag = 0;
          ipv6_flag = 0;
          if (strcmp(row_route->from, OVSREC_ROUTE_FROM_STATIC)) {
              continue;
          }

          if (row_route->address_family != NULL) {
              if (!strcmp(row_route->address_family, "ipv4")) {
                  ipv4_flag = 1;
              } else if (!strcmp(row_route->address_family, "ipv6")) {
                  ipv6_flag = 1;
              }
          } else {
              break;
          }

          if (ipv4_flag == 1 || ipv6_flag == 1) {
              for (i = 0; i < row_route->n_nexthops; i++) {
                  if (row_route->prefix) {
                      memset(str, 0, sizeof(str));
                      snprintf(str, sizeof(str), "%s", row_route->prefix);
                      if (ipv4_flag == 1 && ipv6_flag == 0) {
                          snprintf(str_temp, sizeof(str_temp), "ip route %s",
                                   str);
                      }
                      else {
                          snprintf(str_temp, sizeof(str_temp), "ipv6 route %s",
                                   str);
                      }
                  } else {
                      return e_vtysh_error;
                  }

                  if (row_route->distance != NULL) {
                    if (row_route->n_nexthops &&
                        row_route->nexthops[i]->ip_address &&
                        row_route->distance) {
                        if (*row_route->distance == 1) {
#ifdef VRF_ENABLE
                            if (strncmp(row_route->vrf->name, DEFAULT_VRF_NAME,
                                        OVSDB_VRF_NAME_MAXLEN)) {
                                vtysh_ovsdb_cli_print(p_msg,"%s %s vrf %s",
                                                      str_temp,
                                                      row_route->nexthops[i]->ip_address,
                                                      row_route->vrf->name);
                            } else {
                                vtysh_ovsdb_cli_print(p_msg,"%s %s", str_temp,
                                                      row_route->nexthops[i]->ip_address);
                            }
#else
                            vtysh_ovsdb_cli_print(p_msg,"%s %s", str_temp,
                                row_route->nexthops[i]->ip_address);
#endif

                        } else {
                            vtysh_ovsdb_cli_print(p_msg,"%s %s %d", str_temp,
                                row_route->nexthops[i]->ip_address,
                                *row_route->distance);
                        }

                    } else if (row_route->n_nexthops &&
                               row_route->nexthops[i]->ports
                               && row_route->distance) {
                        if (*row_route->distance == 1) {
#ifdef VRF_ENABLE
                            if (strncmp(row_route->vrf->name, DEFAULT_VRF_NAME,
                                        OVSDB_VRF_NAME_MAXLEN)) {
                                vtysh_ovsdb_cli_print(p_msg,"%s %s vrf %s",
                                                      str_temp,
                                                      row_route->nexthops[i]->ports[0]->name,
                                                      row_route->vrf->name);
                            } else {
                                vtysh_ovsdb_cli_print(p_msg,"%s %s", str_temp,
                                    row_route->nexthops[i]->ports[0]->name);
                            }
#else
                            vtysh_ovsdb_cli_print(p_msg,"%s %s", str_temp,
                                row_route->nexthops[i]->ports[0]->name);
#endif

                        } else {
                            vtysh_ovsdb_cli_print(p_msg,"%s %s %d", str_temp,
                                                  row_route->nexthops[i]->ports[0]->name,
                                                  *row_route->distance);
                        }
                    } else {
                        return e_vtysh_error;
                    }
                }
             }
          }
      }
  } else {
      return CMD_SUCCESS;
  }
  return e_vtysh_ok;
}
