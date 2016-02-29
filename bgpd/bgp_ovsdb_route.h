/* bgp daemon ovsdb Route table integration.
 *
 * (c) Copyright 2015-2016 Hewlett Packard Enterprise Development LP
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
 * File: bgp_ovsdb_route.h
 *
 * Purpose: This file defines all public declarations of OVSDB route table
 * interface
 */
#ifndef BGP_OVSDB_RIB_H
#define BGP_OVSDB_RIB_H 1

#include "vswitch-idl.h"
#include "openswitch-idl.h"
#include "ovsdb-idl.h"
#include "smap.h"

struct bgp_info;
struct prefix;
struct bgp;

enum
{
  SET_COMMUNITY,
  SET_METRIC,
  SET_AGGREGATOR_AS,
  SET_AS_PATH_EXCLUDE,
  SET_AS_PATH_PREPEND,
  SET_ATOMIC_AGGREGATE,
  SET_COMM_LIST,
  SET_ECOMMUNITY_RT,
  SET_ECOMMUNITY_SOO,
  SET_IPV6_NEXT_HOP_GLOBAL,
  SET_LOCAL_PREFERENCE,
  SET_ORIGIN,
  SET_WEIGHT,
  SET_MAX,
} set;

enum
{
  MATCH_PREFIX,
  MATCH_IPV6_PREFIX,
  MATCH_COMMUNITY,
  MATCH_EXTCOMMUNITY,
  MATCH_ASPATH,
  MATCH_ORIGIN,
  MATCH_METRIC,
  MATCH_IPV6_NEXTHOP,
  MATCH_PROBABILITY,
  MATCH_MAX,
} match;

enum
{
  RT_MAP_NAME,
  RT_MAP_ACTION,
  RT_MAP_PREFERENCE,
  RT_MAP_DESCRIPTION,
  RT_MAP_MAX,
} rt_map;

enum
{
  PREFIX_LIST_NAME,
  PREFIX_LIST_DESCRIPTION,
  PREFIX_LIST_ACTION,
  PREFIX_LIST_PREFIX,
  PREFIX_LIST_GE,
  PREFIX_LIST_LE,
  PREFIX_LIST_MAX,
} prefix_list;

enum
{
  BGP_ASPATH_FILTER_NAME,
  BGP_ASPATH_FILTER_ACTION,
  BGP_ASPATH_FILTER_DESCRIPTION,
  BGP_ASPATH_FILTER_MAX,
} aspath_filter;

extern struct ovsdb_idl *idl;

extern int policy_ovsdb_community_filter_get(struct ovsdb_idl *idl);
extern int policy_ovsdb_prefix_list_get (struct ovsdb_idl *idl);
extern int policy_ovsdb_rt_map(struct ovsdb_idl *idl);

extern const struct ovsrec_vrf*
bgp_ovsdb_get_vrf(struct bgp *bgp);

extern const struct ovsrec_route*
bgp_ovsdb_lookup_rib_entry(struct prefix *p, struct bgp_info *info,
                           struct bgp *bgp, safi_t safi);

extern int
bgp_ovsdb_add_local_rib_entry(struct prefix *p, struct bgp_info *info,
                        struct bgp *bgp, safi_t safi);
extern int
bgp_ovsdb_withdraw_rib_entry(struct prefix *p, struct bgp_info *info,
                             struct bgp *bgp, safi_t safi);
extern int
bgp_ovsdb_announce_rib_entry(struct prefix *p, struct bgp_info *info,
                             struct bgp *bgp, safi_t safi);
extern int
bgp_ovsdb_delete_local_rib_entry(struct prefix *p, struct bgp_info *info,
                                 struct bgp *bgp, safi_t safi);
extern int
bgp_ovsdb_update_local_rib_entry_attributes(struct prefix *p, struct bgp_info *info,
                                            struct bgp *bgp, safi_t safi);
extern const struct ovsrec_bgp_route*
bgp_ovsdb_lookup_local_rib_entry(struct prefix *p,
                                 struct bgp_info *info,
                                 struct bgp *bgp,
                                 safi_t safi);
extern int
bgp_ovsdb_republish_route(const struct ovsrec_bgp_router *bgp_first, int asn);

extern void
bgp_txn_complete_processing(void);
#endif /* BGP_OVSDB_RIB_H */
