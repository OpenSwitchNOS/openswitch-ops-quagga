High level design of OPS-ZEBRA
==============================
Quagga Zebra project is integrated as one of the modules in OpenSwitch. To fit Zebra in OpenSwitch architecture, Quagga Zebra is modified to register for Route, Nexthop, Interface and Port table notifications from OVSDB (Open vSwitch Database Management Protocol) and program the best routes and nexthops in the kernel for slow path routing. This document mainly focuses on the role that Zebra plays in the OpenSwitch Architecture and its interaction with other modules. For the details of any other module that participates in refer to corresponding module DESIGN.md.

Responsibilities
----------------
The main responsibility of ops-zebra is to read routes and next-hop configurations from OVSDB and select the best of these active routes and program them in kernel.

Design choices
--------------
Quagga open source project was chosen for layer-3 funcationality in OpenSwitch, and zebra is one of the module in the Quagga project.

Relationships to external OpenSwitch entities
---------------------------------------------
The following diagram (Figure 1) indicates inter-module interaction and Zebra data flow through the OpenSwitch Architecture.

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
OVSDB serves as a central communication hub, all other modules communicate to and from Zebra through OVSDB. OVSDB provides a single view of data to all modules in the system. All modules and OVSDB interact through publisher and subscriber mechanisms. As a result with no direct interaction with other modules, Zebra is shielded from all sorts of failures of other modules in the system.

OPS-ZEBRA
---------
* Zebra subscribes with OVSDB for Routes, Nexthop, Port and Interface table update notification.
* All static and protocol routes are advertised to Zebra through OVSDB.
* Zebra takes all the advertised routes into account and internally decides the set of best next-hops for the routes.
* On selecting/unselecting set of best next-hops for an active route, Zebra creates Forwarding Information Base (FIB) and update the kernel with these routes.
* These selected routes are also communicated to ops-switchd through OVSDB for further programming them in ASIC.
* To handle routes and nexthop deletes, on getting delete notification from OVSDB,  Zebra creates a local hash of current routes and nexthop, and compares them with its local RIB/FIB storage, and removes the deleted ones from its storage and kernel.
* On getting interface up/down notification from OVSDB, Zebra walks through all static routes and next-hops, and which ever is using that interface, it marks them selected/unselected in FIB and updates OVSDB accordingly.
* On getting interface enable/disable of layer-3 funtionality, Zebra walks through all static routes and next-hops, and which ever is using that interface, deletes them from RIB/FIB, kernel and OVSDB.

Static Routes
-------------
Static routes are important in the absence of routing layer3 protocols or when user wishes to override the routes advertised by the routing protocols. User configures the static routes from one of the management interface i.e. CLI, REST etc. which are written to the OVSDB. Static routes has configurable distance and have default distance of 1 (highest prefrence), which is the least distance compared to the routes advertised by the routing protocols. So for the same destination prefix, a static next-hop will be preferred and selected as active route over any other protocol next-hop. Zebra picks the static routes from OVSDB and programs them in kernel.

BGP / Routing Protocols
-----------------------
BGP selects the best routes from all routes it learned and publishes them in OVSDB. Similary other routing protocols update the active routes to OVSDB. Zebra gets these active protocol routes from OSVDB and programs them in the kernel.

Slow-path Routing
-----------------
In OpenSwitch, slow routing refers to instances where the routing happens in the kernel. On selecting/unselecting an active routes, Zebra updates the kernel with these routes. And the kernel  has a copy of all the active routes and neighbors. When a transit packet is received by the kernel,  the destination prefix is looked up in the kernel routing table (Forwarding Information Base, FIB) for the longest match. Once a match is found, the kernel uses information from the route, its nexthop and the corresponding ARP entry to reconstruct the packet and send it to the correct egress interface. OpenSwitch running on a virtual machine always use slow-routing whereas OpenSwitch running on a physical device will use slow routing on need basis when the necessary information is not available in the ASIC for fast routing.

ECMP
----
Equal Cost Multipath routing is a scenario where a single prefix can have multiple "Equal Cost" route nexthops. Zebra accepts static and protocol routes with multiple nexthops and programs them as ECMP routes in kernel. For slowpath, the default Linux kernel ECMP algorithm of load-balancing across all the nexthop will be used. And once the Routes and Nexthops are programmed in ASIC, the configured ASIC ECMP algorithm will be used during fastpath forwarding.
Current version of Zebra support ECMP for ipv4 routes only.

Kernel
------
Kernel receives a copy of FIB and can do slow path forwarding compared to ASIC fast path forwarding.

UI
--
CLI/REST is responsible for configuring ip addresses to a layer-3 interface and providing static routes, which are published in OVSDB and notified to Zebra to be programmed in kernel.

Interface
---------
Zebra address notifications related to configuration and state of interface, up/down state changes, and enabling/disabling of layer-3 on an interface. When an interface goes down, Zebra walks through all routes and nexthops, and which ever is using that interface, it marks them unselected in FIB and updates OVSDB accordingly. And when layer-3 functionality is disabled on an interface, Zebra walks through all routes and next-hops, and which ever is using that interface, deletes them from FIB and kernel and also deletes them from OVSDB.

Inter module data flows
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
The following diagram describes the OVSDB tables related to Zebra.
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

      - 1 Zebra subscribes to Route table and gets notifications for any route configurations.
          Zebra updates the Route selected/unselected column.
      - 2 Zebra subscribes to Nexthop table.
          Zebra updates the Nexthop selected/unselected column.
      - 3 Zebra subscribes to Port table and gets port layer-3 enable/disable configurations.
      - 4 Zebra subscribes to Interface table and gets interface up/down status.
      - 5 Zebra selects best Routes and programs them in kernel

Zebra Table Summary
-------------------
The following list summarizes the purpose of each of the tables in the OpenSwitch database subscribed by Zebra. Some important columns referenced by Zebra from these tabes are described after the summary table.

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

Table 2: Column summary for Interface Table
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

Table 3: Column summary for Nexthop Table
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

Table 4: Column summary for Port Table
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

Table 5: Column summary for RIB (Route) Table
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

Table 6: Column summary for VRF Table
-------------------------------------
```ditaa

    Column           |   Purpose
=====================|==========================================================
     name            |   unique vrf name.
--------------------------------------------------------------------------------
     ports           |   set of Ports pariticipating in this VRF.
---------------------|----------------------------------------------------------
```

References
----------
* [Reference 3 OpenSwitch Archiecture](http://www.openswitch.net/documents/user/architecture)
* [Reference 1 Quagga Documents](http://www.nongnu.org/quagga/docs.html)
* [Reference 2 OpenSwitch L3 Archiecture](http://git.openswitch.net/cgit/openswitch/ops/tree/docs/layer3_design.md)
