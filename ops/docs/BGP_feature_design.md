#Overview of BGP in OpenSwitch Architecture#
OpenSwitch is designed to achieve aggressive modularization, hight availability, portability, extensibility, and reuse of open source projects. Quagga BGP project is integrated as one of the modules. BGP alone can provide complete dynamic routing for OpenSwitch. It can also work together with other protocols such as OSPF, ISIS etc. This document mainly focus on the role that BGP plays in the OpenSwitch Architecture and its interaction with other modules. For BGP internal design, refer to BGP_DESIGN.md. For the details of any other module that partcicipates in refer to corresponding module DESIGN.md.

#Participating Modules and Data Flow#
The following diagram (Figure 1) indicates inter module communications and BGP data flow through the OpenSwitch Architecture.

```ditaa

    +------------------------------------------------------------------------+
    |                                BGP                                     |
    |                       (EBGP, IBGP, MPLSVPN)                            |
    +---^--------------------------------------^-----------------------------+
        |                                      |
      1 |                                    2 |
    +---v----+       +-------------+       +---v-----+        +--------------+
    |        |<----->|   Zebra     |<----->|         |<------>|     UI       |
    |   K    |       |   (RIB)     |       |         |        | Config/Show  |
    |        |       +-------------+       |         |        +--------------+
    |   E    |                             |         |
    |        |       +-------------+       |         |        +--------------+
    |   R    |<----->|   Arpmgrd   |<----->|         |<------>|   OSPF-2/3   |
    |        |       |             |       |         |        | (ISIS/RIP)   |
    |   N    |       +-------------+       |    O    |        +--------------+
    |        |                             |         |
    |   E    |       +-------------+       |    V    |        +--------------+
    |        |<----->|   Ported    |<----->|         |<------>|   Policy     |
    |   L    |       | (interface) |       |    S    |        |              |
    |        |       +-------------+       |         |        +--------------+
    | (FIB)  |                             |    D    |
    |        |                             |         |        +--------------+
    +---^----+                             |    B    |        |    BFD       |
        |                                  |         |        |              |
      3 |                                  |         |        +--------------+
    +------------------------------+       |         |
    |   ASIC/HW Forwarding         |       |         |        +--------------+
    |           (FIB)              |       |         |        |    MPLS      |
    +--------------^---------------+       |         |        |  (LDP/RSVP)  |
                   |                       |         |        +--------------+
                   |                       |         |
    +--------------v---------------+       |         |        +--------------+
    |          Vswitchd            |<----->|         |        |  Multicast   |
    |                              |       |         |        | (PIM/IGMP)   |
    +------------------------------+       +---------+        +--------------+
                         Figure 1, Routing Architecture Overview
```

##OVSDB##
OVSDB serves as a central communication hub, all other modules communicate to and from BGP trough OVSDB indirectly. As a result, BGP is shield from all sorts of failures of other modules in the system. OVSDB also provide a single view of data to all modules in the system. All modules and OVSDB interact through publish and subscribe mechanisms.

##BGP##
BGP is an exterior gateway protocol (EGP) that is desinged to exchange routing information among routers and switches in different autonomous systems (AS). BGP runs on top of TCP protocol.

##Kernel##
All BGP protocol control packets, such as open, update, keepalive, and notification are sent and received through Kernel (BGP<--->Kernel<--->ASIC). In addition to provide operating system functions and TCP for BGP, Kernel receives a copy of FIB and can do slow path forwarding compared to ASIC fast path forwarding.

##OSPF and/or ISIS##
(Currently only OSPF is supported, ISIS is one of the future projects ? )
OSPF or ISIS are both link state interior gateway protocol (IGP) that are designed to discover the shortest pathes among routers and switches in a single autonomous systems. OSPF runs on top of IP protocol. OSPF process supports IPv4, OSPF3 supports IPV6. Unlike OSPF, ISIS runs natively on L2 and it does not need interface addressing information to transmit a message. Therefore, it can route multiple protocols and support both IPv4 and IPv6. BGP often relies on IGP to resolves its protocol nexthops.

