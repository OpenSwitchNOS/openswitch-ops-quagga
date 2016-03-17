/* zebra daemon ovsdb integration.
 *
 * (c) Copyright 2015-2016 Hewlett Packard Enterprise Development LP
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

#include <zebra.h>

#include <lib/version.h>
#include "getopt.h"
#include "command.h"
#include "thread.h"
#include "memory.h"
#include "zebra/zserv.h"
#include "zebra/debug.h"

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
#include "openvswitch/vlog.h"
#include "vswitch-idl.h"
#include "coverage.h"
#include "hash.h"
#include "jhash.h"

#include "openswitch-idl.h"

#include "zebra/zebra_ovsdb_if.h"

#define NUM_CHAR_CMP 6
#define NUM_CHAR_UNSUPPORTED 20

/* Local structure to hold the master thread
 * and counters for read/write callbacks
 */
typedef struct zebra_ovsdb_t_ {
  int enabled;
  struct thread_master *master;

  unsigned int read_cb_count;
  unsigned int write_cb_count;
} zebra_ovsdb_t;

static zebra_ovsdb_t glob_zebra_ovs;

COVERAGE_DEFINE(zebra_ovsdb_cnt);
VLOG_DEFINE_THIS_MODULE(zebra_ovsdb_if);

static struct ovsdb_idl *idl;
static unsigned int idl_seqno;
static char *appctl_path = NULL;
static struct unixctl_server *appctl;
static int system_configured = false;
static struct ovsdb_idl_txn *zebra_txn = NULL;
bool zebra_txn_updates = false;

boolean exiting = false;
/* Hash for ovsdb route.*/
static struct hash *zebra_route_hash;

/* List of delete route */
struct list *zebra_route_del_list;

static int zebra_ovspoll_enqueue (zebra_ovsdb_t *zovs_g);
static int zovs_read_cb (struct thread *thread);
int zebra_add_route (bool is_ipv6, struct prefix *p, int type, safi_t safi,
                     const struct ovsrec_route *route);
#ifdef HAVE_IPV6
extern int
rib_add_ipv6_multipath (struct prefix_ipv6 *p, struct rib *rib, safi_t safi);
#endif

#define HASH_BUCKET_SIZE 32768

#define OVSDB_ROUTE_MIN     0
#define OVSDB_ROUTE_ADD     1
#define OVSDB_ROUTE_DELETE  2

/*
 ********************************************************************
 * Start of the set of debugging functions for OVSDB zebra interface.
 ********************************************************************
 */
#ifdef VRF_ENABLE
char *zebra_vrf = NULL;

/*
 * Given the uuid of a vrf row, get its vrf name.
 */
static bool
zebra_get_vrf_from_uuid (char *uuid, char *vrf)
{
  char buff[UUID_LEN + 1];
  const struct ovsrec_vrf *vrf_row = NULL;

  if (!vrf || !ovsrec_vrf_first(idl))
    return false;

  OVSREC_VRF_FOR_EACH (vrf_row, idl)
    {
      memset(buff, 0, UUID_LEN + 1);
      sprintf(buff, UUID_FMT, UUID_ARGS(&(vrf_row->header_.uuid)));
      if (!strncmp(buff, uuid, UUID_LEN + 1))
        {
          /* vrf row found. break */
          break;
        }
    }

  if (!vrf_row)
    return false;

  /* copy the vrf name */
  strncpy(vrf, vrf_row->name, OVSDB_VRF_NAME_MAXLEN);

  return true;
}

/*
 * Get the network namespace name for this daemon
 */
static void
zebra_get_my_netns_name (char *netns)
{
  pid_t pid;
  FILE* fp = NULL;
  char command[100] = {0};

  if(!netns)
    return;
  memset(netns, 0, UUID_LEN + 1);
  pid = getpid();
  /*
   * This command will not be necessary later when vrfmgrd will pass
   * the namespace identity during service start.
   */
  sprintf(command, "ip netns identify %d", pid);
  fp = popen(command, "r");

  if(fp)
    fscanf(fp, "%s", netns);

  return;
}

/*
 * Read the vrf name for this daemon
 */
static char*
zebra_get_my_vrf_name (void)
{
  char vrf_s[] = "swns";
  char vrf_d[] = DEFAULT_VRF_NAME;
  char netns[UUID_LEN + 1] = {0};
  char *vrf_name = NULL;

  vrf_name = (char*) calloc (OVSDB_VRF_NAME_MAXLEN, sizeof(char));
  if(!vrf_name)
    return NULL;

  zebra_get_my_netns_name(netns);

  if(!strlen(netns))
    {
      free(vrf_name);
      return NULL;
    }
  /* if netns is "swns" mark the vrf_name as vrf_default */
  if(strncmp(netns, vrf_s, OVSDB_VRF_NAME_MAXLEN) == 0)
    {
      strncpy(vrf_name, vrf_d, strlen(vrf_d));
      return vrf_name;
    }

  /* if vrf name can't be retrived, cleanup and return */
  if(!zebra_get_vrf_from_uuid(netns, vrf_name))
    {
      free(vrf_name);
      return NULL;
    }

  VLOG_DBG("VRF name for this daemon is %s", vrf_name);
  return vrf_name;
}

/*
 * Presently zebra daemon is running per namespace.
 * Where each namespace represent a VRF.
 * Given a route check if it belongs to this VRF
 */
static bool
zebra_is_route_in_my_vrf (const struct ovsrec_route *ovs_route)
{
  char *vrf_name = NULL;
  char *ovs_rt_vrf = NULL;

  if(ovs_route->vrf == NULL)
    {
      ovs_rt_vrf = DEFAULT_VRF_NAME;
    }
  else
    {
      ovs_rt_vrf = ovs_route->vrf->name;
    }

  return(!strncmp(ovs_rt_vrf, zebra_vrf, OVSDB_VRF_NAME_MAXLEN));
}
#endif
/*
 * This function dumps the details of the next-hops for a given route row in
 * OVSDB route table.
 */
static void
zebra_dump_ovsdb_nexthop_entry (const struct ovsrec_nexthop *nh_row)
{
  int port_index;

  if (!nh_row)
    {
      VLOG_DBG("    The next-hop entry is NULL\n");
      return;
    }

  /*
   * Printing next-hop row parameters.
   */
  VLOG_DBG("    Address = %s %s%s\n", nh_row->ip_address,
           OVSREC_IDL_IS_ROW_INSERTED(nh_row, idl_seqno) ? "(I)":"",
           OVSREC_IDL_IS_ROW_MODIFIED(nh_row, idl_seqno) ? "(M)":"");

  /*
   * Walk the port list for the next-hop and print the details of
   * next-hop.
   */
  for (port_index = 0; port_index < nh_row->n_ports; ++port_index)
    {
      VLOG_DBG("        The next-hop port is %s\n",
               (nh_row->ports[port_index]->name) ?
                nh_row->ports[port_index]->name :
                "NULL");
    }
}

/*
 * This function dumps the details of a route row in OVSDB route table.
 */
static void
zebra_dump_ovsdb_route_entry (const struct ovsrec_route *route_row)
{
  int next_hop_index;

  if (!route_row)
    {
      VLOG_DBG("The route entry is NULL\n");
      return;
    }

  /*
   * Printing the route row details.
   */
  VLOG_DBG("Route = %s AF = %s protocol = %s vrf = %s\n %s%s",
           route_row->prefix ? route_row->prefix : "NULL",
           route_row->address_family ? route_row->address_family : "NULL",
           route_row->from ? route_row->from : "NULL",
           route_row->vrf ? (route_row->vrf->name ? route_row->vrf->name :
                             "NULL") : "NULL",
           OVSREC_IDL_IS_ROW_INSERTED(route_row, idl_seqno) ? "(I)":"",
           OVSREC_IDL_IS_ROW_MODIFIED(route_row, idl_seqno) ? "(M)":"");

  /*
   * Walk the array of nxt-hops and print the route's next-hop details.
   */
  for (next_hop_index = 0; next_hop_index < route_row->n_nexthops;
       ++next_hop_index)
    {
      zebra_dump_ovsdb_nexthop_entry(route_row->nexthops[next_hop_index]);
    }
}

/*
 * This function causes the dumps of the entire OVSDB route table.
 */
static void
zebra_dump_ovsdb_route_table (void)
{
  const struct ovsrec_route *route_row = NULL;
  int count = 0;

  VLOG_DBG("Printing the OVSDB route table snapshot\n");

  /*
   * Walk all the entries in the OVSDB route table and print all the
   * route entries.
   */
  OVSREC_ROUTE_FOR_EACH (route_row, idl)
    {
      if (route_row)
        {
          ++count;
          zebra_dump_ovsdb_route_entry(route_row);
        }
    }

  VLOG_DBG("Total number of route entries in OVSDB route table are %d\n",
           count);
}

/*
 ******************************************************************
 * End of the set of debugging functions for OVSDB zebra interface.
 ******************************************************************
 */

/*
 ************************************************************************
 * Start of function for handling port add, delete and update triggers
 * from OVSDB.
 */
/*
 * Type of port actions. The action done on the port is stored in the
 * cached L3 port node.
 */
enum zebra_l3_port_cache_actions
{
  ZEBRA_L3_PORT_NO_CHANGE,
  ZEBRA_L3_PORT_ADD,
  ZEBRA_L3_PORT_L3_CHANGED_TO_L2,
  ZEBRA_L3_PORT_DELETE,
  ZEBRA_L3_PORT_UPADTE_IP_ADDR
};

/*
 * Options under which we need to walk the zebra's route table and
 * decode which nexthop ports/addresses we need to withdraw from kernel
 * and remove or mark unselected in the OVSDB tables.
 */
enum zebra_handle_port_op_options
{
  ZEBRA_L3_PORT_DELETE_UPDATE_OPTION,
  ZEBRA_L3_PORT_ACTIVE_STATE_CHN_OPTION
};

/*
 * the string representation of the port actions.
 */
char* zebra_l3_port_cache_actions_str[] =
{
  "L3 port no change",
  "L3 port add",
  "L3 port changed to L2",
  "L3 port delete",
  "L3 port IP address update"
};

/*
 * The L3 port structure. This structure is used to store the
 * L3 ovsrec_port data. We need to cache this data in order to
 * handle triggers like "no routing" on a port where the port
 * entry in the port table loses all the IP/IPv6 addresses. We
 * use the cached IP addresses to clean up the kernel and the
 * update the OVSDB tables appropriately.
 */
struct zebra_l3_port
{
  char *port_name;                       /* name of the port */
  char *ip4_address;                     /* Primary IP address on port */
  char *ip6_address;                     /* Primary IPv6 address on port */
  struct shash ip4_address_secondary;    /* Hash for the secondary
                                            IP addresses */
  struct shash ip6_address_secondary;    /* Hash for the secondary
                                            IPv6 addresses */
  const struct ovsrec_port *cfg;         /* Pointer to the OVSDB port
                                            entry */
  enum zebra_l3_port_cache_actions port_action;   /* Action performed on the
                                                     port */
  bool if_active;                        /* If the port is still active in
                                            event of shut/un-shut triggers
                                            on the resolving interfaces.*/
};

/*
 * Hash to keep track of the L3 ports in the zebra system
 */
struct shash zebra_cached_l3_ports;

/*
 * Hash to keep track of the L3 ports which are deleted or
 * changed to L2 ports by configuration.
 */
struct shash zebra_updated_or_changed_l3_ports;

/*
 * This bool variable keeps track if in given iteration of
 * proacessing the OVSDB interface update, any interface admin
 * state changed.
 */
bool zebra_if_port_active_state_changed;

/*
 * This bool variable keeps track if in given iteration of
 * proacessing the OVSDB port update, any L3 port changed
 * its state from L3 to L2, any port got deleted or any
 * port IP/IPv6 addresses changed.
 */
bool zebra_if_port_updated_or_changed;

/*
 * this function initializes all the L3 port nodes in the
 * L3 port hash to "deleted", in order to find which L3 ports
 * got deleted in a given IDL update of OVSDB.
 */
static void
zebra_port_change_cached_l3_ports_hash_init (void)
{
    struct shash_node *node, *next;
    struct zebra_l3_port* l3_port;

    VLOG_DBG("Walking the L3 port cache to mark all the L3 ports "
              "as deleted");

    SHASH_FOR_EACH_SAFE (node, next, &zebra_cached_l3_ports) {

        if (!node) {
            VLOG_ERR("No node found in the L3 port hash\n");
            continue;
        }

        if (!(node->data)) {
            VLOG_ERR("No node data found\n");
            continue;
        }

        l3_port = (struct zebra_l3_port*)node->data;

        /*
         * Mark the cached L3 port node as deleted.
         */
        l3_port->port_action = ZEBRA_L3_PORT_DELETE;
    }
}

/*
 * This function returns true if a port is L3 port and false
 * otherwise.
 */
static bool
zebra_if_port_is_l3 (struct zebra_l3_port* port)
{
  if (!port)
    return(false);

  /*
   * Check if there are any primary IP/IPv6 addresses
   * on the port
   */
  if (port->ip4_address || port->ip6_address)
    return(true);

  /*
   * Check if there are any secondary IP addresses
   * on the port
   */
  if (shash_count(&(port->ip4_address_secondary)))
    return(true);

  /*
   * Check if there are any secondary IPv6 addresses
   * on the port
   */
  if (shash_count(&(port->ip6_address_secondary)))
    return(true);

  /*
   * If there are no primary or secondary IP/IPv6
   * addresses on the the port, then port is L2.
   */
  return(false);
}

/*
 * This function returns true if an OVSDB port is L3 port and false
 * otherwise.
 */
static bool
zebra_if_ovsrec_port_is_l3 (const struct ovsrec_port* port)
{
  const struct ovsrec_vrf *vrf_row = NULL;
  const struct ovsrec_port *port_row = NULL;
  size_t port_index;
  bool if_ovsrec_port_is_l3 = false;

  if (!port)
    return(false);

  OVSREC_VRF_FOR_EACH (vrf_row, idl)
    {
      #ifdef VRF_ENABLE
      if (strncmp(vrf_row->name, zebra_vrf, OVSDB_VRF_NAME_MAXLEN))
        continue;
      #endif
      for (port_index = 0; port_index < vrf_row->n_ports; ++port_index)
       {
         if (port->name && vrf_row->ports[port_index] &&
             vrf_row->ports[port_index]->name &&
             (strcmp((const char*)port->name,
                   (const char*)vrf_row->ports[port_index]->name) == 0))
           {
             VLOG_DBG("Found a match for port %s in vrf %s",
                      port->name, vrf_row->name);
             if_ovsrec_port_is_l3 = true;
             break;
           }
       }

       if (if_ovsrec_port_is_l3)
         break;
    }

  return(if_ovsrec_port_is_l3);
}

/*
 * This function returns 'true' if there is a change in the L3 IP addresses
 * on the L3 port with respect to OVSDB port entry.
 */
static bool
zebra_if_cached_port_and_ovsrec_port_ip4_addr_change (
                                    const struct ovsrec_port* port,
                                    struct zebra_l3_port* l3_port)
{
  char* secondary_addr_data;
  int secondary_addr_index;

  /*
   * If both are NULL, then return false.
   */
  if (!port && !l3_port)
    return(false);

  /*
   * If OVSDB port is not NULL and L3 port is NULL,
   * then return true.
   */
  if (port && !l3_port)
    return(true);

  /*
   * If OVSDB port is NULL and L3 port is not NULL,
   * then return true.
   */
  if (!port && l3_port)
    return(true);

  /*
   * Chaeck if the secondary IP addresses changed.
   *
   * 1. Check if the number of IPv4 secondary addresses have changed.
   */
  if (shash_count(&(l3_port->ip4_address_secondary)) !=
                                    port->n_ip4_address_secondary)
    return(true);

  /*
   * 2. Check if the IPv4 addresses are same in the local L3 port cache
   *    and the ovsrec_port structure.
   */
  for (secondary_addr_index = 0;
       secondary_addr_index < port->n_ip4_address_secondary;
       ++ secondary_addr_index)
    {
      secondary_addr_data  =
                    (char*)shash_find_data(&(l3_port->ip4_address_secondary),
                          port->ip4_address_secondary[secondary_addr_index]);

      if (!secondary_addr_data)
        return(true);

    }

  /*
   * If the OVSDB port primary address and L3 port primary addresses
   * are NULL, then return 'false'.
   */
  if (!(port->ip4_address) && !(l3_port->ip4_address))
    return(false);

  /*
   * If the OVSDB port primary address is not NULL and L3 port primary
   * addresses is NULL, then return 'true'.
   */
  if ((port->ip4_address) && !(l3_port->ip4_address))
    return(true);

  /*
   * If the OVSDB port primary address is NULL and L3 port primary
   * addresses is not NULL, then return 'true'.
   */
  if (!(port->ip4_address) && (l3_port->ip4_address))
    return(true);

  /*
   * If the OVSDB port primary address and L3 port primary address
   * are not same, then return 'true'.
   */
  if (strcmp(port->ip4_address, l3_port->ip4_address) != 0)
    return(true);

  /*
   * In other cases return 'false'.
   */
  return(false);
}

/*
 * This function returns 'true' if there is a change in the L3 IPv6 addresses
 * on the L3 port with respect to OVSDB port entry.
 */
static bool
zebra_if_cached_port_and_ovsrec_port_ip6_addr_change (
                                    const struct ovsrec_port* port,
                                    struct zebra_l3_port* l3_port)
{
  char* secondary_addr_data;
  int secondary_addr_index;

  /*
   * If both are NULL, then return false.
   */
  if (!port && !l3_port)
    return(false);

  /*
   * If OVSDB port is not NULL and L3 port is NULL,
   * then return true.
   */
  if (port && !l3_port)
    return(true);

  /*
   * If OVSDB port is NULL and L3 port is not NULL,
   * then return true.
   */
  if (!port && l3_port)
    return(true);

  /*
   * Chaeck if the secondary IP addresses changed.
   *
   * 1. Check if the number of IPv4 secondary addresses have changed.
   */
  if (shash_count(&(l3_port->ip6_address_secondary)) !=
                                     port->n_ip6_address_secondary)
    return(true);

