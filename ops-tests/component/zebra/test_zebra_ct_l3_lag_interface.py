# -*- coding: utf-8 -*-
#
# (c)Copyright 2015 Hewlett Packard Enterprise Development LP
#
# GNU Zebra is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2, or (at your option) any
# later version.
#
# GNU Zebra is distributed in the hope that it will be useful, but
# WITHoutput ANY WARRANTY; withoutput even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Zebra; see the file COPYING. If not, write to the Free
# Software Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.from re import match
# Topology definition. the topology contains two back to back switches
# having four links between them.


from zebra_routing import (
    verify_show_ip_route,
    verify_show_ipv6_route,
    verify_show_rib,
    ZEBRA_DEFAULT_TIMEOUT
)
from pytest import mark

TOPOLOGY = """
# +-------+    +-------+
# |       <---->       |
# |       <---->       |
# |  sw1  |    |  sw2  |
# |       <---->       |
# |       <---->       |
# +-------+    +-------+

# Nodes
[type=openswitch name="Switch 1"] sw1
[type=openswitch name="Switch 2"] sw2

# Links
sw1:if01 -- sw2:if01
sw1:if02 -- sw2:if02
sw1:if03 -- sw2:if03
sw1:if04 -- sw2:if04
"""


"""
    Format of the route dictionary used for component test verification
        data keys
        Route - string set to route which is of the format
                "Prefix/Masklen"
        NumberNexthops - string set to the number of next-hops
                         of the route
        Next-hop - string set to the next-hop port or IP/IPv6
                   address as the key and a dictionary as value
        data keys
            Distance - String whose numeric value is the administration
                       distance of the next-hop
            Metric - String whose numeric value is the metric of the
                     next-hop
            RouteType - String which is the route type of the next-hop
"""

