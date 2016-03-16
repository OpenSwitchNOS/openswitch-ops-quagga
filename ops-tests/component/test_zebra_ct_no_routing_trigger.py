# -*- coding: utf-8 -*-

# (c) Copyright 2015 Hewlett Packard Enterprise Development LP
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
# along with GNU Zebra; see the file COPYING.  If not, write to the Free
# Software Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.

from re import match

# Topology definition. the topology contains two back to back switches
# having four links between them.
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


def get_route_and_nexthops_from_output(output, route, route_type):
    found_route = False
    found_nexthop = False
    lines = output.splitlines()
    route_output = ''
    for line in lines:
        if not found_route:
            if route in line:
                found_route = True
                route_output = "{}{}\n".format(route_output, line)
        else:
            if 'via' in line and route_type in line:
                route_output = "{}{}\n".format(route_output, line)
                found_nexthop = True
            else:
                if not found_nexthop:
                    found_route = False
                    route_output = ''
                else:
                    break
    return route_output


def get_route_from_show(sw1, route, route_type, show):
    show_output = sw1("do show {}".format(show))
    route_output = get_route_and_nexthops_from_output(show_output,
                                                      route, route_type)
    route_dict = dict()
    route_dict['Route'] = route
    lines = route_output.splitlines()
    for line in lines:
        routeline = match("(.*)(%s)(,  )(\d+)( unicast next-hops)"
                          "".format(route), line)
        if routeline:
            route_dict['Route'] = routeline.group(2)
            route_dict['NumberNexthops'] = routeline.group(4)
        nexthop = match("(.+)via  ([0-9.:]+),  \[(\d+)/(\d+)\],  (.+)",
                        line)
        if nexthop:
            route_dict[nexthop.group(2)] = dict()
            route_dict[nexthop.group(2)]['Distance'] = nexthop.group(3)
            route_dict[nexthop.group(2)]['Metric'] = nexthop.group(4)
            aux_nexthop = nexthop.group(5).rstrip('\r')
            route_dict[nexthop.group(2)]['RouteType'] = aux_nexthop
    return route_dict


def verify_show(sw1, route, route_type, p_dict, show):
    dict_from_show = get_route_from_show(sw1,
                                         route,
                                         route_type,
                                         show)
    for key in dict_from_show.keys():
        if key in p_dict:
            assert dict_from_show[key] == p_dict[key]


IPV4_STATIC_ROUTE = "ipv4_static_route"
IPV6_STATIC_ROUTE = "ipv6_static_route"


def if_config_in_running_config(**kwargs):
    sw1 = kwargs.get('sw1', None)
    config_type = kwargs.get('config_type', None)
    running_config_string = ''
    if config_type is IPV4_STATIC_ROUTE or config_type is IPV6_STATIC_ROUTE:
        route = kwargs.get('route', None)
        nexthop = kwargs.get('nexthop', None)
        distance = kwargs.get('distance', None)
        if config_type is IPV4_STATIC_ROUTE:
            if distance is None:
                running_config_string = 'ip route {} {}'.format(route,
                                                                nexthop)
            else:
                running_config_string = 'ip route {} {} {}'.format(route,
                                                                   nexthop,
                                                                   distance)
        else:
            if distance is None:
                running_config_string = 'ipv6 route {} {}'.format(route,
                                                                  nexthop)
            else:
                running_config_string = 'ipv6 route {} {} '
                '{}'.format(route,
                            nexthop,
                            distance)
    show_running_config = sw1("do show running-config")
    show_running_config_lines = show_running_config.split('\n')
    found = False
    for line in show_running_config_lines:
        if running_config_string in line:
            found = True
            break
    return found


def route_and_nexthop_in_show_running_config(**kwargs):
    sw1 = kwargs.get('sw1', None)
    if_ipv4 = kwargs.get('if_ipv4', None)
    route = kwargs.get('route', None)
    nexthop = kwargs.get('nexthop', None)
    distance = kwargs.get('distance', None)
    if if_ipv4 is True:
        return if_config_in_running_config(sw1=sw1,
                                           config_type=IPV4_STATIC_ROUTE,
                                           route=route,
                                           nexthop=nexthop,
                                           distance=distance)
    else:
        return if_config_in_running_config(sw1=sw1,
                                           config_type=IPV6_STATIC_ROUTE,
                                           route=route,
                                           nexthop=nexthop,
                                           distance=distance)