  /*
   * 2. Check if the IPv4 addresses are same in the local L3 port
   *    cache and the ovsrec_port structure.
   */
  for (secondary_addr_index = 0;
       secondary_addr_index < port->n_ip6_address_secondary;
       ++ secondary_addr_index)
    {
      secondary_addr_data  =
                (char*)shash_find_data(&(l3_port->ip6_address_secondary),
                      port->ip6_address_secondary[secondary_addr_index]);

      if (!secondary_addr_data)
        return(true);
    }

  /*
   * If the OVSDB port primary address and L3 port primary addresses
   * are NULL, then return 'false'.
   */
  if (!(port->ip6_address) && !(l3_port->ip6_address))
    return(false);

  /*
   * If the OVSDB port primary address is not NULL and L3 port primary
   * addresses is NULL, then return 'true'.
   */
  if ((port->ip6_address) && !(l3_port->ip6_address))
    return(true);

  /*
   * If the OVSDB port primary address is NULL and L3 port primary
   * addresses is not NULL, then return 'true'.
   */
  if (!(port->ip6_address) && (l3_port->ip6_address))
    return(true);

  /*
   * If the OVSDB port primary address and L3 port primary address
   * are not same, then return 'true'.
   */
  if (strcmp(port->ip6_address, l3_port->ip6_address) != 0)
    return(true);

  /*
   * In other cases return 'false'.
   */
  return(false);
}

/*
 * If the interfaces is admin "up", then set the 'if_active' to 'true'
 * else set this to 'false'.
 */
static bool
zebra_get_port_active_state (
                    const struct ovsrec_port* port)
{
  bool active_state = false;
  int interface_index;
  const struct ovsrec_interface* interface = NULL;

  if (!port)
    {
      VLOG_ERR("The port pointer is NULL");
      return(active_state);
    }

  if (!(port->name))
    {
      VLOG_ERR("The port name pointer is NULL");
      return(active_state);
    }

  VLOG_DBG("The number of interfaces resolving the port %s are %d",
            port->name, port->n_interfaces);
  if (port->n_interfaces)
    {
      for (interface_index = 0;
           interface_index < port->n_interfaces;
           ++interface_index)
        {
          interface = port->interfaces[interface_index];

          if (!interface)
            {
              VLOG_DBG("The interface pointer in port is NULL");
              continue;
            }

          if (interface->admin_state &&
              (strcmp(interface->admin_state,
                      OVSREC_INTERFACE_ADMIN_STATE_UP) == 0))
            {
              VLOG_DBG("Found an interface %s in admin up state. "
                        "Setting the port %s in active state",
                        interface->name, port->name);
              active_state = true;
              break;
            }
        }
    }

    return(active_state);
}

/*
 * This function allocates a L3 port node and fills its data members
 * using the corresponding values in the OVSDB port entry. This function
 * returns a pointer reference to the allocated L3 port node.
 */
static struct zebra_l3_port*
zebra_l3_port_node_create (const struct ovsrec_port* ovsrec_port)
{
  struct zebra_l3_port* l3_port = NULL;
  int secondary_addr_index;
  int interface_index;

  /*
   * If the OVSDB port entry is NULL, then return NULL from this
   * function.
   */
  if (!ovsrec_port)
    {
      VLOG_ERR("The OVSDB port entry is NULL.");
      return(NULL);
    }

  l3_port = (struct zebra_l3_port *)xzalloc(sizeof(struct zebra_l3_port));

  /*
   * Copy the name of the port.
   */
  l3_port->port_name = xstrdup(ovsrec_port->name);

  /*
   * Copy the IPv4 address if the IPv4 address is present on the port.
   */
  if (ovsrec_port->ip4_address)
    l3_port->ip4_address = xstrdup(ovsrec_port->ip4_address);

  /*
   * Copy the IPv6 address if the IPv6 address is present on the port.
   */
  if (ovsrec_port->ip6_address)
    l3_port->ip6_address = xstrdup(ovsrec_port->ip6_address);

  /*
   * Record the reference to the OVSDB port entry.
   */
  l3_port->cfg = ovsrec_port;

  /*
   * Record the port action as a new added prot.
   */
  l3_port->port_action = ZEBRA_L3_PORT_ADD;

  /*
   * Walk the secondary IPv4 addresses array and add the secondary addresses
   * into the IPv4 secondary addresses hash.
   */
  shash_init(&(l3_port->ip4_address_secondary));
  for (secondary_addr_index = 0;
       secondary_addr_index < ovsrec_port->n_ip4_address_secondary;
       ++ secondary_addr_index)
    {

      if (!shash_add(
             &(l3_port->ip4_address_secondary),
             ovsrec_port->ip4_address_secondary[secondary_addr_index],
             xstrdup(ovsrec_port->ip4_address_secondary[secondary_addr_index])))
        {
          VLOG_ERR("Unable to add the secondary IP address %s to "
                   "L3 port hash table",
                   ovsrec_port->ip4_address_secondary[secondary_addr_index]);
        }
      else
        {
          VLOG_DBG("Added the secondary IP address %s to "
                    "L3 port hash table",
                    ovsrec_port->ip4_address_secondary[secondary_addr_index]);
        }
    }

  /*
   * Walk the secondary IPv6 addresses array and add the secondary addresses
   * into the IPv6 secondary addresses hash.
   */
  shash_init(&(l3_port->ip6_address_secondary));
  for (secondary_addr_index = 0;
       secondary_addr_index < ovsrec_port->n_ip6_address_secondary;
       ++ secondary_addr_index)
    {

      if (!shash_add(
            &(l3_port->ip6_address_secondary),
            ovsrec_port->ip6_address_secondary[secondary_addr_index],
            xstrdup(ovsrec_port->ip6_address_secondary[secondary_addr_index])))
        {
          VLOG_ERR("Unable to add the secondary IPv6 address %s to "
                   "L3 port hash table",
                   ovsrec_port->ip6_address_secondary[secondary_addr_index]);
        }
      else
        {
          VLOG_DBG("Added the secondary IPv6 address %s to "
                    "L3 port hash table",
                    ovsrec_port->ip6_address_secondary[secondary_addr_index]);
        }
    }

  /*
   * Set 'if_active' for the port to record if the interface resolving this
   * port are in admin UP or DOWN.
   */
  l3_port->if_active = zebra_get_port_active_state(l3_port->cfg);

  /*
   * Return the pointer reference to the L3 port node.
   */
  return(l3_port);
}

/*
 * This function releases the memory allocated for a cached L3 port node
 * once the port node is no longer in use.
 */
static void
zebra_l3_port_node_free (struct zebra_l3_port* l3_port)
{
  struct shash_node *node, *next;
  char* ip_secondary_address;
  int secondary_address_count;

  if (!l3_port)
    {
      VLOG_ERR("The L3 port structure is NULL. Nothing to free");
      return;
    }

  /*
   * Free the port name
   */
  free(l3_port->port_name);

  /*
   * Free the port IPv4 primary address.
   */
  free(l3_port->ip4_address);

  /*
   * Free the port IPv6 primary address.
   */
  free(l3_port->ip6_address);
  l3_port->cfg = NULL;

  /*
   * Walk the IPv4 seocndary hash table, Free the secondary IPv4 address.
   */
  if (shash_count(&(l3_port->ip4_address_secondary)))
    {
      SHASH_FOR_EACH_SAFE (node, next, &(l3_port->ip4_address_secondary))
        {
          if (!node)
            {
              VLOG_ERR("No node found in the L3 port hash\n");
              continue;
            }

          if (!(node->data))
            {
              VLOG_ERR("No node data found\n");
              continue;
            }

          ip_secondary_address = (char*)node->data;

          shash_delete(&(l3_port->ip4_address_secondary), node);
          free(ip_secondary_address);
        }
    }

  shash_destroy(&(l3_port->ip4_address_secondary));

  /*
   * Walk the IPv6 seocndary hash table, Free the secondary IPv4 address.
   */
  if (shash_count(&(l3_port->ip6_address_secondary)))
    {
      SHASH_FOR_EACH_SAFE (node, next, &(l3_port->ip6_address_secondary))
        {
          if (!node)
            {
              VLOG_ERR("No node found in the L3 port hash\n");
              continue;
            }

          if (!(node->data))
            {
              VLOG_ERR("No node data found\n");
              continue;
            }

          ip_secondary_address = (char*)node->data;

          shash_delete(&(l3_port->ip6_address_secondary), node);
          free(ip_secondary_address);
        }
    }

  shash_destroy(&(l3_port->ip6_address_secondary));

  free(l3_port);
}

/*
 * This function prints the contents of the cached L3 port node. This is
 * useful for debugging the port/interface triggers.
 */
static void
zebra_l3_port_node_print (struct zebra_l3_port* l3_port)
{
  struct shash_node *node, *next;
  char* ip_secondary_address;
  int secondary_address_count;

  if (!l3_port)
    {
      VLOG_DBG("The L3 port structure is NULL. Nothing to print");
      return;
    }

  VLOG_DBG("Printing the L3 node\n");
  VLOG_DBG("     Port Name: %s", l3_port->port_name ? l3_port->port_name :
                                                       "NULL");
  VLOG_DBG("     Port Primary IP Address: %s", l3_port->ip4_address ?
                                                l3_port->ip4_address :
                                                "NULL");
  VLOG_DBG("     Port Primary IPv6 Address: %s", l3_port->ip6_address ?
                                                  l3_port->ip6_address :
                                                  "NULL");

  VLOG_DBG("     OVSDB port pointer is: %p", l3_port->cfg);

  VLOG_DBG("     Port action is: %s", zebra_l3_port_cache_actions_str[
                                                     l3_port->port_action]);
  VLOG_DBG("     Port state is: %s",
            l3_port->if_active ? "Active" : "Inactive");

  VLOG_DBG("     Printing the IPv4 seconary address in the port");
  if (!shash_count(&(l3_port->ip4_address_secondary)))
    VLOG_DBG("         No IPv4 seconary address in the port");
  else
    {
      secondary_address_count = 0;
      SHASH_FOR_EACH_SAFE (node, next, &(l3_port->ip4_address_secondary))
        {
          if (!node)
            {
              VLOG_DBG("No node found in the L3 port hash\n");
              continue;
            }

          if (!(node->data))
            {
              VLOG_DBG("No node data found\n");
              continue;
            }

          ip_secondary_address = (char*)node->data;
          ++secondary_address_count;

          VLOG_DBG("         %d. Address %s", secondary_address_count,
                    ip_secondary_address);

        }
    }

  VLOG_DBG("     Printing the IPv6 seconary address in the port");
  if (!shash_count(&(l3_port->ip6_address_secondary)))
    VLOG_DBG("         No IPv6 seconary address in the port");
  else
    {
      secondary_address_count = 0;
      SHASH_FOR_EACH_SAFE (node, next, &(l3_port->ip6_address_secondary))
        {
          if (!node)
            {
              VLOG_DBG("No node found in the L3 port hash\n");
              continue;
            }

          if (!(node->data))
            {
              VLOG_DBG("No node data found\n");
               continue;
            }

          ip_secondary_address = (char*)node->data;
          ++secondary_address_count;

          VLOG_DBG("         %d. Address %s", secondary_address_count,
                    ip_secondary_address);

        }
    }
}

/*
 * Walk all cached L3 ports in the hash table 'zebra_cached_l3_ports' This is
 * useful for debugging the port/interface triggers.
 */
static void
zebra_l3_port_walk_cache_and_print (struct shash* zebra_cached_l3_ports,
                                    bool if_permanent_hash)
{
  struct shash_node *node, *next;
  struct zebra_l3_port* l3_port;

  VLOG_DBG("Walking the L3 port cache to print all L3 ports in %s cache",
            if_permanent_hash ? "permanent" : "temporary");

  if (!shash_count(zebra_cached_l3_ports))
    {
      VLOG_DBG("The hash table is empty. Nothing to walk and print");
      return;
    }

  SHASH_FOR_EACH_SAFE (node, next, zebra_cached_l3_ports)
    {
      if (!node)
        {
          VLOG_DBG("No node found in the L3 port hash\n");
          continue;
        }

      if (!(node->data))
        {
          VLOG_DBG("No node data found\n");
          continue;
        }

      l3_port = (struct zebra_l3_port*)node->data;

      zebra_l3_port_node_print(l3_port);
    }
}

/*
 * This function intitalizes the L3 port cache hash.
 */
static void
zebra_init_cached_l3_ports_hash (void)
{
  shash_init(&zebra_cached_l3_ports);
}

/*
 * This function intitalizes the hash for the L3 ports which are
 * deleted or changed to L2 ports by configuration.
 */
static void
zebra_init_updated_or_changed_l3_ports_hash (void)
{
  shash_init(&zebra_updated_or_changed_l3_ports);
}

/*
 * This function frees all the deleted L3 ports in the hash for the
 * L3 ports which are deleted or changed to L2 ports by configuration.
 */
static void
zebra_cleanup_updated_or_changed_l3_ports_hash (void)
{
  struct shash_node *node, *next;
  struct zebra_l3_port* l3_port;

  VLOG_DBG("Walk all nodes in the deleted L3 port hash and "
           "free all the nodes");

  if (!shash_count(&zebra_updated_or_changed_l3_ports))
    {
      VLOG_DBG("The hash table is empty. Nothing to walk and free");
      return;
    }

  SHASH_FOR_EACH_SAFE (node, next, &zebra_updated_or_changed_l3_ports)
    {
      if (!node)
        {
          VLOG_ERR("No node found in the L3 port hash\n");
          continue;
        }

      if (!(node->data))
        {
          VLOG_ERR("No node data found\n");
          continue;
        }

      l3_port = (struct zebra_l3_port*)node->data;

      zebra_l3_port_node_free(l3_port);
    }
}

/*
 * This function intitalizes the value for zebra_if_port_active_state_changed
 * to false.
 */
static void
zebra_init_if_port_active_state_changed (void)
{
  zebra_if_port_active_state_changed = false;
}

/*
 * This function sets the value for zebra_if_port_active_state_changed
 * to true if some interface admin state changes.
 */
static void
zebra_set_if_port_active_state_changed (void)
{
  zebra_if_port_active_state_changed = true;
}

/*
 * This function gets the value for zebra_if_port_active_state_changed.
 */
static bool
zebra_get_if_port_active_state_changed (void)
{
  return(zebra_if_port_active_state_changed);
}

/*
 * This function clears the value for zebra_if_port_active_state_changed
 * and sets it to false.
 */
static void
zebra_cleanup_if_port_active_state_changed (void)
{
  zebra_if_port_active_state_changed = false;
}

/*
 * This function intitalizes the value for zebra_if_port_updated_or_changed
 * to false.
 */
static void
zebra_init_if_port_updated_or_changed (void)
{
  zebra_if_port_updated_or_changed = false;
  zebra_init_updated_or_changed_l3_ports_hash();
  zebra_port_change_cached_l3_ports_hash_init();
}

/*
 * This function sets the value for zebra_if_port_updated_or_changed
 * to true if some L3 port changes its configuration.
 */
static void
zebra_set_if_port_updated_or_changed (void)
{
  zebra_if_port_updated_or_changed = true;
}

/*
 * This function gets the value for zebra_if_port_updated_or_changed.
 */
static bool
zebra_get_if_port_updated_or_changed (void)
{
  return(zebra_if_port_updated_or_changed);
}

/*
 * This function clears the value for zebra_if_port_updated_or_changed
 * and sets it to false.
 */
static void
zebra_cleanup_if_port_updated_or_changed (void)
{
  zebra_cleanup_updated_or_changed_l3_ports_hash();
  zebra_if_port_updated_or_changed = false;
}

/*
 * This function takes an OVSDB port entry and updates the L3 port cache if
 * it needs to.
 */
