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
# "show ip/ipv6 route/show rib".
def configure_static_routes(**kwargs):

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

    LogOutput('info', "Entering interface for link 1 SW1, "
              "giving an ip/ip6 address")

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

    LogOutput('info', "Entering interface for link 2 SW1, "
              "giving an ip/ip6 address")

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

    LogOutput('info', "Entering interface for link 3 SW1, "
              "giving an ip/ip6 address")

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

    LogOutput('info', "Entering interface for link 4 SW1, "
              "giving an ip/ip6 address")

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

    LogOutput('info', "Entering interface for link 4 SW1, "
              "giving an secondary ip/ip6 address")

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

    LogOutput('info', "\n\n\n######### Configuring switch 1 "
              "IP static routes #########")

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

    LogOutput('info', "\n\n\n######### Configuring switch 1 "
              "IPv6 static routes #########")

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

    # Verify route 123.0.0.1/32 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute1, 'static')

    # Verify route 143.0.0.1/32 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute2, 'static')

    # Verify route 163.0.0.1/32 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute3, 'static')

    LogOutput('info', "\n\n\n######### Verifying the IPv6 static routes on "
              "switch 1#########")

    # Verify route 1234:1234::1/128 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute1, 'static')

    # Verify route 2234:2234::1/128 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute2, 'static')

    # Verify route 3234:3234::1/128 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute3, 'static')

    LogOutput('info', "\n\n\n######### Configuration and verification of IPv4 "
              "and IPv6 static routes on switch 1 passed#########")


