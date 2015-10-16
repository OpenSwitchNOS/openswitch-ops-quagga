# Quagga Test Cases

## Contents

- [Zebra update](#zebra-update)
- [Topology with ECMP routes](#topology-with-ecmp-routes)
- [BGP maximum paths](#bgp-maximum-paths)
- [BGP network configuration](#bgp-network-configuration)
- [BGP neighbor route-map](#bgp-neighbor-route-map)
- [Router BGP configuration](#router-bgp-configuration)
- [BGP router-ID configuration](#bgp-router-id-configuration)
- [Show BGP neighbors](#show-bgp-neighbors)
- [Show IP BGP](#show-ip-bgp)
- [BGP show running config](#bgp-show-running-config)
- [Timers BGP configuration](#timers-bgp-configuration)

##  Zebra update
### Objective
This test case verifies selected column zebra updates in the dtabase when static routes are added.

### Requirements
- Virtual Mininet Test Setup
- **CT File**: ops-quagga/zebra/test\_zebra\_ct\_fib\_selection.py (Route Table Update)

### Setup
#### Topology diagram
```ditaa
  +------------+            +------------+
  |            |            |            |
  |  Switch 1  +------------+  Switch 2  |
  |            |            |            |
  +------------+            +------------+
```

### Description
1. Setup two switches with two host topologies.
2. Add the static routes on the two switches to be able to reach the end hosts.
3. Configure the end hosts with valid IP addresses.
4. Dump the route table into the database using `ovsdb-client dump`.

### Test result criteria
#### Test pass criteria
Verify that the selected column in the route table (for the rows with static routes) is set to **true**.

#### Test fail criteria

##  Topology with ECMP routes
### Objective
This test case checks for connectivity in a topology with three hosts and four switches.

### Requirements
- Virtual Mininet Test Setup
- **CT File**: ops-quagga/zebra/test\_zebra\_ct\_ecmp.py

### Setup

#### Topology diagram
```ditaa
    10.0.10.1/24  10.0.10.2/24  10.0.30.1/24 10.0.30.2/24  10.0.70.2/24
    +-----------+      +---------------+          +------------+
    |           |      |               |          |            |
    |           |      |               |          |            |      10.0.70.1/24
    |           |      |               |          |            |      +----------+
    |   Host 1  +---[Link 1]           |          |            |      |          |
    |           |      |               |          |            |      |          |
    |           |      |            [Link 3]---[Link 1]        |      |          |
    |           |      |               |          |            |      |          |
    +-----------+      |               |          |            |      |  Host 3  |
                       |   Switch 1    |          |  Switch 2  |      |          |
                       |               |          |            |      |          |
                       |               |          |         [Link 3]--+          |
                       |               |          |            |      |          |
                       |               |          |            |      |          |
    +-----------+      |               |          |            |      |          |
    |           |      |               |          |            |      +----------+
    |           |      |            [Link 4]---[Link 2]        |
    |           |      |               |          |            |
    |  Host 2   +---[Link 2]           |          |            |
    |           |      |               |          |            |
    |           |      |               |          |            |
    |           |      |               |          |            |
    +-----------+      +---------------+          +------------+
    10.0.20.1/24  10.0.20.2/24  10.0.40.1/24       10.0.40.2/24
```

### Description
1. Create a topology with three hosts and two switches.
2. Setup Switch 1 with an ECMP route to Switch 2 with nexthops connected to Switch 2 by Link 1 and Link 2.
3. Setup Switch 2 with two ECMP routes towards Host 1 via Switch 2 Link 3 and Switch 1 Link 4.
4. Ping Host 3 10.0.70.1 from Host 1.
5. Ping Host 3 from Host 2.

### Test result criteria

#### Test pass criteria
* When pinging Host 3 from Host 1, the kernel load balances pings because of the ECMP route with two next hops, one via Switch 2 Link 1 and Link 2.
* When pinging Host 3 from Host 2, the kernel load balances pings because of the ECMP route with two next hops, one via Switch 2 Link 1 and Link 2.

#### Test fail criteria


## BGP maximum paths
### Objective
This test case verifies `maximum-paths` and `no maximum-paths` by configuring three different paths to the same switch.

### Requirements

Physical or virtual switches

### Setup
#### Topology diagram

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

#### Test setup
**Switch 1** is configured with:

```
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
```

**Switch 2** is configured with:

```
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
```

**Switch 3** is configured with:

```
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
```

**Switch 4** is configured with:

```
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
```

**Switch 5** is configured with:

```
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
```

### Description

1. Configure the IP addresses on all switches in `vtysh` with the following commands:

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

2. Verify that the BGP processes are running on the switches by confirming a non-null value after executing `pgrep -f bgpd` on the switches.
3. Apply BGP configurations in `vtysh` for each switch with the following commands:

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

4. Verify all BGP configurations by comparing the expected values against the output of `show running-config`.
5. Confirm that the advertised peer routes are received on all switches using the `show ip bgp` command.
6. Ensure that the output of `show ip route` contains three different paths for network 12.0.0.0/8 on Switch 1. The paths should contain IP addresses 10.10.10.2, 20.20.20.2, and 30.30.30.2.
7. Remove the maximum-paths configuration on Switch 1 by issuing the following commands in `vtysh`:

    **Switch 1**

    ```
    configure terminal
    router bgp 1
    no maximum-paths
    ```

8. Verify that `maximum-paths` does not exist in the `show running-config` command output on Switch 1.
9. Remove the neighbors of Switch 1 to refresh all routes by issuing the following commands in `vtysh`:

    **Switch 1**

    ```
    configure terminal
    router bgp 1
    no neighbor 10.10.10.2
    no neighbor 20.20.20.2
    no neighbor 30.30.30.2
    ```

10. Verify that all peer advertised networks are not in the `show ip bgp` command output on Switch 1.
11. Reconfigure the neighbors of Switch 1 to refresh all routes by issuing the following commands in `vtysh`:

    **Switch 1**

    ```
    configure terminal
    router bgp 1
    neighbor 10.10.10.2 remote-as 2
    neighbor 20.20.20.2 remote-as 3
    neighbor 30.30.30.2 remote-as 4
    ```

12. Verify that all routes from configured peers are received on Switch 1.
13. Confirm that only one path is recorded in the `show ip route` command output.
14. Disable and test Equal-Cost Multi-Path (ECMP) routing by issuing the following commands in `vtysh`:

    **Switch 1**

    ```
    configure terminal
    ip ecmp disable
    router bgp 1
    maximum-paths 3
    ```

15. Verify that both `ip ecmp disable` and `maximum-paths 3` is displayed in the `show running-config` command output on Switch 1.
16. Refresh the routes to the neighbors by repeating steps 9-12.
17. The `maximum-paths` configuration should not take effect since ECMP is disabled. Verify that the number of paths is one in the `show ip route` command output, on Switch 1, for network 12.0.0.0/8.
18. Enable and test Equal-Cost Multi-Path (ECMP) routing by issuing the following commands in `vtysh`:

    **Switch 1**

    ```
    configure terminal
    no ip ecmp disable
    router bgp 1
    maximum-paths 3
    ```

19. Verify that `ip ecmp disable` does not exist and that `maximum-paths 3` does exist in the `show running-config` command output on Switch 1.
20. Refresh the routes to the neighbors by repeating steps 9-12.
21. Since ECMP is enabled, the `maximum-paths` configuration should take effect. Verify that the number of paths is three in the `show ip route` command output, on Switch 1, for network 12.0.0.0/8.

### Test result criteria
#### Test pass criteria

This test case is considered passing for the following reasons:

- The number of paths detected in the `show ip route` command output is one when the number of `maximum-paths` is set to three and the `ip ecmp disable` command is applied.
- The number of paths detected in the `show ip route` command output is three when the number of `maximum-paths` is set to three and the `no ip ecmp disable` command is applied.
- The number of paths detected in the `show ip route` command output is three when the number of `maximum-paths` is set to five on Switch 1, as shown below:

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

- The number of paths detected in the `show ip route` command output is one when `no maximum-paths` is set on Switch 1, as shown below:

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

#### Test fail criteria
This test case is considered failing for the following reasons:

- The advertised routes from the peers are not present in the `show ip bgp` command output.
- The BGP daemon is not running on at least one of the switches.
- The number of paths in the `show ip route` command output is one when the number of `maximum-paths` is set to a value greater than one.
- The number of paths in the `show ip route` command output is three when `no maximum-paths` command is applied.
- The number of paths in the `show ip route` command output is three when `ip ecmp disable` and `maximum-paths` with a value of three is set.
- The number of paths in the `show ip route` command output is less than one when `no ip ecmp disable` and `maximum-paths` with a value of three is set.





## BGP network configuration
### Objective
This test case verifies the BGP network by configuring and unconfiguring the `network` and validating the results against the output of the `show running-config` command.

### Requirements

Physical or virtual switches

### Setup
#### Topology diagram

```ditaa
    +----------------+
    |                |
    |                |
    |     Switch     |
    |                |
    |                |
    +----------------+
```

#### Test setup
**Switch** is configured with:

```
router bgp 1
    bgp router-id 9.0.0.1
    network 11.0.0.0/8
```

### Description
1. Verify if the BGP process is running on the switch by ensuring that a non-null value exists after executing `pgrep -f bgpd` on the Switch.
2. Apply BGP configurations in `vtysh` with the following commands:

    ***Switch***

    ```
    configure terminal
    router bgp 1
    bgp router-id 9.0.0.1
    network 11.0.0.0/8
    ```

3. Verify that the `bgp router-id` exists in the `show running-config` command output.
4. Ensure that the configured `network 11.0.0.0/8` exists in the `show ip bgp` command output.
5. Apply the `no network` command via `vtysh` with the following commands:

    ```
    configure terminal
    router bgp 1
    no network 11.0.0.0/8
    ```

6. Run the `show ip bgp` command and verify that the 11.0.0.0/8 route does not exist.

### Test result criteria
#### Test pass criteria
This test case is considered passing for the following reasons:

- The output of the `show running-config` command contains the `bgp router-id` configuration after applying the BGP configurations.
- The network 11.0.0.0/8 exists in the `show ip bgp` command output.
- The network 11.0.0.0/8 does not exist in the `show ip bgp` command output after applying `no network 11.0.0.0/8`.

#### Test fail criteria
This test case is considered failing for the following reasons:

- The BGP daemon is not running on the switch.
- The network 11.0.0.0/8 is not present in the `show ip bgp` command output after applying the network configuration.
- The network 11.0.0.0/8 still exists in the `show ip bgp` command output after applying `no network 11.0.0.0/8`.





## BGP neighbor route-map
### Objective
This test case verifies the `ip prefix-list`, `route-map`, `route-map set`, `route-map match`, `neighbor route-map`, `no route-map description`, `no route-map`, and `no ip prefix-list` commands by verifying the received routes and configurations after applying and removing the configurations.

### Requirements

Physical or virtual switches

### Setup
#### Topology diagram

```ditaa
    +----------------+         +----------------+
    |                |         |                |
    |                |         |                |
    |    Switch 1    +---------+    Switch 2    |
    |                |         |                |
    |                |         |                |
    +----------------+         +----------------+
```

#### Test setup
**Switch 1** is configured with:

```
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
```

**Switch 2** is configured with:

```
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
```

### Description
This test case verifies the `ip prefix-list` command by configuring a `route-map`, applying the route-map to a neighbor via the `neighbor route-map` command, and verifying that the routes are filtered and exchanged successfully between the two switches. This test case also verifies `route-map match`, `no route-map description`, `no route-map`, and `no ip prefix-list` commands.

1. Configure Switch 1 and Switch 2 with networks **8.0.0.1/8** and **8.0.0.2/8**, respectively, in `vtysh` with the following commands:

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

2. Verify that the BGP processes are running on the switches by confirming a non-null value after executing `pgrep -f bgpd` on the switches.
3. Create the IP prefix-lists on Switch 1 to prohibit network 11.0.0.0/8 and permit network 10.0.0.0/8 with the following commands:

    ***Switch 1***

    ```
    configure terminal
    ip prefix-list BGP1_IN seq 5 deny 11.0.0.0/8
    ip prefix-list BGP1_IN seq 10 permit 10.0.0.0/8
    ```

4. Create the route-map on Switch 1, assign the prefix-list to the route-map using the `match` command, and set a description:

    ***Switch 1***

    ```
    configure terminal
    route-map BGP1_IN permit 5
    description A route-map description for testing.
    match ip address prefix-list BGP1_IN
    ```

5. Apply BGP configurations on each switch. The route-map configuration is applied to a neighbor, which filters incoming advertised routes.

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

6. Verify all BGP configurations by comparing the expected values against the `show running-config` command output.
7. Using the `show ip bgp` command, confirm that the `neighbor route-map` configuration is applied successfully by ensuring the following:
    - Check that the network 9.0.0.0/8 from Switch 1 is received on Switch 2.
    - Establish that the network 10.0.0.0/8 from Switch 2 is received on Switch 1.
    - Verify that the network 11.0.0.0/8 is not received from Switch 2 on Switch 1.
8. Verify that the route-map has a description from the `show running-config` command output.
9. Remove the route-map `description` by issuing the following commands in `vtysh` on Switch 1:

    **Switch 1**

    ```
    configure terminal
    route-map BGP1_IN permit 5
    no description
    ```

10. Verify the route-map `description` is removed from the `show running-config` command output on Switch 1.
11. Remove the `route-map` configuration by issuing the following commands in `vtysh` on Switch 1:

    **Switch 1**

    ```
    configure terminal
    no route-map BGP1_IN permit 5
    ```

12. Verify that the `route-map` configuration is removed from the `show running-config` command output on Switch 1.
13. Remove the `ip prefix-list` configuration by issuing the following commands in `vtysh` on Switch 1:

    **Switch 1**

    ```
    configure terminal
    no ip prefix-list BGP1_IN seq 5 deny 11.0.0.0/8
    no ip prefix-list BGP1_IN seq 10 permit 10.0.0.0/8
    ```

14. Verify that the `ip prefix-list` configurations are removed from the `show running-config` command output on Switch 1.

### Test result criteria
#### Test pass criteria

This test case is considered passing if the advertised routes from Switch 2 do not include network 11.0.0.0/8 in the `show ip bgp` command output on Switch 1.

The `ip prefix-list`, `route-map`, and `neighbor route-map` commands prohibit network 11.0.0.0/8 from being advertised out from Switch 2 to Switch 1.

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

This test case is considered passing for the `no route-map` and `no ip prefix-list` commands, if the configurations are not present in the `show running-config` command output on Switch 1.

#### Test fail criteria
This test case is considered failing for the following reasons:

- The advertised peer routes are not present in the `show ip bgp` command output.
- The BGP daemon is not running on at least one of the switches.
- The prohibited network 11.0.0.0/8 from Switch 2 exists in the `show ip bgp` command output on Switch 1.
- The route-map `description` still exists in the `show running-config` command output on Switch 1 after applying `no description`.
- The `route-map` configuration still exists in the `show running-config` command output on Switch 1 after applying `no route-map`.
- The `ip prefix-list` configuration still exists in the `show running-config` command output on Switch 1 after applying `no ip prefix-list`.





## Router BGP configuration
### Objective
This test case verifies BGP router functionality by configuring and unconfiguring `router bgp` and verifying against the output of `show running-config` and `show ip bgp` commands.

### Requirements

Physical or virtual switches

### Setup
#### Topology diagram

```ditaa
    +----------------+
    |                |
    |                |
    |     Switch     |
    |                |
    |                |
    +----------------+
```

#### Test setup
**Switch** is configured with:

```
router bgp 1
    bgp router-id 9.0.0.1
    network 11.0.0.0/8
    neighbor 9.0.0.2 remote-as 2
```

### Description
1. Verify that the BGP process is running on the switch by confirming a non-null value after executing `pgrep -f bgpd` on the Switch.
2. Apply BGP configurations in `vtysh` for the switch with the following commands:

    ***Switch***

    ```
    configure terminal
    router bgp 1
    bgp router-id 9.0.0.1
    network 11.0.0.0/8
    neighbor 9.0.0.2 remote-as 2
    ```

3. Verify all BGP configurations by comparing the expected values against the `show running-config` command output.
4. Ensure that the configured `network 11.0.0.0/8` exists in the `show ip bgp` command output.
5. Apply the `no router bgp` command via `vtysh` with the following commands:

    ```
    configure terminal
    no router bgp 1
    ```

6. Run the `show ip bgp` command and verify that the 11.0.0.0/8 route does not exist.

### Test result criteria
#### Test pass criteria
This test case is considered passing for the following reasons:

- The network 11.0.0.0/8 exists in the `show ip bgp` command output.
- The network 11.0.0.0/8 does not exist in the `show ip bgp` command output after applying `no router bgp 1`.

#### Test fail criteria
This test case is considered failing for the following reasons:

- The BGP daemon is not running on the switch.
- The network 11.0.0.0/8 is not present in the `show ip bgp` command output after applying the network configuration.
- The network 11.0.0.0/8 still exists in the `show ip bgp` command output after applying `no router bgp 1`.





## BGP router-ID configuration
### Objective
This test case verifies that BGP router-ID command works by configuring or unconfiguring `bgp router-id` and confirming the results against the `show ip bgp` command output.

### Requirements

Physical or virtual switches

### Setup
#### Topology diagram

```ditaa
    +----------------+
    |                |
    |                |
    |     Switch     |
    |                |
    |                |
    +----------------+
```

#### Test setup
**Switch** is configured with:

```
router bgp 1
    bgp router-id 9.0.0.1
    network 11.0.0.0/8
```

### Description
1. Verify that the BGP process is running on the switch by confirming a non-null value after executing `pgrep -f bgpd` on the Switch.
2. Apply BGP configurations in `vtysh` for the switch with the following commands:

    ***Switch***

    ```
    configure terminal
    router bgp 1
    bgp router-id 9.0.0.1
    network 11.0.0.0/8
    ```

3. Verify that the `bgp router-id` exists in the `show ip bgp` command output.
4. Apply the `no bgp router-id` command via `vtysh` with the following commands:

    ```
    configure terminal
    router bgp 1
    no bgp router-id 9.0.0.1
    ```

5. Run the `show ip bgp` command and verify that the `router-id` does not exist.

### Test result criteria
#### Test pass criteria
This test case is considered passing for the following reasons:

- The output of `show ip bgp` contains 9.0.0.1 after applying the BGP configurations.
- The `router-id` 9.0.0.1 does not exist in the `show ip bgp` command output after applying the `no bgp router-id` command.

#### Test fail criteria
This test case is considered failing for the following reasons:

- The BGP daemon is not running on the switch.
- The `router-id` is not present in the `show ip bgp` command output after applying the BGP configurations.
- The `router-id` still exists in the `show ip bgp` command output after applying the `no bgp router-id` command.





## Show BGP neighbors
### Objective
This test case verifies the `show bgp neighbors` command by configuring or unconfiguring neighbors and confirming the results in the `show bgp neighbors` command output.

### Requirements

Physical or virtual switches

### Setup
#### Topology diagram

```ditaa
    +----------------+
    |                |
    |                |
    |     Switch     |
    |                |
    |                |
    +----------------+
```

#### Test Setup
**Switch** is configured with:

```
router bgp 1
    neighbor 1.1.1.1 remote-as 1111
```

### Description
1. Apply BGP configurations in `vtysh` for the switch with the following commands:

    ***Switch***

    ```
    configure terminal
    router bgp 1
    neighbor 1.1.1.1 remote-as 1111
    ```

2. Verify that the neighbor IP address, remote-as, TCP port number, and keep-alive count values are displayed correctly in the `show bgp neighbors` command output.
3. Remove the neighbor configuration via `vtysh` with the following commands:

    ***Switch***

    ```
    configure terminal
    router bgp 1
    no neighbor 1.1.1.1
    ```

4. Verify that the neighbor IP address, remote-as, TCP port number, and keep-alive count are not displayed in the `show bgp neighbors` command output.

### Test result criteria
#### Test pass criteria
This test case is considered passing for the following reasons:

- The output of `show bgp neighbors` contains the neighbor IP address, remote-as, TCP port number, and keep-alive count after applying the BGP configurations.
- The output of `show bgp neighbors` does not contain the neighbor IP address, remote-as, TCP port number, and keep-alive count after applying the `no neighbor` command.

#### Test fail criteria
This test case is considered failing for the following reasons:

- The output of `show bgp neighbors` does not contain the neighbor IP address, remote-as, TCP port number, and keep-alive count after applying the BGP configurations.
- The output of `show bgp neighbors` contains the neighbor IP address, remote-as, TCP port number, and keep-alive count after applying the `no neighbor` command.





## Show IP BGP
### Objective
This test case verifies the `show ip bgp` command by confirming the received route after configuring and removing the neighbor configurations.

### Requirements

Physical or virtual switches

### Setup
#### Topology diagram

```ditaa
    +----------------+         +----------------+
    |                |         |                |
    |                |         |                |
    |    Switch 1    +---------+    Switch 2    |
    |                |         |                |
    |                |         |                |
    +----------------+         +----------------+
```

#### Test setup
**Switch 1** is configured with:

```
!
interface 1
    no shutdown
    ip address 9.0.0.1/8
!
router bgp 1
    bgp router-id 9.0.0.1
    network 11.0.0.0/8
    neighbor 9.0.0.2 remote-as 2
```

**Switch 2** is configured with:

```
!
interface 1
    no shutdown
    ip address 9.0.0.2/8
!
router bgp 2
    bgp router-id 9.0.0.2
    network 12.0.0.0/8
    neighbor 9.0.0.1 remote-as 1
```

### Description
1. Configure switches 1 and 2 with **9.0.0.1/8** and **9.0.0.2/8**, respectively, in `vtysh` with the following commands:

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

2. Verify that the BGP processes are running on the switches by confirming a non-null value after executing `pgrep -f bgpd` on the switches.
3. Apply BGP configurations in `vtysh` for each switch with the following commands:

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

4. Verify all BGP configurations by comparing the expected values against the results of the `show running-config` command output.
5. Verify that the `show ip bgp` command works by confirming the route advertised from the neighbor exists in the output on Switch 1.
6. Remove the neighbor configuration on Switch 1 by issuing the following commands in `vtysh`:

    **Switch 1**

    ```
    configure terminal
    router bgp 1
    no neighbor 9.0.0.2
    ```

7. Verify that the network advertised from Switch 2 does not exist in the `show ip bgp` command output when executed on Switch 1.

### Test result criteria
#### Test pass criteria

For the `neighbor remote-as` command, this test case is considered passing if the advertised routes of each peer exists in the `show ip bgp` command output on both switches.

The network and next hop route, as returned from the `show ip bgp` command, must match the information as configured on the peer.

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

Applying the `no neighbor` command causes the route from the output of the `show ip bgp` command to be removed.

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

#### Test fail criteria
This test case is considered failing for the following reasons:

- The advertised routes from the peers are not present in the `show ip bgp` command output.
- The BGP daemon is not running on at least one of the switches.
- The advertised peer routes are still present in the `show ip bgp` command output after applying the `no neighbor` command.





## BGP show running config
### Objective
This test case verifies the `show running-config` by applying BGP configurations and confirming the results against the `show running-config` command output.

### Requirements

Physical or virtual switches

### Setup
#### Topology diagram

```ditaa
    +----------------+
    |                |
    |                |
    |     Switch     |
    |                |
    |                |
    +----------------+
```

#### Test setup
**Switch** is configured with:

```
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

### Description
1. Verify that the BGP process is running on the switch by confirming a non-null value after executing `pgrep -f bgpd` on the switch.
2. Apply BGP configurations in `vtysh` for the Switch with the following commands:

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

3. Verify all BGP configurations, including `timers bgp` by comparing the expected values against the  `show running-config` command output.

### Test result criteria
#### Test pass criteria
This test case is considered passing if the output of `show running-config` contains all configurations.

#### Test fail criteria
This test case is considered failing for the following reasons:

- The BGP daemon is not running on the switch.
- At least one configuration is missing from the `show running-config` command output.





## Timers BGP configuration
### Objective
This test case verifies the BGP timers command by configuring or unconfiguring `timers bgp` and by confirming against the `show running-config` command output.

### Requirements

Physical or virtual switches

### Setup
#### Topology diagram

```ditaa
    +----------------+
    |                |
    |                |
    |     Switch     |
    |                |
    |                |
    +----------------+
```

#### Test setup
**Switch** is configured with:

```
router bgp 1
    timers bgp 5 10
```

### Description
1. Verify that the BGP process is running on the switch by confirming a non-null value after executing `pgrep -f bgpd` on the Switch.
2. Apply BGP configurations in `vtysh` for the switch with the following commands:

    ***Switch***

    ```
    configure terminal
    router bgp 1
    timers bgp 5 10
    ```

3. Verify all BGP configurations, including `timers bgp` by comparing the expected values against the  `show running-config` command output.
4. Apply the `no timers bgp` command via `vtysh` with the following commands:

    ```
    configure terminal
    router bgp 1
    no timers bgp
    ```

5. Run the `show running-config` command and verify that the `timers bgp` configuration does not exist.

### Test result criteria
#### Test pass criteria
This test case is considered passing if the output of `show running-config` contains `timers bgp` configuration after `timers bgp` is configured.

Setting `no timers bgp` removes the `timers bgp` configuration and it must not be displayed in the `show running-config` command output.

#### Test fail criteria
This test case is considered failing for the following reasons:

- The BGP daemon is not running on the Switch.
- The BGP configurations are not applied successfully.
- The `timers bgp` configuration still exists in the `show running-config` command output after applying the `no timers bgp` configuration command.
