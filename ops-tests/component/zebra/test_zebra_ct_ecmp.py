# -*- coding: utf-8 -*-

# (c) Copyright 2015-2016 Hewlett Packard Enterprise Development LP
#
# GNU Zebra is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2, or (at your option) any
# later version.
#
# GNU Zebra is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Zebra; see the file COPYING.  If not, write to the Free
# Software Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.

from helpers_routing import (
    verify_show_ip_route,
    verify_show_ipv6_route,
    verify_show_rib
)
from pytest import mark

TOPOLOGY = """
#               +-------+     +-------+
# +-------+     |       <----->  hs2  |
# |  hs1  <----->       |     +-------+
# +-------+     |  sw1  <----+
#               |       |    | +-------+
#               |       <-+  +->       |    +-------+
#               +-------+ |    |  sw2  <---->  hs3  |
#                         +---->       |    +-------+
#                              +-------+

# Nodes
[type=openswitch name="Switch 1"] sw1
[type=openswitch name="Switch 2"] sw2
[type=host name="Host 1"] hs1
[type=host name="Host 2"] hs2
[type=host name="Host 3"] hs3

# Links
sw1:if01 -- hs1:if01
sw1:if03 -- sw2:if01
sw1:if04 -- sw2:if02
sw1:if02 -- hs2:if01
sw2:if03 -- hs3:if01
"""