# This test shuts down two interfaces and checks if the static routes and
# next-hops show correctly in the output of "show ip/ipv6 route/show rib".
def interface_shut_trigger_static_routes(**kwargs):

    switch1 = kwargs.get('switch1', None)
    switch2 = kwargs.get('switch2', None)

    switch1.commandErrorCheck = 0
    switch2.commandErrorCheck = 0

    # Shutting interface 2 on switch1
    LogOutput('info', "shutting interface2 on SW1")
    retStruct = InterfaceEnable(deviceObj=switch1, enable=False,
                                interface=switch1.linkPortMapping['lnk02'])
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Unable to disable interafce 2 on SW1"

    # Shutting interface 4 on switch1
    LogOutput('info', "shutting interface4 on SW1")
    retStruct = InterfaceEnable(deviceObj=switch1, enable=False,
                                interface=switch1.linkPortMapping['lnk04'])
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Unable to disable interafce 4 on SW1"

    # Add a new IPv4 static route 193.0.0.1/32 via interface 4
    LogOutput('info', "Add a ipv4 static route via shut interface4 on SW1")
    retStruct = IpRouteConfig(deviceObj=switch1, route="193.0.0.1", mask=32,
                              nexthop="4", config=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv4 route"

    # Add a new IPv6 static route 4234:4234::1/128 via interface 4
    LogOutput('info', "Add a ipv6 static route via shut interface4 on SW1")
    retStruct = IpRouteConfig(deviceObj=switch1, route="4234:4234::1",
                              mask=128, nexthop="4", config=True,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv6 route"

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 123.0.0.1/32 and its next-hops. The next-hops via interfaces 2 and
    # 4 should be withdrawn from FIB.
    ExpRouteDictIpv4StaticRoute1 = dict()
    ExpRouteDictIpv4StaticRoute1['Route'] = '123.0.0.1' + '/' + '32'
    ExpRouteDictIpv4StaticRoute1['NumberNexthops'] = '2'
    ExpRouteDictIpv4StaticRoute1['1.1.1.2'] = dict()
    ExpRouteDictIpv4StaticRoute1['1.1.1.2']['Distance'] = '1'
    ExpRouteDictIpv4StaticRoute1['1.1.1.2']['Metric'] = '0'
    ExpRouteDictIpv4StaticRoute1['1.1.1.2']['RouteType'] = 'static'
    ExpRouteDictIpv4StaticRoute1['3'] = dict()
    ExpRouteDictIpv4StaticRoute1['3']['Distance'] = '1'
    ExpRouteDictIpv4StaticRoute1['3']['Metric'] = '0'
    ExpRouteDictIpv4StaticRoute1['3']['RouteType'] = 'static'

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 123.0.0.1/32 and its next-hops. All four next-hops of the route should
    # be maintained in the RIB.
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
    # route 143.0.0.1/32 and its next-hops. The next-hop for the route
    # should be withdrawn from the FIB.
    ExpRouteDictIpv4StaticRoute2 = dict()
    ExpRouteDictIpv4StaticRoute2['Route'] = '143.0.0.1' + '/' + '32'

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 143.0.0.1/32 and its next-hops. The next-hop for the route
    # should be maintained in the RIB.
    ExpRibDictIpv4StaticRoute2 = dict()
    ExpRibDictIpv4StaticRoute2['Route'] = '143.0.0.1' + '/' + '32'
    ExpRibDictIpv4StaticRoute2['NumberNexthops'] = '1'
    ExpRibDictIpv4StaticRoute2['4.4.4.1'] = dict()
    ExpRibDictIpv4StaticRoute2['4.4.4.1']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute2['4.4.4.1']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute2['4.4.4.1']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 163.0.0.1/32 and its next-hops. The next-hop for the route
    # should be withdrawn from the FIB.
    ExpRouteDictIpv4StaticRoute3 = dict()
    ExpRouteDictIpv4StaticRoute3['Route'] = '163.0.0.1' + '/' + '32'

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 163.0.0.1/32 and its next-hops. The next-hop for the route
    # should be maintained in the RIB.
    ExpRibDictIpv4StaticRoute3 = dict()
    ExpRibDictIpv4StaticRoute3['Route'] = '163.0.0.1' + '/' + '32'
    ExpRibDictIpv4StaticRoute3['NumberNexthops'] = '1'
    ExpRibDictIpv4StaticRoute3['2'] = dict()
    ExpRibDictIpv4StaticRoute3['2']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute3['2']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute3['2']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 193.0.0.1/32 and its next-hops. The next-hop for the route
    # should not be programmed into the FIB.
    ExpRouteDictIpv4StaticRoute4 = dict()
    ExpRouteDictIpv4StaticRoute4['Route'] = '193.0.0.1' + '/' + '32'

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 193.0.0.1/32 and its next-hops. The next-hop for the route
    # should be maintained in the RIB.
    ExpRibDictIpv4StaticRoute4 = dict()
    ExpRibDictIpv4StaticRoute4['Route'] = '193.0.0.1' + '/' + '32'
    ExpRibDictIpv4StaticRoute4['NumberNexthops'] = '1'
    ExpRibDictIpv4StaticRoute4['4'] = dict()
    ExpRibDictIpv4StaticRoute4['4']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute4['4']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute4['4']['RouteType'] = 'static'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 1234:1234::1/128 and its next-hops. The next-hops via interfaces 2
    # and 4 should be withdrawn from FIB.
    ExpRouteDictIpv6StaticRoute1 = dict()
    ExpRouteDictIpv6StaticRoute1['Route'] = '1234:1234::1' + '/' + '128'
    ExpRouteDictIpv6StaticRoute1['NumberNexthops'] = '2'
    ExpRouteDictIpv6StaticRoute1['1'] = dict()
    ExpRouteDictIpv6StaticRoute1['1']['Distance'] = '1'
    ExpRouteDictIpv6StaticRoute1['1']['Metric'] = '0'
    ExpRouteDictIpv6StaticRoute1['1']['RouteType'] = 'static'
    ExpRouteDictIpv6StaticRoute1['3'] = dict()
    ExpRouteDictIpv6StaticRoute1['3']['Distance'] = '1'
    ExpRouteDictIpv6StaticRoute1['3']['Metric'] = '0'
    ExpRouteDictIpv6StaticRoute1['3']['RouteType'] = 'static'

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 1234:1234::1/128 and its next-hops. All four next-hops of the route
    # should be maintained in the RIB.
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
    # route 2234:2234::1/128 and its next-hops. The next-hops via interfaces 2
    # and 4 should be withdrawn from FIB.
    ExpRouteDictIpv6StaticRoute2 = dict()
    ExpRouteDictIpv6StaticRoute2['Route'] = '2234:2234::1' + '/' + '128'

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 2234:2234::1/128 and its next-hops. the next-hops of the route
    # should be maintained in the RIB.
    ExpRibDictIpv6StaticRoute2 = dict()
    ExpRibDictIpv6StaticRoute2['Route'] = '2234:2234::1' + '/' + '128'
    ExpRibDictIpv6StaticRoute2['NumberNexthops'] = '1'
    ExpRibDictIpv6StaticRoute2['4'] = dict()
    ExpRibDictIpv6StaticRoute2['4']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute2['4']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute2['4']['RouteType'] = 'static'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 3234:3234::1/128 and its next-hops. The next-hops via interfaces 2
    # and 4 should be withdrawn from FIB.
    ExpRouteDictIpv6StaticRoute3 = dict()
    ExpRouteDictIpv6StaticRoute3['Route'] = '3234:3234::1' + '/' + '128'

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 3234:3234::1/128 and its next-hops. the next-hops of the route
    # should be maintained in the RIB.
    ExpRibDictIpv6StaticRoute3 = dict()
    ExpRibDictIpv6StaticRoute3['Route'] = '3234:3234::1' + '/' + '128'
    ExpRibDictIpv6StaticRoute3['NumberNexthops'] = '1'
    ExpRibDictIpv6StaticRoute3['2'] = dict()
    ExpRibDictIpv6StaticRoute3['2']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute3['2']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute3['2']['RouteType'] = 'static'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 4234:4234::1/128 and its next-hops. The next-hops via interfaces 2
    # and 4 should not be added into the FIB.
    ExpRouteDictIpv6StaticRoute4 = dict()
    ExpRouteDictIpv6StaticRoute4['Route'] = '4234:4234::1' + '/' + '128'

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 4234:4234::1/128 and its next-hops. the next-hops of the route
    # should be maintained in the RIB.
    ExpRibDictIpv6StaticRoute4 = dict()
    ExpRibDictIpv6StaticRoute4['Route'] = '4234:4234::1' + '/' + '128'
    ExpRibDictIpv6StaticRoute4['NumberNexthops'] = '1'
    ExpRibDictIpv6StaticRoute4['4'] = dict()
    ExpRibDictIpv6StaticRoute4['4']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute4['4']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute4['4']['RouteType'] = 'static'

    LogOutput('info', "\n\n\n######### Verifying the IPv4 static routes on "
              "switch 1 after interface shut triggers#########")

    # Verify route 123.0.0.1/32 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute1, 'static')

    # Verify route 143.0.0.1/32 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute2, 'static')

    # Verify route 163.0.0.1/32 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute3, 'static')

    # Verify route 193.0.0.1/32 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute4,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute4, 'static')

    LogOutput('info', "\n\n\n######### Verifying the IPv6 static routes on "
              "switch 1 after interface shut triggers#########")

    # Verify route 1234:1234::1/128 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute1, 'static')

    # Verify route 2234:2234::1/128 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute2, 'static')

    # Verify route 3234:3234::1/128 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute3, 'static')

    # Verify route 4234:4234::1/128 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute4,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute4, 'static')

    LogOutput('info', "\n\n\n######### Verification of IPv4 and IPv6 static "
              "routes on switch 1 after interface shutdown passed#########")


# This test brings up two shut down interfaces and checks if the static
# routes and next-hops show correctly in the output of
# "show ip/ipv6 route/show rib".
def interface_no_shut_trigger_static_routes(**kwargs):

    switch1 = kwargs.get('switch1', None)
    switch2 = kwargs.get('switch2', None)

    switch1.commandErrorCheck = 0
    switch2.commandErrorCheck = 0

    # Un-Shutting interface 2 on switch1
    LogOutput('info', "Un-shutting interface2 on SW1")
    retStruct = InterfaceEnable(deviceObj=switch1, enable=True,
                                interface=switch1.linkPortMapping['lnk02'])
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Unable to disable interafce 2 on SW1"

    # Un-Shutting interface 4 on switch1
    LogOutput('info', "Un-shutting interface4 on SW1")
    retStruct = InterfaceEnable(deviceObj=switch1, enable=True,
                                interface=switch1.linkPortMapping['lnk04'])
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Unable to disable interafce 4 on SW1"

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
    # route 123.0.0.1/32 and its next-hops. The next-hops via interfaces
    # 2 and 4 should now be present in the FIB.
    ExpRouteDictIpv4StaticRoute1 = ExpRibDictIpv4StaticRoute1

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 143.0.0.1/32 and its next-hops.
    ExpRibDictIpv4StaticRoute2 = dict()
    ExpRibDictIpv4StaticRoute2['Route'] = '143.0.0.1' + '/' + '32'
    ExpRibDictIpv4StaticRoute2['NumberNexthops'] = '1'
    ExpRibDictIpv4StaticRoute2['4.4.4.1'] = dict()
    ExpRibDictIpv4StaticRoute2['4.4.4.1']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute2['4.4.4.1']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute2['4.4.4.1']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 143.0.0.1/32 and its next-hops. The next-hops via interfaces
    # 2 and 4 should now be present in the FIB.
    ExpRouteDictIpv4StaticRoute2 = ExpRibDictIpv4StaticRoute2

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 163.0.0.1/32 and its next-hops.
    ExpRibDictIpv4StaticRoute3 = dict()
    ExpRibDictIpv4StaticRoute3['Route'] = '163.0.0.1' + '/' + '32'
    ExpRibDictIpv4StaticRoute3['NumberNexthops'] = '1'
    ExpRibDictIpv4StaticRoute3['2'] = dict()
    ExpRibDictIpv4StaticRoute3['2']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute3['2']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute3['2']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 163.0.0.1/32 and its next-hops. The next-hops via interfaces
    # 2 and 4 should now be present in the FIB.
    ExpRouteDictIpv4StaticRoute3 = ExpRibDictIpv4StaticRoute3

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 193.0.0.1/32 and its next-hops.
    ExpRibDictIpv4StaticRoute4 = dict()
    ExpRibDictIpv4StaticRoute4['Route'] = '193.0.0.1' + '/' + '32'
    ExpRibDictIpv4StaticRoute4['NumberNexthops'] = '1'
    ExpRibDictIpv4StaticRoute4['4'] = dict()
    ExpRibDictIpv4StaticRoute4['4']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute4['4']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute4['4']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 193.0.0.1/32 and its next-hops. The next-hops via interfaces
    # 2 and 4 should now be present in the FIB.
    ExpRouteDictIpv4StaticRoute4 = ExpRibDictIpv4StaticRoute4

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
    # route 1234:1234::1/128 and its next-hops. The next-hops via interfaces
    # 2 and 4 should now be present in the FIB.
    ExpRouteDictIpv6StaticRoute1 = ExpRibDictIpv6StaticRoute1

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
    # route 2234:2234::1/128 and its next-hops. The next-hops via interfaces
    # 2 and 4 should now be present in the FIB.
    ExpRouteDictIpv6StaticRoute2 = ExpRibDictIpv6StaticRoute2

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
    # route 3234:3234::1/128 and its next-hops. The next-hops via interfaces
    # 2 and 4 should now be present in the FIB.
    ExpRouteDictIpv6StaticRoute3 = ExpRibDictIpv6StaticRoute3

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 4234:4234::1/128 and its next-hops.
    ExpRibDictIpv6StaticRoute4 = dict()
    ExpRibDictIpv6StaticRoute4['Route'] = '4234:4234::1' + '/' + '128'
    ExpRibDictIpv6StaticRoute4['NumberNexthops'] = '1'
    ExpRibDictIpv6StaticRoute4['4'] = dict()
    ExpRibDictIpv6StaticRoute4['4']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute4['4']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute4['4']['RouteType'] = 'static'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 4234:4234::1/128 and its next-hops. The next-hops via interfaces
    # 2 and 4 should now be present in the FIB.
    ExpRouteDictIpv6StaticRoute4 = ExpRibDictIpv6StaticRoute4

    LogOutput('info', "\n\n\n######### Verifying the IPv4 static routes on "
              "switch 1 after interface no shut triggers#########")

    # Verify route 123.0.0.1/32 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute1, 'static')

    # Verify route 143.0.0.1/32 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute2, 'static')

    # Verify route 163.0.0.1/32 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute3, 'static')

    # Verify route 193.0.0.1/32 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute4,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute4, 'static')

    LogOutput('info', "\n\n\n######### Verifying the IPv6 static routes on "
              "switch 1 after interface no shut triggers#########")

    # Verify route 1234:1234::1/128 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute1, 'static')

    # Verify route 2234:2234::1/128 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute2, 'static')

    # Verify route 3234:3234::1/128 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute3, 'static')

    # Verify route 4234:4234::1/128 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute4,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute4, 'static')

    LogOutput('info', "\n\n\n######### Verification of IPv4 and IPv6 static "
              "routes on switch 1 after interface un-shut passed#########")


# This test unconfigures the interface addresses and checks if the static
# routes and next-hops show correctly in the output of
# "show ip/ipv6 route/show rib".
def interface_unconfiguring_addresses_trigger_static_routes(**kwargs):

    switch1 = kwargs.get('switch1', None)
    switch2 = kwargs.get('switch2', None)

    switch1.commandErrorCheck = 0
    switch2.commandErrorCheck = 0

    # Unconfiguring the IP address on interface 1
    LogOutput('info', "Entering interface for link 1 SW1, removing an "
              "ip/ip6 address")
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk01'],
                                  addr="1.1.1.1", mask=24, config=False)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to unconfigure an ipv4 address"

    # Unconfiguring the IPv6 address on interface 1
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk01'],
                                  addr="111:111::1", mask=64, ipv6flag=True,
                                  config=False)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to unconfigure an ipv6 address"

    # Unconfiguring the secondary IP address on interface 4
    LogOutput('info', "Entering interface for link 4 SW1, removing an "
              "secondary ip/ip6 address")
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk04'],
                                  addr="5.5.5.5", mask=24, config=False,
                                  secondary=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to unconfigure a secondary ipv4 address"

    # Unconfiguring the secondary IPv6 address on interface 4
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk04'],
                                  addr="555:555::5", mask=64, ipv6flag=True,
                                  config=False, secondary=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to unconfigure a secondary ipv6 address"

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 123.0.0.1/32 and its next-hops. The next-hops via IP addresses
    # interfaces 1 and 4  should be withdrawn from FIB.
    ExpRouteDictIpv4StaticRoute1 = dict()
    ExpRouteDictIpv4StaticRoute1['Route'] = '123.0.0.1' + '/' + '32'
    ExpRouteDictIpv4StaticRoute1['NumberNexthops'] = '2'
    ExpRouteDictIpv4StaticRoute1['2'] = dict()
    ExpRouteDictIpv4StaticRoute1['2']['Distance'] = '1'
    ExpRouteDictIpv4StaticRoute1['2']['Metric'] = '0'
    ExpRouteDictIpv4StaticRoute1['2']['RouteType'] = 'static'
    ExpRouteDictIpv4StaticRoute1['3'] = dict()
    ExpRouteDictIpv4StaticRoute1['3']['Distance'] = '1'
    ExpRouteDictIpv4StaticRoute1['3']['Metric'] = '0'
    ExpRouteDictIpv4StaticRoute1['3']['RouteType'] = 'static'

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 123.0.0.1/32 and its next-hops. All four next-hops of the route should
    # be maintained in the RIB.
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

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 143.0.0.1/32 and its next-hops. The next-hops of the route should
    # be maintained in the RIB.
    ExpRibDictIpv4StaticRoute2 = dict()
    ExpRibDictIpv4StaticRoute2['Route'] = '143.0.0.1' + '/' + '32'
    ExpRibDictIpv4StaticRoute2['NumberNexthops'] = '1'
    ExpRibDictIpv4StaticRoute2['4.4.4.1'] = dict()
    ExpRibDictIpv4StaticRoute2['4.4.4.1']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute2['4.4.4.1']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute2['4.4.4.1']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 143.0.0.1/32 and its next-hops. The next-hops via IP addresses
    # interfaces 1 and 4  should be withdrawn from FIB.
    ExpRouteDictIpv4StaticRoute2 = ExpRibDictIpv4StaticRoute2

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 163.0.0.1/32 and its next-hops. The next-hops of the route should
    # be maintained in the RIB.
    ExpRibDictIpv4StaticRoute3 = dict()
    ExpRibDictIpv4StaticRoute3['Route'] = '163.0.0.1' + '/' + '32'
    ExpRibDictIpv4StaticRoute3['NumberNexthops'] = '1'
    ExpRibDictIpv4StaticRoute3['2'] = dict()
    ExpRibDictIpv4StaticRoute3['2']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute3['2']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute3['2']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 163.0.0.1/32 and its next-hops. The next-hops via IP addresses
    # interfaces 1 and 4  should be withdrawn from FIB.
    ExpRouteDictIpv4StaticRoute3 = ExpRibDictIpv4StaticRoute3

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 1234:1234::1/128 and its next-hops. The next-hops of the route
    # should be maintained in the RIB.
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
    # route 1234:1234::1/128 and its next-hops. The next-hops via IPv6
    # addresses interfaces 1 and 4  should be withdrawn from FIB.
    ExpRouteDictIpv6StaticRoute1 = ExpRibDictIpv6StaticRoute1

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 2234:2234::1/128 and its next-hops. The next-hops of the route
    # should be maintained in the RIB.
    ExpRibDictIpv6StaticRoute2 = dict()
    ExpRibDictIpv6StaticRoute2['Route'] = '2234:2234::1' + '/' + '128'
    ExpRibDictIpv6StaticRoute2['NumberNexthops'] = '1'
    ExpRibDictIpv6StaticRoute2['4'] = dict()
    ExpRibDictIpv6StaticRoute2['4']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute2['4']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute2['4']['RouteType'] = 'static'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 2234:2234::1/128 and its next-hops. The next-hops via IPv6
    # addresses interfaces 1 and 4  should be withdrawn from FIB.
    ExpRouteDictIpv6StaticRoute2 = ExpRibDictIpv6StaticRoute2

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 3234:3234::1/128 and its next-hops. The next-hops of the route
    # should be maintained in the RIB.
    ExpRibDictIpv6StaticRoute3 = dict()
    ExpRibDictIpv6StaticRoute3['Route'] = '3234:3234::1' + '/' + '128'
    ExpRibDictIpv6StaticRoute3['NumberNexthops'] = '1'
    ExpRibDictIpv6StaticRoute3['2'] = dict()
    ExpRibDictIpv6StaticRoute3['2']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute3['2']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute3['2']['RouteType'] = 'static'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 3234:3234::1/128 and its next-hops. The next-hops via IPv6
    # addresses interfaces 1 and 4  should be withdrawn from FIB.
    ExpRouteDictIpv6StaticRoute3 = ExpRibDictIpv6StaticRoute3

    LogOutput('info', "\n\n\n######### Verifying the IPv4 static routes on "
              "switch 1 after unconfiguring interface addresses "
              "triggers#########")

    # Verify route 123.0.0.1/32 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute1, 'static')

    # Verify route 143.0.0.1/32 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute2, 'static')

    # Verify route 163.0.0.1/32 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute3, 'static')

    LogOutput('info', "\n\n\n######### Verifying the IPv6 static routes on "
              "switch 1 after unconfiguring interface addresses "
              "triggers#########")

    # Verify route 1234:1234::1/128 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute1, 'static')

    # Verify route 2234:2234::1/128 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute2, 'static')

    # Verify route 3234:3234::1/128 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute3, 'static')


