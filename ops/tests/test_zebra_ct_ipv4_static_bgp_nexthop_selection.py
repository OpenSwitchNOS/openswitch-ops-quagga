#!/usr/bin/python

# (c) Copyright 2015 Hewlett Packard Enterprise Development LP
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

import pytest
from opstestfw import *
from opstestfw.switch.CLI import *
from opstestfw.switch.OVS import *
import re

# Topology definition. the topology contains two back to back switches
# having four links between them.
topoDict = {"topoExecution": 1000,
            "topoTarget": "dut01 dut02",
            "topoDevices": "dut01 dut02",
            "topoLinks": "lnk01:dut01:dut02,\
                          lnk02:dut01:dut02,\
                          lnk03:dut01:dut02,\
                          lnk04:dut01:dut02",
            "topoFilters": "dut01:system-category:switch,\
                            dut02:system-category:switch"}

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


def get_vrf_uuid(switch, vrf_name):
    """
    This function takes a switch and a vrf_name as inputs and returns
    the uuid of the vrf.

    """
    LogOutput('info', "\n\n\nGetting uuid for the vrf " + vrf_name)

    ovsdb_command = 'ovs-vsctl list vrf ' + vrf_name
    devIntRetStruct = switch.DeviceInteract(command=ovsdb_command)
    retCode = devIntRetStruct.get('returnCode')
    vrf_buffer = devIntRetStruct.get('buffer')
    if retCode != 0:
        assert "Failed to get the vrf information"

    lines = vrf_buffer.split('\n')

    vrf_uuid = None
    for line in lines:
        vrf_uuid = re.match("(.*)_uuid( +): (.*)", line)

        if vrf_uuid is not None:
            break

    if vrf_uuid is not None:
        print "The vrf uuid is: " + vrf_uuid.group(3).rstrip('\r')
    else:
        assert "Could not locate vrf uuid"

    return vrf_uuid.group(3).rstrip('\r')


