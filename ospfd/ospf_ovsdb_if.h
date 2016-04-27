/* ospf daemon ovsdb integration.
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
#define OSPF_DEFAULT_INSTANCE 1

#define OSPF_STAT_NAME_LEN 64
#define OSPF_MAX_NBR_OPTIONS 7

#define OSPF_MAX_PREFIX_LEN 50
#define OSPF_NEXTHOP_SAF_UNICAST "unicast"

#define OSPF_KEY_AREA_STATS_ABR_COUNT            "abr_count"
#define OSPF_KEY_AREA_STATS_ASBR_COUNT            "asbr_count"

#define OSPF_MIN_INTERVAL                   1
#define OSPF_MIN__RETRANSMIT_INTERVAL       1
#define OSPF_MAX_INTERVAL                   65535

#define OSPF_MIN_PRIORITY                   1
#define OSPF_MAX_PRIORITY                   255

/* TODO Many of the below Macro definitions will move to a common file later point in time   */
#define OSPF_KEY_STUB_ROUTER_STATE_ACTIVE      "stub_router_state_active"
#define OSPF_KEY_ROUTE_AREA_ID                 "area_id"
#define OSPF_KEY_ROUTE_TYPE_ABR                "area_type_abr"
#define OSPF_KEY_ROUTE_TYPE_ASBR               "area_type_asbr"
#define OSPF_KEY_ROUTE_EXT_TYPE                "ext_type"
#define OSPF_KEY_ROUTE_EXT_TAG                 "ext_tag"
#define OSPF_KEY_ROUTE_TYPE2_COST              "type2_cost"

#define OSPF_KEY_ROUTE_COST                    "cost"

#define OSPF_NBR_OPTION_STRING_T               "type_of_service"
#define OSPF_NBR_OPTION_STRING_E               "external_routing"
#define OSPF_NBR_OPTION_STRING_MC              "multicast"
#define OSPF_NBR_OPTION_STRING_NP              "type_7_lsa"
#define OSPF_NBR_OPTION_STRING_EA              "external_attributes_lsa"
#define OSPF_NBR_OPTION_STRING_DC              "demand_circuits"
#define OSPF_NBR_OPTION_STRING_O               "opaque_lsa"

#define OSPF_PATH_TYPE_STRING_INTER_AREA       "inter_area"
#define OSPF_PATH_TYPE_STRING_INTRA_AREA       "intra_area"
#define OSPF_PATH_TYPE_STRING_EXTERNAL         "external"

#define OSPF_EXT_TYPE_STRING_TYPE1             "ext_type_1"
#define OSPF_EXT_TYPE_STRING_TYPE2             "ext_type_2"

#define OSPF_DEFAULT_INFO_ORIGINATE            "default_info_originate"
#define OSPF_DEFAULT_INFO_ORIGINATE_ALWAYS     "always"

#define BOOLEAN_STRING_FALSE                   "false"
#define BOOLEAN_STRING_TRUE                    "true"

#define MAX_PATH_STRING_LEN                    128
#define OVSDB_OSPF_DEFAULT_REF_BANDWIDTH       (40000 * 1000)   /* kbps */

/* Utils Macros */
#define STR_EQ(s1, s2)      ((strlen((s1)) == strlen((s2))) && (!strncmp((s1), (s2), strlen((s2)))))

extern u_int vlink_count;

typedef struct
{
   unsigned char lsa_type;
   char* lsa_type_str;
}lsa_type;

/* Configuration data for virtual links
 */
struct ospf_vl_config_data {
  char* vl_name;
  struct in_addr area_id;       /* area ID from command line */
  int format;                   /* command line area ID format */
  struct in_addr vl_peer;       /* command line vl_peer */
  int auth_type;                /* Authehntication type, if given */
  char *auth_key;               /* simple password if present */
  int crypto_key_id;            /* Cryptographic key ID */
  char *md5_key;                /* MD5 authentication key */
  int hello_interval;           /* Obvious what these are... */
  int retransmit_interval;
  int transmit_delay;
  int dead_interval;
};


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
ovsdb_ospf_get_router_by_instance_num (int instance);

extern void
ovsdb_ospf_add_area_to_router (int ospf_intance,struct in_addr area_id);

extern void ovsdb_ospf_set_area_tbl_default(const struct ovsrec_ospf_area *area_row);

extern int
ovsdb_ospf_is_area_tbl_empty(const struct ovsrec_ospf_area *ospf_area_row);

extern void
ovsdb_ospf_remove_area_from_router(int instance, struct in_addr area_id);

extern void
ovsdb_ospf_set_interface_if_config_tbl_default (const struct ovsrec_port *ovs_port);

extern void
ovsdb_ospf_set_dead_time_intervals (char* ifname, int interval_type,long time_msec,
                                      struct in_addr src);

extern void
ovsdb_ospf_set_hello_time_intervals (const char* ifname, int interval_type,
                  long time_msec);

extern void
ovsdb_ospf_set_spf_timestamp (int instance, struct in_addr area_id,
                              long spf_ts);

extern void
ovsdb_ospf_remove_interface_from_area(int instance, struct in_addr area_id,
                                      char* ifname);

/* Set the reference to the interface row to the area table. */
extern void
ovsdb_area_set_interface(int instance,struct in_addr area_id,
                   struct ospf_interface* oi);

extern void
ovsdb_ospf_add_lsa (struct ospf_lsa* lsa);

extern void
ovsdb_ospf_remove_lsa (struct ospf_lsa* lsa);

extern void
ovsdb_ospf_add_nbr (struct ospf_neighbor* nbr);

extern void
ovsdb_ospf_add_nbr_self (struct ospf_neighbor* nbr, char* intf);

extern void
ovsdb_ospf_set_nbr_self_router_id (char* ifname, struct in_addr if_addr,
                                                struct in_addr router_id);

extern void
ovsdb_ospf_update_nbr (struct ospf_neighbor* nbr);

extern void
ovsdb_ospf_update_nbr_dr_bdr (struct in_addr router_id,
                      struct in_addr d_router, struct in_addr bd_router);

extern void
ovsdb_ospf_delete_nbr (struct ospf_neighbor* nbr);

extern void
ovsdb_ospf_delete_nbr_self (struct ospf_neighbor* nbr, char* ifname);

extern void
ovsdb_ospf_update_full_nbr_count (struct ospf_neighbor* nbr,
                           uint32_t full_nbr_count);

extern void
ovsdb_ospf_update_vl_full_nbr_count (struct ospf_area*);

extern void
ovsdb_ospf_update_ifsm_state (char* ifname, int ism_state);

extern void
ovsdb_ospf_add_rib_entry (struct prefix_ipv4 *p, struct ospf_route *or);

extern void
ovsdb_ospf_delete_rib_entry (struct prefix_ipv4 *p, struct ospf_route *or);

extern void
ovsdb_ospf_update_network_routes (const struct ospf *, const struct route_table *);

extern void
ovsdb_ospf_update_router_routes (const struct ospf *, const struct route_table *);

extern void
ovsdb_ospf_update_ext_routes (const struct ospf *, const struct route_table *);

extern void
ovsdb_ospf_update_ext_route (const struct ospf *, const struct prefix *, const struct ospf_route *);

void
if_set_value_from_ovsdb (struct ovsdb_idl *, const struct ovsrec_port *, struct interface *);

extern void
ovsdb_ospf_vl_update (const struct ospf_interface*);

#endif /* OSPF_OVSDB_IF_H */