##UI##
UI is responsible for BGP configurations, state monitoring, show commands and debug dumping.

##Portd/interface##
BGP receives interface up/down state changes, and address notifications from Portd and interface modules.

##Zebra##
Zebra creates FIB by selecting active routes from all routes learned from all protocols including from BGP. On selecting the active routes, Zebra download FIB to kernel, trigger the start of BGP route redistribution, and does nexthop recursive resolution on behalf of BGP.

##BFD##
(Future project to integrate ?)
Bidirectional Forwarding Detection (BFD) can be used to detect faults between two forwarding engines connected by a link. It provides low-overhead detection of faults on physical media that does not support failure detection itself, such as Ethernet, virtual circuits, and tunnels. BGP protocols can use BFD to receive faster notification of failing links than would normally be possible using the native keepalive mechanism to play an important role for BGP fast convergence or fast recovering from link failures. Fast detection of failures is the key for BGP to converge quickly by using ECMP or add path.

##MPLS-LDP-RSVP##
(Future projects to integrate ?)
LDP or RSVP are both MPLS signaling protocols that is used to set up MPLS tunnels. In L3 VPN deployment, BGP relies on the MPLS tunnel to route VPN traffic.

##Multicast-PIM-IGMP##
(Future project to integrate ?)

##HA in OpenSwitch architecture##
(Future project to integrate ?)
    - Non-stop forwarding or graceful restart (GR)
    - Non-stop routing (NSR) using multipath TCP ?

## Policy ##
Policy in Quagga is a libary. BGP includes all policy into BGP process. Then it can be applied when import or export BGP routes. Prefix list can be used for filtering, while route map can be used to change BGP path attributes.

##Inter module data flows##
###Path for BGP input:###
    - Configurations:                     BGP <--- OVSDB <--- UI
    - Port/Interface up/down/addresss:    BGP <--- OVSDB <--- Portd
    - Redistributed routes:               BGP <--- OVSDB <--- Zebra
    - Recursive nexthop resolution:       BGP <--- OVSDB <--- Zebra
    - Route map configuration:            BGP <--- OVSDB <--- Policy
    - Protocol packets:                   BGP <--- Kernel <--- ASIC (3-1)

###Path for BGP output:###
    - Best routes:                        BGP ---> OVSDB ---> Zebra
    - Local RIB:                          BGP ---> OVSDB
    - show/dump/stats                     BGP ---> OVSDB ---> UI
    - Advertise routes, keep alive etc:   BGP ---> Kernel ---> ASIC (1-3)


#OVSDB-Schema#
------------
All BGP configurations come from OVSDB. UI writes configurations to OVSDB.  There are two OVSDB tables designed for BGP configurations corresponding to three hierarchical level of BGP configurations. BGP router table is for global BGP configurations. BGP neighbor and peer group table store group and peer level configurations. BGP subscribes to OVSDB, whenever there is a new configuration or configuration changes, BGP gets notification, and pickups the new configurations, and then programs BGP back end as if the configuration comes from VTYSH directly.

After BGP selects best pathes, BGP writes the selected routes to RIB table in OVSDB. triggerring the start of FIB computation by Zebra. BGP also writes statistics to OVSDB BGP tables.

## BGP and OVSDB table relationships##
The following diagram describes the interaction between BGP and OVSDB tables