# This test reconfigures the interface addresses and checks if the static
# routes and next-hops show correctly in the output of
# "show ip/ipv6 route/show rib".
def interface_configuring_addresses_trigger_static_routes(**kwargs):
    switch1 = kwargs.get('switch1', None)
    switch2 = kwargs.get('switch2', None)

    switch1.commandErrorCheck = 0
    switch2.commandErrorCheck = 0

    # Reconfiguring the IP address on interface 1
    LogOutput('info', "Entering interface for link 1 SW1, adding an "
              "ip/ip6 address")
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk01'],
                                  addr="1.1.1.1", mask=24, config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to configure an ipv4 address"

    # Reconfiguring the IPv6 address on interface 1
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk01'],
                                  addr="111:111::1", mask=64, ipv6flag=True,
                                  config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to configure an ipv6 address"

    # Reconfiguring the secondary IP address on interface 4
    LogOutput('info', "Entering interface for link 4 SW1, adding an secondary "
              "ip/ip6 address")
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk04'],
                                  addr="5.5.5.5", mask=24, config=True,
                                  secondary=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to configure a secondary ipv4 address"

    # Reconfiguring the secondary IPv6 address on interface 4
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk04'],
                                  addr="555:555::5", mask=64, ipv6flag=True,
                                  config=True, secondary=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to configure a secondary ipv6 address"

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 123.0.0.1/32 and its next-hops. All four next-hops of the route should
    # be maintained in the RIB.
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
    # route 123.0.0.1/32 and its next-hops. The next-hops via IP addresses
    # interfaces 1 and 4  should be reprogrammed into FIB.
    ExpRouteDictIpv4StaticRoute1 = ExpRibDictIpv4StaticRoute1

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 143.0.0.1/32 and its next-hops. The next-hops of the route should
    # be maintained in the RIB.
    ExpRibDictIpv4StaticRoute2 = dict()
    ExpRibDictIpv4StaticRoute2['Route'] = '143.0.0.1' + '/' + '32'
    ExpRibDictIpv4StaticRoute2['NumberNexthops'] = '1'
    ExpRibDictIpv4StaticRoute2['4.4.4.1'] = dict()
    ExpRibDictIpv4StaticRoute2['4.4.4.1']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute2['4.4.4.1']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute2['4.4.4.1']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 143.0.0.1/32 and its next-hops. The next-hops via IP addresses
    # interfaces 1 and 4  should be reprogrammed into FIB.
    ExpRouteDictIpv4StaticRoute2 = ExpRibDictIpv4StaticRoute2

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 163.0.0.1/32 and its next-hops. The next-hops of the route should
    # be maintained in the RIB.
    ExpRibDictIpv4StaticRoute3 = dict()
    ExpRibDictIpv4StaticRoute3['Route'] = '163.0.0.1' + '/' + '32'
    ExpRibDictIpv4StaticRoute3['NumberNexthops'] = '1'
    ExpRibDictIpv4StaticRoute3['2'] = dict()
    ExpRibDictIpv4StaticRoute3['2']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute3['2']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute3['2']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 163.0.0.1/32 and its next-hops. The next-hops via IP addresses
    # interfaces 1 and 4  should be reprogrammed into FIB.
    ExpRouteDictIpv4StaticRoute3 = ExpRibDictIpv4StaticRoute3

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 1234:1234::1/128 and its next-hops. The next-hops of the route should
    # be maintained in the RIB.
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
    # route 1234:1234::1/128 and its next-hops. The next-hops via IPv6
    # addresses interfaces 1 and 4  should be reprogrammed into FIB.
    ExpRouteDictIpv6StaticRoute1 = ExpRibDictIpv6StaticRoute1

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 2234:2234::1/128 and its next-hops. The next-hops of the route should
    # be maintained in the RIB.
    ExpRibDictIpv6StaticRoute2 = dict()
    ExpRibDictIpv6StaticRoute2['Route'] = '2234:2234::1' + '/' + '128'
    ExpRibDictIpv6StaticRoute2['NumberNexthops'] = '1'
    ExpRibDictIpv6StaticRoute2['4'] = dict()
    ExpRibDictIpv6StaticRoute2['4']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute2['4']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute2['4']['RouteType'] = 'static'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 2234:2234::1/128 and its next-hops. The next-hops via IPv6
    # addresses interfaces 1 and 4  should be reprogrammed into FIB.
    ExpRouteDictIpv6StaticRoute2 = ExpRibDictIpv6StaticRoute2

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 3234:3234::1/128 and its next-hops. The next-hops of the route should
    # be maintained in the RIB.
    ExpRibDictIpv6StaticRoute3 = dict()
    ExpRibDictIpv6StaticRoute3['Route'] = '3234:3234::1' + '/' + '128'
    ExpRibDictIpv6StaticRoute3['NumberNexthops'] = '1'
    ExpRibDictIpv6StaticRoute3['2'] = dict()
    ExpRibDictIpv6StaticRoute3['2']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute3['2']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute3['2']['RouteType'] = 'static'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 3234:3234::1/128 and its next-hops. The next-hops via IPv6
    # addresses interfaces 1 and 4  should be reprogrammed into FIB.
    ExpRouteDictIpv6StaticRoute3 = ExpRibDictIpv6StaticRoute3

    LogOutput('info', "\n\n\n######### Verifying the IPv4 static routes on "
              "switch 1 after configuring interface addresses "
              "triggers#########")

    # Verify route 123.0.0.1/32 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute1,
                             'static')

    # Verify route 143.0.0.1/32 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute2,
                             'static')

    # Verify route 163.0.0.1/32 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute3, 'static')

    LogOutput('info', "\n\n\n######### Verifying the IPv6 static routes on "
              "switch 1 after configuring interface addresses "
              "triggers#########")

    # Verify route 1234:1234::1/128 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute1, 'static')

    # Verify route 2234:2234::1/128 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute2,
                               'static')

    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute2, 'static')

    # Verify route 3234:3234::1/128 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute3, 'static')

    LogOutput('info', "\n\n\n######### Verification of IPv4 and IPv6 static "
              "routes on switch 1 after configuring interface addresses "
              "passed#########")


