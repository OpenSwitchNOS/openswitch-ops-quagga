/*
 * (c) Copyright 2015 Hewlett Packard Enterprise Development LP
 *
 * This file is part of GNU Zebra.
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

#ifndef ZEBRA_OVSDB_IF_H
#define ZEBRA_OVSDB_IF_H 1

#define ZEBRA_RT_UNINSTALL  0
#define ZEBRA_RT_INSTALL    1

#define ZEBRA_NH_UNINSTALL  ZEBRA_RT_UNINSTALL
#define ZEBRA_NH_INSTALL    ZEBRA_RT_INSTALL

/*
 * TODO: Remove this macro once the macro is available through OVSDB IDL
 *       libraries.
 */
#define OVSREC_IDL_GET_TABLE_ROW_UUID(ovsrec_row_struct) \
                             (ovsrec_row_struct->header_.uuid)

extern bool zebra_cleanup_kernel_after_restart;

struct ipv4v6_addr
{
  union {
    struct in_addr ipv4_addr;
    struct in6_addr ipv6_addr;
  } u;
};

struct zebra_route_key
{
  struct ipv4v6_addr prefix;
  int64_t prefix_len;
  struct ipv4v6_addr nexthop;
  char ifname[IF_NAMESIZE+1];
  /* OPS_TODO: add vrf support */
};

struct zebra_route_del_data
{
  struct route_node *rnode;
  struct rib *rib;
  struct nexthop *nexthop;
};

/* Setup zebra to connect with ovsdb and daemonize. This daemonize is used
 * over the daemonize in the main function to keep the behavior consistent
 * with the other daemons in the OpenSwitch system
 */
void zebra_ovsdb_init (int argc, char *argv[]);

/* When the daemon is ready to shut, delete the idl cache
 * This happens with the ovs-appctl exit command.
 */
void zebra_ovsdb_exit (void);

/* Initialize and integrate the ovs poll loop with the daemon */
void zebra_ovsdb_init_poll_loop (struct zebra_t *zebrad);

void zebra_delete_route_nexthop_port_from_db (struct rib *route,
                                              char* port_name);
void zebra_delete_route_nexthop_addr_from_db (struct rib *route,
                                              char* port_name);
void zebra_route_list_add_data (struct route_node *rnode,
                                struct rib *rib_p,
                                struct nexthop *nhop);
void zebra_update_selected_nh (struct route_node *rn,
                               struct rib *route,
                               char* port_name,
                               char* nh_addr,
                               int if_selected);
void zebra_update_selected_route_nexthops_to_db (
                                            struct route_node *rn,
                                            struct rib *route,
                                            int action);
void zebra_dump_internal_nexthop (struct prefix *p, struct nexthop* nexthop);
void zebra_dump_internal_rib_entry (struct prefix *p, struct rib* rib);
void zebra_dump_internal_route_node (struct route_node *rn);
void zebra_dump_internal_route_table (struct route_table *table);
void cleanup_kernel_routes_after_restart();
void zebra_update_system_table_router_id(const struct ovsrec_interface *interface_row);
extern int zebra_create_txn (void);
extern int zebra_finish_txn (void);

#endif /* ZEBRA_OVSDB_IF_H */