# This test configures IPv4 and IPv6 ECMP static routes and checks if the
# routes and next-hops show correctly in the output of
# "show ip/ipv6 route/show rib/show running-config".
def add_static_routes(sw1, sw2, step):
    # Enabling interface 1 on sw1
    step("Enabling interface1 on SW1")
    sw1_interfaces = []
    sw1_ifs_ips = ["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4", "5.5.5.5"]
    sw1_ifs_ipv6s = ["111:111::1", "222:222::2", "333:333::3", "444:444::4",
                     "555:555::5"]
    size = len(sw1_ifs_ips)
    for i in range(size):
        if i is not size-1:
            sw1_interfaces.append(sw1.ports["if0{}".format(i+1)])
        else:
            sw1_interfaces.append(sw1.ports["if0{}".format(i)])
    sw1_mask = 24
    sw1_ipv6_mask = 64
    step("Configuring interfaces and IPs on SW1")
    sw1("configure terminal")
    for i in range(size):
        sw1("interface {}".format(sw1_interfaces[i]))
        sw1("ip address {}/{}".format(sw1_ifs_ips[i], sw1_mask))
        sw1("ipv6 address {}/{}".format(sw1_ifs_ipv6s[i], sw1_ipv6_mask))
        sw1("no shutdown")
        sw1("exit")
        output = sw1("do show running-config")
        assert "interface {}".format(sw1_interfaces[i]) in output
        assert "ip address {}/{}".format(sw1_ifs_ips[i], sw1_mask) in output
        assert "ipv6 address {}/{}".format(sw1_ifs_ipv6s[i],
                                           sw1_ipv6_mask) in output
    step("Cofiguring sw1 IPV4 static routes")
    nexthops = ["1.1.1.2", "2", "3", "5.5.5.1"]
    for i in range(size-1):
        sw1("ip route 123.0.0.1/32 {}".format(nexthops[i]))
        output = sw1("do show running-config")
        assert "ip route 123.0.0.1/32 {}".format(nexthops[i]) in output
    # Populate the expected RIB ("show rib") route dictionary for the route
    # 123.0.0.1/32 and its next-hops.
    rib_ipv4_static_route1 = dict()
    rib_ipv4_static_route1['Route'] = '123.0.0.1/32'
    rib_ipv4_static_route1['NumberNexthops'] = '4'
    rib_ipv4_static_route1['1.1.1.2'] = dict()
    rib_ipv4_static_route1['1.1.1.2']['Distance'] = '1'
    rib_ipv4_static_route1['1.1.1.2']['Metric'] = '0'
    rib_ipv4_static_route1['1.1.1.2']['RouteType'] = 'static'
    rib_ipv4_static_route1['2'] = dict()
    rib_ipv4_static_route1['2']['Distance'] = '1'
    rib_ipv4_static_route1['2']['Metric'] = '0'
    rib_ipv4_static_route1['2']['RouteType'] = 'static'
    rib_ipv4_static_route1['3'] = dict()
    rib_ipv4_static_route1['3']['Distance'] = '1'
    rib_ipv4_static_route1['3']['Metric'] = '0'
    rib_ipv4_static_route1['3']['RouteType'] = 'static'
    rib_ipv4_static_route1['5.5.5.1'] = dict()
    rib_ipv4_static_route1['5.5.5.1']['Distance'] = '1'
    rib_ipv4_static_route1['5.5.5.1']['Metric'] = '0'
    rib_ipv4_static_route1['5.5.5.1']['RouteType'] = 'static'
    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 123.0.0.1/32 and its next-hops.
    route_ipv4_static_route1 = rib_ipv4_static_route1
    # Configure IPv4 route 143.0.0.1/32 with 1 next-hop.
    sw1("ip route 143.0.0.1/32 4.4.4.1")
    output = sw1("do show running-config")
    assert "ip route 143.0.0.1/32 4.4.4.1" in output
    # Populate the expected RIB ("show rib") route dictionary for the
    # route 143.0.0.1/32 and its next-hops.
    rib_ipv4_static_route2 = dict()
    rib_ipv4_static_route2['Route'] = '143.0.0.1/32'
    rib_ipv4_static_route2['NumberNexthops'] = '1'
    rib_ipv4_static_route2['4.4.4.1'] = dict()
    rib_ipv4_static_route2['4.4.4.1']['Distance'] = '1'
    rib_ipv4_static_route2['4.4.4.1']['Metric'] = '0'
    rib_ipv4_static_route2['4.4.4.1']['RouteType'] = 'static'
    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 143.0.0.1/32 and its next-hops.
    route_ipv4_static_route2 = rib_ipv4_static_route2
    # Configure IPv4 route 163.0.0.1/32 with 1 next-hop.
    sw1("ip route 163.0.0.1/32 2")
    output = sw1("do show running-config")
    assert "ip route 163.0.0.1/32 2" in output
    # Populate the expected RIB ("show rib") route dictionary for the
    # route 163.0.0.1/32 and its next-hops.
    rib_ipv4_static_route3 = dict()
    rib_ipv4_static_route3['Route'] = '163.0.0.1/32'
    rib_ipv4_static_route3['NumberNexthops'] = '1'
    rib_ipv4_static_route3['2'] = dict()
    rib_ipv4_static_route3['2']['Distance'] = '1'
    rib_ipv4_static_route3['2']['Metric'] = '0'
    rib_ipv4_static_route3['2']['RouteType'] = 'static'
    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 163.0.0.1/32 and its next-hops.
    route_ipv4_static_route3 = rib_ipv4_static_route3
    step("Configuring switch 1 IPv6 static routes ")
    # Configure IPv6 route 1234:1234::1/128 with 4 ECMP next-hops.
    for i in range(4):
        sw1("ipv6 route 1234:1234::1/128 {}".format(i+1))
        output = sw1("do show running-config")
        assert "ipv6 route 1234:1234::1/128 {}".format(i+1) in output
    # Populate the expected RIB ("show rib") route dictionary for the
    # route 1234:1234::1/128 and its next-hops.
    rib_ipv6_static_route1 = dict()
    rib_ipv6_static_route1['Route'] = '1234:1234::1/128'
    rib_ipv6_static_route1['NumberNexthops'] = '4'
    rib_ipv6_static_route1['1'] = dict()
    rib_ipv6_static_route1['1']['Distance'] = '1'
    rib_ipv6_static_route1['1']['Metric'] = '0'
    rib_ipv6_static_route1['1']['RouteType'] = 'static'
    rib_ipv6_static_route1['2'] = dict()
    rib_ipv6_static_route1['2']['Distance'] = '1'
    rib_ipv6_static_route1['2']['Metric'] = '0'
    rib_ipv6_static_route1['2']['RouteType'] = 'static'
    rib_ipv6_static_route1['3'] = dict()
    rib_ipv6_static_route1['3']['Distance'] = '1'
    rib_ipv6_static_route1['3']['Metric'] = '0'
    rib_ipv6_static_route1['3']['RouteType'] = 'static'
    rib_ipv6_static_route1['4'] = dict()
    rib_ipv6_static_route1['4']['Distance'] = '1'
    rib_ipv6_static_route1['4']['Metric'] = '0'
    rib_ipv6_static_route1['4']['RouteType'] = 'static'
    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 1234:1234::1/128 and its next-hops.
    route_ipv6_static_route1 = rib_ipv6_static_route1
    # Configure IPv4 route 2234:2234::1/128 with 1 next-hop.
    sw1("ipv6 route 2234:2234::1/128 4")
    output = sw1("do show running-config")
    assert "ipv6 route 2234:2234::1/128 4" in output
    # Populate the expected RIB ("show rib") route dictionary for the
    # route 2234:2234::1/128 and its next-hops.
    rib_ipv6_static_route2 = dict()
    rib_ipv6_static_route2['Route'] = '2234:2234::1/128'
    rib_ipv6_static_route2['NumberNexthops'] = '1'
    rib_ipv6_static_route2['4'] = dict()
    rib_ipv6_static_route2['4']['Distance'] = '1'
    rib_ipv6_static_route2['4']['Metric'] = '0'
    rib_ipv6_static_route2['4']['RouteType'] = 'static'
    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 2234:2234::1/128 and its next-hops.
    route_ipv6_static_route2 = rib_ipv6_static_route2
    # Configure IPv4 route 3234:3234::1/128 with 1 next-hop.
    sw1("ipv6 route 3234:3234::1/128 2")
    output = sw1("do show running-config")
    assert "ipv6 route 3234:3234::1/128 2" in output
    # Populate the expected RIB ("show rib") route dictionary for the
    # route 3234:3234::1/128 and its next-hops.
    rib_ipv6_static_route3 = dict()
    rib_ipv6_static_route3['Route'] = '3234:3234::1/128'
    rib_ipv6_static_route3['NumberNexthops'] = '1'
    rib_ipv6_static_route3['2'] = dict()
    rib_ipv6_static_route3['2']['Distance'] = '1'
    rib_ipv6_static_route3['2']['Metric'] = '0'
    rib_ipv6_static_route3['2']['RouteType'] = 'static'
    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 3234:3234::1/128 and its next-hops.
    route_ipv6_static_route3 = rib_ipv6_static_route3
    step("Verifying the IPv4 static routes on switch 1")
    # Verify route 123.0.0.1/32 and next-hops in RIB, FIB and
    # running-config
    aux_route = route_ipv4_static_route1["Route"]
    verify_show(sw1, aux_route, 'static', route_ipv4_static_route1,
                'ip route')
    aux_route = rib_ipv4_static_route1["Route"]
    verify_show(sw1, aux_route, 'static', rib_ipv4_static_route1, 'rib')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=True,
                                                    route='123.0.0.1/32',
                                                    nexthop='1.1.1.2')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=True,
                                                    route='123.0.0.1/32',
                                                    nexthop='2')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=True,
                                                    route='123.0.0.1/32',
                                                    nexthop='3')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=True,
                                                    route='123.0.0.1/32',
                                                    nexthop='5.5.5.1')
    # Verify route 143.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    aux_route = route_ipv4_static_route2["Route"]
    verify_show(sw1, aux_route, 'static', route_ipv4_static_route2,
                'ip route')
    aux_route = rib_ipv4_static_route2["Route"]
    verify_show(sw1, aux_route, 'static', rib_ipv4_static_route2, 'rib')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=True,
                                                    route='143.0.0.1/32',
                                                    nexthop='4.4.4.1')
    # Verify route 163.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    aux_route = route_ipv4_static_route3["Route"]
    verify_show(sw1, aux_route, 'static', route_ipv4_static_route3,
                'ip route')
    aux_route = rib_ipv4_static_route3["Route"]
    verify_show(sw1, aux_route, 'static', rib_ipv4_static_route3, 'rib')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=True,
                                                    route='163.0.0.1/32',
                                                    nexthop='2')
    step("Verifying the IPv6 static routes on switch 1")
    # Verify route 1234:1234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    aux_route = route_ipv6_static_route1["Route"]
    verify_show(sw1, aux_route, 'static', route_ipv6_static_route1,
                'ipv6 route')
    aux_route = rib_ipv6_static_route1["Route"]
    verify_show(sw1, aux_route, 'static', rib_ipv6_static_route1, 'rib')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=False,
                                                    route='1234:1234::1/128',
                                                    nexthop='1')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=False,
                                                    route='1234:1234::1/128',
                                                    nexthop='2')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=False,
                                                    route='1234:1234::1/128',
                                                    nexthop='3')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=False,
                                                    route='1234:1234::1/128',
                                                    nexthop='4')
    # Verify route 2234:2234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    aux_route = route_ipv6_static_route2["Route"]
    verify_show(sw1, aux_route, 'static', route_ipv6_static_route2,
                'ipv6 route')
    aux_route = rib_ipv6_static_route2["Route"]
    verify_show(sw1, aux_route, 'static', rib_ipv6_static_route2, 'rib')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=False,
                                                    route='2234:2234::1/128',
                                                    nexthop='4')
    # Verify route 3234:3234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    aux_route = route_ipv6_static_route3["Route"]
    verify_show(sw1, aux_route, 'static', route_ipv6_static_route3,
                'ipv6 route')
    aux_route = rib_ipv6_static_route3["Route"]
    verify_show(sw1, aux_route, 'static', rib_ipv6_static_route3, 'rib')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=False,
                                                    route='3234:3234::1/128',
                                                    nexthop='2')