```ditaa

    +-------+        +------------+       +-------------+       +-------------+
    |       |   1    |            |       |             |       | BGP Peer/   |
    |       <-------->   VRF      +------->  BGP_Router +-------> Peer Group  |
    |       |        +------------+       +-------------+       +-------------+
    |       |
    |       |        +------------+       +-------------+
    |       |   2    |            |       |             |
    |       <--------+ Route Map  +-------> Rt Map Entry|
    |       |        +------------+       +-------------+
    |       |
    |       |        +------------+       +-------------+
    |   B   |   3    |            |       |             |
    |       <--------+Prefix List +-------> Plist Entry |
    |       |        +------------+       +-------------+
    |       |
    |   G   |        +------------+        +-------------+
    |       |   4    | Global RIB |        |             |
    |       <--------+  FIB       |------->| Nexthop     |
    |       |        +------------+        +-------------+
    |   P   |
    |       |        +------------+       +-------------+
    |       |   5    |            |       |             |
    |       <--------+  Port      +-------> Interface   |
    |       |        +------------+       +-------------+
    |       |
    |       |        +------------+       +-------------+
    |       |   6    |            |       |             |
    |       +-------->  BGP RIB   +-------> BGP Nexthop |
    +-------+        +------------+       +-------------+

              Figure 2 BGP and OVSDB tables
```

      - 1 BGP subscribing to VRF, BGP_router, BGP_Neighbor tables for BGP configurations
              BPG also publishing stats to the three BGP tables
      - 2 BGP subscribing to route map table for route map configurations
      - 3 BGP subscribing to Prefix table for prefix filter configurations
      - 4 BGP publishing best pathes to global RIB table, and for high availability
      - 4 BGP subscribing to FIB for route redistribution and nexthop resolution
      - 5 BGP subscribing to port/interface table for interface states and addresses
      - 6 BGP sending local route to BGP RIB table in OVSDB as a database for BGP internal data

##TABLE SUMMARY##
The following list summarizes the purpose of each of the tables in the OpenSwitch database. Each table is described in more detail following the summary table.

###Table 1: Table summary ###

```ditaa

    Table        |  Purpose
=================|==============================================================
    VRF          |  Virtual Routing and Forwarding
    BGP_router   |  BGP configurations, statuses and statistics
    BGP_neighbor |  BGP peer groups, peers, statuses and statistics
    Route Map    |  Route map to modify BGP path attributes
    Prefix List  |  Prefix list used to filter BGP routes
    RIB/FIB      |  Routing Information Base and Forwarding Information Base
    Nexthop      |  Nexthops for IP routes
    Port         |  Physical port, including L3 interface addresses
    Interface    |  Interface state
    BGP Local RIB|  BGP private RIB, statuses and statistics
-----------------|--------------------------------------------------------------

```

###Table 2: Column SUMMARY for Route Map Table###

```ditaa

    Column         |   Purpose
===================|============================================================
    Name           |   tag of route map
-------------------|------------------------------------------------------------
  route_map_entries|   references to Route Map Entry Table
-------------------|------------------------------------------------------------

```

###Table 3: Column SUMMARY for Route Map Entry Table###

```ditaa

    Column     |   Purpose
===============|================================================================
    action     |   On match permit or deny
---------------|----------------------------------------------------------------
    continue   |   Continue on a entry <1-65536> within the route-map
---------------|----------------------------------------------------------------
    on match   |   On match goto <1-65535> or next
---------------|----------------------------------------------------------------
    call       |   Jump to another Route-Map WORD after match+set
---------------|----------------------------------------------------------------
    match      |   key                           value
               |----------------------------------------------------------------
               | as-path                      name of access list
               | community                    <1-99>|<100-500>|WORD
               | community                    <1-99>|<100-500>|WORD exact-match
               | extcommunity                 <1-99>|<100-500>|WORD
               | interface                    name of 1st hop interface
               | ip address  prefix-list      name of prefix list
               | ip address                   <1-199>|<1300-2699>|WORD of alist
               | ip next-hop prefix-list      name
               | ip next-hop                  <1-199>|<1300-2699>|WORD
               | ip route-source prefix-list
               | ip route-source              <1-199>|<1300-2699>|WORD
               | ipv6 address prefix-list
               | ipv6 address                 name
               | ipv6 next-hop                X:X::X:X
               | metric                       <0-4294967295>
               | origin                       egp|igp|incomplete
               | peer                         A.B.C.D|X:X::X:X
               | tag                          <0-65535>
---------------|----------------------------------------------------------------
    set        |   Key                       value
               |----------------------------------------------------------------
               |   aggregator  as           <1-4294967295> A.B.C.D
               |   as-path  exclude         <1-4294967295>
               |   as-path  prepend         <1-4294967295>
               |   atomic-aggregate
               |   comm-list                <1-99>|<100-500>|WORD delete
               |   community                AA:NN|AA:NN additive/none
               |   extcommunity  rt         ASN:nn_or_I-address:nn
               |   extcommunity  soo        ASN:nn_or_IP-address:nn
               |   forwarding-address       X:X::X:X
               |   ip next-hop              A.B.C.D/peer-address
               |   ipv6  next-hop  global   X:X::X:X
               |   ipv6  next-hop  local    X:X::X:X
               |   local-preference         <0-4294967295>
               |   metric                   <+/-metric>|<0-4294967295>
               |   origin                   egp|igp|incomplete
               |   originator-id            A.B.C.D
               |   src                      A.B.C.D
               |   tag                      <0-65535>
               |   vpnv4  next-hop          A.B.C.D
               |   weight                   <0-4294967295>
---------------|----------------------------------------------------------------

```

