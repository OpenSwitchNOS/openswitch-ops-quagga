High level design of OPS-ZEBRA
==============================
The Zebra module from Quagga project is integrated as one of the modules in OpenSwitch. To fit Zebra in the OpenSwitch architecture, Quagga Zebra is modified to register for route, next hop, interface, and port table notifications from the OVSDB and also program the best routes and next hops in the kernel for slow path routing. This document mainly focuses on the role that Zebra plays in the OpenSwitch architecture and its interaction with other modules. For the details of any other module that participates in, refer to corresponding module DESIGN.md page

Responsibilities
----------------
The main responsibility of ops-zebra is to read routes and next hop configurations from the OVSDB and select the active routes and program them into the kernel.

Design choices
--------------
The Quagga open source project was chosen for layer-3 functionality in OpenSwitch, and zebra is one of the modules in the Quagga project.

Relationships to external OpenSwitch entities
---------------------------------------------
Figure 1 indicates the intermodule interaction and Zebra data flow through the OpenSwitch architecture.

```ditaa
    +------------------------+  +---------------------------+
    |  Management Daemons    |  |   Routing Protocol        |
    |  (CLI, REST, etc.)     |  |       Daemons             |
    |                        |  |   (BGP, OSPF etc.)        |
    |                        |  |                           |
    +------------------------+  +------------+--------------+
    L3 Interfaces|               Protocol    |
    Static Routes|               Routes      |
                 |                           |
    +------------v---------------------------v---------------+
    |                                                        |
    |                        OVSDB                           |
    |                                                        |
    +----------------^---------------------------------+-----+
         Routes/     |                                 |
         Port/Intf.  |                           Routes|Intf.
         Config/Stat |                           Nbr.  |
                     |                                 |
               +-----v-----+                     +-----v------+
               |           |                     |            |
               | ops-zebra |                     | ops-switchd|
               |           |                     |            |
               +-----------+                     +-----^------+
                Route|                                 |
                     |                                 |
    +----------------v------------------------+  +-----v-----+
    |                                         |  |           |
    |                 Kernel                  <--+   ASIC    |
    |               (SlowPath)                |  | (FastPath)|
    +-----------------------------------------+  +-----------+
                  Figure 1, ZEBRA Architecture
```

OVSDB
-----
OVSDB serves as a central communication hub. All other modules communicate from and to Zebra through the OVSDB.
The OVSDB provides a single view of data to all modules in the system. All modules and the OVSDB interact through publisher and subscriber mechanisms. As a result with no direct interaction with other rmodules, Zebra is shielded from all sorts of other module issues in the system.

OPS-ZEBRA
---------
* Zebra subscribes to the OVSDB for routes, next hop, port and interface table update notifications.
* All static and protocol routes are advertised to Zebra through the OVSDB.
* Zebra takes all the advertised routes into account and internally decides the best as the active routes and set of best next hops for the routes.
* When selecting or unselecting the set of best next hops for an active route, Zebra creates a Forwarding Infor mation Base (FIB) and updates the kernel with these routes.
* These selected routes are also communicated to ops-switchd through the OVSDB for further programming in ASIC.
* To handle routes and next hop deletes when getting delete notification from the OVSDB, Zebra creates a local hash of current routes and next hops, and compares them with its local RIB/FIB storage. It also removes the deleted routes from its storage and kernel.
* On getting interface up/down notification from OVSDB, Zebra walks through all the static routes and next hops, marks them selected or unselected in the FIB, and updates the OVSDB accordingly.
* On getting interface enable/disable of layer-3 funtionality, Zebra walks through all the static routes and next hops, deletes them from the FIB, the kernel, and the OVSDB.

Static routes
-------------
Static routes are important in the absence of routing layer3 protocols or when there is a need to override the routes advertised by the routing protocols.
When the static routes are configured using one of the management interfaces such as the CLI or the REST, this information is written to the OVSDB.
A static route has a configurable distance and has a default distance of 1 (highest preference), which is the least distance compared to the routes advertised by the routing protocols. So for the same destination prefix, a static next hop is preferred and selected as an active route over any other protocol next hop. Zebra picks the static routes from the OVSDB and programs them into the kernel.

BGP / Routing protocols
-----------------------
BGP selects the best routes from all routes and publishes them in the OVSDB. Similary other routing protocols update the active routes in the OVSDB. Zebra gets these active protocol routes from OSVDB and programs them into the kernel.