# This test does "no routing" trigger on the routed interfaces and checks if
# the routes and next-hops show correctly or deleted correctly in the output
# of "show ip/ipv6 route/show rib/show running-config".
def no_routing_trigger_static_routes(sw1, sw2, step):
    step("Entering interface for link 1 SW1, to execute 'no routing'")
    # Make the L3 interface 1 as L2 by executing "no routing"
    sw1("interface {}".format(sw1.ports["if01"]))
    sw1("no routing")
    sw1("exit")
    step("Entering interface for link 4 SW1, to execute 'no routing'")
    # Make the L3 interface 4 as L2 by executing "no routing"
    sw1("interface {}".format(sw1.ports["if04"]))
    sw1("no routing")
    sw1("exit")
    # Populate the expected RIB ("show rib") route dictionary for the route
    # 123.0.0.1/32 and its next-hops. The next-hops which were routing via
    # "no routed" interfaces should be removed from the RIB.
    rib_ipv4_static_route1 = dict()
    rib_ipv4_static_route1['Route'] = '123.0.0.1/32'
    rib_ipv4_static_route1['NumberNexthops'] = '2'
    rib_ipv4_static_route1['2'] = dict()
    rib_ipv4_static_route1['2']['Distance'] = '1'
    rib_ipv4_static_route1['2']['Metric'] = '0'
    rib_ipv4_static_route1['2']['RouteType'] = 'static'
    rib_ipv4_static_route1['3'] = dict()
    rib_ipv4_static_route1['3']['Distance'] = '1'
    rib_ipv4_static_route1['3']['Metric'] = '0'
    rib_ipv4_static_route1['3']['RouteType'] = 'static'
    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 123.0.0.1/32 and its next-hops. The next-hops which were
    # routing via "no routed" interfaces should be removed from the FIB.
    route_ipv4_static_route1 = rib_ipv4_static_route1
    # Populate the expected RIB ("show rib") route dictionary for the route
    # 143.0.0.1/32 and its next-hops. The next-hops which were routing via
    # "no routed" interfaces should be removed from the RIB.
    rib_ipv4_static_route2 = dict()
    rib_ipv4_static_route2['Route'] = '143.0.0.1/32'
    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 143.0.0.1/32 and its next-hops. The next-hops which were
    # routing via "no routed" interfaces should be removed from the FIB.
    route_ipv4_static_route2 = rib_ipv4_static_route2
    # Populate the expected RIB ("show rib") route dictionary for the route
    # 163.0.0.1/32 and its next-hops. The next-hops which were routing via
    # "no routed" interfaces should be removed from the RIB.
    rib_ipv4_static_route3 = dict()
    rib_ipv4_static_route3['Route'] = '163.0.0.1/32'
    rib_ipv4_static_route3['NumberNexthops'] = '1'
    rib_ipv4_static_route3['2'] = dict()
    rib_ipv4_static_route3['2']['Distance'] = '1'
    rib_ipv4_static_route3['2']['Metric'] = '0'
    rib_ipv4_static_route3['2']['RouteType'] = 'static'
    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 163.0.0.1/32 and its next-hops. The next-hops which were
    # routing via "no routed" interfaces should be removed from the FIB.
    route_ipv4_static_route3 = rib_ipv4_static_route3
    # Populate the expected RIB ("show rib") route dictionary for the route
    # 1234:1234::1/128 and its next-hops. The next-hops which were routing via
    # "no routed" interfaces should be removed from the RIB.
    rib_ipv6_static_route1 = dict()
    rib_ipv6_static_route1['Route'] = '1234:1234::1/128'
    rib_ipv6_static_route1['NumberNexthops'] = '2'
    rib_ipv6_static_route1['2'] = dict()
    rib_ipv6_static_route1['2']['Distance'] = '1'
    rib_ipv6_static_route1['2']['Metric'] = '0'
    rib_ipv6_static_route1['2']['RouteType'] = 'static'
    rib_ipv6_static_route1['3'] = dict()
    rib_ipv6_static_route1['3']['Distance'] = '1'
    rib_ipv6_static_route1['3']['Metric'] = '0'
    rib_ipv6_static_route1['3']['RouteType'] = 'static'
    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 1234:1234::1/128 and its next-hops. The next-hops which were
    # routing via "no routed" interfaces should be removed from the FIB.
    route_ipv6_static_route1 = rib_ipv6_static_route1
    # Populate the expected RIB ("show rib") route dictionary for the route
    # 2234:2234::1/128 and its next-hops. The next-hops which were routing via
    # "no routed" interfaces should be removed from the RIB.
    rib_ipv6_static_route2 = dict()
    rib_ipv6_static_route2['Route'] = '2234:2234::1/128'
    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 2234:2234::1/128 and its next-hops. The next-hops which were
    # routing via "no routed" interfaces should be removed from the FIB.
    route_ipv6_static_route2 = rib_ipv6_static_route2
    # Populate the expected RIB ("show rib") route dictionary for the route
    # 3234:3234::1/128 and its next-hops. The next-hops which were routing via
    # "no routed" interfaces should be removed from the RIB.
    rib_ipv6_static_route3 = dict()
    rib_ipv6_static_route3['Route'] = '3234:3234::1/128'
    rib_ipv6_static_route3['NumberNexthops'] = '1'
    rib_ipv6_static_route3['2'] = dict()
    rib_ipv6_static_route3['2']['Distance'] = '1'
    rib_ipv6_static_route3['2']['Metric'] = '0'
    rib_ipv6_static_route3['2']['RouteType'] = 'static'
    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 3234:3234::1/128 and its next-hops. The next-hops which were
    # routing via "no routed" interfaces should be removed from the FIB.
    route_ipv6_static_route3 = rib_ipv6_static_route3
    step("Verifying the IPv4 static routes on switch 1")
    # Verify route 123.0.0.1/32 and next-hops in RIB, FIB and
    # running-config. The next-hops which were "no routed" should not
    # appear in running-config.
    aux_route = route_ipv4_static_route1["Route"]
    verify_show(sw1, aux_route, 'static', route_ipv4_static_route1,
                'ip route')
    aux_route = rib_ipv4_static_route1["Route"]
    verify_show(sw1, aux_route, 'static', rib_ipv4_static_route1, 'rib')
    assert not route_and_nexthop_in_show_running_config(sw1=sw1,
                                                        if_ipv4=True,
                                                        route='123.0.0.1/32',
                                                        nexthop='1.1.1.2')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=True,
                                                    route='123.0.0.1/32',
                                                    nexthop='2')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=True,
                                                    route='123.0.0.1/32',
                                                    nexthop='3')
    assert not route_and_nexthop_in_show_running_config(sw1=sw1,
                                                        if_ipv4=True,
                                                        route='123.0.0.1/32',
                                                        nexthop='5.5.5.1')
    # Verify route 143.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    aux_route = route_ipv4_static_route2["Route"]
    verify_show(sw1, aux_route, 'static', route_ipv4_static_route2,
                'ip route')
    aux_route = rib_ipv4_static_route2["Route"]
    verify_show(sw1, aux_route, 'static', rib_ipv4_static_route2, 'rib')
    assert not route_and_nexthop_in_show_running_config(sw1=sw1,
                                                        if_ipv4=True,
                                                        route='143.0.0.1/32',
                                                        nexthop='4.4.4.1')
    # Verify route 163.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    aux_route = route_ipv4_static_route3["Route"]
    verify_show(sw1, aux_route, 'static', route_ipv4_static_route3,
                'ip route')
    aux_route = rib_ipv4_static_route3["Route"]
    verify_show(sw1, aux_route, 'static', rib_ipv4_static_route3, 'rib')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=True,
                                                    route='163.0.0.1/32',
                                                    nexthop='2')
    step("Verifying the IPv6 static routes on switch 1")
    # Verify route 1234:1234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    aux_route = route_ipv6_static_route1["Route"]
    verify_show(sw1, aux_route, 'static', route_ipv6_static_route1,
                'ipv6 route')
    aux_route = rib_ipv6_static_route1["Route"]
    verify_show(sw1, aux_route, 'static', rib_ipv6_static_route1, 'rib')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=False,
                                                    route='1234:1234::1/128',
                                                    nexthop='1')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=False,
                                                    route='1234:1234::1/128',
                                                    nexthop='2')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=False,
                                                    route='1234:1234::1/128',
                                                    nexthop='3')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=False,
                                                    route='1234:1234::1/128',
                                                    nexthop='4')
    # Verify route 2234:2234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    aux_route = route_ipv6_static_route2["Route"]
    verify_show(sw1, aux_route, 'static', route_ipv6_static_route2,
                'ipv6 route')
    aux_route = rib_ipv6_static_route2["Route"]
    verify_show(sw1, aux_route, 'static', rib_ipv6_static_route2, 'rib')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=False,
                                                    route='2234:2234::1/128',
                                                    nexthop='4')
    # Verify route 3234:3234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    aux_route = route_ipv6_static_route3["Route"]
    verify_show(sw1, aux_route, 'static', route_ipv6_static_route3,
                'ipv6 route')
    aux_route = rib_ipv6_static_route3["Route"]
    verify_show(sw1, aux_route, 'static', rib_ipv6_static_route3, 'rib')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=False,
                                                    route='3234:3234::1/128',
                                                    nexthop='2')


