/*
 * (c) Copyright 2016 Hewlett Packard Enterprise Development LP
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

#ifndef ZEBRA_DIAGNOSTICS_H
#define ZEBRA_DIAGNOSTICS_H 1

#define NUM_CHAR_CMP               6
#define NUM_CHAR_UNSUPPORTED       20
#define ZEBRA_DIAG_DUMP_BUF_LEN    16000
#define MAX_PROMPT_MSG_STR_LEN     256

extern struct ovsdb_idl *idl;
extern unsigned int idl_seqno;
extern struct shash zebra_cached_l3_ports;
extern struct shash zebra_updated_or_changed_l3_ports;
extern char *appctl_path;
extern struct unixctl_server *appctl;

extern void zebra_diagnostics_init();
extern void zebra_dump_internal_nexthop (struct ds *ds, struct prefix *p, struct nexthop* nexthop);
extern void zebra_dump_internal_rib_entry (struct ds *ds, struct prefix *p, struct rib* rib);
extern void zebra_dump_internal_route_node (struct ds *ds, struct route_node *rn);
extern void zebra_dump_internal_route_table (struct ds *ds, struct route_table *table);
extern void zebra_l3_port_walk_cache_and_print (struct ds *ds, struct shash* zebra_cached_l3_ports,
                                                bool if_permanent_hash);
extern void zebra_l3_port_node_print (struct ds *ds, struct zebra_l3_port* l3_port);
char* zebra_dump_ovsdb_uuid (struct uuid* uuid);
extern void zebra_dump_ovsdb_route_table (void);

#endif /* ZEBRA_DIAGNOSTICS_H */
