#Overview of ZEBRA in OpenSwitch Architecture
OpenSwitch is designed to achieve aggressive modularization, high availability, portability, extensi bility, and reuse of open source projects. Quagga Zebra project is integrated as one of the modules in OpenSwitch. Zebra provide the interface to update routes from OVSDB (Open vSwitch Database Management Protocol) to kernel for slow path. This document mainly focuses on the role that Zebra plays in the OpenSwitch Architecture and its interaction with other modules. For the details of any other module that participates in refer to corresponding module DESIGN.md.

#Participating Modules and Data Flow
The following diagram (Figure 1) indicates inter module communications and Zebra data flow through the OpenSwitch Architecture.

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
+---------------^----------------------------------+-----+
     Routes/    ||                                 |
     Port/Intf. ||                           Routes|Intf.
     Config/Stat||                           Nbr.  |
                ||                                 |
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

##OVSDB
OVSDB serves as a central communication hub, all other modules communicate to and from Zebra through OVSDB indirectly. OVSDB provides a single view of data to all modules in the system. All modules and OVSDB interact through publisher and subscriber mechanisms. As a result with no direct interaction with other modules, Zebra is shielded from all sorts of failures of other modules in the system.

##OPS-ZEBRA
All static and protocol routes are advertised to Zebra through OVSDB. Zebra takes all the advertised routes into account and internally decides best routes which of those routes will be programmed to the kernel. On selecting/unselecting an active route, Zebra creates FIB and update the kernel with these routes. This selected routes are also communicated to ops-vswitchd through OVSDB for further programming these routes to the ASIC.

##Static Routes
User configures the static routes from one of the management daemons i.e. CLI, REST etc. which are written to the OVSDB. Static routes are important in the absence of routing layer3 protocols or when user wishes to override the routes advertised by the routing protocols. Static routes have the least distance (highest priority) compared to the routes advertised by the routing protocols. So for the same destination prefix, a static route will be preferred (and selected as active route )over any other protocol route. Zebra picks these static routes from OVSDB and programs them in kernel.

##BGP
BGP is an exterior gateway protocol (EGP) that is desinged to exchange routing information among routers in different autonomous systems (AS). BGP upates the routes it learned to OVSDB and Zebra picks them up and program them in the kernel.

##Slow-path Routing
In OpenSwitch, slow routing refers to instances where the routing happens in the kernel. On selecting/unselecting an active route, Zebra updates the kernel with these routes. And the kernel  has a copy of all the active routes and neighbors. When a transit packet is received by the kernel,  the destination prefix is looked up in the kernel routing table (Forwarding Information Base, FIB) for the longest match. Once a match is found, the kernel uses information from the route nexthop and the corresponding ARP entry to reconstruct the packet and send it to the correct egress interface. OpenSwitch running on a virtual machine always use slow-routing whereas OpenSwitch running on a physical device will use slow routing on need basis when the necessary information is not available in the ASIC for fast routing.

##ECMP
Equal Cost Multipath is a scenario where a single prefix can have multiple "Equal Cost" route nexthops. Zebra accepts static and protocol routes with multiple nexthops and program them as ECMP routes in kernel. For slowpath, the default Linux kernel ECMP algorithm of load-balancing across all the nexthop will be used. And once the Routes and Nexthops are programmed in ASIC, the configured ASIC ECMP algorithm will be used during fastpath forwarding.
Current version of Zebra support ECMP for ipv4 routes only.

##Kernel
Kernel receives a copy of FIB and can do slow path forwarding compared to ASIC fast path forwarding.

##UI
CLI/REST is responsible for configuring ip addresses to a Layer 3 interface and providing static routes. Which are published in OVSDB and notified to Zebra to be programmed in kernel.

##Interface
Zebra address notifications related to configuration and state of interface, up/down state changes, and enabling/disabling of Layer 3 on an interface. When an interface goes down Zebra walks through all routes and there nexthops, and which ever is using that interface, it marks them unselected in FIB and updates OVSDB accordingly. And when interface disabled with Layer 3, Zebra walks through all routes and next hops, and delete them from FIB and kernel and update OVSDB.