# This test configures IPv4 static/BGP routes and checks if the
# routes and next-hops show correctly selected in the output of
# "show ip route/show rib".
def add_static_bgp_routes(**kwargs):

    switch1 = kwargs.get('switch1', None)
    switch2 = kwargs.get('switch2', None)

    switch1.commandErrorCheck = 0
    switch2.commandErrorCheck = 0

    # Enabling interface 1 on switch1
    LogOutput('info', "Enabling interface1 on SW1")
    retStruct = InterfaceEnable(deviceObj=switch1, enable=True,
                                interface=switch1.linkPortMapping['lnk01'])
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Unable to enable interafce on SW1"

    # Enabling interface 2 on switch1
    LogOutput('info', "Enabling interface2 on SW1")
    retStruct = InterfaceEnable(deviceObj=switch1, enable=True,
                                interface=switch1.linkPortMapping['lnk02'])
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Unable to enable interafce on SW1"

    # Enabling interface 3 on switch1
    LogOutput('info', "Enabling interface3 on SW1")
    retStruct = InterfaceEnable(deviceObj=switch1, enable=True,
                                interface=switch1.linkPortMapping['lnk03'])
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Unable to enable interafce on SW1"

    # Enabling interface 4 on switch1
    LogOutput('info', "Enabling interface4 on SW1")
    retStruct = InterfaceEnable(deviceObj=switch1, enable=True,
                                interface=switch1.linkPortMapping['lnk04'])
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Unable to enable interafce on SW1"

    LogOutput('info', "Entering interface for link 1 SW1, giving an "
              "ip address")

    # Configure IPv4 address on interface 1 on switch1
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk01'],
                                  addr="1.1.1.1", mask=24, config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to configure an ipv4 address"

    LogOutput('info', "Entering interface for link 2 SW1, giving an "
              "ip address")

    # Configure IPv4 address on interface 2 on switch1
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk02'],
                                  addr="2.2.2.2", mask=24, config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to configure an ipv4 address"

    LogOutput('info', "Entering interface for link 3 SW1, giving an "
              "ip address")

    # Configure IPv4 address on interface 3 on switch1
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk03'],
                                  addr="3.3.3.3", mask=24, config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to configure an ipv4 address"

    LogOutput('info', "Entering interface for link 4 SW1, giving an "
              "ip address")

    # Configure IPv4 address on interface 4 on switch1
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk04'],
                                  addr="4.4.4.4", mask=24, config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to configure an ipv4 address"

    LogOutput('info', "\n\n\n######### Configuring switch 1 "
              "IPv4 static routes #########")

    # Configure IPv4 route 123.0.0.1/32 with 4 ECMP next-hops with
    # administration distance as 10.
    retStruct = IpRouteConfig(deviceObj=switch1, route="123.0.0.1", mask=32,
                              nexthop="1.1.1.2", config=True, metric=10)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv4 route"

    retStruct = IpRouteConfig(deviceObj=switch1, route="123.0.0.1", mask=32,
                              nexthop="2", config=True, metric=10)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv4 route"

    retStruct = IpRouteConfig(deviceObj=switch1, route="123.0.0.1", mask=32,
                              nexthop="3", config=True, metric=10)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv4 route"

    retStruct = IpRouteConfig(deviceObj=switch1, route="123.0.0.1", mask=32,
                              nexthop="4.4.4.1", config=True, metric=10)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv4 route"

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 123.0.0.1/32 and its next-hops.
    ExpRibDictIpv4StaticRoute1 = dict()
    ExpRibDictIpv4StaticRoute1['Route'] = '123.0.0.1' + '/' + '32'
    ExpRibDictIpv4StaticRoute1['NumberNexthops'] = '4'
    ExpRibDictIpv4StaticRoute1['1.1.1.2'] = dict()
    ExpRibDictIpv4StaticRoute1['1.1.1.2']['Distance'] = '10'
    ExpRibDictIpv4StaticRoute1['1.1.1.2']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute1['1.1.1.2']['RouteType'] = 'static'
    ExpRibDictIpv4StaticRoute1['2'] = dict()
    ExpRibDictIpv4StaticRoute1['2']['Distance'] = '10'
    ExpRibDictIpv4StaticRoute1['2']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute1['2']['RouteType'] = 'static'
    ExpRibDictIpv4StaticRoute1['3'] = dict()
    ExpRibDictIpv4StaticRoute1['3']['Distance'] = '10'
    ExpRibDictIpv4StaticRoute1['3']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute1['3']['RouteType'] = 'static'
    ExpRibDictIpv4StaticRoute1['4.4.4.1'] = dict()
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['Distance'] = '10'
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 123.0.0.1/32 and its next-hops. Since static is configured with a
    # higher administration distance than BGP route, so the static route
    # cannot be in FIB.
    ExpRouteDictIpv4StaticRoute1 = dict()
    ExpRouteDictIpv4StaticRoute1['Route'] = '123.0.0.1' + '/' + '32'

    # Configure IPv4 route 143.0.0.1/32 with 1 next-hop.
    retStruct = IpRouteConfig(deviceObj=switch1, route="143.0.0.1", mask=32,
                              nexthop="4.4.4.1", config=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv4 route"

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 143.0.0.1/32 and its next-hops.
    ExpRibDictIpv4StaticRoute2 = dict()
    ExpRibDictIpv4StaticRoute2['Route'] = '143.0.0.1' + '/' + '32'
    ExpRibDictIpv4StaticRoute2['NumberNexthops'] = '1'
    ExpRibDictIpv4StaticRoute2['4.4.4.1'] = dict()
    ExpRibDictIpv4StaticRoute2['4.4.4.1']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute2['4.4.4.1']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute2['4.4.4.1']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 143.0.0.1/32 and its next-hops.
    ExpRouteDictIpv4StaticRoute2 = ExpRibDictIpv4StaticRoute2

    LogOutput('info', "\n\n\n######### Configuring switch 1 "
              "IPv4 BGP routes #########")

    # Get the UUID od the default vrf on the switch1
    vrf_uuid = get_vrf_uuid(switch1, "vrf_default")

    # Prepare string for a BGP route 123.0.0.1/32 using ovsdb-client with
    # lower administration distance as compared with the corresponding
    # static route.This makes the BGP route more preferable than the static
    # route.
    bpg_route_command_ipv4_route1 = "ovsdb-client transact \'[ \"OpenSwitch\",\
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
]\'" %(vrf_uuid)

    # Configure the BGP route for prefix 123.0.0.1/32 using ovsdb-client
    # interface
    devIntRetStruct = switch1.DeviceInteract(command=bpg_route_command_ipv4_route1)
    retCode = devIntRetStruct.get('returnCode')
    if retCode != 0:
        assert "Failed to configure IPv4 BGP route"

    # Populate the expected RIB ("show rib") route dictionary for the BGP route
    # 123.0.0.1/32 and its next-hops.
    ExpRibDictIpv4BgpRoute1 = dict()
    ExpRibDictIpv4BgpRoute1['Route'] = '123.0.0.1' + '/' + '32'
    ExpRibDictIpv4BgpRoute1['NumberNexthops'] = '1'
    ExpRibDictIpv4BgpRoute1['3.3.3.5'] = dict()
    ExpRibDictIpv4BgpRoute1['3.3.3.5']['Distance'] = '6'
    ExpRibDictIpv4BgpRoute1['3.3.3.5']['Metric'] = '0'
    ExpRibDictIpv4BgpRoute1['3.3.3.5']['RouteType'] = 'bgp'

    # Populate the expected FIB ("show ip route") route dictionary for the BGP
    # route 143.0.0.1/32 and its next-hops.
    ExpRouteDictIpv4BgpRoute1 = ExpRibDictIpv4BgpRoute1

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
]\'" %(vrf_uuid)

    # Configure the BGP route for prefix 143.0.0.1/32 using ovsdb-client
    # interface
    devIntRetStruct = switch1.DeviceInteract(
                                        command=bpg_route_command_ipv4_route2)
    retCode = devIntRetStruct.get('returnCode')
    if retCode != 0:
        assert "Failed to configure IPv4 BGP route"

    # Populate the expected RIB ("show rib") route dictionary for the BGP route
    # 143.0.0.1/32 and its next-hops.
    ExpRibDictIpv4BgpRoute2 = dict()
    ExpRibDictIpv4BgpRoute2['Route'] = '143.0.0.1' + '/' + '32'
    ExpRibDictIpv4BgpRoute2['NumberNexthops'] = '1'
    ExpRibDictIpv4BgpRoute2['3.3.3.5'] = dict()
    ExpRibDictIpv4BgpRoute2['3.3.3.5']['Distance'] = '6'
    ExpRibDictIpv4BgpRoute2['3.3.3.5']['Metric'] = '0'
    ExpRibDictIpv4BgpRoute2['3.3.3.5']['RouteType'] = 'bgp'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 123.0.0.1/32 and its next-hops. Since static is configured with a
    # lower administration distance than BGP route, so the BGP route cannot be
    # in FIB.
    ExpRouteDictIpv4BgpRoute2 = dict()
    ExpRouteDictIpv4BgpRoute2['Route'] = '143.0.0.1' + '/' + '32'

    LogOutput('info', "\n\n\n######### Verifying the IPv4 static "
              "and BGP routes on switch 1#########")

    # Verify the static/BGP routes in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute1, 'static')
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4BgpRoute1, 'bgp')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4BgpRoute1, 'bgp')
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute2, 'static')
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4BgpRoute2, 'bgp')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4BgpRoute2, 'bgp')

    LogOutput('info', "\n\n\n######### Configuration and verification "
              "of IPv4 static and BGP routes on switch 1 passed#########")


