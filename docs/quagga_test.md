# Quagga Test Cases

## Contents

- [Zebra update](#zebra-update)
- [Topology with ecmp routes](#topology-with-ecmp-routes)

##  Zebra update
### Objective
Test case verifies zebra update of selected column in DB when static routes are added.
### Requirements
- Virtual Mininet Test Setup
- **CT File**: ops-quagga/zebra/test_zebra_ct_fib_selection.py (Route Table Update)

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
* Add the static routes on the 2 switches to be able to reach the end hosts
* Configure the end hosts with valid IP addresses
* Dump the route table in the db using `ovsdb-client dump`
### Test Result Criteria
#### Test Pass Criteria
Verify that the selected column in the Route table for the rows with static routes are set to **true**
#### Test Fail Criteria

##  Topology with ecmp routes
### Objective
Test case checks for connectivity in topology with 3 host and 4 switches
### Requirements
- Virtual Mininet Test Setup
- **CT File**: ops-quagga/zebra/test_zebra_ct_fib_selection.py (Route Table Update)

### Setup

#### Topology Diagram
[TOPLOGY DIAGRAM MISSING]

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
