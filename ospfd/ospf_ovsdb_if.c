/* ospf daemon ovsdb integration.
 * Copyright (C) 2015 Hewlett Packard Enterprise Development LP
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
 * File: ospf_ovsdb_if.c
 *
 * Purpose: Main file for integrating ospfd with ovsdb and ovs poll-loop.
 */
#include <zebra.h>

#include <lib/version.h>
#include "getopt.h"
#include "command.h"
#include "thread.h"
#include "memory.h"
#include "ospfd/ospfd.h"
/* OVS headers */
#include "config.h"
#include "command-line.h"
#include "daemon.h"
#include "dirs.h"
#include "dummy.h"
#include "fatal-signal.h"
#include "poll-loop.h"
#include "stream.h"
#include "timeval.h"
#include "unixctl.h"
#include "table.h"
#include "openvswitch/vlog.h"
#include "vswitch-idl.h"
#include "coverage.h"
#include "prefix.h"

#include "openswitch-idl.h"
#include "ospfd/ospf_lsa.h"
#include "ospfd/ospf_lsdb.h"
#include "ospfd/ospf_nsm.h"
#include "ospfd/ospf_ism.h"
#include "ospfd/ospf_neighbor.h"
#include "ospfd/ospf_route.h"
#include "ospfd/ospf_ovsdb_if.h"
#include "ospfd/ospf_interface.h"


COVERAGE_DEFINE(ospf_ovsdb_cnt);
VLOG_DEFINE_THIS_MODULE(ospf_ovsdb_if);

/* Local structure to hold the master thread
 * and counters for read/write callbacks
 */
typedef struct ospf_ovsdb_t_ {
    int enabled;
    struct thread_master *master;

    unsigned int read_cb_count;
    unsigned int write_cb_count;
} ospf_ovsdb_t;

static ospf_ovsdb_t glob_ospf_ovs;
static struct ovsdb_idl *idl;
static unsigned int idl_seqno;
static char *appctl_path = NULL;
static struct unixctl_server *appctl;
static int system_configured = false;

boolean exiting = false;

lsa_type lsa_str[] = {
    {OSPF_UNKNOWN_LSA,"unknown_lsa"},
    {OSPF_ROUTER_LSA,"type1_router_lsa"},
    {OSPF_NETWORK_LSA,"type2_network_lsa"},
    {OSPF_SUMMARY_LSA,"type3_abr_summary_lsa"},
    {OSPF_ASBR_SUMMARY_LSA,"type4_asbr_summary_lsa"},
    {OSPF_AS_EXTERNAL_LSA,"type5_as_external_lsa"},
    {OSPF_GROUP_MEMBER_LSA,"type6_multicast_lsa"},
    {OSPF_AS_NSSA_LSA,"type7_nssa_lsa"},
    {OSPF_EXTERNAL_ATTRIBUTES_LSA,"type8_external_attributes_lsa"},
    {OSPF_OPAQUE_LINK_LSA,"type9_opaque_link_lsa"},
    {OSPF_OPAQUE_AREA_LSA,"type10_opaque_area_lsa"},
    {OSPF_OPAQUE_AS_LSA,"type11_opaque_as_lsa"}
};

typedef struct
{
  int key;
  const char *str;
}nsm_str;

const nsm_str ospf_nsm_state[] =
{
  { NSM_DependUpon, "depend_upon" },
  { NSM_Deleted,    "deleted"    },
  { NSM_Down,       "down" },
  { NSM_Attempt,    "attempt" },
  { NSM_Init,       "init" },
  { NSM_TwoWay,     "two_way" },
  { NSM_ExStart,    "ex_start" },
  { NSM_Exchange,   "exchange" },
  { NSM_Loading,    "loading" },
  { NSM_Full,       "full" },
};

typedef nsm_str ism_str;

const ism_str ospf_ism_state[] =
{
  { ISM_DependUpon, "depend_upon" },
  { ISM_Down,       "down" },
  { ISM_Loopback,    "loopback" },
  { ISM_Waiting,       "waiting" },
  { ISM_PointToPoint,     "point_to_point" },
  { ISM_DROther,    "dr_other" },
  { ISM_Backup,   "backup_dr" },
  { ISM_DR,    "dr" },
};

static int ospf_ovspoll_enqueue (ospf_ovsdb_t *ospf_ovs_g);
static int ospf_ovs_read_cb (struct thread *thread);

/* ovs appctl dump function for this daemon
 * This is useful for debugging
 */
static void
ospf_unixctl_dump(struct unixctl_conn *conn, int argc OVS_UNUSED,
                  const char *argv[] OVS_UNUSED, void *aux OVS_UNUSED)
{
    unixctl_command_reply_error(conn, "Nothing to dump :)");
}

/* Register OSPF tables to idl */
/* Add more columns and tables if needed by tge daemon */
static void
ospf_ovsdb_tables_init()
{
   /* Add VRF columns */
    ovsdb_idl_add_table(idl, &ovsrec_table_vrf);
    ovsdb_idl_add_column(idl, &ovsrec_vrf_col_name);
    ovsdb_idl_add_column(idl, &ovsrec_vrf_col_ospf_routers);

    /* Add interface columns */
    ovsdb_idl_add_table(idl, &ovsrec_table_interface);
    ovsdb_idl_add_column(idl, &ovsrec_interface_col_admin_state);
    ovsdb_idl_add_column(idl, &ovsrec_interface_col_duplex);
    ovsdb_idl_add_column(idl, &ovsrec_interface_col_error);
    ovsdb_idl_add_column(idl, &ovsrec_interface_col_hw_intf_config);
    ovsdb_idl_add_column(idl, &ovsrec_interface_col_link_resets);
    ovsdb_idl_add_column(idl, &ovsrec_interface_col_link_speed);
    ovsdb_idl_add_column(idl, &ovsrec_interface_col_link_state);
    ovsdb_idl_add_column(idl, &ovsrec_interface_col_mac_in_use);
    ovsdb_idl_add_column(idl, &ovsrec_interface_col_mtu);
    ovsdb_idl_add_column(idl, &ovsrec_interface_col_name);
    ovsdb_idl_add_column(idl, &ovsrec_interface_col_options);
    ovsdb_idl_add_column(idl, &ovsrec_interface_col_other_config);
    ovsdb_idl_add_column(idl, &ovsrec_interface_col_pause);
    ovsdb_idl_add_column(idl, &ovsrec_interface_col_statistics);
    ovsdb_idl_add_column(idl, &ovsrec_interface_col_status);
    ovsdb_idl_add_column(idl, &ovsrec_interface_col_type);
    ovsdb_idl_add_column(idl, &ovsrec_interface_col_user_config);

    /* Add OSPF_Router columns */
    ovsdb_idl_add_table(idl, &ovsrec_table_ospf_router);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_router_col_areas);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_router_col_areas);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_router_col_as_ext_lsas);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_router_col_default_information);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_router_col_distance);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_router_col_lsa_timers);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_router_col_opaque_as_lsas);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_router_col_ext_ospf_routes);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_router_col_opaque_as_lsas);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_router_col_passive_interface_default);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_router_col_redistribute);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_router_col_router_id);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_router_col_status);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_router_col_spf_calculation);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_router_col_stub_router_adv);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_router_col_networks);

    /* Add Route columns */
    ovsdb_idl_add_table(idl, &ovsrec_table_route);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_address_family);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_distance);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_from);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_metric);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_nexthops);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_prefix);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_protocol_private);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_protocol_specific);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_selected);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_sub_address_family);
    ovsdb_idl_add_column(idl, &ovsrec_route_col_vrf);

    /* Add Port columns */
    ovsdb_idl_add_table(idl, &ovsrec_table_port);
    ovsdb_idl_add_column(idl, &ovsrec_port_col_admin);
    ovsdb_idl_add_column(idl, &ovsrec_port_col_hw_config);
    ovsdb_idl_add_column(idl, &ovsrec_port_col_interfaces);
    ovsdb_idl_add_column(idl, &ovsrec_port_col_ip4_address);
    ovsdb_idl_add_column(idl, &ovsrec_port_col_ip4_address_secondary);
    ovsdb_idl_add_column(idl, &ovsrec_port_col_mac);
    ovsdb_idl_add_column(idl, &ovsrec_port_col_name);
    ovsdb_idl_add_column(idl, &ovsrec_port_col_ospf_intervals);
    ovsdb_idl_omit_alert(idl, &ovsrec_port_col_ospf_intervals);
    ovsdb_idl_add_column(idl, &ovsrec_port_col_ospf_if_out_cost);
    ovsdb_idl_omit_alert(idl, &ovsrec_port_col_ospf_if_out_cost);
    ovsdb_idl_add_column(idl, &ovsrec_port_col_ospf_priority);
    ovsdb_idl_omit_alert(idl, &ovsrec_port_col_ospf_priority);
    ovsdb_idl_add_column(idl, &ovsrec_port_col_ospf_if_type);
    ovsdb_idl_omit_alert(idl, &ovsrec_port_col_ospf_if_type);
    ovsdb_idl_add_column(idl, &ovsrec_port_col_ospf_auth_type);
    ovsdb_idl_omit_alert(idl, &ovsrec_port_col_ospf_auth_type);
    ovsdb_idl_add_column(idl, &ovsrec_port_col_ospf_mtu_ignore);
    ovsdb_idl_omit_alert(idl, &ovsrec_port_col_ospf_mtu_ignore);
    ovsdb_idl_add_column(idl, &ovsrec_port_col_other_config);
    ovsdb_idl_add_column(idl, &ovsrec_port_col_statistics);
    ovsdb_idl_add_column(idl, &ovsrec_port_col_status);

    /* Add OSPF_Area columns */
    ovsdb_idl_add_table(idl, &ovsrec_table_ospf_area);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_area_col_abr_summary_lsas);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_area_col_area_type);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_area_col_area_type);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_area_col_nssa_translator_role);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_area_col_nssa_translator_role);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_area_col_other_config);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_area_col_other_config);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_area_col_ospf_area_summary_addresses);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_area_col_statistics);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_area_col_statistics);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_area_col_status);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_area_col_status);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_area_col_asbr_summary_lsas);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_area_col_as_nssa_lsas);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_area_col_ospf_auth_type);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_area_col_prefix_lists);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_area_col_network_lsas);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_area_col_network_lsas);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_area_col_opaque_area_lsas);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_area_col_ospf_interfaces);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_area_col_ospf_interfaces);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_area_col_inter_area_ospf_routes);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_area_col_intra_area_ospf_routes);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_area_col_router_ospf_routes);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_area_col_router_lsas);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_area_col_router_lsas);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_area_col_ospf_vlinks);

    /* Add OSPF_Area_Summary_Addr columns */
    ovsdb_idl_add_table(idl, &ovsrec_table_ospf_summary_address);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_summary_address_col_other_config);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_summary_address_col_prefix);

    /* Add OSPF_Interface columns */
    ovsdb_idl_add_table(idl, &ovsrec_table_ospf_interface);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_interface_col_ifsm_state);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_interface_col_ifsm_state);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_interface_col_statistics);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_interface_col_status);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_interface_col_status);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_interface_col_name);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_interface_col_name);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_interface_col_neighbors);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_interface_col_neighbors);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_interface_col_port);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_interface_col_port);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_interface_col_ospf_vlink);

    /* Add OSPF_Neighbor columns */
    ovsdb_idl_add_table(idl, &ovsrec_table_ospf_neighbor);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_neighbor_col_bdr);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_neighbor_col_bdr);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_neighbor_col_dr);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_neighbor_col_dr);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_neighbor_col_nbma_nbr);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_neighbor_col_nbr_if_addr);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_neighbor_col_nbr_if_addr);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_neighbor_col_nbr_options);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_neighbor_col_nbr_options);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_neighbor_col_nbr_router_id);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_neighbor_col_nbr_router_id);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_neighbor_col_statistics);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_neighbor_col_statistics);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_neighbor_col_status);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_neighbor_col_status);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_neighbor_col_nfsm_state);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_neighbor_col_nfsm_state);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_neighbor_col_nbr_priority);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_neighbor_col_nbr_priority);

    /* Add OSPF_NBMA_Neighbor_Config columns */
    ovsdb_idl_add_table(idl, &ovsrec_table_ospf_nbma_neighbor);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_nbma_neighbor_col_interface_name);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_nbma_neighbor_col_other_config);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_nbma_neighbor_col_status);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_nbma_neighbor_col_nbr_router_id);

    /* Add OSPF_Vlink columns */
    ovsdb_idl_add_table(idl, &ovsrec_table_ospf_vlink);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_vlink_col_area_id);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_vlink_col_ospf_auth_type);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_vlink_col_name);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_vlink_col_peer_router_id);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_vlink_col_other_config);

    /* Add OSPF_Route columns */
    ovsdb_idl_add_table(idl, &ovsrec_table_ospf_route);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_route_col_paths);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_route_col_path_type);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_route_col_prefix);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_route_col_route_info);

    /* Add OSPF_lsa columns */
    ovsdb_idl_add_table(idl, &ovsrec_table_ospf_lsa);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_lsa_col_adv_router);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_lsa_col_adv_router);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_lsa_col_area_id);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_lsa_col_area_id);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_lsa_col_chksum);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_lsa_col_chksum);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_lsa_col_flags);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_lsa_col_length);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_lsa_col_lsa_data);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_lsa_col_lsa_type);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_lsa_col_lsa_type);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_lsa_col_ls_birth_time);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_lsa_col_ls_birth_time);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_lsa_col_ls_id);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_lsa_col_ls_id);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_lsa_col_ls_seq_num);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_lsa_col_ls_seq_num);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_lsa_col_num_router_links);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_lsa_col_options);
    ovsdb_idl_add_column(idl, &ovsrec_ospf_lsa_col_prefix);
    ovsdb_idl_omit_alert(idl, &ovsrec_ospf_lsa_col_prefix);
}

/* Create a connection to the OVSDB at db_path and create a dB cache
 * for this daemon. */
static void
ovsdb_init (const char *db_path)
{
    /* Initialize IDL through a new connection to the dB. */
    idl = ovsdb_idl_create(db_path, &ovsrec_idl_class, false, true);
    idl_seqno = ovsdb_idl_get_seqno(idl);
    ovsdb_idl_set_lock(idl, "OpenSwitch_ospf");
    //ovsdb_idl_verify_write_only(idl);

    /* Cache OpenVSwitch table */
    ovsdb_idl_add_table(idl, &ovsrec_table_open_vswitch);

    ovsdb_idl_add_column(idl, &ovsrec_system_col_cur_cfg);
    ovsdb_idl_add_column(idl, &ovsrec_system_col_hostname);

    ospf_ovsdb_tables_init();

    /* Register ovs-appctl commands for this daemon. */
    unixctl_command_register("ospfd/dump", "", 0, 0, ospf_unixctl_dump, NULL);
}

static void
ops_ospf_exit(struct unixctl_conn *conn, int argc OVS_UNUSED,
                const char *argv[] OVS_UNUSED, void *exiting_)
{
    boolean *exiting = exiting_;
    *exiting = true;
    unixctl_command_reply(conn, NULL);
}

static void
ops_ospf_lsa_dump(struct unixctl_conn *conn, int argc OVS_UNUSED,
                const char *argv[] OVS_UNUSED, void *ext_arg)
{
    struct ospf* ospf = NULL;
    struct ospf_lsa *lsa;
    struct route_node *rn;
    struct ospf_area *area;
    struct listnode *node;
    int type;
    char buf[4096] = {0};

    ospf= ospf_lookup();
    if (!ospf)
        unixctl_command_reply_error(conn,"NO OSPF instance present");
    else
    {
        for (ALL_LIST_ELEMENTS_RO (ospf->areas, node, area))
        {
            for (type = OSPF_MIN_LSA; type < OSPF_MAX_LSA; type++)
            {
                switch (type)
                {
                    case OSPF_AS_EXTERNAL_LSA:
                    #ifdef HAVE_OPAQUE_LSA
                    case OSPF_OPAQUE_AS_LSA:
                    #endif /* HAVE_OPAQUE_LSA */
                      continue;
                    default:
                      break;
                }
                LSDB_LOOP (AREA_LSDB (area, type), rn, lsa)
                {
                    sprintf (buf+strlen(buf),"%-15s ", inet_ntoa (lsa->data->id));
                    sprintf (buf+strlen(buf),"%-15s %4d 0x%08lx 0x%04x type%d\n",
                     inet_ntoa (lsa->data->adv_router), LS_AGE (lsa),
                     (u_long)ntohl (lsa->data->ls_seqnum),
                     ntohs (lsa->data->checksum),lsa->data->type);
                }
            }
        }
        unixctl_command_reply(conn,buf);
    }
}


static void
usage(void)
{
    printf("%s: Halon ospf daemon\n"
           "usage: %s [OPTIONS] [DATABASE]\n"
           "where DATABASE is a socket on which ovsdb-server is listening\n"
           "      (default: \"unix:%s/db.sock\").\n",
           program_name, program_name, ovs_rundir());
    stream_usage("DATABASE", true, false, true);
    daemon_usage();
    vlog_usage();
    printf("\nOther options:\n"
           "  --unixctl=SOCKET        override default control socket name\n"
           "  -h, --help              display this help message\n"
           "  -V, --version           display version information\n");

    exit(EXIT_SUCCESS);
}

