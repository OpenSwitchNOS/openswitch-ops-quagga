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

# import pytest
# from opstestfw import *
# from opstestfw.switch.CLI import *
# from opstestfw.switch.OVS import *
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
        assert key in p_dict
        assert dict_from_show[key] == p_dict[key]


def get_vrf_uuid(switch, vrf_name, step):
    """
    This function takes a switch and a vrf_name as inputs and returns
    the uuid of the vrf.
    """
    step("Getting uuid for the vrf {}".format(vrf_name))
    ovsdb_command = 'list vrf {}'.format(vrf_name)
    output = switch(ovsdb_command, shell='vsctl')
    lines = output.splitlines()
    vrf_uuid = None
    for line in lines:
        vrf_uuid = match("(.*)_uuid( +): (.*)", line)
        if vrf_uuid is not None:
            break
    assert vrf_uuid is not None
    return vrf_uuid.group(3).rstrip('\r')


# This test configures IPv4 static/BGP routes and checks if the
# routes and next-hops show correctly selected in the output of
# "show ip route/show rib".
def add_static_bgp_routes(sw1, sw2, step):
    sw1_interfaces = []
    sw1_ifs_ips = ["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4"]
    size = len(sw1_ifs_ips)
    for i in range(size):
        sw1_interfaces.append(sw1.ports["if0{}".format(i+1)])
    sw1_mask = 24
    step("Configuring interfaces and IPs on SW1")
    sw1("configure terminal")
    for i in range(size):
        sw1("interface {}".format(sw1_interfaces[i]))
        sw1("ip address {}/{}".format(sw1_ifs_ips[i], sw1_mask))
        sw1("no shutdown")
        sw1("exit")
        output = sw1("do show running-config")
        assert "interface {}".format(sw1_interfaces[i]) in output
        assert "ip address {}/{}".format(sw1_ifs_ips[i], sw1_mask) in output
    step("Cofiguring sw1 IPV4 static routes")
    nexthops = ["1.1.1.2", "2", "3", "4.4.4.1"]
    for i in range(size):
        sw1("ip route 123.0.0.1/32 {} 10".format(nexthops[i]))
        output = sw1("do show running-config")
        assert "ip route 123.0.0.1/32 {} 10".format(nexthops[i]) in output
    # Populate the expected RIB ("show rib") route dictionary for the route
    # 123.0.0.1/32 and its next-hops.
    rib_ipv4_static_route1 = dict()
    rib_ipv4_static_route1['Route'] = '123.0.0.1/32'
    rib_ipv4_static_route1['NumberNexthops'] = '4'
    rib_ipv4_static_route1['1.1.1.2'] = dict()
    rib_ipv4_static_route1['1.1.1.2']['Distance'] = '10'
    rib_ipv4_static_route1['1.1.1.2']['Metric'] = '0'
    rib_ipv4_static_route1['1.1.1.2']['RouteType'] = 'static'
    rib_ipv4_static_route1['2'] = dict()
    rib_ipv4_static_route1['2']['Distance'] = '10'
    rib_ipv4_static_route1['2']['Metric'] = '0'
    rib_ipv4_static_route1['2']['RouteType'] = 'static'
    rib_ipv4_static_route1['3'] = dict()
    rib_ipv4_static_route1['3']['Distance'] = '10'
    rib_ipv4_static_route1['3']['Metric'] = '0'
    rib_ipv4_static_route1['3']['RouteType'] = 'static'
    rib_ipv4_static_route1['4.4.4.1'] = dict()
    rib_ipv4_static_route1['4.4.4.1']['Distance'] = '10'
    rib_ipv4_static_route1['4.4.4.1']['Metric'] = '0'
    rib_ipv4_static_route1['4.4.4.1']['RouteType'] = 'static'
    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 123.0.0.1/32 and its next-hops. Since static is configured with a
    # higher administration distance than BGP route, so the static route
    # cannot be in FIB.
    route_ipv4_static_route1 = dict()
    route_ipv4_static_route1['Route'] = '123.0.0.1/32'
    sw1("ip route 143.0.0.1/32 4.4.4.1")
    output = sw1("do show running-config")
    assert "ip route 143.0.0.1/32 4.4.4.1" in output
    # Configure IPv4 route 143.0.0.1/32 with 1 next-hop.
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
    step("Configuring switch 1 IPv4 BGP routes")
    # Get the UUID od the default vrf on the sw1
    vrf_uuid = get_vrf_uuid(sw1, "vrf_default", step)
    # Prepare string for a BGP route 123.0.0.1/32 using ovsdb-client with
    # lower administration distance as compared with the corresponding
    # static route.This makes the BGP route more preferable than the static
    # route.
    bpg_route_cmd_ipv4_route1 = "ovsdb-client transact \'[ \"OpenSwitch\",\
         {\
             \"op\" : \"insert\",\
             \"table\" : \"Nexthop\",\
             \"row\" : {\
                 \"ip_address\" : \"3.3.3.5\",\
                 \"weight\" : 3,\
                 \"selected\": true\
             },\
             \"uuid-name\" : \"nh01\"\
         },\
        {\
            \"op\" : \"insert\",\
            \"table\" : \"Route\",\
            \"row\" : {\
                     \"prefix\":\"123.0.0.1/32\",\
                     \"from\":\"bgp\",\
                     \"vrf\":[\"uuid\",\"%s\"],\
                     \"address_family\":\"ipv4\",\
                     \"sub_address_family\":\"unicast\",\
                     \"distance\":6,\
                     \"nexthops\" : [\
                     \"set\",\
                     [\
                         [\
                             \"named-uuid\",\
                             \"nh01\"\
                         ]\
                     ]]\
                     }\
        }\
    ]\'" % vrf_uuid
    # Configure the BGP route for prefix 123.0.0.1/32 using ovsdb-client
    # interface
    sw1(bpg_route_cmd_ipv4_route1, shell='bash')
    # Populate the expected RIB ("show rib") route dictionary for the BGP route
    # 123.0.0.1/32 and its next-hops.
    rib_ipv4_bgp_route1 = dict()
    rib_ipv4_bgp_route1['Route'] = '123.0.0.1/32'
    rib_ipv4_bgp_route1['NumberNexthops'] = '1'
    rib_ipv4_bgp_route1['3.3.3.5'] = dict()
    rib_ipv4_bgp_route1['3.3.3.5']['Distance'] = '6'
    rib_ipv4_bgp_route1['3.3.3.5']['Metric'] = '0'
    rib_ipv4_bgp_route1['3.3.3.5']['RouteType'] = 'bgp'
    # Populate the expected FIB ("show ip route") route dictionary for the BGP
    # route 143.0.0.1/32 and its next-hops.
    route_ipv4_bgp_route1 = rib_ipv4_bgp_route1
    # Prepare string for a BGP route 143.0.0.1/32 using ovsdb-client with
    # administration distance as greater than the corresponding static route.
    # This makes the BGP route less preferable than the corresponding
    # static route.
    bpg_route_command_ipv4_route2 = "ovsdb-client transact \'[ \"OpenSwitch\",\
         {\
             \"op\" : \"insert\",\
             \"table\" : \"Nexthop\",\
             \"row\" : {\
                 \"ip_address\" : \"3.3.3.5\",\
                 \"weight\" : 3,\
                 \"selected\": true\
             },\
             \"uuid-name\" : \"nh01\"\
         },\
        {\
            \"op\" : \"insert\",\
            \"table\" : \"Route\",\
            \"row\" : {\
                     \"prefix\":\"143.0.0.1/32\",\
                     \"from\":\"bgp\",\
                     \"vrf\":[\"uuid\",\"%s\"],\
                     \"address_family\":\"ipv4\",\
                     \"sub_address_family\":\"unicast\",\
                     \"distance\":6,\
                     \"nexthops\" : [\
                     \"set\",\
                     [\
                         [\
                             \"named-uuid\",\
                             \"nh01\"\
                         ]\
                     ]]\
                     }\
        }\
    ]\'" % vrf_uuid
    # Configure the BGP route for prefix 143.0.0.1/32 using ovsdb-client
    # interface
    sw1(bpg_route_command_ipv4_route2, shell='bash')
    # Populate the expected RIB ("show rib") route dictionary for the BGP route
    # 143.0.0.1/32 and its next-hops.
    rib_ipv4_bgp_route2 = dict()
    rib_ipv4_bgp_route2['Route'] = '143.0.0.1/32'
    rib_ipv4_bgp_route2['NumberNexthops'] = '1'
    rib_ipv4_bgp_route2['3.3.3.5'] = dict()
    rib_ipv4_bgp_route2['3.3.3.5']['Distance'] = '6'
    rib_ipv4_bgp_route2['3.3.3.5']['Metric'] = '0'
    rib_ipv4_bgp_route2['3.3.3.5']['RouteType'] = 'bgp'
    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 123.0.0.1/32 and its next-hops. Since static is configured with a
    # lower administration distance than BGP route, so the BGP route cannot be
    # in FIB.
    route_ipv4_bgp_route2 = dict()
    route_ipv4_bgp_route2['Route'] = '143.0.0.1/32'
    step("Verifying the IPv4 static and BGP routes on switch 1")
    aux_route = rib_ipv4_static_route1['Route']
    verify_show(sw1, aux_route, 'static', rib_ipv4_static_route1, "rib")
    aux_route = route_ipv4_bgp_route1['Route']
    verify_show(sw1, aux_route, 'bgp', route_ipv4_bgp_route1, "ip route")
    aux_route = rib_ipv4_bgp_route1['Route']
    verify_show(sw1, aux_route, 'bgp', rib_ipv4_bgp_route1, "rib")
    aux_route = route_ipv4_static_route2["Route"]
    verify_show(sw1, aux_route, 'static', route_ipv4_static_route2,
                'ip route')
    aux_route = rib_ipv4_static_route2['Route']
    verify_show(sw1, aux_route, 'static', rib_ipv4_static_route2, "rib")
    aux_route = route_ipv4_bgp_route2["Route"]
    verify_show(sw1, aux_route, 'bgp', route_ipv4_bgp_route2, "ip route")
    aux_route = rib_ipv4_bgp_route2['Route']
    verify_show(sw1, aux_route, 'bgp', rib_ipv4_bgp_route2, "rib")