# This test configures IPv4 and IPv6 interface addresses on L3 lag interface
# and checks if the corresponding connected route have been programmed in
# FIB by looking into the output of "show ip/ipv6 route/show rib". This test
# also configures a static route via the L3 lag interface and checks if the
# corresponding connected route have been programmed in FIB by looking into
# the output of "show ip/ipv6 route/show rib".
def configure_l3_lag_interface_and_static_route(sw1, sw2, step):

    # Define physical layer-3 interfaces which are used for configuration
    sw1_intf1 = format(sw1.ports["if01"])
    sw1_intf2 = format(sw1.ports["if02"])
    sw1_intf3 = format(sw1.ports["if03"])
    sw1_intf4 = format(sw1.ports["if04"])

    # L3 lag interface name
    l3_lag_name = "lag100"

    # Configure physical layer-3 interfaces and toggle them up
    sw1("configure terminal")
    sw1("interface {}".format(sw1_intf1))
    sw1("no shutdown")
    sw1("exit")

    sw1("interface {}".format(sw1_intf2))
    sw1("no shutdown")
    sw1("exit")

    # Configure a L3 LAG interface.
    sw1("interface lag 100")
    sw1("ip address 5.5.5.5/24")
    sw1("ip address 55.55.55.55/24 secondary")
    sw1("ipv6 address 5:5::5/64")
    sw1("ipv6 address 55:55::55/64 secondary")
    sw1("no shutdown")
    sw1("exit")

    # Configure lag in the physical interface
    sw1("interface {}".format(sw1_intf1))
    sw1("lag 100")
    sw1("exit")

    sw1("interface {}".format(sw1_intf2))
    sw1("lag 100")
    sw1("exit")

    # Populate the expected RIB ("show rib") route dictionary for the connected
    # IPv4 route for LAG primary address and its next-hops.
    rib_ipv4_lag_route_primary = dict()
    rib_ipv4_lag_route_primary['Route'] = '5.5.5.0/24'
    rib_ipv4_lag_route_primary['NumberNexthops'] = '1'
    rib_ipv4_lag_route_primary[l3_lag_name] = dict()
    rib_ipv4_lag_route_primary[l3_lag_name]['Distance'] = '0'
    rib_ipv4_lag_route_primary[l3_lag_name]['Metric'] = '0'
    rib_ipv4_lag_route_primary[l3_lag_name]['RouteType'] = 'connected'

    # Populate the expected RIB ("show ip route") route dictionary for the
    # connected IPv4 route for LAG primary address and its next-hops.
    fib_ipv4_lag_route_primary = rib_ipv4_lag_route_primary

    # Populate the expected RIB ("show rib") route dictionary for the connected
    # IPv4 route for LAG secondary address and its next-hops.
    rib_ipv4_lag_route_secondary = dict()
    rib_ipv4_lag_route_secondary['Route'] = '55.55.55.0/24'
    rib_ipv4_lag_route_secondary['NumberNexthops'] = '1'
    rib_ipv4_lag_route_secondary[l3_lag_name] = dict()
    rib_ipv4_lag_route_secondary[l3_lag_name]['Distance'] = '0'
    rib_ipv4_lag_route_secondary[l3_lag_name]['Metric'] = '0'
    rib_ipv4_lag_route_secondary[l3_lag_name]['RouteType'] = 'connected'

    # Populate the expected RIB ("show ip route") route dictionary for the \
    # connected IPv4 route for LAG secondary address and its next-hops.
    fib_ipv4_lag_route_secondary = rib_ipv4_lag_route_secondary

    # Populate the expected RIB ("show rib") route dictionary for the connected
    # IPv6 route for LAG primary address and its next-hops.
    rib_ipv6_lag_route_primary = dict()
    rib_ipv6_lag_route_primary['Route'] = '5:5::/64'
    rib_ipv6_lag_route_primary['NumberNexthops'] = '1'
    rib_ipv6_lag_route_primary[l3_lag_name] = dict()
    rib_ipv6_lag_route_primary[l3_lag_name]['Distance'] = '0'
    rib_ipv6_lag_route_primary[l3_lag_name]['Metric'] = '0'
    rib_ipv6_lag_route_primary[l3_lag_name]['RouteType'] = 'connected'

    # Populate the expected RIB ("show ipv6 route") route dictionary for the
    # connected IPv6 route for LAG primary address and its next-hops.
    fib_ipv6_lag_route_primary = rib_ipv6_lag_route_primary

    # Populate the expected RIB ("show rib") route dictionary for the connected
    # IPv6 route for LAG secondary address and its next-hops.
    rib_ipv6_lag_route_secondary = dict()
    rib_ipv6_lag_route_secondary['Route'] = '55:55::/64'
    rib_ipv6_lag_route_secondary['NumberNexthops'] = '1'
    rib_ipv6_lag_route_secondary[l3_lag_name] = dict()
    rib_ipv6_lag_route_secondary[l3_lag_name]['Distance'] = '0'
    rib_ipv6_lag_route_secondary[l3_lag_name]['Metric'] = '0'
    rib_ipv6_lag_route_secondary[l3_lag_name]['RouteType'] = 'connected'

    # Populate the expected RIB ("show ipv6 route") route dictionary for the
    # connected IPv6 route for LAG secndary address and its next-hops.
    fib_ipv6_lag_route_secondary = rib_ipv6_lag_route_secondary

    # Configure IPv4 route 143.0.0.1/32 with 1 next-hop via L3 lag.
    sw1("ip route 143.0.0.1/32 5.5.5.1")
    output = sw1("do show running-config")
    assert "ip route 143.0.0.1/32 5.5.5.1" in output

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 143.0.0.1/32 and its next-hops.
    rib_ipv4_static_route = dict()
    rib_ipv4_static_route['Route'] = '143.0.0.1/32'
    rib_ipv4_static_route['NumberNexthops'] = '1'
    rib_ipv4_static_route['5.5.5.1'] = dict()
    rib_ipv4_static_route['5.5.5.1']['Distance'] = '1'
    rib_ipv4_static_route['5.5.5.1']['Metric'] = '0'
    rib_ipv4_static_route['5.5.5.1']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 143.0.0.1/32 and its next-hops.
    route_ipv4_static_route = rib_ipv4_static_route

    # Configure IPv6 route 2234:2234::1/128 with 1 next-hop via L3 lag.
    sw1("ipv6 route 2234:2234::1/128 %s" % l3_lag_name)
    output = sw1("do show running-config")
    assert "ipv6 route 2234:2234::1/128 %s" % l3_lag_name in output

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 2234:2234::1/128 and its next-hops.
    rib_ipv6_static_route = dict()
    rib_ipv6_static_route['Route'] = '2234:2234::1/128'
    rib_ipv6_static_route['NumberNexthops'] = '1'
    rib_ipv6_static_route[l3_lag_name] = dict()
    rib_ipv6_static_route[l3_lag_name]['Distance'] = '1'
    rib_ipv6_static_route[l3_lag_name]['Metric'] = '0'
    rib_ipv6_static_route[l3_lag_name]['RouteType'] = 'static'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 2234:2234::1/128 and its next-hops.
    route_ipv6_static_route = rib_ipv6_static_route

    step("Verifying the IPv4/IPv6 connected routes for L3 lag interface on switch 1")

    # Verify IPv4 route for LAG primary address and next-hops in RIB and FIB
    aux_route = fib_ipv4_lag_route_primary["Route"]
    verify_show_ip_route(sw1, aux_route, 'connected',
                         fib_ipv4_lag_route_primary)
    aux_route = rib_ipv4_lag_route_primary["Route"]
    verify_show_rib(
        sw1,
        aux_route,
        'connected',
        rib_ipv4_lag_route_primary)

    # Verify IPv4 route for LAG secondary address and next-hops in RIB and FIB
    aux_route = fib_ipv4_lag_route_secondary["Route"]
    verify_show_ip_route(sw1, aux_route, 'connected',
                         fib_ipv4_lag_route_secondary)
    aux_route = rib_ipv4_lag_route_secondary["Route"]
    verify_show_rib(sw1, aux_route, 'connected',
                    rib_ipv4_lag_route_secondary)

    # Verify IPv6 route for LAG primary address and next-hops in RIB and FIB
    aux_route = fib_ipv6_lag_route_primary["Route"]
    verify_show_ipv6_route(sw1, aux_route, 'connected',
                           fib_ipv6_lag_route_primary)
    aux_route = rib_ipv6_lag_route_primary["Route"]
    verify_show_rib(
        sw1,
        aux_route,
        'connected',
        rib_ipv6_lag_route_primary)

    # Verify IPv6 route for LAG secondary address and next-hops in RIB and FIB
    aux_route = fib_ipv6_lag_route_secondary["Route"]
    verify_show_ipv6_route(sw1, aux_route, 'connected',
                           fib_ipv6_lag_route_secondary)
    aux_route = rib_ipv6_lag_route_secondary["Route"]
    verify_show_rib(sw1, aux_route, 'connected',
                    rib_ipv6_lag_route_secondary)

    step("Verifying the IPv4/IPv6 static routes via L3 lag interface on switch 1")

    # Verify route 143.0.0.1/32 and next-hops in RIB and FIB
    aux_route = route_ipv4_static_route["Route"]
    verify_show_ip_route(sw1, aux_route, 'static', route_ipv4_static_route)
    aux_route = rib_ipv4_static_route["Route"]
    verify_show_rib(sw1, aux_route, 'static', rib_ipv4_static_route)

    # Verify route 2234:2234::1/128 and next-hops in RIB and FIB
    aux_route = route_ipv6_static_route["Route"]
    verify_show_ipv6_route(sw1, aux_route, 'static', route_ipv6_static_route)
    aux_route = rib_ipv6_static_route["Route"]
    verify_show_rib(sw1, aux_route, 'static', rib_ipv6_static_route)


