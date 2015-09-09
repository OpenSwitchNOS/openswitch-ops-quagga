/* bgp daemon ovsdb Route table integration.
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
 * File: bgp_ovsdb_route.h
 *
 * Purpose: This file defines all public declarations of OVSDB route table interface
 */
#ifndef BGP_OVSDB_RIB_H
#define BGP_OVSDB_RIB_H 1

#include "vswitch-idl.h"
#include "openhalon-idl.h"
#include "ovsdb-idl.h"
#include "smap.h"

struct bgp_info;
struct prefix;
struct bgp;

enum
{
  SET_COMMUNITY,
  SET_METRIC,
  SET_MAX,
} set;

enum
{
  MATCH_PREFIX,
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
  PREFIX_LIST_ACTION,
  PREFIX_LIST_PREFIX,
  PREFIX_LIST_MAX,
} prefix_list;

extern struct ovsdb_idl *idl;

extern int policy_ovsdb_prefix_list_get (struct ovsdb_idl *idl);
extern int policy_ovsdb_rt_map(struct ovsdb_idl *idl);

extern const struct ovsrec_vrf*
bgp_ovsdb_get_vrf(struct bgp *bgp);

extern const struct ovsrec_route*
bgp_ovsdb_lookup_rib_entry(struct prefix *p, struct bgp_info *info,
                           struct bgp *bgp, safi_t safi);
extern int
bgp_ovsdb_add_rib_entry(struct prefix *p, struct bgp_info *info,
                        struct bgp *bgp, safi_t safi);
extern int
bgp_ovsdb_withdraw_rib_entry(struct prefix *p, struct bgp_info *info,
                             struct bgp *bgp, safi_t safi);
extern int
bgp_ovsdb_announce_rib_entry(struct prefix *p, struct bgp_info *info,
                             struct bgp *bgp, safi_t safi);
extern int
bgp_ovsdb_delete_rib_entry(struct prefix *p, struct bgp_info *info,
                           struct bgp *bgp, safi_t safi);
extern int
bgp_ovsdb_update_flags(struct prefix *p, struct bgp_info *info,
                       struct bgp *bgp, safi_t safi);
extern void
bgp_ovsdb_rib_txn_create(void);

extern int
bgp_ovsdb_rib_txn_commit(void);

#endif /* BGP_OVSDB_RIB_H */