Slow-path routing
-----------------
In OpenSwitch, slow routing refers to instances where the routing happens in the kernel. On selecting or unselecting active routes, Zebra updates the kernel with these routes.
The kernel has a copy of all the active routes and neighbors. When a transit packet is received by the kernel, the destination prefix is accessed in the kernel routing table (Forwarding Information Base, FIB) for the longest match. Once a match is found, the kernel uses the information from the route, its next hop and the corresponding ARP entry to reconstruct the packet and send it to the correct egress interface.
OpenSwitch running on a virtual machine always uses slow routing, whereas OpenSwitch running on a physical device uses slow routing on an as-needed basis when the necessary fast routing information is not available in the ASIC.

ECMP
----
Equal Cost Multipath routing is a scenario where a single prefix can have multiple "Equal Cost" route next hops. Zebra accepts static and protocol routes with multiple next hops and programs them as ECMP routes in the kernel.
For slow path routing, the default Linux kernel ECMP algorithm of load-balancing across all the next hops is used. And once the routes and next hops are programmed in ASIC, the configured ASIC ECMP algorithm is used during fast path forwarding.

The current version of Zebra supports ECMP for ipv4 routes only.

Kernel
------
The kernel receives a copy of FIB and can perform slow path forwarding compared to ASIC fast path forwarding.

UI
--
The CLI or REST is responsible for configuring IP addresses in a layer-3 interface and providing static rou tes, which are published in the OVSDB and then Zebra is notified to program the IP addresses and static routes in the kernel.

Interface
---------
Zebra gets notifications related to interface configurations, up or down state changes, and enabling or disabling of a layer-3 network on an interface.
When an interface goes down, Zebra walks through all the routes and next hops and it marks whatever routes or next hops using that interface, unselected in FIB and updates the OVSDB accordingly. And when layer-3 functionality is disabled on an interface, Zebra walks through all routes and next-hops, and deletes whatever routes or next hops using that interface, from the FIB, the kernel, and the OVSDB.

Intermodule data flows
-----------------------
Input to Zebra:
---------------
```ditaa
    - Static Routes Configurations:       UI---->OVSDB---->Zebra
    - Port/Interface ip addr/up/down:     UI/Intfd/Portd---> OVSDB ----> Zebra
    - Protocol routes:                    BGP ---> OVSDB --->Zebra
```

Zebra output:
-------------
```ditaa
    - Best routes:                        Zebra ----> kernel
                                                |
                                                ----> OVSDB
    - show rib/route                      OVSDB ---> UI
```

OVSDB-Schema related to Zebra
-----------------------------------
The following Figure 2 describes the OVSDB tables related to Zebra.
```ditaa
    +-----------+
    |  +----+   |         +------+
    |  |VRF |   |         |  O   |
    |  |    |   |         |      |
    |  +-^--+   |         |  P   |         +-----+
    |    |      |         |      |         |     |
    |  +-+--+   |         |  S   |         |  K  |
    |  |Route   + 1       |      |         |     |
    |  |(RIB/FIB)<-------->  |   |         |  E  |
    |  +-+--+   +         |      |         |     |
    |    |      |         |  Z   | 5       |  R  |
    |  +-v--+   |         |      +--------->     |
    |  |Nexthop | 2       |  E   |         |  N  |
    |  |    +------------->      |         |     |
    |  +--+-+   |         |  B   |         |  E  |
    |     |     |         |      |         |     |
    |  +--v-+   +         |  R   |         |  L  |
    |  |Port|     3       |      |         +-----+
    |  |    +---+--------->  A   |
    |  +--+-+   |         |      |
    |     |     |         |      |
    |  +--v-+   +         | (RIB/|
    |  |Interface 4       |  FIB)|
    |  |    +---+--------->      |
    |  +----+   |         +------+
    +-----------+
              Figure 2 Zebra and OVSDB tables
```

Zebra performs the following tasks:
-Subscribes to the route table and gets notifications for any route configurations.
-Updates the route selected or unselected column.
-Subscribes to the next hop table and updates the next hop selected or unselected column.
-Subscribes to the port table and gets port layer-3 enabled or disabled configurations.
-Subscribes to the interface table and gets the interface up or down status.
-Selects the best routes and programs them into the kernel.

Zebra table summary
-------------------
The following list summarizes the purpose of each of the tables in the OpenSwitch database subscribed by Zebra. Some important columns referenced by Zebra from these tables are described after the summary table.