# This test case shuts down the member interfaces in L3 lag interface
# and checks if the corresponding connected/static route have been
# un-programmed in FIB by looking into the output of
# "show ip/ipv6 route/show rib".
def shutdown_member_interfaces_l3_lag(sw1, sw2, step):

    # Define physical layer-3 interfaces which are used for configuration
    sw1_intf1 = format(sw1.ports["if01"])
    sw1_intf2 = format(sw1.ports["if02"])
    sw1_intf3 = format(sw1.ports["if03"])
    sw1_intf4 = format(sw1.ports["if04"])

    # L3 lag interface name
    l3_lag_name = "lag100"

    # Configure physical layer-3 interfaces and toggle them up
    sw1("configure terminal")
    sw1("interface {}".format(sw1_intf1))
    sw1("shutdown")
    sw1("exit")

    sw1("interface {}".format(sw1_intf2))
    sw1("shutdown")
    sw1("exit")

    # Populate the expected RIB ("show rib") route dictionary for the connected
    # IPv4 route for LAG primary address and its next-hops.
    rib_ipv4_lag_route_primary = dict()
    rib_ipv4_lag_route_primary['Route'] = '5.5.5.0/24'
    rib_ipv4_lag_route_primary['NumberNexthops'] = '1'
    rib_ipv4_lag_route_primary[l3_lag_name] = dict()
    rib_ipv4_lag_route_primary[l3_lag_name]['Distance'] = '0'
    rib_ipv4_lag_route_primary[l3_lag_name]['Metric'] = '0'
    rib_ipv4_lag_route_primary[l3_lag_name]['RouteType'] = 'connected'

    # Populate the expected RIB ("show ip route") route dictionary for the
    # connected IPv4 route for LAG primary address and its next-hops.
    fib_ipv4_lag_route_primary = dict()
    fib_ipv4_lag_route_primary['Route'] = '5.5.5.0/24'

    # Populate the expected RIB ("show rib") route dictionary for the connected
    # IPv4 route for LAG secondary address and its next-hops.
    rib_ipv4_lag_route_secondary = dict()
    rib_ipv4_lag_route_secondary['Route'] = '55.55.55.0/24'
    rib_ipv4_lag_route_secondary['NumberNexthops'] = '1'
    rib_ipv4_lag_route_secondary[l3_lag_name] = dict()
    rib_ipv4_lag_route_secondary[l3_lag_name]['Distance'] = '0'
    rib_ipv4_lag_route_secondary[l3_lag_name]['Metric'] = '0'
    rib_ipv4_lag_route_secondary[l3_lag_name]['RouteType'] = 'connected'

    # Populate the expected RIB ("show ip route") route dictionary for the \
    # connected IPv4 route for LAG secondary address and its next-hops.
    fib_ipv4_lag_route_secondary = dict()
    fib_ipv4_lag_route_secondary['Route'] = '55.55.55.0/24'

    # Populate the expected RIB ("show rib") route dictionary for the connected
    # IPv6 route for LAG primary address and its next-hops.
    rib_ipv6_lag_route_primary = dict()
    rib_ipv6_lag_route_primary['Route'] = '5:5::/64'
    rib_ipv6_lag_route_primary['NumberNexthops'] = '1'
    rib_ipv6_lag_route_primary[l3_lag_name] = dict()
    rib_ipv6_lag_route_primary[l3_lag_name]['Distance'] = '0'
    rib_ipv6_lag_route_primary[l3_lag_name]['Metric'] = '0'
    rib_ipv6_lag_route_primary[l3_lag_name]['RouteType'] = 'connected'

    # Populate the expected RIB ("show ipv6 route") route dictionary for the
    # connected IPv6 route for LAG primary address and its next-hops.
    fib_ipv6_lag_route_primary = dict()
    fib_ipv6_lag_route_primary['Route'] = '5:5::/64'

    # Populate the expected RIB ("show rib") route dictionary for the connected
    # IPv6 route for LAG secondary address and its next-hops.
    rib_ipv6_lag_route_secondary = dict()
    rib_ipv6_lag_route_secondary['Route'] = '55:55::/64'
    rib_ipv6_lag_route_secondary['NumberNexthops'] = '1'
    rib_ipv6_lag_route_secondary[l3_lag_name] = dict()
    rib_ipv6_lag_route_secondary[l3_lag_name]['Distance'] = '0'
    rib_ipv6_lag_route_secondary[l3_lag_name]['Metric'] = '0'
    rib_ipv6_lag_route_secondary[l3_lag_name]['RouteType'] = 'connected'

    # Populate the expected RIB ("show ipv6 route") route dictionary for the
    # connected IPv6 route for LAG secndary address and its next-hops.
    fib_ipv6_lag_route_secondary = dict()
    fib_ipv6_lag_route_secondary['Route'] = '55:55::/64'

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 143.0.0.1/32 and its next-hops.
    rib_ipv4_static_route = dict()
    rib_ipv4_static_route['Route'] = '143.0.0.1/32'
    rib_ipv4_static_route['NumberNexthops'] = '1'
    rib_ipv4_static_route['5.5.5.1'] = dict()
    rib_ipv4_static_route['5.5.5.1']['Distance'] = '1'
    rib_ipv4_static_route['5.5.5.1']['Metric'] = '0'
    rib_ipv4_static_route['5.5.5.1']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 143.0.0.1/32 and its next-hops.
    route_ipv4_static_route = dict()
    route_ipv4_static_route['Route'] = '143.0.0.1/32'

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 2234:2234::1/128 and its next-hops.
    rib_ipv6_static_route = dict()
    rib_ipv6_static_route['Route'] = '2234:2234::1/128'
    rib_ipv6_static_route['NumberNexthops'] = '1'
    rib_ipv6_static_route[l3_lag_name] = dict()
    rib_ipv6_static_route[l3_lag_name]['Distance'] = '1'
    rib_ipv6_static_route[l3_lag_name]['Metric'] = '0'
    rib_ipv6_static_route[l3_lag_name]['RouteType'] = 'static'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 2234:2234::1/128 and its next-hops.
    route_ipv6_static_route = dict()
    route_ipv6_static_route['Route'] = '2234:2234::1/128'

    step("Verifying the IPv4/IPv6 connected routes for L3 lag interface on switch 1")

    # Verify IPv4 route for LAG primary address and next-hops in RIB and FIB
    aux_route = fib_ipv4_lag_route_primary["Route"]
    verify_show_ip_route(sw1, aux_route, 'connected',
                         fib_ipv4_lag_route_primary)
    aux_route = rib_ipv4_lag_route_primary["Route"]
    verify_show_rib(
        sw1,
        aux_route,
        'connected',
        rib_ipv4_lag_route_primary)

    # Verify IPv4 route for LAG secondary address and next-hops in RIB and FIB
    aux_route = fib_ipv4_lag_route_secondary["Route"]
    verify_show_ip_route(sw1, aux_route, 'connected',
                         fib_ipv4_lag_route_secondary)
    aux_route = rib_ipv4_lag_route_secondary["Route"]
    verify_show_rib(sw1, aux_route, 'connected',
                    rib_ipv4_lag_route_secondary)

    # Verify IPv6 route for LAG primary address and next-hops in RIB and FIB
    aux_route = fib_ipv6_lag_route_primary["Route"]
    verify_show_ipv6_route(sw1, aux_route, 'connected',
                           fib_ipv6_lag_route_primary)
    aux_route = rib_ipv6_lag_route_primary["Route"]
    verify_show_rib(
        sw1,
        aux_route,
        'connected',
        rib_ipv6_lag_route_primary)

    # Verify IPv6 route for LAG secondary address and next-hops in RIB and FIB
    aux_route = fib_ipv6_lag_route_secondary["Route"]
    verify_show_ipv6_route(sw1, aux_route, 'connected',
                           fib_ipv6_lag_route_secondary)
    aux_route = rib_ipv6_lag_route_secondary["Route"]
    verify_show_rib(sw1, aux_route, 'connected',
                    rib_ipv6_lag_route_secondary)

    step("Verifying the IPv4/IPv6 static routes via L3 lag interface on switch 1")

    # Verify route 143.0.0.1/32 and next-hops in RIB and FIB
    aux_route = route_ipv4_static_route["Route"]
    verify_show_ip_route(sw1, aux_route, 'static', route_ipv4_static_route)
    aux_route = rib_ipv4_static_route["Route"]
    verify_show_rib(sw1, aux_route, 'static', rib_ipv4_static_route)

    # Verify route 2234:2234::1/128 and next-hops in RIB and FIB
    aux_route = route_ipv6_static_route["Route"]
    verify_show_ipv6_route(sw1, aux_route, 'static', route_ipv6_static_route)
    aux_route = rib_ipv6_static_route["Route"]
    verify_show_rib(sw1, aux_route, 'static', rib_ipv6_static_route)


