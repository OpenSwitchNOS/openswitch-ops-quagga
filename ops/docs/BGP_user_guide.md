## BGP ##
**BGP** (Border Gateway Protocol) is most commonly used **inter-AS** (autonomous system) routing protocol. The latest BGP version is 4. **BGP-4** supports Classless Inter-Domain Routing (CIDR) i.e. advertises the routes based on destinations as an IP prefix and not the network/class.
## Overview ##
BGP is **path-vector** protocol which provides routing information across various BGP routers to be exchanged using destination-based forwarding i.e. router sends packets based merely on destination IP address carried in the IP header of the packet. In most cases, we have multiple routes to the same destination then BGP decides which route to choose using path attributes, for e.g. *"Shortest AS_Path"*, *"Multi_Exit_Disc (Multi-exit discriminator, or MED)"*,*"Origin attribute"*, etc.
## How to use the feature ##

BGP provides routing for routers/switches that can be deployed in ISP, Enterprise and data centers.

## Setting up the basic configuration ##
Following is the minimum configuration needed to setup the BGP router. AS number is unique to the Autonomous system and is used to distinguish between internal/external BGP connections.

> router bgp < asn >

Enable **BGP router** for given AS number. AS numbers ranges from 1-65535.

> 	bgp router-id A.B.C.D

Specifies **BGP router-ID**. When not configured with above command *bgpd* gets the interface and address information from *zebra*. In this case, the default router-ID value is largest interface address. If *zebra* router is not enabled, set the *bgpd* router-ID.  By default, the router-ID is set to **0.0.0.0**.

> 	no router bgp < asn >

Disable the BGP process with given AS number.

## Setting up the optional configuration ##
**BGP Router**

> maximum-paths < paths >

Limits the maximum number of paths for BGP. When global ECMP is enabled and BGP maximum-paths is set greater than zebra maximum-paths, then, zebra overrides BGP maximum-paths. When global ECMP is disabled then only single best path gets selected by zebra.
>no  maximum-paths

When unset, defaults maximum-paths as "1".

> timers bgp < keepalive > < holdtime >

Sets the keep-alive and hold-time timers for BGP router.

>no timers bgp < keepalive > < holdtime >

Defaults the keep-alive and hold-time timers for BGP router. Sets keep-alive to 180 seconds and hold-time to 60 seconds.

Note: All BGP commands should be executed under **"router bgp < asn >"** context.

**BGP Network**

BGP network adds a static network to BGP routing table.

> network A.B.C.D/M

Announces the specified network to all peers in the AS.

> no network A.B.C.D/M

Deletes the specified network announcement from all neighbor's routing tables.

**BGP Peer**

Following  are the neighbor configuration commands.

> neighbor peer remote-as asn

Defines a new peer with remote-as as *asn*. *peer* is IPv4 address. If remote-as is not configured, *bgpd* throws an error as *"can’t find neighbor peer"*.

>no neighbor peer remote-as asn

Deletes the peer.
> neighbor peer description < some_description >

Sets the description for BGP peer.

>no  neighbor peer description < some_description >

Deletes the neighbor description info.
> neighbor peer password < some_password >

Enables MD5 authentication on TCP connection between BGP peers.
> no neighbor peer password < some_password >

Disables MD5 authentication on TCP connection between BGP peers.

> neighbor peer timers < keepalive > < holdtimer >

Sets the keep-alive and hold-time for a specific BGP peer.

> no neighbor peer timers < keepalive > < holdtimer >

Clears the keep-alive and hold-time for a specific BGP peer.

> neighbor peer allowas-in < ASN_instances_allowed >

Specifies the number of times BGP allows an instance of AS to be in the AS_PATH.

> no neighbor peer allowas-in < ASN_instances_allowed >

Removes the number of times BGP allows an instance of AS to be in the AS_PATH. Range is 1-10.

> neighbor peer remove-private-AS

Removes private AS numbers from the AS path in outbound routing updates.

> no neighbor peer remove-private-AS

Allows the private AS numbers from the AS path in outbound routing updates.

> neighbor peer soft-reconfiguration inbound

Enables software-based reconfiguration to generate inbound updates from a neighbor without clearing the BGP session.

**BGP Peer-Group**

Peer-group is a collection of peers which shares same outbound policy. Neighbors belonging to the same peer-group might have different inbound policies.
> neighbor *word* peer-group

Defines a new peer-group. *word* is name of the peer-group.

> neighbor peer peer-group word

Binds a specific peer to the peer-group provided.

Note: All peer commands are applicable to peer-group as well.

