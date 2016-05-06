#-*- coding: utf-8 -*-
#
#Copyright (C) 2015 Hewlett Packard Enterprise Development LP
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing,
#software distributed under the License is distributed on an
#"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#KIND, either express or implied.  See the License for the
#specific language governing permissions and limitations
#under the License.

from .ospf_configs import configure_interface, configure_ospf_router
from .ospf_configs import wait_for_adjacency
from .ospf_configs import wait_for_2way_state, get_neighbor_state
from pytest import fixture

TOPOLOGY = """
#                         sw4(L2)
#                   1 __|  |_ 2 |__3
#                    |       |     |
#                 1  |       | 1   |1
#                   sw1     sw2    sw3
#

# Nodes
[type=openswitch name="Switch 1"] sw1
[type=openswitch name="Switch 2"] sw2
[type=openswitch name="Switch 3"] sw3
[type=openswitch name="Switch 4"] sw4

# Links
sw1:1 -- sw4:1
sw2:1 -- sw4:2
sw3:1 -- sw4:3
"""

# Generic macros used accross the test cases
SW1_INTF1_IPV4_ADDR = "10.10.10.1/8"
SW2_INTF1_IPV4_ADDR = "10.10.10.2/8"
SW3_INTF1_IPV4_ADDR = "10.10.10.3/8"

SW1_INTF1 = "1"
SW2_INTF1 = "1"
SW3_INTF1 = "1"

SW1_ROUTER_ID = "2.2.2.2"
SW2_ROUTER_ID = "4.4.4.4"
SW3_ROUTER_ID = "1.1.1.1"

OSPF_AREA_1 = "1"


@fixture(scope='module')
def configuration(topology, request):
    sw1 = topology.get('sw1')
    sw2 = topology.get('sw2')
    sw3 = topology.get('sw3')
    sw4 = topology.get('sw4')

    assert sw1 is not None
    assert sw2 is not None
    assert sw3 is not None
    assert sw4 is not None

    # Configuring ip address for sw1, sw2 and sw3
    configure_interface(sw1, SW1_INTF1, SW1_INTF1_IPV4_ADDR)
    configure_interface(sw2, SW2_INTF1, SW2_INTF1_IPV4_ADDR)
    configure_interface(sw3, SW3_INTF1, SW3_INTF1_IPV4_ADDR)

    # Configuring ospf with network command in sw1, sw2 and sw3
    configure_ospf_router(sw1, SW1_ROUTER_ID, SW1_INTF1_IPV4_ADDR, OSPF_AREA_1)
    configure_ospf_router(sw2, SW2_ROUTER_ID, SW2_INTF1_IPV4_ADDR, OSPF_AREA_1)
    configure_ospf_router(sw3, SW3_ROUTER_ID, SW3_INTF1_IPV4_ADDR, OSPF_AREA_1)


# Test case [3.01] : Test case to verify that the DR and BDR is selected
def test_ospfv2_ft_election_dr_bdr(topology, configuration, step):
    sw1 = topology.get('sw1')
    sw2 = topology.get('sw2')
    sw3 = topology.get('sw3')
    sw4 = topology.get('sw4')

    assert sw1 is not None
    assert sw2 is not None
    assert sw3 is not None
    assert sw4 is not None

    step('###### Step 1 - configuring sw4 as L2 switch ######')
    with sw4.libs.vtysh.ConfigInterface('1') as ctx:
        ctx.no_routing()
        ctx.no_shutdown()

    with sw4.libs.vtysh.ConfigInterface('2') as ctx:
        ctx.no_routing()
        ctx.no_shutdown()

    with sw4.libs.vtysh.ConfigInterface('3') as ctx:
        ctx.no_routing()
        ctx.no_shutdown()

    step('###### Step 2 - Verifying adjacency between switches ######')
    retval = wait_for_adjacency(sw3, SW2_ROUTER_ID)
    if retval:
        step('Adjacency formed between SW3 and SW2(router-id = 4.4.4.4)')
    else:
        assert False, "Failed to form adjacency between"
        "SW3 and SW2(router-id = %s)" % SW2_ROUTER_ID

    retval = wait_for_adjacency(sw1, SW2_ROUTER_ID)
    if retval:
        step('Adjacency formed between SW1 and SW2(router-id = 4.4.4.4)')
    else:
        assert False, "Failed to form adjacency between"
        "SW1 and SW2(router-id = %s)" % SW2_ROUTER_ID

    step('###### Step 3 - Verifying states of switches ######')
    retval = wait_for_2way_state(sw2, SW1_ROUTER_ID)
    if retval:
        state = get_neighbor_state(sw2, SW1_ROUTER_ID)
        if state == "Backup":
            step('SW1 is in Backup DR state')
        else:
            assert False, "SW1 is not in Backup DR state"
    else:
        assert False, "SW1 is not in correct state"

    retval = wait_for_2way_state(sw3, SW2_ROUTER_ID)
    if retval:
        state = get_neighbor_state(sw3, SW2_ROUTER_ID)
        if (state == "DR"):
            step('SW2 is in DR state')
        else:
            assert False, "SW2 is not in DR state"
    else:
        assert False, "SW2 is not in correct state"

    retval = wait_for_2way_state(sw1, SW3_ROUTER_ID)
    if retval:
        state = get_neighbor_state(sw1, SW3_ROUTER_ID)
        if (state == "DROther"):
            step('Switch3 is in DROther state')
        else:
            assert False, "SW3 is not in DROther state"
    else:
        assert False, "SW3 is not in correct state"

    step('###### TC- 3.01  PASSED ######')