def _configure_switches(topology, step):
    sw1 = topology.get("sw1")
    assert sw1 is not None
    sw2 = topology.get("sw2")
    assert sw2 is not None
    step('1-Configuring Switches')
    # Configure switch sw1
    sw1("configure terminal")

    # Configure interface 1 on switch sw1
    sw1("interface 1")
    sw1("ip address 10.0.10.2/24")
    sw1("no shut")
    sw1("exit")

    # Configure interface 2 on switch sw1
    sw1("interface 2")
    sw1("ip address 10.0.20.2/24")
    sw1("no shut")
    sw1("exit")

    # Configure interface 3 on switch sw1
    sw1("interface 3")
    sw1("ip address 10.0.30.1/24")
    sw1("no shut")
    sw1("exit")

    # Configure interface 4 on switch sw1
    sw1("interface 4")
    sw1("ip address 10.0.40.1/24")
    sw1("no shut")
    sw1("exit")

    # Populate the expected RIB ("show rib") route dictionary for the connected
    # IPv4 route for layer-3 interface '1'.
    sw1_rib_ipv4_layer3_connected_route_primary_1 = dict()
    sw1_rib_ipv4_layer3_connected_route_primary_1['Route'] = '10.0.10.0/24'
    sw1_rib_ipv4_layer3_connected_route_primary_1['NumberNexthops'] = '1'
    sw1_rib_ipv4_layer3_connected_route_primary_1['1'] = dict()
    sw1_rib_ipv4_layer3_connected_route_primary_1['1']['Distance'] = '0'
    sw1_rib_ipv4_layer3_connected_route_primary_1['1']['Metric'] = '0'
    sw1_rib_ipv4_layer3_connected_route_primary_1['1']['RouteType'] = 'connected'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # connected IPv4 route for layer-3 interface '1'.
    sw1_fib_ipv4_layer3_connected_route_primary_1 = sw1_rib_ipv4_layer3_connected_route_primary_1

    # Populate the expected RIB ("show rib") route dictionary for the connected
    # IPv4 route for layer-3 interface '2'.
    sw1_rib_ipv4_layer3_connected_route_primary_2 = dict()
    sw1_rib_ipv4_layer3_connected_route_primary_2['Route'] = '10.0.20.0/24'
    sw1_rib_ipv4_layer3_connected_route_primary_2['NumberNexthops'] = '1'
    sw1_rib_ipv4_layer3_connected_route_primary_2['2'] = dict()
    sw1_rib_ipv4_layer3_connected_route_primary_2['2']['Distance'] = '0'
    sw1_rib_ipv4_layer3_connected_route_primary_2['2']['Metric'] = '0'
    sw1_rib_ipv4_layer3_connected_route_primary_2['2']['RouteType'] = 'connected'

    # Populate the expected RIB ("show ip route") route dictionary for the connected
    # IPv4 route for layer-3 interface '2'.
    sw1_fib_ipv4_layer3_connected_route_primary_2 = sw1_rib_ipv4_layer3_connected_route_primary_2

    # Populate the expected RIB ("show rib") route dictionary for the connected
    # IPv4 route for layer-3 interface '3'.
    sw1_rib_ipv4_layer3_connected_route_primary_3 = dict()
    sw1_rib_ipv4_layer3_connected_route_primary_3['Route'] = '10.0.30.0/24'
    sw1_rib_ipv4_layer3_connected_route_primary_3['NumberNexthops'] = '1'
    sw1_rib_ipv4_layer3_connected_route_primary_3['3'] = dict()
    sw1_rib_ipv4_layer3_connected_route_primary_3['3']['Distance'] = '0'
    sw1_rib_ipv4_layer3_connected_route_primary_3['3']['Metric'] = '0'
    sw1_rib_ipv4_layer3_connected_route_primary_3['3']['RouteType'] = 'connected'

    # Populate the expected FIB ("show ip route") route dictionary for the connected
    # IPv4 route for layer-3 interface '3'.
    sw1_fib_ipv4_layer3_connected_route_primary_3 = sw1_rib_ipv4_layer3_connected_route_primary_3

    # Populate the expected RIB ("show rib") route dictionary for the connected
    # IPv4 route for layer-3 interface '4'.
    sw1_rib_ipv4_layer3_connected_route_primary_4 = dict()
    sw1_rib_ipv4_layer3_connected_route_primary_4['Route'] = '10.0.40.0/24'
    sw1_rib_ipv4_layer3_connected_route_primary_4['NumberNexthops'] = '1'
    sw1_rib_ipv4_layer3_connected_route_primary_4['4'] = dict()
    sw1_rib_ipv4_layer3_connected_route_primary_4['4']['Distance'] = '0'
    sw1_rib_ipv4_layer3_connected_route_primary_4['4']['Metric'] = '0'
    sw1_rib_ipv4_layer3_connected_route_primary_4['4']['RouteType'] = 'connected'

    # Populate the expected FIB ("show ip route") route dictionary for the connected
    # IPv4 route for layer-3 interface '4'.
    sw1_fib_ipv4_layer3_connected_route_primary_4 = sw1_rib_ipv4_layer3_connected_route_primary_4

    # Add IPv4 static route on sw1 and sw2
    sw1("ip route 10.0.70.0/24 10.0.30.2")
    sw1("ip route 10.0.70.0/24 10.0.40.2")

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 10.0.70.0/24 and its next-hops.
    sw1_rib_ipv4_layer3_static_route_primary_1 = dict()
    sw1_rib_ipv4_layer3_static_route_primary_1['Route'] = '10.0.70.0/24'
    sw1_rib_ipv4_layer3_static_route_primary_1['NumberNexthops'] = '2'
    sw1_rib_ipv4_layer3_static_route_primary_1['10.0.30.2'] = dict()
    sw1_rib_ipv4_layer3_static_route_primary_1['10.0.30.2']['Distance'] = '1'
    sw1_rib_ipv4_layer3_static_route_primary_1['10.0.30.2']['Metric'] = '0'
    sw1_rib_ipv4_layer3_static_route_primary_1['10.0.30.2']['RouteType'] = 'static'
    sw1_rib_ipv4_layer3_static_route_primary_1['10.0.40.2'] = dict()
    sw1_rib_ipv4_layer3_static_route_primary_1['10.0.40.2']['Distance'] = '1'
    sw1_rib_ipv4_layer3_static_route_primary_1['10.0.40.2']['Metric'] = '0'
    sw1_rib_ipv4_layer3_static_route_primary_1['10.0.40.2']['RouteType'] = 'static'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 10.0.70.0/24 and its next-hops.
    sw1_fib_ipv4_layer3_static_route_primary_1 = sw1_rib_ipv4_layer3_static_route_primary_1

    # Verify route 10.0.10.0/24 and next-hops in RIB and FIB
    aux_route = sw1_fib_ipv4_layer3_connected_route_primary_1["Route"]
    verify_show_ip_route(sw1, aux_route, 'connected', sw1_fib_ipv4_layer3_connected_route_primary_1)
    aux_route = sw1_rib_ipv4_layer3_connected_route_primary_1["Route"]
    verify_show_rib(sw1, aux_route, 'connected', sw1_rib_ipv4_layer3_connected_route_primary_1)

    # Verify route 10.0.20.0/24 and next-hops in RIB and FIB
    aux_route = sw1_fib_ipv4_layer3_connected_route_primary_2["Route"]
    verify_show_ip_route(sw1, aux_route, 'connected', sw1_fib_ipv4_layer3_connected_route_primary_2)
    aux_route = sw1_rib_ipv4_layer3_connected_route_primary_2["Route"]
    verify_show_rib(sw1, aux_route, 'connected', sw1_rib_ipv4_layer3_connected_route_primary_2)

    # Verify route 10.0.30.0/24 and next-hops in RIB and FIB
    aux_route = sw1_fib_ipv4_layer3_connected_route_primary_3["Route"]
    verify_show_ip_route(sw1, aux_route, 'connected', sw1_fib_ipv4_layer3_connected_route_primary_3)
    aux_route = sw1_rib_ipv4_layer3_connected_route_primary_3["Route"]
    verify_show_rib(sw1, aux_route, 'connected', sw1_rib_ipv4_layer3_connected_route_primary_3)

    # Verify route 10.0.40.0/24 and next-hops in RIB and FIB
    aux_route = sw1_fib_ipv4_layer3_connected_route_primary_4["Route"]
    verify_show_ip_route(sw1, aux_route, 'connected', sw1_fib_ipv4_layer3_connected_route_primary_4)
    aux_route = sw1_rib_ipv4_layer3_connected_route_primary_4["Route"]
    verify_show_rib(sw1, aux_route, 'connected', sw1_rib_ipv4_layer3_connected_route_primary_4)

    # Verify route 10.0.70.0/24 and next-hops in RIB and FIB
    aux_route = sw1_fib_ipv4_layer3_static_route_primary_1["Route"]
    verify_show_ip_route(sw1, aux_route, 'static', sw1_fib_ipv4_layer3_static_route_primary_1)
    aux_route = sw1_rib_ipv4_layer3_static_route_primary_1["Route"]
    verify_show_rib(sw1, aux_route, 'static', sw1_rib_ipv4_layer3_static_route_primary_1)

    # Add second ecmp IPv4 static route on sw1 and sw2
    # sw1("ip route 10.0.70.0/24 10.0.40.2")
    # Configure switch sw2
    sw2("configure terminal")

    # Configure interface 1 on switch sw2
    sw2("interface 1")
    sw2("ip address 10.0.30.2/24")
    sw2("no shut")
    sw2("exit")

    # Configure interface 2 on switch sw2
    sw2("interface 2")
    sw2("ip address 10.0.40.2/24")
    sw2("no shut")
    sw2("exit")

    # Configure interface 3 on switch s4
    sw2("interface 3")
    sw2("ip address 10.0.70.2/24")
    sw2("no shut")
    sw2("exit")

    # Populate the expected RIB ("show rib") route dictionary for the connected
    # IPv4 route for layer-3 interface '1'.
    sw2_rib_ipv4_layer3_connected_route_primary_1 = dict()
    sw2_rib_ipv4_layer3_connected_route_primary_1['Route'] = '10.0.30.0/24'
    sw2_rib_ipv4_layer3_connected_route_primary_1['NumberNexthops'] = '1'
    sw2_rib_ipv4_layer3_connected_route_primary_1['1'] = dict()
    sw2_rib_ipv4_layer3_connected_route_primary_1['1']['Distance'] = '0'
    sw2_rib_ipv4_layer3_connected_route_primary_1['1']['Metric'] = '0'
    sw2_rib_ipv4_layer3_connected_route_primary_1['1']['RouteType'] = 'connected'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # connected IPv4 route for layer-3 interface '1'.
    sw2_fib_ipv4_layer3_connected_route_primary_1 = sw2_rib_ipv4_layer3_connected_route_primary_1

    # Populate the expected RIB ("show rib") route dictionary for the connected
    # IPv4 route for layer-3 interface '2'.
    sw2_rib_ipv4_layer3_connected_route_primary_2 = dict()
    sw2_rib_ipv4_layer3_connected_route_primary_2['Route'] = '10.0.40.0/24'
    sw2_rib_ipv4_layer3_connected_route_primary_2['NumberNexthops'] = '1'
    sw2_rib_ipv4_layer3_connected_route_primary_2['2'] = dict()
    sw2_rib_ipv4_layer3_connected_route_primary_2['2']['Distance'] = '0'
    sw2_rib_ipv4_layer3_connected_route_primary_2['2']['Metric'] = '0'
    sw2_rib_ipv4_layer3_connected_route_primary_2['2']['RouteType'] = 'connected'

    # Populate the expected RIB ("show ip route") route dictionary for the connected
    # IPv4 route for layer-3 interface '2'.
    sw2_fib_ipv4_layer3_connected_route_primary_2 = sw2_rib_ipv4_layer3_connected_route_primary_2

    # Populate the expected RIB ("show rib") route dictionary for the connected
    # IPv4 route for layer-3 interface '3'.
    sw2_rib_ipv4_layer3_connected_route_primary_3 = dict()
    sw2_rib_ipv4_layer3_connected_route_primary_3['Route'] = '10.0.70.0/24'
    sw2_rib_ipv4_layer3_connected_route_primary_3['NumberNexthops'] = '1'
    sw2_rib_ipv4_layer3_connected_route_primary_3['3'] = dict()
    sw2_rib_ipv4_layer3_connected_route_primary_3['3']['Distance'] = '0'
    sw2_rib_ipv4_layer3_connected_route_primary_3['3']['Metric'] = '0'
    sw2_rib_ipv4_layer3_connected_route_primary_3['3']['RouteType'] = 'connected'

    # Populate the expected FIB ("show ip route") route dictionary for the connected
    # IPv4 route for layer-3 interface '3'.
    sw2_fib_ipv4_layer3_connected_route_primary_3 = sw2_rib_ipv4_layer3_connected_route_primary_3

    sw2("ip route 10.0.10.0/24 10.0.30.1")
    sw2("ip route 10.0.10.0/24 10.0.40.1")
    sw2("ip route 10.0.20.0/24 10.0.30.1")
    sw2("ip route 10.0.20.0/24 10.0.40.1")

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 10.0.10.0/24 and its next-hops.
    sw2_rib_ipv4_layer3_static_route_primary_1 = dict()
    sw2_rib_ipv4_layer3_static_route_primary_1['Route'] = '10.0.10.0/24'
    sw2_rib_ipv4_layer3_static_route_primary_1['NumberNexthops'] = '2'
    sw2_rib_ipv4_layer3_static_route_primary_1['10.0.30.1'] = dict()
    sw2_rib_ipv4_layer3_static_route_primary_1['10.0.30.1']['Distance'] = '1'
    sw2_rib_ipv4_layer3_static_route_primary_1['10.0.30.1']['Metric'] = '0'
    sw2_rib_ipv4_layer3_static_route_primary_1['10.0.30.1']['RouteType'] = 'static'
    sw2_rib_ipv4_layer3_static_route_primary_1['10.0.40.1'] = dict()
    sw2_rib_ipv4_layer3_static_route_primary_1['10.0.40.1']['Distance'] = '1'
    sw2_rib_ipv4_layer3_static_route_primary_1['10.0.40.1']['Metric'] = '0'
    sw2_rib_ipv4_layer3_static_route_primary_1['10.0.40.1']['RouteType'] = 'static'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 10.0.10.0/24 and its next-hops.
    sw2_fib_ipv4_layer3_static_route_primary_1 = sw2_rib_ipv4_layer3_static_route_primary_1

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 10.0.10.0/24 and its next-hops.
    sw2_rib_ipv4_layer3_static_route_primary_2 = dict()
    sw2_rib_ipv4_layer3_static_route_primary_2['Route'] = '10.0.20.0/24'
    sw2_rib_ipv4_layer3_static_route_primary_2['NumberNexthops'] = '2'
    sw2_rib_ipv4_layer3_static_route_primary_2['10.0.30.1'] = dict()
    sw2_rib_ipv4_layer3_static_route_primary_2['10.0.30.1']['Distance'] = '1'
    sw2_rib_ipv4_layer3_static_route_primary_2['10.0.30.1']['Metric'] = '0'
    sw2_rib_ipv4_layer3_static_route_primary_2['10.0.30.1']['RouteType'] = 'static'
    sw2_rib_ipv4_layer3_static_route_primary_2['10.0.40.1'] = dict()
    sw2_rib_ipv4_layer3_static_route_primary_2['10.0.40.1']['Distance'] = '1'
    sw2_rib_ipv4_layer3_static_route_primary_2['10.0.40.1']['Metric'] = '0'
    sw2_rib_ipv4_layer3_static_route_primary_2['10.0.40.1']['RouteType'] = 'static'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 10.0.10.0/24 and its next-hops.
    sw2_fib_ipv4_layer3_static_route_primary_2 = sw2_rib_ipv4_layer3_static_route_primary_2

    # Verify route 10.0.30.0/24 and next-hops in RIB and FIB
    aux_route = sw2_fib_ipv4_layer3_connected_route_primary_1["Route"]
    verify_show_ip_route(sw2, aux_route, 'connected', sw2_fib_ipv4_layer3_connected_route_primary_1)
    aux_route = sw2_rib_ipv4_layer3_connected_route_primary_1["Route"]
    verify_show_rib(sw2, aux_route, 'connected', sw2_rib_ipv4_layer3_connected_route_primary_1)

    # Verify route 10.0.40.0/24 and next-hops in RIB and FIB
    aux_route = sw2_fib_ipv4_layer3_connected_route_primary_2["Route"]
    verify_show_ip_route(sw2, aux_route, 'connected', sw2_fib_ipv4_layer3_connected_route_primary_2)
    aux_route = sw2_rib_ipv4_layer3_connected_route_primary_2["Route"]
    verify_show_rib(sw2, aux_route, 'connected', sw2_rib_ipv4_layer3_connected_route_primary_2)

    # Verify route 10.0.70.0/24 and next-hops in RIB and FIB
    aux_route = sw2_fib_ipv4_layer3_connected_route_primary_3["Route"]
    verify_show_ip_route(sw2, aux_route, 'connected', sw2_fib_ipv4_layer3_connected_route_primary_3)
    aux_route = sw2_rib_ipv4_layer3_connected_route_primary_3["Route"]
    verify_show_rib(sw2, aux_route, 'connected', sw2_rib_ipv4_layer3_connected_route_primary_3)

    # Verify route 10.0.10.0/24 and next-hops in RIB and FIB
    aux_route = sw2_fib_ipv4_layer3_static_route_primary_1["Route"]
    verify_show_ip_route(sw2, aux_route, 'static', sw2_fib_ipv4_layer3_static_route_primary_1)
    aux_route = sw2_rib_ipv4_layer3_static_route_primary_1["Route"]
    verify_show_rib(sw2, aux_route, 'static', sw2_rib_ipv4_layer3_static_route_primary_1)

    # Verify route 10.0.20.0/24 and next-hops in RIB and FIB
    aux_route = sw2_fib_ipv4_layer3_static_route_primary_2["Route"]
    verify_show_ip_route(sw2, aux_route, 'static', sw2_fib_ipv4_layer3_static_route_primary_2)
    aux_route = sw2_rib_ipv4_layer3_static_route_primary_2["Route"]
    verify_show_rib(sw2, aux_route, 'static', sw2_rib_ipv4_layer3_static_route_primary_2)


