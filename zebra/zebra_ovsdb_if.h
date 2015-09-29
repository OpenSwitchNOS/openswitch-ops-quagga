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
 * with the other daemons in the HALON system
 */
void zebra_ovsdb_init (int argc, char *argv[]);

/* When the daemon is ready to shut, delete the idl cache
 * This happens with the ovs-appctl exit command.
 */
void zebra_ovsdb_exit (void);

/* Initialize and integrate the ovs poll loop with the daemon */
void zebra_ovsdb_init_poll_loop (struct zebra_t *zebrad);

int zebra_update_selected_route_to_db (struct route_node *rn,
                                       struct rib *route,
                                       int action);

extern int zebra_create_txn (void);
extern int zebra_finish_txn (void);

#endif /* ZEBRA_OVSDB_IF_H */