Table 1: Table summary
----------------------
```ditaa

    Table        |  Purpose
=================|==============================================================
    Interface    |  Interface referred by a Port.
    Nexthop      |  Nexthops for IP routes, either ip address or out going interface.
    Port         |  Port within an VRF, If  port has an IP address, then it becomes L3.
    RIB/FIB      |  Routing Information Base and Forwarding Information Base.
    VRF          |  Virtual Routing and Forwarding domain.
-----------------|--------------------------------------------------------------
```

Table 2: Column summary for interface table
-------------------------------------------
```ditaa

    Column           |   Purpose
=====================|==========================================================
    name             |   Unique name of Interface
---------------------|----------------------------------------------------------
    type             |   System/Internal
---------------------|----------------------------------------------------------
    admin_state      |   Up/Down
---------------------|----------------------------------------------------------
    link_state       |   Up/Down
---------------------|----------------------------------------------------------
```

Table 3: Column summary for nexthop table
------------------------------------------
```ditaa

    Column           |   Purpose
=====================|==========================================================
    ip_address       |   Nexthop ip address
---------------------|----------------------------------------------------------
    type             |   Nexthop type  (unicast, multicast, indirect etc)
---------------------|----------------------------------------------------------
    port             |   Reference to Port table entry, if nexthop is via an port
  ---------------------|--------------------------------------------------------
    selected         |   Active nexthop
---------------------|----------------------------------------------------------
```

Table 4: Column summary for port table
------------------------------------------
```ditaa

    Column           |   Purpose
=====================|==========================================================
    name             |   Unique name of port.
---------------------|----------------------------------------------------------
    interfaces       |   References to Interface Table
---------------------|----------------------------------------------------------
    ip4_address      |   port IPv4 address
---------------------|----------------------------------------------------------
    ip6_address      |   port IPv6 address
---------------------|----------------------------------------------------------
    ip4_address_     |   port IPv4 secondary addresses
    secondary        |
---------------------|----------------------------------------------------------
    ip6_address_     |   port IPv6 secondary addresses
    secondary        |
---------------------|----------------------------------------------------------

```

Table 5: Column summary for route table (RIB)
---------------------------------------------
```ditaa

    Column             |   Purpose
=======================|========================================================
    vrf                |   Back pointer to vrf table that this rib belong to.
-----------------------|--------------------------------------------------------
    prefix             |   Prefix/len
-----------------------|--------------------------------------------------------
    from               |   Which protocol this prefix learned
-----------------------|--------------------------------------------------------
    address_family     |   IPv4, IPv6
-----------------------|--------------------------------------------------------
    sub_address_family |   Unicast, multicast
-----------------------|--------------------------------------------------------
    distance           |   Administrative preference of this route
-----------------------|--------------------------------------------------------
                       |   n_nexthops: count of nh
    nexthops           |   Array of pointer to next hop table row
-----------------------|--------------------------------------------------------
    selected           |   Active route
-----------------------|--------------------------------------------------------
```

Table 6: Column summary for vrf table
-------------------------------------
```ditaa

    Column           |   Purpose
=====================|==========================================================
     name            |   unique vrf name.
--------------------------------------------------------------------------------
     ports           |   set of Ports pariticipating in this VRF.
---------------------|----------------------------------------------------------
```

Zebra debugging
--------------------
ovs-appctl command can be used to enable different levels of debug in ops-zebra daemon.
Sample: ovs-appctl -t ops-zebra vlog/set dbg.

Apart from standard appctl debug levels, appctl can also be used with zebra/debug
option to enable various existing debug level in zebra.

The bash command to look at the help string for the zebra debug options is:
"ovs-appctl -t ops-zebra list-commands"

The output of the command contains the following line:
zebra/debug           event|packet|send|recv|detail|kernel|rib|ribq|fpm|all|show

One example of using the command to set the zebra kernel debugs is :
"ovs-appctl -t ops-zebra zebra/debug kernel"

References
----------
* [Reference 3 OpenSwitch Archiecture](http://www.openswitch.net/documents/user/architecture)
* [Reference 1 Quagga Documents](http://www.nongnu.org/quagga)
* [Reference 2 OpenSwitch L3 Archiecture](http://git.openswitch.net/cgit/openswitch/ops/tree/docs/layer3_design.md)
