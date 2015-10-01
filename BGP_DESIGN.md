#High level design of OPS-Guagga-BGP#
============================
#BGP Overview#

BGP can be classified as EBGP, IBGP, and MPLSVPN. EBGP is an exterior gateway protocol (EGP) that is designed to exchange large amount of routing information among routers and switches in different autonomous systems (AS). IBGP is designed to exchange routing information within an AS. BGP VPN is based on RFC 4364, BGP/MPLS IP Virtual Private Networks (VPNs) to ensure that VPNs remain private and isolated from public internet and other VPNs. It is known as BGP/MPLS VPNs because BGP is used to distribute VPN routing information across the provider backbone, and MPLS is used to forward VPN traffic across the backbone.

Unlike IGP that does neighbor auto-discovery, BGP learns its peer by configurations. Firstly BGP establishes peer sessions with its peers. On successfully establishing sessions, BGP starts to exchange routing information, chooses the best to a destination among multiple paths, adds the best to global RIB for forwarding, and advertises the selected routing information. By selecting best paths, BGP constructs a graph of network topology that consists of reachable paths and are free of loops.

BGP frequently uses routing policy to control routing information exchanges. Quagga routing policy is in the form of a library that includes prefix list, access list, and route map. By match prefixes, destination addresses, tags, communities, and as-paths, policy can influence BGP decisions on both receiving and advertising routes. By using route map, BGP can modify path attributes before route selection to influence routing decisions or before advertising it to a peer (refer to Figure 5).

OpenSwitch BGP supports BGP version 4 that supports for classless inter-domain routing (CIDR), aggregation of routes, Ipv4, IPv6, unicast, multicast, and capability negotiations. OpenSwitch BGP also supports 4 byte AS numbers.

Because BGP establishes its session on top of TCP that provides ordered, reliable, secured transport. BGP is freed from implementing update fragmentation, re-transmission, acknowledgment, and sequencing. Unlike IGP periodic flooding, BGP is able to do incremental updates as the routing table changes for the same reasons.