##Inter module data flows
###Input to Zebra:
```ditaa
    - Static Routes Configurations:       UI---->OVSDB---->Zebra
    - Port/Interface ip addr/up/down:     UI/Intfd/Portd---> OVSDB ----> Zebra
    - Protocol routes:                    BGP ---> OVSDB --->Zebra
```
###Zebra output:
```ditaa
    - Best routes:                        Zebra ----> kernel
                                                |
                                                ----> OVSDB
    - show rib/route                      OVSDB ---> UI
```

#OVSDB-Schema related to Zebra
Zebra configurations come from OVSDB. UI and routing protocols writes configurations to OVSDB.  Route table has all these route configurations. And an prefix entery in Route table points to an entry in Neighbor table which can be either ip address on out going interface. Zebra subscribes to OVSDB for notification for these tables, whenever there is a new configuration or configuration changes, Zebra gets notification, and pickups the new configurations, and then programs Zebra local RIB/FIB and picks up the best routes and porgrams them in kernel. When Zebra selects the best route it also mark that route in Route as selected. Apart from Routes, Zebra also registers for notification on Interface and Port table. For any interface status change, and if the interface goes down/up it marks the route/nexthop referring that interface as unslected / selected in OVSDB. And for port disable/enable of layer 3, Zebra deletes the route/nexthop refering that port.

## Zebra and OVSDB table relationships
The following diagram describes the interaction between Zebra and OVSDB tables
```ditaa
+-----------+
|  +----+   |         +------+
|  |VRF |   |         |      |
|  |    |   |         |      |
|  +-^--+   |         |  Z   |         +-----+
|    |      |         |      |         |     |
|  +-+--+   |         |  E   |         |  K  |
|  |Route   + 1       |      |         |     |
|  |(RIB/FIB)<-------->  B   |         |  E  |
|  +-+--+   +         |      |         |     |
|    |      |         |  R   | 5       |  R  |
|  +-v--+   |         |      +--------->     |
|  |Nexthop | 2       |  A   |         |  N  |
|  |    +------------->      |         |     |
|  +--+-+   |         | (RIB/|         |  E  |
|     |     |         |  FIB)|         |     |
|  +--v-+   +         |      |         |  L  |
|  |Port|     3       |      |         +-----+
|  |    +---+--------->      |
|  +--+-+   |         |      |
|     |     |         |      |
|  +--v-+   +         |      |
|  |Interface 4       |      |
|  |    +---+--------->      |
|  +----+   |         +------+
+-----------+
              Figure 2 Zebra and OVSDB tables
```

      - 1 Zebra subscribs to Route table and gets notifications for any route configurations.
          Zebra updates the Route selected/unselected column.
      - 2 Zebra subscribs to Nexthop table.
          Zebra updates the Nexthop selected/unselected column.
      - 3 Zebra subscribs to Port table and gets port layer 3 enable/disable configurations.
      - 4 Zebra subscribs to Interface table and gets interface up/down status.
      - 5 Zebra selects best Routes and programs them in kernel

##TABLE SUMMARY
The following list summarizes the purpose of each of the tables in the OpenSwitch database subscribed by Zebra. Some important columns referenced by Zebra from these tabes are described after the summary table.

###Table 1: Table summary
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

###Table 2: Column SUMMARY for Interface Table
An interface within a Port.
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
###Table 3: Column SUMMARY for Nexthop Table
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

###Table 13: Column SUMMARY for Port Table

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

```

###Table 4: Column SUMMARY for RIB (Route) Table
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

###Table 6: Column SUMMARY for VRF Table
```ditaa

    Column           |   Purpose        288
=====================|==========================================================
     name            |   unique vrf name.
--------------------------------------------------------------------------------
     ports           |   set of Ports pariticipating in this VRF.
---------------------|----------------------------------------------------------
```

#References
-----------
* [Reference 3 OpenSwitch Archiecture](http://www.openswitch.net/documents/user/architecture)
* [Reference 1 Quagga Documents](http://www.nongnu.org/quagga/docs.html)
* [Reference 2 OpenSwitch L3 Archiecture](https://www.openswitch.net/documents/user/)
* [Reference 4 OpenSwitch L3 User Guide](https://www.openswitch.net/documents/)