# This test case brings-up the member interfaces in L3 lag interface
# and checks if the corresponding connected/static route have been
# re-programmed in FIB by looking into the output of
# "show ip/ipv6 route/show rib".
def bringup_member_interfaces_l3_lag(sw1, sw2, step):

    # Define physical layer-3 interfaces which are used for configuration
    sw1_intf1 = format(sw1.ports["if01"])
    sw1_intf2 = format(sw1.ports["if02"])
    sw1_intf3 = format(sw1.ports["if03"])
    sw1_intf4 = format(sw1.ports["if04"])

    # L3 lag interface name
    l3_lag_name = "lag100"

    # Configure physical layer-3 interfaces and toggle them up
    sw1("configure terminal")
    sw1("interface {}".format(sw1_intf1))
    sw1("no shutdown")
    sw1("exit")

    sw1("interface {}".format(sw1_intf2))
    sw1("no shutdown")
    sw1("exit")

    # Populate the expected RIB ("show rib") route dictionary for the connected
    # IPv4 route for LAG primary address and its next-hops.
    rib_ipv4_lag_route_primary = dict()
    rib_ipv4_lag_route_primary['Route'] = '5.5.5.0/24'
    rib_ipv4_lag_route_primary['NumberNexthops'] = '1'
    rib_ipv4_lag_route_primary[l3_lag_name] = dict()
    rib_ipv4_lag_route_primary[l3_lag_name]['Distance'] = '0'
    rib_ipv4_lag_route_primary[l3_lag_name]['Metric'] = '0'
    rib_ipv4_lag_route_primary[l3_lag_name]['RouteType'] = 'connected'

    # Populate the expected RIB ("show ip route") route dictionary for the
    # connected IPv4 route for LAG primary address and its next-hops.
    fib_ipv4_lag_route_primary = rib_ipv4_lag_route_primary

    # Populate the expected RIB ("show rib") route dictionary for the connected
    # IPv4 route for LAG secondary address and its next-hops.
    rib_ipv4_lag_route_secondary = dict()
    rib_ipv4_lag_route_secondary['Route'] = '55.55.55.0/24'
    rib_ipv4_lag_route_secondary['NumberNexthops'] = '1'
    rib_ipv4_lag_route_secondary[l3_lag_name] = dict()
    rib_ipv4_lag_route_secondary[l3_lag_name]['Distance'] = '0'
    rib_ipv4_lag_route_secondary[l3_lag_name]['Metric'] = '0'
    rib_ipv4_lag_route_secondary[l3_lag_name]['RouteType'] = 'connected'

    # Populate the expected RIB ("show ip route") route dictionary for the \
    # connected IPv4 route for LAG secondary address and its next-hops.
    fib_ipv4_lag_route_secondary = rib_ipv4_lag_route_secondary

    # Populate the expected RIB ("show rib") route dictionary for the connected
    # IPv6 route for LAG primary address and its next-hops.
    rib_ipv6_lag_route_primary = dict()
    rib_ipv6_lag_route_primary['Route'] = '5:5::/64'
    rib_ipv6_lag_route_primary['NumberNexthops'] = '1'
    rib_ipv6_lag_route_primary[l3_lag_name] = dict()
    rib_ipv6_lag_route_primary[l3_lag_name]['Distance'] = '0'
    rib_ipv6_lag_route_primary[l3_lag_name]['Metric'] = '0'
    rib_ipv6_lag_route_primary[l3_lag_name]['RouteType'] = 'connected'

    # Populate the expected RIB ("show ipv6 route") route dictionary for the
    # connected IPv6 route for LAG primary address and its next-hops.
    fib_ipv6_lag_route_primary = rib_ipv6_lag_route_primary

    # Populate the expected RIB ("show rib") route dictionary for the connected
    # IPv6 route for LAG secondary address and its next-hops.
    rib_ipv6_lag_route_secondary = dict()
    rib_ipv6_lag_route_secondary['Route'] = '55:55::/64'
    rib_ipv6_lag_route_secondary['NumberNexthops'] = '1'
    rib_ipv6_lag_route_secondary[l3_lag_name] = dict()
    rib_ipv6_lag_route_secondary[l3_lag_name]['Distance'] = '0'
    rib_ipv6_lag_route_secondary[l3_lag_name]['Metric'] = '0'
    rib_ipv6_lag_route_secondary[l3_lag_name]['RouteType'] = 'connected'

    # Populate the expected RIB ("show ipv6 route") route dictionary for the
    # connected IPv6 route for LAG secndary address and its next-hops.
    fib_ipv6_lag_route_secondary = rib_ipv6_lag_route_secondary

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 143.0.0.1/32 and its next-hops.
    rib_ipv4_static_route = dict()
    rib_ipv4_static_route['Route'] = '143.0.0.1/32'
    rib_ipv4_static_route['NumberNexthops'] = '1'
    rib_ipv4_static_route['5.5.5.1'] = dict()
    rib_ipv4_static_route['5.5.5.1']['Distance'] = '1'
    rib_ipv4_static_route['5.5.5.1']['Metric'] = '0'
    rib_ipv4_static_route['5.5.5.1']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 143.0.0.1/32 and its next-hops.
    route_ipv4_static_route = rib_ipv4_static_route

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 2234:2234::1/128 and its next-hops.
    rib_ipv6_static_route = dict()
    rib_ipv6_static_route['Route'] = '2234:2234::1/128'
    rib_ipv6_static_route['NumberNexthops'] = '1'
    rib_ipv6_static_route[l3_lag_name] = dict()
    rib_ipv6_static_route[l3_lag_name]['Distance'] = '1'
    rib_ipv6_static_route[l3_lag_name]['Metric'] = '0'
    rib_ipv6_static_route[l3_lag_name]['RouteType'] = 'static'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 2234:2234::1/128 and its next-hops.
    route_ipv6_static_route = rib_ipv6_static_route

    step("Verifying the IPv4/IPv6 connected routes for L3 lag interface on switch 1")

    # Verify IPv4 route for LAG primary address and next-hops in RIB and FIB
    aux_route = fib_ipv4_lag_route_primary["Route"]
    verify_show_ip_route(sw1, aux_route, 'connected',
                         fib_ipv4_lag_route_primary)
    aux_route = rib_ipv4_lag_route_primary["Route"]
    verify_show_rib(
        sw1,
        aux_route,
        'connected',
        rib_ipv4_lag_route_primary)

    # Verify IPv4 route for LAG secondary address and next-hops in RIB and FIB
    aux_route = fib_ipv4_lag_route_secondary["Route"]
    verify_show_ip_route(sw1, aux_route, 'connected',
                         fib_ipv4_lag_route_secondary)
    aux_route = rib_ipv4_lag_route_secondary["Route"]
    verify_show_rib(sw1, aux_route, 'connected',
                    rib_ipv4_lag_route_secondary)

    # Verify IPv6 route for LAG primary address and next-hops in RIB and FIB
    aux_route = fib_ipv6_lag_route_primary["Route"]
    verify_show_ipv6_route(sw1, aux_route, 'connected',
                           fib_ipv6_lag_route_primary)
    aux_route = rib_ipv6_lag_route_primary["Route"]
    verify_show_rib(
        sw1,
        aux_route,
        'connected',
        rib_ipv6_lag_route_primary)

    # Verify IPv6 route for LAG secondary address and next-hops in RIB and FIB
    aux_route = fib_ipv6_lag_route_secondary["Route"]
    verify_show_ipv6_route(sw1, aux_route, 'connected',
                           fib_ipv6_lag_route_secondary)
    aux_route = rib_ipv6_lag_route_secondary["Route"]
    verify_show_rib(sw1, aux_route, 'connected',
                    rib_ipv6_lag_route_secondary)

    step("Verifying the IPv4/IPv6 static routes via L3 lag interface on switch 1")

    # Verify route 143.0.0.1/32 and next-hops in RIB and FIB
    aux_route = route_ipv4_static_route["Route"]
    verify_show_ip_route(sw1, aux_route, 'static', route_ipv4_static_route)
    aux_route = rib_ipv4_static_route["Route"]
    verify_show_rib(sw1, aux_route, 'static', rib_ipv4_static_route)

    # Verify route 2234:2234::1/128 and next-hops in RIB and FIB
    aux_route = route_ipv6_static_route["Route"]
    verify_show_ipv6_route(sw1, aux_route, 'static', route_ipv6_static_route)
    aux_route = rib_ipv6_static_route["Route"]
    verify_show_rib(sw1, aux_route, 'static', rib_ipv6_static_route)