###Table 4: Column SUMMARY for Prefix List Table###

```ditaa

    Column           |   Purpose
=====================|==========================================================
    Name             |   tag of prefix list
---------------------|----------------------------------------------------------
  prefix_list_entries|   references to Prefix List Entry Table
---------------------|----------------------------------------------------------

```

###Table 5: Column SUMMARY for Prefix List Entry Table###

```ditaa

    Column         |   Purpose
===================|============================================================
    action         |   permit or deny
-------------------|------------------------------------------------------------
    prefix         |   ip address
-------------------|------------------------------------------------------------
    ge             |
-------------------|------------------------------------------------------------
    le             |
-------------------|------------------------------------------------------------

```

###Table 6: Column SUMMARY for VRF Table###

```ditaa

    Column           |   Purpose
=====================|==========================================================
    Name             |   tag of vrf
---------------------|----------------------------------------------------------
    bgp_routers      |   references to BGP Router Table
---------------------|----------------------------------------------------------

```

###Table 7: Column SUMMARY for BGP Router Table###

```ditaa

    Column           |   Purpose
=====================|==========================================================
    router_id        |   id of BGP router
---------------------|----------------------------------------------------------
    networks         |   BGP configured network routes
---------------------|----------------------------------------------------------
    maximum_paths    |   max ECMP path allowed, to enable ECMP
---------------------|----------------------------------------------------------
                     |   key              value
    timers           |   keepalive
                     |   holdtime
---------------------|----------------------------------------------------------
    redistribute     |   export routes from other protocols to BGP
---------------------|----------------------------------------------------------
  always_compare_med |
---------------------|----------------------------------------------------------
  deterministic_med  |
---------------------|----------------------------------------------------------
  gr_stale_timer     |
---------------------|----------------------------------------------------------
                     |   n_bgp_neighbors: count of bgp instances
   bgp_neighbors     |   key_bgp_neighbors: tag of bgp peer or peer group
                     |   value_bgp_neighbors: pointer to bgp router row
---------------------|----------------------------------------------------------
  fast-external-failover|
---------------------|----------------------------------------------------------
  enforce-first-as   |
---------------------|----------------------------------------------------------
  aggregate-address  |
---------------------|----------------------------------------------------------
  cluster-id         |
---------------------|----------------------------------------------------------
  graceful-restart   | Not fully supported in Quagga, only EOR supported
---------------------|----------------------------------------------------------

```

###Table 8: Column SUMMARY for BGP Neighbour Table###

