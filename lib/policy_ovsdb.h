/* policy ovsdb integration.
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
 * File: policy_ovsdb.h
 *
 * Purpose: Policy integrating with ovsdb.
 */
#ifndef POLICY_OVSDB_H
#define POLICY_OVSDB_H

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
  PREFIX_LIST_DESCRIPTION,
  PREFIX_LIST_ACTION,
  PREFIX_LIST_PREFIX,
  PREFIX_LIST_GE,
  PREFIX_LIST_LE,
  PREFIX_LIST_MAX,
} prefix_list;




int policy_ovsdb_prefix_list_get (struct ovsdb_idl *idl);
int policy_ovsdb_rt_map(struct ovsdb_idl *idl);


#endif /* POLICY_OVSDB */