# This test deletes IPv4 static/BGP routes and checks if the
# routes and next-hops show correctly selected in the output of
def delete_static_bgp_routes(sw1, sw2, step):
    step("Testing the BGP and static route deletion on sw1")
    step("Deleting 123.0.0.0.1/32 BGP route on sw1")
    # Command to delete the BGP route 123.0.0.1/32. This should make the static
    # route more preferable in RIB.
    bgp_route_delete_command = "ovsdb-client transact \'[ \"OpenSwitch\",\
        {\
            \"op\" : \"delete\",\
            \"table\" : \"Route\",\
             \"where\":[[\"prefix\",\"==\",\"123.0.0.1/32\"],[\"from\",\"==\",\"bgp\"]]\
        }\
    ]\'"
    # Delete the BGP route for prefix 123.0.0.1/32 using ovsdb-client interface
    sw1(bgp_route_delete_command, shell='bash')
    # Delete the static route for 143.0.0.1/32 so that BGP route becomes the
    # more preferable route in RIB.
    step("Deleting 143.0.0.0.1/32 static route on sw1")
    sw1("no ip route 143.0.0.1/32 4.4.4.1")
    # Populate the expected RIB ("show rib") route dictionary for the route
    # 123.0.0.1/32 and its next-hops.
    rib_ipv4_static_route1 = dict()
    rib_ipv4_static_route1['Route'] = '123.0.0.1/32'
    rib_ipv4_static_route1['NumberNexthops'] = '4'
    rib_ipv4_static_route1['1.1.1.2'] = dict()
    rib_ipv4_static_route1['1.1.1.2']['Distance'] = '10'
    rib_ipv4_static_route1['1.1.1.2']['Metric'] = '0'
    rib_ipv4_static_route1['1.1.1.2']['RouteType'] = 'static'
    rib_ipv4_static_route1['2'] = dict()
    rib_ipv4_static_route1['2']['Distance'] = '10'
    rib_ipv4_static_route1['2']['Metric'] = '0'
    rib_ipv4_static_route1['2']['RouteType'] = 'static'
    rib_ipv4_static_route1['3'] = dict()
    rib_ipv4_static_route1['3']['Distance'] = '10'
    rib_ipv4_static_route1['3']['Metric'] = '0'
    rib_ipv4_static_route1['3']['RouteType'] = 'static'
    rib_ipv4_static_route1['4.4.4.1'] = dict()
    rib_ipv4_static_route1['4.4.4.1']['Distance'] = '10'
    rib_ipv4_static_route1['4.4.4.1']['Metric'] = '0'
    rib_ipv4_static_route1['4.4.4.1']['RouteType'] = 'static'
    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 123.0.0.1/32 and its next-hops.
    route_ipv4_static_route1 = rib_ipv4_static_route1
    # Populate the expected RIB ("show rib") route dictionary for the BGP route
    # 123.0.0.1/32 and its next-hops. This should not be in RIB as it has been
    # deleted.
    rib_ipv4_bgp_route1 = dict()
    rib_ipv4_bgp_route1['Route'] = '123.0.0.1/32'
    # Populate the expected FIB ("show ip route") route dictionary for the BGP
    # route 123.0.0.1/32 and its next-hops. This should not be in FIB as it has
    # been deleted.
    route_ipv4_bgp_route1 = rib_ipv4_bgp_route1
    # Populate the expected RIB ("show rib") route dictionary for the static
    # route 143.0.0.1/32 and its next-hops. This should not be in RIB as it has
    # been deleted.
    rib_ipv4_static_route2 = dict()
    rib_ipv4_static_route2['Route'] = '143.0.0.1/32'
    # Populate the expected RIB ("show rib") route dictionary for the static
    # route 143.0.0.1/32 and its next-hops. This should not be in FIB as it
    # has been deleted.
    route_ipv4_static_route2 = rib_ipv4_static_route2
    # Populate the expected RIB ("show rib") route dictionary for the BGP route
    # 123.0.0.1/32 and its next-hops.
    rib_ipv4_bgp_route2 = dict()
    rib_ipv4_bgp_route2['Route'] = '143.0.0.1/32'
    rib_ipv4_bgp_route2['NumberNexthops'] = '1'
    rib_ipv4_bgp_route2['3.3.3.5'] = dict()
    rib_ipv4_bgp_route2['3.3.3.5']['Distance'] = '6'
    rib_ipv4_bgp_route2['3.3.3.5']['Metric'] = '0'
    rib_ipv4_bgp_route2['3.3.3.5']['RouteType'] = 'bgp'
    # Populate the expected FIB ("show ip route") route dictionary for the BGP
    # route 123.0.0.1/32 and its next-hops.
    route_ipv4_bgp_route2 = rib_ipv4_bgp_route2
    step("Verifying the IPv4 static and BGP "
         "routes on switch 1 after route deletes")
    # Verify the static/BGP routes in RIB and FIB
    aux_route = route_ipv4_static_route1["Route"]
    verify_show(sw1, aux_route, 'static', route_ipv4_static_route1, "ip route")
    aux_route = rib_ipv4_static_route1["Route"]
    verify_show(sw1, aux_route, 'static', rib_ipv4_static_route1, "rib")
    aux_route = route_ipv4_bgp_route1["Route"]
    verify_show(sw1, aux_route, 'bgp', route_ipv4_bgp_route1, "ip route")
    aux_route = rib_ipv4_bgp_route1["Route"]
    verify_show(sw1, aux_route, 'bgp', rib_ipv4_bgp_route1, "rib")
    aux_route = route_ipv4_static_route2["Route"]
    verify_show(sw1, aux_route, 'static', route_ipv4_static_route2, "ip route")
    aux_route = rib_ipv4_static_route2["Route"]
    verify_show(sw1, aux_route, 'static', rib_ipv4_static_route2, "rib")
    aux_route = route_ipv4_bgp_route2["Route"]
    verify_show(sw1, aux_route, 'bgp', route_ipv4_bgp_route2, "ip route")
    aux_route = rib_ipv4_bgp_route2["Route"]
    verify_show(sw1, aux_route, 'bgp', rib_ipv4_bgp_route2, "rib")


def test_zebra_ct_ipv4_static_bgp_nexthop_selection(topology, step):
    sw1 = topology.get("sw1")
    assert sw1 is not None
    sw2 = topology.get("sw2")
    assert sw2 is not None
    add_static_bgp_routes(sw1, sw2, step)
    delete_static_bgp_routes(sw1, sw2, step)