```ditaa

    Column           |   Purpose
=====================|==========================================================
    is_peer_group    |   peer or peer group
---------------------|----------------------------------------------------------
    shutdown         |   Shutdown peer but keep configurations
---------------------|----------------------------------------------------------
  remove_private_as  |   Do not send private AS out of AS
---------------------|----------------------------------------------------------
    passive          |
---------------------|----------------------------------------------------------
    bgp_peer_group   |   Peer pointing to peer group it belong to
---------------------|----------------------------------------------------------
    remote_as        |   AS number of a peer
---------------------|----------------------------------------------------------
    allow_as_in      |   Permit own AS appearing in the as path
---------------------|----------------------------------------------------------
    local_as         |   AS number of self
---------------------|----------------------------------------------------------
    weight           |   Local weight for best path selection
---------------------|----------------------------------------------------------
   tcp_port_number   |
---------------------|----------------------------------------------------------
 advertise_interval  |   Mimum time to wait before advertise routes
---------------------|----------------------------------------------------------
    maximum_prefix   |   Maxinum number of prefix can receive from a peer
---------------------|----------------------------------------------------------
    capability       |
---------------------|----------------------------------------------------------
 override_capability |
---------------------|----------------------------------------------------------
 inbound_soft_reconfiguration | keep a copy of all received routes
---------------------|----------------------------------------------------------
    password         |   MD5 TCP password
---------------------|----------------------------------------------------------
                     |   key              value
    timers           |   keepalive
                     |   holdtime
---------------------|----------------------------------------------------------
                     |   key              value
    route_maps       |   in/out           pointer to a row of a Route_Map table
---------------------|----------------------------------------------------------
    statistics       |   Key                           value
                     |   bgp-peer-established-count
                     |   bgp-peer-dropped-count
                     |   bgp-peer-open_in-count
                     |   bgp-peer-open_out-count
                     |   bgp-peer-update_in-count
                     |   bgp-peer-update_out-count
                     |   bgp-peer-keepalive_in-count
                     |   bgp-peer-keepalive_out-count
                     |   bgp-peer-notify_in-count
                     |   bgp-peer-notify_out-count
                     |   bgp-peer-refresh_in-count: count of route refresh received
                     |   bgp-peer-refresh_out-count
                     |   bgp-peer-dynamic_cap_in-count: how many time dynamic cap send
                     |   bgp-peer-dynamic_cap_out-count: how many time dynamic cap send
                     |   bgp-peer-uptime: how long since peer is established
                     |   bgp-peer-readtime: when was last time u/k message received
                     |   bgp-peer-readtime: when was last time peer get reset
---------------------|----------------------------------------------------------
  timers connect     |   BGP connect tiemr
---------------------|----------------------------------------------------------
  advertisement-interval| Minimum gap between send updates
---------------------|----------------------------------------------------------
  capability dynamic |  Advertise dynamic capability
---------------------|----------------------------------------------------------
  capability orf     |  Advertise ORF capability of prefix list send/receive
---------------------|----------------------------------------------------------
  override-capability|  Override negotiation
---------------------|----------------------------------------------------------
  disable-connected-check| Multihop EBGP
---------------------|----------------------------------------------------------
  ebgp-multihop      |  Enable multihop EBGP
---------------------|----------------------------------------------------------
  next-hop-self      |
---------------------|----------------------------------------------------------
  route-reflector-client| Nbr as a RR client
---------------------|----------------------------------------------------------
  send-community     |  Send cummunity to this nbr
---------------------|----------------------------------------------------------
  ttl-security hops  |  Max hop to BGP peer
---------------------|----------------------------------------------------------

```

###Table 9: Column SUMMARY for RIB (Route) Table###

```ditaa

    Column             |   Purpose
=======================|==========================================================
    vrf                |   back pointer to vrf table that this rib belong to
-----------------------|----------------------------------------------------------
    prefix             |   prefix/len
-----------------------|----------------------------------------------------------
    from               |   which protocol this prefix learned
-----------------------|----------------------------------------------------------
    address_family     |   IPv4, IPv6
-----------------------|----------------------------------------------------------
    sub_address_family |   Unicast, multicast
-----------------------|----------------------------------------------------------
    distance           |   Administrative preference of this route
-----------------------|----------------------------------------------------------
    metric             |   BGP MED value
-----------------------|----------------------------------------------------------
                       |   n_nexthops: count of nh
    nexthops           |   Array of pointer to next hop table row
-----------------------|----------------------------------------------------------
    selected           |
-----------------------|----------------------------------------------------------

```


