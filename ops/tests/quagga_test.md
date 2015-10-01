# Quagga Test Cases

## Contents

- [Zebra update](#zebra-update)
- [Topology with ecmp routes](#topology-with-ecmp-routes)
- [BGP Maximum Paths](#bgp-maximum-paths)
- [BGP Network Configuration](#bgp-network-configuration)
- [BGP Neighbor Route-Map](#bgp-neighbor-route-map)
- [Router BGP Configuration](#router-bgp-configuration)
- [BGP Router-ID Configuration](#bgp-router-id-configuration)
- [Show BGP Neighbors](#show-bgp-neighbors)
- [Show IP BGP](#show-ip-bgp)
- [BGP Show Running Config](#bgp-show-running-config)
- [Timers BGP Configuration](#timers-bgp-configuration)

##  Zebra update
### Objective
Test case verifies zebra update of selected column in DB when static routes are added.

### Requirements
- Virtual Mininet Test Setup
- **CT File**: ops-quagga/zebra/test\_zebra\_ct\_fib\_selection.py (Route Table Update)

### Setup
#### Topology Diagram
```ditaa
  +------+              +------+
  |      |              |      |
  |  S1  +------------> |  S2  |
  |      |              |      |
  +------+              +------+
```

### Description
1. Use the 2 switch, 2 host topology
2. Add the static routes on the 2 switches to be able to reach the end hosts
3. Configure the end hosts with valid IP addresses
4. Dump the route table in the db using `ovsdb-client dump`

### Test Result Criteria
#### Test Pass Criteria
Verify that the selected column in the Route table for the rows with static routes are set to **true**

#### Test Fail Criteria

##  Topology with ecmp routes
### Objective
Test case checks for connectivity in topology with 3 host and 4 switches

### Requirements
- Virtual Mininet Test Setup
- **CT File**: ops-quagga/zebra/test\_zebra\_ct\_ecmp.py

### Setup

#### Topology Diagram
```ditaa
    10.0.10.1/24  10.0.10.2/24  10.0.30.1/24 10.0.30.2/24  10.0.70.2/24
    +-----------+      +---------------+          +------------+
    |           |      |               |          |            |
    |           |      |               |          |            |      10.0.70.1/24
    |           |      |               |          |            |      +----------+
    |   Host 1  +------+               |          |            |      |          |
    |           |      |               |          |            |      |          |
    |           |      |               +----------+            |      |          |
    |           |      |               |          |            |      |          |
    +-----------+      |               |          |            |      |  Host 3  |
                       |   Switch 1    |          |  Switch 2  |      |          |
                       |               |          |            +------+          |
                       |               |          |            |      |          |
                       |               |          |            |      |          |
    +-----------+      |               |          |            |      |          |
    |           |      |               |          |            |      +----------+
    |           |      |               +----------+            |
    |           |      |               |          |            |
    |  Host 2   +------+               |          |            |
    |           |      |               |          |            |
    |           |      |               |          |            |
    |           |      |               |          |            |
    +-----------+      +---------------+          +------------+
    10.0.20.1/24  10.0.20.2/24  10.0.40.1/24       10.0.40.2/24
```

### Description
1. Create a topology with 3 host and 4 switches
2. Switch 1 having ecmp route with one nexthop going to  sw2 and second going to sw3
3. Switch 4 having two ecmp routes, 1st ecmp route for 10.0.10.1 with nexthop going through sw2 and sw3, and another ecmp route for 10.0.20.1 going through sw2 and sw3
4. ping host3 10.0.70.1 from host 1
5. ping host3 from host 2

### Test Result Criteria

#### Test Pass Criteria
* When pinging host3 from host1 3 the kernel will load balance pings because of ecmp route with 2 nexthop, one via s2 and another one via s3
* Similarly when pinging host3 from host2

#### Test Fail Criteria


## BGP Maximum Paths ##
### Objective ###
The test case verifies **maximum-paths** and **no maximum-paths** by configuring three different paths to the same switch.

### Requirements ###

- Physical/Virtual Switches

### Setup ###
#### Topology Diagram ####

```ditaa
                          +----------------+
                          |                |
                          |                |
             +------------+    Switch 1    +-------------+
             |            |                |             |
             |            |                |             |
             |            +--------+-------+             |
             |                     |                     |
             |                     |                     |
    +--------+-------+    +--------+-------+    +--------+-------+
    |                |    |                |    |                |
    |                |    |                |    |                |
    |    Switch 2    |    |    Switch 3    |    |    Switch 4    |
    |                |    |                |    |                |
    |                |    |                |    |                |
    +--------+-------+    +--------+-------+    +--------+-------+
             |                     |                     |
             |                     |                     |
             |            +--------+-------+             |
             |            |                |             |
             |            |                |             |
             +------------+    Switch 5    +-------------+
                          |                |
                          |                |
                          +----------------+

```

#### Test Setup ####
**Switch 1** is configured with:

    !
    interface 3
        no shutdown
        ip address 30.30.30.1/8
    interface 1
        no shutdown
        ip address 10.10.10.1/8
    interface 2
        no shutdown
        ip address 20.20.20.1/8
    !
    router bgp 1
        bgp router-id 9.0.0.1
        network 11.0.0.0/8
        maximum-paths 5
        neighbor 10.10.10.2 remote-as 2
        neighbor 20.20.20.2 remote-as 3
        neighbor 30.30.30.2 remote-as 4

**Switch 2** is configured with:

    !
    interface 1
        no shutdown
        ip address 10.10.10.2/8
    interface 2
        no shutdown
        ip address 40.40.40.1/8
    !
    router bgp 2
        bgp router-id 9.0.0.2
        neighbor 10.10.10.1 remote-as 1
        neighbor 40.40.40.2 remote-as 5

**Switch 3** is configured with:

    !
    interface 1
        no shutdown
        ip address 20.20.20.2/8
    interface 2
        no shutdown
        ip address 50.50.50.1/8
    !
    router bgp 3
        bgp router-id 9.0.0.3
        neighbor 20.20.20.1 remote-as 1
        neighbor 50.50.50.2 remote-as 5

**Switch 4** is configured with:

    !
    interface 1
        no shutdown
        ip address 30.30.30.2/8
    interface 2
        no shutdown
        ip address 60.60.60.1/8
    !
    router bgp 4
        bgp router-id 9.0.0.4
        neighbor 30.30.30.1 remote-as 1
        neighbor 60.60.60.2 remote-as 5

**Switch 5** is configured with:

    !
    interface 1
        no shutdown
        ip address 40.40.40.2/8
    interface 2
        no shutdown
        ip address 50.50.50.2/8
    interface 3
        no shutdown
        ip address 60.60.60.2/8
    !
    router bgp 5
        bgp router-id 9.0.0.5
        network 12.0.0.0/8
        neighbor 40.40.40.1 remote-as 2
        neighbor 50.50.50.1 remote-as 3
        neighbor 60.60.60.1 remote-as 4

### Description ###

1. Configure the IP addresses on all switches in **vtysh** with the following commands:

    ***Switch 1***

    ```
    configure terminal
    interface 1
    no shutdown
    ip address 10.10.10.1/8
    interface 2
    no shutdown
    ip address 20.20.20.1/8
    interface 3
    no shutdown
    ip address 30.30.30.1/8
    ```

    ***Switch 2***

    ```
    configure terminal
    interface 1
    no shutdown
    ip address 10.10.10.2/8
    interface 2
    no shutdown
    ip address 40.40.40.1/8
    ```

    ***Switch 3***

    ```
    configure terminal
    interface 1
    no shutdown
    no shutdown
    ip address 20.20.20.2/8
    no shutdown
    ip address 50.50.50.1/8
    ```

    ***Switch 4***

    ```
    configure terminal
    interface 1
    no shutdown
    ip address 30.30.30.2/8
    interface 2
    no shutdown
    ip address 60.60.60.1/8
    ```

    ***Switch 5***

    ```
    configure terminal
    interface 1
    no shutdown
    ip address 40.40.40.2/8
    interface 2
    no shutdown
    ip address 60.60.60.2/8
    ```

2. Verify BGP processes are running on the switches by verifying a non-null value after executing "pgrep -f bgpd" on the switches.
3. Apply BGP configurations in **vtysh** for each switch with the following commands:

    ***Switch 1***

    ```
    configure terminal
    router bgp 1
    bgp router-id 9.0.0.1
    network 11.0.0.0/8
    maximum-paths 5
    neighbor 10.10.10.2 remote-as 2
    neighbor 20.20.20.2 remote-as 3
    neighbor 30.30.30.2 remote-as 4
    ```

    ***Switch 2***

    ```
    configure terminal
    router bgp 2
    bgp router-id 9.0.0.2
    neighbor 10.10.10.1 remote-as 1
    neighbor 40.40.40.2 remote-as 5
    ```

    ***Switch 3***

    ```
    configure terminal
    router bgp 3
    bgp router-id 9.0.0.3
    neighbor 20.20.20.1 remote-as 1
    neighbor 50.50.50.2 remote-as 5
    ```

    ***Switch 4***

    ```
    configure terminal
    router bgp 4
    bgp router-id 9.0.0.4
    neighbor 30.30.30.1 remote-as 1
    neighbor 60.60.60.2 remote-as 5
    ```

    ***Switch 5***

    ```
    configure terminal
    router bgp 5
    bgp router-id 9.0.0.5
    network 12.0.0.0/8
    neighbor 40.40.40.1 remote-as 2
    neighbor 50.50.50.1 remote-as 3
    neighbor 60.60.60.1 remote-as 4
    ```

4. Verify all BGP configurations by comparing the expected values against the output of **show running-config**.
5. Verify the advertised routes from the peers are received on all switches via the **show ip bgp** command.
6. Verify the output of **show ip route** contains three different paths for network 12.0.0.0/8 on switch 1, which should contain 10.10.10.2, 20.20.20.2, and 30.30.30.2.
7. Remove the maximum-paths configuration on switch 1 by issuing the following commands in **vtysh**:

    **Switch 1**

    ```
    configure terminal
    router bgp 1
    no maximum-paths
    ```

8. Verify **maximum-paths** does not exist in the output of **show running-config** on switch 1.
9. Remove the neighbors of switch 1 to refresh all routes by issuing the following commands in **vtysh**:

    **Switch 1**

    ```
    configure terminal
    router bgp 1
    no neighbor 10.10.10.2
    no neighbor 20.20.20.2
    no neighbor 30.30.30.2
    ```

10. Verify all networks advertised from peers are not in the output of **show ip bgp** of switch 1.
11. Reconfigure the neighbors of switch 1 to refresh all routes by issuing the following commands in **vtysh**:

    **Switch 1**

    ```
    configure terminal
    router bgp 1
    neighbor 10.10.10.2 remote-as 2
    neighbor 20.20.20.2 remote-as 3
    neighbor 30.30.30.2 remote-as 4
    ```

12. Verify all routes are received on switch 1 from the configured peers.
13. Verify only one path is recorded in the output of the **show ip route** command.
14. Disable and test Equal-Cost Multi-Path (ECMP) routing by issuing the following commands in **vtysh**:

    **Switch 1**

    ```
    configure terminal
    ip ecmp disable
    router bgp 1
    maximum-paths 3
    ```

15. Verify **ip ecmp disable** and **maximum-paths 3** exists in the output of **show running-config** on switch 1.
16. Refresh the routes to the neighbors by repeating steps 9-12.
17. The **maximum-paths** configuration should not take effect since ECMP is disabled. Verify the number of paths in the output of **show ip route**, on switch 1, for network 12.0.0.0/8 is one.
18. Enable and test Equal-Cost Multi-Path (ECMP) routing by issuing the following commands in **vtysh**:

    **Switch 1**

    ```
    configure terminal
    no ip ecmp disable
    router bgp 1
    maximum-paths 3
    ```

19. Verify **ip ecmp disable** does not exist and **maximum-paths 3** exists in the output of **show running-config** on switch 1.
20. Refresh the routes to the neighbors by repeating steps 9-12.
21. Since ECMP is enabled, the **maximum-paths** configuration should take effect. Verify the number of paths in the output of **show ip route**, on switch 1, for network 12.0.0.0/8 is three.

### Test Result Criteria ###
#### Test Pass Criteria ####

The test case is considered passing in the following cases:

- The number of paths detected in the output of the **show ip route** command is three when **maximum-paths** was set as five on switch 1.
- The number of paths detected in the output of the **show ip route** command is one when **no maximum-paths** was set on switch 1.
- The number of paths detected in the output of the **show ip route** command is one when **maximum-paths** was set to three and **ip ecmp disable** was set.
- The number of paths detected in the output of the **show ip route** command is three when **maximum-paths** was set to three and **no ip ecmp disable** was applied.

**Expected Switch 1 Routes**

```
Local router-id 9.0.0.1
   Network          Next Hop            Metric LocPrf Weight Path
*> 11.0.0.0/8       0.0.0.0                  0      0  32768  i
*  12.0.0.0/8       10.10.10.2               0      0      0 2 5 i
*> 12.0.0.0/8       20.20.20.2               0      0      0 3 5 i
*  12.0.0.0/8       30.30.30.2               0      0      0 4 5 i
```

**Expected Switch 1 Paths - Maximum-Paths is Set**

```
12.0.0.0/8,  3 unicast next-hops
    via  10.10.10.2,  [20/0],  BGP
    via  30.30.30.2,  [20/0],  BGP
    via  20.20.20.2,  [20/0],  BGP
30.0.0.0/8,  1 unicast next-hops
    via  3,  [0/0],  connected
10.0.0.0/8,  1 unicast next-hops
    via  1,  [0/0],  connected
20.0.0.0/8,  1 unicast next-hops
    via  2,  [0/0],  connected
```

**Expected Switch 1 Paths - Maximum-Paths not Set**

```
12.0.0.0/8,  1 unicast next-hops
    via  10.10.10.2,  [20/0],  BGP
30.0.0.0/8,  1 unicast next-hops
    via  3,  [0/0],  connected
10.0.0.0/8,  1 unicast next-hops
    via  1,  [0/0],  connected
20.0.0.0/8,  1 unicast next-hops
    via  2,  [0/0],  connected
```

#### Test Fail Criteria ####
The test case is considered failing in the following cases:

- The advertised routes from the peers are not present in the output from the **show ip bgp** command and fails during verification when the neighbor configurations are applied.
- The BGP daemon is not running on at least one of the switches and fails during verification.
- The number of paths in the output of the **show ip route** command is one when **maximum-paths** is set to a value greater than one.
- The number of paths in the output of the **show ip route** command is three when **no maximum-paths** is applied.
- The number of paths in the output of the **show ip route** command is three when **ip ecmp disable** and **maximum-paths** with a value of three is set.
- The number of paths in the output of the **show ip route** command is less than one when **no ip ecmp disable** and **maximum-paths** with a value of three is set.





## BGP Network Configuration ##
### Objective ###
The test case verifies BGP network by configuring/unconfiguring **network** and verifying against the output of **show running-config** command.

### Requirements ###

- Physical/Virtual Switches

### Setup ###
#### Topology Diagram ####

```ditaa
    +----------------+
    |                |
    |                |
    |     Switch     |
    |                |
    |                |
    +----------------+
```

#### Test Setup ####
**Switch** is configured with:

    router bgp 1
        bgp router-id 9.0.0.1
        network 11.0.0.0/8

### Description ###
1. Verify BGP process is running on the switch by verifying a non-null value after executing "pgrep -f bgpd" on the switch.
2. Apply BGP configurations in **vtysh** with the following commands:

    ***Switch***

    ```
    configure terminal
    router bgp 1
    bgp router-id 9.0.0.1
    network 11.0.0.0/8
    ```

3. Verify **bgp router-id** exists in the output of the **show running-config** command.
4. Verify the configured **network 11.0.0.0/8** exists in the output of the **show ip bgp** command.
5. Apply the **no network** command via **vtysh** with the following commands:

    ```
    configure terminal
    router bgp 1
    no network 11.0.0.0/8
    ```

6. Run the **show ip bgp** command and verify the 11.0.0.0/8 route does not exist.

### Test Result Criteria ###
#### Test Pass Criteria ####
The test case is considered passing in the following cases:

- The output of **show running-config** contains **bgp router-id** configuration after applying the BGP configurations.
- Network 11.0.0.0/8 exists in the output of the **show ip bgp** command.
- Network 11.0.0.0/8 does not exist in the output of the **show ip bgp** command after applying **no network 11.0.0.0/8**.

#### Test Fail Criteria ####
The test case is considered failing in the following cases:

- The BGP daemon is not running on the switch and fails during verification.
- The network 11.0.0.0/8 is not present in the output of the **show ip bgp** command after applying the network configuration.
- Network 11.0.0.0/8 still exists in the output of the **show ip bgp** command after applying **no network 11.0.0.0/8**.





## BGP Neighbor Route-Map ##
### Objective ###
The test case verifies the **ip prefix-list**, **route-map**, **route-map set**, **route-map match**, **neighbor route-map**, **no route-map description**, **no route-map**, and **no ip prefix-list** commands by verifying the received routes and configurations after applying and removing the configurations.

### Requirements ###

- Physical/Virtual Switches

### Setup ###
#### Topology Diagram ####

```ditaa
    +----------------+         +----------------+
    |                |         |                |
    |                |         |                |
    |    Switch 1    +---------+    Switch 2    |
    |                |         |                |
    |                |         |                |
    +----------------+         +----------------+
```

#### Test Setup ####
**Switch 1** is configured with:

    !
    interface 1
        no shutdown
        ip address 8.0.0.1/8
    !
    ip prefix-list BGP1_IN seq 5 deny 11.0.0.0/8
    ip prefix-list BGP1_IN seq 10 permit 10.0.0.0/8
    !
    route-map BGP1_IN permit 5
        description A route-map description for testing.
        match ip address prefix-list BGP1_IN
    !
    router bgp 1
        bgp router-id 8.0.0.1
        network 9.0.0.0/8
        neighbor 8.0.0.2 remote-as 2
        neighbor 8.0.0.2 route-map BGP1_IN in

**Switch 2** is configured with:

    !
    interface 1
        no shutdown
        ip address 8.0.0.2/8
    !
    router bgp 2
        bgp router-id 8.0.0.2
        network 10.0.0.0/8
        network 11.0.0.0/8
        neighbor 8.0.0.1 remote-as 1

### Description ###
The test case verifies the **ip prefix-list** command by configuring a **route-map**, applying the route-map to a neighbor via the **neighbor route-map** command, and verifying that the routes are filtered and exchanged successfully between the two switches. The test case also verifies **route-map match**, **no route-map description**, **no route-map**, and **no ip prefix-list** commands.

1. Configure switches 1 and 2 with **8.0.0.1/8** and **8.0.0.2/8**, respectively, in **vtysh** with the following commands:

    ***Switch 1***

    ```
    configure terminal
    interface 1
    no shutdown
    ip address 8.0.0.1/8
    ```

    ***Switch 2***

    ```
    configure terminal
    interface 1
    no shutdown
    ip address 8.0.0.2/8
    ```

2. Verify BGP processes are running on the switches by verifying a non-null value after executing "pgrep -f bgpd" on the switches.
3. Create the IP prefix-lists on switch 1 to prohibit network 11.0.0.0/8 and permit network 10.0.0.0/8 with the following commands:

    ***Switch 1***

    ```
    configure terminal
    ip prefix-list BGP1_IN seq 5 deny 11.0.0.0/8
    ip prefix-list BGP1_IN seq 10 permit 10.0.0.0/8
    ```

4. Create the route-map on switch 1, assign the prefix-list to the route-map using the **match** command, and set a description:

    ***Switch 1***

    ```
    configure terminal
    route-map BGP1_IN permit 5
    description A route-map description for testing.
    match ip address prefix-list BGP1_IN
    ```

5. Apply BGP configurations on each switch. The route-map configuration is applied to a neighbor, which will filter incoming advertised routes.

    ***Switch 1***

    ```
    configure terminal
    router bgp 1
    bgp router-id 8.0.0.1
    network 9.0.0.0/8
    neighbor 8.0.0.2 remote-as 2
    neighbor 8.0.0.2 route-map BGP1_IN out
    ```

    ***Switch 2***

    ```
    configure terminal
    router bgp 2
    bgp router-id 8.0.0.2
    network 10.0.0.0/8
    network 11.0.0.0/8
    neighbor 8.0.0.1 remote-as 1
    ```

6. Verify all BGP configurations by comparing the expected values against the output of **show running-config**.
7. Verify the **neighbor route-map** configuration is applied succesfully by checking the network 9.0.0.0/8 from switch 1 is received on switch 2, and the network 10.0.0.0/8 is received and the network 11.0.0.0/8 is not received from switch 2 on switch 1 via the **show ip bgp** command.
8. Verify the route-map **description** from the output of the **show running-config** command.
9. Remove the route-map **description** by issuing the following commands in **vtysh** on switch 1:

    **Switch 1**

    ```
    configure terminal
    route-map BGP1_IN permit 5
    no description
    ```

10. Verify the route-map **description** is removed from the output of the **show running-config** command on switch 1.
11. Remove the **route-map** configuration by issuing the following commands in **vtysh** on switch 1:

    **Switch 1**

    ```
    configure terminal
    no route-map BGP1_IN permit 5
    ```

12. Verify the **route-map** configuration is removed from the output of the **show running-config** command on switch 1.
13. Remove the **ip prefix-list** configuration by issuing the following commands in **vtysh** on switch 1:

    **Switch 1**

    ```
    configure terminal
    no ip prefix-list BGP1_IN seq 5 deny 11.0.0.0/8
    no ip prefix-list BGP1_IN seq 10 permit 10.0.0.0/8
    ```

14. Verify the **ip prefix-list** configurations are removed from the output of the **show running-config** command on switch 1.

### Test Result Criteria ###
#### Test Pass Criteria ####

The test case is considered passing if the advertised routes from switch 2 do not include network 11.0.0.0/8 in the output of the **show ip bgp** command on switch 1. The **ip prefix-list**, **route-map**, and **neighbor route-map** commands prohibit network 11.0.0.0/8 from being advertised out from switch 2 towards switch 1.

**Expected Switch 1 Routes**

```
Local router-id 8.0.0.1
   Network          Next Hop            Metric LocPrf Weight Path
*> 9.0.0.0          0.0.0.0                  0         32768 i
*> 10.0.0.0         8.0.0.2                  0             0 2 i
```

**Expected Switch 2 Routes**

```
Local router-id 8.0.0.2
   Network          Next Hop            Metric LocPrf Weight Path
*> 9.0.0.0          8.0.0.1                  0             0 1 i
*> 10.0.0.0         0.0.0.0                  0         32768 i
*> 11.0.0.0         0.0.0.0                  0         32768 i
```

The test case is considered passing, for the **no route-map** and **no ip prefix-list** command, if the configurations are not present in the output of the **show running-config** on switch 1.

#### Test Fail Criteria ####
The test case is considered failing in the following cases:

- The advertised routes from the peers are not present in the output from the **show ip bgp** command.
- The BGP daemon is not running on at least one of the switches and fails during verification.
- The prohibited network 11.0.0.0/8 from switch 2 exists in the output of the **show ip bgp** command on switch 1.
- The route-map **description** still exists in the output of the **show running-config** command on switch 1 after applying **no description**.
- The **route-map** configuration still exists in the output of the **show running-config** command on switch 1 after applying **no route-map**.
- The **ip prefix-list** configuration still exists in the output of the **show running-config** command on switch 1 after applying **no ip prefix-list**.





## Router BGP Configuration ##
### Objective ###
The test case verifies BGP router functionality by configuring/unconfiguring **router bgp** and verifying against the output of **show running-config** and **show ip bgp** commands.

### Requirements ###

- Physical/Virtual Switches

### Setup ###
#### Topology Diagram ####

```ditaa
    +----------------+
    |                |
    |                |
    |     Switch     |
    |                |
    |                |
    +----------------+
```

#### Test Setup ####
**Switch** is configured with:

    router bgp 1
        bgp router-id 9.0.0.1
        network 11.0.0.0/8
        neighbor 9.0.0.2 remote-as 2

### Description ###
1. Verify BGP process is running on the switch by verifying a non-null value after executing "pgrep -f bgpd" on the switch.
2. Apply BGP configurations in **vtysh** for the switch with the following commands:

    ***Switch***

    ```
    configure terminal
    router bgp 1
    bgp router-id 9.0.0.1
    network 11.0.0.0/8
    neighbor 9.0.0.2 remote-as 2
    ```

3. Verify all BGP configurations by comparing the expected values against the output of **show running-config**.
4. Verify the configured **network 11.0.0.0/8** exists in the output of the **show ip bgp** command.
5. Apply the **no router bgp** command via **vtysh** with the following commands:

    ```
    configure terminal
    no router bgp 1
    ```

6. Run the **show ip bgp** command and verify 11.0.0.0/8 route does not exist.

### Test Result Criteria ###
#### Test Pass Criteria ####
The test case is considered passing in the following cases:

- Network 11.0.0.0/8 exists in the output of the **show ip bgp** command.
- Network 11.0.0.0/8 does not exist in the output of the **show ip bgp** command after applying **no router bgp 1**.

#### Test Fail Criteria ####
The test case is considered failing in the following cases:

- The BGP daemon is not running on the switch and fails during verification.
- The network 11.0.0.0/8 is not present in the output of the **show ip bgp** command after applying the network configuration.
- Network 11.0.0.0/8 still exists in the output of the **show ip bgp** command after applying **no router bgp 1**.





## BGP Router-ID Configuration ##
### Objective ###
The test case verifies BGP router-ID command by configuring/unconfiguring **bgp router-id** and verifying against the output of **show ip bgp** command.

### Requirements ###

- Physical/Virtual Switches

### Setup ###
#### Topology Diagram ####

```ditaa
    +----------------+
    |                |
    |                |
    |     Switch     |
    |                |
    |                |
    +----------------+
```

#### Test Setup ####
**Switch** is configured with:

    router bgp 1
        bgp router-id 9.0.0.1
        network 11.0.0.0/8

### Description ###
1. Verify BGP process is running on the switch by verifying a non-null value after executing "pgrep -f bgpd" on the switch.
2. Apply BGP configurations in **vtysh** for the switch with the following commands:

    ***Switch***

    ```
    configure terminal
    router bgp 1
    bgp router-id 9.0.0.1
    network 11.0.0.0/8
    ```

3. Verify **bgp router-id** exists in the output of the **show ip bgp** command.
4. Apply the **no bgp router-id** command via **vtysh** with the following commands:

    ```
    configure terminal
    router bgp 1
    no bgp router-id 9.0.0.1
    ```

5. Run the **show ip bgp** command and verify the **router-id** does not exist.

### Test Result Criteria ###
#### Test Pass Criteria ####
The test case is considered passing in the following cases:

- The output of **show ip bgp** contains 9.0.0.1 after applying the BGP configurations.
- The **router-id** 9.0.0.1 does not exist in the output of the **show ip bgp** command after applying **no bgp router-id**.

#### Test Fail Criteria ####
The test case is considered failing in the following cases:

- The BGP daemon is not running on the switch and fails during verification.
- The **router-id** is not present in the output of the **show ip bgp** command after applying the BGP configurations.
- The **router-id** still exists in the output of the **show ip bgp** command after applying **no bgp router-id**.





## Show BGP Neighbors ##
### Objective ###
The test case verifies the **show bgp neighbors** command by configuring/unconfiguring neighbors and verifying the output of the **show bgp neighbors** command.

### Requirements ###

- Physical/Virtual Switches

### Setup ###
#### Topology Diagram ####

```ditaa
    +----------------+
    |                |
    |                |
    |     Switch     |
    |                |
    |                |
    +----------------+
```

#### Test Setup ####
**Switch** is configured with:

    router bgp 1
        neighbor 1.1.1.1 remote-as 1111

### Description ###
1. Apply BGP configurations in **vtysh** for the switch with the following commands:

    ***Switch***

    ```
    configure terminal
    router bgp 1
    neighbor 1.1.1.1 remote-as 1111
    ```

2. Verify neighbor IP address, remote-as, TCP port number, and keep-alive count values are displayed correctly in the output of the **show bgp neighbors** command.
3. Remove the neighbor configuration via **vtysh** with the following commands:

    ***Switch***

    ```
    configure terminal
    router bgp 1
    no neighbor 1.1.1.1
    ```

4. Verify neighbor IP address, remote-as, TCP port number, and keep-alive count are not displayed in the output of the **show bgp neighbors** command.

### Test Result Criteria ###
#### Test Pass Criteria ####
The test case is considered passing in the following cases:

- The output of **show bgp neighbors** contains the neighbor IP address, remote-as, TCP port number, and keep-alive count after applying the BGP configurations.
- The output of **show bgp neighbors** does not contain the neighbor IP address, remote-as, TCP port number, and keep-alive count after applying the **no neighbor** command.

#### Test Fail Criteria ####
The test case is considered failing in the following cases:

- The output of **show bgp neighbors** does not contain the neighbor IP address, remote-as, TCP port number, and keep-alive count after applying the BGP configurations.
- The output of **show bgp neighbors** contains the neighbor IP address, remote-as, TCP port number, and keep-alive count after applying the **no neighbor** command.





## Show IP BGP ##
### Objective ###
The test case verifies the **show ip bgp** command by verifying the received route after configuring and removing the neighbor configurations.

### Requirements ###

- Physical/Virtual Switches

### Setup ###
#### Topology Diagram ####

```ditaa
    +----------------+         +----------------+
    |                |         |                |
    |                |         |                |
    |    Switch 1    +---------+    Switch 2    |
    |                |         |                |
    |                |         |                |
    +----------------+         +----------------+
```

#### Test Setup ####
**Switch 1** is configured with:

    !
    interface 1
        no shutdown
        ip address 9.0.0.1/8
    !
    router bgp 1
        bgp router-id 9.0.0.1
        network 11.0.0.0/8
        neighbor 9.0.0.2 remote-as 2

**Switch 2** is configured with:

    !
    interface 1
        no shutdown
        ip address 9.0.0.2/8
    !
    router bgp 2
        bgp router-id 9.0.0.2
        network 12.0.0.0/8
        neighbor 9.0.0.1 remote-as 1

### Description ###
1. Configure switches 1 and 2 with **9.0.0.1/8** and **9.0.0.2/8**, respectively, in **vtysh** with the following commands:

    ***Switch 1***

    ```
    configure terminal
    interface 1
    no shutdown
    ip address 9.0.0.1/8
    ```

    ***Switch 2***

    ```
    configure terminal
    interface 1
    no shutdown
    ip address 9.0.0.2/8
    ```

2. Verify BGP processes are running on the switches by verifying a non-null value after executing "pgrep -f bgpd" on the switches.
3. Apply BGP configurations in **vtysh** for each switch with the following commands:

    ***Switch 1***

    ```
    configure terminal
    router bgp 1
    bgp router-id 9.0.0.1
    network 11.0.0.0/8
    neighbor 9.0.0.2 remote-as 2
    ```

    ***Switch 2***

    ```
    configure terminal
    router bgp 2
    bgp router-id 9.0.0.2
    network 12.0.0.0/8
    neighbor 9.0.0.1 remote-as 1
    ```

4. Verify all BGP configurations by comparing the expected values against the output of **show running-config**.
5. Verify the **show ip bgp** command works by verifying the route advertised from the neighbor exists in the output on switch 1.
6. Remove the neighbor configuration on switch 1 by issuing the following commands in **vtysh**:

    **Switch 1**

    ```
    configure terminal
    router bgp 1
    no neighbor 9.0.0.2
    ```

7. Verify the network advertised from switch 2 in the output of **show ip bgp** of switch 1 is no longer present.

### Test Result Criteria ###
#### Test Pass Criteria ####

The test case is considered passing, for the **neighbor remote-as** command, if the advertised routes of each peer exists in the output of the **show ip bgp** command on both switches. The network and next-hop, as returned from the **show ip bgp** command, must match the information as configured on the peer.

**Expected Switch 1 Routes**

```
Local router-id 9.0.0.1
   Network          Next Hop            Metric LocPrf Weight Path
*> 11.0.0.0/8       0.0.0.0                  0      0  32768  i
*> 12.0.0.0/8       9.0.0.2                  0      0      0 2 i
```

**Expected Switch 2 Routes**

```
Local router-id 9.0.0.2
   Network          Next Hop            Metric LocPrf Weight Path
*> 11.0.0.0/8       9.0.0.1                  0      0      0 1 i
*> 12.0.0.0/8       0.0.0.0                  0      0  32768  i
```

Applying the **no neighbor** command causes the route from the output of the **show ip bgp** command to be removed.

**Expected Switch 1 Routes**

```
Local router-id 9.0.0.1
   Network          Next Hop            Metric LocPrf Weight Path
*> 11.0.0.0/8       0.0.0.0                  0      0  32768  i
```

**Expected Switch 2 Routes**

```
Local router-id 9.0.0.2
   Network          Next Hop            Metric LocPrf Weight Path
*> 12.0.0.0/8       0.0.0.0                  0      0  32768  i
```

#### Test Fail Criteria ####
The test case is considered failing in the following cases:

- The advertised routes from the peers are not present in the output from the **show ip bgp** command and fails during verification when the neighbor configurations are applied.
- The BGP daemon is not running on at least one of the switches and fails during verification.
- The advertised routes from the peers are still present in the output from the **show ip bgp** command after applying the **no neighbor** command.





## BGP Show Running Config ##
### Objective ###
The test case verifies **show running-config** by applying BGP configurations and verifying against the output of **show running-config** command.

### Requirements ###

- Physical/Virtual Switches

### Setup ###
#### Topology Diagram ####

```ditaa
    +----------------+
    |                |
    |                |
    |     Switch     |
    |                |
    |                |
    +----------------+
```

#### Test Setup ####
**Switch** is configured with:

    router bgp 12
        bgp router-id 9.0.0.1
        network 11.0.0.0/8
        maximum-paths 20
        timers bgp 3 10
        neighbor openswitch peer-group
        neighbor 9.0.0.2 remote-as 2
        neighbor 9.0.0.2 description abcd
        neighbor 9.0.0.2 password abcdef
        neighbor 9.0.0.2 timers 3 10
        neighbor 9.0.0.2 allowas-in 7
        neighbor 9.0.0.2 remove-private-AS
        neighbor 9.0.0.2 soft-reconfiguration inbound
        neighbor 9.0.0.2 peer-group openswitch

### Description ###
1. Verify BGP process is running on the switch by verifying a non-null value after executing "pgrep -f bgpd" on the switch.
2. Apply BGP configurations in **vtysh** for the switch with the following commands:

    ***Switch***

    ```
    configure terminal
    router bgp 12
    bgp router-id 9.0.0.1
    network 11.0.0.0/8
    maximum-paths 20
    timers bgp 3 10
    neighbor openswitch peer-group
    neighbor 9.0.0.2 remote-as 2
    neighbor 9.0.0.2 description abcd
    neighbor 9.0.0.2 password abcdef
    neighbor 9.0.0.2 timers 3 10
    neighbor 9.0.0.2 allowas-in 7
    neighbor 9.0.0.2 remove-private-AS
    neighbor 9.0.0.2 soft-reconfiguration inbound
    neighbor 9.0.0.2 peer-group openswitch
    ```

3. Verify all BGP configurations, including **timers bgp** by comparing the expected values against the output of **show running-config**.

### Test Result Criteria ###
#### Test Pass Criteria ####
The test case is considered passing if the output of **show running-config** contains all configurations.

#### Test Fail Criteria ####
The test case is considered failing in the following cases:

- The BGP daemon is not running on the switch and fails during verification.
- At least one configuration is missing from the output of **show running-config**.





## Timers BGP Configuration ##
### Objective ###
The test case verifies BGP timers command by configuring/unconfiguring **timers bgp** and verifying against the output of **show running-config** command.
### Requirements ###

- Physical/Virtual Switches

### Setup ###
#### Topology Diagram ####

```ditaa
    +----------------+
    |                |
    |                |
    |     Switch     |
    |                |
    |                |
    +----------------+
```

#### Test Setup ####
**Switch** is configured with:

    router bgp 1
        timers bgp 5 10

### Description ###
1. Verify BGP process is running on the switch by verifying a non-null value after executing "pgrep -f bgpd" on the switch.
2. Apply BGP configurations in **vtysh** for the switch with the following commands:

    ***Switch***

    ```
    configure terminal
    router bgp 1
    timers bgp 5 10
    ```

3. Verify all BGP configurations, including **timers bgp** by comparing the expected values against the output of **show running-config**.
4. Apply the **no timers bgp** command via **vtysh** with the following commands:

    ```
    configure terminal
    router bgp 1
    no timers bgp
    ```

5. Run the **show running-config** command and verify **timers bgp** configuration does not exist.

### Test Result Criteria ###
#### Test Pass Criteria ####
The test case is considered passing if the output of **show running-config** contains **timers bgp** configuration after **timers bgp** was configured. Setting **no timers bgp** removes the **timers bgp** configuration and must not be displayed in **show running-config**.

#### Test Fail Criteria ####
The test case is considered failing in the following cases:

- The BGP daemon is not running on the switch and fails during verification.
- The BGP configurations are not applied successfully and fails during verification.
- The **timers bgp** configuration still exists in the output of the **show running-config** after applying **no timers bgp**.