static void
zebra_add_or_update_cached_l3_ports_hash (const struct ovsrec_port* ovsrec_port)
{
  /*
   * If the 'ovsrec_port' is NULL, then we have nothing to add/modify
   * into the hash table 'zebra_cached_l3_ports'.
   */
  if (!ovsrec_port)
    {
      VLOG_ERR("The OVSDB port entry is NULL.");
      return;
    }

  if (!ovsrec_port->name)
    {
      VLOG_ERR("The OVSDB port name is NULL.");
      return;
    }

  /*
   * Find the cached L3 port using port name as the key in L3 port
   * hash table .
   */
  struct zebra_l3_port* l3_port =
              (struct zebra_l3_port *)shash_find_data(&zebra_cached_l3_ports,
                                                      ovsrec_port->name);
  struct zebra_l3_port* new_l3_port = NULL;

  /*
   * If l3_port is null, then the port does not exists in the cache.
   */
  if (!l3_port)
    {
      VLOG_DBG("No L3 port exists for port %s in the port cache\n",
                ovsrec_port->name);

      /*
       * If the OVSDB port is not a L3 port, then no need to add the
       * port in the cache.
       */
      if (!zebra_if_ovsrec_port_is_l3(ovsrec_port))
        {
          VLOG_DBG("     This is an L2 port. No need to add into the"
                    " l3 port cache");
          return;
        }

      /*
       * Create a new structure of type zebra_l3_port and add into the
       * hash table.
       */
      l3_port = zebra_l3_port_node_create(ovsrec_port);

      /*
       * If we are not able to allocate the structure for the L3 interface,
       * then return.
       */
      if (!l3_port)
        {
          VLOG_ERR("Unable to add L3 port to the hash");
          return;
        }

      /*
       * Add the L3 port to the hash table 'zebra_cached_l3_ports'.
       * The 'key' into hash table is the port name (l3_port->port_name)
       * while the value is the 'l3_port' pointer. If the add to hash table
       * fails, then free the structure 'l3_port' and return.
       */
      if (!shash_add(&zebra_cached_l3_ports, ovsrec_port->name,
                     l3_port))
        {
          VLOG_ERR("Unable to add L3 port to the hash");
          zebra_l3_port_node_free(l3_port);
        }
      else
          VLOG_DBG("Added L3 port to the hash successfully");
    }
  else
    {
      /*
       * Check if anything changed for this L3 port from the with respect
       * to previous configuration. The following checks need to be done:-
       *
       * 1. If port changed from L3 capable to L2 capable.
       * 2. If the primary and secondary IP addresses changed on the port.
       */
      if (!zebra_if_ovsrec_port_is_l3(ovsrec_port) &&
                              zebra_if_port_is_l3(l3_port))
        {
          VLOG_DBG("Port changed from L3 to L2. Deleting the port %s"
                   " from the hash\n", ovsrec_port->name);

          /*
           * If the OVSDB port is L2 now, then remove the cached port from
           * the L3 port cache.
           */
          l3_port = (struct zebra_l3_port *)shash_find_and_delete(
                                                      &zebra_cached_l3_ports,
                                                      ovsrec_port->name);

          /*
           * Add the convertered L2 port to hash table
           * 'zebra_updated_or_changed_l3_port' for clean up of
           * :static routes.
           */
          l3_port->port_action = ZEBRA_L3_PORT_L3_CHANGED_TO_L2;

          /*
           * If addition of the L3 port into the hash table
           * zebra_updated_or_changed_l3_ports fails, then free the
           * node and return..
           */
          if (!shash_add(&zebra_updated_or_changed_l3_ports,
                         l3_port->port_name,
                         l3_port))
            {
              VLOG_ERR("Unable to add L3 port to the temp hash");
              zebra_l3_port_node_free(l3_port);
            }
          else
            {
              /*
               * If the addition to the hash table is successful,
               * then set a bool suggesting that we need to walk the
               * zebra route table.
               */
              VLOG_DBG("Added L3 port to the hash successfully");
              zebra_set_if_port_updated_or_changed();
            }
        }
      else if (zebra_if_cached_port_and_ovsrec_port_ip4_addr_change
                                                 (ovsrec_port, l3_port) ||
               zebra_if_cached_port_and_ovsrec_port_ip6_addr_change
                                                 (ovsrec_port, l3_port))
        {
          /*
           * If the IP/IPv6 addresses on the port changes, then update the
           * L3 ports cache.
           */
          VLOG_DBG("Port IPv4 changed. Update the port %s IP address in "
                    " the hash and add a node in the temp hash\n",
                    ovsrec_port->name);

          /*
           * Delete the current L3 port node from the L3 port cache.
           */
          l3_port = (struct zebra_l3_port *)shash_find_and_delete(
                                                      &zebra_cached_l3_ports,
                                                      ovsrec_port->name);

          /*
           * Free the cached port node.
           */
          zebra_l3_port_node_free(l3_port);

          /*
           * Add an updated sanpshot of overec_port structure into the
           * &zebra_cached_l3_ports
           *
           * Create a new structure of type zebra_l3_port and add into the
           * hash table.
           */
          new_l3_port = zebra_l3_port_node_create(ovsrec_port);
          new_l3_port->port_action =
                  ZEBRA_L3_PORT_UPADTE_IP_ADDR;

          if (!new_l3_port)
          {
            VLOG_ERR("Unable to add L3 port to the hash");
            return;
          }

          /*
           * If the addition to L3 cache is not successful, then free the
           * newly allocated L3 node.
           */
          if (!shash_add(&zebra_cached_l3_ports, ovsrec_port->name,
                                  new_l3_port))
            {
              VLOG_ERR("Unable to add L3 port to the hash");
              zebra_l3_port_node_free(new_l3_port);
            }
          else
            {

              /*
               * If the addition to the hash table is successful,
               * then set a bool suggesting that we need to walk the
               * zebra route table.
               */
              VLOG_DBG("Added L3 port to the hash successfully");
              zebra_set_if_port_updated_or_changed();
            }
        }
      else
        {
          /*
           * If anything changed in the configuration of the L3 port,
           * then mark the no change flag in the node.
           */
          VLOG_DBG("No change in configuration for this port");
          l3_port->port_action = ZEBRA_L3_PORT_NO_CHANGE;
        }
    }
}

/*
 * This function reclaims all the L3 ports in the cache which were marked
 * for deletion before processing all the ports in the IDL update. All the
 * ports which are not processed in the IDL update will be deleted.
 */
static void
zebra_remove_deleted_cached_l3_ports_hash (void)
{
  struct shash_node *node, *next;
  struct zebra_l3_port* l3_port;

  VLOG_DBG("Walking the L3 port cache to print all L3 ports");

  /*
   * Walk the L3 ports hash table.
   */
  SHASH_FOR_EACH_SAFE (node, next, &zebra_cached_l3_ports)
    {
      if (!node)
        {
          VLOG_ERR("No node found in the L3 port hash\n");
          continue;
        }

      if (!(node->data))
        {
          VLOG_ERR("No data found in the node\n");
          continue;
        }

      l3_port = (struct zebra_l3_port*)node->data;

      /*
       * If the port was marked for deletion, then move the port to
       * the hash table zebra_updated_or_changed_l3_ports for cleanup.
       */
      if (l3_port->port_action == ZEBRA_L3_PORT_DELETE)
        {
          l3_port = (struct zebra_l3_port *)shash_find_and_delete(
                                                    &zebra_cached_l3_ports,
                                                    l3_port->port_name);

          if (!shash_add(&zebra_updated_or_changed_l3_ports,
                         l3_port->port_name,
                         l3_port))
            {
              VLOG_ERR("Unable to add L3 port to the temp hash");
              zebra_l3_port_node_free(l3_port);
            }
          else
            {
              VLOG_DBG("Added L3 port to the hash successfully");
              zebra_set_if_port_updated_or_changed();
            }
        }
    }
}

/*
 * This function finds the L3 port node in a hash table by port name.
 * A pointer to the L3 port node is returned from this function.
 */
struct zebra_l3_port*
zebra_search_port_name_in_l3_ports_hash (struct shash* port_hash,
                                         char* port_name)
{
  struct zebra_l3_port* l3_port = NULL;

  if (!port_hash)
    {
      VLOG_ERR("The port hash is NULL");
      return;
    }

  if (!port_name)
    {
      VLOG_ERR("The port name is NULL");
      return;
    }

  l3_port = (struct zebra_l3_port *)shash_find_data(port_hash,
                                                    port_name);

  return(l3_port);
}

/*
 * This function finds if an IP/IPv6 addresses ocurrs in some subnet
 * of the IP/IPv6 addresses in the port nodes in the port hash.
 * A pointer to the L3 port node is returned from this function. The
 * addresses family is specified by 'afi'.
 */
struct zebra_l3_port*
zebra_search_nh_addr_in_l3_ports_hash (struct shash* port_hash,
                                       char* nexthop_str, afi_t afi)
{
  struct shash_node *node, *next;
  struct shash_node *secondary_node, *secondary_next;
  int ret;
  bool if_next_hop_address_match_found;
  char* ip4_secondary_address;
  char* ip6_secondary_address;
  struct zebra_l3_port* l3_port = NULL;
  struct prefix nexthop_prefix;
  struct prefix port_ip_addr_prefix;

  if (!port_hash)
    {
      VLOG_ERR("The port hash is NULL");
      return;
    }

  if (!nexthop_str || !nexthop_str[0])
    {
      VLOG_ERR("The nexthop string is null");
      return(NULL);
    }

  memset(&nexthop_prefix, 0, sizeof(struct prefix));
  ret = str2prefix(nexthop_str, &nexthop_prefix);

  if (!ret)
    {
      VLOG_ERR("The conversion from nexthop string to "
               "prefix structure for nexthop %s failed",
               nexthop_str);
      return(NULL);
    }
  else
    {
      VLOG_DBG("The conversion from nexthop string to "
                "prefix structure for nexthop %s passed",
                nexthop_str);

      if_next_hop_address_match_found = false;
      SHASH_FOR_EACH_SAFE (node, next, port_hash)
        {
          if (!node)
            {
              VLOG_ERR("No node found in the L3 port "
                       "hash\n");
              continue;
            }

          if (!(node->data))
            {
              VLOG_ERR("No data found in the node\n");
              continue;
            }

          l3_port = (struct zebra_l3_port*)node->data;

          memset(&port_ip_addr_prefix, 0,
                                 sizeof(struct prefix));

          if ((afi == AFI_IP) && !((l3_port->ip4_address) ||
              (shash_count(&(l3_port->ip4_address_secondary)))))
            {
              VLOG_ERR("Mismatch between address family "
                       "and IPv4 address");
              continue;
            }

          if ((afi == AFI_IP6) && !((l3_port->ip6_address) ||
                (shash_count(&(l3_port->ip6_address_secondary)))))
            {
                VLOG_ERR("Mismatch between address family "
                         "and IPv6 address");
                continue;
            }

           if ((afi == AFI_IP) && ((l3_port->ip4_address) ||
                (shash_count(&(l3_port->ip4_address_secondary)))))
            {
              ret = str2prefix(l3_port->ip4_address,
                                  &port_ip_addr_prefix);

              if (!ret)
                {
                  VLOG_ERR("The conversion from ipv4 "
                           "address string to prefix "
                           "structure for nexthop %s "
                           "failed", l3_port->ip4_address);
                  continue;
                }
              else
                {
                  VLOG_DBG("The conversion from ipv4 "
                           "address string to prefix "
                           "structure for nexthop %s "
                           "passed", l3_port->ip4_address);
                }

              if (prefix_match(&port_ip_addr_prefix,
                               &nexthop_prefix))
                {
                  VLOG_DBG("Got a match for the ip4 address "
                            "%s and nexthop ip %s",
                            l3_port->ip4_address, nexthop_str);
                  if_next_hop_address_match_found = true;
                  break;
                }
              else
                {
                  VLOG_DBG("No match for the ip4 address "
                           "%s and nexthop ip %s",
                           l3_port->ip4_address, nexthop_str);
                }

              VLOG_DBG("Walking the IPv4 secondary address "
                       "hash to find if the nexthop occurs "
                       "secondary subnet");

              SHASH_FOR_EACH_SAFE (
                  secondary_node, secondary_next,
                  &(l3_port->ip4_address_secondary))
                {
                  if (!secondary_node)
                    {
                      VLOG_ERR("No node found in the L3 "
                               "port hash\n");
                      continue;
                    }

                  if (!(secondary_node->data))
                    {
                      VLOG_ERR("No node data found\n");
                      continue;
                    }

                  ip4_secondary_address =
                                 (char*)secondary_node->data;

                  ret = str2prefix(ip4_secondary_address,
                                          &port_ip_addr_prefix);

                  if (!ret)
                    {
                      VLOG_ERR("The conversion from ipv4 "
                               "address string to prefix "
                               "structure for nexthop %s "
                               "failed",
                               ip4_secondary_address);
                      continue;
                    }
                  else
                    {
                      VLOG_DBG("The conversion from ipv4 "
                                "address string to prefix "
                                "structure for nexthop %s "
                                "passed",
                                ip4_secondary_address);
                    }

                  if (prefix_match(&port_ip_addr_prefix,
                                   &nexthop_prefix))
                    {
                      VLOG_DBG("Got a match for the ip4 address "
                                 "%s and nexthop ip %s",
                                 ip4_secondary_address, nexthop_str);
                       if_next_hop_address_match_found = true;
                       break;
                    }
                  else
                    {
                      VLOG_DBG("No match for the ip4 address "
                                "%s and nexthop ip %s",
                                ip4_secondary_address, nexthop_str);
                    }
                }

                if (if_next_hop_address_match_found)
                  break;

            }

          if ((afi == AFI_IP6) && ((l3_port->ip6_address) ||
              (shash_count(&(l3_port->ip6_address_secondary)))))
            {
              ret = str2prefix(l3_port->ip6_address,
                               &port_ip_addr_prefix);

              if (!ret)
                {
                  VLOG_ERR("The conversion from ipv6 "
                           "address string to prefix "
                           "structure for nexthop %s "
                           "failed", l3_port->ip6_address);
                  continue;
                }
              else
                {
                  VLOG_DBG("The conversion from ipv6 "
                           "address string to prefix "
                           "structure for nexthop %s "
                           "passed", l3_port->ip6_address);
                }

              if (prefix_match(&port_ip_addr_prefix,
                               &nexthop_prefix))
                {
                  VLOG_DBG("Got a match for the ip6 address "
                           "%s and nexthop ip %s",
                           l3_port->ip6_address, nexthop_str);
                  if_next_hop_address_match_found = true;
                  break;
                }
              else
                {
                  VLOG_DBG("No match for the ip6 address "
                            "%s and nexthop ip %s",
                            l3_port->ip6_address, nexthop_str);
                }

              VLOG_DBG("Walking the IPv6 secondary address "
                        "hash to find if the nexthop occurs "
                        "secondary subnet");

              SHASH_FOR_EACH_SAFE (
                  secondary_node, secondary_next,
                  &(l3_port->ip6_address_secondary))
                {
                  if (!secondary_node)
                    {
                      VLOG_ERR("No node found in the L3 "
                               "port hash\n");
                      continue;
                    }

                  if (!(secondary_node->data))
                    {
                      VLOG_ERR("No node data found\n");
                      continue;
                    }

                  ip6_secondary_address =
                                     (char*)secondary_node->data;

                  ret = str2prefix(ip6_secondary_address,
                                            &port_ip_addr_prefix);

                  if (!ret)
                    {
                      VLOG_ERR("The conversion from ipv4 "
                               "address string to prefix "
                               "structure for nexthop %s "
                               "failed",
                               ip6_secondary_address);
                      continue;
                    }
                  else
                    {
                      VLOG_DBG("The conversion from ipv4 "
                               "address string to prefix "
                               "structure for nexthop %s "
                               "passed",
                               ip6_secondary_address);
                    }

                  if (prefix_match(&port_ip_addr_prefix,
                                         &nexthop_prefix))
                    {
                      VLOG_DBG("Got a match for the ip6 address "
                               "%s and nexthop ip %s",
                               ip6_secondary_address, nexthop_str);
                      if_next_hop_address_match_found = true;
                      break;
                    }
                  else
                    {
                      VLOG_DBG("No match for the ip6 address "
                               "%s and nexthop ip %s",
                               ip6_secondary_address, nexthop_str);
                    }
                }

                if (if_next_hop_address_match_found)
                  break;
            }
        }
    }

  if (!if_next_hop_address_match_found)
    return(NULL);

  return(l3_port);
}

static bool
zebra_nh_port_in_deleted_cached_l3_ports_hash (char* port_name)
{
  struct zebra_l3_port* l3_port = NULL;

  if (!port_name || !port_name[0])
    {
      VLOG_ERR("The port name is null");
      return(false);
    }

  l3_port = zebra_search_port_name_in_l3_ports_hash(
                                &zebra_updated_or_changed_l3_ports,
                                port_name);

  if (!l3_port)
    {
      VLOG_DBG("Interface %s not found in the hash", port_name);
      return(false);
    }
  else
    {
      VLOG_DBG("Found a valid L3 port structure");
      zebra_l3_port_node_print(l3_port);
      if ((l3_port->port_action ==
                        ZEBRA_L3_PORT_L3_CHANGED_TO_L2) ||
          (l3_port->port_action == ZEBRA_L3_PORT_DELETE))
        {
          VLOG_DBG("The next-hop is now deleted. Cleanup "
                   "The OVSDB route and next-hop and kernel"
                   " route and next-hop");
          return(true);
        }
    }

  return(false);
}

static bool
zebra_nh_address_in_deleted_cached_l3_ports_hash (char* nexthop_str,
                                                  afi_t afi)
{
  struct zebra_l3_port* l3_port = NULL;

  if (!nexthop_str || !nexthop_str[0])
    {
      VLOG_ERR("The nexthop string is null");
      return(false);
    }

  l3_port = zebra_search_nh_addr_in_l3_ports_hash(
                          &zebra_updated_or_changed_l3_ports,
                          nexthop_str, afi);

  if (!l3_port)
    {
      VLOG_DBG("Nexthop addr %s not found in the hash",
               nexthop_str);
      return(false);
    }
  else
    {
      VLOG_DBG("Found a valid L3 port structure containing "
               "nexthop %s", nexthop_str);

      zebra_l3_port_node_print(l3_port);
      if ((l3_port->port_action ==
                        ZEBRA_L3_PORT_L3_CHANGED_TO_L2) ||
          (l3_port->port_action == ZEBRA_L3_PORT_DELETE))
        {
          VLOG_DBG("The next-hop is now deleted. Cleanup "
                   "The OVSDB route and next-hop and kernel"
                   " route and next-hop");
          return(true);
        }
    }

    return(false);
}

static bool
zebra_nh_port_active_in_cached_l3_ports_hash (char* port_name)
{
  struct zebra_l3_port* l3_port = NULL;

  if (!port_name || !port_name[0])
    {
      VLOG_ERR("The port name is null");
      assert(0);
    }

  l3_port = zebra_search_port_name_in_l3_ports_hash(
                                &zebra_cached_l3_ports,
                                port_name);

  if (!l3_port)
    {
      VLOG_DBG("Interface %s not found in the hash", port_name);
      return(false);
    }

  VLOG_DBG("Found a valid L3 port structure for port %s state %s",
           port_name, l3_port->if_active ? "up":"down");

  return(l3_port->if_active);
}

static bool
zebra_nh_addr_active_in_cached_l3_ports_hash (char* nexthop_str,
                                              afi_t afi)
{
  struct zebra_l3_port* l3_port = NULL;

  l3_port = zebra_search_nh_addr_in_l3_ports_hash(
                                &zebra_cached_l3_ports,
                                nexthop_str, afi);

  if (!l3_port)
    {
      VLOG_DBG("nexthop address %s not found in the hash",
                nexthop_str);
      return(false);
    }

  VLOG_DBG("Found a valid L3 port structure for next-hop %s",
           nexthop_str);

  return(l3_port->if_active);
}

struct zebra_l3_port*
zebra_l3_port_node_lookup_by_interface_name (char* interface_name)
{
  struct zebra_l3_port* l3_port = NULL;
  struct shash_node *node, *next;
  bool if_found;
  int interface_index;
  struct ovsrec_interface* interface = NULL;

  if (!interface_name)
    {
      VLOG_DBG("The interface name is NULL");
      return(NULL);
    }

  SHASH_FOR_EACH_SAFE (node, next, &zebra_cached_l3_ports)
    {
      if (!node)
        {
          VLOG_DBG("No node found in the L3 port hash\n");
          continue;
        }

      if (!(node->data))
        {
          VLOG_DBG("No node data found\n");
          continue;
        }

      l3_port = (struct zebra_l3_port*)node->data;

      if_found = false;

      VLOG_DBG("THe number of interface are: %u",
                l3_port->cfg->n_interfaces);

      for (interface_index = 0;
           interface_index < l3_port->cfg->n_interfaces;
           ++interface_index)
        {
          interface = l3_port->cfg->interfaces[interface_index];

          VLOG_DBG("Walking interface %s", interface->name);

          if (!interface)
            {
              VLOG_DBG("The interface pointer in port is NULL");
              continue;
            }

          if (interface->name &&
              (strcmp(interface->name,
                      interface_name) == 0))
           {
              VLOG_DBG("Found the interface %s in port %s",
                        interface_name, l3_port->port_name);
              if_found = true;
              break;
            }
        }

        if (if_found)
          break;
    }

    if (!if_found)
      return(NULL);

    return(l3_port);
}