# This test changes the interface addresses and checks if the static
# routes and next-hops show correctly in the output of
# "show ip/ipv6 route/show rib".
def interface_changing_addresses_trigger_static_routes(**kwargs):

    switch1 = kwargs.get('switch1', None)
    switch2 = kwargs.get('switch2', None)

    switch1.commandErrorCheck = 0
    switch2.commandErrorCheck = 0

    LogOutput('info', "Entering interface for link 1 SW1, changing an "
              "ip/ip6 address")

    # Changing the IP address on interface 1
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk01'],
                                  addr="8.8.8.8", mask=24, config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to change an ipv4 address"

    # Changing the IPv6 address on interface 1
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk01'],
                                  addr="888:888::8", mask=64, ipv6flag=True,
                                  config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to change an ipv6 address"

    LogOutput('info', "Entering interface for link 4 SW1, changing an "
              "ip/ip6 address")

    # Changing the IP address on interface 4
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk04'],
                                  addr="6.6.6.6", mask=24, config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to changing a ipv4 address"

    # Changing the IPv6 address on interface 4
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk04'],
                                  addr="666:666::6", mask=64, ipv6flag=True,
                                  config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to changing a ipv6 address"

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 123.0.0.1/32 and its next-hops. All four next-hops of the route should
    # be maintained in the RIB.
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
    # route 123.0.0.1/32 and its next-hops. The next-hops via IP addresses,
    # if the next-hops do not occur in subnets on interfaces 1 and 4,
    # should be withdrawn from FIB.
    ExpRouteDictIpv4StaticRoute1 = dict()
    ExpRouteDictIpv4StaticRoute1['Route'] = '123.0.0.1' + '/' + '32'
    ExpRouteDictIpv4StaticRoute1['NumberNexthops'] = '3'
    ExpRouteDictIpv4StaticRoute1['2'] = dict()
    ExpRouteDictIpv4StaticRoute1['2']['Distance'] = '1'
    ExpRouteDictIpv4StaticRoute1['2']['Metric'] = '0'
    ExpRouteDictIpv4StaticRoute1['2']['RouteType'] = 'static'
    ExpRouteDictIpv4StaticRoute1['3'] = dict()
    ExpRouteDictIpv4StaticRoute1['3']['Distance'] = '1'
    ExpRouteDictIpv4StaticRoute1['3']['Metric'] = '0'
    ExpRouteDictIpv4StaticRoute1['3']['RouteType'] = 'static'
    ExpRouteDictIpv4StaticRoute1['5.5.5.1'] = dict()
    ExpRouteDictIpv4StaticRoute1['5.5.5.1']['Distance'] = '1'
    ExpRouteDictIpv4StaticRoute1['5.5.5.1']['Metric'] = '0'
    ExpRouteDictIpv4StaticRoute1['5.5.5.1']['RouteType'] = 'static'

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 143.0.0.1/32 and its next-hops. All four next-hops of the route should
    # be maintained in the RIB.
    ExpRibDictIpv4StaticRoute2 = dict()
    ExpRibDictIpv4StaticRoute2['Route'] = '143.0.0.1' + '/' + '32'
    ExpRibDictIpv4StaticRoute2['NumberNexthops'] = '1'
    ExpRibDictIpv4StaticRoute2['4.4.4.1'] = dict()
    ExpRibDictIpv4StaticRoute2['4.4.4.1']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute2['4.4.4.1']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute2['4.4.4.1']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 143.0.0.1/32 and its next-hops. The next-hops via IP addresses,
    # if the next-hops do not occur in subnets on interfaces 1 and 4,
    # should be withdrawn from FIB.
    ExpRouteDictIpv4StaticRoute2 = dict()
    ExpRouteDictIpv4StaticRoute2['Route'] = '143.0.0.1' + '/' + '32'

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 163.0.0.1/32 and its next-hops. All four next-hops of the route should
    # be maintained in the RIB.
    ExpRibDictIpv4StaticRoute3 = dict()
    ExpRibDictIpv4StaticRoute3['Route'] = '163.0.0.1' + '/' + '32'
    ExpRibDictIpv4StaticRoute3['NumberNexthops'] = '1'
    ExpRibDictIpv4StaticRoute3['2'] = dict()
    ExpRibDictIpv4StaticRoute3['2']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute3['2']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute3['2']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 163.0.0.1/32 and its next-hops. The next-hops via IP addresses,
    # if the next-hops do not occur in subnets on interfaces 1 and 4,
    # should be withdrawn from FIB.
    ExpRouteDictIpv4StaticRoute3 = ExpRibDictIpv4StaticRoute3

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 1234:1234::1/128 and its next-hops. All four next-hops of the route
    # should be maintained in the RIB.
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

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 1234:1234::1/128  and its next-hops. The next-hops via IPv6
    # addresses, if the next-hops do not occur in subnets on interfaces 1
    # and 4, should be withdrawn from FIB.
    ExpRouteDictIpv6StaticRoute1 = ExpRibDictIpv6StaticRoute1

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 2234:2234::1/128 and its next-hops. All four next-hops of the route
    # should be maintained in the RIB.
    ExpRibDictIpv6StaticRoute2 = dict()
    ExpRibDictIpv6StaticRoute2['Route'] = '2234:2234::1' + '/' + '128'
    ExpRibDictIpv6StaticRoute2['NumberNexthops'] = '1'
    ExpRibDictIpv6StaticRoute2['4'] = dict()
    ExpRibDictIpv6StaticRoute2['4']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute2['4']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute2['4']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 2234:2234::1/128  and its next-hops. The next-hops via IPv6
    # addresses, if the next-hops do not occur in subnets on interfaces 1
    # and 4, should be withdrawn from FIB.
    ExpRouteDictIpv6StaticRoute2 = ExpRibDictIpv6StaticRoute2

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 3234:3234::1/128 and its next-hops. All four next-hops of the route
    # should be maintained in the RIB.
    ExpRibDictIpv6StaticRoute3 = dict()
    ExpRibDictIpv6StaticRoute3['Route'] = '3234:3234::1' + '/' + '128'
    ExpRibDictIpv6StaticRoute3['NumberNexthops'] = '1'
    ExpRibDictIpv6StaticRoute3['2'] = dict()
    ExpRibDictIpv6StaticRoute3['2']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute3['2']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute3['2']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 3234:3234::1/128  and its next-hops. The next-hops via IPv6
    # addresses, if the next-hops do not occur in subnets on interfaces 1
    # and 4, should be withdrawn from FIB.
    ExpRouteDictIpv6StaticRoute3 = ExpRibDictIpv6StaticRoute3

    LogOutput('info', "\n\n\n######### Verifying the IPv4 static routes on "
              "switch 1 after changing interface addresses triggers#########")

    # Verify route 123.0.0.1/32 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute1, 'static')

    # Verify route 143.0.0.1/32 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute2, 'static')

    # Verify route 163.0.0.1/32 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute3, 'static')

    LogOutput('info', "\n\n\n######### Verifying the IPv6 static routes on "
              "switch 1 after changing interface addresses triggers#########")

    # Verify route 1234:1234::1/128 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute1, 'static')

    # Verify route 2234:2234::1/128 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute2, 'static')

    # Verify route 3234:3234::1/128 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute3, 'static')

    LogOutput('info', "\n\n\n######### Verification of IPv4 and IPv6 static "
              "routes on switch 1 after changing interface addresses passed"
              "#########")