# This test deletes IPv4 static/BGP routes and checks if the
# routes and next-hops show correctly selected in the output of
def delete_static_bgp_routes(**kwargs):

    switch1 = kwargs.get('switch1', None)
    switch2 = kwargs.get('switch2', None)

    switch1.commandErrorCheck = 0
    switch2.commandErrorCheck = 0

    LogOutput('info', "\n\n\n######### Testing the BGP and static route "
              "deletion on switch1 #########")

    LogOutput('info', "Deleting 123.0.0.0.1/32 BGP route on switch1 #########")

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
    devIntRetStruct = switch1.DeviceInteract(command=bgp_route_delete_command)
    retCode = devIntRetStruct.get('returnCode')
    if retCode != 0:
        assert "Failed to delete the IPv4 BGP route"

    # Delete the static route for 143.0.0.1/32 so that BGP route becomes the
    # more preferable route in RIB.
    LogOutput('info', "Deleting 143.0.0.0.1/32 static route on "
              "switch1 #########")
    retStruct = IpRouteConfig(deviceObj=switch1, route="143.0.0.1", mask=32,
                              nexthop="4.4.4.1", config=False)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to delete ipv4 route"

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 123.0.0.1/32 and its next-hops.
    ExpRibDictIpv4StaticRoute1 = dict()
    ExpRibDictIpv4StaticRoute1['Route'] = '123.0.0.1' + '/' + '32'
    ExpRibDictIpv4StaticRoute1['NumberNexthops'] = '4'
    ExpRibDictIpv4StaticRoute1['1.1.1.2'] = dict()
    ExpRibDictIpv4StaticRoute1['1.1.1.2']['Distance'] = '10'
    ExpRibDictIpv4StaticRoute1['1.1.1.2']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute1['1.1.1.2']['RouteType'] = 'static'
    ExpRibDictIpv4StaticRoute1['2'] = dict()
    ExpRibDictIpv4StaticRoute1['2']['Distance'] = '10'
    ExpRibDictIpv4StaticRoute1['2']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute1['2']['RouteType'] = 'static'
    ExpRibDictIpv4StaticRoute1['3'] = dict()
    ExpRibDictIpv4StaticRoute1['3']['Distance'] = '10'
    ExpRibDictIpv4StaticRoute1['3']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute1['3']['RouteType'] = 'static'
    ExpRibDictIpv4StaticRoute1['4.4.4.1'] = dict()
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['Distance'] = '10'
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 123.0.0.1/32 and its next-hops.
    ExpRouteDictIpv4StaticRoute1 = ExpRibDictIpv4StaticRoute1

    # Populate the expected RIB ("show rib") route dictionary for the BGP route
    # 123.0.0.1/32 and its next-hops. This should not be in RIB as it has been
    # deleted.
    ExpRibDictIpv4BgpRoute1 = dict()
    ExpRibDictIpv4BgpRoute1['Route'] = '123.0.0.1' + '/' + '32'

    # Populate the expected FIB ("show ip route") route dictionary for the BGP
    # route 123.0.0.1/32 and its next-hops. This should not be in FIB as it has
    # been deleted.
    ExpRouteDictIpv4BgpRoute1 = ExpRibDictIpv4BgpRoute1

    # Populate the expected RIB ("show rib") route dictionary for the static
    # route 143.0.0.1/32 and its next-hops. This should not be in RIB as it has
    # been deleted.
    ExpRibDictIpv4StaticRoute2 = dict()
    ExpRibDictIpv4StaticRoute2['Route'] = '143.0.0.1' + '/' + '32'

    # Populate the expected RIB ("show rib") route dictionary for the static
    # route 143.0.0.1/32 and its next-hops. This should not be in FIB as it
    # has been deleted.
    ExpRouteDictIpv4StaticRoute2 = ExpRibDictIpv4StaticRoute2

    # Populate the expected RIB ("show rib") route dictionary for the BGP route
    # 123.0.0.1/32 and its next-hops.
    ExpRibDictIpv4BgpRoute2 = dict()
    ExpRibDictIpv4BgpRoute2['Route'] = '143.0.0.1' + '/' + '32'
    ExpRibDictIpv4BgpRoute2['NumberNexthops'] = '1'
    ExpRibDictIpv4BgpRoute2['3.3.3.5'] = dict()
    ExpRibDictIpv4BgpRoute2['3.3.3.5']['Distance'] = '6'
    ExpRibDictIpv4BgpRoute2['3.3.3.5']['Metric'] = '0'
    ExpRibDictIpv4BgpRoute2['3.3.3.5']['RouteType'] = 'bgp'

    # Populate the expected FIB ("show ip route") route dictionary for the BGP
    # route 123.0.0.1/32 and its next-hops.
    ExpRouteDictIpv4BgpRoute2 = ExpRibDictIpv4BgpRoute2

    LogOutput('info', "\n\n\n######### Verifying the IPv4 static and BGP "
              "routes on switch 1 after route deletes#########")

    # Verify the static/BGP routes in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute1, 'static')
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4BgpRoute1, 'bgp')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4BgpRoute1, 'bgp')
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute2, 'static')
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4BgpRoute2, 'bgp')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4BgpRoute2, 'bgp')


# Set the maximum timeout for all the test cases
# @pytest.mark.timeout(5000)


# Test class for testing static/BGP routes add and delete triggers.
@pytest.mark.skipif(True, reason="Skipping old tests")
class Test_static_bgp_nexthop_selection:
    def setup_class(cls):
        # Test object will parse command line and formulate the env
        Test_static_bgp_nexthop_selection.testObj = testEnviron(topoDict=topoDict)
        # Get topology object
        Test_static_bgp_nexthop_selection.topoObj = Test_static_bgp_nexthop_selection.testObj.topoObjGet()

    def teardown_class(cls):
        Test_static_bgp_nexthop_selection.topoObj.terminate_nodes()

    def test_add_static_bgp_routes(self):
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        dut02Obj = self.topoObj.deviceObjGet(device="dut02")
        add_static_bgp_routes(switch1=dut01Obj, switch2=dut02Obj)

    def test_delete_static_bgp_routes(self):
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        dut02Obj = self.topoObj.deviceObjGet(device="dut02")
        delete_static_bgp_routes(switch1=dut01Obj, switch2=dut02Obj)