/*
 * This function takes a pointer to an OVSDB interface entry and
 * updates the L3 port state. If the interface state becomes "up",
 * then the L3 port state is set to be active otherwise it will be
 * set to inactive.
 */
static void
zebra_update_port_active_state (const struct ovsrec_interface *interface)
{
  struct zebra_l3_port* l3_port = NULL;
  bool new_active_state;

  /*
   * If the OVSDB interface entry pointer is null, then return.
   */
  if (!(interface->name))
    {
      VLOG_ERR("The interface name is NULL");
      return;
    }

  /*
   * Search the L3 port node using the interface name.
   */
  l3_port =
      zebra_l3_port_node_lookup_by_interface_name(interface->name);

  /*
   * If the port entry is null, then this L3 port does not exist in
   * the L3 port cache. Return from this function.
   */
  if (!l3_port)
    {
      VLOG_DBG("Unable to find the port for interface %s",
                interface->name);
      return;
    }

  /*
   * Get the new admin state from the interface entry.
   */
  new_active_state = zebra_get_port_active_state(l3_port->cfg);

  /*
   * Update the port active state. If the port state has changed,
   * then force a full walk of zebra's route table.
   */
  if (new_active_state != l3_port->if_active)
    {
      VLOG_DBG("Port state for %s changed from %s to %s",
               l3_port->port_name,
               l3_port->if_active ? "Active" : "Inactive",
               new_active_state ? "Active" : "Inactive");
      l3_port->if_active = new_active_state;
      zebra_set_if_port_active_state_changed();
    }
}


/*
 * Find routes and their next-hops which have been deleted/shut and add them to
 * route delete list. List is used to delete routes from system
 */
static void
zebra_find_routes_with_deleted_ports (
                        afi_t afi, safi_t safi, u_int32_t id,
                        enum zebra_handle_port_op_options option)
{
  struct route_table *table;
  struct route_node *rn;
  struct rib *rib;
  struct nexthop *nexthop;
  char prefix_str[256];
  struct prefix *p = NULL;
  char nexthop_str[256];
  char ifname[IF_NAMESIZE + 1];
  #ifdef VRF_ENABLE
  const struct ovsrec_route *ovs_route = NULL;
  #endif
  table = vrf_table (afi, safi, id);
  if (!table)
    {
      VLOG_ERR("Table not found");
      return;
    }

  /*
   * returning from the function if the hash table
   * 'zebra_updated_or_changed_l3_ports' is empty.
   */
  if (!zebra_get_if_port_updated_or_changed()
      && !zebra_get_if_port_active_state_changed())
    {
      VLOG_DBG("No change in L3 port configuration. No nexthops to delete");
      return;
    }

  for (rn = route_top (table); rn; rn = route_next (rn))
    {
      if (!rn)
        {
          VLOG_ERR("Route node is NULL");
          continue;
        }

      p = &rn->p;
      memset(prefix_str, 0, sizeof(prefix_str));
      prefix2str(p, prefix_str, sizeof(prefix_str));

      VLOG_DBG("Prefix %s Family %d\n",prefix_str, PREFIX_FAMILY(p));

      RNODE_FOREACH_RIB (rn, rib)
        {
          #ifdef VRF_ENABLE
          if (rib->ovsdb_route_row_ptr)
            {
              ovs_route = (struct ovsrec_route *)(rib->ovsdb_route_row_ptr);
              if (!(zebra_is_route_in_my_vrf(ovs_route)))
                continue;
            }
          #endif

          if ((rib->type != ZEBRA_ROUTE_STATIC &&
              rib->type != ZEBRA_ROUTE_BGP) ||
              !rib->nexthop)
            {
              VLOG_DBG("Not a static/BGP route or null next-hop");
              continue;
            }

          for (nexthop = rib->nexthop; nexthop; nexthop = nexthop->next)
            {
              memset(nexthop_str, 0, sizeof(nexthop_str));
              memset(ifname, 0, sizeof(ifname));

              if (afi == AFI_IP)
                {
                  if (nexthop->type == NEXTHOP_TYPE_IPV4)
                    inet_ntop(AF_INET, &nexthop->gate.ipv4,
                              nexthop_str, sizeof(nexthop_str));
                }
              else if (afi == AFI_IP6)
                {
                  if (nexthop->type == NEXTHOP_TYPE_IPV6)
                    inet_ntop(AF_INET6, &nexthop->gate.ipv6,
                              nexthop_str, sizeof(nexthop_str));
                }

              if ((nexthop->type == NEXTHOP_TYPE_IFNAME) ||
                  (nexthop->type == NEXTHOP_TYPE_IPV4_IFNAME) ||
                  (nexthop->type == NEXTHOP_TYPE_IPV6_IFNAME))
                strncpy(ifname, nexthop->ifname, IF_NAMESIZE);

              VLOG_DBG("Processing route %s for the next-hop IP %s or "
                        "interface %s\n", prefix_str,
                        nexthop_str[0] ? nexthop_str : "NONE",
                        ifname[0] ? ifname : "NONE");

              /*
               * If 'ifname' is legal, then peak into the hash table
               * 'zebra_updated_or_changed_l3_ports' to see if the L3 port
               * got deleted.
               */
              if (ifname[0])
                {
                  switch (option)
                    {
                      case ZEBRA_L3_PORT_DELETE_UPDATE_OPTION:
                        if (zebra_nh_port_in_deleted_cached_l3_ports_hash(ifname))
                          {
                            /*
                              * Remove the next-hop via the deleted port from
                              * the kernel.
                              */
                            zebra_route_list_add_data(rn, rib, nexthop);
                            zebra_delete_route_nexthop_port_from_db(rib,
                                                                  ifname);
                          }
                        break;

                      case ZEBRA_L3_PORT_ACTIVE_STATE_CHN_OPTION:
                        if (!zebra_nh_port_active_in_cached_l3_ports_hash(ifname))
                          {
                            VLOG_DBG("Mark the next-hop port %s of the "
                                     "route as unselected in OVSDB", ifname);
                            zebra_update_selected_nh(rn, rib, ifname, NULL,
                                                     ZEBRA_NH_UNINSTALL);
                          }
                        else
                          {
                            VLOG_DBG("Mark the next-hop port %s of the "
                                     "route as selected in OVSDB", ifname);
                            zebra_update_selected_nh(rn, rib, ifname, NULL,
                                                     ZEBRA_NH_INSTALL);
                          }
                        break;

                      default:
                        VLOG_ERR("Unsupported option for zebra OVSDB route "
                                 "cleanup");
                        break;
                    }
                }

              /*
               * If 'nexthop' is legal, then walk the hash table
               * 'zebra_updated_or_changed_l3_ports' to see if the L3 port
               * with the IP subnet got deleted.
               */
              if (nexthop_str[0])
                {
                  switch (option)
                    {
                      case ZEBRA_L3_PORT_DELETE_UPDATE_OPTION:

                        /*
                         * Check if the next-hop occurs in the port cache for
                         * deleted ports.
                         */
                        if (zebra_nh_address_in_deleted_cached_l3_ports_hash(
                                                         nexthop_str, afi))
                          {
                            VLOG_DBG("The next-hop string %s found in the "
                                     " deleted L3 port list", nexthop_str);
                            zebra_route_list_add_data(rn, rib, nexthop);
                            zebra_delete_route_nexthop_addr_from_db(rib,
                                                                  nexthop_str);
                          }
                        else
                          {
                            /*
                             * If the next-hop address does not occur in the
                             * L3 port cache or if the next-hop address occurs
                             * in some port node in L3 port cache but the port
                             * is shut, then mark the next-hop as unselected in
                             * OVSDB. Otherwise mark the next-hop as selected
                             * in OVSDB.
                             */
                            if (!zebra_nh_addr_active_in_cached_l3_ports_hash(
                                                                nexthop_str, afi))
                              {
                                VLOG_DBG("Mark the next-hop addr %s of the "
                                         "route as unselected in OVSDB",
                                         nexthop_str);
                                zebra_update_selected_nh(rn, rib, NULL,
                                                         nexthop_str,
                                                         ZEBRA_NH_UNINSTALL);
                              }
                            else
                              {
                                VLOG_DBG("Mark the next-hop addr %s of the "
                                         "route as selected in OVSDB",
                                         nexthop_str);
                                zebra_update_selected_nh(rn, rib, NULL,
                                                         nexthop_str,
                                                         ZEBRA_NH_INSTALL);
                              }
                          }
                        break;

                      case ZEBRA_L3_PORT_ACTIVE_STATE_CHN_OPTION:
                        if (!zebra_nh_addr_active_in_cached_l3_ports_hash(
                                                                nexthop_str, afi))
                          {
                            VLOG_DBG("Mark the next-hop addr %s of the "
                                      "route as unselected in OVSDB", nexthop_str);
                            zebra_update_selected_nh(rn, rib, NULL, nexthop_str,
                                                     ZEBRA_NH_UNINSTALL);
                          }
                        else
                          {
                            VLOG_DBG("Mark the next-hop addr %s of the "
                                     "route as selected in OVSDB", nexthop_str);
                            zebra_update_selected_nh(rn, rib, NULL, nexthop_str,
                                                     ZEBRA_NH_INSTALL);
                          }
                        break;

                      default:
                        VLOG_ERR("Unsupported option for zebra OVSDB route "
                                 "cleanup");
                        break;
                    }
                }
            }
        }
    }
}

/*
 * End of function for handling port add, delete and update triggers
 * from OVSDB.
 ************************************************************************
 */

/* ovs appctl dump function for this daemon
 * This is useful for debugging
 */
static void
zebra_unixctl_dump (struct unixctl_conn *conn, int argc OVS_UNUSED,
                    const char *argv[] OVS_UNUSED, void *aux OVS_UNUSED)
{
  unixctl_command_reply_error(conn, "Nothing to dump");
}

/* ovs appctl function for this daemon
 * to display or modify the level of zebra logging.
 */
static void
debug_parse_options(int argc, const char *argv[], char *return_status,
                    struct unixctl_conn *conn)
{
  if (argc != 2) {
    sprintf(return_status, "Wrong argument count - %d", argc);
    return;
  }

  if (!strncmp("event", argv[1], NUM_CHAR_CMP)) {
    zebra_debug_event = ZEBRA_DEBUG_EVENT;
  } else if (!strncmp("packet", argv[1], NUM_CHAR_CMP)) {
    zebra_debug_packet |= ZEBRA_DEBUG_PACKET;
  } else if (!strncmp("send", argv[1], NUM_CHAR_CMP)) {
    zebra_debug_packet |= ZEBRA_DEBUG_SEND;
  } else if (!strncmp("recv", argv[1], NUM_CHAR_CMP)) {
    zebra_debug_packet |= ZEBRA_DEBUG_RECV;
  } else if (!strncmp("detail", argv[1], NUM_CHAR_CMP)) {
    zebra_debug_packet |= ZEBRA_DEBUG_DETAIL;
  } else if (!strncmp("kernel", argv[1], NUM_CHAR_CMP)) {
    zebra_debug_kernel = ZEBRA_DEBUG_KERNEL;
  } else if (!strncmp("rib", argv[1], NUM_CHAR_CMP)) {
    zebra_debug_rib |= ZEBRA_DEBUG_RIB;
  } else if (!strncmp("ribq", argv[1], NUM_CHAR_CMP)) {
    zebra_debug_rib |= ZEBRA_DEBUG_RIB_Q;
  } else if (!strncmp("fpm", argv[1], NUM_CHAR_CMP)) {
    zebra_debug_fpm = ZEBRA_DEBUG_FPM;
  } else if (!strncmp("all", argv[1], NUM_CHAR_CMP)) {
    zebra_debug_event = ZEBRA_DEBUG_EVENT;
    zebra_debug_packet = ZEBRA_DEBUG_PACKET | ZEBRA_DEBUG_SEND | \
                         ZEBRA_DEBUG_RECV  | ZEBRA_DEBUG_DETAIL;
    zebra_debug_kernel = ZEBRA_DEBUG_KERNEL;
    zebra_debug_rib = ZEBRA_DEBUG_RIB | ZEBRA_DEBUG_RIB_Q;
    zebra_debug_fpm = ZEBRA_DEBUG_FPM;
  } else if (!strncmp("off", argv[1], NUM_CHAR_CMP)) {
    zebra_debug_event = 0;
    zebra_debug_packet = 0;
    zebra_debug_kernel = 0;
    zebra_debug_rib = 0;
    zebra_debug_fpm = 0;
  } else if (!strncmp("show", argv[1], NUM_CHAR_CMP)) {
    if (IS_ZEBRA_DEBUG_EVENT)
      sprintf(return_status + strlen(return_status), "event\n");
    if (IS_ZEBRA_DEBUG_KERNEL)
      sprintf(return_status + strlen(return_status), "kernel\n");
    if (IS_ZEBRA_DEBUG_FPM)
      sprintf(return_status + strlen(return_status), "fpm\n");
    if (IS_ZEBRA_DEBUG_PACKET)
      sprintf(return_status + strlen(return_status), "packet\n");
    if (IS_ZEBRA_DEBUG_SEND)
      sprintf(return_status + strlen(return_status), "send\n");
    if (IS_ZEBRA_DEBUG_RECV)
      sprintf(return_status + strlen(return_status), "recv\n");
    if (IS_ZEBRA_DEBUG_DETAIL)
      sprintf(return_status + strlen(return_status), "detail\n");
    if (IS_ZEBRA_DEBUG_RIB)
      sprintf(return_status + strlen(return_status), "rib\n");
    if (IS_ZEBRA_DEBUG_RIB_Q)
      sprintf(return_status + strlen(return_status), "ribq\n");
  } else {
    sprintf(return_status, "Unsupported argument - %s", argv[1]);
  }

  return;
}

static void
zebra_unixctl_set_debug_level (struct unixctl_conn *conn, int argc OVS_UNUSED,
                    const char *argv[] OVS_UNUSED, void *aux OVS_UNUSED)
{
  char return_status[200] = "";

  debug_parse_options(argc, argv, return_status, conn);

  if (!strncmp(return_status, "Unsupported argument", NUM_CHAR_UNSUPPORTED)) {
    unixctl_command_reply_error(conn, return_status);
  } else {
    unixctl_command_reply(conn, return_status);
  }

  return;
}

/* Create a connection to the OVSDB at db_path and create a dB cache
 * for this daemon. */
static void
ovsdb_init (const char *db_path)
{
  #ifdef VRF_ENABLE
  char lock_name[64] = {0};
  char netns_name[UUID_LEN + 1];
  #endif
  /* Initialize IDL through a new connection to the dB. */
  idl = ovsdb_idl_create(db_path, &ovsrec_idl_class, false, true);
  idl_seqno = ovsdb_idl_get_seqno(idl);

  #ifdef VRF_ENABLE
  zebra_get_my_netns_name(netns_name);

  /* TODO "swns" to be defined later as a string in openswitch-idl.h*/
  if (strncmp(netns_name, "swns", OVSDB_VRF_NAME_MAXLEN))
    {
      sprintf(lock_name, "%s_%d", "ops_zebra", getpid());
    }
  else
    {
      sprintf(lock_name, "%s", "ops_zebra");
    }

  ovsdb_idl_set_lock(idl, lock_name);
  #else
  ovsdb_idl_set_lock(idl, "ops_zebra");
  #endif

  ovsdb_idl_verify_write_only(idl);

  /* Cache OpenVSwitch table */
  ovsdb_idl_add_table(idl, &ovsrec_table_system);

  ovsdb_idl_add_column(idl, &ovsrec_system_col_cur_cfg);
  ovsdb_idl_add_column(idl, &ovsrec_system_col_hostname);

  /* Register for ROUTE table */
  /* We need to register for columns to really get rows in the idl */
  ovsdb_idl_add_table(idl, &ovsrec_table_route);
  ovsdb_idl_add_column(idl, &ovsrec_route_col_prefix);
  ovsdb_idl_add_column(idl, &ovsrec_route_col_address_family);
  ovsdb_idl_add_column(idl, &ovsrec_route_col_distance);
  ovsdb_idl_add_column(idl, &ovsrec_route_col_metric);
  ovsdb_idl_add_column(idl, &ovsrec_route_col_from);
  ovsdb_idl_add_column(idl, &ovsrec_route_col_sub_address_family);
  #ifdef VRF_ENABLE
  ovsdb_idl_add_column(idl, &ovsrec_route_col_vrf);
  #endif
  ovsdb_idl_add_column(idl, &ovsrec_route_col_nexthops);
  ovsdb_idl_omit_alert(idl, &ovsrec_route_col_nexthops);

  /*
   * Register to the "selected" column in the route table to write
   * to it. If selected is TRUE, this is a FIB entry
   */
  ovsdb_idl_add_column(idl, &ovsrec_route_col_selected);
  ovsdb_idl_omit_alert(idl, &ovsrec_route_col_selected);

  /* Register for NextHop table */
  ovsdb_idl_add_table(idl, &ovsrec_table_nexthop);
  ovsdb_idl_add_column(idl, &ovsrec_nexthop_col_ip_address);
  ovsdb_idl_add_column(idl, &ovsrec_nexthop_col_ports);
  ovsdb_idl_add_column(idl, &ovsrec_nexthop_col_status);
  ovsdb_idl_add_column(idl, &ovsrec_nexthop_col_selected);
  ovsdb_idl_omit_alert(idl, &ovsrec_nexthop_col_selected);

  /* Register for port table */
  ovsdb_idl_add_table(idl, &ovsrec_table_port);
  ovsdb_idl_add_column(idl, &ovsrec_port_col_name);
  ovsdb_idl_add_column(idl, &ovsrec_port_col_ip6_address);
  ovsdb_idl_add_column(idl, &ovsrec_port_col_ip4_address);
  ovsdb_idl_add_column(idl, &ovsrec_port_col_ip4_address_secondary);
  ovsdb_idl_add_column(idl, &ovsrec_port_col_ip6_address_secondary);
  ovsdb_idl_add_column(idl, &ovsrec_port_col_interfaces);

  /*
   * Adding the interface table so that we can listen to interface
   * "up"/"down" notifications. We need to add two columns to the
   * interface table:-
   * 1. Interface name for finding which port corresponding to the
   *    interface went "up"/"down".
   * 2. Interface admin state.
   */
  ovsdb_idl_add_table(idl, &ovsrec_table_interface);
  ovsdb_idl_add_column(idl, &ovsrec_interface_col_name);
  ovsdb_idl_add_column(idl, &ovsrec_interface_col_admin_state);

  /* Register for the vrf table to find the if the port is L2/L# */
  ovsdb_idl_add_table(idl, &ovsrec_table_vrf);
  ovsdb_idl_add_column(idl, &ovsrec_vrf_col_name);
  ovsdb_idl_add_column(idl, &ovsrec_vrf_col_ports);

  /*
   * Intialize the local L3 port hash.
   */
  zebra_init_cached_l3_ports_hash();

  /* Register ovs-appctl commands for this daemon. */
  unixctl_command_register("zebra/dump", "", 0, 0, zebra_unixctl_dump, NULL);
  unixctl_command_register("zebra/debug", "event|packet|send|recv|detail|kernel"
                           "|rib|ribq|fpm|all|show|off", 1, 1,
                           zebra_unixctl_set_debug_level, NULL);
}