/* OPS_TODO: Need to merge this parse function with the main parse function
 * in ospf_main to avoid issues.
 */
static char *
ospf_ovsdb_parse_options(int argc, char *argv[], char **unixctl_pathp)
{
    enum {
        OPT_UNIXCTL = UCHAR_MAX + 1,
        VLOG_OPTION_ENUMS,
        DAEMON_OPTION_ENUMS,
        OVSDB_OPTIONS_END,
    };
    static const struct option long_options[] = {
        {"help",        no_argument, NULL, 'h'},
        {"unixctl",     required_argument, NULL, OPT_UNIXCTL},
        DAEMON_LONG_OPTIONS,
        VLOG_LONG_OPTIONS,
        {NULL, 0, NULL, 0},
    };
    char *short_options = long_options_to_short_options(long_options);

    for (;;) {
        int c;

        c = getopt_long(argc, argv, short_options, long_options, NULL);
        if (c == -1) {
            break;
        }

        switch (c) {
        case 'h':
            usage();

        case OPT_UNIXCTL:
            *unixctl_pathp = optarg;
            break;

        VLOG_OPTION_HANDLERS
        DAEMON_OPTION_HANDLERS

        case '?':
            exit(EXIT_FAILURE);

        default:
           abort();
        }
    }
    free(short_options);

    argc -= optind;
    argv += optind;

    return xasprintf("unix:%s/db.sock", ovs_rundir());
}

/* Setup ospf to connect with ovsdb and daemonize. This daemonize is used
 * over the daemonize in the main function to keep the behavior consistent
 * with the other daemons in the OpenSwitch system
 */
void ospf_ovsdb_init (int argc, char *argv[])
{
    int retval;
    char *ovsdb_sock;

    memset(&glob_ospf_ovs, 0, sizeof(glob_ospf_ovs));

    set_program_name(argv[0]);
    proctitle_init(argc, argv);
    fatal_ignore_sigpipe();

    /* Parse commandline args and get the name of the OVSDB socket. */
    ovsdb_sock = ospf_ovsdb_parse_options(argc, argv, &appctl_path);

    /* Initialize the metadata for the IDL cache. */
    ovsrec_init();
    /* Fork and return in child process; but don't notify parent of
     * startup completion yet. */
    daemonize_start();

    /* Create UDS connection for ovs-appctl. */
    retval = unixctl_server_create(appctl_path, &appctl);
    if (retval) {
       exit(EXIT_FAILURE);
    }

    /* Register the ovs-appctl "exit" command for this daemon. */
    unixctl_command_register("exit", "", 0, 0, ops_ospf_exit, &exiting);

    unixctl_command_register("lsdb/dump", "", 0, 0, ops_ospf_lsa_dump, NULL);

   /* Create the IDL cache of the dB at ovsdb_sock. */
   ovsdb_init(ovsdb_sock);
   free(ovsdb_sock);

   /* Notify parent of startup completion. */
   daemonize_complete();

   /* Enable asynch log writes to disk. */
   vlog_enable_async();

   VLOG_INFO_ONCE("%s (Halon Ospfd Daemon) started", program_name);

   glob_ospf_ovs.enabled = 1;
   return;
}

static void
ospf_ovs_clear_fds (void)
{
    struct poll_loop *loop = poll_loop();
    free_poll_nodes(loop);
    loop->timeout_when = LLONG_MAX;
    loop->timeout_where = NULL;
}

/* Check if the system is already configured. The daemon should
 * not process any callbacks unless the system is configured.
 */
static inline void ospf_chk_for_system_configured(void)
{
    const struct ovsrec_system *ovs_vsw = NULL;

    if (system_configured) {
        /* Nothing to do if we're already configured. */
        return;
    }

    ovs_vsw = ovsrec_system_first(idl);

    if (ovs_vsw && (ovs_vsw->cur_cfg > (int64_t) 0)) {
        system_configured = true;
        VLOG_INFO("System is now configured (cur_cfg=%d).",
                 (int)ovs_vsw->cur_cfg);
    }
}

static struct ovsrec_ospf_interface*
find_ospf_interface_by_name (const char* ifname)
{
    struct ovsrec_ospf_interface* ospf_intf_row = NULL;

    OVSREC_OSPF_INTERFACE_FOR_EACH(ospf_intf_row,idl)
    {
        if (0 == strcmp (ospf_intf_row->name,ifname))
            return ospf_intf_row;
    }
    return NULL;
}

static struct ovsrec_port*
find_port_by_name (const char* ifname)
{
    struct ovsrec_port* port_row = NULL;

    OVSREC_PORT_FOR_EACH(port_row,idl)
    {
        if (0 == strcmp (port_row->name,ifname))
            return port_row;
    }
    return NULL;
}

static struct ovsrec_ospf_neighbor*
find_ospf_nbr_by_if_addr (const struct ovsrec_ospf_interface* ovs_oi, struct in_addr src)
{
    struct ovsrec_ospf_neighbor* nbr_row = NULL;
    int i = 0;

    for (i = 0 ; i < ovs_oi->n_neighbors ; i++)
    {
        nbr_row = ovs_oi->neighbors[i];
        if (nbr_row && (*(nbr_row->nbr_if_addr) == (int64_t)(src.s_addr)))
            return nbr_row;
    }
    return NULL;
}

int
modify_ospf_router_id_config (struct ospf *ospf_cfg,
    const struct ovsrec_ospf_router *ospf_mod_row)
{
    bool router_id_static = false;
    char* router_ip = NULL;
    struct in_addr addr;

    memset (&addr,0,sizeof(addr));
    router_ip = smap_get(&(ospf_mod_row->router_id),"router_id_val");

    if (router_ip)
    {
        if(0 == inet_aton(router_ip,&addr))
            VLOG_DBG ("Unable to convert Router id");
    }

    router_id_static = smap_get_bool(&(ospf_mod_row->router_id),"router_id_static",false);

    if (router_id_static)
        ospf_cfg->router_id_static.s_addr = addr.s_addr;
    else
        ospf_cfg->router_id.s_addr = addr.s_addr;

    ospf_router_id_update(ospf_cfg);

    return 0;
}

int
modify_ospf_router_config (struct ospf *ospf_cfg,
    const struct ovsrec_ospf_router *ospf_mod_row)
{
   if (smap_get_bool(&(ospf_mod_row->other_config), "ospf_rfc1583_compatible",false))
        SET_FLAG(ospf_cfg->config,OSPF_RFC1583_COMPATIBLE);
   else
        UNSET_FLAG(ospf_cfg->config,OSPF_RFC1583_COMPATIBLE);

   if (smap_get_bool(&(ospf_mod_row->other_config), "enable_ospf_opaque_lsa",false))
        SET_FLAG(ospf_cfg->config,OSPF_OPAQUE_CAPABLE);
   else
        UNSET_FLAG(ospf_cfg->config,OSPF_OPAQUE_CAPABLE);

   if (smap_get_bool(&(ospf_mod_row->other_config), "log_adjacency_changes",false))
        SET_FLAG(ospf_cfg->config,OSPF_LOG_ADJACENCY_CHANGES);
   else
        UNSET_FLAG(ospf_cfg->config,OSPF_LOG_ADJACENCY_CHANGES);

   if (smap_get_bool(&(ospf_mod_row->other_config), "log_adjacency_details",false))
        SET_FLAG(ospf_cfg->config,OSPF_LOG_ADJACENCY_DETAIL);
   else
        UNSET_FLAG(ospf_cfg->config,OSPF_LOG_ADJACENCY_DETAIL);

   return 0;
}

int
modify_ospf_stub_router_config (struct ovsdb_idl *idl, struct ospf *ospf_cfg,
    const struct ovsrec_ospf_router *ospf_mod_row)
{
    struct listnode *ln;
    struct ospf_area *area;
    int stub_admin_set = -1;
    bool admin_set = false;
    int startup = 0;
    int i = 0;

    admin_set = smap_get_bool(&(ospf_mod_row->stub_router_adv),
                              OVSREC_OSPF_ROUTER_STUB_ROUTER_ADV_ADMIN_SET,false);
    startup = smap_get_int(&(ospf_mod_row->stub_router_adv),
                              OVSREC_OSPF_ROUTER_STUB_ROUTER_ADV_STARTUP,0);
    if(admin_set) {
       if (!CHECK_FLAG(ospf_cfg->stub_router_admin_set,OSPF_STUB_ROUTER_ADMINISTRATIVE_SET))
           stub_admin_set = 1;
    }
    else {
       if (CHECK_FLAG(ospf_cfg->stub_router_admin_set,OSPF_STUB_ROUTER_ADMINISTRATIVE_SET))
               stub_admin_set = 0;
    }
   if (startup != ospf_cfg->stub_router_startup_time)
       ospf_cfg->stub_router_startup_time = startup;

   if (1 == stub_admin_set)
   {
       for (ALL_LIST_ELEMENTS_RO (ospf_cfg->areas, ln, area))
       {
         SET_FLAG (area->stub_router_state, OSPF_AREA_ADMIN_STUB_ROUTED);

         if (!CHECK_FLAG (area->stub_router_state, OSPF_AREA_IS_STUB_ROUTED))
             ospf_router_lsa_update_area (area);
       }
       ospf_cfg->stub_router_admin_set = OSPF_STUB_ROUTER_ADMINISTRATIVE_SET;
   }
   else if (0 == stub_admin_set)
   {
    for (ALL_LIST_ELEMENTS_RO (ospf_cfg->areas, ln, area))
    {
      UNSET_FLAG (area->stub_router_state, OSPF_AREA_ADMIN_STUB_ROUTED);

      /* Don't trample on the start-up stub timer */
      if (CHECK_FLAG (area->stub_router_state, OSPF_AREA_IS_STUB_ROUTED)
          && !area->t_stub_router)
        {
          UNSET_FLAG (area->stub_router_state, OSPF_AREA_IS_STUB_ROUTED);
          ospf_router_lsa_update_area (area);
        }
    }
    ospf_cfg->stub_router_admin_set = OSPF_STUB_ROUTER_ADMINISTRATIVE_UNSET;
   }
}

static struct ovsrec_ospf_area*
ovsrec_ospf_area_get_area_by_id (struct ovsrec_ospf_router* ovs_ospf,
                                                     struct in_addr areaid)
{
    int i = 0;
    struct ovsrec_ospf_area* ovs_area = NULL;
    for (i = 0 ; i < ovs_ospf->n_areas ; i++) {
        ovs_area = ovs_ospf->value_areas[i];
        if (ovs_ospf->key_areas[i] == areaid.s_addr)
            return ovs_area;
    }

    return NULL;
}

struct ovsrec_ospf_router*
ovsdb_ospf_get_router_by_instance_num (int instance)
{
    struct ovsrec_vrf* ovs_vrf = NULL;
    struct ovsrec_ospf_router* ovs_router = NULL;
    int i = 0;

    /* OPS_TODO : Support for multiple VRF */
    ovs_vrf = ovsrec_vrf_first(idl);
    if (!ovs_vrf)
    {
       VLOG_DBG ("No VRF found");
       return NULL;
    }

    for (i = 0 ; i < ovs_vrf->n_ospf_routers ; i++)
    {
       ovs_router = ovs_vrf->value_ospf_routers[i];
       if (instance == ovs_vrf->key_ospf_routers[i])
        return ovs_router;
    }

    return NULL;
}

void
ovsdb_ospf_add_lsa  (struct ospf_lsa* lsa)
{
    struct ovsrec_ospf_router* ospf_router_row = NULL;
    struct ovsrec_ospf_area* area_row = NULL;
    struct ovsdb_idl_txn* area_txn = NULL;
    struct ovsrec_ospf_lsa* new_lsas = NULL;
    struct ovsrec_ospf_lsa** router_lsas = NULL;
    struct ovsrec_ospf_lsa** network_lsas = NULL;
    enum ovsdb_idl_txn_status status;
    struct smap chksum_smap;
    char buf [64] = {0};
    int64_t lsa_area_id = 0;
    int64_t lsa_id = 0;
    int64_t lsa_age = 0;
    int64_t lsa_adv_router = 0;
    int64_t lsa_chksum = 0;
    int64_t lsa_seqnum = 0;
    int ospf_instance = 0;
    int i = 0;

    memset (&chksum_smap,0,sizeof(chksum_smap));
    if (NULL == lsa->data)
    {
        VLOG_DBG ("No LSA data to add");
        return;
    }
    if (NULL == lsa->area)
    {
        VLOG_DBG ("No area may be AS_EXTERNAL LSA, Not dealing now");
        return;
    }

    ospf_instance = lsa->area->ospf->ospf_inst;

    area_txn = ovsdb_idl_txn_create(idl);
    if (!area_txn)
    {
        VLOG_DBG ("Transaction create failed");
        return;
    }
    ospf_router_row =
        ovsdb_ospf_get_router_by_instance_num (ospf_instance);
    if (!ospf_router_row)
    {
       VLOG_DBG ("No OSPF router found");
       ovsdb_idl_txn_abort(area_txn);
       return;
    }
    /* OPS_TODO : AS_EXTERNAL LSA check */
    area_row = ovsrec_ospf_area_get_area_by_id(ospf_router_row,
                             lsa->area->area_id);
    if (!area_row)
    {
       VLOG_DBG ("No associated OSPF area : %d exist",lsa->area->area_id.s_addr);
       ovsdb_idl_txn_abort(area_txn);
       return;
    }
    new_lsas = ovsrec_ospf_lsa_insert(area_txn);
    if (!new_lsas)
    {
       VLOG_DBG ("LSA insert failed");
       ovsdb_idl_txn_abort(area_txn);
       return;
    }
    switch (lsa->data->type)
    {
        case OSPF_ROUTER_LSA:
            router_lsas = xmalloc(sizeof * area_row->router_lsas *
                                         (area_row->n_router_lsas + 1));
            for (i = 0; i < area_row->n_router_lsas; i++) {
                   router_lsas[i] = area_row->router_lsas[i];
            }
            router_lsas[area_row->n_router_lsas] = new_lsas;

            ovsrec_ospf_area_set_router_lsas (area_row,router_lsas,
                                   area_row->n_router_lsas + 1);

            if (NULL != lsa->lsdb)
            {
                snprintf (buf,sizeof(buf),"%u",lsa->lsdb->type[OSPF_ROUTER_LSA].checksum);
                smap_clone(&chksum_smap,&(area_row->status));
                smap_replace(&chksum_smap,"router_lsas_sum_cksum",buf);
                ovsrec_ospf_area_set_status(area_row,&chksum_smap);
                smap_destroy(&chksum_smap);
            }

            lsa_area_id = lsa->area->area_id.s_addr;
            ovsrec_ospf_lsa_set_area_id (new_lsas,
                                            &lsa_area_id,1);

            ovsrec_ospf_lsa_set_lsa_type (new_lsas,
                                            lsa_str[lsa->data->type].lsa_type_str);
            lsa_id = lsa->data->id.s_addr;
            ovsrec_ospf_lsa_set_ls_id (new_lsas,lsa_id);

            lsa_age = lsa->data->ls_age;
            ovsrec_ospf_lsa_set_ls_birth_time(new_lsas, lsa_age);

            ovsrec_ospf_lsa_set_prefix (new_lsas, "0.0.0.0");

            lsa_adv_router = lsa->data->adv_router.s_addr;
            ovsrec_ospf_lsa_set_adv_router (new_lsas,lsa_adv_router);

            lsa_chksum = lsa->data->checksum;
            ovsrec_ospf_lsa_set_chksum (new_lsas,&lsa_chksum,1);
            lsa_seqnum = lsa->data->ls_seqnum;
            ovsrec_ospf_lsa_set_ls_seq_num (new_lsas,lsa_seqnum);

            free(router_lsas);
            break;
        case OSPF_NETWORK_LSA:
                network_lsas = xmalloc(sizeof * area_row->network_lsas *
                                         (area_row->n_network_lsas + 1));
            for (i = 0; i < area_row->n_network_lsas; i++) {
                   network_lsas[i] = area_row->network_lsas[i];
            }
            network_lsas[area_row->n_network_lsas] = new_lsas;

            ovsrec_ospf_area_set_network_lsas (area_row,network_lsas,
                                   area_row->n_network_lsas + 1);

            if (NULL != lsa->lsdb)
            {
                snprintf (buf,sizeof(buf),"%u",lsa->lsdb->type[OSPF_NETWORK_LSA].checksum);
                smap_clone(&chksum_smap,&(area_row->status));
                smap_replace(&chksum_smap,"network_lsas_sum_cksum",buf);
                ovsrec_ospf_area_set_status(area_row,&chksum_smap);
                smap_destroy(&chksum_smap);
            }
            lsa_area_id = lsa->area->area_id.s_addr;
            ovsrec_ospf_lsa_set_area_id (new_lsas,
                                            &lsa_area_id,1);

            ovsrec_ospf_lsa_set_lsa_type (new_lsas,
                                            lsa_str[lsa->data->type].lsa_type_str);
            lsa_id = lsa->data->id.s_addr;
            ovsrec_ospf_lsa_set_ls_id (new_lsas,lsa_id);
            lsa_age = lsa->data->ls_age;
            ovsrec_ospf_lsa_set_ls_birth_time (new_lsas, lsa_age);
            ovsrec_ospf_lsa_set_prefix (new_lsas, "0.0.0.0");  //change to prefix as its type 3
            lsa_adv_router = lsa->data->adv_router.s_addr;
            ovsrec_ospf_lsa_set_adv_router (new_lsas,lsa_adv_router);
            lsa_chksum = lsa->data->checksum;
            ovsrec_ospf_lsa_set_chksum (new_lsas,&lsa_chksum,1);
            lsa_seqnum = lsa->data->ls_seqnum;
            ovsrec_ospf_lsa_set_ls_seq_num (new_lsas,lsa_seqnum);
            free(router_lsas);
            break;
    }

    status = ovsdb_idl_txn_commit_block(area_txn);
    if (TXN_SUCCESS != status &&
        TXN_UNCHANGED != status)
        VLOG_DBG ("LSA transaction commit failed:%d",status);

    ovsdb_idl_txn_destroy(area_txn);
}

