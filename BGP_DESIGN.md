#High level design of OPS-Guagga-BGP
============================
#BGP overview

BGP can be classified into the following types:
-eBGP--Acts as an exterior gateway protocol to exchange large amount of routing information among routers and switches in different autonomous systems (AS).
-iBGP--Exchanges routing information within an AS, typically to distribute exterior routing information across an AS while leaving interior routing to a dedicated IGP.
-MPLSVPN--Is a BGP VPN based on RFC 4364, "BGP/MPLS IP Virtual Private Networks (VPNs)", to ensure that VPNs remain private and isolated from public internet and other VPNs. It is known as BGP/MPLS VPNs because BGP is used to distribute VPN routing information across the provider backbone, and MPLS is used to forward VPN traffic across the backbone.

Unlike IGP that does neighbor auto-discovery, BGP acquires its peers by configuration.

BGP establishes sessions with its peers. On successfully establishing a session with a neighbor, BGP starts exchanging routing information, and updates its local RIB accordingly.

BGP then chooses the best path to a destination from among the paths available in the BGP RIB. The best path is then sent to the global RIB for forwarding, and is also advertised to its other BGP peers.

As a result, BGP selects best-paths through an extended form of distributed Bellman-Ford.

Each BGP speaker selects a set of path vectors according to what is locally available, and updates its neighbors accordingly, converging on a reachable set of paths that are available to the BGP speaker.

BGP frequently uses routing policy to control routing information exchanges. Quagga routing policy is in the form of a library that includes a prefix list, an access list, and a route map.

By matching prefixes, destination addresses, tags, communities, and as-paths, Quagga routing policy can influence BGP decisions on both receiving and advertising routes.

By using the Quagga route map, BGP can modify path attributes before route selection to influence routing decisions or before advertising it to a peer (refer to Figure 5).

OpenSwitch BGP supports BGP version 4 that supports for Ipv4, IPv6, unicast, multicast, and capability negotiations. OpenSwitch BGP also supports 4 byte AS numbers.

Because BGP establishes its session on top of TCP which provides ordered, reliable, secured transport, it is freed from implementing update fragmentation, re-transmission, acknowledgment, and sequencing. Unlike IGP periodic flooding, BGP is able to do incremental updates as the routing table changes.

