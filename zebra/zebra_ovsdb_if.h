/*
 * Copyright (C) 2015 Hewlett Packard Enterprise Development LP
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License. You may obtain
 * a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 *
 * File: zebra_ovsdb_if.h
 *
 * Purpose: This file includes all public interface defines needed by
 *          the new zebra_ovsdb.c for zebra - ovsdb integration
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
 * with the other daemons in the OpenSwitch system
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
