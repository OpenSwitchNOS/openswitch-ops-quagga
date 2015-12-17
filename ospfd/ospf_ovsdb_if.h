/* ospf daemon ovsdb integration.
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
 * File: ospf_ovsdb_if.h
 *
 * Purpose: This file includes all public interface defines needed by
 *          the new ospf_ovsdb_if.c for ospf - ovsdb integration
 */

#ifndef OSPF_OVSDB_IF_H
#define BGP_OVSDB_IF_H 1

#include "vswitch-idl.h"
#include "openswitch-dflt.h"

#define OSPF_STRING_NULL    "null"
#define OSPF_TIME_INTERVAL_HELLO_DUE 0
#define OSPF_TIME_INTERVAL_DEAD_DUE 1

#define OSPF_STAT_NAME_LEN 64

#define OSPF_KEY_AREA_STATS_ABR_COUNT            "abr_count"
#define OSPF_KEY_AREA_STATS_ASBR_COUNT            "asbr_count"

typedef struct
{
   unsigned char lsa_type;
   char* lsa_type_str;
}lsa_type;

/* Setup zebra to connect with ovsdb and daemonize. This daemonize is used
 * over the daemonize in the main function to keep the behavior consistent
 * with the other daemons in the HALON system
 */
void ospf_ovsdb_init(int argc, char *argv[]);

/* When the daemon is ready to shut, delete the idl cache
 * This happens with the ovs-appctl exit command.
 */
void ospf_ovsdb_exit(void);

/* Initialize and integrate the ovs poll loop with the daemon */
void ospf_ovsdb_init_poll_loop (struct ospf_master *bm);

extern struct ovsrec_ospf_router*
ovsrec_ospf_router_get_by_instance_num (int instance);

extern void
ovsdb_add_area_to_router (int ospf_intance,struct in_addr area_id);

extern void ospf_area_tbl_default(const struct ovsrec_ospf_area *area_row);

extern int
ospf_is_area_tbl_empty(const struct ovsrec_ospf_area *ospf_area_row);

extern void
ospf_area_remove_from_router(int instance, struct in_addr area_id);

extern void ospf_interface_if_config_tbl_default (const struct ovsrec_port *ovs_port);

extern void
ovsdb_ospf_set_spf_time_intervals (char* ifname, int interval_type,long time_msec,
                                      struct in_addr src);

extern void
ovsdb_ospf_set_hello_time_intervals (const char* ifname, int interval_type,
                  long time_msec);

extern void
ovsdb_ospf_set_spf_timestamp (int instance, struct in_addr area_id,
                              long spf_ts);

extern void
ospf_interface_remove_from_area(int instance, struct in_addr area_id,
                                      char* ifname);

extern void
ovsdb_add_lsa (struct ospf_lsa* lsa);

extern void
ovsdb_remove_lsa (struct ospf_lsa* lsa);

extern void
ovsdb_add_nbr (struct ospf_neighbor* nbr);

extern void
ovsdb_update_nbr (struct ospf_neighbor* nbr);

extern void
ovsdb_update_nbr_dr_bdr (char* ifname,
                      struct in_addr d_router, struct in_addr bd_router);

extern void
ovsdb_delete_nbr (struct ospf_neighbor* nbr);

extern void
ovsdb_update_full_nbr_count (struct ospf_neighbor* nbr,
                           uint32_t full_nbr_count);

#endif /* OSPF_OVSDB_IF_H */