//void
//ovsdb_ospf_remove_lsa  (struct in_addr lsa_id, unsigned char lsa_type, struct ospf_lsa* lsa)
void
ovsdb_ospf_remove_lsa  (struct ospf_lsa* lsa)
{
    struct ovsrec_ospf_router* ospf_router_row = NULL;
    struct ovsrec_ospf_area* area_row = NULL;
    struct ovsdb_idl_txn* area_txn = NULL;
    struct ovsrec_ospf_lsa* old_lsas = NULL;
    struct ovsrec_ospf_lsa** router_lsas = NULL;
    struct ovsrec_ospf_lsa** network_lsas = NULL;
    enum ovsdb_idl_txn_status status;
    int ospf_instance = 0;
    int i = 0, j = 0;

    if (NULL == lsa->data)
    {
        VLOG_DBG ("No LSA data to delete");
        return;
    }
    if (NULL == lsa->area)
    {
        VLOG_DBG ("No area may be AS_EXTERNAL LSA");
        return;
    }
    ospf_instance = lsa->area->ospf->ospf_inst;

    area_txn = ovsdb_idl_txn_create(idl);
    if (!area_txn)
    {
        VLOG_DBG ("Transaction create failed");
        return;
    }
    ospf_router_row =
        ovsdb_ospf_get_router_by_instance_num (ospf_instance);
    if (!ospf_router_row)
    {
       VLOG_DBG ("No OSPF router found");
       ovsdb_idl_txn_abort(area_txn);
       return;
    }
    /* OPS_TODO : AS_EXTERNAL LSA check */
    area_row = ovsrec_ospf_area_get_area_by_id(ospf_router_row,
                             lsa->area->area_id);
    if (!area_row)
    {
       VLOG_DBG ("No associated OSPF area : %d exist",lsa->area->area_id.s_addr);
       ovsdb_idl_txn_abort(area_txn);
       return;
    }
    switch (lsa->data->type)
    {
        case OSPF_ROUTER_LSA:
            if (0 >= area_row->n_router_lsas)
            {
               ovsdb_idl_txn_abort(area_txn);
               return;
            }
            router_lsas = xmalloc(sizeof * area_row->router_lsas *
                                         (area_row->n_router_lsas - 1));

            for (i = 0,j = 0; (i < area_row->n_router_lsas) && (j < area_row->n_router_lsas - 1); i++) {
                if ((area_row->router_lsas[i]->ls_id == lsa->data->id.s_addr) &&
                    (area_row->router_lsas[i]->ls_seq_num == lsa->data->ls_seqnum) &&
                    (area_row->router_lsas[i]->adv_router == lsa->data->adv_router.s_addr)) {
                   old_lsas = area_row->router_lsas[i];
                }
                else
                {
                   router_lsas[j] = area_row->router_lsas[i];
                   j++;
                }
            }
            if (!old_lsas)
            {

                ovsdb_idl_txn_abort(area_txn);
                free(router_lsas);
                return;
            }

            ovsrec_ospf_area_set_router_lsas (area_row,router_lsas,
                                   area_row->n_router_lsas - 1);


            ovsrec_ospf_lsa_delete (old_lsas);
            // TODO: Update the checksum sum
            free(router_lsas);
            break;
        case OSPF_NETWORK_LSA:
            if (0 >= area_row->n_network_lsas)
            {
               ovsdb_idl_txn_abort(area_txn);
               return;
            }
            network_lsas = xmalloc(sizeof * area_row->network_lsas *
                                         (area_row->n_network_lsas - 1));

            for (i = 0,j = 0; (i < area_row->n_network_lsas) & (j < area_row->n_network_lsas - 1); i++) {
                if ((area_row->network_lsas[i]->ls_id == lsa->data->id.s_addr) &&
                    (area_row->network_lsas[i]->ls_seq_num == lsa->data->ls_seqnum) &&
                    (area_row->network_lsas[i]->adv_router == lsa->data->adv_router.s_addr)) {
                    old_lsas = area_row->network_lsas[i];
                }
                else
                {
                   network_lsas[j] = area_row->network_lsas[i];
                   j++;
                }
            }

            if (!old_lsas)
            {
                VLOG_DBG ("No lsa");
                ovsdb_idl_txn_abort(area_txn);
                free(network_lsas);
                return;
            }

            ovsrec_ospf_area_set_network_lsas (area_row,network_lsas,
                                   area_row->n_network_lsas - 1);

            ovsrec_ospf_lsa_delete (old_lsas);
            // TODO: Update the checksum sum
            free(network_lsas);
            break;
    }

    status = ovsdb_idl_txn_commit_block(area_txn);
    if (TXN_SUCCESS != status &&
        TXN_UNCHANGED != status)
        VLOG_DBG ("LSA delete transaction commit failed:%d",status);

    ovsdb_idl_txn_destroy(area_txn);
    return;
}

void
ovsdb_ospf_update_full_nbr_count (struct ospf_neighbor* nbr,
                           uint32_t full_nbr_count)
{
    struct ovsrec_ospf_area* ovs_area = NULL;
    struct ovsrec_ospf_router* ovs_router = NULL;
    struct ovsdb_idl_txn* nbr_txn = NULL;
    enum ovsdb_idl_txn_status status;
    struct smap area_smap;
    char buf[32] = {0};

    int instance = 0;

    if (NULL == nbr)
    {
        VLOG_DBG ("No neighbor data to add");
        return;
    }
    if (NULL == nbr->oi)
    {
        VLOG_DBG ("No associated interface of neighbor");
        return;
    }
    if (NULL == nbr->oi->ospf)
    {
        VLOG_DBG ("No associated ospf instance of neighbor");
        return;
    }
    if (NULL == nbr->oi->area)
    {
        VLOG_DBG ("No associated area of neighbor");
        return;
    }
    nbr_txn = ovsdb_idl_txn_create(idl);
    if (!nbr_txn)
    {
        VLOG_DBG ("Transaction create failed");
        return;
    }

    instance = nbr->oi->ospf->ospf_inst;
    ovs_router = ovsdb_ospf_get_router_by_instance_num (instance);
    if (NULL == ovs_router)
    {
        VLOG_DBG ("No ospf instance of neighbor");
        ovsdb_idl_txn_abort(nbr_txn);
        return;
    }
    ovs_area = ovsrec_ospf_area_get_area_by_id(ovs_router,nbr->oi->area->area_id);
    if (NULL == ovs_area)
    {
        VLOG_DBG ("No associated area of neighbor");
        ovsdb_idl_txn_abort(nbr_txn);
        return;
    }
    snprintf(buf,sizeof(buf),"%u",full_nbr_count);
    memset(&area_smap,0,sizeof(area_smap));
    smap_clone(&area_smap,&(ovs_area->status));
    smap_replace(&area_smap,"full_nbrs",buf);
    ovsrec_ospf_area_set_status(ovs_area,&area_smap);

    status = ovsdb_idl_txn_commit_block(nbr_txn);
    if (TXN_SUCCESS != status &&
        TXN_UNCHANGED != status)
        VLOG_DBG ("Full nbr # transaction commit failed:%d",status);

    ovsdb_idl_txn_destroy(nbr_txn);
    smap_destroy(&area_smap);
    return;
}

void
ovsdb_ospf_update_nbr_dr_bdr  (struct in_addr if_addr,
                      struct in_addr d_router, struct in_addr bd_router)
{
    struct ovsrec_ospf_neighbor* ovs_nbr = NULL;
    struct ovsdb_idl_txn* nbr_txn = NULL;
    int64_t ip_src = 0;
    enum ovsdb_idl_txn_status status;
    int i = 0;

    nbr_txn = ovsdb_idl_txn_create(idl);
    if (!nbr_txn)
    {
        VLOG_DBG ("Transaction create failed");
        return;
    }
    OVSREC_OSPF_NEIGHBOR_FOR_EACH(ovs_nbr,idl)
    {
        /* Includes self-neighbor */
        if (ovs_nbr && (if_addr.s_addr == ovs_nbr->nbr_if_addr[0]))
        {
            ip_src = d_router.s_addr;
            ovsrec_ospf_neighbor_set_dr (ovs_nbr,&ip_src,1);

            ip_src = bd_router.s_addr;
            ovsrec_ospf_neighbor_set_bdr (ovs_nbr,&ip_src,1);
            break;
        }
    }

    status = ovsdb_idl_txn_commit_block(nbr_txn);
    if (TXN_SUCCESS != status &&
        TXN_UNCHANGED != status)
        VLOG_DBG ("NBR DR-BDR transaction commit failed:%d",status);

    ovsdb_idl_txn_destroy(nbr_txn);
    return;
}