###Table 10: Column SUMMARY for Nexthop Table###

```ditaa

    Column           |   Purpose
=====================|==========================================================
    ip_address       |
---------------------|----------------------------------------------------------
    type             |   nexthop type  (unicast, multicast, indirect etc)
---------------------|----------------------------------------------------------
    ports            |   n_ports
                     |   array of pointer to Port table row
---------------------|----------------------------------------------------------
    selected         |
---------------------|----------------------------------------------------------
    weight           |   weight for unequal cost load balance
---------------------|----------------------------------------------------------

```

###Table 11: Column SUMMARY for BGP RIB (BGP_Route) Table###

```ditaa

    Column             |   Purpose
=======================|==========================================================
    vrf                |   back pointer to vrf table that this rib belong to
-----------------------|----------------------------------------------------------
    prefix             |   prefix/len
-----------------------|----------------------------------------------------------
    address_family     |   IPv4, IPv6
-----------------------|----------------------------------------------------------
    sub_address_family |   Unicast, multicast
-----------------------|----------------------------------------------------------
    peer               |
-----------------------|----------------------------------------------------------
    distance           |   Administrative preference of this route
-----------------------|----------------------------------------------------------
    metric             |   BGP MED value
-----------------------|----------------------------------------------------------
                       |   n_nexthops: count of nh
    bgp_nexthops       |   Array of pointer to bgp next hop table row
-----------------------|----------------------------------------------------------
    path_attributes    |   key                      value
                       |----------------------------------------------------------
                       |   as-path
                       |   Origin
                       |   metric/MULTI_EXIT_DISC
                       |   local pref
                       |   community                7010:6010 7012:6012
                       |   excommunity
                       |   weight
                       |   ORIGINATOR_ID
                       |   CLUSTER_LIST
                       |   ADVERTISER
                       |   AGGREGATOR
-----------------------|----------------------------------------------------------
    flags              |   TBD
-----------------------|----------------------------------------------------------

```

###Table 12: Column SUMMARY for BGP Nexthop Table###

```ditaa

    Column           |   Purpose
=====================|==========================================================
    ip_address       |
---------------------|----------------------------------------------------------
    type             |   nexthop type  (unicast, multicast, indirect etc)
---------------------|----------------------------------------------------------
    Weight           |   TBD
---------------------|----------------------------------------------------------

```

###Table 13: Column SUMMARY for Port Table###

```ditaa

    Column           |   Purpose
=====================|==========================================================
    name             |   tag of port
---------------------|----------------------------------------------------------
    interfaces       |   references to Interface Table
---------------------|----------------------------------------------------------
    vlan_mode        |   trunk/access/native-tagged/native-untagged
---------------------|----------------------------------------------------------
    tag              |
---------------------|----------------------------------------------------------
    trunk            |
---------------------|----------------------------------------------------------
    mac              |
---------------------|----------------------------------------------------------
    ip4_address      |
---------------------|----------------------------------------------------------
    ip6_address      |
---------------------|----------------------------------------------------------

```

###Table 14: Column SUMMARY for Interface Table###

```ditaa

    Column           |   Purpose
=====================|==========================================================
    name             |   tag of port
---------------------|----------------------------------------------------------
    name             |   tag of interface
---------------------|----------------------------------------------------------
    type             |   system/internal
---------------------|----------------------------------------------------------
    admin_state      |   up/down
---------------------|----------------------------------------------------------
    link_state       |   up/down
---------------------|----------------------------------------------------------
    mtu              |
---------------------|----------------------------------------------------------

```

#Any other sections that are relevant for the module#
---------------------------------------------------
TBD

#References#
----------
* [Reference 1](http://www.nongnu.org/quagga/docs.html)
* [Reference 2](https://www.ietf.org/rfc/rfc4271.txt)
* ...

Include references to DESIGN.md of any module that participates in the feature.
Include reference to user guide of the feature.