def _configure_hosts(topology, step):
    hs1 = topology.get("hs1")
    assert hs1 is not None
    hs2 = topology.get("hs2")
    assert hs2 is not None
    hs3 = topology.get("hs3")
    assert hs3 is not None

    step('2-Configuring hosts')

    # Configure host 1
    hs1.libs.ip.interface('if01', addr="10.0.10.1/24", up=True)

    # Configure host 2
    hs2.libs.ip.interface('if01', addr="10.0.20.1/24", up=True)

    # hs2("ip addr add 10.0.20.1/24 dev if01")
    # hs2("ip addr del 10.0.0.2/8 dev if01")
    # Configure host 3
    hs3.libs.ip.interface('if01', addr="10.0.70.1/24", up=True)

    # hs3("ip addr add 10.0.70.1/24 dev if01")
    # hs3("ip addr del 10.0.0.3/8 dev if01")
    # Add V4 default gateway on hosts hs1 and hs2
    hs1("ip route add 10.0.30.0/24 via 10.0.10.2")
    hs1("ip route add 10.0.40.0/24 via 10.0.10.2")
    hs1("ip route add 10.0.70.0/24 via 10.0.10.2")
    hs2("ip route add 10.0.30.0/24 via 10.0.20.2")
    hs2("ip route add 10.0.40.0/24 via 10.0.10.2")
    hs2("ip route add 10.0.70.0/24 via 10.0.20.2")
    hs3("ip route add 10.0.10.0/24 via 10.0.70.2")
    hs3("ip route add 10.0.20.0/24 via 10.0.70.2")
    hs3("ip route add 10.0.30.0/24 via 10.0.70.2")
    hs3("ip route add 10.0.40.0/24 via 10.0.70.2")