# This test changes the interface addresses back to the original addresses
# and checks if the static routes and next-hops show correctly in the output
# of "show ip/ipv6 route/show rib".
def interface_changing_back_addresses_trigger_static_routes(**kwargs):

    switch1 = kwargs.get('switch1', None)
    switch2 = kwargs.get('switch2', None)

    switch1.commandErrorCheck = 0
    switch2.commandErrorCheck = 0

    LogOutput('info', "Entering interface for link 1 SW1, changing back an "
              "ip/ip6 address")

    # Changing back the IP address on interface 1
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk01'],
                                  addr="1.1.1.1", mask=24, config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to change back an ipv4 address"

    # Changing back the IPv6 address on interface 1
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk01'],
                                  addr="111:111::1", mask=64, ipv6flag=True,
                                  config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to change back an ipv6 address"

    LogOutput('info', "Entering interface for link 4 SW1, changing back an "
              "ip/ip6 address")

    # Changing back the IP address on interface 4
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk04'],
                                  addr="4.4.4.4", mask=24, config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to changing back a ipv4 address"

    # Changing back the IPv6 address on interface 4
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk04'],
                                  addr="444:444::4", mask=64, ipv6flag=True,
                                  config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to changing back a ipv6 address"

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 123.0.0.1/32 and its next-hops. All four next-hops of the route should
    # be maintained in the RIB.
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
    # route 123.0.0.1/32 and its next-hops. The next-hops via IP addresses,
    # if the next-hops occur in subnets on interfaces 1 and 4, should be
    # reprogrammed in FIB.
    ExpRouteDictIpv4StaticRoute1 = ExpRibDictIpv4StaticRoute1

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 143.0.0.1/32 and its next-hops. All four next-hops of the route should
    # be maintained in the RIB.
    ExpRibDictIpv4StaticRoute2 = dict()
    ExpRibDictIpv4StaticRoute2['Route'] = '143.0.0.1' + '/' + '32'
    ExpRibDictIpv4StaticRoute2['NumberNexthops'] = '1'
    ExpRibDictIpv4StaticRoute2['4.4.4.1'] = dict()
    ExpRibDictIpv4StaticRoute2['4.4.4.1']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute2['4.4.4.1']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute2['4.4.4.1']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 143.0.0.1/32 and its next-hops. The next-hops via IP addresses,
    # if the next-hops occur in subnets on interfaces 1 and 4, should be
    # reprogrammed in FIB.
    ExpRouteDictIpv4StaticRoute2 = ExpRibDictIpv4StaticRoute2

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 163.0.0.1/32 and its next-hops. All four next-hops of the route should
    # be maintained in the RIB.
    ExpRibDictIpv4StaticRoute3 = dict()
    ExpRibDictIpv4StaticRoute3['Route'] = '163.0.0.1' + '/' + '32'
    ExpRibDictIpv4StaticRoute3['NumberNexthops'] = '1'
    ExpRibDictIpv4StaticRoute3['2'] = dict()
    ExpRibDictIpv4StaticRoute3['2']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute3['2']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute3['2']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 163.0.0.1/32 and its next-hops. The next-hops via IP addresses,
    # if the next-hops occur in subnets on interfaces 1 and 4, should be
    # reprogrammed in FIB.
    ExpRouteDictIpv4StaticRoute3 = ExpRibDictIpv4StaticRoute3

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 1234:1234::1/128 and its next-hops. All four next-hops of the route
    # should be maintained in the RIB.
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
    # route 1234:1234::1/128 and its next-hops. The next-hops via IPv6
    # addresses, if the next-hops occur in subnets on interfaces 1 and 4,
    # should be reprogrammed in FIB.
    ExpRouteDictIpv6StaticRoute1 = ExpRibDictIpv6StaticRoute1

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 2234:2234::1/128 and its next-hops. All four next-hops of the route
    # should be maintained in the RIB.
    ExpRibDictIpv6StaticRoute2 = dict()
    ExpRibDictIpv6StaticRoute2['Route'] = '2234:2234::1' + '/' + '128'
    ExpRibDictIpv6StaticRoute2['NumberNexthops'] = '1'
    ExpRibDictIpv6StaticRoute2['4'] = dict()
    ExpRibDictIpv6StaticRoute2['4']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute2['4']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute2['4']['RouteType'] = 'static'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 2234:2234::1/128 and its next-hops. The next-hops via IPv6
    # addresses, if the next-hops occur in subnets on interfaces 1 and 4,
    # should be reprogrammed in FIB.
    ExpRouteDictIpv6StaticRoute2 = ExpRibDictIpv6StaticRoute2

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 3234:3234::1/128 and its next-hops. All four next-hops of the route
    # should be maintained in the RIB.
    ExpRibDictIpv6StaticRoute3 = dict()
    ExpRibDictIpv6StaticRoute3['Route'] = '3234:3234::1' + '/' + '128'
    ExpRibDictIpv6StaticRoute3['NumberNexthops'] = '1'
    ExpRibDictIpv6StaticRoute3['2'] = dict()
    ExpRibDictIpv6StaticRoute3['2']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute3['2']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute3['2']['RouteType'] = 'static'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 3234:3234::1/128 and its next-hops. The next-hops via IPv6
    # addresses, if the next-hops occur in subnets on interfaces 1 and 4,
    # should be reprogrammed in FIB.
    ExpRouteDictIpv6StaticRoute3 = ExpRibDictIpv6StaticRoute3

    LogOutput('info', "\n\n\n######### Verifying the IPv4 static routes on "
              "switch 1 after changing back interface addresses triggers"
              "#########")

    # Verify route 123.0.0.1/32 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute1, 'static')

    # Verify route 143.0.0.1/32 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute2, 'static')

    # Verify route 163.0.0.1/32 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute3, 'static')

    LogOutput('info', "\n\n\n######### Verifying the IPv6 static routes on "
              "switch 1 after changing back interface addresses triggers"
              "#########")

    # Verify route 1234:1234::1/128 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute1, 'static')

    # Verify route 2234:2234::1/128 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute2, 'static')

    # Verify route 3234:3234::1/128 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute3, 'static')

    LogOutput('info', "\n\n\n######### Verification of IPv4 and IPv6 static "
              "routes on switch 1 after changing back interface addresses "
              "passed#########")


