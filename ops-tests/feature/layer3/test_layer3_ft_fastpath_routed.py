# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016 Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from pytest import mark
from layer3_common import L3
from time import sleep

TOPOLOGY = """
# +-------+     +--------+     +--------+     +-------+
# |  hs1  <----->  ops1  <----->  ops2  <----->  hs2  |
# +-------+     +--------+     +--------+     +-------+

# Nodes
[type=openswitch] ops1
[type=openswitch] ops2
[type=host] hs1
[type=host] hs2

# Links
hs1:eth0 -- ops1:if01
ops1:if02 -- ops2:if02
ops2:if01 -- hs2:eth0
"""


@mark.platform_incompatible(['docker'])
def test_fastpath_routed(topology, step):
    """
    OpenSwitch Test for simple static routes between nodes.
    """

    hs1 = topology.get('hs1')
    hs2 = topology.get('hs2')
    ops1 = topology.get('ops1')
    ops2 = topology.get('ops2')

    assert hs1 is not None
    assert hs2 is not None
    assert ops1 is not None
    assert ops2 is not None

    # ----------Configure Switches and Hosts----------

    step('Configure Switches and Hosts')
    L3.switch_cfg_iface(ops1, 'if01', '10.0.10.2/24', '2000::2/120')
    L3.switch_cfg_iface(ops1, 'if02', '10.0.20.1/24', '2001::1/120')
    L3.switch_cfg_iface(ops2, 'if01', '10.0.30.2/24', '2002::2/120')
    L3.switch_cfg_iface(ops2, 'if02', '10.0.20.2/24', '2001::2/120')
    sleep(10)

    L3.host_cfg_iface(hs1, 'eth0', '10.0.10.1/24', '2000::1/120')
    L3.host_cfg_iface(hs2, 'eth0', '10.0.30.1/24', '2002::1/120')

    L3.host_add_route(hs1, '10.0.20.0/24', '10.0.10.2')
    L3.host_add_route(hs1, '10.0.30.0/24', '10.0.10.2')
    L3.host_add_route(hs2, '10.0.10.0/24', '10.0.30.2')
    L3.host_add_route(hs2, '10.0.20.0/24', '10.0.30.2')
    L3.host_add_route(hs1, '2001::/120', '2000::2')
    L3.host_add_route(hs1, '2002::/120', '2000::2')
    L3.host_add_route(hs2, '2000::/120', '2002::2')
    L3.host_add_route(hs2, '2001::/120', '2002::2')

    # ----------Add IPv4 and IPv6 static routes to switches----------

    step('Add IPv4 and IPv6 static routes to switches')
    L3.switch_add_ipv4_route(ops1, '10.0.30.0/24', '10.0.20.2')
    L3.switch_add_ipv4_route(ops2, '10.0.10.0/24', '10.0.20.1')
    L3.switch_add_ipv6_route(ops1, '2002::/120', '2001::2')
    L3.switch_add_ipv6_route(ops2, '2000::/120', '2001::1')

    # ----------Test Ping after adding static routes----------

    step('Test Ping after adding static routes')
    L3.host_ping_expect_success(1, hs1, hs2, '10.0.30.1')
    L3.host_ping_expect_success(1, hs1, hs2, '2002::1')
    L3.host_ping_expect_success(1, hs2, hs1, '10.0.10.1')
    L3.host_ping_expect_success(1, hs2, hs1, '2000::1')

    # ----------Verifying Hit bit in ASIC for IPv4 ping----------

    step('Verifying Hit bit in ASIC for IPv4 ping')
    verify_hit_bit(ops1, '10.0.30.0')
    verify_hit_bit(ops2, '10.0.10.0')

    # ----------Remove IPv4 and IPv6 static routes from switches----------

    step('Remove IPv4 and IPv6 static routes from switches')
    L3.switch_remove_ipv4_route(ops1, '10.0.30.0/24', '10.0.20.2')
    L3.switch_remove_ipv4_route(ops2, '10.0.10.0/24', '10.0.20.1')
    L3.switch_remove_ipv6_route(ops1, '2002::/120', '2001::2')
    L3.switch_remove_ipv6_route(ops2, '2000::/120', '2001::1')

    # ----------Test Ping after removing static routes----------

    step('RTest Ping after removing static routes')
    L3.host_ping_expect_failure(1, hs1, hs2, '10.0.30.1')
    L3.host_ping_expect_failure(1, hs1, hs2, '2002::1')
    L3.host_ping_expect_failure(1, hs2, hs1, '10.0.10.1')
    L3.host_ping_expect_failure(1, hs2, hs1, '2000::1')


def verify_hit_bit(switch, dest_subnet):
    header = 'Verifying HIT Bit for IPv4 ping on {0}'
    print(header.format(switch.identifier))

    result = switch('ovs-appctl plugin/debug l3route', shell='bash')
    assert result, 'could not get l3route debug\n'

    rows = result.split('\n')
    route_row = None
    for row in rows:
        if dest_subnet in row:
            route_row = row

    assert route_row is not None, 'route not programmed in ASIC\n'

    columns = route_row.split()
    route_hit = columns[5]
    assert route_hit == 'Y', 'route not selected in ASIC\n'