# This test case un-configures the member L3 interfaces for L3 lag interface
# and checks if the corresponding connected/static route have been
# un-programmed in FIB by looking into the output of
# "show ip/ipv6 route/show rib".
def unconfigure_member_interfaces_l3_lag(sw1, sw2, step):

    # Define physical layer-3 interfaces which are used for configuration
    sw1_intf1 = format(sw1.ports["if01"])
    sw1_intf2 = format(sw1.ports["if02"])
    sw1_intf3 = format(sw1.ports["if03"])
    sw1_intf4 = format(sw1.ports["if04"])

    # L3 lag interface name
    l3_lag_name = "lag100"

    # Configure physical layer-3 interfaces and toggle them up
    sw1("configure terminal")
    sw1("interface {}".format(sw1_intf1))
    sw1("no lag 100")
    sw1("exit")

    sw1("interface {}".format(sw1_intf2))
    sw1("no lag 100")
    sw1("exit")

    # Populate the expected RIB ("show rib") route dictionary for the connected
    # IPv4 route for LAG primary address and its next-hops.
    rib_ipv4_lag_route_primary = dict()
    rib_ipv4_lag_route_primary['Route'] = '5.5.5.0/24'
    rib_ipv4_lag_route_primary['NumberNexthops'] = '1'
    rib_ipv4_lag_route_primary[l3_lag_name] = dict()
    rib_ipv4_lag_route_primary[l3_lag_name]['Distance'] = '0'
    rib_ipv4_lag_route_primary[l3_lag_name]['Metric'] = '0'
    rib_ipv4_lag_route_primary[l3_lag_name]['RouteType'] = 'connected'

    # Populate the expected RIB ("show ip route") route dictionary for the
    # connected IPv4 route for LAG primary address and its next-hops.
    fib_ipv4_lag_route_primary = dict()
    fib_ipv4_lag_route_primary['Route'] = '5.5.5.0/24'

    # Populate the expected RIB ("show rib") route dictionary for the connected
    # IPv4 route for LAG secondary address and its next-hops.
    rib_ipv4_lag_route_secondary = dict()
    rib_ipv4_lag_route_secondary['Route'] = '55.55.55.0/24'
    rib_ipv4_lag_route_secondary['NumberNexthops'] = '1'
    rib_ipv4_lag_route_secondary[l3_lag_name] = dict()
    rib_ipv4_lag_route_secondary[l3_lag_name]['Distance'] = '0'
    rib_ipv4_lag_route_secondary[l3_lag_name]['Metric'] = '0'
    rib_ipv4_lag_route_secondary[l3_lag_name]['RouteType'] = 'connected'

    # Populate the expected RIB ("show ip route") route dictionary for the \
    # connected IPv4 route for LAG secondary address and its next-hops.
    fib_ipv4_lag_route_secondary = dict()
    fib_ipv4_lag_route_secondary['Route'] = '55.55.55.0/24'

    # Populate the expected RIB ("show rib") route dictionary for the connected
    # IPv6 route for LAG primary address and its next-hops.
    rib_ipv6_lag_route_primary = dict()
    rib_ipv6_lag_route_primary['Route'] = '5:5::/64'
    rib_ipv6_lag_route_primary['NumberNexthops'] = '1'
    rib_ipv6_lag_route_primary[l3_lag_name] = dict()
    rib_ipv6_lag_route_primary[l3_lag_name]['Distance'] = '0'
    rib_ipv6_lag_route_primary[l3_lag_name]['Metric'] = '0'
    rib_ipv6_lag_route_primary[l3_lag_name]['RouteType'] = 'connected'

    # Populate the expected RIB ("show ipv6 route") route dictionary for the
    # connected IPv6 route for LAG primary address and its next-hops.
    fib_ipv6_lag_route_primary = dict()
    fib_ipv6_lag_route_primary['Route'] = '5:5::/64'

    # Populate the expected RIB ("show rib") route dictionary for the connected
    # IPv6 route for LAG secondary address and its next-hops.
    rib_ipv6_lag_route_secondary = dict()
    rib_ipv6_lag_route_secondary['Route'] = '55:55::/64'
    rib_ipv6_lag_route_secondary['NumberNexthops'] = '1'
    rib_ipv6_lag_route_secondary[l3_lag_name] = dict()
    rib_ipv6_lag_route_secondary[l3_lag_name]['Distance'] = '0'
    rib_ipv6_lag_route_secondary[l3_lag_name]['Metric'] = '0'
    rib_ipv6_lag_route_secondary[l3_lag_name]['RouteType'] = 'connected'

    # Populate the expected RIB ("show ipv6 route") route dictionary for the
    # connected IPv6 route for LAG secndary address and its next-hops.
    fib_ipv6_lag_route_secondary = dict()
    fib_ipv6_lag_route_secondary['Route'] = '55:55::/64'

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 143.0.0.1/32 and its next-hops.
    rib_ipv4_static_route = dict()
    rib_ipv4_static_route['Route'] = '143.0.0.1/32'
    rib_ipv4_static_route['NumberNexthops'] = '1'
    rib_ipv4_static_route['5.5.5.1'] = dict()
    rib_ipv4_static_route['5.5.5.1']['Distance'] = '1'
    rib_ipv4_static_route['5.5.5.1']['Metric'] = '0'
    rib_ipv4_static_route['5.5.5.1']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 143.0.0.1/32 and its next-hops.
    route_ipv4_static_route = dict()
    route_ipv4_static_route['Route'] = '143.0.0.1/32'

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 2234:2234::1/128 and its next-hops.
    rib_ipv6_static_route = dict()
    rib_ipv6_static_route['Route'] = '2234:2234::1/128'
    rib_ipv6_static_route['NumberNexthops'] = '1'
    rib_ipv6_static_route[l3_lag_name] = dict()
    rib_ipv6_static_route[l3_lag_name]['Distance'] = '1'
    rib_ipv6_static_route[l3_lag_name]['Metric'] = '0'
    rib_ipv6_static_route[l3_lag_name]['RouteType'] = 'static'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 2234:2234::1/128 and its next-hops.
    route_ipv6_static_route = dict()
    route_ipv6_static_route['Route'] = '2234:2234::1/128'

    step("Verifying the IPv4/IPv6 connected routes for L3 lag interface on switch 1")

    # Verify IPv4 route for LAG primary address and next-hops in RIB and FIB
    aux_route = fib_ipv4_lag_route_primary["Route"]
    verify_show_ip_route(sw1, aux_route, 'connected',
                         fib_ipv4_lag_route_primary)
    aux_route = rib_ipv4_lag_route_primary["Route"]
    verify_show_rib(
        sw1,
        aux_route,
        'connected',
        rib_ipv4_lag_route_primary)

    # Verify IPv4 route for LAG secondary address and next-hops in RIB and FIB
    aux_route = fib_ipv4_lag_route_secondary["Route"]
    verify_show_ip_route(sw1, aux_route, 'connected',
                         fib_ipv4_lag_route_secondary)
    aux_route = rib_ipv4_lag_route_secondary["Route"]
    verify_show_rib(sw1, aux_route, 'connected',
                    rib_ipv4_lag_route_secondary)

    # Verify IPv6 route for LAG primary address and next-hops in RIB and FIB
    aux_route = fib_ipv6_lag_route_primary["Route"]
    verify_show_ipv6_route(sw1, aux_route, 'connected',
                           fib_ipv6_lag_route_primary)
    aux_route = rib_ipv6_lag_route_primary["Route"]
    verify_show_rib(
        sw1,
        aux_route,
        'connected',
        rib_ipv6_lag_route_primary)

    # Verify IPv6 route for LAG secondary address and next-hops in RIB and FIB
    aux_route = fib_ipv6_lag_route_secondary["Route"]
    verify_show_ipv6_route(sw1, aux_route, 'connected',
                           fib_ipv6_lag_route_secondary)
    aux_route = rib_ipv6_lag_route_secondary["Route"]
    verify_show_rib(sw1, aux_route, 'connected',
                    rib_ipv6_lag_route_secondary)

    step("Verifying the IPv4/IPv6 static routes via L3 lag interface on switch 1")

    # Verify route 143.0.0.1/32 and next-hops in RIB and FIB
    aux_route = route_ipv4_static_route["Route"]
    verify_show_ip_route(sw1, aux_route, 'static', route_ipv4_static_route)
    aux_route = rib_ipv4_static_route["Route"]
    verify_show_rib(sw1, aux_route, 'static', rib_ipv4_static_route)

    # Verify route 2234:2234::1/128 and next-hops in RIB and FIB
    aux_route = route_ipv6_static_route["Route"]
    verify_show_ipv6_route(sw1, aux_route, 'static', route_ipv6_static_route)
    aux_route = rib_ipv6_static_route["Route"]
    verify_show_rib(sw1, aux_route, 'static', rib_ipv6_static_route)


@mark.timeout(ZEBRA_DEFAULT_TIMEOUT)
@mark.gate
def test_zebra_ct_l3_lag_interface(topology, step):
    sw1 = topology.get("sw1")
    sw2 = topology.get("sw2")

    assert sw1 is not None
    assert sw2 is not None

    configure_l3_lag_interface_and_static_route(sw1, sw2, step)
    shutdown_member_interfaces_l3_lag(sw1, sw2, step)
    bringup_member_interfaces_l3_lag(sw1, sw2, step)
    unconfigure_member_interfaces_l3_lag(sw1, sw2, step)