def _v4_route_ping_test(topology, step):
    hs1 = topology.get("hs1")
    assert hs1 is not None
    hs2 = topology.get("hs2")
    assert hs2 is not None
    step('3-IPv4 Ping test')

    # Ping host3 from host1
    ping = hs1.libs.ping.ping(5, '10.0.70.1')
    assert ping['transmitted'] >= 3 and ping['received'] >= 3

    # Ping host3 from host2
    ping = hs2.libs.ping.ping(5, '10.0.70.1')
    assert ping['transmitted'] >= 3 and ping['received'] >= 3


def _v4_route_delete_ping_test(topology, step):
    sw1 = topology.get("sw1")
    assert sw1 is not None
    hs1 = topology.get("hs1")
    assert hs1 is not None
    step('4-Verify TCPDUMP on SW2 to confirm ecmp load balance')
    step('\n######### Verify deletion of IPv4 static routes ##########\n')

    # Delete IPv4 route on switchs1 towards host2 network
    # sw1("configure terminal")
    sw1("no ip route 10.0.70.0/24 10.0.40.2")
    sw1("no ip route 10.0.70.0/24 10.0.30.2")

    # Ping host1 from host2
    ping = hs1.libs.ping.ping(5, '10.0.70.1')
    assert ping['transmitted'] is 5 and ping['received'] is 0


@mark.timeout(300)
def test_zebra_ct_ecmp(topology, step):
    _configure_switches(topology, step)
    _configure_hosts(topology, step)
    _v4_route_ping_test(topology, step)
    _v4_route_delete_ping_test(topology, step)