This document mainly describes EBGP design in OpenSwitch Architecture by using large-scale data centers as an example (Figure 1). BGP major internal data structures is also documented in this document. For the interactions among BGP and other OpenSwitch modules, refer to BGP_feature_design.md (http://www.openswitch.net/documents/dev/ops/docs/BGP_feature_design.md)

#Responsibilities#
---------------
BGP is responsible for providing dynamic routing for routers and switches that are usually deployed in ISP, enterprise, campus, and large scale data centers. BGP can be deployed alone or together with OSPF, ISIS, MPLS and so on.

#Design choice#
--------------
The current goal is to provide simple and stable routing for large scale data centers that support over 100,000 servers. In a typical large data center, a common choice of topology is a Clos (see 5-stage Clos as illustrated on Figure 1). ECMP is the fundamental load-sharing mechanism used by a Clos topology. BGP is chosen because it provides multi-path, multi-hop features and is simple to operate.

#BGP route selection process#
BGP selects best routes according to the following order (see Table 1).


```ditaa

          ##Table 1, BGP Route Selection##

     Check Order           |  Favor
===============================================================================
     1. Weight             |  highest
     2. Local preference   |  highest
     3. Local route        |  static, aggregate, or redistribute
     4. AS path length     |  shortest
     5. Origin             |  IGP > EGP > INCOMPLETE
     6. MED                |  Lowest (default: missing as lowest)
     7. Peer type          |  EBGP > IBGP
     8. IGP metric         |  Lowest
     9. Router-ID          |  Lowest (tie breaker)
     10. Cluster length    |  Shortest
     11. Neighbor address  |  Lowest
---------------------------|----------------------------------------------------

```

#BGP Multipath, equal-cost load balancing#
Figure 1 shows 5-stage Clos topology and the the ECMP paths existing in this topology.

```ditaa

                                  Tier 1
                                 +-----+
                                 | DEV |
                              +->|  1  |--+
                              |  +-----+  |
                      Tier 2  |           |   Tier 2
        Tier 3       +-----+  |  +-----+  |  +-----+      Tier 3
       +------------>| DEV |--+->| DEV |--+--|     |-------------+
       |       +-----|  B  |--+  |  2  |  +--|  E  |-----+       |
       |       |     +-----+     +-----+     +-----+     |       |
       |       |                                         |       |
       |       |     +-----+     +-----+     +-----+     |       |
       | +-----+---->| DEV |--+  | DEV |  +--|     |-----+-----+ |
       | |     | +---|  C  |--+->|  3  |--+--|  F  |---+ |     | |
       | |     | |   +-----+  |  +-----+  |  +-----+   | |     | |
       | |     | |            |           |            | |     | |
     +-----+ +-----+          |  +-----+  |          +-----+ +-----+
     | DEV | |     |          +->| DEV |--+          |     | |     |
     |  A  | |     |             |  4  |             |  G  | |     |
     +-----+ +-----+             +-----+             +-----+ +-----+
       | |     | |                                     | |     | |
       O O     O O            <- Servers ->            X Y     X O


     Figure 1: ECMP paths from A to X and Y in a 5-stage Clos topology

    - A--->B--->1--->E--->G
    - A--->B--->2--->E--->G
    - A--->c--->3--->F--->G
    - A--->c--->4--->F--->G

```

BGP implementations declare paths to be equal from ECMP perspective if they match up to and including step (e) in Section 9.1.2.2 of [RFC4271] (refer to Table 1, (8)). ECMP paths bear the same AS path length, they can have the different router ids, or different AS path value. Figure 1 shows that this topology has four ECMP paths from source A to destination X.

By default, multipath is disabled. To enable multipath, the "max-path" needs to be configured. For load-balancing applications, the same prefix can be advertised from multiple Tier-3 switches. Such a prefix would have BGP paths with different AS PATH attribute values, although the same AS path attribute length. To support load-sharing over such paths, the "AS PATH multipath relax" needs to be configured separately for some implementations. This extra configuration effectively allows for ECMP across different neighboring ASNs. In OpenSwitch this is automatically enabled when max-path is configured (This is a workaround for the Quagga BGP bug).

When using BGP multipath, the link failure is minimized. For example, if a link between Tier-1 and Tier-2 fails. The local node can simply update its ECMP group, the Tier-3 devices will not be involved in the re-convergence process.

Relying on BGP keep-alive packets solely may result in high convergence delays, in the order of multiple seconds (minimum BGP hold timer value is 3 seconds). However, in modern data centers, fiber link failure can be detected in milliseconds. BGP implementations with "fast fail-over" feature, can shut down local eBGP peering sessions immediately in response to the "link down" event for the outgoing interface and subsequently triggers a BGP re-convergence quickly. (Refer to Table 2 for multipath columns in OVSDB BGP Router table)

#BGP unequal-cost load-balancing#
With add path technique, BGP would make it possible to implement unequal-cost load-balancing. When a link failure occur, the local node can immediately find a backup path.

#Multihop EBGP#
Multihop EBGP makes it possible to establishing an EBGP multihop peering session with the application "controller". This allows for ECMP or forwarding based on application-defined forwarding paths. This requires recursive resolution of the next-hop address specified in BGP updates to be fully supported.

#OVSDB-Schema#
------------
BGP configurations and statistics are stored in BGP_router, and BGP_Neighbor tables in OVSDB. For details refer to tables/columns in BGP_feature_design.md (http://www.openswitch.net/documents/dev/ops/docs/BGP_feature_design.md). BGP uses a three level of hierarchical configuration schema. From top to bottom, they are global BGP router, BGP peer group, and BGP peer. Lower level inherits higher level configuration if a configuration is missing in this level, and lower level overwrite higher level configuration if a configuration exists in this level.

##ECMP feature related OVSDB table and column##
In the OVSDB, the following columns in OVSDB BGP_router table are related to the BGP multipath (Table 2).


```ditaa

    ##Table 2, Column related to multipath in BGP_Router table##

    Column               |   Purpose
=========================|======================================================
    ......               |
-------------------------|------------------------------------------------------
  maximum_paths          |   max ECMP path allowed, to enable ECMP
-------------------------|------------------------------------------------------
  fast-external-failover |   fast convergence
-------------------------|------------------------------------------------------
  multipath relax        |   allow ECMP accross different neighboring ASNs
-------------------------|------------------------------------------------------

```


#Internal structure#
------------------
##BGP FSM##
BGP peers use a finite state machine (FSM) to establish session with peers.

Figure 2 illustrate the six FSM states and their relationships.

```ditaa

    +-------+         1           +---------------+
    |       <--------------------->               <--+
    |       |       +------+      |   CONNECT     |  |
    |       |       |  A   <------>               +--+
    |       |       |  C   |      +-------+-------+
    |       |       |  T   <--+           |
    |   I   <-------+  I   |  |           v
    |       |       |  V   +--+           | 2
    |       |       |  E   |      +-------v-------+
    |       |       |      <------>               |
    |       |       +------+      |   OPENSEND    |
    |   D   |                     |               |
    |       <--+                  +-------+-------+
    |       |  |                          |
    |       +--+                          | 3
    |       |                     +-------v-------+
    |   L   |                     |               <--+
    |       <---------------------+  OPENCONFIRM  |  |
    |       |                     |               +--+
    |       |                     +-------+-------+
    |       |                             |
    |   E   |                             | 4
    |       |                     +-------v-------+
    |       |                     |               <--+
    |       <---------------------+  ESTABLISHED  |  |
    +-------+                     |               +--+
                                  +---------------+

             Figure 2, BGP FSM

```

The first state is "Idle" state. In the "Idle" state, BGP initializes all resources and initiates a TCP connection to the peer. The second state is "Connect". In the "Connect" state, the router waits for the TCP connection to complete and transitions to the "OpenSend" state if successful. In the "OpenSent" state, the router sends an Open message and waits for one in return in order to transition to the "OpenConfirm" state. In "OpenConfirm" state, keepalive messages are exchanged and, upon successful receipt of keepalive message, the router is transit into the "Established" state. "Established" is the BGP normal operational state.


##BGP Local RIB##
BGP maintains a local routing table into which received route from all peers are added. A route in BGP does not automatically mean that it is used for forwarding. Routes in local RIB may be advertised to other BGP speakers on another interface.

Figure 3 shows the internal data structure of BGP rib. Each route is a bgp_node, that consists of a prefix, and path attributes organized as a bgp_info (refer to Figure 3).


```ditaa

                               2. bgp
                           +---------------------+
                           | as                  |
                           | config              |
                           | router_id           |
                           | cluster_id          |
                           | confed_id           |
                           | confed_peers        |
                           | confed_peers_cnt    |
                           |                     |
                           | t_startup           |
                           | flags               |
                           | af_flags[AFI][SAFI] |
                           | route[AFI][SAFI]    |
                           | aggregate[][]       |
                           | redist[AFI][SAFI]   |
                           | default_holdtime    |
                           | defautl_keepalive   |
     1. bgp_master         | restart_time        |          3. bgp_node
    +---------------+      | stalepath_time      |          (radix tree)
    |               |      |                     |         +-------------+
    | bgp (list) ---+----->| peer (list)         |         | p           |
    |               |      | group (list)        |         | info (list) |-----+
    |               |      | rib[AFI][SAFI] -----+-------->| adj_in(list)|     |
    +---------------+      | rmap[AFI][SAFI]     |         | adj_o(list) |     |
                           | maxpaths[AFI][SAFI] |         | aggreagate  |     |
                           +---------------------+         +-------------+     |
                                                                               |
    +--------------------------------------------------------------------------+
    |
    |        bgp_info            attr              attr_extra
    |      +-----------+      +-----------+     +----------------+
    +----->| peer      |      | aspath    |     | mp_nh_global   |
           | attr -----+----->| community |     | mp_nh_local    |
           | extra     |      | extra ----+---->| ecommunity     |
           | mpath ----+--+   | refcnt    |     | cluster        |
           | uptime    |  |   | flag      |     | transit (TLV)  |
           | flags     |  |   | nexthop   |     | aggregator_addr|
           | type      |  |   | med       |     | orignator_id   |
           | sub_type  |  |   | local_pref|     | weight         |
           | next/prev |  |   | origin    |     | aggregator_as  |
           +-----------+  |   +-----------+     | mp_nh_len      |
                          |                     +----------------+
                          |
                          |      7. bgp_info_mpath
                          |      +-----------+
                          +----->| mp_info   |
                                 | mp_count  |
                                 | mp_attr   |
                                 +-----------+

                  Figure 3, RIB internal data structure and relationships

```

##BGP Peer##
Each BGP speaker is organized as a peer structure. BGP peer holds all BGP configurations, states, timers, threads, and statistics. It also contains the BGP filter that controls routes received from a peer and routes advertised to a peer. BGP peer filter consists of distribute list, prefix list, as list, and route map. Route map with its match and set operations is the technique that is used to modify BGP route information (Refer to Figure 4).

```ditaa

                                      peer
                                +----------------------+
                                | config               |
                                | allowasin[AFI][SAFI] |
                                | weight               |
                                | holdtime             |
                                | keepalive            |
                                | connect              |
                                | routeadv             |
                                | v_start              |
                                | v_connect            |
                                | v_holdtime           |
                                | v_keepalive          |
                                | v_asorig             |
                                | v_routeadv           |
      2. bgp                    | v_gr_restart         |
    +---------------------+     |                      |
    |                     |     | t_read               |
    | group (list)        |     | t_start              |
    | peer (list)  -------+---->| t_write              |
    | rib[AFI][SAFI]      |     | t_connect            |
    | rmap[AFI][SAFI]     |     | t_holdtime           |
    | maxpaths[AFI][SAFI] |     | t_keepalive          |
    |                     |     | t_asorig             |
    +---------------------+     | t_routeadv           |
                                | t_gr_restart         |      bgp_synchronize
                                | t_gr_stale           |     +--------------+
                                |                      |     | update       |
                                | sync[AFI][SAFI] -----+---->| withdraw     |
                                | synctime             |     | withdraw_low |
                                | bgp                  |     +--------------+
                                | group                |
                                | as                   |
                                | sort                 |
                                | remote_d             |
                                | local_id             |
                                | status               |
                                | ostatus              |
                                | fd                   |
                                | ttl                  |
                                | ibuf                 |
                                | work                 |
                                | scratch              |
                                | obuf                 |
                                | port                 |       bgp_filter
                                | su                   |     +-------------+
                                | uptime               |     | dlist[MAX]  |
                                | notify               |     | plist[MAX]  |
                                | filter[AFI][SAFI] ---+---->| aslist[Max] |
                                | orf_plist[AFI][SAFI] |     | map[MAX] ---+---+
                                | last_reset           |     | usmap       |   |
                                | su_local             |     +-------------+   |
                                | su_remote            |                       |
                                | nexthop              |                       |
                                | afc[AFI][SAFI]       |                       |
                                | afc_nego[AFI][SAFI]  |                       |
                                | afc_recv[AFI][SAFI]  |                       |
                                | cap                  |                       |
                                | af_cap[AFI][SAFI]    |                       |
                                | flags                |                       |
                                | nsf[AFI][SAFI]       |                       |
                                | af_flags[AFI][SAFI]  |                       |
                                | sflags               |                       |
                                | af_sflags[AFI][SAFI] |                       |
                                | ...                  |                       |
                                +----------------------+                       |
                                                                               |
    +--------------------------------------------------------------------------+
    |
    |    route_map    route_map_index
    |    +------+     +------------+
    |    | name |     | pref       |
    +--->| head |---->| type       |    route_map_rule     route_map_rule_cmd
         | tail |     | exitpolicy |     +----------+     +--------------+
         | next |     | nextpref   |     | cmd  ----|---->| str          |
         | prev |     | nextrm     |     | rule_str |     | func_apply   |
         +------+     | match_list |---->| value    |     | func_compile |
                      | set_list   |     | next/prev|     | func_free    |
                      | next/prev  |     +----------+     +--------------+
                      +------------+

                 Figure 4, BGP peer internal data structure

```

##BGP Policy/Filter##

I-Filter controls which routes BGP place in the routing tables. O-Filter controls which routes BGP advertise (see Figure 5). Route map is used to change specific route information, and controls which route is selected as the best route to reach a destination.

```ditaa

                        +-----+                       +-----+
                        |  i  |                       |  o  |
                        |     |                       |     |
    +-------------+     |  F  |     +-----------+     |  F  |    +-------------+
    |             |     |  i  |     |           |     |  i  |    |             |
    | BGP speaker +----->  l  +----->   RIB     +----->  l  +----> BGP speaker |
    |             |     |  t  |     |           |     |  t  |    |             |
    +-------------+     |  e  |     +-----------+     |  e  |    +-------------+
                        |  r  |                       |  r  |
                        +-----+                       +-----+

               Figure 5: Routing Policies to Control Routing Information Flow

```

##BGP Timer##
BGP employs six per-peer timers: ConnectRetryTimer, HoldTimer, KeepaliveTimer, MinASOriginationIntervalTimer, MinRouteAdvertisementIntervalTimer, and GRRestartTimer (see Table 3).


```ditaa

         ##Table 3, BGP important timers##

              | default | Description
  ============|=========|======================================
  v_connect   | 120     | minimum connection retry interval
  v_holdtime  | 180     | time to wait to declear connection down
  v_keepalive | 60      | keepalive timer (1/3 holdtimer)
  v_asorig    | 15      | minimum AS origination interval
  v_routeadv  | 30/5    | minimum route advertisement interval
  v_gr_restart|         | maximum wait for session re-establishing

```

Hold Time: The maximum number of seconds that may elapse between the receipt of successive KEEPALIVE and/or UPDATE messages from the sender. The Hold Time MUST be either zero or at least three seconds

As origination time: MinASOriginationIntervalTimer determines the minimum amount of time that must elapse between successive advertisements of UPDATE messages that report changes within the advertising BGP speaker's own autonomous systems.

Route advertisement time: Two UPDATE messages sent by a BGP speaker to a peer that advertise feasible routes and/or withdrawal of unfeasible routes to some common set of destinations MUST be separated by at least MinRouteAdvertisementIntervalTimer.

GR restart time: Restart time is received from restarting peer advertised previously. If the session does not get re-established within the "Restart Time", the receiving speaker MUST delete all the stale routes from the peer that it is retaining.

#References#
----------
* [Quagga](http://www.nongnu.org/quagga/docs.html)
* [BGP](https://www.ietf.org/rfc/rfc4271.txt)
* [OpenSwitch](http://www.openswitch.net/documents/dev/ops-openvswitch/DESIGN)
* [Archtecture](http://www.openswitch.net/documents/user/architecture)
