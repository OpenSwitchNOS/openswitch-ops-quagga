
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


# This test configures IPv4 and IPv6 ECMP static routes and checks if the
# routes and next-hops show correctly in the output of
# "show ip route/show rib". The route configuration is also verified in
# the output of "show running-config".
def add_static_routes(**kwargs):

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
              "ip/ip6 address")

    # Configure IPv4 address on interface 1 on switch1
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk01'],
                                  addr="1.1.1.1", mask=24, config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to configure an ipv4 address"

    # Configure IPv6 address on interface 1 on switch1
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk01'],
                                  addr="111:111::1", mask=64, ipv6flag=True,
                                  config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to configure an ipv6 address"

    LogOutput('info', "Entering interface for link 2 SW1, giving an "
              "ip/ip6 address")

    # Configure IPv4 address on interface 2 on switch1
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk02'],
                                  addr="2.2.2.2", mask=24, config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to configure an ipv4 address"

    # Configure IPv6 address on interface 2 on switch1
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk02'],
                                  addr="222:222::2", mask=64, ipv6flag=True,
                                  config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to configure an ipv6 address"

    LogOutput('info', "Entering interface for link 3 SW1, giving an "
              "ip/ip6 address")

    # Configure IPv4 address on interface 3 on switch1
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk03'],
                                  addr="3.3.3.3", mask=24, config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to configure an ipv4 address"

    # Configure IPv6 address on interface 3 on switch1
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk03'],
                                  addr="333:333::3", mask=64, ipv6flag=True,
                                  config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to configure an ipv6 address"

    LogOutput('info', "Entering interface for link 4 SW1, giving an "
              "ip/ip6 address")

    # Configure IPv4 address on interface 4 on switch1
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk04'],
                                  addr="4.4.4.4", mask=24, config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to configure an ipv4 address"

    # Configure IPv6 address on interface 4 on switch1
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk04'],
                                  addr="444:444::4", mask=64, ipv6flag=True,
                                  config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to configure an ipv6 address"

    LogOutput('info', "Entering interface for link 4 SW1, giving an secondary "
              "ip/ip6 address")

    # Configure IPv4 secondary address on interface 4 on switch1
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk04'],
                                  addr="5.5.5.5", mask=24, config=True,
                                  secondary=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to configure a secondary ipv4 address"

    # Configure IPv6 secondary address on interface 4 on switch1
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk04'],
                                  addr="555:555::5", mask=64, ipv6flag=True,
                                  config=True, secondary=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to configure a secondary ipv6 address"

    LogOutput('info', "\n\n\n######### Configuring switch 1 IPv4 "
              "static routes #########")

    # Configure IPv4 route 123.0.0.1/32 with 4 ECMP next-hops.
    retStruct = IpRouteConfig(deviceObj=switch1, route="123.0.0.1", mask=32,
                              nexthop="1.1.1.2", config=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv4 route"

    retStruct = IpRouteConfig(deviceObj=switch1, route="123.0.0.1", mask=32,
                              nexthop="2", config=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv4 route"

    retStruct = IpRouteConfig(deviceObj=switch1, route="123.0.0.1", mask=32,
                              nexthop="3", config=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv4 route"

    retStruct = IpRouteConfig(deviceObj=switch1, route="123.0.0.1", mask=32,
                              nexthop="5.5.5.1", config=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv4 route"

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 123.0.0.1/32 and its next-hops.
    ExpRibDictIpv4StaticRoute1 = dict()
    ExpRibDictIpv4StaticRoute1['Route'] = '123.0.0.1' + '/' + '32'
    ExpRibDictIpv4StaticRoute1['NumberNexthops'] = '4'
    ExpRibDictIpv4StaticRoute1['1.1.1.2'] = dict()
    ExpRibDictIpv4StaticRoute1['1.1.1.2']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute1['1.1.1.2']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute1['1.1.1.2']['RouteType'] = 'static'
    ExpRibDictIpv4StaticRoute1['2'] = dict()
    ExpRibDictIpv4StaticRoute1['2']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute1['2']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute1['2']['RouteType'] = 'static'
    ExpRibDictIpv4StaticRoute1['3'] = dict()
    ExpRibDictIpv4StaticRoute1['3']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute1['3']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute1['3']['RouteType'] = 'static'
    ExpRibDictIpv4StaticRoute1['5.5.5.1'] = dict()
    ExpRibDictIpv4StaticRoute1['5.5.5.1']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute1['5.5.5.1']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute1['5.5.5.1']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 123.0.0.1/32 and its next-hops.
    ExpRouteDictIpv4StaticRoute1 = ExpRibDictIpv4StaticRoute1

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

    # Configure IPv4 route 163.0.0.1/32 with 1 next-hop.
    retStruct = IpRouteConfig(deviceObj=switch1, route="163.0.0.1", mask=32,
                              nexthop="2", config=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv4 route"

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 163.0.0.1/32 and its next-hops.
    ExpRibDictIpv4StaticRoute3 = dict()
    ExpRibDictIpv4StaticRoute3['Route'] = '163.0.0.1' + '/' + '32'
    ExpRibDictIpv4StaticRoute3['NumberNexthops'] = '1'
    ExpRibDictIpv4StaticRoute3['2'] = dict()
    ExpRibDictIpv4StaticRoute3['2']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute3['2']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute3['2']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 163.0.0.1/32 and its next-hops.
    ExpRouteDictIpv4StaticRoute3 = ExpRibDictIpv4StaticRoute3

    LogOutput('info', "\n\n\n######### Configuring switch 1 IPv6 static "
              "routes #########")

    # Configure IPv6 route 1234:1234::1/128 with 4 ECMP next-hops.
    retStruct = IpRouteConfig(deviceObj=switch1, route="1234:1234::1",
                              mask=128, nexthop="1", config=True,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv6 route"

    retStruct = IpRouteConfig(deviceObj=switch1, route="1234:1234::1",
                              mask=128, nexthop="2", config=True,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv6 route"

    retStruct = IpRouteConfig(deviceObj=switch1, route="1234:1234::1",
                              mask=128, nexthop="3", config=True,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv6 route"

    retStruct = IpRouteConfig(deviceObj=switch1, route="1234:1234::1",
                              mask=128, nexthop="4", config=True,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv6 route"

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 1234:1234::1/128 and its next-hops.
    ExpRibDictIpv6StaticRoute1 = dict()
    ExpRibDictIpv6StaticRoute1['Route'] = '1234:1234::1' + '/' + '128'
    ExpRibDictIpv6StaticRoute1['NumberNexthops'] = '4'
    ExpRibDictIpv6StaticRoute1['1'] = dict()
    ExpRibDictIpv6StaticRoute1['1']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute1['1']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute1['1']['RouteType'] = 'static'
    ExpRibDictIpv6StaticRoute1['2'] = dict()
    ExpRibDictIpv6StaticRoute1['2']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute1['2']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute1['2']['RouteType'] = 'static'
    ExpRibDictIpv6StaticRoute1['3'] = dict()
    ExpRibDictIpv6StaticRoute1['3']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute1['3']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute1['3']['RouteType'] = 'static'
    ExpRibDictIpv6StaticRoute1['4'] = dict()
    ExpRibDictIpv6StaticRoute1['4']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute1['4']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute1['4']['RouteType'] = 'static'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 1234:1234::1/128 and its next-hops.
    ExpRouteDictIpv6StaticRoute1 = ExpRibDictIpv6StaticRoute1

    # Configure IPv4 route 2234:2234::1/128 with 1 next-hop.
    retStruct = IpRouteConfig(deviceObj=switch1, route="2234:2234::1",
                              mask=128, nexthop="4", config=True,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv6 route"

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 2234:2234::1/128 and its next-hops.
    ExpRibDictIpv6StaticRoute2 = dict()
    ExpRibDictIpv6StaticRoute2['Route'] = '2234:2234::1' + '/' + '128'
    ExpRibDictIpv6StaticRoute2['NumberNexthops'] = '1'
    ExpRibDictIpv6StaticRoute2['4'] = dict()
    ExpRibDictIpv6StaticRoute2['4']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute2['4']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute2['4']['RouteType'] = 'static'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 2234:2234::1/128 and its next-hops.
    ExpRouteDictIpv6StaticRoute2 = ExpRibDictIpv6StaticRoute2

    # Configure IPv4 route 3234:3234::1/128 with 1 next-hop.
    retStruct = IpRouteConfig(deviceObj=switch1, route="3234:3234::1",
                              mask=128, nexthop="2", config=True,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv6 route"

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 3234:3234::1/128 and its next-hops.
    ExpRibDictIpv6StaticRoute3 = dict()
    ExpRibDictIpv6StaticRoute3['Route'] = '3234:3234::1' + '/' + '128'
    ExpRibDictIpv6StaticRoute3['NumberNexthops'] = '1'
    ExpRibDictIpv6StaticRoute3['2'] = dict()
    ExpRibDictIpv6StaticRoute3['2']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute3['2']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute3['2']['RouteType'] = 'static'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 3234:3234::1/128 and its next-hops.
    ExpRouteDictIpv6StaticRoute3 = ExpRibDictIpv6StaticRoute3

    LogOutput('info', "\n\n\n######### Verifying the IPv4 static routes on "
              "switch 1#########")

    # Verify route 123.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute1, 'static')
    verify_route_and_nexthop_in_show_running_config(deviceObj=switch1,
                                                    if_ipv4=True,
                                                    route='123.0.0.1/32',
                                                    nexthop='1.1.1.2')
    verify_route_and_nexthop_in_show_running_config(deviceObj=switch1,
                                                    if_ipv4=True,
                                                    route='123.0.0.1/32',
                                                    nexthop='2')
    verify_route_and_nexthop_in_show_running_config(deviceObj=switch1,
                                                    if_ipv4=True,
                                                    route='123.0.0.1/32',
                                                    nexthop='3')
    verify_route_and_nexthop_in_show_running_config(deviceObj=switch1,
                                                    if_ipv4=True,
                                                    route='123.0.0.1/32',
                                                    nexthop='5.5.5.1')

    # Verify route 143.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute2, 'static')
    verify_route_and_nexthop_in_show_running_config(deviceObj=switch1,
                                                    if_ipv4=True,
                                                    route='143.0.0.1/32',
                                                    nexthop='4.4.4.1')

    # Verify route 163.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute3, 'static')
    verify_route_and_nexthop_in_show_running_config(deviceObj=switch1,
                                                    if_ipv4=True,
                                                    route='163.0.0.1/32',
                                                    nexthop='2')

    LogOutput('info', "\n\n\n######### Verifying the IPv6 static routes on "
              "switch 1#########")

    # Verify route 1234:1234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute1, 'static')
    verify_route_and_nexthop_in_show_running_config(deviceObj=switch1,
                                                    if_ipv4=False,
                                                    route='1234:1234::1/128',
                                                    nexthop='1')
    verify_route_and_nexthop_in_show_running_config(deviceObj=switch1,
                                                    if_ipv4=False,
                                                    route='1234:1234::1/128',
                                                    nexthop='2')
    verify_route_and_nexthop_in_show_running_config(deviceObj=switch1,
                                                    if_ipv4=False,
                                                    route='1234:1234::1/128',
                                                    nexthop='3')
    verify_route_and_nexthop_in_show_running_config(deviceObj=switch1,
                                                    if_ipv4=False,
                                                    route='1234:1234::1/128',
                                                    nexthop='4')

    # Verify route 2234:2234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute2, 'static')
    verify_route_and_nexthop_in_show_running_config(deviceObj=switch1,
                                                    if_ipv4=False,
                                                    route='2234:2234::1/128',
                                                    nexthop='4')

    # Verify route 3234:3234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute3, 'static')
    verify_route_and_nexthop_in_show_running_config(deviceObj=switch1,
                                                    if_ipv4=False,
                                                    route='3234:3234::1/128',
                                                    nexthop='2')

    LogOutput('info', "\n\n\n######### Configuration and verification of "
              "IPv4 and IPv6 static routes on switch 1 passed#########")


# This test removes the configuration for IPv4 and IPv6 ECMP static routes
# and checks if the routes and remaining next-hops show correctly in the
# output of "show ip route/show rib". The route configuration removal is also
# verified in the output of "show running-config".
def delete_static_routes(**kwargs):

    switch1 = kwargs.get('switch1', None)
    switch2 = kwargs.get('switch2', None)

    switch1.commandErrorCheck = 0
    switch2.commandErrorCheck = 0

    # Unconfiguring next-hop 5.5.5.1 for route 123.0.0.1/32
    LogOutput('info', "Unconfiguring next-hop 5.5.5.1 for route 123.0.0.1/32")
    retStruct = IpRouteConfig(deviceObj=switch1, route="123.0.0.1", mask=32,
                              nexthop="5.5.5.1", config=False)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to unconfigure ipv4 route"

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 123.0.0.1/32 and its remaining next-hops.
    ExpRibDictIpv4StaticRoute1 = dict()
    ExpRibDictIpv4StaticRoute1['Route'] = '123.0.0.1' + '/' + '32'
    ExpRibDictIpv4StaticRoute1['NumberNexthops'] = '3'
    ExpRibDictIpv4StaticRoute1['1.1.1.2'] = dict()
    ExpRibDictIpv4StaticRoute1['1.1.1.2']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute1['1.1.1.2']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute1['1.1.1.2']['RouteType'] = 'static'
    ExpRibDictIpv4StaticRoute1['2'] = dict()
    ExpRibDictIpv4StaticRoute1['2']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute1['2']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute1['2']['RouteType'] = 'static'
    ExpRibDictIpv4StaticRoute1['3'] = dict()
    ExpRibDictIpv4StaticRoute1['3']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute1['3']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute1['3']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 123.0.0.1/32 and its remaining next-hops.
    ExpRouteDictIpv4StaticRoute1 = ExpRibDictIpv4StaticRoute1

    # Unconfiguring next-hop 4.4.4.1 for route 143.0.0.1/32
    LogOutput('info', "Unconfiguring next-hop 4.4.4.1 for route 143.0.0.1/32")
    retStruct = IpRouteConfig(deviceObj=switch1, route="143.0.0.1", mask=32,
                              nexthop="4.4.4.1", config=False)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to unconfigure ipv4 route"

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 143.0.0.1/32 and its remaining next-hops.
    ExpRibDictIpv4StaticRoute2 = dict()
    ExpRibDictIpv4StaticRoute2['Route'] = '143.0.0.1' + '/' + '32'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 143.0.0.1/32 and its remaining next-hops.
    ExpRouteDictIpv4StaticRoute2 = ExpRibDictIpv4StaticRoute2

    # Unconfiguring next-hop 2 for route 163.0.0.1/32
    LogOutput('info', "Unconfiguring next-hop 2 for route 163.0.0.1/32")
    retStruct = IpRouteConfig(deviceObj=switch1, route="163.0.0.1", mask=32,
                              nexthop="2", config=False)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to unconfigure ipv4 route"

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 163.0.0.1/32 and its remaining next-hops.
    ExpRibDictIpv4StaticRoute3 = dict()
    ExpRibDictIpv4StaticRoute3['Route'] = '163.0.0.1' + '/' + '32'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 163.0.0.1/32 and its remaining next-hops.
    ExpRouteDictIpv4StaticRoute3 = ExpRibDictIpv4StaticRoute3

    #Unconfiguring next-hop 1 for route 1234:1234::1/128
    LogOutput('info', "Unconfiguring next-hop 1 for route 1234:1234::1/128")
    retStruct = IpRouteConfig(deviceObj=switch1, route="1234:1234::1",
                              mask=128, nexthop="1", config=False,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to unconfigure ipv6 route"

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 1234:1234::1/128 and its remaining next-hops.
    ExpRibDictIpv6StaticRoute1 = dict()
    ExpRibDictIpv6StaticRoute1['Route'] = '1234:1234::1' + '/' + '128'
    ExpRibDictIpv6StaticRoute1['NumberNexthops'] = '3'
    ExpRibDictIpv6StaticRoute1['4'] = dict()
    ExpRibDictIpv6StaticRoute1['4']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute1['4']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute1['4']['RouteType'] = 'static'
    ExpRibDictIpv6StaticRoute1['2'] = dict()
    ExpRibDictIpv6StaticRoute1['2']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute1['2']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute1['2']['RouteType'] = 'static'
    ExpRibDictIpv6StaticRoute1['3'] = dict()
    ExpRibDictIpv6StaticRoute1['3']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute1['3']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute1['3']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 1234:1234::1/128 and its remaining next-hops.
    ExpRouteDictIpv6StaticRoute1 = ExpRibDictIpv6StaticRoute1

    # Unconfiguring next-hop 4 for route 2234:2234::1/128
    LogOutput('info', "Unconfiguring next-hop 4 for route 2234:2234::1/128")
    retStruct = IpRouteConfig(deviceObj=switch1, route="2234:2234::1",
                              mask=128, nexthop="4", config=False,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to unconfigure ipv6 route"

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 2234:2234::1/128 and its remaining next-hops.
    ExpRibDictIpv6StaticRoute2 = dict()
    ExpRibDictIpv6StaticRoute2['Route'] = '2234:2234::1' + '/' + '128'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 2234:2234::1/128 and its remaining next-hops.
    ExpRouteDictIpv6StaticRoute2 = ExpRibDictIpv6StaticRoute2

    LogOutput('info', "\n\n\n######### Verifying the IPv4 static routes "
              "on switch 1#########")

    # Verify route 123.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of active next-hops in running-config and absence of deleted
    # next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute1, 'static')
    verify_route_and_nexthop_in_show_running_config(deviceObj=switch1,
                                                    if_ipv4=True,
                                                    route='123.0.0.1/32',
                                                    nexthop='1.1.1.2')
    verify_route_and_nexthop_in_show_running_config(deviceObj=switch1,
                                                    if_ipv4=True,
                                                    route='123.0.0.1/32',
                                                    nexthop='2')
    verify_route_and_nexthop_in_show_running_config(deviceObj=switch1,
                                                    if_ipv4=True,
                                                    route='123.0.0.1/32',
                                                    nexthop='3')
    verify_route_and_nexthop_not_in_show_running_config(deviceObj=switch1,
                                                        if_ipv4=True,
                                                        route='123.0.0.1/32',
                                                        nexthop='5.5.5.1')

    # Verify route 143.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of active next-hops in running-config and absence of deleted
    # next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute2, 'static')
    verify_route_and_nexthop_not_in_show_running_config(deviceObj=switch1,
                                                        if_ipv4=True,
                                                        route='143.0.0.1/32',
                                                        nexthop='4.4.4.1')

    # Verify route 163.0.0.1/32 and next-hops in RIB, FIB and verify
    # the presence of active next-hops in running-config and absence of
    # deleted next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute3, 'static')
    verify_route_and_nexthop_not_in_show_running_config(deviceObj=switch1,
                                                        if_ipv4=True,
                                                        route='163.0.0.1/32',
                                                        nexthop='2')

    LogOutput('info', "\n\n\n######### Verifying the IPv6 static routes on "
              "switch 1#########")

    # Verify route 1234:1234::1/128 and next-hops in RIB, FIB and verify the
    # presence of active next-hops in running-config and absence of deleted
    # next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute1, 'static')
    verify_route_and_nexthop_not_in_show_running_config(deviceObj=switch1,
                                                        if_ipv4=False,
                                                        route='1234:1234::1/128',
                                                        nexthop='1')
    verify_route_and_nexthop_in_show_running_config(deviceObj=switch1,
                                                    if_ipv4=False,
                                                    route='1234:1234::1/128',
                                                    nexthop='2')
    verify_route_and_nexthop_in_show_running_config(deviceObj=switch1,
                                                    if_ipv4=False,
                                                    route='1234:1234::1/128',
                                                    nexthop='3')
    verify_route_and_nexthop_in_show_running_config(deviceObj=switch1,
                                                    if_ipv4=False,
                                                    route='1234:1234::1/128',
                                                    nexthop='4')

    # Verify route 2234:2234::1/128 and next-hops in RIB, FIB and verify the
    # presence of active next-hops in running-config and absence of deleted
    # next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute2, 'static')
    verify_route_and_nexthop_not_in_show_running_config(deviceObj=switch1,
                                                        if_ipv4=False,
                                                        route='2234:2234::1/128',
                                                        nexthop='4')

    LogOutput('info', "\n\n\n######### Deletion and verification of IPv4 and "
              "IPv6 static routes on switch 1 passed#########")


# Set the maximum timeout for all the test cases
# @pytest.mark.timeout(5000)


# Test class for testing static routes add and delete triggers.
@pytest.mark.skipif(True, reason="Skipping old tests")
class Test_ecmp_route_nexthop_delete:

    def setup_class(cls):
        # Test object will parse command line and formulate the env
        Test_ecmp_route_nexthop_delete.testObj = testEnviron(
                                                topoDict=topoDict,
                                                defSwitchContext="vtyShell")
        # Get topology object
        Test_ecmp_route_nexthop_delete.topoObj = Test_ecmp_route_nexthop_delete.testObj.topoObjGet()

    def teardown_class(cls):
        Test_ecmp_route_nexthop_delete.topoObj.terminate_nodes()

    def test_add_static_routes(self):
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        dut02Obj = self.topoObj.deviceObjGet(device="dut02")
        add_static_routes(switch1=dut01Obj, switch2=dut02Obj)

    def test_delete_static_routes(self):
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        dut02Obj = self.topoObj.deviceObjGet(device="dut02")
        delete_static_routes(switch1=dut01Obj, switch2=dut02Obj)
