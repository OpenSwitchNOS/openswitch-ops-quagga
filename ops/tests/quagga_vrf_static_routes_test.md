
Component Test Cases
=======
The Following test cases verify VRF aware static routes configuration on the switch.

- [Test Cases](#test-cases)
	- [Test case 1.01 : Configure IPv4 static route with VRF and Verify configuration in show running output and route tables](#test-case-1.01-:-configure-IPv4-static-routes-with-VRF-and-verify-configuration-in-show-running-output-and-route-tables)
	- [Test case 1.02 : Un-Configure IPv4 static route with VRF and Verify respective changes in show running output and route tables](#test-case-1.02-:-Un-configure-IPv4-static-routes-with-VRF-and-verify-respective-changes-in-show-running-output-and-route-tables)


##  Test case 1.01 : Configure IPv4 static route with VRF and Verify configuration in show running output and route tables ##
### Objective ###
Configure VRF aware IPv4 static route given the nexthop ip and VRF name and verify running config and route tables. 
### Requirements ###
The requirements for this test case are:
 - Switch NOS docker instance

### Setup ###
A DUT with NOS image.
#### Topology Diagram ####
#### Test Setup ####
              +-----------------------+
              |                       |
              |  NOS switch instance  |
              |                       |
              +-----------------------+
### Description ###
Basic setup configuration: Configure a VRF on the OVSDB, so that a namespace shall be created for the VRF. Then attach an interface to the VRF. 

Configure IPv4 static route for that interface ip address and verify running config and route tables.


### Test Result Criteria ###
Once configuration is done, RIB table will get updated and zebra will mark that route selected. Show running will have the CLI displayed.

The cases in which the above behaviour would fail is:
	- OVSDB not reachable.
	- Zebra Daemon responsble to handle routes is killed

#### Test Pass Criteria ####
A vrf aware Route should get added in routing table. 
#### Test Fail Criteria ####
No route is found in that VRF routing table.

##  Test case 1.02 : Un-Configure IPv4 static route with VRF and Verify respective changes in show running output and route tables ##
### Objective ###
Un-Configure VRF aware IPv4 static route given the nexthop ip and VRF name and verify running config and route tables.
### Requirements ###
The requirements for this test case are:
 - Switch NOS docker instance

### Setup ###
A DUT with NOS image.

#### Topology Diagram ####
#### Test Setup ####
              +-----------------------+
              |                       |
              |  NOS switch instance  |
              |                       |
              +-----------------------+
### Description ###

Un-Configure IPv4 static route given the VRF name and nexthop ip and verify running config and route tables.

### Test Result Criteria ###
Once unconfiguration is done, the routing table will no longer have the route and zebra will do the cleanup. Show running will not have the CLI displayed.

The cases in which the above behaviour would fail is:
	- OVSDB not reachable.
	- Zebra Daemon responsble to handle routes is killed

#### Test Pass Criteria ####
The vrf aware Route should get deleted in routing table. 
#### Test Fail Criteria ####
The vrf aware Route still present in routing table or RIB. 