/* This function is invoked on appctl exit command to stop the daemon
 */
static void
ops_zebra_exit (struct unixctl_conn *conn, int argc OVS_UNUSED,
                const char *argv[] OVS_UNUSED, void *exiting_)
{
  boolean *exiting = exiting_;
  *exiting = true;
  unixctl_command_reply(conn, NULL);
}

/* This function lists all the OVS specific command line options
 * for this daemon
 */
static void
usage (void)
{
  printf("%s: OpenSwitch zebra daemon\n"
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

/* Parse function to parse OVS command line options
 * TODO: Need to merge this parse function with the main parse function
 * in zebra to avoid issues.
 */
static char *
zebra_ovsdb_parse_options (int argc, char *argv[], char **unixctl_pathp)
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

  for (;;)
    {
      int c;

      c = getopt_long(argc, argv, short_options, long_options, NULL);
      if (c == -1)
        break;

      switch (c)
        {
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

/* Setup zebra to connect with ovsdb and daemonize. This daemonize is used
 * over the daemonize in the main function to keep the behavior consistent
 * with the other daemons in the OpenSwitch system
 */
void
zebra_ovsdb_init (int argc, char *argv[])
{
  int retval;
  char *ovsdb_sock;

  memset(&glob_zebra_ovs, 0, sizeof(glob_zebra_ovs));

  set_program_name(argv[0]);
  proctitle_init(argc, argv);
  fatal_ignore_sigpipe();

  /* Parse commandline args and get the name of the OVSDB socket. */
  ovsdb_sock = zebra_ovsdb_parse_options(argc, argv, &appctl_path);

  /* Initialize the metadata for the IDL cache. */
  ovsrec_init();
  /* Fork and return in child process; but don't notify parent of
   * startup completion yet. */
  daemonize_start();

  /* Create UDS connection for ovs-appctl. */
  retval = unixctl_server_create(appctl_path, &appctl);
  if (retval)
    exit(EXIT_FAILURE);

  /* Register the ovs-appctl "exit" command for this daemon. */
  unixctl_command_register("exit", "", 0, 0, ops_zebra_exit, &exiting);

  /* Create the IDL cache of the dB at ovsdb_sock. */
  ovsdb_init(ovsdb_sock);
  free(ovsdb_sock);

  /* Notify parent of startup completion. */
  daemonize_complete();

  /* Enable asynch log writes to disk. */
  vlog_enable_async();

  VLOG_INFO_ONCE("%s (OpenSwich Zebra Daemon) started", program_name);

  glob_zebra_ovs.enabled = 1;
  return;
}

static void
zebra_ovs_clear_fds (void)
{
  struct poll_loop *loop = poll_loop();
  free_poll_nodes(loop);
  loop->timeout_when = LLONG_MAX;
  loop->timeout_where = NULL;
}

/* Check if the system is already configured. The daemon should
 * not process any callbacks unless the system is configured.
 */
static inline void
zebra_chk_for_system_configured (void)
{
  const struct ovsrec_system *ovs_vsw = NULL;

  if (system_configured)
    /* Nothing to do if we're already configured. */
    return;

  ovs_vsw = ovsrec_system_first(idl);

  if (ovs_vsw && (ovs_vsw->cur_cfg > (int64_t) 0))
    {
      system_configured = true;
      VLOG_INFO("System is now configured (cur_cfg=%d).",
		(int)ovs_vsw->cur_cfg);
    }
}

/* For each route row in OVSDB, walk all the nexthops and
 * return TRUE if any nexthop is modified
 */
bool
is_route_nh_rows_modified (const struct ovsrec_route *route)
{
  const struct ovsrec_nexthop *nexthop;
  int index;

  for(index=0; index < route->n_nexthops; index++)
    {
      nexthop = route->nexthops[index];
      if ( (OVSREC_IDL_IS_ROW_INSERTED(nexthop, idl_seqno)) ||
           (OVSREC_IDL_IS_ROW_MODIFIED(nexthop, idl_seqno)) )
        return true;
    }

  return false;
}

/* Return true of any nexthop is deleted for route
 */
bool
is_rib_nh_rows_deleted (const struct ovsrec_route *route)
{
  const struct ovsrec_nexthop *nexthop;

  nexthop = route->nexthops[0];
  if ( ( nexthop != NULL ) &&
       ( OVSREC_IDL_ANY_TABLE_ROWS_DELETED(nexthop, idl_seqno) ) )
    return 1;

  return 0;
}

static void
print_key (struct zebra_route_key *rkey)
{
  VLOG_DBG("prefix=0x%x", rkey->prefix.u.ipv4_addr.s_addr);
  VLOG_DBG("prefix len=%d", rkey->prefix_len);
  VLOG_DBG("nexthop=0x%x", rkey->nexthop.u.ipv4_addr.s_addr);
  if ( strlen(rkey->ifname) !=0 )
    VLOG_DBG("ifname=0x%s", rkey->ifname);
}

/* Hash route key */
unsigned int
zebra_route_key_make (void *p)
{
  const struct zebra_route_key *rkey = (struct zebra_route_key *) p;
  unsigned int key = 0;

   key = jhash2((const uint32_t *)rkey,
                (sizeof(struct zebra_route_key)) / sizeof(uint32_t), 0);

  return key;
}

/* Compare two keys */
static int
zebra_route_key_cmp (const void *arg1, const void *arg2)
{
  const struct zebra_route_key *rkey_1 = (struct zebra_route_key *) arg1;

  const struct zebra_route_key *rkey_2 = (struct zebra_route_key *) arg2;

  if (!memcmp(rkey_1, rkey_2, sizeof(struct zebra_route_key)))
    return 1;
  else
    return 0;
}

/* Init hash table and size of table */
static void
zebra_route_hash_init (void)
{
  zebra_route_hash = hash_create_size(HASH_BUCKET_SIZE, zebra_route_key_make,
                                      zebra_route_key_cmp);
}

/* Allocate route key */
static void *
zebra_route_hash_alloc (void *p)
{
  struct zebra_route_key *val = (struct zebra_route_key *)p;
  struct zebra_route_key *addr;

  addr = XMALLOC(MTYPE_TMP, sizeof (struct zebra_route_key));
  assert(addr);
  memcpy(addr, val, sizeof(struct zebra_route_key));

  return addr;
}

/* Add ovsdb routes to hash table */
static void
zebra_route_hash_add (const struct ovsrec_route *route)
{
  struct zebra_route_key tmp_key;
  struct zebra_route_key *add;
  int ret;
  size_t i;
  struct ovsrec_nexthop *nexthop;
  struct prefix p;
  int addr_family;

  if (!route || !route->prefix)
    return;

  ret = str2prefix(route->prefix, &p);
  if (ret <= 0)
    {
      VLOG_ERR("Malformed Dest address=%s", route->prefix);
      return;
    }

  memset(&tmp_key, 0, sizeof(struct zebra_route_key));
  if (strcmp(route->address_family,
             OVSREC_ROUTE_ADDRESS_FAMILY_IPV4) == 0)
    {
      addr_family = AF_INET;
      tmp_key.prefix.u.ipv4_addr = p.u.prefix4;
    }
  else if (strcmp(route->address_family,
             OVSREC_ROUTE_ADDRESS_FAMILY_IPV6) == 0)
    {
      addr_family = AF_INET6;
      tmp_key.prefix.u.ipv6_addr = p.u.prefix6;
    }

  tmp_key.prefix_len = p.prefixlen;

  for (i = 0; i < route->n_nexthops; i++)
    {

      /*
       * Clear the next-hop specific entries in the 'zebra_route_key;
       * structure since we are populating the next-hop interface address
       * and next-hop interface conditionally.
       */
      memset(&(tmp_key.nexthop), 0, sizeof(struct ipv4v6_addr));
      memset(&(tmp_key.ifname), 0, sizeof(tmp_key.ifname));

      nexthop = route->nexthops[i];
      if (nexthop)
        {
          if (nexthop->ip_address)
	    {
              if (addr_family == AF_INET)
                inet_pton(AF_INET, nexthop->ip_address,
                          &tmp_key.nexthop.u.ipv4_addr);
	      else if (addr_family == AF_INET6)
                inet_pton(AF_INET6, nexthop->ip_address,
                          &tmp_key.nexthop.u.ipv6_addr);
            }

          if (nexthop->ports)
            strncpy(tmp_key.ifname, nexthop->ports[0]->name,
                    IF_NAMESIZE);

          VLOG_DBG("Hash insert prefix %s nexthop %s, interface %s",
                   route->prefix,
                   nexthop->ip_address ? nexthop->ip_address : "NONE",
                   tmp_key.ifname[0] ? tmp_key.ifname : "NONE");

          if (VLOG_IS_DBG_ENABLED())
            print_key(&tmp_key);

          add = hash_get(zebra_route_hash, &tmp_key,
                         zebra_route_hash_alloc);
          assert(add);
        }
    }
}

/* Free hash key memory */
static void
zebra_route_hash_free (struct zebra_route_key *p)
{
  XFREE (MTYPE_TMP, p);
}

/* Free hash table memory */
static void
zebra_route_hash_finish (void)
{
  hash_clean(zebra_route_hash, (void (*) (void *)) zebra_route_hash_free);
  hash_free(zebra_route_hash);
  zebra_route_hash = NULL;
}

/* Free link list data memory */
static void
zebra_route_list_free_data (struct zebra_route_del_data *data)
{
  XFREE (MTYPE_TMP, data);
}

/* Add delated route to list */
void
zebra_route_list_add_data (struct route_node *rnode, struct rib *rib_p,
                           struct nexthop *nhop)
{
  struct zebra_route_del_data *data;

  data = XCALLOC (MTYPE_TMP, sizeof (struct zebra_route_del_data));
  assert (data);

  data->rnode = rnode;
  data->rib = rib_p;
  data->nexthop = nhop;
  listnode_add(zebra_route_del_list, data);
}

/* Init link list and hash table */
static void
zebra_route_del_init (void)
{
  zebra_route_hash_init();
  zebra_route_del_list = list_new();
  zebra_route_del_list->del = (void (*) (void *)) zebra_route_list_free_data;
}

/* Run through the list of all OVSDB deleted routes and delete them
 * from the local RIB
 */
static void
zebra_route_del_process (void)
{
  struct listnode *node, *nnode;
  struct zebra_route_del_data *rdata;
  rib_table_info_t *info;
  struct prefix *pprefix;

  /* Loop through the local cache of deleted routes */
  for (ALL_LIST_ELEMENTS (zebra_route_del_list, node, nnode, rdata))
    {
      if (rdata->rnode && rdata->rib && rdata->nexthop)
        {
          info = rib_table_info (rdata->rnode->table);
	  /* Ignore broadcast and multicast routes */
          if (info->safi != SAFI_UNICAST)
            continue ;

          pprefix = &rdata->rnode->p;

          if (pprefix->family == AF_INET)
	    {
              if (rdata->rib->type == ZEBRA_ROUTE_STATIC)
                static_delete_ipv4_safi (info->safi, pprefix,
                                         (rdata->nexthop->ifname ?
                                          NULL : &rdata->nexthop->gate.ipv4),
                                         rdata->nexthop->ifname,
                                         rdata->rib->distance,
                                         info->vrf->id);
	      else
                rib_delete_ipv4(rdata->rib->type,              /*protocol*/
                                0,                             /*flags*/
                                (struct prefix_ipv4 *)pprefix, /*prefix*/
                                (rdata->nexthop->ifname ?
                                 NULL : &rdata->nexthop->gate.ipv4),/*gate*/
                                ifname2ifindex(rdata->nexthop->ifname),
                                                               /* ifindex */
                                0,                             /*vrf_id*/
                                info->safi                     /*safi*/
                                );
#ifdef HAVE_IPV6
	    }
	  else if (pprefix->family == AF_INET6)
	    {
              if (rdata->rib->type == ZEBRA_ROUTE_STATIC)
                static_delete_ipv6 (pprefix,
                                    (rdata->nexthop->ifname ?
                                               STATIC_IPV6_IFNAME :
                                               STATIC_IPV6_GATEWAY),
                                    &rdata->nexthop->gate.ipv6,
                                    rdata->nexthop->ifname,
                                    rdata->rib->distance,
                                    info->vrf->id);
	      else
                rib_delete_ipv6(rdata->rib->type,             /*protocol*/
                                0,                            /*flags*/
                                (struct prefix_ipv6 *)pprefix,/*prefix*/
                                (rdata->nexthop->ifname ?
                                 NULL : &rdata->nexthop->gate.ipv6),/*gate*/
                                ifname2ifindex(rdata->nexthop->ifname),
                                                              /* ifindex */
                                0,                            /*vrf_id*/
                                info->safi                    /*safi*/
                                );
#endif
	    }
	}
    }
}

/* Free hash and link list memory */
static void
zebra_route_del_finish (void)
{
  list_free(zebra_route_del_list);
  zebra_route_hash_finish();
}

/* Find routes not in ovsdb and add it to list.
  List is used to delete routes from system*/
static void
zebra_find_ovsdb_deleted_routes (afi_t afi, safi_t safi, u_int32_t id)
{
  struct route_table *table;
  struct route_node *rn;
  struct rib *rib;
  struct nexthop *nexthop;
  struct zebra_route_key rkey;
  char prefix_str[256];
  char nexthop_str[256];

  VLOG_DBG("Walk RIB table to find deleted routes");
  table = vrf_table (afi, safi, id);

  if (!table)
    return;

  /* Loop through all the route nodes in the local rib database */
  for (rn = route_top (table); rn; rn = route_next (rn))
    {
      if (!rn)
        continue;

      RNODE_FOREACH_RIB (rn, rib)
        {
	  /* Ignore any routes other than static. OSPF and BGP routes.
	   * Other protocols are not supported currently.*/
          if ((rib->type != ZEBRA_ROUTE_STATIC &&
              rib->type != ZEBRA_ROUTE_BGP &&
              rib->type != ZEBRA_ROUTE_OSPF) ||
              !rib->nexthop)
            continue;

	  /* Loop through the nexthops for each route and add it to
	   * the local cache for deletion
	   */
          for (nexthop = rib->nexthop; nexthop; nexthop = nexthop->next)
	    {
              memset(&rkey, 0, sizeof (struct zebra_route_key));
              memset(prefix_str, 0, sizeof(prefix_str));
              memset(nexthop_str, 0, sizeof(nexthop_str));

              if (afi == AFI_IP)
	        {
                  rkey.prefix.u.ipv4_addr = rn->p.u.prefix4;
                  rkey.prefix_len = rn->p.prefixlen;
                  if (nexthop->type == NEXTHOP_TYPE_IPV4)
		    {
                      rkey.nexthop.u.ipv4_addr = nexthop->gate.ipv4;
                      inet_ntop(AF_INET, &nexthop->gate.ipv4,
                                nexthop_str, sizeof(nexthop_str));
                    }
                }
	      else if (afi == AFI_IP6)
	        {
                  rkey.prefix.u.ipv6_addr = rn->p.u.prefix6;
                  rkey.prefix_len = rn->p.prefixlen;
                  if (nexthop->type == NEXTHOP_TYPE_IPV6)
		    {
                      rkey.nexthop.u.ipv6_addr = nexthop->gate.ipv6;
                      inet_ntop(AF_INET6, &nexthop->gate.ipv6,
                                nexthop_str, sizeof(nexthop_str));
                    }
                }

              if ((nexthop->type == NEXTHOP_TYPE_IFNAME) ||
                  (nexthop->type == NEXTHOP_TYPE_IPV4_IFNAME) ||
                  (nexthop->type == NEXTHOP_TYPE_IPV6_IFNAME))
                strncpy(rkey.ifname, nexthop->ifname, IF_NAMESIZE);

              if (VLOG_IS_DBG_ENABLED())
                print_key(&rkey);

              if (!hash_get(zebra_route_hash, &rkey, NULL))
	        {
                  zebra_route_list_add_data(rn, rib, nexthop);
                  prefix2str(&rn->p, prefix_str, sizeof(prefix_str));
                  VLOG_DBG("Delete route, prefix %s, nexthop %s, interface %s",
                           prefix_str[0] ? prefix_str : "NONE",
                           nexthop_str[0] ? nexthop_str : "NONE",
                           nexthop->ifname ? nexthop->ifname : "NONE");
                }
            }
        } /* RNODE_FOREACH_RIB */
    }
}

/* Find deleted route in ovsdb and remove from route table */
static void
zebra_route_delete (void)
{
  const struct ovsrec_route *route_row;

  zebra_route_del_init();
  /* Add ovsdb route and nexthop in hash */
  OVSREC_ROUTE_FOR_EACH (route_row, idl)
    {
        zebra_route_hash_add(route_row);
    }

  zebra_find_ovsdb_deleted_routes(AFI_IP, SAFI_UNICAST, 0);
  zebra_find_ovsdb_deleted_routes(AFI_IP6, SAFI_UNICAST, 0);

  zebra_route_del_process();
  zebra_route_del_finish();
}

/* Convert OVSDB protocol string to Zebra constants
 */
static unsigned int
ovsdb_proto_to_zebra_proto (char *from_protocol)
{
  if (!strcmp(from_protocol, OVSREC_ROUTE_FROM_CONNECTED))
    return ZEBRA_ROUTE_CONNECT;
  else if (!strcmp(from_protocol, OVSREC_ROUTE_FROM_STATIC))
    return ZEBRA_ROUTE_STATIC;
  else if (!strcmp(from_protocol, OVSREC_ROUTE_FROM_BGP))
    return ZEBRA_ROUTE_BGP;
  else if (!strcmp(from_protocol, OVSREC_ROUTE_FROM_OSPF))
    return ZEBRA_ROUTE_OSPF;
  else
    {
      VLOG_ERR("Unknown protocol. Conversion failed");
      return ZEBRA_ROUTE_MAX;
    }
  return ZEBRA_ROUTE_MAX;
}

/* Convert OVSDB sub-address family string to Zebra constants
 */
static unsigned int
ovsdb_safi_to_zebra_safi (char *safi_str)
{
  if (!strcmp(safi_str, OVSREC_ROUTE_SUB_ADDRESS_FAMILY_UNICAST))
    return SAFI_UNICAST;
  else if (!strcmp(safi_str, OVSREC_ROUTE_SUB_ADDRESS_FAMILY_MULTICAST))
    return SAFI_MULTICAST;
  else if (!strcmp(safi_str, OVSREC_ROUTE_SUB_ADDRESS_FAMILY_VPN))
    return SAFI_MPLS_VPN;
  else
    {
      VLOG_ERR("Unknown sub-address family. Conversion failed");
      return SAFI_MAX;
    }
  return SAFI_MAX;
}

/*
** Function to handle static route add/delete.
*/
static void
zebra_handle_static_route_change (const struct ovsrec_route *route)
{
  const struct ovsrec_nexthop *nexthop;
  struct prefix p;
  struct in_addr gate;
  struct in6_addr ipv6_gate;
  const char *ifname = NULL;
  u_char flag = 0;
  u_char distance;
  safi_t safi = 0;
  u_char type = 0;
  int ipv6_addr_type = 0;
  int ret;
  int next_hop_index;
  bool if_selected;

  VLOG_DBG("Rib prefix_str=%s", route->prefix);

  /*
   * Extract all the next-hop independent route parameters from the
   * OSVDB 'route' pointer.
   *
   * Convert the prefix/len
   */
  ret = str2prefix (route->prefix, &p);
  if (ret <= 0)
    {
      VLOG_ERR("Malformed Dest address=%s", route->prefix);
      return;
    }

  /*
   * Apply mask for given prefix.
   */
  apply_mask(&p);

  /*
   * Extract the route's address-family
   */
  if (route->address_family)
    {
      VLOG_DBG("address_family %s", route->address_family);
      if (strcmp(route->address_family,
                 OVSREC_ROUTE_ADDRESS_FAMILY_IPV6) == 0)
        ipv6_addr_type = true;
    }

  /*
   * Extract the route's sub-address-family
   */
  if (route->sub_address_family)
    {
      VLOG_DBG("Checking sub-address-family=%s", route->sub_address_family);
      if (strcmp(route->sub_address_family,
                 OVSREC_ROUTE_SUB_ADDRESS_FAMILY_UNICAST) == 0)
        safi = SAFI_UNICAST;
      else
        {
          VLOG_DBG("BAD! Not valid sub-address-family=%s",
                    route->sub_address_family);
          return;
        }
    }
  else
    safi = SAFI_UNICAST;

  /*
   * Get the route's administration distance.
   */
  if (route->distance != NULL)
    distance = route->distance[0];
  else
    distance = ZEBRA_STATIC_DISTANCE_DEFAULT;

  /*
   * Walk all the next-hops of the route and check if any of the next-hops
   * changed or got added.
   */
  VLOG_DBG("The total number of next-hops are: %d", route->n_nexthops);

  for (next_hop_index = 0; next_hop_index < route->n_nexthops;
       ++next_hop_index)
    {

      VLOG_DBG("Walking next-hop number %d\n", next_hop_index);

      ifname = NULL;
      memset(&gate, 0, sizeof(struct in_addr));
      memset(&ipv6_gate, 0, sizeof(struct in6_addr));

      /* Get Nexthop ip/interface */
      nexthop = route->nexthops[next_hop_index];

      if (nexthop == NULL)
        {
          VLOG_DBG("Null next hop");
          continue;
        }

      /*
       * If the next-hop in the route has changed or a new
       * next-hop has been added, then only look to program the
       * static next-hop in the kernel.
       */
      if (OVSREC_IDL_IS_ROW_INSERTED(nexthop, idl_seqno) ||
          OVSREC_IDL_IS_ROW_MODIFIED(nexthop, idl_seqno))
        {

          if (nexthop->ports)
            {
              ifname = nexthop->ports[0]->name;
              VLOG_DBG("Rib nexthop ifname=%s", ifname);
              if (ipv6_addr_type)
                type = STATIC_IPV6_IFNAME;
            }
          else if (nexthop->ip_address)
            {
              if (ipv6_addr_type)
                ret = inet_pton (AF_INET6, nexthop->ip_address, &ipv6_gate);
              else
                ret = inet_aton(nexthop->ip_address, &gate);

              if (ret == 1)
                {
                  VLOG_DBG("Rib nexthop ip=%s", nexthop->ip_address);
                  type = STATIC_IPV6_GATEWAY;
                }
              else
               {
                  VLOG_ERR("BAD! Rib nexthop ip=%s", nexthop->ip_address);
                  continue;
                }
            }
          else
            {
              VLOG_DBG("BAD! No nexthop ip or iface");
              continue;
            }

          if (ipv6_addr_type)
           {
#ifdef HAVE_IPV6
              static_add_ipv6(&p, type, &ipv6_gate, ifname, flag, distance, 0,
                              (void*) route);
#endif
            }
          else
            static_add_ipv4_safi(safi, &p, ifname ? NULL : &gate, ifname,
                                 flag, distance, 0, (void*) route);
        }
    }
}

/*
 * This function is called when a route is added/modified.
 * Determine the final action to take based on the current state
 * of the route
 */
static int
zebra_route_action_calculate (const struct ovsrec_route *route)
{
  /*
   * Logic:
   * If public route inserted, add the route
   * If public row is modified, add the route
   * If private route is inserted, ignore
   * If private row is modified, ignore
   */
  if (OVSREC_IDL_IS_ROW_MODIFIED(route, idl_seqno)
      || OVSREC_IDL_IS_ROW_INSERTED(route, idl_seqno))
    {
        return OVSDB_ROUTE_ADD;
    }
  return OVSDB_ROUTE_MIN;
}

/*
 * This function handles route update from routing protocols
 */
static void
zebra_handle_proto_route_change (const struct ovsrec_route *route,
                                 int from)
{
  int safi = ovsdb_safi_to_zebra_safi(route->sub_address_family);
  int ret;
  struct prefix p;
  bool is_ipv6 = false;

  VLOG_DBG("Route change for %s", route->prefix);
  ret = str2prefix (route->prefix, &p);
  if (ret <= 0)
    {
      VLOG_ERR("Malformed Dest address=%s", route->prefix);
      return;
    }
  apply_mask(&p);

  /*
   * Invoke internal zebra functions to add this route to RIB
   */
  if (!strcmp(route->address_family, OVSREC_ROUTE_ADDRESS_FAMILY_IPV4))
    {
      /* This is a IPv4 route update */
      switch (zebra_route_action_calculate(route))
        {
	case OVSDB_ROUTE_ADD:
	  VLOG_DBG("Got ipv4 add route");
	  zebra_add_route(is_ipv6, &p, from, safi, route);
	  break;
	case OVSDB_ROUTE_DELETE:
	  /* Delete is handled in process_delete */
	  break;
	default:
	  break;
	}

#ifdef HAVE_IPV6
    }
  else if (!strcmp(route->address_family, OVSREC_ROUTE_ADDRESS_FAMILY_IPV6))
    {
      is_ipv6 = true;
      /* This is a IPv6 route update */
      switch (zebra_route_action_calculate(route))
        {
	case OVSDB_ROUTE_ADD:
	  /* Handle v6 single or multiple nexthop routes. */
	  VLOG_DBG("Got ipv6 add route");
	  zebra_add_route(is_ipv6, &p, from, safi, route);
	  break;
	case OVSDB_ROUTE_DELETE:
	  /* Delete is handled in process_delete */
	  break;
	default:
	  break;
	}
#endif
    }
}

/*
 * A route has been modified or added. Update the local RIB structures
 * accordingly.
 */
static void
zebra_handle_route_change (const struct ovsrec_route *route)
{
  int from_protocol = ovsdb_proto_to_zebra_proto(route->from);
  /*
   * OVSDB stores the almost everything as a string. Zebra uses integers.
   * If we convert the string to integer initially, we can avoid multiple
   * string operations further.
   */
  switch (from_protocol)
    {
    case ZEBRA_ROUTE_CONNECT:
      VLOG_DBG("Adding a connected route for prefix %s\n",route->prefix);
      /* This is a directly connected route */
      /* TODO: Might have to delete this case */
      break;
    case ZEBRA_ROUTE_STATIC:
      VLOG_DBG("Adding a static route for prefix %s\n",route->prefix);
      /* This is a static route */
      zebra_handle_static_route_change(route);
      break;
    case ZEBRA_ROUTE_BGP:
      VLOG_DBG("Adding a Protocol route for prefix %s protocol %s\n",
                route->prefix, route->from);
      /* This is a protocol route */
      zebra_handle_proto_route_change(route, from_protocol);
      break;
   case ZEBRA_ROUTE_OSPF:
      VLOG_DBG("Adding a Protocol route for prefix %s protocol %s\n",
                route->prefix, route->from);
      /* This is a protocol route */
      zebra_handle_proto_route_change(route, from_protocol);
      break;
    case ZEBRA_ROUTE_MAX:
    default:
      VLOG_ERR("Unknown protocol");
      return;
    }
}

/* route add/delete in ovsdb */
static void
zebra_apply_route_changes (void)
{
  const struct ovsrec_route *route_first;
  const struct ovsrec_route *route_row;
  const struct ovsrec_nexthop *nh_first;
  const struct ovsrec_nexthop *nh_row;

  route_first = ovsrec_route_first(idl);
  nh_first = ovsrec_nexthop_first(idl);
  if (route_first == NULL)
    {
      VLOG_DBG("No rows in ROUTE table");
      /* Possible last row gets deleted */
      zebra_route_delete();
      return;
    }

  /*
   * If debug logging is enabled, then dump the OVSDB route table.
   */
  if (VLOG_IS_DBG_ENABLED())
    zebra_dump_ovsdb_route_table();

  /*
   * Check if anything changed in the route table and the next-hop table.
   * If nothing changed then return from this function.
   */
  if ( (!OVSREC_IDL_ANY_TABLE_ROWS_MODIFIED(route_first, idl_seqno)) &&
     (!OVSREC_IDL_ANY_TABLE_ROWS_DELETED(route_first, idl_seqno))  &&
     (!OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(route_first, idl_seqno)) &&
     (!OVSREC_IDL_ANY_TABLE_ROWS_MODIFIED(nh_first, idl_seqno)) &&
     (!OVSREC_IDL_ANY_TABLE_ROWS_DELETED(nh_first, idl_seqno))  &&
     (!OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(nh_first, idl_seqno)))
    {
      VLOG_DBG("No modification in ROUTE table");
      return;
    }

  if ( (OVSREC_IDL_ANY_TABLE_ROWS_MODIFIED(route_first, idl_seqno)) ||
       (OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(route_first, idl_seqno)) ||
        (OVSREC_IDL_ANY_TABLE_ROWS_MODIFIED(nh_first, idl_seqno)) ||
       (OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(nh_first, idl_seqno)) )
    {
      VLOG_DBG("Some modification or inserts in ROUTE table");

      OVSREC_ROUTE_FOR_EACH (route_row, idl)
        {
          nh_row = route_row->nexthops[0];
          if (nh_row == NULL)
            {
              VLOG_DBG("Null next hop");
              continue;
            }

          if ( (OVSREC_IDL_IS_ROW_INSERTED(route_row, idl_seqno)) ||
               (OVSREC_IDL_IS_ROW_MODIFIED(route_row, idl_seqno)) ||
               (is_route_nh_rows_modified(route_row)) )
            {
              VLOG_DBG("Row modification or inserts in ROUTE table "
                       "for route %s\n", route_row->prefix);
              zebra_handle_route_change(route_row);
            }
        }
    }

  if ( (OVSREC_IDL_ANY_TABLE_ROWS_DELETED(route_first, idl_seqno) ) ||
       (is_rib_nh_rows_deleted(route_first)) )
    {
      VLOG_DBG("Deletes in RIB table");
      zebra_route_delete();
    }
}

/*
 * This function handles the interface UP/DOWN events. This function
 * eventually marks the next-hops/routes as selected or unselected.
 */
static void
zebra_handle_interface_admin_state_changes (void)
{
  const struct ovsrec_interface *interface_row = NULL;
  bool int_up = false;
  struct smap user_config;
  const char *admin_status;

  zebra_init_if_port_active_state_changed();

  /*
   * Check which interface admin state column got
   * modified.
   */
  if (OVSREC_IDL_IS_COLUMN_MODIFIED(
             ovsrec_interface_col_admin_state, idl_seqno))
    {
      OVSREC_INTERFACE_FOR_EACH (interface_row, idl)
        {
          /*
           * Check if the interface row changed.
           */
          if (OVSREC_IDL_IS_ROW_MODIFIED(interface_row, idl_seqno))
            {
              VLOG_DBG("Got a interface admin state modified for "
                       "interface %s to state %s\n",
                       interface_row->name,
                       interface_row->admin_state);

              /*
               * Update the L3 port cache with the interface's admin
               * state.
               */
              zebra_update_port_active_state(interface_row);
            }
        }
    }

  /*
   * If some L3 port became active or iactive due to interface unshut or
   * shut, then walk all zebra routes and mark the appropriate
   * next-hops/routes as selected or unselected in the OVSDB.
   */
  if (zebra_get_if_port_active_state_changed())
    {
      zebra_find_routes_with_deleted_ports(
                                        AFI_IP, SAFI_UNICAST, 0,
                                        ZEBRA_L3_PORT_ACTIVE_STATE_CHN_OPTION);
      zebra_find_routes_with_deleted_ports(
                                        AFI_IP6, SAFI_UNICAST, 0,
                                        ZEBRA_L3_PORT_ACTIVE_STATE_CHN_OPTION);
    }

  zebra_cleanup_if_port_active_state_changed();
}

/*
 * This function handles the port add/delete events. THis function
 * eventually deletes the next-hops or routes if the resolving
 * interface is deleted or chnaged to L2.
 */
static void
zebra_handle_port_add_delete_changes (void)
{
  const struct ovsrec_port *first_port_row = NULL;

  first_port_row = ovsrec_port_first(idl);
  if (!first_port_row)
    {
      VLOG_DBG("There are no port rows in the port table.");

      /*
       * TODO: Cleanup all static routes created by zebra in kernel
       */
      return;
    }

  zebra_init_if_port_updated_or_changed();

  /*
   * Initialize the delete list
   */
  zebra_route_del_list = list_new();
  zebra_route_del_list->del = (void (*) (void *))
                                      zebra_route_list_free_data;

  /*
   * Walk through all the port in the IDL and update the L3 port
   * hash.
   */
  OVSREC_PORT_FOR_EACH (first_port_row, idl)
    {
      if (first_port_row)
        {
          VLOG_DBG("Got a port name %s (%s)(%s) (%s)\n",
                   first_port_row->name,
                   OVSREC_IDL_IS_ROW_INSERTED(
                            first_port_row, idl_seqno) ? "I" : "",
                   OVSREC_IDL_IS_ROW_MODIFIED(
                            first_port_row, idl_seqno) ? "M" : "",
                   zebra_if_ovsrec_port_is_l3(first_port_row) ?
                                                       "L3" : "L2");

          /*
           * Update the hash bucket for maintaining the configured L3
           * ports.
           */
          zebra_add_or_update_cached_l3_ports_hash(first_port_row);
        }
    }

  /*
   * Find out which ports got deleted from the L3 port hash.
   */
  zebra_remove_deleted_cached_l3_ports_hash();

  /*
   * If debug logging is enabled, then dump the OVSDB route table.
   */
  if (VLOG_IS_DBG_ENABLED())
    {
      zebra_l3_port_walk_cache_and_print(
                                  &zebra_cached_l3_ports, true);
      zebra_l3_port_walk_cache_and_print(
                     &zebra_updated_or_changed_l3_ports, false);
    }

  /*
   * Walk the zebra route table and find which nexthops need to be
   * deleted from the kernel and OVSDB.
   */
  zebra_find_routes_with_deleted_ports(AFI_IP, SAFI_UNICAST, 0,
                                       ZEBRA_L3_PORT_DELETE_UPDATE_OPTION);
  zebra_find_routes_with_deleted_ports(AFI_IP6, SAFI_UNICAST, 0,
                                       ZEBRA_L3_PORT_DELETE_UPDATE_OPTION);

  /*
   * Delte the next-hops which have been marked for deletion from
   * he kernel and the OVSDB.
   */
  zebra_route_del_process();
  list_free(zebra_route_del_list);

  zebra_cleanup_if_port_updated_or_changed();
}

/* Check if any changes are there to the idl and update
 * the local structures accordingly.
 */
static void
zebra_reconfigure (struct ovsdb_idl *idl)
{
  unsigned int new_idl_seqno = ovsdb_idl_get_seqno(idl);
  COVERAGE_INC(zebra_ovsdb_cnt);

  if (new_idl_seqno == idl_seqno)
    {
      VLOG_DBG("No config change for zebra in ovs\n");
      return;
    }

  /* Create txn for any IDL updates */
  zebra_create_txn();

  /* Apply all ovsdb notifications */
  zebra_apply_route_changes();
  zebra_handle_interface_admin_state_changes();
  zebra_handle_port_add_delete_changes();

  /* Submit any modifications in IDl to DB */
  zebra_finish_txn();

  /* update the seq. number */
  idl_seqno = new_idl_seqno;
}

/* Wrapper function that checks for idl updates and reconfigures the daemon
 */
static void
zebra_ovs_run (void)
{
  ovsdb_idl_run(idl);
  unixctl_server_run(appctl);
#ifdef VRF_ENABLE
  /* Check if zebra_vrf is set; */
  if (!zebra_vrf || !strlen(zebra_vrf))
    {
      zebra_vrf = zebra_get_my_vrf_name();
      VLOG_DBG("zebra_ovs_run for vrf %s", zebra_vrf);
      if (!zebra_vrf)
        {
          VLOG_ERR("Can't retrieve vrf name");
          return;
        }
    }
#endif

  if (ovsdb_idl_is_lock_contended(idl))
    {
      static struct vlog_rate_limit rl = VLOG_RATE_LIMIT_INIT(1, 1);

      VLOG_ERR_RL(&rl, "another zebra process is running, "
                  "disabling this process until it goes away");
      return;
    }
  else if (!ovsdb_idl_has_lock(idl))
    return;

  zebra_chk_for_system_configured();

  if (system_configured)
    {
      zebra_reconfigure(idl);

      daemonize_complete();
      vlog_enable_async();
      VLOG_INFO_ONCE("%s (OpenSwitch zebra) %s", program_name, VERSION);
    }
}

static void
zebra_ovs_wait (void)
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
zovs_read_cb (struct thread *thread)
{
  zebra_ovsdb_t *zovs_g;
  if (!thread)
    {
      VLOG_ERR("NULL thread in read cb function\n");
      return -1;
    }
  zovs_g = THREAD_ARG(thread);
  if (!zovs_g)
    {
      VLOG_ERR("NULL args in read cb function\n");
      return -1;
    }

  zovs_g->read_cb_count++;

  zebra_ovs_clear_fds();
  zebra_ovs_run();
  zebra_ovs_wait();

  if (0 != zebra_ovspoll_enqueue(zovs_g))
    {
      /*
       * Could not enqueue the events.
       * Retry in 1 sec
       */
      thread_add_timer(zovs_g->master,
                       zovs_read_cb, zovs_g, 1);
    }
  return 1;
}

/* Add the list of OVS poll fd to the master thread of the daemon
 */
static int
zebra_ovspoll_enqueue (zebra_ovsdb_t *zovs_g)
{
  struct poll_loop *loop = poll_loop();
  struct poll_node *node;
  long int timeout;
  int retval = -1;

  /* Populate with all the fds events. */
  HMAP_FOR_EACH (node, hmap_node, &loop->poll_nodes)
    {
      thread_add_read(zovs_g->master,
                      zovs_read_cb,
                      zovs_g, node->pollfd.fd);
      /*
       * If we successfully connected to OVS return 0.
       * Else return -1 so that we try to reconnect.
       * */
      retval = 0;
    }

  /* Populate the timeout event */
  timeout = loop->timeout_when - time_msec();
  if (timeout > 0 && loop->timeout_when > 0 &&
      loop->timeout_when < LLONG_MAX)
    {
      /* Convert msec to sec */
      timeout = (timeout + 999)/1000;

      thread_add_timer(zovs_g->master,
		       zovs_read_cb, zovs_g,
		       timeout);
    }

  return retval;
}

/* Initialize and integrate the ovs poll loop with the daemon */
void
zebra_ovsdb_init_poll_loop (struct zebra_t *zebrad)
{
  if (!glob_zebra_ovs.enabled)
    {
      VLOG_ERR("OVS not enabled for zebra. Return\n");
      return;
    }
  glob_zebra_ovs.master = zebrad->master;

  zebra_ovs_clear_fds();
  zebra_ovs_run();
  zebra_ovs_wait();
  zebra_ovspoll_enqueue(&glob_zebra_ovs);
}

static void
ovsdb_exit (void)
{
  ovsdb_idl_destroy(idl);
}

/* When the daemon is ready to shut, delete the idl cache
 * This happens with the ovs-appctl exit command.
 */
void
zebra_ovsdb_exit (void)
{
  #ifdef VRF_ENABLE
  free(zebra_vrf);
  zebra_vrf = NULL;
  #endif
  ovsdb_exit();
}

/*
 * This is a helper function which deletes the OVSDB next-hop entries from the
 * route. The next-hops which are marked as true in bool array will be deleted
 * from OVSDB. If the number of next-hops for the route becomes 0, then the route
 * itself is deleted from the OVSDB.
 */
static void
zebra_route_delete_nexthops (struct ovsrec_route *route, bool *nexthop_decision,
                             size_t number_next_hops)
{
  struct ovsrec_nexthop **nexthops = NULL;
  size_t i, n;

  if (!nexthop_decision)
    {
      VLOG_ERR("The next-hop decision array in NULL");
      return;
    }

  if (route->n_nexthops != number_next_hops)
    {
        VLOG_ERR("The number of route nexthops %u is not same as decision"
                 " array's length %u", route->n_nexthops, number_next_hops);
        return;
    }

  nexthops = xmalloc(sizeof(struct ovsrec_nexthop *) * (route->n_nexthops));
  for (i = n = 0; i < route->n_nexthops; i++)
    {
        if (!nexthop_decision[i])
          nexthops[n++] = route->nexthops[i];
    }

  ovsrec_route_set_nexthops(route, nexthops, n);
  zebra_txn_updates = true;

  /*
   * If the route does not have any next-hops left, then delete this route.
   */
  if (n == 0)
    {
      VLOG_DBG("Need to delete the OVSDB route for prefix %s", route->prefix);
      ovsrec_route_delete(route);
    }

  free(nexthops);
}


/*
 * This function takes a zebra rib entry and the next-hop port and deletes the
 * corresponding next-hop port from OVSDB.
 */
void zebra_delete_route_nexthop_addr_from_db (struct rib *route,
                                              char* nexthop_str)
{
  struct ovsrec_route *route_row = NULL;
  struct ovsrec_nexthop *nh_row;
  int port_index;
  int next_hop_index;
  bool *found_nexthop_addr;

  if (!route || !nexthop_str)
    {
      VLOG_ERR("The route's rib entry or next-hop address in null");
      return;
    }

  if (route && (route->ovsdb_route_row_ptr))
    {
      route_row = (struct ovsrec_route *)(route->ovsdb_route_row_ptr);
      #ifdef VRF_ENABLE
      if (!(zebra_is_route_in_my_vrf(route_row)))
        return;
      #endif
      VLOG_DBG("Cached OVSDB Route Entry: Prefix %s family %s "
               "from %s priv %p", route_row->prefix,
               route_row->address_family, route_row->from,
               route_row->protocol_private);

      VLOG_DBG("Walk route next-hops to find the next-hop "
               " corresponding to the next-hop address %s",
               nexthop_str);

      /*
       * This bool array stores the decision as to which next-hop rows
       * need to be deleted. If a next-hop need to be deleted, then the
       * bool array entry will be set to true.
       */
      found_nexthop_addr =
              (bool *)xmalloc(sizeof(bool) * (route_row->n_nexthops));
      memset(found_nexthop_addr, 0, sizeof(bool) * (route_row->n_nexthops));

      /*
       * Walk all next-hops to find which next-hop address needs to
       * be deleted from OVSDB.
       */
      for (next_hop_index = 0; next_hop_index < route_row->n_nexthops;
           ++next_hop_index)
        {
          nh_row = route_row->nexthops[next_hop_index];
          VLOG_DBG("Inspecting the next-hop with address %s",
                    nh_row->ip_address);

          if (!(nh_row->ip_address))
            {
              continue;
            }

          /*
           * Check if the nexthop_str is same as the next-hop IP
           * address.
           */
          if (strcmp(nexthop_str, nh_row->ip_address) == 0)
            {
              VLOG_DBG("Found the nexthop match");
              found_nexthop_addr[next_hop_index] = true;
            }
        }

      /*
       * Delete the next-hop rows which are marked as true in the
       * bool array.
       */
      zebra_route_delete_nexthops(route_row, found_nexthop_addr,
                                  route_row->n_nexthops);

      /*
       * Free the allocated bool array.
       */
      free(found_nexthop_addr);
    }
  else
    {
      VLOG_DBG("Cannot delete the next-hop address from OVSDB");
    }
}

/*
 * This function takes a zebra rib entry and the next-hop port and deletes
 * the corresponding next-hop port from OVSDB.
 */
void zebra_delete_route_nexthop_port_from_db (struct rib *route,
                                              char* port_name)
{
  struct ovsrec_route *route_row = NULL;
  struct ovsrec_nexthop *nh_row;
  int port_index;
  int next_hop_index;
  bool* found_port = NULL;

  if (!route || !port_name)
    {
      VLOG_ERR("The route's rib entry or port name in null");
      return;
    }

  if (route && (route->ovsdb_route_row_ptr))
    {
      route_row = (struct ovsrec_route *)(route->ovsdb_route_row_ptr);
      #ifdef VRF_ENABLE
      if (!(zebra_is_route_in_my_vrf(route_row)))
        return;
      #endif
      VLOG_DBG("Cached OVSDB Route Entry: Prefix %s family %s "
               "from %s priv %p", route_row->prefix,
               route_row->address_family, route_row->from,
               route_row->protocol_private);

      VLOG_DBG("Finding the nexthop row corresponding to the port %s",
               port_name);

      /*
       * This bool array stores the decision as to which next-hop rows
       * need to be deleted. If a next-hop need to be deleted, then the
       * bool array entry will be set to true.
       */
      found_port = (bool *)xmalloc(sizeof(bool) * (route_row->n_nexthops));
      memset(found_port, 0, sizeof(bool) * (route_row->n_nexthops));

      /*
       * Walk all next-hops to find which next-hop port needs to
       * be deleted from OVSDB.
       */
      for (next_hop_index = 0; next_hop_index < route_row->n_nexthops;
           ++next_hop_index)
        {
          nh_row = route_row->nexthops[next_hop_index];

          /*
           * If the nexthop does not have a valid ip address or
           * port, then cleanup this port.
           */
          if (!(nh_row->ip_address) && !(nh_row->n_ports))
            {
              VLOG_DBG("The next-hop IP and port are NULL. "
                        "Delete this port from OVSDB");
              found_port[next_hop_index] = true;
            }
          else if (nh_row->ports && nh_row->ports[0]
                       && nh_row->ports[0]->name)
            {
              /*
               * Check the first port in the port list to see if the port_name
               * is the same as the first port entry.
               */
              VLOG_DBG("Inspecting port %s to see if same as %s",
                        nh_row->ports[0]->name, port_name);

              if (strcmp(nh_row->ports[0]->name, port_name) == 0)
                found_port[next_hop_index] = true;
            }
        }

      /*
       * Delete the next-hop rows which are marked as true in the
       * bool array.
       */
      zebra_route_delete_nexthops(route_row, found_port,
                                  route_row->n_nexthops);

      /*
       * Free the allocated bool array.
       */
      free(found_port);
    }
  else
    {
      VLOG_DBG("Cannot delete the next-hop port from OVSDB");
    }
}

/* Update the selected column in the route row in OVSDB
 */
static int
zebra_ovs_update_selected_route (const struct ovsrec_route *ovs_route,
                                 bool *selected)
{
  if (ovs_route)
    {
      /*
       * Found the route entry. Update the selected column.
       * ECMP: Update only if it is different.
       */
      VLOG_DBG("Updating selected flag for route %s", ovs_route->prefix);
      if ( (ovs_route->selected != NULL) &&
          (ovs_route->selected[0] == *selected) )
        {
          VLOG_DBG("No change in selected flag previous %s and new %s",
                    ovs_route->selected[0] ? "true" : "false",
                    *selected ? "true" : "false");
          return 0;
        }

      /*
       * Update the selected bit, and mark it to commit into DB.
       */
      ovsrec_route_set_selected(ovs_route, selected, 1);
      zebra_txn_updates = true;
      VLOG_DBG("Route update successful");

    }
  return 0;
}

/*
 * When zebra is ready to update the kernel with the selected route,
 * update the DB with the same information. This function will take care
 * of updating the DB
 */
static int
zebra_update_selected_route_to_db (struct route_node *rn, struct rib *route,
                                   int action)
{
  char prefix_str[256];
  const struct ovsrec_route *ovs_route = NULL;
  bool selected = (action == ZEBRA_RT_INSTALL) ? true:false;
  struct prefix *p = NULL;
  rib_table_info_t *info = NULL;

  /*
   * Fetch the rib entry from the DB and update the selected field based
   * on action:
   * action == ZEBRA_RT_INSTALL => selected = 1
   * action == ZEBRA_RT_UNINSTALL => selected = 0
   *
   * If the 'route' has a valid 'ovsdb_route_row_ptr' pointer,
   * then reference the 'ovsrec_route' structure directly from
   * 'ovsdb_route_row_ptr' pointer. Otherwise iterate through the
   * OVSDB route to find out the relevant 'ovsrec_route' structure. We
   * need to investigate more on how to set the route selected bit
   * in cases when zebra adds/update/deletes the route from the kernel.
   */
  if (route->ovsdb_route_row_ptr)
    {
      ovs_route = (struct ovsrec_route *)(route->ovsdb_route_row_ptr);

      #ifdef VRF_ENABLE
      if (!(zebra_is_route_in_my_vrf(ovs_route)))
        return 0;
      #endif

      VLOG_DBG("Cached OVSDB Route Entry: Prefix %s family %s "
               "from %s priv %p for setting selected to %s", ovs_route->prefix,
               ovs_route->address_family, ovs_route->from,
               ovs_route->protocol_private,
               selected ? "true" : "false");
    }
  else
    {
      p = &rn->p;
      info = rib_table_info(rn->table);
      memset(prefix_str, 0, sizeof(prefix_str));
      prefix2str(p, prefix_str, sizeof(prefix_str));

      VLOG_DBG("Prefix %s Family %d\n",prefix_str, PREFIX_FAMILY(p));

      switch (PREFIX_FAMILY (p))
        {
	case AF_INET:

	  VLOG_DBG("Walk the OVSDB route DB to find the relevant row for"
		   " prefix %s\n", prefix_str);

	  OVSREC_ROUTE_FOR_EACH (ovs_route, idl)
	    {
              #ifdef VRF_ENABLE
              if (!(zebra_is_route_in_my_vrf(ovs_route)))
                continue;
              #endif

	      VLOG_DBG("DB Entry: Prefix %s family %s from %s",
		       ovs_route->prefix, ovs_route->address_family,
		       ovs_route->from);

	      if (!strcmp(ovs_route->address_family,
			  OVSREC_ROUTE_ADDRESS_FAMILY_IPV4))
		{
		  if (!strcmp(ovs_route->prefix, prefix_str))
		    {
		      if (route->type ==
			  ovsdb_proto_to_zebra_proto(ovs_route->from))
			{
			  if (info->safi ==
			      ovsdb_safi_to_zebra_safi(
					ovs_route->sub_address_family))
			    break;
			}
		    }
		}
	    }
	  break;
#ifdef HAVE_IPV6
	case AF_INET6:

          VLOG_DBG("Walk the OVSDB route DB to find the relevant row for"
		   " prefix %s\n", prefix_str);

          OVSREC_ROUTE_FOR_EACH (ovs_route, idl)
	    {
              #ifdef VRF_ENABLE
              if (!(zebra_is_route_in_my_vrf(ovs_route)))
                continue;
              #endif

	      VLOG_DBG("DB Entry: Prefix %s family %s from %s",
		       ovs_route->prefix, ovs_route->address_family,
		       ovs_route->from);

	      if (!strcmp(ovs_route->address_family,
				  OVSREC_ROUTE_ADDRESS_FAMILY_IPV6))
		{
		  if (!strcmp(ovs_route->prefix, prefix_str))
		    {
		      if (route->type ==
			      ovsdb_proto_to_zebra_proto(ovs_route->from))
			{
			  if (info->safi ==
			      ovsdb_safi_to_zebra_safi(
					ovs_route->sub_address_family))
			    break;
			}
		    }
		}
	    }
          break;
#endif
          default:
          /* Unsupported protocol family! */
          VLOG_ERR("Unsupported protocol in route update");
          return 0;
	}
    }

  if (ovs_route)
    {
        VLOG_DBG("Updating the selected flag for the non-private routes. "
                 "Setting selected %s for prefix %s",
                 selected ? "true":"false", ovs_route->prefix);
        zebra_ovs_update_selected_route(ovs_route, &selected);
    }
  return 0;
}

/*
 * This function takes a zebra rn, zebra rib entry, the next-hop
 * port or IP/IPv6 address and the selected bit. The function then
 * looks for the corresponding next-hop row for the port or next-hop
 * IP/IPv6 addresses  in the OVSDB and marks the selected bit for
 * OVSDB next-hop row as true or false depending on the selected value.
 *
 * If all the next-hops are marked as unselected in the OVSDB, then the
 * OSVDB route's selected bit is also marked as false. If a next-hop is
 * marked as selected and this is the first next-hop for the route to be
 * marked selected, then the route's selected bit is also marked as true.
 */
void zebra_update_selected_nh (struct route_node *rn, struct rib *route,
                               char* port_name, char* nh_addr, int selected)
{
  struct ovsrec_route *route_row = NULL;
  struct ovsrec_nexthop *nh_row;
  struct ovsrec_nexthop *cand_nh_row;
  int next_hop_index;
  bool is_selected = (ZEBRA_NH_INSTALL == selected) ? true : false;
  int number_of_selected_nh = 0;

  /*
   * If the zebra route node rib entry are NULL and both of port_name
   * and nh_addr are NULL, then return from the function.
   */
  if (!rn || !route || (!port_name && !nh_addr))
    {
      VLOG_ERR("The route node or route's rib entry in null");
      return;
    }

  if (route->ovsdb_route_row_ptr)
    {
      route_row = (struct ovsrec_route *)(route->ovsdb_route_row_ptr);
      #ifdef VRF_ENABLE
      if (!(zebra_is_route_in_my_vrf(route_row)))
        return;
      #endif
      VLOG_DBG("Cached OVSDB Route Entry: Prefix %s family %s "
               "from %s priv %p for setting %s to %s", route_row->prefix,
               route_row->address_family, route_row->from,
               route_row->protocol_private, port_name ? port_name : nh_addr,
               is_selected ? "true" : "false");


      cand_nh_row = NULL; /* reference to the candidate next-hop row which
                             matches the port or next-hop address. */
      number_of_selected_nh = 0; /* counter to keep track of the number of
                                    next-hops whose selected bit is set to
                                    true. */

      /*
       * Walk all next-hops to find which next-hop needs to
       * selected or unselected in OVSDB.
       */
      for (next_hop_index = 0; next_hop_index < route_row->n_nexthops;
           ++next_hop_index)
        {
          nh_row = route_row->nexthops[next_hop_index];

          /*
           * Check if the port_name matches the next-hop port.
           */
          if (port_name && nh_row->ports && nh_row->ports[0]
              && nh_row->ports[0]->name)
            {
              if (strcmp(nh_row->ports[0]->name, port_name) == 0)
                {
                  VLOG_DBG("Found a match with the nh port %s",
                            nh_row->ports[0]->name);
                  cand_nh_row = nh_row;
                }
            }

          /*
           * Check if the nh_addr matches the next-hop IP/IPv6 address.
           */
          if (nh_addr && nh_row->ip_address)
            {
              if (strcmp(nh_row->ip_address, nh_addr) == 0)
                {
                  VLOG_DBG("Found a match with the nh address %s",
                            nh_row->ip_address);
                  cand_nh_row = nh_row;
                }
            }

          /*
           * If the selected field for the next-hop is set to true
           * increment the counter number_of_selected_nh.
           */
          if (((!cand_nh_row) || (cand_nh_row != nh_row)) &&
              (!(nh_row->selected) || (nh_row->selected[0] == true)))
            {
              ++number_of_selected_nh;
            }
        }

      if (cand_nh_row)
        {
          if (!(cand_nh_row->selected))
            {
              /*
               * If the selected pointer is null, update the selected
               * with the is_selected boolean.
               */
              VLOG_DBG("Changing the next-hop selected flag from %s to %s",
                       !cand_nh_row->selected ? "true" : "false",
                       is_selected ? "true" : "false");
              ovsrec_nexthop_set_selected(cand_nh_row, &is_selected, 1);
              zebra_txn_updates = true;
            }
          else
            {
              /*
               * If the selected pointer is not null, update the selected
               * with the is_selected boolean if the selected value and the
               * is_selected values are different.
               */
              if (cand_nh_row->selected[0] != is_selected)
                {
                  VLOG_DBG("Changing the next-hop selected flag from %s to %s",
                           cand_nh_row->selected[0] ? "true" : "false",
                           is_selected ? "true" : "false");
                  ovsrec_nexthop_set_selected(cand_nh_row, &is_selected, 1);
                  zebra_txn_updates = true;
                }
            }

          if (is_selected)
            {
              /*
               * If at least one next-hop is selected, then mark the
               * route as selected. if 'number_of_selected_nh' is zero,
               * we have at least one next-hop that is selected.
               */
              if (!number_of_selected_nh)
                {
                  VLOG_DBG("The route has at least one active next-hop. "
                           "Set the selected bit on the route.");
                  zebra_update_selected_route_to_db(rn, route,
                                                    ZEBRA_RT_INSTALL);
                }
            }
          else
            {
              /*
               * If no next-hop is selected, then mark the route as
               * unselected. If 'number_of_selected_nh' is one, then
               * we should mark the route as unselected as no next-hops
               * that are selected.
               */
              if (!number_of_selected_nh)
                {
                  VLOG_DBG("The route has no active next-hops. "
                           "Unset the selected bit on the route.");
                  zebra_update_selected_route_to_db(rn, route,
                                                    ZEBRA_RT_UNINSTALL);
                }
            }
        }
    }
  else
    {
      VLOG_DBG("Cannot update the selected flag for the next-hop");
    }
}

/*
 * This function sets the selected flag on the route and next-hops
 * based on the 'action' variable. The OVSDB route entry is references
 * from the 'rib' data structure from zebra. This function should not
 * be called in cases when there are route entry deletions in the
 * OVSDB route table. The OVSDB route table entry is garbage collected
 * and hence the related pointer should not be referenced.
 */
void
zebra_update_selected_route_nexthops_to_db (struct route_node *rn,
                                            struct rib *route,
                                            int action)
{
  char prefix_str[256];
  const struct ovsrec_route *ovs_route = NULL;
  bool selected = (action == ZEBRA_NH_INSTALL) ? true:false;
  struct prefix *p = NULL;
  rib_table_info_t *info = NULL;
  struct nexthop *nexthop;
  char nexthop_str[256];

  if (!rn)
    {
      VLOG_DBG("The route node is NULL");
      return;
    }

  if (!route)
    {
      VLOG_DBG("The route rib entry is NULL");
      return;
    }

  p = &rn->p;
  info = rib_table_info(rn->table);
  memset(prefix_str, 0, sizeof(prefix_str));
  prefix2str(p, prefix_str, sizeof(prefix_str));

  VLOG_DBG("Prefix %s Family %d selected = %s\n",prefix_str, PREFIX_FAMILY(p),
           selected ? "true":"false");

  switch (PREFIX_FAMILY (p))
    {
      /*
       * Case when the address family is IPv4.
       */
	  case AF_INET:

        /*
         * Walk all the next-hops of the 'rib' entry and set/un-set
         * the selected flag on the next-hop.
         */
        nexthop = route->nexthop;
        while (nexthop)
          {
            memset(nexthop_str, 0, sizeof(nexthop_str));
            switch (nexthop->type)
              {
                /*
                 * Case when the next-hop is of IP address.
                 */
                case NEXTHOP_TYPE_IPV4_IFINDEX:
                case NEXTHOP_TYPE_IPV4:
                  if (inet_ntop(AF_INET, &nexthop->gate.ipv4,
                                nexthop_str, sizeof(nexthop_str)))
                    {
                      /*
                       * If the next-hop should be marked as selected, then
                       * check whether the next-hop address is active or not.
                       */
                      if (action == ZEBRA_NH_INSTALL)
                        {
                          /*
                           * If the next-hop address is not active, then mark
                           * the next-hop as unselected in OVSDB. If the next-hop
                           * address is active, then mark the next-hop and route
                           * selected.
                           */
                          if (!zebra_nh_addr_active_in_cached_l3_ports_hash(
                                                         nexthop_str, AFI_IP))
                            {
                              zebra_update_selected_nh(rn, route, NULL, nexthop_str,
                                                       ZEBRA_NH_UNINSTALL);
                            }
                          else
                            {
                              zebra_update_selected_nh(rn, route, NULL, nexthop_str,
                                                       ZEBRA_NH_INSTALL);
                            }
                        }
                      else
                        {
                          /*
                           * In case, the next-hop is to be marked as unselected,
                           * then mark the next-hop and route as unselected in
                           * OVSDB roue table.
                           */
                          zebra_update_selected_nh(rn, route, NULL,
                                                 nexthop_str, ZEBRA_NH_UNINSTALL);
                        }
                    }
                  break;

                /*
                 * Case when the next-hop is of port type.
                 */
                case NEXTHOP_TYPE_IFNAME:

                  /*
                   * If the next-hop should be marked as selected, then
                   * check whether the next-hop port is active or not.
                   */
                  if (action == ZEBRA_NH_INSTALL)
                    {
                      /*
                       * If the next-hop port is not active, then mark
                       * the next-hop as unselected in OVSDB. If the next-hop
                       * port is active, then mark the next-hop and route
                       * selected.
                       */
                      if (!zebra_nh_port_active_in_cached_l3_ports_hash(
                                                              nexthop->ifname))
                        {
                          zebra_update_selected_nh(rn, route, nexthop->ifname,
                                                   NULL, ZEBRA_NH_UNINSTALL);
                        }
                      else
                        {
                          zebra_update_selected_nh(rn, route, nexthop->ifname,
                                                   NULL, ZEBRA_NH_INSTALL);
                        }
                    }
                  else
                    {
                      /*
                       * In case, the next-hop is to be marked as unselected,
                       * then mark the next-hop and route as unselected in
                       * OVSDB roue table.
                       */
                      zebra_update_selected_nh(rn, route, nexthop->ifname,
                                               NULL, ZEBRA_NH_UNINSTALL);
                    }
                  break;

                /*
                 * Case when the next-hop type is unregnizable.
                 */
                default:
                  VLOG_ERR("Unrecognizable next-hop");
                  break;
              }

            nexthop = nexthop->next;
          }
        break;

#ifdef HAVE_IPV6
      /*
       * Case when the address family is IPv6.
       */
	  case AF_INET6:

        /*
         * Walk all the next-hops of the 'rib' entry and set/un-set
         * the selected flag on the next-hop.
         */
        nexthop = route->nexthop;
        while (nexthop)
          {
            switch (nexthop->type)
              {
                /*
                 * Case when the next-hop is of IPv6 address.
                 */
                case NEXTHOP_TYPE_IPV6:
                  if (inet_ntop(AF_INET6, &nexthop->gate.ipv6,
                                nexthop_str, sizeof(nexthop_str)))
                    {
                      /*
                       * If the next-hop should be marked as selected, then
                       * check whether the next-hop address is active or not.
                       */
                      if (action == ZEBRA_NH_INSTALL)
                        {
                          /*
                           * If the next-hop address is not active, then mark
                           * the next-hop as unselected in OVSDB. If the next-hop
                           * address is active, then mark the next-hop and route
                           * selected.
                           */
                          if (!zebra_nh_addr_active_in_cached_l3_ports_hash(
                                                         nexthop_str, AFI_IP6))
                            {
                              zebra_update_selected_nh(rn, route, NULL, nexthop_str,
                                                       ZEBRA_NH_UNINSTALL);
                            }
                          else
                            {
                              zebra_update_selected_nh(rn, route, NULL, nexthop_str,
                                                       ZEBRA_NH_INSTALL);
                            }
                        }
                      else
                        {
                          /*
                           * In case, the next-hop is to be marked as unselected,
                           * then mark the next-hop and route as unselected in
                           * OVSDB roue table.
                           */
                          zebra_update_selected_nh(rn, route, NULL,
                                                   nexthop_str, ZEBRA_NH_UNINSTALL);
                        }
                    }
                  break;

                /*
                 * Case when the next-hop is of port type.
                 */
                case NEXTHOP_TYPE_IFNAME:

                  /*
                   * If the next-hop should be marked as selected, then
                   * check whether the next-hop port is active or not.
                   */
                  if (action == ZEBRA_NH_INSTALL)
                    {
                      /*
                       * If the next-hop port is not active, then mark
                       * the next-hop as unselected in OVSDB. If the next-hop
                       * port is active, then mark the next-hop and route
                       * selected.
                       */
                      if (!zebra_nh_port_active_in_cached_l3_ports_hash(
                                                              nexthop->ifname))
                        {
                          zebra_update_selected_nh(rn, route, nexthop->ifname,
                                                   NULL, ZEBRA_NH_UNINSTALL);
                        }
                      else
                        {
                          zebra_update_selected_nh(rn, route, nexthop->ifname,
                                                   NULL, ZEBRA_NH_INSTALL);
                        }
                    }
                  else
                    {
                      /*
                       * In case, the next-hop is to be marked as unselected,
                       * then mark the next-hop and route as unselected in
                       * OVSDB roue table.
                       */
                       zebra_update_selected_nh(rn, route, nexthop->ifname,
                                                NULL, ZEBRA_NH_UNINSTALL);
                    }
                  break;

                /*
                 * Case when the next-hop type is unregnizable.
                 */
                default:
                  VLOG_ERR("Unrecognizable next-hop");
                  break;
              }

            nexthop = nexthop->next;
          }
        break;
#endif

      /*
       * Case when the address family is unregnizable.
       */
      default:
        VLOG_ERR("Unrecognizable address family");
        break;
    }
}

/*
 * Function to add ipv4/6 route from protocols, with one or multiple nexthops.
 */
int
zebra_add_route (bool is_ipv6, struct prefix *p, int type, safi_t safi,
                 const struct ovsrec_route *route)
{
  struct rib *rib;
  int flags = 0;
  u_int32_t vrf_id = 0;
  struct ovsrec_nexthop *idl_nexthop;
  struct in_addr ipv4_dest_addr;
  struct in6_addr ipv6_dest_addr;
  unsigned int ifindex = 0;
  int count;
  int rc = 1;

  /* Allocate new rib. */
  rib = XCALLOC (MTYPE_RIB, sizeof (struct rib));

  /* Type, flags, nexthop_num. */
  rib->type = type;
  rib->flags = flags;
  rib->uptime = time (NULL);
  rib->nexthop_num = 0; /* Start with zero */
  rib->ovsdb_route_row_ptr = (void*) route;

  VLOG_DBG("Going through %d next-hops", route->n_nexthops);
  for (count = 0; count < route->n_nexthops; count++)
    {
      idl_nexthop = route->nexthops[count];

      /* If valid and selected nexthop */
      if ( (idl_nexthop == NULL) ||
           ( (idl_nexthop->selected != NULL) &&
             (idl_nexthop->selected[0] != true) ) )
        continue;

      if (idl_nexthop->ports != NULL &&
          idl_nexthop->ip_address != NULL) {
          memset(&ipv4_dest_addr, 0, sizeof(struct in_addr));
          memset(&ipv6_dest_addr, 0, sizeof(struct in6_addr));

          ifindex = ifname2ifindex(idl_nexthop->ports[0]->name);
          if (1 == inet_pton(AF_INET, idl_nexthop->ip_address,
                        &ipv4_dest_addr))
          {
              VLOG_DBG("Processing ipv4 %d-next-hop ipv4 %s",
                       count, idl_nexthop->ip_address);
              nexthop_ipv4_ifindex_add(rib, &ipv4_dest_addr, NULL, ifindex);
          }
          else
          {
              if (1 == inet_pton(AF_INET6, idl_nexthop->ip_address,
                             &ipv6_dest_addr))
               {
                   VLOG_DBG("Processing %d-next-hop ipv6 %s",
                           count, idl_nexthop->ip_address);
                   nexthop_ipv6_ifindex_add(rib, &ipv6_dest_addr, ifindex);
               }
               else
               {
                   VLOG_DBG("Invalid next-hop ip %s", idl_nexthop->ip_address);
                   continue;
               }
          }
      }
      else {
          /* If next hop is port */
          if(idl_nexthop->ports != NULL)
            {
              VLOG_DBG("Processing %d-next-hop %s", count,
                         idl_nexthop->ports[0]->name);
              nexthop_ifname_add(rib, idl_nexthop->ports[0]->name);
            }
          else
          {
              memset(&ipv4_dest_addr, 0, sizeof(struct in_addr));
              memset(&ipv6_dest_addr, 0, sizeof(struct in6_addr));
              /* Check if ipv4 or ipv6 */
              if (inet_pton(AF_INET, idl_nexthop->ip_address,
                            &ipv4_dest_addr) != 1)
              {
                   if (inet_pton(AF_INET6, idl_nexthop->ip_address,
                                 &ipv6_dest_addr) != 1)
                   {
                       VLOG_DBG("Invalid next-hop ip %s", idl_nexthop->ip_address);
                       continue;
                   }
                   else
                   {
                       VLOG_DBG("Processing %d-next-hop ipv6 %s",
                                 count, idl_nexthop->ip_address);
                       nexthop_ipv6_add(rib, &ipv6_dest_addr);
                   }
              }
              else
              {
                  VLOG_DBG("Processing ipv4 %d-next-hop ipv4 %s",
                             count, idl_nexthop->ip_address);
                  nexthop_ipv4_add(rib, &ipv4_dest_addr, NULL);
              }
          }
      }
    }

  /* Distance. */
  if (route->distance != NULL)
    rib->distance = route->distance[0];
  else
    rib->distance = 0;

  /* TODO: What about weight in Nexthop, metric and weight are same?? */
  /* Metric. */
  if (route->metric != NULL)
    rib->metric = route->metric[0];
  else
    rib->metric = 0;

  /* Table */
  rib->table = vrf_id;

  if (is_ipv6)
    {
      /* Set rc, incase of no ipv6 */
#ifdef HAVE_IPV6
      rc = rib_add_ipv6_multipath((struct prefix_ipv6 *)p, rib, safi);
#endif
    }
  else
    rc = rib_add_ipv4_multipath((struct prefix_ipv4 *)p, rib, safi);

  return rc;
}

/*
** Function to create transaction for submitting rib updates to DB.
** Create only if not created already by main thread.
*/
int
zebra_create_txn (void)
{
  if (zebra_txn == NULL)
    {
      zebra_txn = ovsdb_idl_txn_create(idl);
      if (!zebra_txn)
        {
          VLOG_ERR("%s: Transaction creation failed" , __func__);
          return 1;
        }
    }

  /* Else txn already there, continue the updates and commit */
  return 0;
}

/*
** Function to commit the idl transaction if there are any updates to be
** submitted to DB.
*/
int
zebra_finish_txn (void)
{
  enum ovsdb_idl_txn_status status;

  /* Commit txn if any updates to be submitted to DB */
  if (zebra_txn_updates)
    {
      if (zebra_txn)
        {
          status = ovsdb_idl_txn_commit(zebra_txn);
          if (!((status == TXN_SUCCESS) || (status == TXN_UNCHANGED)
                    || (status == TXN_INCOMPLETE)))
	    /*
	     * TODO: In case of commit failure, retry.
	     */
	    VLOG_ERR("Route update failed. The transaction error is %s",
		     ovsdb_idl_txn_status_to_string(status));
	  else
            zebra_txn_updates = false;
        }
      else
        VLOG_ERR("Commiting NULL txn");
    }

  /* Finally in any case destory */
  if (zebra_txn)
    ovsdb_idl_txn_destroy(zebra_txn);

  zebra_txn = NULL;
}