# This test does "routing" trigger on the non-routed interfaces and checks if
# the routes and next-hops show correctly or not added incorrectly in the
# output of "show ip/ipv6 route/show rib/show running-config".
def routing_trigger_static_routes(sw1, sw2, step):
    step("Entering interface for link 1 SW1, to execute 'routing'")
    # Make the L2 interface 1 as L3 by executing "routing"
    sw1("interface {}".format(sw1.ports["if01"]))
    sw1("routing")
    sw1("exit")
    step("Entering interface for link 4 SW1, to execute 'routing'")
    # Make the L2 interface 4 as L3 by executing "routing"
    sw1("interface {}".format(sw1.ports["if04"]))
    sw1("routing")
    sw1("exit")
    # Populate the expected RIB ("show rib") route dictionary for the route
    # 123.0.0.1/32 and its next-hops. "Routing" trigger on interfaces should
    # not add any next-hops to the RIB.
    rib_ipv4_static_route1 = dict()
    rib_ipv4_static_route1['Route'] = '123.0.0.1/32'
    rib_ipv4_static_route1['NumberNexthops'] = '2'
    rib_ipv4_static_route1['2'] = dict()
    rib_ipv4_static_route1['2']['Distance'] = '1'
    rib_ipv4_static_route1['2']['Metric'] = '0'
    rib_ipv4_static_route1['2']['RouteType'] = 'static'
    rib_ipv4_static_route1['3'] = dict()
    rib_ipv4_static_route1['3']['Distance'] = '1'
    rib_ipv4_static_route1['3']['Metric'] = '0'
    rib_ipv4_static_route1['3']['RouteType'] = 'static'
    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 123.0.0.1/32 and its next-hops. "Routing" trigger on interfaces
    # should not add any next-hops to the RIB.
    route_ipv4_static_route1 = rib_ipv4_static_route1
    # Populate the expected RIB ("show rib") route dictionary for the route
    # 143.0.0.1/32 and its next-hops. "Routing" trigger on interfaces should
    # not add any next-hops to the RIB.
    rib_ipv4_static_route2 = dict()
    rib_ipv4_static_route2['Route'] = '143.0.0.1/32'
    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 143.0.0.1/32 and its next-hops. "Routing" trigger on interfaces
    # should not add any next-hops to the RIB.
    route_ipv4_static_route2 = rib_ipv4_static_route2
    # Populate the expected RIB ("show rib") route dictionary for the route
    # 163.0.0.1/32 and its next-hops. "Routing" trigger on interfaces should
    # not add any next-hops to the RIB.
    rib_ipv4_static_route3 = dict()
    rib_ipv4_static_route3['Route'] = '163.0.0.1/32'
    rib_ipv4_static_route3['NumberNexthops'] = '1'
    rib_ipv4_static_route3['2'] = dict()
    rib_ipv4_static_route3['2']['Distance'] = '1'
    rib_ipv4_static_route3['2']['Metric'] = '0'
    rib_ipv4_static_route3['2']['RouteType'] = 'static'
    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 163.0.0.1/32 and its next-hops. "Routing" trigger on interfaces
    # should not add any next-hops to the RIB.
    route_ipv4_static_route3 = rib_ipv4_static_route3
    # Populate the expected RIB ("show rib") route dictionary for the route
    # 1234:1234::1/128 and its next-hops. "Routing" trigger on interfaces
    # should not add any next-hops to the RIB.
    rib_ipv6_static_route1 = dict()
    rib_ipv6_static_route1['Route'] = '1234:1234::1/128'
    rib_ipv6_static_route1['NumberNexthops'] = '2'
    rib_ipv6_static_route1['2'] = dict()
    rib_ipv6_static_route1['2']['Distance'] = '1'
    rib_ipv6_static_route1['2']['Metric'] = '0'
    rib_ipv6_static_route1['2']['RouteType'] = 'static'
    rib_ipv6_static_route1['3'] = dict()
    rib_ipv6_static_route1['3']['Distance'] = '1'
    rib_ipv6_static_route1['3']['Metric'] = '0'
    rib_ipv6_static_route1['3']['RouteType'] = 'static'
    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 1234:1234::1/128 and its next-hops. "Routing" trigger on
    # interfaces should not add any next-hops to the RIB.
    route_ipv6_static_route1 = rib_ipv6_static_route1
    # Populate the expected RIB ("show rib") route dictionary for the route
    # 2234:2234::1/128 and its next-hops. "Routing" trigger on interfaces
    # should not add any next-hops to the RIB.
    rib_ipv6_static_route2 = dict()
    rib_ipv6_static_route2['Route'] = '2234:2234::1/128'
    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 2234:2234::1/128 and its next-hops. "Routing" trigger on
    # interfaces should not add any next-hops to the RIB.
    route_ipv6_static_route2 = rib_ipv6_static_route2
    # Populate the expected RIB ("show rib") route dictionary for the route
    # 3234:3234::1/128 and its next-hops. "Routing" trigger on interfaces
    # should not add any next-hops to the RIB.
    rib_ipv6_static_route3 = dict()
    rib_ipv6_static_route3['Route'] = '3234:3234::1/128'
    rib_ipv6_static_route3['NumberNexthops'] = '1'
    rib_ipv6_static_route3['2'] = dict()
    rib_ipv6_static_route3['2']['Distance'] = '1'
    rib_ipv6_static_route3['2']['Metric'] = '0'
    rib_ipv6_static_route3['2']['RouteType'] = 'static'
    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 3234:3234::1/128 and its next-hops. "Routing" trigger on
    # interfaces should not add any next-hops to the RIB.
    route_ipv6_static_route3 = rib_ipv6_static_route3
    step("Verifying the IPv4 static routes on switch 1")
    # Verify route 123.0.0.1/32 and next-hops in RIB, FIB and
    # running-config. The next-hops which were "no routed" earlier and
    # now routed should not appear in running-config.
    aux_route = route_ipv4_static_route1["Route"]
    verify_show(sw1, aux_route, 'static', route_ipv4_static_route1,
                'ip route')
    aux_route = rib_ipv4_static_route1["Route"]
    verify_show(sw1, aux_route, 'static', rib_ipv4_static_route1, 'rib')
    assert not route_and_nexthop_in_show_running_config(sw1=sw1,
                                                        if_ipv4=True,
                                                        route='123.0.0.1/32',
                                                        nexthop='1.1.1.2')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=True,
                                                    route='123.0.0.1/32',
                                                    nexthop='2')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=True,
                                                    route='123.0.0.1/32',
                                                    nexthop='3')
    assert not route_and_nexthop_in_show_running_config(sw1=sw1,
                                                        if_ipv4=True,
                                                        route='123.0.0.1/32',
                                                        nexthop='5.5.5.1')
    # Verify route 143.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of active next-hops in running-config and absence of deleted
    # next-hops in running-config
    aux_route = route_ipv4_static_route2["Route"]
    verify_show(sw1, aux_route, 'static', route_ipv4_static_route2,
                'ip route')
    aux_route = rib_ipv4_static_route2["Route"]
    verify_show(sw1, aux_route, 'static', rib_ipv4_static_route2, 'rib')
    assert not route_and_nexthop_in_show_running_config(sw1=sw1,
                                                        if_ipv4=True,
                                                        route='143.0.0.1/32',
                                                        nexthop='4.4.4.1')
    # Verify route 163.0.0.1/32 and next-hops in RIB, FIB and verify
    # the presence of active next-hops in running-config and absence of
    # deleted next-hops in running-config
    aux_route = route_ipv4_static_route3["Route"]
    verify_show(sw1, aux_route, 'static', route_ipv4_static_route3,
                'ip route')
    aux_route = rib_ipv4_static_route3["Route"]
    verify_show(sw1, aux_route, 'static', rib_ipv4_static_route3, 'rib')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=True,
                                                    route='163.0.0.1/32',
                                                    nexthop='2')
    step("Verifying the IPv6 static routes on switch 1")
    # Verify route 1234:1234::1/128 and next-hops in RIB, FIB and verify the
    # presence of active next-hops in running-config and absence of deleted
    # next-hops in running-config
    aux_route = route_ipv6_static_route1["Route"]
    verify_show(sw1, aux_route, 'static', route_ipv6_static_route1,
                'ipv6 route')
    aux_route = rib_ipv6_static_route1["Route"]
    verify_show(sw1, aux_route, 'static', rib_ipv6_static_route1, 'rib')
    aux_route = '1234:1234::1/128'
    assert not route_and_nexthop_in_show_running_config(sw1=sw1,
                                                        if_ipv4=False,
                                                        route=aux_route,
                                                        nexthop='1')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=False,
                                                    route='1234:1234::1/128',
                                                    nexthop='2')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=False,
                                                    route='1234:1234::1/128',
                                                    nexthop='3')
    aux_route = '1234:1234::1/128'
    assert not route_and_nexthop_in_show_running_config(sw1=sw1,
                                                        if_ipv4=False,
                                                        route=aux_route,
                                                        nexthop='4')
    # Verify route 2234:2234::1/128 and next-hops in RIB, FIB and verify the
    # presence of active next-hops in running-config and absence of deleted
    # next-hops in running-config
    aux_route = route_ipv6_static_route2["Route"]
    verify_show(sw1, aux_route, 'static', route_ipv6_static_route2,
                'ipv6 route')
    aux_route = rib_ipv6_static_route2["Route"]
    verify_show(sw1, aux_route, 'static', rib_ipv6_static_route2, 'rib')
    aux_route = '2234:2234::1/128'
    assert not route_and_nexthop_in_show_running_config(sw1=sw1,
                                                        if_ipv4=False,
                                                        route=aux_route,
                                                        nexthop='4')
    # Verify route 3234:3234::1/128 and next-hops in RIB, FIB and
    # running-config. The next-hops which were "no routed" earlier and
    # now routed should not appear in running-config.
    aux_route = route_ipv6_static_route3["Route"]
    verify_show(sw1, aux_route, 'static', route_ipv6_static_route3,
                'ipv6 route')
    aux_route = rib_ipv6_static_route3["Route"]
    verify_show(sw1, aux_route, 'static', rib_ipv6_static_route3, 'rib')
    assert route_and_nexthop_in_show_running_config(sw1=sw1,
                                                    if_ipv4=False,
                                                    route='3234:3234::1/128',
                                                    nexthop='2')


def test_zebra_ct_no_routing_trigger(topology, step):
    sw1 = topology.get("sw1")
    assert sw1 is not None
    sw2 = topology.get("sw2")
    assert sw2 is not None
    add_static_routes(sw1, sw2, step)
    no_routing_trigger_static_routes(sw1, sw2, step)
    routing_trigger_static_routes(sw1, sw2, step)
