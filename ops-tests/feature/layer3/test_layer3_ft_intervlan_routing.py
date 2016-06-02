# -*- coding: utf-8 -*-

# Copyright (C) 2015-2016 Hewlett Packard Enterprise Development LP
#
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from layer3_common import L3
from time import sleep

TOPOLOGY = """
# +-------+                        +-------+
# |  hs1  <---+   +--------+   +--->  hs3  |
# +-------+   +--->        <---+   +-------+
#                 |  ops1  |
# +-------+   +--->        <---+   +-------+
# |  hs2  <---+   +--------+   +--->  hs4  |
# +-------+                        +-------+

# Nodes
[type=openswitch] ops1
[type=host] hs1
[type=host] hs2
[type=host] hs3
[type=host] hs4

# Links
ops1:if01 -- hs1:eth0
ops1:if02 -- hs2:eth0
ops1:if03 -- hs3:eth0
ops1:if04 -- hs4:eth0
"""


def test_intervlan_routing(topology, step):
    """
    Verify intervlan routing.
    """

    ops1 = topology.get('ops1')
    hs1 = topology.get('hs1')
    hs2 = topology.get('hs2')
    hs3 = topology.get('hs3')
    hs4 = topology.get('hs4')

    assert ops1 is not None
    assert hs1 is not None
    assert hs2 is not None
    assert hs3 is not None
    assert hs4 is not None

    # ----------Configure Switches and Hosts----------

    step('Configure Switches and Hosts')
    L3.switch_add_vlan(ops1, 10)
    L3.switch_add_vlan(ops1, 20)

    L3.switch_add_vlan_port(ops1, 10, 'if01')
    L3.switch_add_vlan_port(ops1, 10, 'if02')
    L3.switch_add_vlan_port(ops1, 20, 'if03')

    L3.switch_cfg_vlan(ops1, 10, '10.0.0.1/24', '1000::1/120')
    L3.switch_cfg_vlan(ops1, 20, '20.0.0.1/24', '2000::1/120')

    L3.switch_cfg_iface(ops1, 'if04', '30.0.0.1/24', '3000::1/120')
    sleep(10)

    L3.host_cfg_iface(hs1, 'eth0', '10.0.0.9/24', '1000::9/120')
    L3.host_cfg_iface(hs2, 'eth0', '10.0.0.10/24', '1000::10/120')
    L3.host_cfg_iface(hs3, 'eth0', '20.0.0.10/24', '2000::10/120')
    L3.host_cfg_iface(hs4, 'eth0', '30.0.0.10/24', '3000::10/120')

    L3.host_add_route(hs1, '0.0.0.0/0', '10.0.0.1')
    L3.host_add_route(hs2, '0.0.0.0/0', '10.0.0.1')
    L3.host_add_route(hs3, '0.0.0.0/0', '20.0.0.1')
    L3.host_add_route(hs4, '0.0.0.0/0', '30.0.0.1')
    L3.host_add_route(hs1, '::/0', '1000::1')
    L3.host_add_route(hs2, '::/0', '1000::1')
    L3.host_add_route(hs3, '::/0', '2000::1')
    L3.host_add_route(hs4, '::/0', '3000::1')

    # ----------Ping after configuring vlan----------
    while True:
        sleep(10)

    step('Ping after configuring vlan')
    L3.host_ping_expect_success(1, hs1, hs2, '10.0.0.10')
    L3.host_ping_expect_success(1, hs1, hs3, '20.0.0.10')
    L3.host_ping_expect_success(1, hs1, hs4, '30.0.0.10')
    L3.host_ping_expect_success(1, hs1, hs2, '1000::10')
    L3.host_ping_expect_success(1, hs1, hs3, '2000::10')
    L3.host_ping_expect_success(1, hs1, hs4, '3000::10')

    # ----------Remove vlans----------

    step('Remove vlans')
    L3.switch_remove_vlan(ops1, "10")
    L3.switch_remove_vlan(ops1, "20")

    # ----------Ping after removing vlan----------

    step('Ping after removing vlan')
    L3.host_ping_expect_failure(1, hs1, hs2, '10.0.0.10')
    L3.host_ping_expect_failure(1, hs1, hs3, '20.0.0.10')
    L3.host_ping_expect_failure(1, hs1, hs2, '1000::10')
    L3.host_ping_expect_failure(1, hs1, hs3, '2000::10')
