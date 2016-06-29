# -*- coding: utf-8 -*-

# Copyright (C) 2016 Hewlett Packard Enterprise Development LP
# All Rights Reserved.
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

import layer3_common as lib
from time import sleep
from pytest import mark

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


@mark.timeout(500)
def test_static_routes(topology, step):
    """
    Test for static routes.
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
    lib.switch_cfg_iface(ops1, 'if01', '10.0.10.2/24', '2000::2/120')
    lib.switch_cfg_iface(ops1, 'if02', '10.0.20.1/24', '2001::1/120')
    lib.switch_cfg_iface(ops2, 'if01', '10.0.30.2/24', '2002::2/120')
    lib.switch_cfg_iface(ops2, 'if02', '10.0.20.2/24', '2001::2/120')
    sleep(15)

    lib.host_cfg_iface(hs1, 'eth0', '10.0.10.1/24', '2000::1/120')
    lib.host_cfg_iface(hs2, 'eth0', '10.0.30.1/24', '2002::1/120')

    lib.switch_add_ipv4_route(ops1, '10.0.30.0/24', '10.0.20.2')
    lib.switch_add_ipv6_route(ops1, '2002::/120', '2001::2')
    lib.switch_add_ipv4_route(ops2, '10.0.10.0/24', '10.0.20.1')
    lib.switch_add_ipv6_route(ops2, '2000::/120', '2001::1')

    lib.host_add_route(hs1, '10.0.20.0/24', '10.0.10.2')
    lib.host_add_route(hs1, '10.0.30.0/24', '10.0.10.2')
    lib.host_add_route(hs1, '2001::/120', '2000::2')
    lib.host_add_route(hs1, '2002::/120', '2000::2')
    lib.host_add_route(hs2, '10.0.10.0/24', '10.0.30.2')
    lib.host_add_route(hs2, '10.0.20.0/24', '10.0.30.2')
    lib.host_add_route(hs2, '2000::/120', '2002::2')
    lib.host_add_route(hs2, '2001::/120', '2002::2')

    # ----------Test IPv4 ping----------

    step('Test IPv4 ping')
    lib.host_ping_expect_success(10, hs1, ops1, '10.0.10.2')
    lib.host_ping_expect_success(10, hs2, ops2, '10.0.30.2')
    lib.switch_ping_expect_success(10, ops1, ops2, '10.0.20.2')
    lib.host_ping_expect_success(10, hs1, hs2, '10.0.30.1')
    lib.host_ping_expect_success(10, hs2, hs1, '10.0.10.1')

    # ----------Test IPv6 ping----------

    step('Test IPv6 ping')
    lib.host_ping_expect_success(10, hs1, ops1, '2000::2')
    lib.host_ping_expect_success(10, hs2, ops2, '2002::2')
    lib.switch_ping_expect_success(10, ops1, ops2, '2001::2')
    lib.host_ping_expect_success(10, hs1, hs2, '2002::1')
    lib.host_ping_expect_success(10, hs2, hs1, '2000::1')

    # ----------Verify deletion of IPv4 static routes----------

    step('Verify deletion of IPv4 static routes')
    lib.host_ping_expect_success(10, hs1, hs2, '10.0.30.1')
    lib.switch_remove_ipv4_route(ops1, '10.0.30.0/24', '10.0.20.2')
    lib.host_ping_expect_failure(10, hs1, hs2, '10.0.30.1')

    # ----------Verify deletion of IPv6 static routes----------

    step('Verify deletion of IPv6 static routes')
    lib.host_ping_expect_success(10, hs1, hs2, '2002::1')
    lib.switch_remove_ipv6_route(ops1, '2002::/120', '2001::2')
    lib.host_ping_expect_failure(10, hs1, hs2, '2002::1')