**Peer filtering**

 - **Route Map**

	>  route-map *word* (deny|permit) < sequence_num >

	Configures a route map for given sequence number. *word* is route_map name. *sequence_num* ranges  between 1-65535.

	> neighbor peer route-map *word* in|out

	Assigns the route map to the peer for given direction.

	> description < some_route_map_description >

	Allows to add route map description.

	> set community .AA:NN additive

	Assigns or changes community for route map.

	>  set metric <0-4294967295>

	Sets/changes metric for route map.

 - **IP Prefix List**

	> ip prefix-list *word* seq <1-4294967295> (deny|permit) (A.B.C.D/M|any)

	Configures the ip prefix-list for given route map.

	>  match ip address prefix-list *word*

	Configure route map for match on given IP_address.

## Verifying the configuration ##
Verification of configuration can be done using **"show running-config".** All active configs should be available in the show running-config. Please see the sample output below:

> s1# show running-config
> Current configuration:
!
ip prefix-list BGP1 seq 5 permit 11.0.0.0/8
ip prefix-list BGP1 seq 6 deny 12.0.0.0/8
!
route-map BGP2 permit 5
     description tsting route map description
     match ip address prefix-list bgp1
     set community 123:345 additive
     set metric 1000
!
router bgp 6001
     bgp router-id 9.0.0.1
     network 11.0.0.0/8
     maximum-paths 5
     timers bgp 3 10
     neighbor openswitch peer-group
     neighbor 9.0.0.2 remote-as 2
     neighbor 9.0.0.2 description abcd
     neighbor 9.0.0.2 password abcdef
     neighbor 9.0.0.2 timers 3 10
     neighbor 9.0.0.2 route-map BGP2 in
     neighbor 9.0.0.2 route-map BGP2 out
     neighbor 9.0.0.2 allowas-in 7
     neighbor 9.0.0.2 remove-private-AS
     neighbor 9.0.0.2 soft-reconfiguration inbound
     neighbor 9.0.0.2 peer-group openswitch
!

## Troubleshooting the configuration ##

All the logs are logged into **/var/log/messages**. Debug logs can be enabled by adding following line to *"build/conf/local.conf"*.

> EXTRA_IMAGE_FEATURES = "dbg-pkgs"

To enable debug logs at daemon level, change  vlog level of *"yocto/openswitch/meta-distro-openswitch/recipes-ops/l3/ops-quagga/bgpd.service"* from **INFO** to **DBG**  as shown:

> ExecStart=/sbin/ip netns exec swns /usr/sbin/bgpd --detach --pidfile -vSYSLOG:**DBG**

Following are the commands to verify the BGP route related information.
> **s2# show ip bgp**
Status codes: s suppressed, d damped, h history, * valid, > best, = multipath,
              i internal, S Stale, R Removed
Origin codes: i - IGP, e - EGP, ? - incomplete
Local router-id 9.0.0.2
   Network           Next Hop            Metric LocPrf Weight Path
*> 11.0.0.0/8       9.0.0.1                  0      0      0 1 i
*> 12.0.0.0/8       0.0.0.0                  0      0  32768  i
Total number of entries 2

> **s2# show ip bgp 11.0.0.0/8**
BGP routing table entry for 11.0.0.0/8
Paths: (1 available, best #1)
AS: 1
    9.0.0.1 from 9.0.0.1
      Origin IGP, metric 0, localpref 0, weight 0, valid, external, best
      Last update: Thu Sep 24 22:45:52 2015

>**s2# show ip bgp summary**
BGP router identifier 9.0.0.2, local AS number 2
RIB entries 2
Peers 1
Neighbor             AS MsgRcvd MsgSent Up/Down  State

> **s2# show ip bgp neighbors**
  name: 9.0.0.1, remote-as: 1
    state: Established
    description: abcd
    password: abcd
    tcp_port_number: 179
    statistics:
       bgp_peer_dropped_count: 1
       bgp_peer_dynamic_cap_in_count: 0
       bgp_peer_dynamic_cap_out_count: 0
       bgp_peer_established_count: 1
       bgp_peer_keepalive_in_count: 3
       bgp_peer_keepalive_out_count: 4
       bgp_peer_notify_in_count: 0
       bgp_peer_notify_out_count: 1
       bgp_peer_open_in_count: 1
       bgp_peer_open_out_count: 1
       bgp_peer_readtime: 25066
       bgp_peer_refresh_in_count: 0
       bgp_peer_refresh_out_count: 0
       bgp_peer_resettime: 25101
       bgp_peer_update_in_count: 2
       bgp_peer_update_out_count: 2
       bgp_peer_uptime: 25101