void
ovsdb_ospf_update_nbr  (struct ospf_neighbor* nbr)
{
    struct ovsrec_ospf_interface* ovs_oi = NULL;
    struct ovsrec_ospf_neighbor* ovs_nbr = NULL;
    struct ovsdb_idl_txn* nbr_txn = NULL;
    struct interface* intf = NULL;
    //int64_t ip_src = 0;
    int64_t nbr_id = 0;
    int64_t nbr_priority = 0;
    enum ovsdb_idl_txn_status status;
    char** value_nbr_option = NULL;
    int nbr_option_cnt = 0;
    char** key_nbr_statistics = NULL;
    int64_t* value_nbr_statistics = NULL;
    int i = 0;

    if (NULL == nbr)
    {
        VLOG_DBG ("No neighbor data to add");
        return;
    }
    if (NULL == nbr->oi)
    {
        VLOG_DBG ("No associated interface of neighbor");
        return;
    }

    nbr_txn = ovsdb_idl_txn_create(idl);
    if (!nbr_txn)
    {
        VLOG_DBG ("Transaction create failed");
        return;
    }
    intf = nbr->oi->ifp;
    if (NULL == intf)
    {
        VLOG_DBG ("No associated interface of neighbor");
        ovsdb_idl_txn_abort(nbr_txn);
        return;
    }
    ovs_oi = find_ospf_interface_by_name(intf->name);
    if (NULL == ovs_oi)
    {
        VLOG_DBG ("No associated interface of neighbor");
        ovsdb_idl_txn_abort(nbr_txn);
        return;
    }
    ovs_nbr = find_ospf_nbr_by_if_addr(ovs_oi,nbr->src);
    if (!ovs_nbr)
    {
       VLOG_DBG ("No Neighbor present");
       ovsdb_idl_txn_abort(nbr_txn);
       return;
    }

    nbr_id = nbr->router_id.s_addr;
    ovsrec_ospf_neighbor_set_nbr_router_id (ovs_nbr,&nbr_id,1);

    if (CHECK_FLAG(nbr->options,OSPF_OPTION_E))
    {
        nbr_option_cnt++;
        if(!value_nbr_option)
            value_nbr_option = xmalloc(OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        else
            value_nbr_option = xrealloc(value_nbr_option,
                                  OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        value_nbr_option[nbr_option_cnt -1 ] =
            OVSREC_OSPF_NEIGHBOR_NBR_OPTIONS_EXTERNAL_ROUTING;
    }
    if (CHECK_FLAG(nbr->options,OSPF_OPTION_MC))
    {
        nbr_option_cnt++;
        if(!value_nbr_option)
            value_nbr_option = xmalloc(OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        else
            value_nbr_option = xrealloc(value_nbr_option,
                                  OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        value_nbr_option[nbr_option_cnt -1 ] =
            OVSREC_OSPF_NEIGHBOR_NBR_OPTIONS_MULTICAST;
    }
    if (CHECK_FLAG(nbr->options,OSPF_OPTION_NP))
    {
        nbr_option_cnt++;
        if(!value_nbr_option)
            value_nbr_option = xmalloc(OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        else
            value_nbr_option = xrealloc(value_nbr_option,
                                  OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        value_nbr_option[nbr_option_cnt -1 ] =
            OVSREC_OSPF_NEIGHBOR_NBR_OPTIONS_TYPE_7_LSA;
    }
    if (CHECK_FLAG(nbr->options,OSPF_OPTION_EA))
    {
        nbr_option_cnt++;
        if(!value_nbr_option)
            value_nbr_option = xmalloc(OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        else
            value_nbr_option = xrealloc(value_nbr_option,
                                  OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        value_nbr_option[nbr_option_cnt -1 ] =
            OVSREC_OSPF_NEIGHBOR_NBR_OPTIONS_EXTERNAL_ATTRIBUTES_LSA;
    }
    if (CHECK_FLAG(nbr->options,OSPF_OPTION_DC))
    {
        nbr_option_cnt++;
        if(!value_nbr_option)
            value_nbr_option = xmalloc(OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        else
            value_nbr_option = xrealloc(value_nbr_option,
                                  OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        value_nbr_option[nbr_option_cnt -1 ] =
            OVSREC_OSPF_NEIGHBOR_NBR_OPTIONS_DEMAND_CIRCUITS;
    }
    if (CHECK_FLAG(nbr->options,OSPF_OPTION_O))
    {
        nbr_option_cnt++;
        if(!value_nbr_option)
            value_nbr_option = xmalloc(OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        else
            value_nbr_option = xrealloc(value_nbr_option,
                                  OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        value_nbr_option[nbr_option_cnt -1 ] =
            OVSREC_OSPF_NEIGHBOR_NBR_OPTIONS_OPAQUE_LSA;
    }

    ovsrec_ospf_neighbor_set_nbr_options (ovs_nbr,value_nbr_option,
                                                             nbr_option_cnt);
    nbr_priority = nbr->priority;
    ovsrec_ospf_neighbor_set_nbr_priority (ovs_nbr,&nbr_priority,1);

    ovsrec_ospf_neighbor_set_nfsm_state (ovs_nbr,ospf_nsm_state[nbr->state].str);

    for (i = 0 ; i < ovs_nbr->n_statistics; i++)
        if (0 == strcmp (ovs_nbr->key_statistics[i],OSPF_KEY_NEIGHBOR_STATE_CHG_CNT))
            ovs_nbr->value_statistics[i] = nbr->state_change;
    ovsrec_ospf_neighbor_set_statistics(ovs_nbr,ovs_nbr->key_statistics,
        ovs_nbr->value_statistics,ovs_nbr->n_statistics);

    status = ovsdb_idl_txn_commit_block(nbr_txn);
    if (TXN_SUCCESS != status &&
        TXN_UNCHANGED != status)
        VLOG_DBG ("NBR add transaction commit failed:%d",status);

    ovsdb_idl_txn_destroy(nbr_txn);
    free (key_nbr_statistics);
    free (value_nbr_statistics);
    free (value_nbr_option);
    return;
}

void
ovsdb_ospf_add_nbr  (struct ospf_neighbor* nbr)
{
    struct ovsrec_ospf_interface* ovs_oi = NULL;
    struct ovsrec_ospf_neighbor** ovs_nbr = NULL;
    struct ovsrec_ospf_neighbor* new_ovs_nbr = NULL;
    struct ovsdb_idl_txn* nbr_txn = NULL;
    struct timeval tv;
    struct smap nbr_status;
    struct interface* intf = NULL;
    int64_t ip_src = 0;
    int64_t nbr_id = 0;
    enum ovsdb_idl_txn_status status;
    char** key_nbr_statistics = NULL;
    char** value_nbr_option = NULL;
    int nbr_option_cnt = 0;
    int64_t* value_nbr_statistics = NULL;
    long nbr_up_time = 0;
    char buf[32] = {0};
    int i = 0;

    if (NULL == nbr)
    {
        VLOG_DBG ("No neighbor data to add");
        return;
    }
    if (NULL == nbr->oi)
    {
        VLOG_DBG ("No associated interface of neighbor");
        return;
    }

    nbr_txn = ovsdb_idl_txn_create(idl);
    if (!nbr_txn)
    {
        VLOG_DBG ("Transaction create failed");
        return;
    }
    intf = nbr->oi->ifp;
    if (NULL == intf)
    {
        VLOG_DBG ("No associated interface of neighbor");
        ovsdb_idl_txn_abort(nbr_txn);
        return;
    }
    ovs_oi = find_ospf_interface_by_name(intf->name);
    if (NULL == ovs_oi)
    {
        VLOG_DBG ("No associated interface of neighbor");
        ovsdb_idl_txn_abort(nbr_txn);
        return;
    }
    /* Fix me : Update NBR instead of looping through
     * all the neighbor (OVSDB lookup). May be a local cache
     * and if there is change then commit to DB
     */

    new_ovs_nbr = find_ospf_nbr_by_if_addr(ovs_oi,nbr->src);
    if (new_ovs_nbr)
    {
       VLOG_DBG ("Neighbor already present");
       ovsdb_idl_txn_abort(nbr_txn);
       return;
    }
    new_ovs_nbr = ovsrec_ospf_neighbor_insert (nbr_txn);
    if (NULL == new_ovs_nbr)
    {
        VLOG_DBG ("Neighbor insertion failed");
        ovsdb_idl_txn_abort(nbr_txn);
        return;
    }
    ovs_nbr = xmalloc(sizeof * ovs_oi->neighbors *
                                    (ovs_oi->n_neighbors + 1));
    for (i = 0; i < ovs_oi->n_neighbors; i++) {
                 ovs_nbr[i] = ovs_oi->neighbors[i];
    }
    ovs_nbr[ovs_oi->n_neighbors] = new_ovs_nbr;
    ovsrec_ospf_interface_set_neighbors (ovs_oi,ovs_nbr,ovs_oi->n_neighbors + 1);
    nbr_id = nbr->router_id.s_addr;
    ovsrec_ospf_neighbor_set_nbr_router_id (new_ovs_nbr,&nbr_id,1);

    ip_src = nbr->src.s_addr;
    ovsrec_ospf_neighbor_set_nbr_if_addr (new_ovs_nbr,&ip_src,1);

    if (CHECK_FLAG(nbr->options,OSPF_OPTION_E))
    {
        nbr_option_cnt++;
        if(!value_nbr_option)
            value_nbr_option = xmalloc(OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        else
            value_nbr_option = xrealloc(value_nbr_option,
                                  OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        value_nbr_option[nbr_option_cnt -1 ] =
            OVSREC_OSPF_NEIGHBOR_NBR_OPTIONS_EXTERNAL_ROUTING;
    }
    if (CHECK_FLAG(nbr->options,OSPF_OPTION_MC))
    {
        nbr_option_cnt++;
        if(!value_nbr_option)
            value_nbr_option = xmalloc(OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        else
            value_nbr_option = xrealloc(value_nbr_option,
                                  OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        value_nbr_option[nbr_option_cnt -1 ] =
            OVSREC_OSPF_NEIGHBOR_NBR_OPTIONS_MULTICAST;
    }
    if (CHECK_FLAG(nbr->options,OSPF_OPTION_NP))
    {
        nbr_option_cnt++;
        if(!value_nbr_option)
            value_nbr_option = xmalloc(OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        else
            value_nbr_option = xrealloc(value_nbr_option,
                                  OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        value_nbr_option[nbr_option_cnt -1 ] =
            OVSREC_OSPF_NEIGHBOR_NBR_OPTIONS_TYPE_7_LSA;
    }
    if (CHECK_FLAG(nbr->options,OSPF_OPTION_EA))
    {
        nbr_option_cnt++;
        if(!value_nbr_option)
            value_nbr_option = xmalloc(OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        else
            value_nbr_option = xrealloc(value_nbr_option,
                                  OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        value_nbr_option[nbr_option_cnt -1 ] =
            OVSREC_OSPF_NEIGHBOR_NBR_OPTIONS_EXTERNAL_ATTRIBUTES_LSA;
    }
    if (CHECK_FLAG(nbr->options,OSPF_OPTION_DC))
    {
        nbr_option_cnt++;
        if(!value_nbr_option)
            value_nbr_option = xmalloc(OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        else
            value_nbr_option = xrealloc(value_nbr_option,
                                  OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        value_nbr_option[nbr_option_cnt -1 ] =
            OVSREC_OSPF_NEIGHBOR_NBR_OPTIONS_DEMAND_CIRCUITS;
    }
    if (CHECK_FLAG(nbr->options,OSPF_OPTION_O))
    {
        nbr_option_cnt++;
        if(!value_nbr_option)
            value_nbr_option = xmalloc(OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        else
            value_nbr_option = xrealloc(value_nbr_option,
                                  OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        value_nbr_option[nbr_option_cnt -1 ] =
            OVSREC_OSPF_NEIGHBOR_NBR_OPTIONS_OPAQUE_LSA;
    }

    ovsrec_ospf_neighbor_set_nbr_options (new_ovs_nbr,value_nbr_option,
                                                             nbr_option_cnt);

    ovsrec_ospf_neighbor_set_nfsm_state (new_ovs_nbr,ospf_nsm_state[nbr->state].str);

    key_nbr_statistics =  xmalloc(OSPF_STAT_NAME_LEN * (OSPF_NEIGHBOR_STATISTICS_MAX));

    value_nbr_statistics =  xmalloc(sizeof *new_ovs_nbr->value_statistics *
                                 (OSPF_NEIGHBOR_STATISTICS_MAX));

    key_nbr_statistics [OSPF_NEIGHBOR_DB_SUMMARY_COUNT] = OSPF_KEY_NEIGHBOR_DB_SUMMARY_CNT;
    key_nbr_statistics [OSPF_NEIGHBOR_LS_REQUEST_COUNT] = OSPF_KEY_NEIGHBOR_LS_REQUEST_CNT;
    key_nbr_statistics [OSPF_NEIGHBOR_LS_RETRANSMIT_COUNT] = OSPF_KEY_NEIGHBOR_LS_RE_TRANSMIT_CNT;
    key_nbr_statistics [OSPF_NEIGHBOR_STATE_CHANGE_COUNT] = OSPF_KEY_NEIGHBOR_STATE_CHG_CNT;

    value_nbr_statistics [OSPF_NEIGHBOR_DB_SUMMARY_COUNT] = 0;
    value_nbr_statistics [OSPF_NEIGHBOR_LS_REQUEST_COUNT] = 0;
    value_nbr_statistics [OSPF_NEIGHBOR_LS_RETRANSMIT_COUNT] = 0;
    value_nbr_statistics [OSPF_NEIGHBOR_STATE_CHANGE_COUNT] = nbr->state_change;

    ovsrec_ospf_neighbor_set_statistics(new_ovs_nbr,key_nbr_statistics,
                          value_nbr_statistics,OSPF_NEIGHBOR_STATISTICS_MAX);

    quagga_gettime(QUAGGA_CLK_MONOTONIC,&tv);
    nbr_up_time = (1000000 * tv.tv_sec + tv.tv_usec)/1000;
    snprintf(buf,sizeof (buf),"%u",nbr_up_time);
    smap_clone (&nbr_status,&(new_ovs_nbr->status));
    smap_replace(&nbr_status, OSPF_KEY_NEIGHBOR_LAST_UP_TIMESTAMP, buf);
    ovsrec_ospf_neighbor_set_status(new_ovs_nbr,&nbr_status);

    status = ovsdb_idl_txn_commit_block(nbr_txn);
    if (TXN_SUCCESS != status &&
        TXN_UNCHANGED != status)
        VLOG_DBG ("NBR add transaction commit failed:%d",status);

    ovsdb_idl_txn_destroy(nbr_txn);
    smap_destroy (&nbr_status);
    free (ovs_nbr);
    free (key_nbr_statistics);
    free (value_nbr_statistics);
    free (value_nbr_option);
    return;
}

void
ovsdb_ospf_add_nbr_self  (struct ospf_neighbor* nbr, char* intf)
{
    struct ovsrec_ospf_interface* ovs_oi = NULL;
    struct ovsrec_ospf_neighbor** ovs_nbr = NULL;
    struct ovsrec_ospf_neighbor* new_ovs_nbr = NULL;
    struct ovsdb_idl_txn* nbr_txn = NULL;
    struct timeval tv;
    struct smap nbr_status;
    int64_t ip_src = 0;
    int64_t nbr_id = 0;
    enum ovsdb_idl_txn_status status;
    char** key_nbr_statistics = NULL;
    char** value_nbr_option = NULL;
    int nbr_option_cnt = 0;
    int64_t* value_nbr_statistics = NULL;
    long nbr_up_time = 0;
    char buf[32] = {0};
    int i = 0;

    if (NULL == nbr)
    {
        VLOG_DBG ("No neighbor data to add");
        return;
    }
    nbr_txn = ovsdb_idl_txn_create(idl);
    if (!nbr_txn)
    {
        VLOG_DBG ("Transaction create failed");
        return;
    }
    if (NULL == intf)
    {
        VLOG_DBG ("No associated interface of neighbor");
        ovsdb_idl_txn_abort(nbr_txn);
        return;
    }
    ovs_oi = find_ospf_interface_by_name(intf);
    if (NULL == ovs_oi)
    {
        VLOG_DBG ("No associated interface of neighbor");
        ovsdb_idl_txn_abort(nbr_txn);
        return;
    }
    /* Fix me : Update NBR instead of looping through
     * all the neighbor (OVSDB lookup). May be a local cache
     * and if there is change then commit to DB
     */

    new_ovs_nbr = find_ospf_nbr_by_if_addr(ovs_oi,nbr->src);
    if (new_ovs_nbr)
    {
       VLOG_DBG ("Neighbor already present");
       ovsdb_idl_txn_abort(nbr_txn);
       return;
    }
    new_ovs_nbr = ovsrec_ospf_neighbor_insert (nbr_txn);
    if (NULL == new_ovs_nbr)
    {
        VLOG_DBG ("Neighbor insertion failed");
        ovsdb_idl_txn_abort(nbr_txn);
        return;
    }
    ovs_nbr = xmalloc(sizeof * ovs_oi->neighbors *
                                    (ovs_oi->n_neighbors + 1));
    for (i = 0; i < ovs_oi->n_neighbors; i++) {
                 ovs_nbr[i] = ovs_oi->neighbors[i];
    }
    ovs_nbr[ovs_oi->n_neighbors] = new_ovs_nbr;
    ovsrec_ospf_interface_set_neighbors (ovs_oi,ovs_nbr,ovs_oi->n_neighbors + 1);
    nbr_id = nbr->router_id.s_addr;
    ovsrec_ospf_neighbor_set_nbr_router_id (new_ovs_nbr,&nbr_id,1);

    ip_src = nbr->src.s_addr;
    ovsrec_ospf_neighbor_set_nbr_if_addr (new_ovs_nbr,&ip_src,1);
    /*  Non-zero TOS are not supported
        if (CHECK_FLAG(nbr->options,OSPF_OPTION_T))
        {
            nbr_option_cnt++;
            if(!value_nbr_option)
                value_nbr_option = xmalloc(OSPF_STAT_NAME_LEN * (nbr_option_cnt));
            else
                value_nbr_option = xrealloc(value_nbr_option,
                                      OSPF_STAT_NAME_LEN * (nbr_option_cnt));
            value_nbr_option[nbr_option_cnt -1 ] =
                OVSREC_OSPF_NEIGHBOR_NBR_OPTIONS_TYPE_OF_SERVICE;
        }
    */
    if (CHECK_FLAG(nbr->options,OSPF_OPTION_E))
    {
        nbr_option_cnt++;
        if(!value_nbr_option)
            value_nbr_option = xmalloc(OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        else
            value_nbr_option = xrealloc(value_nbr_option,
                                  OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        value_nbr_option[nbr_option_cnt -1 ] =
            OVSREC_OSPF_NEIGHBOR_NBR_OPTIONS_EXTERNAL_ROUTING;
    }
    if (CHECK_FLAG(nbr->options,OSPF_OPTION_MC))
    {
        nbr_option_cnt++;
        if(!value_nbr_option)
            value_nbr_option = xmalloc(OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        else
            value_nbr_option = xrealloc(value_nbr_option,
                                  OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        value_nbr_option[nbr_option_cnt -1 ] =
            OVSREC_OSPF_NEIGHBOR_NBR_OPTIONS_MULTICAST;
    }
    if (CHECK_FLAG(nbr->options,OSPF_OPTION_NP))
    {
        nbr_option_cnt++;
        if(!value_nbr_option)
            value_nbr_option = xmalloc(OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        else
            value_nbr_option = xrealloc(value_nbr_option,
                                  OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        value_nbr_option[nbr_option_cnt -1 ] =
            OVSREC_OSPF_NEIGHBOR_NBR_OPTIONS_TYPE_7_LSA;
    }
    if (CHECK_FLAG(nbr->options,OSPF_OPTION_EA))
    {
        nbr_option_cnt++;
        if(!value_nbr_option)
            value_nbr_option = xmalloc(OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        else
            value_nbr_option = xrealloc(value_nbr_option,
                                  OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        value_nbr_option[nbr_option_cnt -1 ] =
            OVSREC_OSPF_NEIGHBOR_NBR_OPTIONS_EXTERNAL_ATTRIBUTES_LSA;
    }
    if (CHECK_FLAG(nbr->options,OSPF_OPTION_DC))
    {
        nbr_option_cnt++;
        if(!value_nbr_option)
            value_nbr_option = xmalloc(OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        else
            value_nbr_option = xrealloc(value_nbr_option,
                                  OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        value_nbr_option[nbr_option_cnt -1 ] =
            OVSREC_OSPF_NEIGHBOR_NBR_OPTIONS_DEMAND_CIRCUITS;
    }
    if (CHECK_FLAG(nbr->options,OSPF_OPTION_O))
    {
        nbr_option_cnt++;
        if(!value_nbr_option)
            value_nbr_option = xmalloc(OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        else
            value_nbr_option = xrealloc(value_nbr_option,
                                  OSPF_STAT_NAME_LEN * (nbr_option_cnt));
        value_nbr_option[nbr_option_cnt -1 ] =
            OVSREC_OSPF_NEIGHBOR_NBR_OPTIONS_OPAQUE_LSA;
    }

    ovsrec_ospf_neighbor_set_nbr_options (new_ovs_nbr,value_nbr_option,
                                                             nbr_option_cnt);

    ovsrec_ospf_neighbor_set_nfsm_state (new_ovs_nbr,ospf_nsm_state[nbr->state].str);

    key_nbr_statistics =  xmalloc(OSPF_STAT_NAME_LEN * (OSPF_NEIGHBOR_STATISTICS_MAX));

    value_nbr_statistics =  xmalloc(sizeof *new_ovs_nbr->value_statistics *
                                 (OSPF_NEIGHBOR_STATISTICS_MAX));

    key_nbr_statistics [OSPF_NEIGHBOR_DB_SUMMARY_COUNT] = OSPF_KEY_NEIGHBOR_DB_SUMMARY_CNT;
    key_nbr_statistics [OSPF_NEIGHBOR_LS_REQUEST_COUNT] = OSPF_KEY_NEIGHBOR_LS_REQUEST_CNT;
    key_nbr_statistics [OSPF_NEIGHBOR_LS_RETRANSMIT_COUNT] = OSPF_KEY_NEIGHBOR_LS_RE_TRANSMIT_CNT;
    key_nbr_statistics [OSPF_NEIGHBOR_STATE_CHANGE_COUNT] = OSPF_KEY_NEIGHBOR_STATE_CHG_CNT;

    value_nbr_statistics [OSPF_NEIGHBOR_DB_SUMMARY_COUNT] = 0;
    value_nbr_statistics [OSPF_NEIGHBOR_LS_REQUEST_COUNT] = 0;
    value_nbr_statistics [OSPF_NEIGHBOR_LS_RETRANSMIT_COUNT] = 0;
    value_nbr_statistics [OSPF_NEIGHBOR_STATE_CHANGE_COUNT] = nbr->state_change;

    ovsrec_ospf_neighbor_set_statistics(new_ovs_nbr,key_nbr_statistics,
                          value_nbr_statistics,OSPF_NEIGHBOR_STATISTICS_MAX);

    quagga_gettime(QUAGGA_CLK_MONOTONIC,&tv);
    nbr_up_time = (1000000 * tv.tv_sec + tv.tv_usec)/1000;
    snprintf(buf,sizeof (buf),"%u",nbr_up_time);
    smap_clone (&nbr_status,&(new_ovs_nbr->status));
    smap_replace(&nbr_status, OSPF_KEY_NEIGHBOR_LAST_UP_TIMESTAMP, buf);
    ovsrec_ospf_neighbor_set_status(new_ovs_nbr,&nbr_status);

    status = ovsdb_idl_txn_commit_block(nbr_txn);
    if (TXN_SUCCESS != status &&
        TXN_UNCHANGED != status)
        VLOG_DBG ("NBR add transaction commit failed:%d",status);

    ovsdb_idl_txn_destroy(nbr_txn);
    smap_destroy (&nbr_status);
    free (ovs_nbr);
    free (key_nbr_statistics);
    free (value_nbr_statistics);
    free (value_nbr_option);
    return;
}

void
ovsdb_ospf_set_nbr_self_router_id  (char* ifname, struct in_addr if_addr,
                                                struct in_addr router_id)
{
    struct ovsrec_ospf_interface* ovs_oi = NULL;
    struct ovsrec_ospf_neighbor* ovs_nbr = NULL;
    struct ovsdb_idl_txn* nbr_txn = NULL;
    enum ovsdb_idl_txn_status status;
    int64_t nbr_router_id = 0;

    nbr_txn = ovsdb_idl_txn_create(idl);
    if (!nbr_txn)
    {
        VLOG_DBG ("Transaction create failed");
        return;
    }
    if (NULL == ifname)
    {
        VLOG_DBG ("No associated interface of neighbor");
        ovsdb_idl_txn_abort(nbr_txn);
        return;
    }
    ovs_oi = find_ospf_interface_by_name(ifname);
    if (NULL == ovs_oi)
    {
        VLOG_DBG ("No associated interface of neighbor");
        ovsdb_idl_txn_abort(nbr_txn);
        return;
    }
    ovs_nbr = find_ospf_nbr_by_if_addr(ovs_oi,if_addr);
    if (!ovs_nbr)
    {
       VLOG_DBG ("Self neighbor not present");
       ovsdb_idl_txn_abort(nbr_txn);
       return;
    }
    nbr_router_id = router_id.s_addr;
    ovsrec_ospf_neighbor_set_nbr_router_id(ovs_nbr,&nbr_router_id,1);
    status = ovsdb_idl_txn_commit_block(nbr_txn);
    if (TXN_SUCCESS != status &&
        TXN_UNCHANGED != status)
        VLOG_DBG ("NBR add transaction commit failed:%d",status);

    ovsdb_idl_txn_destroy(nbr_txn);
}


void
ovsdb_ospf_delete_nbr  (struct ospf_neighbor* nbr)
{
    struct ovsrec_ospf_interface* ovs_oi = NULL;
    struct ovsrec_ospf_neighbor** ovs_nbr = NULL;
    struct ovsrec_ospf_neighbor* old_ovs_nbr = NULL;
    struct ovsdb_idl_txn* nbr_txn = NULL;
    struct interface* intf = NULL;
    int64_t ip_src = 0;
    enum ovsdb_idl_txn_status status;
    int i = 0,j = 0;

    if (NULL == nbr)
    {
        VLOG_DBG ("No neighbor data to delete");
        return;
    }
    if (NULL == nbr->oi)
    {
        VLOG_DBG ("No associated interface of neighbor");
        return;
    }

    nbr_txn = ovsdb_idl_txn_create(idl);
    if (!nbr_txn)
    {
        VLOG_DBG ("Transaction create failed");
        return;
    }
    intf = nbr->oi->ifp;
    if (NULL == intf)
    {
        VLOG_DBG ("No associated interface of neighbor");
        ovsdb_idl_txn_abort(nbr_txn);
        return;
    }
    ovs_oi = find_ospf_interface_by_name(intf->name);
    if (NULL == ovs_oi)
    {
        VLOG_DBG ("No associated interface of neighbor");
        ovsdb_idl_txn_abort(nbr_txn);
        return;
    }
    /* Fix me : Update NBR instead of looping through
     * all the neighbor (OVSDB lookup). May be a local cache
     * and if there is change then commit to DB
     */

    old_ovs_nbr = find_ospf_nbr_by_if_addr(ovs_oi,nbr->src);
    if (!old_ovs_nbr)
    {
       VLOG_DBG ("Neighbor not found");
       ovsdb_idl_txn_abort(nbr_txn);
       return;
    }
    ovs_nbr = xmalloc(sizeof * ovs_oi->neighbors *
                                    (ovs_oi->n_neighbors - 1));

    ip_src = nbr->src.s_addr;
    for (i = 0,j = 0; i < ovs_oi->n_neighbors; i++) {
       if (ip_src != ovs_oi->neighbors[i]->nbr_if_addr[0])
          ovs_nbr[j++] = ovs_oi->neighbors[i];
    }
    ovsrec_ospf_interface_set_neighbors (ovs_oi,ovs_nbr,ovs_oi->n_neighbors - 1);

    ovsrec_ospf_neighbor_delete (old_ovs_nbr);

    status = ovsdb_idl_txn_commit_block(nbr_txn);
    if (TXN_SUCCESS != status &&
        TXN_UNCHANGED != status)
        VLOG_DBG ("NBR delete transaction commit failed:%d",status);

    ovsdb_idl_txn_destroy(nbr_txn);
    free (ovs_nbr);
    return;
}


void
ovsdb_ospf_delete_nbr_self  (struct ospf_neighbor* nbr, char* ifname)
{
    struct ovsrec_ospf_interface* ovs_oi = NULL;
    struct ovsrec_ospf_neighbor** ovs_nbr = NULL;
    struct ovsrec_ospf_neighbor* old_ovs_nbr = NULL;
    struct ovsdb_idl_txn* nbr_txn = NULL;
    int64_t ip_src = 0;
    enum ovsdb_idl_txn_status status;
    int i = 0,j = 0;

    if (NULL == nbr)
    {
        VLOG_DBG ("No neighbor data to delete");
        return;
    }
    if (NULL == nbr->oi)
    {
        VLOG_DBG ("No associated interface of neighbor");
        return;
    }

    nbr_txn = ovsdb_idl_txn_create(idl);
    if (!nbr_txn)
    {
        VLOG_DBG ("Transaction create failed");
        return;
    }
    if (NULL == ifname)
    {
        VLOG_DBG ("No associated interface of neighbor");
        ovsdb_idl_txn_abort(nbr_txn);
        return;
    }
    ovs_oi = find_ospf_interface_by_name(ifname);
    if (NULL == ovs_oi)
    {
        VLOG_DBG ("No associated interface of neighbor");
        ovsdb_idl_txn_abort(nbr_txn);
        return;
    }
    /* Fix me : Update NBR instead of looping through
     * all the neighbor (OVSDB lookup). May be a local cache
     * and if there is change then commit to DB
     */

    old_ovs_nbr = find_ospf_nbr_by_if_addr(ovs_oi,nbr->src);
    if (!old_ovs_nbr)
    {
       VLOG_DBG ("Neighbor not found");
       ovsdb_idl_txn_abort(nbr_txn);
       return;
    }
    ovs_nbr = xmalloc(sizeof * ovs_oi->neighbors *
                                    (ovs_oi->n_neighbors - 1));

    ip_src = nbr->src.s_addr;
    for (i = 0,j = 0; i < ovs_oi->n_neighbors; i++) {
       if (ip_src != ovs_oi->neighbors[i]->nbr_if_addr[0])
          ovs_nbr[j++] = ovs_oi->neighbors[i];
    }
    ovsrec_ospf_interface_set_neighbors (ovs_oi,ovs_nbr,ovs_oi->n_neighbors - 1);

    ovsrec_ospf_neighbor_delete (old_ovs_nbr);

    status = ovsdb_idl_txn_commit_block(nbr_txn);
    if (TXN_SUCCESS != status &&
        TXN_UNCHANGED != status)
        VLOG_DBG ("NBR delete transaction commit failed:%d",status);

    ovsdb_idl_txn_destroy(nbr_txn);
    free (ovs_nbr);
    return;
}

void
ovsdb_ospf_add_area_to_router (int ospf_intance,struct in_addr area_id)
{
    int64_t *area;
    struct ovsrec_ospf_router* ospf_router_row = NULL;
    struct ovsrec_ospf_area* area_row = NULL;
    struct ovsrec_ospf_area **area_list;
    struct ovsdb_idl_txn* area_txn = NULL;
    enum ovsdb_idl_txn_status status;
    int i = 0;

    area_txn = ovsdb_idl_txn_create(idl);
    if (!area_txn)
    {
        VLOG_DBG ("Transaction create failed");
        return;
    }

    ospf_router_row =
        ovsdb_ospf_get_router_by_instance_num (ospf_intance);
    if (!ospf_router_row)
    {
       VLOG_DBG ("No OSPF router found");
       ovsdb_idl_txn_abort(area_txn);
       return;
    }

    area_row = ovsrec_ospf_area_insert(area_txn);
    if (!area_row)
    {
       VLOG_DBG ("OSPF area insert failed");
       ovsdb_idl_txn_abort(area_txn);
       return;
    }

    /* Insert OSPF_Area table reference in OSPF_Router table. */
    area = xmalloc(sizeof(int64_t) * (ospf_router_row->n_areas + 1));
    area_list = xmalloc(sizeof * ospf_router_row->key_areas *
                              (ospf_router_row->n_areas + 1));
    for (i = 0; i < ospf_router_row->n_areas; i++)
    {
        area[i] = ospf_router_row->key_areas[i];
        area_list[i] = ospf_router_row->value_areas[i];
    }
    area[ospf_router_row->n_areas] = area_id.s_addr;
    area_list[ospf_router_row->n_areas] =
                        CONST_CAST(struct ovsrec_ospf_area *, area_row);
    ovsrec_ospf_router_set_areas(ospf_router_row, area, area_list,
                               (ospf_router_row->n_areas + 1));
    ovsdb_ospf_set_area_tbl_default (area_row);

    status = ovsdb_idl_txn_commit_block(area_txn);
    if (TXN_SUCCESS != status &&
        TXN_UNCHANGED != status)
        VLOG_DBG ("Area transaction commit failed:%d",status);

    ovsdb_idl_txn_destroy(area_txn);

    free(area);
    free(area_list);

    return;
}

void
ovsdb_ospf_set_spf_statistics (int instance, struct in_addr area_id,
                              long spf_ts, int spf_count)
{
    struct ovsrec_ospf_area* ovs_area = NULL;
    struct ovsrec_ospf_router* ovs_ospf = NULL;
    bool is_found = false;
    char buf[32] = {0};
    struct smap spf_smap;
    struct ovsdb_idl_txn* spf_txn = NULL;
    enum ovsdb_idl_txn_status status;
    int i = 0;

    spf_txn = ovsdb_idl_txn_create (idl);
    if (!spf_txn)
    {
       VLOG_DBG ("Transaction create failed");
       return;
    }
    ovs_ospf = ovsdb_ospf_get_router_by_instance_num (instance);
    if (!ovs_ospf)
    {
       VLOG_DBG ("No OSPF instance");
       return;
    }
    for (i = 0 ; i < ovs_ospf->n_areas ; i++)
    {
       if (ovs_ospf->key_areas[i] == area_id.s_addr)
        {
            ovs_area = ovs_ospf->value_areas[i];
            is_found = true;
            break;
        }
    }

    if (!is_found)
    {
       VLOG_DBG ("No area %s found", inet_ntoa (area_id));
       ovsdb_idl_txn_abort (spf_txn);
       return;
    }

    snprintf(buf,sizeof (buf),"%u",spf_ts);
    smap_clone (&spf_smap, &(ovs_area->status));
    smap_replace (&spf_smap, OSPF_KEY_AREA_SPF_LAST_RUN, buf);

    ovsrec_ospf_area_set_status(ovs_area,&spf_smap);

    for (i = 0 ; i < ovs_area->n_statistics ; i++)
    {
        if (0 == strcmp (ovs_area->key_statistics[i],
                      OSPF_KEY_AREA_STATS_SPF_EXEC)) {
            ovs_area->value_statistics[i] = (int64_t)spf_count;
            break;
        }
    }

    ovsrec_ospf_area_set_statistics(ovs_area,ovs_area->key_statistics,
                        ovs_area->value_statistics,ovs_area->n_statistics);

    status = ovsdb_idl_txn_commit_block (spf_txn);
    if (TXN_SUCCESS != status &&
        TXN_UNCHANGED != status)
        VLOG_DBG ("Set OSPF SPF statistics failed : %d",status);

    ovsdb_idl_txn_destroy (spf_txn);

    smap_destroy (&spf_smap);
}

void
ovsdb_ospf_set_dead_time_intervals (char* ifname, int interval_type,long time_msec,
                                      struct in_addr src)
{
    struct smap interval_smap;
    struct ovsrec_ospf_interface* ospf_if_row = NULL;
    struct ovsrec_ospf_neighbor* ospf_nbr_row = NULL;
    struct ovsdb_idl_txn* if_txn = NULL;
    enum ovsdb_idl_txn_status status;
    char buf[32] = {0};

    if (NULL == ifname)
    {
        VLOG_DBG ("Invalid Interface/Neighbor name");
        return;
    }
    if_txn = ovsdb_idl_txn_create (idl);
    if (!if_txn)
    {
       VLOG_DBG ("Transaction create failed");
       return;
       //smap_destroy (&interval_smap);
    }
    ospf_if_row = find_ospf_interface_by_name(ifname);
    if (!ospf_if_row)
    {
       VLOG_DBG ("No OSPF interface found");
       ovsdb_idl_txn_abort (if_txn);
       return;
    }
    ospf_nbr_row = find_ospf_nbr_by_if_addr(ospf_if_row,src);
    if (!ospf_nbr_row)
    {
       VLOG_DBG ("No OSPF Neighbor found");
       ovsdb_idl_txn_abort (if_txn);
       return;
    }
    snprintf(buf,sizeof (buf),"%u",time_msec);
    smap_clone (&interval_smap,&(ospf_nbr_row->status));
    smap_replace(&interval_smap, OSPF_KEY_NEIGHBOR_DEAD_TIMER_DUE, buf);
    ovsrec_ospf_neighbor_set_status(ospf_nbr_row,&interval_smap);

    status = ovsdb_idl_txn_commit_block (if_txn);
    if (TXN_SUCCESS != status &&
        TXN_UNCHANGED != status)
        VLOG_DBG ("OSPF interval commit failed : %d",status);

    ovsdb_idl_txn_destroy (if_txn);
    smap_destroy (&interval_smap);

    return;
}

void
ovsdb_ospf_set_hello_time_intervals (const char* ifname, int interval_type,long time_msec)
{
    struct smap interval_smap;
    struct ovsrec_ospf_interface* ospf_if_row = NULL;
    struct ovsrec_ospf_neighbor* ospf_nbr_row = NULL;
    struct ovsdb_idl_txn* if_txn = NULL;
    enum ovsdb_idl_txn_status status;
    char buf[32] = {0};

    if (NULL == ifname)
    {
        VLOG_DBG ("Invalid Interface/Neighbor name");
        return;
    }
    //smap_init (&interval_smap);
    if_txn = ovsdb_idl_txn_create (idl);
    if (!if_txn)
    {
       VLOG_DBG ("Transaction create failed");
       return;
       //smap_destroy (&interval_smap);
    }

    ospf_if_row = find_ospf_interface_by_name(ifname);
    if (!ospf_if_row)
    {
       VLOG_DBG ("No OSPF interface found");
       ovsdb_idl_txn_abort (if_txn);
       return;
    }
    snprintf(buf,sizeof (buf),"%u",time_msec);
    smap_clone (&interval_smap,&(ospf_if_row->status));
    smap_replace (&interval_smap, OSPF_KEY_HELLO_DUE, buf);
    ovsrec_ospf_interface_set_status(ospf_if_row,&interval_smap);

    status = ovsdb_idl_txn_commit_block (if_txn);
    if (TXN_SUCCESS != status &&
        TXN_UNCHANGED != status)
        VLOG_DBG ("OSPF interval commit failed : %d",status);

    ovsdb_idl_txn_destroy (if_txn);
    smap_destroy (&interval_smap);
}


/* Set the values in the area table to default. */
void ovsdb_ospf_set_area_tbl_default (const struct ovsrec_ospf_area *area_row)
{
    char** key_area_statistics = NULL;
    int64_t *area_stat_value = NULL;

    if (area_row == NULL)
    {
        return;
    }
    ovsrec_ospf_area_set_area_type(area_row,
                             OVSREC_OSPF_AREA_AREA_TYPE_DEFAULT);
    ovsrec_ospf_area_set_nssa_translator_role(area_row,
                             OVSREC_OSPF_AREA_NSSA_TRANSLATOR_ROLE_CANDIDATE);

    key_area_statistics =
        xmalloc(OSPF_STAT_NAME_LEN * (OSPF_AREA_STATISTICS_MAX));
    area_stat_value =
        xmalloc(sizeof *area_row->value_statistics *
                              (OSPF_AREA_STATISTICS_MAX));

    /* OPS_TODO : Map OSPF memtypes in memtype.h and use XSTRDUP */
    key_area_statistics[OSPF_AREA_STATISTICS_SPF_CALC] =
                           OSPF_KEY_AREA_STATS_SPF_EXEC;
    key_area_statistics[OSPF_AREA_STATISTICS_ABR_COUNT] =
                           OSPF_KEY_AREA_STATS_ABR_COUNT;
    key_area_statistics[OSPF_AREA_STATISTICS_ASBR_COUNT] =
                           OSPF_KEY_AREA_STATS_ASBR_COUNT;

    area_stat_value[OSPF_AREA_STATISTICS_SPF_CALC] = 0;
    area_stat_value[OSPF_AREA_STATISTICS_ABR_COUNT] = 0;
    area_stat_value[OSPF_AREA_STATISTICS_ASBR_COUNT] = 0;

    ovsrec_ospf_area_set_statistics(area_row,key_area_statistics,
                        area_stat_value,OSPF_AREA_STATISTICS_MAX);

    free (key_area_statistics);
    free(area_stat_value);
}


/* Set default OSPF interface config values  */
void ovsdb_ospf_set_interface_if_config_tbl_default  (const struct ovsrec_port *ovs_port)
{
    char** key_ospf_interval = NULL;
    int64_t* value_ospf_interval = NULL;
    int64_t ospf_if_cost = 0;
    int64_t ospf_priority = 0;
    bool ospf_mtu_ignore = false;
    char show_str[10];

    if (ovs_port == NULL)
    {
        return;
    }

    key_ospf_interval =
        xmalloc(OSPF_STAT_NAME_LEN * (OSPF_INTERVAL_MAX));

    value_ospf_interval =
           xmalloc(sizeof *ovs_port->value_ospf_intervals*
                                 (OSPF_INTERVAL_MAX));

    key_ospf_interval [OSPF_INTERVAL_TRANSMIT_DELAY] = OSPF_KEY_TRANSMIT_DELAY;
    key_ospf_interval [OSPF_INTERVAL_RETRANSMIT_INTERVAL] = OSPF_KEY_RETRANSMIT_INTERVAL;
    key_ospf_interval [OSPF_INTERVAL_HELLO_INTERVAL] = OSPF_KEY_HELLO_INTERVAL;
    key_ospf_interval [OSPF_INTERVAL_DEAD_INTERVAL] = OSPF_KEY_DEAD_INTERVAL;

    value_ospf_interval [OSPF_INTERVAL_TRANSMIT_DELAY] = OSPF_TRANSMIT_DELAY_DEFAULT;
    value_ospf_interval [OSPF_INTERVAL_RETRANSMIT_INTERVAL] = OSPF_RETRANSMIT_INTERVAL_DEFAULT;
    value_ospf_interval [OSPF_INTERVAL_HELLO_INTERVAL] = OSPF_HELLO_INTERVAL_DEFAULT;
    value_ospf_interval [OSPF_INTERVAL_DEAD_INTERVAL] = OSPF_ROUTER_DEAD_INTERVAL_DEFAULT;


    ovsrec_port_set_ospf_intervals(ovs_port,key_ospf_interval,value_ospf_interval,OSPF_INTERVAL_MAX);

    ospf_priority = OSPF_ROUTER_PRIORITY_DEFAULT;
    ovsrec_port_set_ospf_priority(ovs_port,&ospf_priority,1);
    ospf_mtu_ignore = OSPF_MTU_IGNORE_DEFAULT;
    ovsrec_port_set_ospf_mtu_ignore(ovs_port,&ospf_mtu_ignore,1);
    ospf_if_cost = OSPF_OUTPUT_COST_DEFAULT;
    ovsrec_port_set_ospf_if_out_cost(ovs_port,&ospf_if_cost,1);
    ovsrec_port_set_ospf_if_type(ovs_port,OVSREC_PORT_OSPF_IF_TYPE_OSPF_IFTYPE_BROADCAST);

}

/* Default the values if OSPF_interface_Config table. */
void ospf_interface_tbl_default(
                  const struct ovsrec_ospf_interface *ospf_if_row)
{
    struct smap smap;
    char show_str[10] = {0};

    if (ospf_if_row == NULL)
       return;
    snprintf(show_str, sizeof(show_str), "%d", OSPF_INTERFACE_ACTIVE);
    smap_clone (&smap, &(ospf_if_row->status));
    smap_replace (&smap, OSPF_KEY_INTERFACE_ACTIVE, (const char *)show_str);

    ovsrec_ospf_interface_set_status(ospf_if_row,&smap);

    smap_destroy(&smap);
}


/* Set the reference to the interface row to the area table. */
void
ovsdb_area_set_interface(int instance,struct in_addr area_id,
                         char *ifname)
{
    struct ovsrec_ospf_interface **ospf_interface_list;
    struct ovsrec_ospf_interface* interface_row = NULL;
    struct ovsrec_port* ovs_port = NULL;
    struct ovsrec_ospf_router* ovs_ospf = NULL;
    struct ovsrec_ospf_area* area_row = NULL;
    struct ovsdb_idl_txn* intf_txn = NULL;
    enum ovsdb_idl_txn_status status;
    struct smap area_smap;
    char buf[10] = {0};
    int i = 0;

    ovs_ospf = ovsdb_ospf_get_router_by_instance_num (instance);
    if (!ovs_ospf)
    {
       VLOG_DBG ("No associated OSPF instance exist");
       return;
    }
    area_row = ovsrec_ospf_area_get_area_by_id(ovs_ospf,area_id);
    if (!area_row)
    {
       VLOG_DBG ("No associated OSPF area : %d exist",area_id.s_addr);
       return;
    }

    intf_txn = ovsdb_idl_txn_create(idl);
    if (!intf_txn)
    {
        VLOG_DBG ("Transaction create failed");
        return;
    }
    ovs_port = find_port_by_name(ifname);
    if (!ovs_port)
    {
       VLOG_DBG ("No associated port exist");
       return;
    }

    interface_row = ovsrec_ospf_interface_insert(intf_txn);
    if (!interface_row)
    {
       VLOG_DBG ("OSPF interface insert failed");
       ovsdb_idl_txn_abort(intf_txn);
       return;
    }
    /* Insert OSPF_Interface table reference in OSPF_Area table. */
    ospf_interface_list = xmalloc(sizeof * area_row->ospf_interfaces *
                              (area_row->n_ospf_interfaces + 1));
    for (i = 0; i < area_row->n_ospf_interfaces; i++) {
        ospf_interface_list[i] = area_row->ospf_interfaces[i];
    }
    ospf_interface_list[area_row->n_ospf_interfaces] =
                        CONST_CAST(struct ovsrec_ospf_interface *, interface_row);
    ovsrec_ospf_area_set_ospf_interfaces(area_row, ospf_interface_list,
                               (area_row->n_ospf_interfaces + 1));

    ovsdb_ospf_set_interface_if_config_tbl_default (ovs_port);
    ovsrec_ospf_interface_set_ifsm_state(interface_row,
                                             OSPF_INTERFACE_IFSM_DEPEND_ON);
    ovsrec_ospf_interface_set_name(interface_row, ifname);

    ospf_interface_tbl_default(interface_row);

    /* OPS_TODO : Need to check for passive interfaces */
    snprintf (buf,sizeof (buf),"%d",area_row->n_ospf_interfaces);
    smap_clone (&area_smap,&(area_row->status));
    smap_replace (&area_smap,OSPF_KEY_AREA_ACTIVE_INTERFACE,buf);
    ovsrec_ospf_area_set_status(area_row,&area_smap);

    ovsrec_ospf_interface_set_port(interface_row,ovs_port);
    status = ovsdb_idl_txn_commit_block(intf_txn);
    if (TXN_SUCCESS != status &&
        TXN_UNCHANGED != status)
        VLOG_DBG ("OSPF interface transaction commit failed : %d",status);

    ovsdb_idl_txn_destroy(intf_txn);

    free(ospf_interface_list);

    return;
}

void
ovsdb_ospf_update_ifsm_state  (char* ifname, int ism_state)
{
    struct ovsrec_ospf_interface* ovs_oi = NULL;
    struct ovsdb_idl_txn* txn = NULL;
    enum ovsdb_idl_txn_status status;

    if (NULL == ifname)
    {
       VLOG_DBG ("No OSPF interface found");
       return;
    }
    ovs_oi = find_ospf_interface_by_name(ifname);
    if (!ovs_oi)
    {
       VLOG_DBG ("No OSPF interface found");
       return;
    }
    txn = ovsdb_idl_txn_create(idl);
    if (!txn)
    {
        VLOG_DBG ("Transaction create failed");
        return;
    }

    ovsrec_ospf_interface_set_ifsm_state(ovs_oi,ospf_ism_state[ism_state].str);

    status = ovsdb_idl_txn_commit_block(txn);
    if (TXN_SUCCESS != status &&
        TXN_UNCHANGED != status)
        VLOG_DBG ("OSPF interface transaction commit failed : %d",status);

    ovsdb_idl_txn_destroy(txn);
}


/* Check if any non default values is present in area table.
    If present then return false. Else true. */
int
ovsdb_ospf_is_area_tbl_empty(const struct ovsrec_ospf_area *ospf_area_row)
{
    const char *val;
    int i = 0;

    if (ospf_area_row->n_ospf_interfaces > 0)
        return false;

   if (ospf_area_row->area_type &&
          (0 != strcmp (ospf_area_row->area_type,OVSREC_OSPF_AREA_AREA_TYPE_DEFAULT)))
            return false;

    if (0 == strcmp (ospf_area_row->nssa_translator_role,OVSREC_OSPF_AREA_NSSA_TRANSLATOR_ROLE_ALWAYS) ||
        0 == strcmp (ospf_area_row->nssa_translator_role,OVSREC_OSPF_AREA_NSSA_TRANSLATOR_ROLE_CANDIDATE))
        return false;

    if (ospf_area_row->n_ospf_vlinks > 0)
        return false;

    if (ospf_area_row->n_ospf_area_summary_addresses > 0)
        return false;

    if (ospf_area_row->ospf_auth_type)
        return false;

    return true;
}

/* Remove the area row matching the area id and remove reference from the router table. */
void
ovsdb_ospf_remove_area_from_router (int instance,
                              struct in_addr area_id)
{
    int64_t *area;
    struct ovsrec_ospf_area **area_list;
    struct ovsrec_ospf_router* ospf_router_row = NULL;
    struct ovsrec_ospf_area* ovs_area = NULL;
    struct ovsdb_idl_txn* txn = NULL;
    enum ovsdb_idl_txn_status status;
    int i = 0, j;

    txn = ovsdb_idl_txn_create(idl);
    if (!txn)
    {
        VLOG_DBG ("Transaction create failed");
        return;
    }
    ospf_router_row = ovsdb_ospf_get_router_by_instance_num (instance);
    if (!ospf_router_row)
    {
        VLOG_DBG ("No OSPF instance there");
        ovsdb_idl_txn_abort(txn);
        return;
    }

    ovs_area = ovsrec_ospf_area_get_area_by_id(ospf_router_row,area_id);
    if (!ovs_area)
    {
        VLOG_DBG ("No OSPF area there");
        ovsdb_idl_txn_abort(txn);
        return;
    }
    if (ovsdb_ospf_is_area_tbl_empty(ovs_area))
    {
        /* Remove OSPF_area table reference in OSPF_Router table. */
        area = xmalloc(sizeof(int64_t) * (ospf_router_row->n_areas - 1));
        area_list = xmalloc(sizeof * ospf_router_row->key_areas *
                                  (ospf_router_row->n_areas - 1));
        for (i = 0, j = 0; i < ospf_router_row->n_areas; i++) {
            if(ospf_router_row->key_areas[i] !=  area_id.s_addr) {
                area[j] = ospf_router_row->key_areas[i];
                area_list[j] = ospf_router_row->value_areas[i];
                j++;
            }
        }
        ovsrec_ospf_router_set_areas(ospf_router_row, area, area_list,
                                   (ospf_router_row->n_areas - 1));
        ovsrec_ospf_area_delete(ovs_area);

        free(area);
        free(area_list);
    }
    status = ovsdb_idl_txn_commit_block(txn);
    if (TXN_SUCCESS != status &&
        TXN_UNCHANGED != status)
        VLOG_DBG ("Transaction commit error");

    ovsdb_idl_txn_destroy(txn);
}

/* Remove the interface row matching the interface name and remove the reference from
     area table. */
void
ovsdb_ospf_remove_interface_from_area (int instance, struct in_addr area_id,
                                      char* ifname)
{
    struct ovsrec_ospf_interface **ospf_interface_list;
    struct ovsrec_ospf_area* area_row = NULL;
    struct ovsrec_ospf_router* ovs_ospf = NULL;
    struct ovsrec_ospf_interface* ovs_oi = NULL;
    struct ovsrec_port* ovs_port = NULL;
    struct ovsdb_idl_txn* txn = NULL;
    enum ovsdb_idl_txn_status status;
    struct smap area_smap;
    char buf[10] = {0};
    int i, j;

    txn = ovsdb_idl_txn_create(idl);
    if (!txn)
    {
        VLOG_DBG ("Transaction create failed");
        return;
    }
    ovs_ospf = ovsdb_ospf_get_router_by_instance_num (instance);
    if (!ovs_ospf)
    {
        VLOG_DBG ("No OSPF instance there : %d",instance);
        ovsdb_idl_txn_abort(txn);
        return;
    }
    area_row = ovsrec_ospf_area_get_area_by_id(ovs_ospf,area_id);
    if (!area_row)
    {
        VLOG_DBG ("No OSPF area there");
        ovsdb_idl_txn_abort(txn);
        return;
    }
    ospf_interface_list = xmalloc(sizeof * area_row->ospf_interfaces *
                              (area_row->n_ospf_interfaces - 1));
    for (i = 0, j = 0; i < area_row->n_ospf_interfaces; i++)
    {
        if (strcmp(area_row->ospf_interfaces[i]->name,  ifname) != 0)
        {
            ospf_interface_list[j] = area_row->ospf_interfaces[i];
            j++;
        }
        else
            ovs_oi = area_row->ospf_interfaces[i];
    }
    if (ovs_oi)
    {
       ovsrec_ospf_area_set_ospf_interfaces(area_row, ospf_interface_list,
                                               (area_row->n_ospf_interfaces - 1));
       ovs_port = ovs_oi->port;

       ovsrec_ospf_interface_delete(ovs_oi);

       /* OPS_TODO : Need to check for passive interfaces */
       snprintf (buf,sizeof (buf),"%d",area_row->n_ospf_interfaces);
       smap_clone (&area_smap,&(area_row->status));
       smap_replace (&area_smap,OSPF_KEY_AREA_ACTIVE_INTERFACE,buf);
       ovsrec_ospf_area_set_status(area_row,&area_smap);
    }
    else
    {
       VLOG_DBG ("No OSPF Interface there for the area");
       ovsdb_idl_txn_abort(txn);
       free(ospf_interface_list);
       return;
    }

    status = ovsdb_idl_txn_commit_block(txn);
    if (TXN_SUCCESS != status &&
        TXN_UNCHANGED != status)
        VLOG_DBG ("Transaction commit error");

    ovsdb_idl_txn_destroy(txn);

    free(ospf_interface_list);
}

int
modify_ospf_network_config (struct ovsdb_idl *idl, struct ospf *ospf_cfg,
    const struct ovsrec_ospf_router *ospf_mod_row)
{
    struct prefix_ipv4 p;
    struct in_addr area_id;
    bool is_network_found = false;
    int i = 0, ret;
    struct listnode* intf_node = NULL, *intf_nnode = NULL;
    struct route_node *rn = NULL;
    struct ospf_network* ospf_netwrk = NULL;
    char prefix_str[32] = {0};

    memset (&p,0,sizeof(p));
    for (i = 0 ; i < ospf_mod_row->n_networks; i++)
    {
        (void)str2prefix_ipv4(ospf_mod_row->key_networks[i],&p);
        area_id.s_addr =  (in_addr_t)(ospf_mod_row->value_networks[i]);

        ret = ospf_network_set (ospf_cfg, &p, area_id);
        if (ret == 0)
        {
          VLOG_DBG ("Network statement prefix:%s area:%d exist",ospf_mod_row->key_networks[i],area_id.s_addr);
          continue;
        }
    }
    /* Check if any network is deleted via. no network command */
    for (rn = route_top (ospf_cfg->networks); rn; rn = route_next (rn))
    {
        /* Continue if no network information is present */
        if(NULL == rn->info)
            continue;
        is_network_found = false;
        for (i = 0 ; i < ospf_mod_row->n_networks ; i++)
        {
            memset(prefix_str,0,sizeof(prefix_str));
            (void)prefix2str(&rn->p,prefix_str,sizeof(prefix_str));
            if (0 == strcmp (prefix_str,ospf_mod_row->key_networks[i]))
            {
                 is_network_found = true;
                 break;
            }
        }
        if (!is_network_found)
        {
            ospf_netwrk = (struct ospf_network*)rn->info;
            ospf_network_unset(ospf_cfg,&rn->p,ospf_netwrk->area_id);
            // TODO:Delete area only if it has no default values

        }
    }
    return 0;
}

void
insert_ospf_router_instance(struct ovsdb_idl *idl, struct ovsrec_ospf_router* ovs_ospf, int64_t instance_number)
{
    struct ospf* ospf = NULL;
    int i = 0;

    /* Check if by any chance the ospf instance is already present */
    ospf = ospf_lookup_by_instance(instance_number);
    if (ospf == NULL)
    {
        ospf = ospf_new ();
        ospf->ospf_inst = instance_number;
        ospf_add (ospf);

  #ifdef HAVE_OPAQUE_LSA
        ospf_opaque_type11_lsa_init (ospf);
  #endif /* HAVE_OPAQUE_LSA */
    }
    else
        VLOG_DBG("%s : That's wierd OSPF instance already present",__FUNCTION__);

    if(!ospf){
        VLOG_DBG("OSPF instance Insertion failed");
        return;
    }
}

void
modify_ospf_router_instance(struct ovsdb_idl *idl,
    const struct ovsrec_ospf_router* ovs_ospf, int64_t instance_number)
{
    const struct ovsrec_ospf_router *ospf_mod_row = ovs_ospf;
    const struct ovsdb_idl_column *column = NULL;
    struct ospf *ospf_instance;
    int ret_status = -1;

    ospf_instance = ospf_lookup_by_instance(instance_number);
    if (!ospf_instance)
    {
         VLOG_DBG ("No OSPF config found!Critical error");
         return;
    }

    /* Check if router_id is modified */
    if (OVSREC_IDL_IS_COLUMN_MODIFIED(ovsrec_ospf_router_col_router_id, idl_seqno)) {
        ret_status = modify_ospf_router_id_config(ospf_instance, ovs_ospf);
        if (!ret_status) {
            VLOG_DBG("OSPF router_id set to %s", inet_ntoa(ospf_instance->router_id));
        }
        else
             VLOG_DBG("OSPF router_id set Failed");
    }

    /* Check if router_config is modified */
    if (OVSREC_IDL_IS_COLUMN_MODIFIED(ovsrec_ospf_router_col_other_config, idl_seqno)) {
        ret_status = modify_ospf_router_config(ospf_instance, ovs_ospf);
        if (!ret_status) {
            VLOG_DBG("OSPF router config set");
        }
    }

    /* Check if stub_router_config is modified */
    if (OVSREC_IDL_IS_COLUMN_MODIFIED(ovsrec_ospf_router_col_stub_router_adv, idl_seqno)) {
        ret_status = modify_ospf_stub_router_config(idl,ospf_instance, ovs_ospf);
        if (!ret_status) {
            VLOG_DBG("OSPF router stub router config set");
        }
    }

    /* Check if network is modified */
    if (OVSREC_IDL_IS_COLUMN_MODIFIED(ovsrec_ospf_router_col_networks, idl_seqno)) {
        ret_status = modify_ospf_network_config(idl,ospf_instance, ovs_ospf);
        if (!ret_status) {
            VLOG_DBG("OSPF router network set");
        }
    }
    else
        VLOG_DBG("OSPF router network not set");

}

void
delete_ospf_router_instance (struct ovsdb_idl *idl)
{
    struct ovsrec_vrf* ovs_vrf;
    struct ospf *ospf_instance;
    struct listnode *node = NULL,*nnode = NULL;
    int i;

    for (ALL_LIST_ELEMENTS(om->ospf,node,nnode,ospf_instance)){
        bool match_found = 0;

        OVSREC_VRF_FOR_EACH (ovs_vrf, idl) {
            for (i = 0; i < ovs_vrf->n_ospf_routers; i++)
            {
                if ( ospf_instance->ospf_inst == ovs_vrf->key_ospf_routers[i]){
                    match_found = 1;
                    break;
                }

            if (!match_found) {
                VLOG_DBG("ospf_instance->ospf_inst: %d will be deleted from OSPFD\n", ospf_instance->ospf_inst);
                ospf_finish(ospf_instance);
            }
        }
    }
  }
}

static void
ospf_router_read_ovsdb_apply_changes(struct ovsdb_idl *idl)
{
    const struct ovsrec_vrf *ovs_vrf = NULL;
    const struct ovsrec_ospf_router* ovs_ospf = NULL;
    int i = 0;

     OVSREC_VRF_FOR_EACH(ovs_vrf, idl) {
        for (i = 0; i < ovs_vrf->n_ospf_routers; i++) {
            ovs_ospf = ovs_vrf->value_ospf_routers[i];
            if (OVSREC_IDL_IS_ROW_INSERTED(ovs_ospf, idl_seqno)) {
                    insert_ospf_router_instance(idl, ovs_ospf,ovs_vrf->key_ospf_routers[i]);
            }
            if (OVSREC_IDL_IS_ROW_MODIFIED(ovs_ospf, idl_seqno) ||
                (OVSREC_IDL_IS_ROW_INSERTED(ovs_ospf, idl_seqno))) {
                    modify_ospf_router_instance(idl, ovs_ospf,ovs_vrf->key_ospf_routers[i]);
            }
        }
    }
}

static void
ospf_set_hostname (char *hostname)
{
    if (host.name)
        XFREE (MTYPE_HOST, host.name);

    host.name = XSTRDUP(MTYPE_HOST, hostname);
}

static void
ospf_apply_global_changes (void)
{
    const struct ovsrec_system *ovs;

    ovs = ovsrec_system_first(idl);
    if (OVSREC_IDL_ANY_TABLE_ROWS_DELETED(ovs, idl_seqno)) {
        VLOG_DBG ("First Row deleted from Open_vSwitch tbl\n");
        return;
    }
    if (!OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(ovs, idl_seqno) &&
            !OVSREC_IDL_ANY_TABLE_ROWS_MODIFIED(ovs, idl_seqno)) {
        VLOG_DBG ("No Open_vSwitch cfg changes");
        return;
    }

//Not needed to set hostname.
    if (ovs) {
        /* Update the hostname */
        ospf_set_hostname(ovs->hostname);
    }

    // TODO: Add reconfigurations that will be needed by OSPF daemon
}

static int
ospf_apply_port_changes (struct ovsdb_idl *idl)
{
   const struct ovsrec_port* port_first = NULL;

   port_first = ovsrec_port_first(idl);
   /*
    * Check if any table changes present.
    * If no change just return from here
    */
    if (port_first && !OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(port_first, idl_seqno)
        && !OVSREC_IDL_ANY_TABLE_ROWS_DELETED(port_first, idl_seqno)
        && !OVSREC_IDL_ANY_TABLE_ROWS_MODIFIED(port_first, idl_seqno)) {
            VLOG_DBG ("No Port changes");
            return 0;
    }
    /* Need to check for LACP interface */
    // TODO: Add reconfigurations that will be needed by OSPF daemon

    return 1;
}

static int
ospf_apply_interface_changes (struct ovsdb_idl *idl)
{
   const struct ovsrec_interface* intf_first = NULL;

   intf_first = ovsrec_interface_first(idl);
   /*
    * Check if any table changes present.
    * If no change just return from here
    */
    if (intf_first && !OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(intf_first, idl_seqno)
        && !OVSREC_IDL_ANY_TABLE_ROWS_DELETED(intf_first, idl_seqno)
        && !OVSREC_IDL_ANY_TABLE_ROWS_MODIFIED(intf_first, idl_seqno)) {
            VLOG_DBG ("No Interface changes");
            return 0;
    }

    // TODO: Add reconfigurations that will be needed by OSPF daemon
    return 1;
}

static int
ospf_apply_ospf_router_changes (struct ovsdb_idl *idl)
{
   const struct ovsrec_ospf_router* ospf_router_first = NULL;
   struct ospf *ospf_instance;

   ospf_router_first = ovsrec_ospf_router_first(idl);
   /*
    * Check if any table changes present.
    * If no change just return from here
    */
    if (ospf_router_first && !OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(ospf_router_first, idl_seqno)
        && !OVSREC_IDL_ANY_TABLE_ROWS_DELETED(ospf_router_first, idl_seqno)
        && !OVSREC_IDL_ANY_TABLE_ROWS_MODIFIED(ospf_router_first, idl_seqno)) {
            VLOG_DBG("No OSPF router changes");
            return 0;
    }
    if (ospf_router_first == NULL) {
            /* Check if it is a first row deletion */
            VLOG_DBG("OSPF config empty!\n");
            /* OPS_TODO : Support for multiple instances */
            ospf_instance = ospf_lookup();
            // TODO: Delete all instance as  there is no OSPF config in DB
            if (ospf_instance) {
                ospf_finish(ospf_instance);
            }
            return 1;
        }

    /* Check if any row deletion */
    if (OVSREC_IDL_ANY_TABLE_ROWS_DELETED(ospf_router_first, idl_seqno)) {
        delete_ospf_router_instance(idl);
    }

    /* insert and modify cases */
    ospf_router_read_ovsdb_apply_changes(idl);

    // TODO: Add reconfigurations that will be needed by OSPF daemon
    return 1;
}

static int
ospf_apply_route_changes (struct ovsdb_idl *idl)
{
   const struct ovsrec_route* route_first = NULL;

   route_first = ovsrec_route_first(idl);
   /*
    * Check if any table changes present.
    * If no change just return from here
    */
    if (route_first && !OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(route_first, idl_seqno)
        && !OVSREC_IDL_ANY_TABLE_ROWS_DELETED(route_first, idl_seqno)
        && !OVSREC_IDL_ANY_TABLE_ROWS_MODIFIED(route_first, idl_seqno)) {
            VLOG_DBG("No Route changes");
            return 0;
    }
    // TODO: Add reconfigurations that will be needed by OSPF daemon
    return 1;
}

/*
 * Update the ospf rib routes in the OSPF_Route table of the OVSDB database *
*/
static void
ospf_route_add_to_area_route_table (struct route_table * oart, struct prefix *p_or, struct ospf_route *or)
{
  struct route_table *area_rt_table;
  struct route_node *rn, *rn_or;
  struct prefix p_area;
  struct ospf_route *or_new;

  if (!oart)
	return;

  p_area.family = AF_INET;
  p_area.prefixlen = IPV4_MAX_BITLEN;
  p_area.u.prefix4 = or->u.std.area_id;

  rn = route_node_get (oart, (struct prefix *)&p_area);

  if (!rn->info)
	rn->info = route_table_init ();

  area_rt_table = (struct  route_table *) (rn->info);

  or_new = ospf_route_new ();
  or_new->type = or->type;
  or_new->id = or->id;
  or_new->mask = or->mask;
  or_new->path_type = or->path_type;
  or_new->cost = or->cost;
  or_new->u = or->u;

  ospf_route_add (area_rt_table, (struct prefix_ipv4 *)p_or, or_new, or);
}

static void
ospf_area_route_table_free (struct route_table *oart)
{
  struct route_table *area_rt_table;
  struct route_node *rn, *rn1;
  struct ospf_route *or;

  if (!oart)
	return;

  for (rn = route_top (oart); rn; rn = route_next (rn)) {
    if ((area_rt_table = rn->info) != NULL) {
      for (rn1 = route_top (area_rt_table); rn1; rn1 = route_next (rn1)) {
         if ((or = rn1->info) != NULL) {
           ospf_route_free (or);
           rn1->info = NULL;
           route_unlock_node (rn1);
         }
      }
      route_table_finish (area_rt_table);
      rn->info = NULL;
      route_unlock_node (rn);
    }
  }
  route_table_finish (oart);
}

/* TODO This util function can be moved to common utils file */
static char *
bollean2string (bool flag)
{
  if (flag)
    return BOOLEAN_STRING_TRUE;
  else
    return BOOLEAN_STRING_FALSE;
}

static char *
ospf_route_path_type_string (u_char path_type)
{
  switch (path_type) {
    case OSPF_PATH_INTRA_AREA:
           return OSPF_PATH_TYPE_STRING_INTRA_AREA;

    case OSPF_PATH_INTER_AREA:
           return OSPF_PATH_TYPE_STRING_INTER_AREA;

    case OSPF_PATH_TYPE1_EXTERNAL:
    case OSPF_PATH_TYPE2_EXTERNAL:
           return OSPF_PATH_TYPE_STRING_EXTERNAL;

    default:
           return "invalid";
  }
}

static char *
ospf_route_path_type_ext_string (u_char path_type)
{
  switch (path_type) {
    case OSPF_PATH_TYPE1_EXTERNAL:
           return OSPF_EXT_TYPE_STRING_TYPE1;
    case OSPF_PATH_TYPE2_EXTERNAL:
           return OSPF_EXT_TYPE_STRING_TYPE2;

    default:
           return "invalid";
  }
}

/*
 * Update the ospf network routes in the OSPF_Route table of the OVSDB database *
*/
void
ovsdb_ospf_update_network_routes (const struct ospf *ospf, const struct route_table *rt)
{
  struct ovsrec_ospf_router *ospf_router_row = NULL;
  struct ovsrec_ospf_area *ospf_area_row = NULL;
  struct ovsrec_ospf_route *ospf_route_row = NULL;
  struct ovsrec_ospf_route **intra_area_rts = NULL, **inter_area_rts = NULL;
  struct ovsdb_idl_txn* ort_txn = NULL;
  enum   ovsdb_idl_txn_status txn_status;
  struct route_node *rn, *rn1;
  struct ospf_route *or;
  struct route_table *ospf_area_route_table = NULL, *per_area_rt_table = NULL;
  int    i = 0, j = 0;

  if (NULL == ospf || NULL == rt)
  {
      VLOG_DBG ("No ospf instance or no routes to add");
      return;
  }

  ospf_router_row = ovsdb_ospf_get_router_by_instance_num (ospf->ospf_inst);
  if (!ospf_router_row)
  {
      VLOG_DBG ("No OSPF Router in OVSDB could be found");
      return;
  }

  if (!ospf_router_row->n_areas)
  {
      VLOG_DBG ("No OSPF Area in OSPF Router in OVSDB could be found");
      return;
  }

  ort_txn = ovsdb_idl_txn_create(idl);
  if (!ort_txn)
  {
      VLOG_DBG ("Transaction create failed");
      return;
  }

  /* Delete all the network routes of all the areas in the ospf router instance */
  for (i = 0 ; i < ospf_router_row->n_areas ; i++) {
    ospf_area_row = ospf_router_row->value_areas[i];

    ovsrec_ospf_area_set_intra_area_ospf_routes (ospf_area_row, NULL, 0);

    ovsrec_ospf_area_set_inter_area_ospf_routes (ospf_area_row, NULL, 0);
  }

  /* Add ospf routes to OVSDB OSPF_Route table */

  /* Generating the per area ospf routing table */
  ospf_area_route_table = route_table_init ();
  for (rn = route_top (rt); rn; rn = route_next (rn))
    if ((or = rn->info))
      ospf_route_add_to_area_route_table (ospf_area_route_table, &(rn->p), or);

  /* Updating the OVSDB databse from the per area ospf routing table */
  for (rn = route_top (ospf_area_route_table); rn; rn = route_next (rn))
    if ((per_area_rt_table = (struct route_table *)(rn->info))) {
      struct in_addr area_id = rn->p.u.prefix4;
      if (ospf_area_row = ovsrec_ospf_area_get_area_by_id (ospf_router_row, area_id)) {
        i = j = 0;
        if (!(intra_area_rts = xcalloc (per_area_rt_table->count, sizeof (struct ovsrec_ospf_route *)))) {
          VLOG_ERR ("Memory allocation Failure");
          ovsdb_idl_txn_abort(ort_txn);
          route_unlock_node (rn);
          return;
        }
        if (!(inter_area_rts = xcalloc (per_area_rt_table->count, sizeof (struct ovsrec_ospf_route *)))) {
          VLOG_ERR ("Memory allocation Failure");
          free (intra_area_rts);
          ovsdb_idl_txn_abort(ort_txn);
          route_unlock_node (rn);
          return;
        }
        for (rn1 = route_top (per_area_rt_table); rn1; rn1 = route_next (rn1))
          if ((or = (struct ospf_route *)(rn1->info))) {
            char prefix_str[19] = {0};
            struct listnode *pnode, *pnnode;
            struct ospf_path *path;

            if (!(ospf_route_row = ovsrec_ospf_route_insert (ort_txn))) {
              VLOG_ERR ("insert in OSPF_Route Failed.");
              continue;
            }

            if (or->path_type == OSPF_PATH_INTRA_AREA) {
              intra_area_rts[i++] = ospf_route_row;
              ovsrec_ospf_route_set_path_type (ospf_route_row, OSPF_PATH_TYPE_STRING_INTRA_AREA);
            }
            else if (or->path_type == OSPF_PATH_INTER_AREA) {
              inter_area_rts[j++] = ospf_route_row;
              ovsrec_ospf_route_set_path_type (ospf_route_row, OSPF_PATH_TYPE_STRING_INTER_AREA);
            }
            else
              continue;

            snprintf (prefix_str, sizeof(prefix_str), "%s/%d", inet_ntoa (rn1->p.u.prefix4), rn1->p.prefixlen);
            ovsrec_ospf_route_set_prefix (ospf_route_row, prefix_str);

            if (!(or->path_type == OSPF_PATH_INTER_AREA && or->type == OSPF_DESTINATION_DISCARD)) {
              struct smap route_info;
              char cost[6] = {0};

              smap_clone (&route_info, &(ospf_route_row->route_info));
              smap_replace (&route_info, OSPF_KEY_ROUTE_AREA_ID, inet_ntoa (or->u.std.area_id));
              snprintf (cost, 6, "%d", or->cost);
              smap_replace (&route_info, OSPF_KEY_ROUTE_COST, cost);
              ovsrec_ospf_route_set_route_info (ospf_route_row, &route_info);
              smap_destroy (&route_info);
            }

            if (or->type == OSPF_DESTINATION_NETWORK) {
              char pathstr[100] = {0};
              int k = 0;
              char **pathstrs = NULL;

              if (or->paths)
                if (!(pathstrs = xcalloc (or->paths->count, sizeof (char *)))) {
                  VLOG_ERR ("Memory allocation Failure");
                  free (intra_area_rts);
                  free (inter_area_rts);
                  ovsdb_idl_txn_abort(ort_txn);
                  route_unlock_node (rn1);
                  route_unlock_node (rn);
                  return;
                }

                for (ALL_LIST_ELEMENTS (or->paths, pnode, pnnode, path)) {
                  if (if_lookup_by_index(path->ifindex)) {
                    if (path->nexthop.s_addr == 0)
                      snprintf (pathstr, 100, "directly attached to %s", ifindex2ifname (path->ifindex));
                    else
                      snprintf (pathstr, 100, "via %s, %s", inet_ntoa (path->nexthop), ifindex2ifname (path->ifindex));

                    pathstrs[k++] = pathstr;
                  }
                }

                ovsrec_ospf_route_set_paths (ospf_route_row, pathstrs, k);
                free (pathstrs);
              }
          }
         ovsrec_ospf_area_set_intra_area_ospf_routes (ospf_area_row, intra_area_rts, i);
         free (intra_area_rts);
         ovsrec_ospf_area_set_inter_area_ospf_routes (ospf_area_row, inter_area_rts, j);
         free (inter_area_rts);
      }
    }

  ospf_area_route_table_free (ospf_area_route_table);

  txn_status = ovsdb_idl_txn_commit_block(ort_txn);
  if (TXN_SUCCESS != txn_status && TXN_UNCHANGED != txn_status)
        VLOG_DBG ("OSPF Route add transaction commit failed:%d",txn_status);

  ovsdb_idl_txn_destroy(ort_txn);

  return;
}

/*
 * Update the ospf router routes in the OSPF_Route table of the OVSDB database *
*/
void
ovsdb_ospf_update_router_routes (const struct ospf *ospf, const struct route_table *rt)
{
  struct ovsrec_ospf_router *ospf_router_row = NULL;
  struct ovsrec_ospf_area *ospf_area_row = NULL;
  struct ovsrec_ospf_route *ospf_route_row = NULL;
  struct ovsrec_ospf_route **router_rts = NULL;
  struct ovsdb_idl_txn* ort_txn = NULL;
  enum   ovsdb_idl_txn_status txn_status;
  struct route_node *rn, *rn1;
  struct listnode *node;
  struct ospf_route *or;
  struct route_table *ospf_area_route_table = NULL, *per_area_rt_table = NULL;
  int    i = 0, j = 0;

  if (NULL == ospf || NULL == rt)
  {
      VLOG_DBG ("No ospf instance or no routes to add");
      return;
  }

  ospf_router_row = ovsdb_ospf_get_router_by_instance_num (ospf->ospf_inst);
  if (!ospf_router_row)
  {
      VLOG_DBG ("No OSPF Router in OVSDB could be found");
      return;
  }

  if (!ospf_router_row->n_areas)
  {
      VLOG_DBG ("No OSPF Area in OSPF Router in OVSDB could be found");
      return;
  }

  ort_txn = ovsdb_idl_txn_create(idl);
  if (!ort_txn)
  {
      VLOG_DBG ("Transaction create failed");
      return;
  }

  /* Delete all the network routes of all the areas in the ospf router instance */
  for (i = 0 ; i < ospf_router_row->n_areas ; i++) {
    ospf_area_row = ospf_router_row->value_areas[i];

    ovsrec_ospf_area_set_router_ospf_routes (ospf_area_row, NULL, 0);
  }

  /* Add ospf routes to OVSDB OSPF_Route table */

  /* Generating the per area ospf routing table */
  ospf_area_route_table = route_table_init ();
  for (rn = route_top (rt); rn; rn = route_next (rn))
    if (rn->info)
      for (ALL_LIST_ELEMENTS_RO ((struct list *)rn->info, node, or))
        ospf_route_add_to_area_route_table (ospf_area_route_table, &(rn->p), or);

  /* Updating the OVSDB databse from the per area ospf routing table */
  for (rn = route_top (ospf_area_route_table); rn; rn = route_next (rn))
    if ((per_area_rt_table = (struct route_table *)(rn->info))) {
      struct in_addr area_id = rn->p.u.prefix4;
      if (ospf_area_row = ovsrec_ospf_area_get_area_by_id (ospf_router_row, area_id)) {
        i = j = 0;
        if (!(router_rts = xcalloc (per_area_rt_table->count, sizeof (struct ovsrec_ospf_route *)))) {
          VLOG_ERR ("Memory allocation Failure");
          ovsdb_idl_txn_abort(ort_txn);
          route_unlock_node (rn);
          return;
        }
        for (rn1 = route_top (per_area_rt_table); rn1; rn1 = route_next (rn1))
          if ((or = (struct ospf_route *)(rn1->info))) {
            char prefix_str[19] = {0};
            struct listnode *pnode, *pnnode;
            struct ospf_path *path;
            struct smap route_info;
            char cost[6] = {0};
            char pathstr[100] = {0};
            int k = 0;
            char **pathstrs = NULL;

            if (!(ospf_route_row = ovsrec_ospf_route_insert (ort_txn))) {
              VLOG_ERR ("insert in OSPF_Route Failed.");
              continue;
            }

            router_rts[i++] = ospf_route_row;

            snprintf (prefix_str, sizeof(prefix_str), "%s/%d", inet_ntoa (rn1->p.u.prefix4), rn1->p.prefixlen);
            ovsrec_ospf_route_set_prefix (ospf_route_row, prefix_str);

            ovsrec_ospf_route_set_path_type (ospf_route_row, ospf_route_path_type_string (or->path_type));

            smap_clone (&route_info, &(ospf_route_row->route_info));
            smap_replace (&route_info, OSPF_KEY_ROUTE_AREA_ID, inet_ntoa (or->u.std.area_id));
            snprintf (cost, 6, "%d", or->cost);
            smap_replace (&route_info, OSPF_KEY_ROUTE_COST, cost);
            smap_replace (&route_info, OSPF_KEY_ROUTE_TYPE_ABR, bollean2string(or->u.std.flags & ROUTER_LSA_BORDER));
            smap_replace (&route_info, OSPF_KEY_ROUTE_TYPE_ASBR, bollean2string(or->u.std.flags & or->u.std.flags & ROUTER_LSA_EXTERNAL));
            ovsrec_ospf_route_set_route_info (ospf_route_row, &route_info);
            smap_destroy (&route_info);

            if (or->paths)
              if (!(pathstrs = xcalloc (or->paths->count, sizeof (char *)))) {
                VLOG_ERR ("Memory allocation Failure");
                free (router_rts);
                ovsdb_idl_txn_abort(ort_txn);
                route_unlock_node (rn1);
                route_unlock_node (rn);
                return;
              }

            for (ALL_LIST_ELEMENTS (or->paths, pnode, pnnode, path)) {
              if (if_lookup_by_index(path->ifindex)) {
                if (path->nexthop.s_addr == 0)
                  snprintf (pathstr, 100, "directly attached to %s", ifindex2ifname (path->ifindex));
                else
                  snprintf (pathstr, 100, "via %s, %s", inet_ntoa (path->nexthop), ifindex2ifname (path->ifindex));

                pathstrs[k++] = pathstr;
              }
            }

            ovsrec_ospf_route_set_paths (ospf_route_row, pathstrs, k);
            free (pathstrs);
        }
        ovsrec_ospf_area_set_router_ospf_routes (ospf_area_row, router_rts, i);
        free (router_rts);
      }
    }

  ospf_area_route_table_free (ospf_area_route_table);

  txn_status = ovsdb_idl_txn_commit_block(ort_txn);
  if (TXN_SUCCESS != txn_status && TXN_UNCHANGED != txn_status)
        VLOG_DBG ("OSPF Route add transaction commit failed:%d",txn_status);

  ovsdb_idl_txn_destroy(ort_txn);

  return;
}

/*
 * Update the ospf external routes in the OSPF_Route table of the OVSDB database *
*/
void
ovsdb_ospf_update_ext_routes (const struct ospf *ospf, const struct route_table *rt)
{
  struct ovsrec_ospf_router *ospf_router_row = NULL;
  struct ovsrec_ospf_route *ospf_route_row = NULL;
  struct ovsrec_ospf_route **ext_rts = NULL;
  struct ovsdb_idl_txn* ort_txn = NULL;
  enum   ovsdb_idl_txn_status txn_status;
  struct route_node *rn;
  struct ospf_route *or;
  int    i = 0;

  if (NULL == ospf || NULL == rt)
  {
      VLOG_DBG ("No ospf instance or no routes to add");
      return;
  }

  ospf_router_row = ovsdb_ospf_get_router_by_instance_num (ospf->ospf_inst);
  if (!ospf_router_row)
  {
      VLOG_DBG ("No OSPF Router in OVSDB could be found");
      return;
  }

  ort_txn = ovsdb_idl_txn_create(idl);
  if (!ort_txn)
  {
      VLOG_DBG ("Transaction create failed");
      return;
  }

  /* Delete all the network routes of all the areas in the ospf router instance */

  ovsrec_ospf_router_set_ext_ospf_routes (ospf_router_row, NULL, 0);

  /* Add ospf routes to OVSDB OSPF_Route table */

  i = 0;
  if (!(ext_rts = xcalloc (rt->count, sizeof (struct ovsrec_ospf_route *)))) {
    VLOG_ERR ("Memory allocation Failure");
    ovsdb_idl_txn_abort(ort_txn);
    return;
  }

  for (rn = route_top (rt); rn; rn = route_next (rn))
    if ((or = (struct ospf_route *)(rn->info))) {
      char prefix_str[19] = {0};
      struct listnode *pnode, *pnnode;
      struct ospf_path *path;
      struct smap route_info;
      char buf[20] = {0};
      char pathstr[100] = {0};
      int k = 0;
      char **pathstrs = NULL;

      if (!(ospf_route_row = ovsrec_ospf_route_insert (ort_txn))) {
        VLOG_ERR ("Insert in OSPF_Route table Failed.");
        continue;
      }

      ext_rts[i++] = ospf_route_row;

      snprintf (prefix_str, sizeof(prefix_str), "%s/%d", inet_ntoa (rn->p.u.prefix4), rn->p.prefixlen);
      ovsrec_ospf_route_set_prefix (ospf_route_row, prefix_str);

      ovsrec_ospf_route_set_path_type (ospf_route_row, ospf_route_path_type_string (or->path_type));

      smap_clone (&route_info, &(ospf_route_row->route_info));
      smap_replace (&route_info, OSPF_KEY_ROUTE_AREA_ID, inet_ntoa (or->u.std.area_id));
      snprintf (buf, 11, "%u", or->cost);
      smap_replace (&route_info, OSPF_KEY_ROUTE_COST, buf);
      smap_replace (&route_info, OSPF_KEY_ROUTE_TYPE_ABR, bollean2string(or->u.std.flags & ROUTER_LSA_BORDER));
      smap_replace (&route_info, OSPF_KEY_ROUTE_TYPE_ASBR, bollean2string(or->u.std.flags & or->u.std.flags & ROUTER_LSA_EXTERNAL));
      smap_replace (&route_info, OSPF_KEY_ROUTE_EXT_TYPE, ospf_route_path_type_ext_string (or->path_type));
      snprintf (buf, 11, "%u", or->u.ext.tag);
      smap_replace (&route_info, OSPF_KEY_ROUTE_EXT_TAG, buf);
      if (or->path_type == OSPF_PATH_TYPE2_EXTERNAL) {
        snprintf (buf, 11, "%u", or->u.ext.type2_cost);
        smap_replace (&route_info, OSPF_KEY_ROUTE_TYPE2_COST, buf);
      }
      ovsrec_ospf_route_set_route_info (ospf_route_row, &route_info);
      smap_destroy (&route_info);

      if (or->paths)
        if (!(pathstrs = xcalloc (or->paths->count, sizeof (char *)))) {
          VLOG_ERR ("Memory allocation Failure");
          free (ext_rts);
          ovsdb_idl_txn_abort(ort_txn);
          route_unlock_node (rn);
          return;
        }
       for (ALL_LIST_ELEMENTS (or->paths, pnode, pnnode, path)) {
        if (if_lookup_by_index(path->ifindex)) {
          if (path->nexthop.s_addr == 0)
            snprintf (pathstr, 100, "directly attached to %s", ifindex2ifname (path->ifindex));
          else
            snprintf (pathstr, 100, "via %s, %s", inet_ntoa (path->nexthop), ifindex2ifname (path->ifindex));
          pathstrs[k++] = pathstr;
        }
      }

      ovsrec_ospf_route_set_paths (ospf_route_row, pathstrs, k);
      free (pathstrs);
    }
  ovsrec_ospf_router_set_ext_ospf_routes (ospf_router_row, ext_rts, i);
  free (ext_rts);

  txn_status = ovsdb_idl_txn_commit_block(ort_txn);
  if (TXN_SUCCESS != txn_status && TXN_UNCHANGED != txn_status)
    VLOG_DBG ("OSPF Route add transaction commit failed:%d",txn_status);

  ovsdb_idl_txn_destroy(ort_txn);

  return;
}

/* Check idl seqno. to make sure there are updates to the idl
 * and update the local structures accordingly.
 */
static void
ospf_reconfigure(struct ovsdb_idl *idl)
{
    unsigned int new_idl_seqno = ovsdb_idl_get_seqno(idl);
    COVERAGE_INC(ospf_ovsdb_cnt);

    if (new_idl_seqno == idl_seqno){
        VLOG_DBG("No config change for ospf in ovs\n");
        return;
    }

    ospf_apply_global_changes();
    if (ospf_apply_port_changes(idl) |
        ospf_apply_interface_changes(idl) |
        ospf_apply_ospf_router_changes(idl) |
        ospf_apply_route_changes(idl))
    {
         /* Some OSPF configuration changed. */
        VLOG_DBG("OSPF Configuration changed\n");
    }

    /* update the seq. number */
    idl_seqno = new_idl_seqno;
}

/* Wrapper function that checks for idl updates and reconfigures the daemon
 */
static void
ospf_ovs_run (void)
{
    ovsdb_idl_run(idl);
    unixctl_server_run(appctl);

    if (ovsdb_idl_is_lock_contended(idl)) {
        static struct vlog_rate_limit rl = VLOG_RATE_LIMIT_INIT(1, 1);

        VLOG_ERR_RL(&rl, "another ospfd process is running, "
                    "disabling this process until it goes away");
        return;
    } else if (!ovsdb_idl_has_lock(idl)) {
        return;
    }

    ospf_chk_for_system_configured();

    if (system_configured) {
        ospf_reconfigure(idl);

        daemonize_complete();
        vlog_enable_async();
        VLOG_INFO_ONCE("%s (Halon ospfd) %s", program_name, VERSION);
    }
}

static void
ospf_ovs_wait (void)
{
    ovsdb_idl_wait(idl);
    unixctl_server_wait(appctl);
}

/* Callback function to handle read events
 * In the event of an update to the idl cache, this callback is triggered.
 * In this event, the changes are processed in the daemon and the cb
 * functions are re-registered.
 */
static int
ospf_ovs_read_cb (struct thread *thread)
{
    ospf_ovsdb_t *ospf_ovs_g;
    if (!thread) {
        VLOG_ERR("NULL thread in read cb function\n");
        return -1;
    }
    ospf_ovs_g = THREAD_ARG(thread);
    if (!ospf_ovs_g) {
        VLOG_ERR("NULL args in read cb function\n");
        return -1;
    }

    ospf_ovs_g->read_cb_count++;

    ospf_ovs_clear_fds();
    ospf_ovs_run();
    ospf_ovs_wait();

    if (0 != ospf_ovspoll_enqueue(ospf_ovs_g)) {
        /*
         * Could not enqueue the events.
         * Retry in 1 sec
         */
        thread_add_timer(ospf_ovs_g->master,
                         ospf_ovs_read_cb, ospf_ovs_g, 1);
    }
    return 1;
}

/* Add the list of OVS poll fd to the master thread of the daemon
 */
static int
ospf_ovspoll_enqueue (ospf_ovsdb_t *ospf_ovs_g)
{
    struct poll_loop *loop = poll_loop();
    struct poll_node *node;
    long int timeout;
    int retval = -1;

    /* Populate with all the fds events. */
    HMAP_FOR_EACH (node, hmap_node, &loop->poll_nodes) {
        thread_add_read(ospf_ovs_g->master,
                                    ospf_ovs_read_cb,
                                    ospf_ovs_g, node->pollfd.fd);
        /*
         * If we successfully connected to OVS return 0.
         * Else return -1 so that we try to reconnect.
         * */
        retval = 0;
    }

    /* Populate the timeout event */
    timeout = loop->timeout_when - time_msec();
    if(timeout > 0 && loop->timeout_when > 0 &&
       loop->timeout_when < LLONG_MAX) {
        /* Convert msec to sec */
        timeout = (timeout + 999)/1000;

        thread_add_timer(ospf_ovs_g->master,
                                     ospf_ovs_read_cb, ospf_ovs_g,
                                     timeout);
    }

    return retval;
}

/* Initialize and integrate the ovs poll loop with the daemon */
void ospf_ovsdb_init_poll_loop (struct ospf_master *ospfm)
{
    if (!glob_ospf_ovs.enabled) {
        VLOG_ERR("OVS not enabled for ospf. Return\n");
        return;
    }
    glob_ospf_ovs.master = ospfm->master;

    ospf_ovs_clear_fds();
    ospf_ovs_run();
    ospf_ovs_wait();
    ospf_ovspoll_enqueue(&glob_ospf_ovs);
}

static void
ovsdb_exit(void)
{
    ovsdb_idl_destroy(idl);
}

/* When the daemon is ready to shut, delete the idl cache
 * This happens with the ovs-appctl exit command.
 */
void ospf_ovsdb_exit(void)
{
    ovsdb_exit();
}