This document mainly describes EBGP design in OpenSwitch Architecture by using large-scale data centers as an example (Figure 1). BGP major internal data structures is also documented in this document. For the interactions among BGP and other OpenSwitch modules, refer to BGP_feature_design.md (http://www.openswitch.net/documents/dev/ops/docs/BGP_feature_design.md)

#Responsibilities
---------------
BGP is responsible for providing dynamic routing for routers and switches that are usually deployed in ISP, enterprise, campus, and large scale data center environments. BGP can be deployed alone or with other protocols such as OSPF, ISIS, MPLS and so on.

#Design choice
--------------
The current goal is to provide simple and stable routing for large scale data centers that support over 100,000 servers. In a typical large data center, a common choice of topology is a Clos (see 5-stage Clos as illustrated on Figure 1). ECMP is the fundamental load-sharing mechanism used by a Clos topology. BGP is chosen because it provides multipath and multi-hop features, and is simple to operate.

#BGP route selection process
BGP selects the best routes according to the order shown Table 1.


```ditaa

          ##Table 1 BGP route selection

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

#BGP multipath, equal-cost load balancing
Figure 1 shows the 5-stage Clos topology and the ECMP paths existing in this topology.

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
       O O     O O            <- Servers ->            X Y     O O


     Figure 1: ECMP paths from A to X and Y in a 5-stage Clos topology

    - A--->B--->1--->E--->G
    - A--->B--->2--->E--->G
    - A--->c--->3--->F--->G
    - A--->c--->4--->F--->G

```
The BGP multi-path implementation declares paths to be equal from an ECMP perspective if they match up with step (e) in Section 9.1.2.2 of [RFC4271] (refer to Table 1, (8)). ECMP paths have the same AS path length, but they can have the different router ids, or different AS path values. Figure 1 displays that this topology has four ECMP paths from source A to destination X. Traffic sending from A to X will load balance to device B and device C, at device B traffic will load balance to device 1 and device 2.

By default, multipath is disabled. To enable multipath, the "max-path" parameter needs to be configured. For load-balancing applications, the same prefix can be advertised from multiple Tier-3 switches. This prefix needs to have BGP paths with different AS PATH attribute values, but with the same AS path attribute lengths.

To support load-sharing over the paths, the "AS PATH multipath relax" parameter needs to be configured separately for some implementations. This extra configuration enables ECMP across different neighboring ASNs. In OpenSwitch, this is automatically enabled when the max-path parameter is configured.

When using BGP multipath, the link failure is minimized. For example, if a link between Tier-1 and Tier-2 fails, the local node can simply update its ECMP group and the Tier-3 devices will not be involved in the re-convergence process.

Relying on BGP Keepalive packets solely may result in high convergence delays, in the order of multiple seconds (minimum BGP hold timer value is 3 seconds). However, in modern data centers, fiber link failure can be detected in milliseconds.

BGP implementations with the "fast fail-over" feature can shut down local eBGP peering sessions immediately in response to a "link down" event for the outgoing interface and subsequently triggers a BGP re-convergence quickly. (Refer to Table 2 for multipath columns in the OVSDB BGP Router table.)

BGP can in some certain circumstances get into unstable, oscillating behavior. This can occur when there is a non-transitive order of preference between different paths AND path-hiding mechanisms are used. Non-transitive ordering of route preferences can occur with interactions between MED and IGP costs, and can also occur with IGP costs if the BGP topology is not aligned with the IGP topology. The common path-hiding mechanism involved in oscillation is iBGP route-reflection. BGP multi-path however also has the potential to hide path information, as it aggregates routes and some, but not all (e.g. not MED) of the metrics.

Operators should satisfy themselves that their topology and configurations will meet their needs when using these features and metrics.


#Multihop EBGP
Multihop EBGP makes it possible to establish a peering session with the application "controller". This allows for ECMP routing or forwarding based on application-defined forwarding paths. This requires recursive resolution of the next-hop address specified in BGP updates to be fully supported.

#OVSDB-Schema
------------
BGP configurations and statistics are stored in the BGP_router, and the BGP_Neighbor tables in OVSDB.
For details refer to the tables/columns in the BGP_feature_design.md at http://www.openswitch.net/documents/dev/ops/docs/BGP_feature_design.md.

BGP uses the following three level hierarchical configuration schema:
-Global BGP router
-BGP peer group
-BGP peer

Lower levels inherit a higher level configuration if a higher level configuration is missing, and the lower level configuration overwrites the higher level configuration if it exists at this level.

##ECMP feature related OVSDB table and column
Table 2 displays multipath parameters related to the OVSDB BGP router.


```ditaa

    ##Table 2 OVSDB BGP router multipath parameters

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


#Internal structure
------------------
##BGP FSM
BGP uses a finite state machine (FSM) to establish a session with its peers.

Figure 2 illustrates the six FSM states and their relationships.

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

There are six FSM states. The first state is "Idle" state. In the "Idle" state. BGP initializes all resources and initiates a TCP connection to the peer.

In the second state or the "Connect" state, the router waits for the TCP connection to complete and transitions to the third state or the "OpenSend" state if the TCP connection is successful.

In the fourth or "OpenSent" state, the router sends an Open message and waits for one in return in order to transition to the fifth or the "OpenConfirm" state.

In the "OpenConfirm" state, keepalive messages are exchanged and, upon a successful receipt of a keepalive message, the router is transferred  to the sixth and last "Established" state.

The "Established"state is the BGP normal operational state.

During the session establishing process, if a pair of BGP speakers try simultaneously to establish a BGP connection with each other, then two parallel connections might be formed. If the source IP address used by one of these connections is the same as the destination IP address used by the other, and the destination IP address used by the first connection is the same as the source IP address used by the other, connection collision has occurred. In the event of connection collision, one of the connections MUST be closed.

If a connection collision occurs with an existing BGP connection that is in Established states, the connection in Established state is preserved and the newly created connection is closed.

If a collision occurs with an existing BGP connection in OpenConfirm or OpenSend state, the BGP Identifier of the local system is compared to the BGP Identifier of the remote system (as specified in the OPEN message), the BGP session with the lower-valued Identifier will be closed.

A connection collision cannot be detected with connections that are in Idle, or Connect, or Active states.


##BGP local RIB
BGP maintains a local routing table (LocRIB), where received routes from all peers are added.

A route established in BGP does not automatically mean that it is used for forwarding. Routes in the local RIB may be advertised to other BGP speakers.

Figure 3 shows the internal data structure of the BGP rib.

Each route is a bgp_node that consists of a prefix, and path attributes organized as bgp_info.


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

##BGP peer
Each BGP speaker is organized as a peer structure. The BGP peer holds all BGP configurations, states, timers, threads, and statistics. It also contains the BGP filter that controls routes received from a peer and routes advertised to a peer. The BGP peer filter consists of distribute, prefix and AS lists, and the route map. The Route map contains match and set operations and it is the technique used to modify BGP route information (Refer to Figure 4).


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

##BGP policy or filter
The I-Filter controls which routes BGP places in the routing tables. The O-Filter controls which routes BGP a dvertises (see Figure 5). The route map is used to change specific route information, and controls which route is selected as the best route to reach the destination.

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

##BGP timer
BGP employs six per-peer timers: ConnectRetryTimer, HoldTimer, KeepaliveTimer, MinASOriginationIntervalTimer, MinRouteAdvertisementIntervalTimer, and GRRestartTimer (see Table 3).


```ditaa

         ##Table 3 BGP important timers

   Timer name            | default | Description
  =======================|=========|======================================
  ConnectRetryTimer      | 120     | Minimum connection retry interval
  HoldTimer              | 180     | Time to wait to declear connection down
  KeepaliveTimer         | 60      | Keepalive timer (1/3 holdtimer)
  AsOriginationTimer     | 15      | Minimum AS origination interval
  RouteAdvertisementTimer| 30/5    | Minimum route advertisement interval
  GRRestartTimer         |         | Maximum wait for session re-establishing

```

Hold Time: The maximum number of seconds that can elapse between the receipt of successive KEEPALIVE or UPDATE messages from the sender. The Hold Time MUST be either zero or at least three seconds.

AS origination time: MinASOriginationIntervalTimer determines the minimum amount of time that must elapse between UPDATE message successive advertisements that report changes within the advertising BGP speaker's own autonomous systems.

Route advertisement time: Two UPDATE messages sent by a BGP speaker to a peer that advertise feasible routes or withdrawal of unfeasible routes to some common set of destinations. These UPDATE messages MUST be separated by at least one MinRouteAdvertisementIntervalTimer.

GR restart time: Restart time is received from restarting a peer previously advertised. If the session does not get re-established within the "Restart Time", the receiving speaker MUST delete all the stale routes from the peer that it is retaining.

#References
----------
* [BGP](https://www.ietf.org/rfc/rfc4271.txt)
* [Quagga](http://www.nongnu.org/quagga/docs.html)
* [OpenSwitch](http://www.openswitch.net/documents/dev/ops-openvswitch/DESIGN)
* [Archtecture](http://www.openswitch.net/documents/user/architecture)