# This test case adds an inactive next-hop to a route whose next-hop
# is in FIB. The new next-hop should not appear in the output of
# "show ip route" but should appear in "show rib" output.
def add_inactive_nexthop_to_static_routes(**kwargs):

    switch1 = kwargs.get('switch1', None)
    switch2 = kwargs.get('switch2', None)

    switch1.commandErrorCheck = 0
    switch2.commandErrorCheck = 0

    # Shutting interface 4 on switch1
    LogOutput('info', "shutting interface4 on SW1")
    retStruct = InterfaceEnable(deviceObj=switch1, enable=False,
                                interface=switch1.linkPortMapping['lnk04'])
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Unable to disable interafce 4 on SW1"

    # Add nexthop 4.4.4.7 to route 163.0.0.1/32
    retStruct = IpRouteConfig(deviceObj=switch1, route="163.0.0.1", mask=32,
                              nexthop="4.4.4.7", config=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv4 route"

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 163.0.0.1/32 and its next-hops.
    ExpRibDictIpv4StaticRoute = dict()
    ExpRibDictIpv4StaticRoute['Route'] = '163.0.0.1' + '/' + '32'
    ExpRibDictIpv4StaticRoute['NumberNexthops'] = '2'
    ExpRibDictIpv4StaticRoute['2'] = dict()
    ExpRibDictIpv4StaticRoute['2']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute['2']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute['2']['RouteType'] = 'static'
    ExpRibDictIpv4StaticRoute['4.4.4.7'] = dict()
    ExpRibDictIpv4StaticRoute['4.4.4.7']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute['4.4.4.7']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute['4.4.4.7']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 163.0.0.1/32 and its next-hops.
    ExpRouteDictIpv4StaticRoute = dict()
    ExpRouteDictIpv4StaticRoute['Route'] = '163.0.0.1' + '/' + '32'
    ExpRouteDictIpv4StaticRoute['NumberNexthops'] = '1'
    ExpRouteDictIpv4StaticRoute['2'] = dict()
    ExpRouteDictIpv4StaticRoute['2']['Distance'] = '1'
    ExpRouteDictIpv4StaticRoute['2']['Metric'] = '0'
    ExpRouteDictIpv4StaticRoute['2']['RouteType'] = 'static'

    # Configure IPv6 route 3234:3234::1/128 with interface 4 as next-hop
    retStruct = IpRouteConfig(deviceObj=switch1, route="3234:3234::1",
                              mask=128, nexthop="4", config=True,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv6 route"

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 3234:3234::1/128 and its next-hops.
    ExpRibDictIpv6StaticRoute = dict()
    ExpRibDictIpv6StaticRoute['Route'] = '3234:3234::1' + '/' + '128'
    ExpRibDictIpv6StaticRoute['NumberNexthops'] = '2'
    ExpRibDictIpv6StaticRoute['2'] = dict()
    ExpRibDictIpv6StaticRoute['2']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute['2']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute['2']['RouteType'] = 'static'
    ExpRibDictIpv6StaticRoute['4'] = dict()
    ExpRibDictIpv6StaticRoute['4']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute['4']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute['4']['RouteType'] = 'static'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 3234:3234::1/128 and its next-hops.
    ExpRouteDictIpv6StaticRoute = dict()
    ExpRouteDictIpv6StaticRoute['Route'] = '3234:3234::1' + '/' + '128'
    ExpRouteDictIpv6StaticRoute['NumberNexthops'] = '1'
    ExpRouteDictIpv6StaticRoute['2'] = dict()
    ExpRouteDictIpv6StaticRoute['2']['Distance'] = '1'
    ExpRouteDictIpv6StaticRoute['2']['Metric'] = '0'
    ExpRouteDictIpv6StaticRoute['2']['RouteType'] = 'static'

    # Verify route 163.0.0.1/32 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute, 'static')

    LogOutput('info', "\n\n\n######### Verification of route 163.0.0.1/32 "
              "after adding inactive next-hop passed #########")

    # Verify route 3234:3234::1/128 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute, 'static')

    LogOutput('info', "\n\n\n######### Verification of route 3234:3234::1/128 "
              "after adding inactive next-hop passed #########")


# This test case removes an active next-hop from a route which already
# has another inactive next-hop. The route should not exist in the output
# of "show ip route" but should appear in "show rib" output.
def remove_active_nexthop_from_static_routes(**kwargs):

    switch1 = kwargs.get('switch1', None)
    switch2 = kwargs.get('switch2', None)

    switch1.commandErrorCheck = 0
    switch2.commandErrorCheck = 0

    # Remove nexthop interface 2 from route 163.0.0.1/32
    retStruct = IpRouteConfig(deviceObj=switch1, route="163.0.0.1", mask=32,
                              nexthop="2", config=False)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv4 route"

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 163.0.0.1/32 and its next-hops.
    ExpRibDictIpv4StaticRoute = dict()
    ExpRibDictIpv4StaticRoute['Route'] = '163.0.0.1' + '/' + '32'
    ExpRibDictIpv4StaticRoute['NumberNexthops'] = '1'
    ExpRibDictIpv4StaticRoute['4.4.4.7'] = dict()
    ExpRibDictIpv4StaticRoute['4.4.4.7']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute['4.4.4.7']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute['4.4.4.7']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 163.0.0.1/32 and its next-hops. The next-hop for the route
    # should be withdrawn from the FIB.
    ExpRouteDictIpv4StaticRoute = dict()
    ExpRouteDictIpv4StaticRoute['Route'] = '163.0.0.1' + '/' + '32'

    # Un-Configure IPv6 route 3234:3234::1/128 with interface 2 as next-hop
    retStruct = IpRouteConfig(deviceObj=switch1, route="3234:3234::1",
                              mask=128, nexthop="2", config=False,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv6 route"

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 3234:3234::1/128 and its next-hops.
    ExpRibDictIpv6StaticRoute = dict()
    ExpRibDictIpv6StaticRoute['Route'] = '3234:3234::1' + '/' + '128'
    ExpRibDictIpv6StaticRoute['NumberNexthops'] = '1'
    ExpRibDictIpv6StaticRoute['4'] = dict()
    ExpRibDictIpv6StaticRoute['4']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute['4']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute['4']['RouteType'] = 'static'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 3234:3234::1/128 and its next-hops. The next-hop for the route
    # should be withdrawn from the FIB.
    ExpRouteDictIpv6StaticRoute = dict()
    ExpRouteDictIpv6StaticRoute['Route'] = '3234:3234::1' + '/' + '128'

    # Verify route 163.0.0.1/32 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute, 'static')

    LogOutput('info', "\n\n\n######### Verification of route 163.0.0.1/32 "
              "after removing active next-hop passed #########")

    # Verify route 3234:3234::1/128 and next-hops in RIB and FIB
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute, 'static')

    LogOutput('info', "\n\n\n######### Verification of route 3234:3234::1/128 "
              "after adding inactive next-hop passed #########")


# Set the maximum timeout for all the test cases
# @pytest.mark.timeout(5000)


# Test class for testing "no shutdown"/"shutdown" triggers on static routes
# cleanup from RIB/FIB.
@pytest.mark.skipif(True, reason="Skipping old tests")
class Test_ecmp_interface_up_down_events:
    def setup_class(cls):
        # Test object will parse command line and formulate the env
        Test_ecmp_interface_up_down_events.testObj = testEnviron(
                                                topoDict=topoDict,
                                                defSwitchContext="vtyShell")
        # Get topology object
        Test_ecmp_interface_up_down_events.topoObj = Test_ecmp_interface_up_down_events.testObj.topoObjGet()

    def teardown_class(cls):
        Test_ecmp_interface_up_down_events.topoObj.terminate_nodes()

    def test_configure_static_routes(self):
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        dut02Obj = self.topoObj.deviceObjGet(device="dut02")
        configure_static_routes(switch1=dut01Obj, switch2=dut02Obj)

    def test_interface_shut_trigger_static_routes(self):
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        dut02Obj = self.topoObj.deviceObjGet(device="dut02")
        interface_shut_trigger_static_routes(switch1=dut01Obj,
                                             switch2=dut02Obj)

    def test_interface_no_shut_trigger_static_routes(self):
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        dut02Obj = self.topoObj.deviceObjGet(device="dut02")
        interface_no_shut_trigger_static_routes(switch1=dut01Obj,
                                                switch2=dut02Obj)

    def test_interface_unconfiguring_addresses_trigger_static_routes(self):
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        dut02Obj = self.topoObj.deviceObjGet(device="dut02")
        interface_unconfiguring_addresses_trigger_static_routes(switch1=dut01Obj, switch2=dut02Obj)

    def test_interface_configuring_addresses_trigger_static_routes(self):
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        dut02Obj = self.topoObj.deviceObjGet(device="dut02")
        interface_configuring_addresses_trigger_static_routes(switch1=dut01Obj, switch2=dut02Obj)

    def test_interface_changing_addresses_trigger_static_routes(self):
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        dut02Obj = self.topoObj.deviceObjGet(device="dut02")
        interface_changing_addresses_trigger_static_routes(switch1=dut01Obj, switch2=dut02Obj)

    def test_interface_changing_back_addresses_trigger_static_routes(self):
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        dut02Obj = self.topoObj.deviceObjGet(device="dut02")
        interface_changing_back_addresses_trigger_static_routes(switch1=dut01Obj, switch2=dut02Obj)

    def test_add_inactive_nexthop_to_static_routes(self):
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        dut02Obj = self.topoObj.deviceObjGet(device="dut02")
        add_inactive_nexthop_to_static_routes(switch1=dut01Obj, switch2=dut02Obj)

    def test_remove_active_nexthop_from_static_routes(self):
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        dut02Obj = self.topoObj.deviceObjGet(device="dut02")
        remove_active_nexthop_from_static_routes(switch1=dut01Obj, switch2=dut02Obj)
