
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
import time
from opstestfw import *
from opstestfw.switch.CLI import *
from opstestfw.switch.OVS import *
from IpKernelRouteShow import *


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
# "show ip route/show rib".
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
                              nexthop="4.4.4.1", config=True)
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
    ExpRibDictIpv4StaticRoute1['4.4.4.1'] = dict()
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 123.0.0.1/32 and its next-hops.
    ExpRouteDictIpv4StaticRoute1 = ExpRibDictIpv4StaticRoute1

    # Populate the version of the route in kernel in the route dictionary
    # for the route 123.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute1 = dict()
    ExpDictIpv4KernelRoute1['Route'] = '123.0.0.1' + '/' + '32'
    ExpDictIpv4KernelRoute1['NumberNexthops'] = '4'
    ExpDictIpv4KernelRoute1['1.1.1.2'] = dict()
    ExpDictIpv4KernelRoute1['1.1.1.2']['Distance'] = ''
    ExpDictIpv4KernelRoute1['1.1.1.2']['Metric'] = ''
    ExpDictIpv4KernelRoute1['1.1.1.2']['RouteType'] = 'zebra'
    ExpDictIpv4KernelRoute1['2'] = dict()
    ExpDictIpv4KernelRoute1['2']['Distance'] = ''
    ExpDictIpv4KernelRoute1['2']['Metric'] = ''
    ExpDictIpv4KernelRoute1['2']['RouteType'] = 'zebra'
    ExpDictIpv4KernelRoute1['3'] = dict()
    ExpDictIpv4KernelRoute1['3']['Distance'] = ''
    ExpDictIpv4KernelRoute1['3']['Metric'] = ''
    ExpDictIpv4KernelRoute1['3']['RouteType'] = 'zebra'
    ExpDictIpv4KernelRoute1['4.4.4.1'] = dict()
    ExpDictIpv4KernelRoute1['4.4.4.1']['Distance'] = ''
    ExpDictIpv4KernelRoute1['4.4.4.1']['Metric'] = ''
    ExpDictIpv4KernelRoute1['4.4.4.1']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 143.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute2 = dict()
    ExpDictIpv4KernelRoute2['Route'] = '143.0.0.1' + '/' + '32'
    ExpDictIpv4KernelRoute2['NumberNexthops'] = '1'
    ExpDictIpv4KernelRoute2['4.4.4.1'] = dict()
    ExpDictIpv4KernelRoute2['4.4.4.1']['Distance'] = ''
    ExpDictIpv4KernelRoute2['4.4.4.1']['Metric'] = ''
    ExpDictIpv4KernelRoute2['4.4.4.1']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 163.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute3 = dict()
    ExpDictIpv4KernelRoute3['Route'] = '163.0.0.1' + '/' + '32'
    ExpDictIpv4KernelRoute3['NumberNexthops'] = '1'
    ExpDictIpv4KernelRoute3['2'] = dict()
    ExpDictIpv4KernelRoute3['2']['Distance'] = ''
    ExpDictIpv4KernelRoute3['2']['Metric'] = ''
    ExpDictIpv4KernelRoute3['2']['RouteType'] = 'zebra'

    LogOutput('info', "\n\n\n######### Configuring switch 1 IPv6 static "
              "routes #########")

    # Configure IPv6 route a234:a234::1/128 with 4 ECMP next-hops.
    retStruct = IpRouteConfig(deviceObj=switch1, route="a234:a234::1",
                              mask=128, nexthop="1", config=True,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv6 route"

    retStruct = IpRouteConfig(deviceObj=switch1, route="a234:a234::1",
                              mask=128, nexthop="2", config=True,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv6 route"

    retStruct = IpRouteConfig(deviceObj=switch1, route="a234:a234::1",
                              mask=128, nexthop="3", config=True,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv6 route"

    retStruct = IpRouteConfig(deviceObj=switch1, route="a234:a234::1",
                              mask=128, nexthop="4", config=True,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv6 route"

    # Populate the expected RIB ("show rib") route dictionary for the
    # route a234:a234::1/128 and its next-hops.
    ExpRibDictIpv6StaticRoute1 = dict()
    ExpRibDictIpv6StaticRoute1['Route'] = 'a234:a234::1' + '/' + '128'
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
    # route a234:a234::1/128 and its next-hops.
    ExpRouteDictIpv6StaticRoute1 = ExpRibDictIpv6StaticRoute1

    # Populate the version of the route in kernel in the route dictionary
    # for the route a234:a234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute1 = dict()
    ExpDictIpv6KernelRoute1['Route'] = 'a234:a234::1' + '/' + '128'
    ExpDictIpv6KernelRoute1['NumberNexthops'] = '4'
    ExpDictIpv6KernelRoute1['1'] = dict()
    ExpDictIpv6KernelRoute1['1']['Distance'] = ''
    ExpDictIpv6KernelRoute1['1']['Metric'] = ''
    ExpDictIpv6KernelRoute1['1']['RouteType'] = 'zebra'
    ExpDictIpv6KernelRoute1['2'] = dict()
    ExpDictIpv6KernelRoute1['2']['Distance'] = ''
    ExpDictIpv6KernelRoute1['2']['Metric'] = ''
    ExpDictIpv6KernelRoute1['2']['RouteType'] = 'zebra'
    ExpDictIpv6KernelRoute1['3'] = dict()
    ExpDictIpv6KernelRoute1['3']['Distance'] = ''
    ExpDictIpv6KernelRoute1['3']['Metric'] = ''
    ExpDictIpv6KernelRoute1['3']['RouteType'] = 'zebra'
    ExpDictIpv6KernelRoute1['4'] = dict()
    ExpDictIpv6KernelRoute1['4']['Distance'] = ''
    ExpDictIpv6KernelRoute1['4']['Metric'] = ''
    ExpDictIpv6KernelRoute1['4']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 2234:2234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute2 = dict()
    ExpDictIpv6KernelRoute2['Route'] = '2234:2234::1' + '/' + '128'
    ExpDictIpv6KernelRoute2['NumberNexthops'] = '1'
    ExpDictIpv6KernelRoute2['4'] = dict()
    ExpDictIpv6KernelRoute2['4']['Distance'] = ''
    ExpDictIpv6KernelRoute2['4']['Metric'] = ''
    ExpDictIpv6KernelRoute2['4']['RouteType'] = 'zebra'

    # Configure IPv6 route 3234:3234::1/128 with 1 next-hop.
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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 3234:3234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute3 = dict()
    ExpDictIpv6KernelRoute3['Route'] = '3234:3234::1' + '/' + '128'
    ExpDictIpv6KernelRoute3['NumberNexthops'] = '1'
    ExpDictIpv6KernelRoute3['2'] = dict()
    ExpDictIpv6KernelRoute3['2']['Distance'] = ''
    ExpDictIpv6KernelRoute3['2']['Metric'] = ''
    ExpDictIpv6KernelRoute3['2']['RouteType'] = 'zebra'

    time.sleep(5)

    LogOutput('info', "\n\n\n######### Verifying the IPv4 static routes on "
              "switch 1#########")

    # Verify route 123.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute1, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute1, 'zebra')

    # Verify route 143.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute2, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute2, 'zebra')

    # Verify route 163.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute3, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute3, 'zebra')

    LogOutput('info', "\n\n\n######### Verifying the IPv6 static routes on "
              "switch 1#########")

    # Verify route a234:a234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute1, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute1, 'zebra')

    # Verify route 2234:2234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute2, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute2, 'zebra')

    # Verify route 3234:3234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute3, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute3, 'zebra')

    LogOutput('info', "\n\n\n######### Configuration and verification of "
              "IPv4 and IPv6 static routes on switch 1 passed#########")


# This test restarts zebra process and checks if the routes and next-hops show
# correctly in the output of "show ip route/show rib" after zebra has restarted.
# There is no configuration change when zebra is not running.
def restart_zebra_without_config_change(**kwargs):

    switch1 = kwargs.get('switch1', None)
    switch2 = kwargs.get('switch2', None)

    switch1.commandErrorCheck = 0
    switch2.commandErrorCheck = 0

    zebra_stop_command_string = "systemctl stop ops-zebra"
    zebra_start_command_string = "systemctl start ops-zebra"

    LogOutput('info', "\n\n\n######### Restarting zebra without config changes on  "
              "switch 1#########")

    LogOutput('info', "\n\n\n######### Restarting zebra. Stopping ops-zebra service on"
              "switch 1#########")

    # Execute the command to stop zebra on the Linux bash interface
    devIntRetStruct = switch1.DeviceInteract(command=zebra_stop_command_string)
    retCode = devIntRetStruct.get('returnCode')

    if retCode != 0:
        assert "Failed to stop zebra"

    LogOutput('info', "\n\n\n######### Restarting zebra. Starting ops-zebra service on"
              "switch 1#########")

    # Execute the command to start zebra on the Linux bash interface
    devIntRetStruct = switch1.DeviceInteract(command=zebra_start_command_string)
    retCode = devIntRetStruct.get('returnCode')

    if retCode != 0:
        assert "Failed to start zebra"

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
    ExpRibDictIpv4StaticRoute1['4.4.4.1'] = dict()
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 123.0.0.1/32 and its next-hops.
    ExpRouteDictIpv4StaticRoute1 = ExpRibDictIpv4StaticRoute1

    # Populate the version of the route in kernel in the route dictionary
    # for the route 123.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute1 = dict()
    ExpDictIpv4KernelRoute1['Route'] = '123.0.0.1' + '/' + '32'
    ExpDictIpv4KernelRoute1['NumberNexthops'] = '4'
    ExpDictIpv4KernelRoute1['1.1.1.2'] = dict()
    ExpDictIpv4KernelRoute1['1.1.1.2']['Distance'] = ''
    ExpDictIpv4KernelRoute1['1.1.1.2']['Metric'] = ''
    ExpDictIpv4KernelRoute1['1.1.1.2']['RouteType'] = 'zebra'
    ExpDictIpv4KernelRoute1['2'] = dict()
    ExpDictIpv4KernelRoute1['2']['Distance'] = ''
    ExpDictIpv4KernelRoute1['2']['Metric'] = ''
    ExpDictIpv4KernelRoute1['2']['RouteType'] = 'zebra'
    ExpDictIpv4KernelRoute1['3'] = dict()
    ExpDictIpv4KernelRoute1['3']['Distance'] = ''
    ExpDictIpv4KernelRoute1['3']['Metric'] = ''
    ExpDictIpv4KernelRoute1['3']['RouteType'] = 'zebra'
    ExpDictIpv4KernelRoute1['4.4.4.1'] = dict()
    ExpDictIpv4KernelRoute1['4.4.4.1']['Distance'] = ''
    ExpDictIpv4KernelRoute1['4.4.4.1']['Metric'] = ''
    ExpDictIpv4KernelRoute1['4.4.4.1']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 143.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute2 = dict()
    ExpDictIpv4KernelRoute2['Route'] = '143.0.0.1' + '/' + '32'
    ExpDictIpv4KernelRoute2['NumberNexthops'] = '1'
    ExpDictIpv4KernelRoute2['4.4.4.1'] = dict()
    ExpDictIpv4KernelRoute2['4.4.4.1']['Distance'] = ''
    ExpDictIpv4KernelRoute2['4.4.4.1']['Metric'] = ''
    ExpDictIpv4KernelRoute2['4.4.4.1']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 163.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute3 = dict()
    ExpDictIpv4KernelRoute3['Route'] = '163.0.0.1' + '/' + '32'
    ExpDictIpv4KernelRoute3['NumberNexthops'] = '1'
    ExpDictIpv4KernelRoute3['2'] = dict()
    ExpDictIpv4KernelRoute3['2']['Distance'] = ''
    ExpDictIpv4KernelRoute3['2']['Metric'] = ''
    ExpDictIpv4KernelRoute3['2']['RouteType'] = 'zebra'

    # Populate the expected RIB ("show rib") route dictionary for the
    # route a234:a234::1/128 and its next-hops.
    ExpRibDictIpv6StaticRoute1 = dict()
    ExpRibDictIpv6StaticRoute1['Route'] = 'a234:a234::1' + '/' + '128'
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
    # route a234:a234::1/128 and its next-hops.
    ExpRouteDictIpv6StaticRoute1 = ExpRibDictIpv6StaticRoute1

    # Populate the version of the route in kernel in the route dictionary
    # for the route a234:a234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute1 = dict()
    ExpDictIpv6KernelRoute1['Route'] = 'a234:a234::1' + '/' + '128'
    ExpDictIpv6KernelRoute1['NumberNexthops'] = '4'
    ExpDictIpv6KernelRoute1['1'] = dict()
    ExpDictIpv6KernelRoute1['1']['Distance'] = ''
    ExpDictIpv6KernelRoute1['1']['Metric'] = ''
    ExpDictIpv6KernelRoute1['1']['RouteType'] = 'zebra'
    ExpDictIpv6KernelRoute1['2'] = dict()
    ExpDictIpv6KernelRoute1['2']['Distance'] = ''
    ExpDictIpv6KernelRoute1['2']['Metric'] = ''
    ExpDictIpv6KernelRoute1['2']['RouteType'] = 'zebra'
    ExpDictIpv6KernelRoute1['3'] = dict()
    ExpDictIpv6KernelRoute1['3']['Distance'] = ''
    ExpDictIpv6KernelRoute1['3']['Metric'] = ''
    ExpDictIpv6KernelRoute1['3']['RouteType'] = 'zebra'
    ExpDictIpv6KernelRoute1['4'] = dict()
    ExpDictIpv6KernelRoute1['4']['Distance'] = ''
    ExpDictIpv6KernelRoute1['4']['Metric'] = ''
    ExpDictIpv6KernelRoute1['4']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 2234:2234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute2 = dict()
    ExpDictIpv6KernelRoute2['Route'] = '2234:2234::1' + '/' + '128'
    ExpDictIpv6KernelRoute2['NumberNexthops'] = '1'
    ExpDictIpv6KernelRoute2['4'] = dict()
    ExpDictIpv6KernelRoute2['4']['Distance'] = ''
    ExpDictIpv6KernelRoute2['4']['Metric'] = ''
    ExpDictIpv6KernelRoute2['4']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 3234:3234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute3 = dict()
    ExpDictIpv6KernelRoute3['Route'] = '3234:3234::1' + '/' + '128'
    ExpDictIpv6KernelRoute3['NumberNexthops'] = '1'
    ExpDictIpv6KernelRoute3['2'] = dict()
    ExpDictIpv6KernelRoute3['2']['Distance'] = ''
    ExpDictIpv6KernelRoute3['2']['Metric'] = ''
    ExpDictIpv6KernelRoute3['2']['RouteType'] = 'zebra'

    time.sleep(5)

    LogOutput('info', "\n\n\n######### Verifying the IPv4 static routes on "
              "switch 1#########")

    # Verify route 123.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute1, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute1, 'zebra')

    # Verify route 143.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute2, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute2, 'zebra')

    # Verify route 163.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute3, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute3, 'zebra')

    LogOutput('info', "\n\n\n######### Verifying the IPv6 static routes on "
              "switch 1#########")

    # Verify route a234:a234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute1, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute1, 'zebra')

    # Verify route 2234:2234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute2, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute2, 'zebra')

    # Verify route 3234:3234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute3, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute3, 'zebra')

    LogOutput('info', "\n\n\n######### Verification of "
              "IPv4 and IPv6 static routes on switch 1 passed after "
              "restart#########")

    LogOutput('info', "\n\n\n######### Restarting zebra without config changes on  "
              "switch 1 passed#########")


# This test restarts zebra process and checks if the routes and next-hops show
# correctly in the output of "show ip route/show rib" after zebra has restarted.
# While zebra is not running,, we change the static route configuration by deleting
# some routes and adding some new routes.
def restart_zebra_with_config_change(**kwargs):

    switch1 = kwargs.get('switch1', None)
    switch2 = kwargs.get('switch2', None)

    switch1.commandErrorCheck = 0
    switch2.commandErrorCheck = 0

    zebra_stop_command_string = "systemctl stop ops-zebra"
    zebra_start_command_string = "systemctl start ops-zebra"

    LogOutput('info', "\n\n\n######### Restarting zebra with config changes on  "
              "switch 1#########")

    LogOutput('info', "\n\n\n######### Restarting zebra. Stopping ops-zebra service on"
              "switch 1#########")

    # Execute the command to stop zebra on the Linux bash interface
    devIntRetStruct = switch1.DeviceInteract(command=zebra_stop_command_string)
    retCode = devIntRetStruct.get('returnCode')

    if retCode != 0:
        assert "Failed to stop zebra"

    LogOutput('info', "\n\n\n######### Removing some static route configuration "
              " while zebra is not running on switch 1#########")

    # Un-configure IPv4 route 123.0.0.1/32 with next-hop 1.1.1.2
    retStruct = IpRouteConfig(deviceObj=switch1, route="123.0.0.1", mask=32,
                              nexthop="1.1.1.2", config=False)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv4 route"

    # Un-configure IPv4 route 123.0.0.1/32 with next-hop 2
    retStruct = IpRouteConfig(deviceObj=switch1, route="123.0.0.1", mask=32,
                              nexthop="2", config=False)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv4 route"

    # Un-configure IPv4 route 143.0.0.1/32 next-hop 4.4.4.1.
    retStruct = IpRouteConfig(deviceObj=switch1, route="143.0.0.1", mask=32,
                              nexthop="4.4.4.1", config=False)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv4 route"

    # Un-configure IPv6 route a234:a234::1/128 with next-hop 1.
    retStruct = IpRouteConfig(deviceObj=switch1, route="a234:a234::1",
                              mask=128, nexthop="1", config=False,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv6 route"

    # Un-configure IPv6 route a234:a234::1/128 with next-hop 2.
    retStruct = IpRouteConfig(deviceObj=switch1, route="a234:a234::1",
                              mask=128, nexthop="2", config=False,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv6 route"

    # un-configure IPv6 route 3234:3234::1/128 with next-hop 2.
    retStruct = IpRouteConfig(deviceObj=switch1, route="3234:3234::1",
                              mask=128, nexthop="2", config=False,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv6 route"

    LogOutput('info', "\n\n\n######### Adding some static route configuration "
              " while zebra is not running on switch 1#########")

    # Configure IPv4 route 173.0.0.1/32 with next-hop 1.1.1.2
    retStruct = IpRouteConfig(deviceObj=switch1, route="173.0.0.1", mask=32,
                              nexthop="1.1.1.2", config=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv4 route"

    # Configure IPv4 route 173.0.0.1/32 with next-hop 3
    retStruct = IpRouteConfig(deviceObj=switch1, route="173.0.0.1", mask=32,
                              nexthop="3", config=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv4 route"

    # Configure IPv4 route 183.0.0.1/32 next-hop 4.4.4.1.
    retStruct = IpRouteConfig(deviceObj=switch1, route="183.0.0.1", mask=32,
                              nexthop="4.4.4.1", config=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv4 route"

    # Configure IPv6 route 7234:7234::1/128 with next-hop 1.
    retStruct = IpRouteConfig(deviceObj=switch1, route="7234:7234::1",
                              mask=128, nexthop="1", config=True,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv6 route"

    # Configure IPv6 route 7234:7234::1/128 with next-hop 3.
    retStruct = IpRouteConfig(deviceObj=switch1, route="7234:7234::1",
                              mask=128, nexthop="3", config=True,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv6 route"

    # Configure IPv6 route 8234:8234::1/128 with next-hop 2.
    retStruct = IpRouteConfig(deviceObj=switch1, route="8234:8234::1",
                              mask=128, nexthop="2", config=True,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv6 route"

    LogOutput('info', "\n\n\n######### Restarting zebra. Starting ops-zebra service on"
              "switch 1#########")

    # Execute the command to start zebra on the Linux bash interface
    devIntRetStruct = switch1.DeviceInteract(command=zebra_start_command_string)
    retCode = devIntRetStruct.get('returnCode')

    if retCode != 0:
        assert "Failed to start zebra"

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 123.0.0.1/32 and its next-hops.
    ExpRibDictIpv4StaticRoute1 = dict()
    ExpRibDictIpv4StaticRoute1['Route'] = '123.0.0.1' + '/' + '32'
    ExpRibDictIpv4StaticRoute1['NumberNexthops'] = '2'
    ExpRibDictIpv4StaticRoute1['3'] = dict()
    ExpRibDictIpv4StaticRoute1['3']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute1['3']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute1['3']['RouteType'] = 'static'
    ExpRibDictIpv4StaticRoute1['4.4.4.1'] = dict()
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 123.0.0.1/32 and its next-hops.
    ExpRouteDictIpv4StaticRoute1 = ExpRibDictIpv4StaticRoute1

    # Populate the version of the route in kernel in the route dictionary
    # for the route 123.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute1 = dict()
    ExpDictIpv4KernelRoute1['Route'] = '123.0.0.1' + '/' + '32'
    ExpDictIpv4KernelRoute1['NumberNexthops'] = '2'
    ExpDictIpv4KernelRoute1['3'] = dict()
    ExpDictIpv4KernelRoute1['3']['Distance'] = ''
    ExpDictIpv4KernelRoute1['3']['Metric'] = ''
    ExpDictIpv4KernelRoute1['3']['RouteType'] = 'zebra'
    ExpDictIpv4KernelRoute1['4.4.4.1'] = dict()
    ExpDictIpv4KernelRoute1['4.4.4.1']['Distance'] = ''
    ExpDictIpv4KernelRoute1['4.4.4.1']['Metric'] = ''
    ExpDictIpv4KernelRoute1['4.4.4.1']['RouteType'] = 'zebra'

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 143.0.0.1/32 and its next-hops.
    ExpRibDictIpv4StaticRoute2 = dict()
    ExpRibDictIpv4StaticRoute2['Route'] = '143.0.0.1' + '/' + '32'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 143.0.0.1/32 and its next-hops.
    ExpRouteDictIpv4StaticRoute2 = ExpRibDictIpv4StaticRoute2

    # Populate the version of the route in kernel in the route dictionary
    # for the route 143.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute2 = dict()
    ExpDictIpv4KernelRoute2['Route'] = '143.0.0.1' + '/' + '32'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 163.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute3 = dict()
    ExpDictIpv4KernelRoute3['Route'] = '163.0.0.1' + '/' + '32'
    ExpDictIpv4KernelRoute3['NumberNexthops'] = '1'
    ExpDictIpv4KernelRoute3['2'] = dict()
    ExpDictIpv4KernelRoute3['2']['Distance'] = ''
    ExpDictIpv4KernelRoute3['2']['Metric'] = ''
    ExpDictIpv4KernelRoute3['2']['RouteType'] = 'zebra'

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 173.0.0.1/32 and its next-hops.
    ExpRibDictIpv4StaticRoute4 = dict()
    ExpRibDictIpv4StaticRoute4['Route'] = '173.0.0.1' + '/' + '32'
    ExpRibDictIpv4StaticRoute4['NumberNexthops'] = '2'
    ExpRibDictIpv4StaticRoute4['3'] = dict()
    ExpRibDictIpv4StaticRoute4['3']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute4['3']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute4['3']['RouteType'] = 'static'
    ExpRibDictIpv4StaticRoute4['1.1.1.2'] = dict()
    ExpRibDictIpv4StaticRoute4['1.1.1.2']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute4['1.1.1.2']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute4['1.1.1.2']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 173.0.0.1/32 and its next-hops.
    ExpRouteDictIpv4StaticRoute4 = ExpRibDictIpv4StaticRoute4

    # Populate the version of the route in kernel in the route dictionary
    # for the route 173.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute4 = dict()
    ExpDictIpv4KernelRoute4['Route'] = '173.0.0.1' + '/' + '32'
    ExpDictIpv4KernelRoute4['NumberNexthops'] = '2'
    ExpDictIpv4KernelRoute4['3'] = dict()
    ExpDictIpv4KernelRoute4['3']['Distance'] = ''
    ExpDictIpv4KernelRoute4['3']['Metric'] = ''
    ExpDictIpv4KernelRoute4['3']['RouteType'] = 'zebra'
    ExpDictIpv4KernelRoute4['1.1.1.2'] = dict()
    ExpDictIpv4KernelRoute4['1.1.1.2']['Distance'] = ''
    ExpDictIpv4KernelRoute4['1.1.1.2']['Metric'] = ''
    ExpDictIpv4KernelRoute4['1.1.1.2']['RouteType'] = 'zebra'

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 183.0.0.1/32 and its next-hops.
    ExpRibDictIpv4StaticRoute5 = dict()
    ExpRibDictIpv4StaticRoute5['Route'] = '183.0.0.1' + '/' + '32'
    ExpRibDictIpv4StaticRoute5['NumberNexthops'] = '1'
    ExpRibDictIpv4StaticRoute5['4.4.4.1'] = dict()
    ExpRibDictIpv4StaticRoute5['4.4.4.1']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute5['4.4.4.1']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute5['4.4.4.1']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 183.0.0.1/32 and its next-hops.
    ExpRouteDictIpv4StaticRoute5 = ExpRibDictIpv4StaticRoute5

    # Populate the version of the route in kernel in the route dictionary
    # for the route 183.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute5 = dict()
    ExpDictIpv4KernelRoute5['Route'] = '183.0.0.1' + '/' + '32'
    ExpDictIpv4KernelRoute5['NumberNexthops'] = '1'
    ExpDictIpv4KernelRoute5['4.4.4.1'] = dict()
    ExpDictIpv4KernelRoute5['4.4.4.1']['Distance'] = ''
    ExpDictIpv4KernelRoute5['4.4.4.1']['Metric'] = ''
    ExpDictIpv4KernelRoute5['4.4.4.1']['RouteType'] = 'zebra'

    # Populate the expected RIB ("show rib") route dictionary for the
    # route a234:a234::1/128 and its next-hops.
    ExpRibDictIpv6StaticRoute1 = dict()
    ExpRibDictIpv6StaticRoute1['Route'] = 'a234:a234::1' + '/' + '128'
    ExpRibDictIpv6StaticRoute1['NumberNexthops'] = '2'
    ExpRibDictIpv6StaticRoute1['3'] = dict()
    ExpRibDictIpv6StaticRoute1['3']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute1['3']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute1['3']['RouteType'] = 'static'
    ExpRibDictIpv6StaticRoute1['4'] = dict()
    ExpRibDictIpv6StaticRoute1['4']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute1['4']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute1['4']['RouteType'] = 'static'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route a234:a234::1/128 and its next-hops.
    ExpRouteDictIpv6StaticRoute1 = ExpRibDictIpv6StaticRoute1

    # Populate the version of the route in kernel in the route dictionary
    # for the route a234:a234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute1 = dict()
    ExpDictIpv6KernelRoute1['Route'] = 'a234:a234::1' + '/' + '128'
    ExpDictIpv6KernelRoute1['NumberNexthops'] = '2'
    ExpDictIpv6KernelRoute1['3'] = dict()
    ExpDictIpv6KernelRoute1['3']['Distance'] = ''
    ExpDictIpv6KernelRoute1['3']['Metric'] = ''
    ExpDictIpv6KernelRoute1['3']['RouteType'] = 'zebra'
    ExpDictIpv6KernelRoute1['4'] = dict()
    ExpDictIpv6KernelRoute1['4']['Distance'] = ''
    ExpDictIpv6KernelRoute1['4']['Metric'] = ''
    ExpDictIpv6KernelRoute1['4']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 2234:2234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute2 = dict()
    ExpDictIpv6KernelRoute2['Route'] = '2234:2234::1' + '/' + '128'
    ExpDictIpv6KernelRoute2['NumberNexthops'] = '1'
    ExpDictIpv6KernelRoute2['4'] = dict()
    ExpDictIpv6KernelRoute2['4']['Distance'] = ''
    ExpDictIpv6KernelRoute2['4']['Metric'] = ''
    ExpDictIpv6KernelRoute2['4']['RouteType'] = 'zebra'

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 3234:3234::1/128 and its next-hops.
    ExpRibDictIpv6StaticRoute3 = dict()
    ExpRibDictIpv6StaticRoute3['Route'] = '3234:3234::1' + '/' + '128'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 3234:3234::1/128 and its next-hops.
    ExpRouteDictIpv6StaticRoute3 = ExpRibDictIpv6StaticRoute3

    # Populate the version of the route in kernel in the route dictionary
    # for the route 3234:3234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute3 = dict()
    ExpDictIpv6KernelRoute3['Route'] = '3234:3234::1' + '/' + '128'

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 7234:7234::1/128 and its next-hops.
    ExpRibDictIpv6StaticRoute4 = dict()
    ExpRibDictIpv6StaticRoute4['Route'] = '7234:7234::1' + '/' + '128'
    ExpRibDictIpv6StaticRoute4['NumberNexthops'] = '2'
    ExpRibDictIpv6StaticRoute4['1'] = dict()
    ExpRibDictIpv6StaticRoute4['1']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute4['1']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute4['1']['RouteType'] = 'static'
    ExpRibDictIpv6StaticRoute4['3'] = dict()
    ExpRibDictIpv6StaticRoute4['3']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute4['3']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute4['3']['RouteType'] = 'static'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 7234:7234::1/128 and its next-hops.
    ExpRouteDictIpv6StaticRoute4 = ExpRibDictIpv6StaticRoute4

    # Populate the version of the route in kernel in the route dictionary
    # for the route 7234:7234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute4 = dict()
    ExpDictIpv6KernelRoute4['Route'] = '7234:7234::1' + '/' + '128'
    ExpDictIpv6KernelRoute4['NumberNexthops'] = '2'
    ExpDictIpv6KernelRoute4['1'] = dict()
    ExpDictIpv6KernelRoute4['1']['Distance'] = ''
    ExpDictIpv6KernelRoute4['1']['Metric'] = ''
    ExpDictIpv6KernelRoute4['1']['RouteType'] = 'zebra'
    ExpDictIpv6KernelRoute4['3'] = dict()
    ExpDictIpv6KernelRoute4['3']['Distance'] = ''
    ExpDictIpv6KernelRoute4['3']['Metric'] = ''
    ExpDictIpv6KernelRoute4['3']['RouteType'] = 'zebra'

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 8234:8234::1/128 and its next-hops.
    ExpRibDictIpv6StaticRoute5 = dict()
    ExpRibDictIpv6StaticRoute5['Route'] = '8234:8234::1' + '/' + '128'
    ExpRibDictIpv6StaticRoute5['NumberNexthops'] = '1'
    ExpRibDictIpv6StaticRoute5['2'] = dict()
    ExpRibDictIpv6StaticRoute5['2']['Distance'] = '1'
    ExpRibDictIpv6StaticRoute5['2']['Metric'] = '0'
    ExpRibDictIpv6StaticRoute5['2']['RouteType'] = 'static'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 8234:8234::1/128 and its next-hops.
    ExpRouteDictIpv6StaticRoute5 = ExpRibDictIpv6StaticRoute5

    # Populate the version of the route in kernel in the route dictionary
    # for the route 8234:8234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute5 = dict()
    ExpDictIpv6KernelRoute5['Route'] = '8234:8234::1' + '/' + '128'
    ExpDictIpv6KernelRoute5['NumberNexthops'] = '1'
    ExpDictIpv6KernelRoute5['2'] = dict()
    ExpDictIpv6KernelRoute5['2']['Distance'] = ''
    ExpDictIpv6KernelRoute5['2']['Metric'] = ''
    ExpDictIpv6KernelRoute5['2']['RouteType'] = 'zebra'

    time.sleep(5)

    LogOutput('info', "\n\n\n######### Verifying the IPv4 static routes on "
              "switch 1#########")

    # Verify route 123.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute1, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute1, 'zebra')

    # Verify route 143.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute2, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute2, 'zebra')

    # Verify route 163.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute3, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute3, 'zebra')

    # Verify route 173.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute4,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute4, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute4, 'zebra')

    # Verify route 183.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute5,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute5, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute5, 'zebra')

    LogOutput('info', "\n\n\n######### Verifying the IPv6 static routes on "
              "switch 1#########")

    # Verify route a234:a234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute1, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute1, 'zebra')

    # Verify route 2234:2234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute2, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute2, 'zebra')

    # Verify route 3234:3234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute3, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute3, 'zebra')

    # Verify route 7234:7234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute4,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute4, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute4, 'zebra')

    # Verify route 8234:8234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute5,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute5, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute5, 'zebra')

    LogOutput('info', "\n\n\n######### Verification of "
              "IPv4 and IPv6 static routes on switch 1 passed after "
              "restart#########")

    LogOutput('info', "\n\n\n######### Restarting zebra with config changes on  "
              "switch 1 passed#########")


# This test restarts zebra process and checks if the routes and next-hops show
# correctly in the output of "show ip route/show rib" after zebra has restarted.
# After zebra has come back up from restart, we change the static route configuration
# by deleting some routes and adding some new routes.
def config_change_after_zebra_restart(**kwargs):

    switch1 = kwargs.get('switch1', None)
    switch2 = kwargs.get('switch2', None)

    switch1.commandErrorCheck = 0
    switch2.commandErrorCheck = 0

    zebra_stop_command_string = "systemctl stop ops-zebra"
    zebra_start_command_string = "systemctl start ops-zebra"

    LogOutput('info', "\n\n\n######### Restarting zebra on switch 1#########")

    LogOutput('info', "\n\n\n######### Restarting zebra. Stopping ops-zebra service on"
              "switch 1#########")

    # Execute the command to stop zebra on the Linux bash interface
    devIntRetStruct = switch1.DeviceInteract(command=zebra_stop_command_string)
    retCode = devIntRetStruct.get('returnCode')

    if retCode != 0:
        assert "Failed to stop zebra"

    LogOutput('info', "\n\n\n######### Restarting zebra. Starting ops-zebra service on"
              "switch 1#########")

    # Execute the command to start zebra on the Linux bash interface
    devIntRetStruct = switch1.DeviceInteract(command=zebra_start_command_string)
    retCode = devIntRetStruct.get('returnCode')

    if retCode != 0:
        assert "Failed to start zebra"

    LogOutput('info', "\n\n\n######### Adding some static route configuration "
              " after zebra has restarted on switch 1#########")

    # Configure IPv4 route 123.0.0.1/32 with next-hop 1.1.1.2
    retStruct = IpRouteConfig(deviceObj=switch1, route="123.0.0.1", mask=32,
                              nexthop="1.1.1.2", config=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv4 route"

    # Configure IPv4 route 123.0.0.1/32 with next-hop 2
    retStruct = IpRouteConfig(deviceObj=switch1, route="123.0.0.1", mask=32,
                              nexthop="2", config=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv4 route"

    # Configure IPv4 route 143.0.0.1/32 next-hop 4.4.4.1.
    retStruct = IpRouteConfig(deviceObj=switch1, route="143.0.0.1", mask=32,
                              nexthop="4.4.4.1", config=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv4 route"

    # Configure IPv6 route a234:a234::1/128 with next-hop 1.
    retStruct = IpRouteConfig(deviceObj=switch1, route="a234:a234::1",
                              mask=128, nexthop="1", config=True,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv6 route"

    # Configure IPv6 route a234:a234::1/128 with next-hop 2.
    retStruct = IpRouteConfig(deviceObj=switch1, route="a234:a234::1",
                              mask=128, nexthop="2", config=True,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv6 route"

    # Configure IPv6 route 3234:3234::1/128 with next-hop 2.
    retStruct = IpRouteConfig(deviceObj=switch1, route="3234:3234::1",
                              mask=128, nexthop="2", config=True,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to configure ipv6 route"

    LogOutput('info', "\n\n\n######### Removing some static route configuration "
              " after zebra has restarted on switch 1#########")

    # Un-configure IPv4 route 173.0.0.1/32 with next-hop 1.1.1.2
    retStruct = IpRouteConfig(deviceObj=switch1, route="173.0.0.1", mask=32,
                              nexthop="1.1.1.2", config=False)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv4 route"

    # Un-configure IPv4 route 173.0.0.1/32 with next-hop 3
    retStruct = IpRouteConfig(deviceObj=switch1, route="173.0.0.1", mask=32,
                              nexthop="3", config=False)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv4 route"

    # Un-configure IPv4 route 183.0.0.1/32 next-hop 4.4.4.1.
    retStruct = IpRouteConfig(deviceObj=switch1, route="183.0.0.1", mask=32,
                              nexthop="4.4.4.1", config=False)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv4 route"

    # Un-configure IPv6 route 7234:7234::1/128 with next-hop 1.
    retStruct = IpRouteConfig(deviceObj=switch1, route="7234:7234::1",
                              mask=128, nexthop="1", config=False,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv6 route"

    # Un-configure IPv6 route 7234:7234::1/128 with next-hop 3.
    retStruct = IpRouteConfig(deviceObj=switch1, route="7234:7234::1",
                              mask=128, nexthop="3", config=False,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv6 route"

    # Un-configure IPv6 route 8234:8234::1/128 with next-hop 2.
    retStruct = IpRouteConfig(deviceObj=switch1, route="8234:8234::1",
                              mask=128, nexthop="2", config=False,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv6 route"


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
    ExpRibDictIpv4StaticRoute1['4.4.4.1'] = dict()
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 123.0.0.1/32 and its next-hops.
    ExpRouteDictIpv4StaticRoute1 = ExpRibDictIpv4StaticRoute1

    # Populate the version of the route in kernel in the route dictionary
    # for the route 123.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute1 = dict()
    ExpDictIpv4KernelRoute1['Route'] = '123.0.0.1' + '/' + '32'
    ExpDictIpv4KernelRoute1['NumberNexthops'] = '4'
    ExpDictIpv4KernelRoute1['1.1.1.2'] = dict()
    ExpDictIpv4KernelRoute1['1.1.1.2']['Distance'] = ''
    ExpDictIpv4KernelRoute1['1.1.1.2']['Metric'] = ''
    ExpDictIpv4KernelRoute1['1.1.1.2']['RouteType'] = 'zebra'
    ExpDictIpv4KernelRoute1['2'] = dict()
    ExpDictIpv4KernelRoute1['2']['Distance'] = ''
    ExpDictIpv4KernelRoute1['2']['Metric'] = ''
    ExpDictIpv4KernelRoute1['2']['RouteType'] = 'zebra'
    ExpDictIpv4KernelRoute1['3'] = dict()
    ExpDictIpv4KernelRoute1['3']['Distance'] = ''
    ExpDictIpv4KernelRoute1['3']['Metric'] = ''
    ExpDictIpv4KernelRoute1['3']['RouteType'] = 'zebra'
    ExpDictIpv4KernelRoute1['4.4.4.1'] = dict()
    ExpDictIpv4KernelRoute1['4.4.4.1']['Distance'] = ''
    ExpDictIpv4KernelRoute1['4.4.4.1']['Metric'] = ''
    ExpDictIpv4KernelRoute1['4.4.4.1']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 143.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute2 = dict()
    ExpDictIpv4KernelRoute2['Route'] = '143.0.0.1' + '/' + '32'
    ExpDictIpv4KernelRoute2['NumberNexthops'] = '1'
    ExpDictIpv4KernelRoute2['4.4.4.1'] = dict()
    ExpDictIpv4KernelRoute2['4.4.4.1']['Distance'] = ''
    ExpDictIpv4KernelRoute2['4.4.4.1']['Metric'] = ''
    ExpDictIpv4KernelRoute2['4.4.4.1']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 163.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute3 = dict()
    ExpDictIpv4KernelRoute3['Route'] = '163.0.0.1' + '/' + '32'
    ExpDictIpv4KernelRoute3['NumberNexthops'] = '1'
    ExpDictIpv4KernelRoute3['2'] = dict()
    ExpDictIpv4KernelRoute3['2']['Distance'] = ''
    ExpDictIpv4KernelRoute3['2']['Metric'] = ''
    ExpDictIpv4KernelRoute3['2']['RouteType'] = 'zebra'

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 173.0.0.1/32 and its next-hops.
    ExpRibDictIpv4StaticRoute4 = dict()
    ExpRibDictIpv4StaticRoute4['Route'] = '173.0.0.1' + '/' + '32'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 173.0.0.1/32 and its next-hops.
    ExpRouteDictIpv4StaticRoute4 = ExpRibDictIpv4StaticRoute4

    # Populate the version of the route in kernel in the route dictionary
    # for the route 173.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute4 = dict()
    ExpDictIpv4KernelRoute4['Route'] = '173.0.0.1' + '/' + '32'

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 183.0.0.1/32 and its next-hops.
    ExpRibDictIpv4StaticRoute5 = dict()
    ExpRibDictIpv4StaticRoute5['Route'] = '183.0.0.1' + '/' + '32'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 183.0.0.1/32 and its next-hops.
    ExpRouteDictIpv4StaticRoute5 = ExpRibDictIpv4StaticRoute5

    # Populate the version of the route in kernel in the route dictionary
    # for the route 183.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute5 = dict()
    ExpDictIpv4KernelRoute5['Route'] = '183.0.0.1' + '/' + '32'

    # Populate the expected RIB ("show rib") route dictionary for the
    # route a234:a234::1/128 and its next-hops.
    ExpRibDictIpv6StaticRoute1 = dict()
    ExpRibDictIpv6StaticRoute1['Route'] = 'a234:a234::1' + '/' + '128'
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
    # route a234:a234::1/128 and its next-hops.
    ExpRouteDictIpv6StaticRoute1 = ExpRibDictIpv6StaticRoute1

    # Populate the version of the route in kernel in the route dictionary
    # for the route a234:a234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute1 = dict()
    ExpDictIpv6KernelRoute1['Route'] = 'a234:a234::1' + '/' + '128'
    ExpDictIpv6KernelRoute1['NumberNexthops'] = '4'
    ExpDictIpv6KernelRoute1['1'] = dict()
    ExpDictIpv6KernelRoute1['1']['Distance'] = ''
    ExpDictIpv6KernelRoute1['1']['Metric'] = ''
    ExpDictIpv6KernelRoute1['1']['RouteType'] = 'zebra'
    ExpDictIpv6KernelRoute1['2'] = dict()
    ExpDictIpv6KernelRoute1['2']['Distance'] = ''
    ExpDictIpv6KernelRoute1['2']['Metric'] = ''
    ExpDictIpv6KernelRoute1['2']['RouteType'] = 'zebra'
    ExpDictIpv6KernelRoute1['3'] = dict()
    ExpDictIpv6KernelRoute1['3']['Distance'] = ''
    ExpDictIpv6KernelRoute1['3']['Metric'] = ''
    ExpDictIpv6KernelRoute1['3']['RouteType'] = 'zebra'
    ExpDictIpv6KernelRoute1['4'] = dict()
    ExpDictIpv6KernelRoute1['4']['Distance'] = ''
    ExpDictIpv6KernelRoute1['4']['Metric'] = ''
    ExpDictIpv6KernelRoute1['4']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 2234:2234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute2 = dict()
    ExpDictIpv6KernelRoute2['Route'] = '2234:2234::1' + '/' + '128'
    ExpDictIpv6KernelRoute2['NumberNexthops'] = '1'
    ExpDictIpv6KernelRoute2['4'] = dict()
    ExpDictIpv6KernelRoute2['4']['Distance'] = ''
    ExpDictIpv6KernelRoute2['4']['Metric'] = ''
    ExpDictIpv6KernelRoute2['4']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 3234:3234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute3 = dict()
    ExpDictIpv6KernelRoute3['Route'] = '3234:3234::1' + '/' + '128'
    ExpDictIpv6KernelRoute3['NumberNexthops'] = '1'
    ExpDictIpv6KernelRoute3['2'] = dict()
    ExpDictIpv6KernelRoute3['2']['Distance'] = ''
    ExpDictIpv6KernelRoute3['2']['Metric'] = ''
    ExpDictIpv6KernelRoute3['2']['RouteType'] = 'zebra'

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 7234:7234::1/128 and its next-hops.
    ExpRibDictIpv6StaticRoute4 = dict()
    ExpRibDictIpv6StaticRoute4['Route'] = '7234:7234::1' + '/' + '128'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 7234:7234::1/128 and its next-hops.
    ExpRouteDictIpv6StaticRoute4 = ExpRibDictIpv6StaticRoute4

    # Populate the version of the route in kernel in the route dictionary
    # for the route 7234:7234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute4 = dict()
    ExpDictIpv6KernelRoute4['Route'] = '7234:7234::1' + '/' + '128'

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 8234:8234::1/128 and its next-hops.
    ExpRibDictIpv6StaticRoute5 = dict()
    ExpRibDictIpv6StaticRoute5['Route'] = '8234:8234::1' + '/' + '128'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 8234:8234::1/128 and its next-hops.
    ExpRouteDictIpv6StaticRoute5 = ExpRibDictIpv6StaticRoute5

    # Populate the version of the route in kernel in the route dictionary
    # for the route 8234:8234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute5 = dict()
    ExpDictIpv6KernelRoute5['Route'] = '8234:8234::1' + '/' + '128'

    time.sleep(5)

    LogOutput('info', "\n\n\n######### Verifying the IPv4 static routes on "
              "switch 1#########")

    # Verify route 123.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute1, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute1, 'zebra')

    # Verify route 143.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute2, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute2, 'zebra')

    # Verify route 163.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute3, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute3, 'zebra')

    # Verify route 173.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute4,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute4, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute4, 'zebra')

    # Verify route 183.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute5,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute5, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute5, 'zebra')

    LogOutput('info', "\n\n\n######### Verifying the IPv6 static routes on "
              "switch 1#########")

    # Verify route a234:a234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute1, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute1, 'zebra')

    # Verify route 2234:2234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute2, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute2, 'zebra')

    # Verify route 3234:3234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute3, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute3, 'zebra')

    # Verify route 7234:7234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute4,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute4, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute4, 'zebra')

    # Verify route 8234:8234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute5,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute5, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute5, 'zebra')

    LogOutput('info', "\n\n\n######### Verification of "
              "IPv4 and IPv6 static routes on switch 1 passed after "
              "restart#########")

    LogOutput('info', "\n\n\n######### Config changes after zebra changes on  "
              "switch 1 passed#########")


# This test restarts zebra process and checks if the routes and next-hops show
# correctly in the output of "show ip route/show rib" after zebra has restarted.
# Before zebra has come back up from restart, we shutdown some next-hop interfaces.
def interface_down_before_zebra_restart(**kwargs):

    switch1 = kwargs.get('switch1', None)
    switch2 = kwargs.get('switch2', None)

    switch1.commandErrorCheck = 0
    switch2.commandErrorCheck = 0

    zebra_stop_command_string = "systemctl stop ops-zebra"
    zebra_start_command_string = "systemctl start ops-zebra"

    LogOutput('info', "\n\n\n######### Restarting zebra and shutting down"
              " some next-hop interfaces on switch1.#########")

    LogOutput('info', "\n\n\n######### Restarting zebra. Stopping ops-zebra service on"
              "switch 1#########")

    # Execute the command to stop zebra on the Linux bash interface
    devIntRetStruct = switch1.DeviceInteract(command=zebra_stop_command_string)
    retCode = devIntRetStruct.get('returnCode')

    if retCode != 0:
        assert "Failed to stop zebra"

    LogOutput('info', "\n\n\n######### Shutdown some next-hop interfaces "
              " after zebra has gone down on switch 1#########")

    # disabling interface 2 on switch1
    LogOutput('info', "Disabling interface2 on SW1")
    retStruct = InterfaceEnable(deviceObj=switch1, enable=False,
                                interface=switch1.linkPortMapping['lnk02'])
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Unable to disable interafce on SW1"

    LogOutput('info', "\n\n\n######### Restarting zebra. Starting ops-zebra service on"
              "switch 1#########")

    # Execute the command to start zebra on the Linux bash interface
    devIntRetStruct = switch1.DeviceInteract(command=zebra_start_command_string)
    retCode = devIntRetStruct.get('returnCode')

    if retCode != 0:
        assert "Failed to start zebra"

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
    ExpRibDictIpv4StaticRoute1['4.4.4.1'] = dict()
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 123.0.0.1/32 and its next-hops.
    ExpRouteDictIpv4StaticRoute1 = dict()
    ExpRouteDictIpv4StaticRoute1['Route'] = '123.0.0.1' + '/' + '32'
    ExpRouteDictIpv4StaticRoute1['NumberNexthops'] = '3'
    ExpRouteDictIpv4StaticRoute1['1.1.1.2'] = dict()
    ExpRouteDictIpv4StaticRoute1['1.1.1.2']['Distance'] = '1'
    ExpRouteDictIpv4StaticRoute1['1.1.1.2']['Metric'] = '0'
    ExpRouteDictIpv4StaticRoute1['1.1.1.2']['RouteType'] = 'static'
    ExpRouteDictIpv4StaticRoute1['3'] = dict()
    ExpRouteDictIpv4StaticRoute1['3']['Distance'] = '1'
    ExpRouteDictIpv4StaticRoute1['3']['Metric'] = '0'
    ExpRouteDictIpv4StaticRoute1['3']['RouteType'] = 'static'
    ExpRouteDictIpv4StaticRoute1['4.4.4.1'] = dict()
    ExpRouteDictIpv4StaticRoute1['4.4.4.1']['Distance'] = '1'
    ExpRouteDictIpv4StaticRoute1['4.4.4.1']['Metric'] = '0'
    ExpRouteDictIpv4StaticRoute1['4.4.4.1']['RouteType'] = 'static'

    # Populate the version of the route in kernel in the route dictionary
    # for the route 123.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute1 = dict()
    ExpDictIpv4KernelRoute1['Route'] = '123.0.0.1' + '/' + '32'
    ExpDictIpv4KernelRoute1['NumberNexthops'] = '3'
    ExpDictIpv4KernelRoute1['1.1.1.2'] = dict()
    ExpDictIpv4KernelRoute1['1.1.1.2']['Distance'] = ''
    ExpDictIpv4KernelRoute1['1.1.1.2']['Metric'] = ''
    ExpDictIpv4KernelRoute1['1.1.1.2']['RouteType'] = 'zebra'
    ExpDictIpv4KernelRoute1['3'] = dict()
    ExpDictIpv4KernelRoute1['3']['Distance'] = ''
    ExpDictIpv4KernelRoute1['3']['Metric'] = ''
    ExpDictIpv4KernelRoute1['3']['RouteType'] = 'zebra'
    ExpDictIpv4KernelRoute1['4.4.4.1'] = dict()
    ExpDictIpv4KernelRoute1['4.4.4.1']['Distance'] = ''
    ExpDictIpv4KernelRoute1['4.4.4.1']['Metric'] = ''
    ExpDictIpv4KernelRoute1['4.4.4.1']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 143.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute2 = dict()
    ExpDictIpv4KernelRoute2['Route'] = '143.0.0.1' + '/' + '32'
    ExpDictIpv4KernelRoute2['NumberNexthops'] = '1'
    ExpDictIpv4KernelRoute2['4.4.4.1'] = dict()
    ExpDictIpv4KernelRoute2['4.4.4.1']['Distance'] = ''
    ExpDictIpv4KernelRoute2['4.4.4.1']['Metric'] = ''
    ExpDictIpv4KernelRoute2['4.4.4.1']['RouteType'] = 'zebra'

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
    ExpRouteDictIpv4StaticRoute3 = dict()
    ExpRouteDictIpv4StaticRoute3['Route'] = '163.0.0.1' + '/' + '32'

    # Populate the version of the route in kernel in the route dictionary
    # for the route 163.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute3 = dict()
    ExpDictIpv4KernelRoute3['Route'] = '163.0.0.1' + '/' + '32'

    # Populate the expected RIB ("show rib") route dictionary for the
    # route a234:a234::1/128 and its next-hops.
    ExpRibDictIpv6StaticRoute1 = dict()
    ExpRibDictIpv6StaticRoute1['Route'] = 'a234:a234::1' + '/' + '128'
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
    # route a234:a234::1/128 and its next-hops.
    ExpRouteDictIpv6StaticRoute1 = dict()
    ExpRouteDictIpv6StaticRoute1['Route'] = 'a234:a234::1' + '/' + '128'
    ExpRouteDictIpv6StaticRoute1['NumberNexthops'] = '3'
    ExpRouteDictIpv6StaticRoute1['1'] = dict()
    ExpRouteDictIpv6StaticRoute1['1']['Distance'] = '1'
    ExpRouteDictIpv6StaticRoute1['1']['Metric'] = '0'
    ExpRouteDictIpv6StaticRoute1['1']['RouteType'] = 'static'
    ExpRouteDictIpv6StaticRoute1['3'] = dict()
    ExpRouteDictIpv6StaticRoute1['3']['Distance'] = '1'
    ExpRouteDictIpv6StaticRoute1['3']['Metric'] = '0'
    ExpRouteDictIpv6StaticRoute1['3']['RouteType'] = 'static'
    ExpRouteDictIpv6StaticRoute1['4'] = dict()
    ExpRouteDictIpv6StaticRoute1['4']['Distance'] = '1'
    ExpRouteDictIpv6StaticRoute1['4']['Metric'] = '0'
    ExpRouteDictIpv6StaticRoute1['4']['RouteType'] = 'static'

    # Populate the version of the route in kernel in the route dictionary
    # for the route a234:a234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute1 = dict()
    ExpDictIpv6KernelRoute1['Route'] = 'a234:a234::1' + '/' + '128'
    ExpDictIpv6KernelRoute1['NumberNexthops'] = '3'
    ExpDictIpv6KernelRoute1['1'] = dict()
    ExpDictIpv6KernelRoute1['1']['Distance'] = ''
    ExpDictIpv6KernelRoute1['1']['Metric'] = ''
    ExpDictIpv6KernelRoute1['1']['RouteType'] = 'zebra'
    ExpDictIpv6KernelRoute1['3'] = dict()
    ExpDictIpv6KernelRoute1['3']['Distance'] = ''
    ExpDictIpv6KernelRoute1['3']['Metric'] = ''
    ExpDictIpv6KernelRoute1['3']['RouteType'] = 'zebra'
    ExpDictIpv6KernelRoute1['4'] = dict()
    ExpDictIpv6KernelRoute1['4']['Distance'] = ''
    ExpDictIpv6KernelRoute1['4']['Metric'] = ''
    ExpDictIpv6KernelRoute1['4']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 2234:2234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute2 = dict()
    ExpDictIpv6KernelRoute2['Route'] = '2234:2234::1' + '/' + '128'
    ExpDictIpv6KernelRoute2['NumberNexthops'] = '1'
    ExpDictIpv6KernelRoute2['4'] = dict()
    ExpDictIpv6KernelRoute2['4']['Distance'] = ''
    ExpDictIpv6KernelRoute2['4']['Metric'] = ''
    ExpDictIpv6KernelRoute2['4']['RouteType'] = 'zebra'

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
    ExpRouteDictIpv6StaticRoute3 = dict()
    ExpRouteDictIpv6StaticRoute3['Route'] = '3234:3234::1' + '/' + '128'

    # Populate the version of the route in kernel in the route dictionary
    # for the route 3234:3234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute3 = dict()
    ExpDictIpv6KernelRoute3['Route'] = '3234:3234::1' + '/' + '128'

    time.sleep(5)

    LogOutput('info', "\n\n\n######### Verifying the IPv4 static routes on "
              "switch 1#########")

    # Verify route 123.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute1, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute1, 'zebra')

    # Verify route 143.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute2, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute2, 'zebra')

    # Verify route 163.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute3, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute3, 'zebra')

    LogOutput('info', "\n\n\n######### Verifying the IPv6 static routes on "
              "switch 1#########")

    # Verify route a234:a234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute1, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute1, 'zebra')

    # Verify route 2234:2234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute2, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute2, 'zebra')

    # Verify route 3234:3234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute3, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute3, 'zebra')

    LogOutput('info', "\n\n\n######### Verification of "
              "IPv4 and IPv6 static routes on switch 1 passed after "
              "restart#########")

    LogOutput('info', "\n\n\n######### Restarting zebra and shutting "
              "down some next-hop interfaces on switch1.#########")


# This test restarts zebra process and checks if the routes and next-hops show
# correctly in the output of "show ip route/show rib" after zebra has restarted.
# Before zebra has come back up from restart, we un-shutdown some next-hop interfaces.
def interface_up_before_zebra_restart(**kwargs):

    switch1 = kwargs.get('switch1', None)
    switch2 = kwargs.get('switch2', None)

    switch1.commandErrorCheck = 0
    switch2.commandErrorCheck = 0

    zebra_stop_command_string = "systemctl stop ops-zebra"
    zebra_start_command_string = "systemctl start ops-zebra"

    LogOutput('info', "\n\n\n######### Restarting zebra and un-shutting"
              " some next-hop interfaces on switch1.#########")

    LogOutput('info', "\n\n\n######### Restarting zebra. Stopping ops-zebra service on"
              "switch 1#########")

    # Execute the command to stop zebra on the Linux bash interface
    devIntRetStruct = switch1.DeviceInteract(command=zebra_stop_command_string)
    retCode = devIntRetStruct.get('returnCode')

    if retCode != 0:
        assert "Failed to stop zebra"

    LogOutput('info', "\n\n\n######### Un-shutdown some next-hop interfaces "
              " after zebra has gone down on switch 1#########")

    # disabling interface 2 on switch1
    LogOutput('info', "Disabling interface2 on SW1")
    retStruct = InterfaceEnable(deviceObj=switch1, enable=True,
                                interface=switch1.linkPortMapping['lnk02'])
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Unable to disable interafce on SW1"

    LogOutput('info', "\n\n\n######### Restarting zebra. Starting ops-zebra service on"
              "switch 1#########")

    # Execute the command to start zebra on the Linux bash interface
    devIntRetStruct = switch1.DeviceInteract(command=zebra_start_command_string)
    retCode = devIntRetStruct.get('returnCode')

    if retCode != 0:
        assert "Failed to start zebra"

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
    ExpRibDictIpv4StaticRoute1['4.4.4.1'] = dict()
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 123.0.0.1/32 and its next-hops.
    ExpRouteDictIpv4StaticRoute1 = ExpRibDictIpv4StaticRoute1

    # Populate the version of the route in kernel in the route dictionary
    # for the route 123.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute1 = dict()
    ExpDictIpv4KernelRoute1['Route'] = '123.0.0.1' + '/' + '32'
    ExpDictIpv4KernelRoute1['NumberNexthops'] = '4'
    ExpDictIpv4KernelRoute1['1.1.1.2'] = dict()
    ExpDictIpv4KernelRoute1['1.1.1.2']['Distance'] = ''
    ExpDictIpv4KernelRoute1['1.1.1.2']['Metric'] = ''
    ExpDictIpv4KernelRoute1['1.1.1.2']['RouteType'] = 'zebra'
    ExpDictIpv4KernelRoute1['2'] = dict()
    ExpDictIpv4KernelRoute1['2']['Distance'] = ''
    ExpDictIpv4KernelRoute1['2']['Metric'] = ''
    ExpDictIpv4KernelRoute1['2']['RouteType'] = 'zebra'
    ExpDictIpv4KernelRoute1['3'] = dict()
    ExpDictIpv4KernelRoute1['3']['Distance'] = ''
    ExpDictIpv4KernelRoute1['3']['Metric'] = ''
    ExpDictIpv4KernelRoute1['3']['RouteType'] = 'zebra'
    ExpDictIpv4KernelRoute1['4.4.4.1'] = dict()
    ExpDictIpv4KernelRoute1['4.4.4.1']['Distance'] = ''
    ExpDictIpv4KernelRoute1['4.4.4.1']['Metric'] = ''
    ExpDictIpv4KernelRoute1['4.4.4.1']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 143.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute2 = dict()
    ExpDictIpv4KernelRoute2['Route'] = '143.0.0.1' + '/' + '32'
    ExpDictIpv4KernelRoute2['NumberNexthops'] = '1'
    ExpDictIpv4KernelRoute2['4.4.4.1'] = dict()
    ExpDictIpv4KernelRoute2['4.4.4.1']['Distance'] = ''
    ExpDictIpv4KernelRoute2['4.4.4.1']['Metric'] = ''
    ExpDictIpv4KernelRoute2['4.4.4.1']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 163.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute3 = dict()
    ExpDictIpv4KernelRoute3['Route'] = '163.0.0.1' + '/' + '32'
    ExpDictIpv4KernelRoute3['NumberNexthops'] = '1'
    ExpDictIpv4KernelRoute3['2'] = dict()
    ExpDictIpv4KernelRoute3['2']['Distance'] = ''
    ExpDictIpv4KernelRoute3['2']['Metric'] = ''
    ExpDictIpv4KernelRoute3['2']['RouteType'] = 'zebra'

    # Populate the expected RIB ("show rib") route dictionary for the
    # route a234:a234::1/128 and its next-hops.
    ExpRibDictIpv6StaticRoute1 = dict()
    ExpRibDictIpv6StaticRoute1['Route'] = 'a234:a234::1' + '/' + '128'
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
    # route a234:a234::1/128 and its next-hops.
    ExpRouteDictIpv6StaticRoute1 = ExpRibDictIpv6StaticRoute1

    # Populate the version of the route in kernel in the route dictionary
    # for the route a234:a234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute1 = dict()
    ExpDictIpv6KernelRoute1['Route'] = 'a234:a234::1' + '/' + '128'
    ExpDictIpv6KernelRoute1['NumberNexthops'] = '4'
    ExpDictIpv6KernelRoute1['1'] = dict()
    ExpDictIpv6KernelRoute1['1']['Distance'] = ''
    ExpDictIpv6KernelRoute1['1']['Metric'] = ''
    ExpDictIpv6KernelRoute1['1']['RouteType'] = 'zebra'
    ExpDictIpv6KernelRoute1['2'] = dict()
    ExpDictIpv6KernelRoute1['2']['Distance'] = ''
    ExpDictIpv6KernelRoute1['2']['Metric'] = ''
    ExpDictIpv6KernelRoute1['2']['RouteType'] = 'zebra'
    ExpDictIpv6KernelRoute1['3'] = dict()
    ExpDictIpv6KernelRoute1['3']['Distance'] = ''
    ExpDictIpv6KernelRoute1['3']['Metric'] = ''
    ExpDictIpv6KernelRoute1['3']['RouteType'] = 'zebra'
    ExpDictIpv6KernelRoute1['4'] = dict()
    ExpDictIpv6KernelRoute1['4']['Distance'] = ''
    ExpDictIpv6KernelRoute1['4']['Metric'] = ''
    ExpDictIpv6KernelRoute1['4']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 2234:2234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute2 = dict()
    ExpDictIpv6KernelRoute2['Route'] = '2234:2234::1' + '/' + '128'
    ExpDictIpv6KernelRoute2['NumberNexthops'] = '1'
    ExpDictIpv6KernelRoute2['4'] = dict()
    ExpDictIpv6KernelRoute2['4']['Distance'] = ''
    ExpDictIpv6KernelRoute2['4']['Metric'] = ''
    ExpDictIpv6KernelRoute2['4']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 3234:3234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute3 = dict()
    ExpDictIpv6KernelRoute3['Route'] = '3234:3234::1' + '/' + '128'
    ExpDictIpv6KernelRoute3['NumberNexthops'] = '1'
    ExpDictIpv6KernelRoute3['2'] = dict()
    ExpDictIpv6KernelRoute3['2']['Distance'] = ''
    ExpDictIpv6KernelRoute3['2']['Metric'] = ''
    ExpDictIpv6KernelRoute3['2']['RouteType'] = 'zebra'

    time.sleep(5)

    LogOutput('info', "\n\n\n######### Verifying the IPv4 static routes on "
              "switch 1#########")

    # Verify route 123.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute1, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute1, 'zebra')

    # Verify route 143.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute2, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute2, 'zebra')

    # Verify route 163.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute3, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute3, 'zebra')

    LogOutput('info', "\n\n\n######### Verifying the IPv6 static routes on "
              "switch 1#########")

    # Verify route a234:a234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute1, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute1, 'zebra')

    # Verify route 2234:2234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute2, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute2, 'zebra')

    # Verify route 3234:3234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute3, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute3, 'zebra')

    LogOutput('info', "\n\n\n######### Verification of "
              "IPv4 and IPv6 static routes on switch 1 passed after "
              "restart#########")

    LogOutput('info', "\n\n\n######### Restarting zebra and un-shutting "
              "down some next-hop interfaces on switch1.#########")


# This test restarts zebra process and checks if the routes and next-hops show
# correctly in the output of "show ip route/show rib" after zebra has restarted.
# Before zebra has come back up from restart, we change interface addresses on
# some interfaces.
def interface_addr_change_before_zebra_restart(**kwargs):

    switch1 = kwargs.get('switch1', None)
    switch2 = kwargs.get('switch2', None)

    switch1.commandErrorCheck = 0
    switch2.commandErrorCheck = 0

    zebra_stop_command_string = "systemctl stop ops-zebra"
    zebra_start_command_string = "systemctl start ops-zebra"

    LogOutput('info', "\n\n\n######### Restarting zebra and changing "
              " some interface addresses on switch1.#########")

    LogOutput('info', "\n\n\n######### Restarting zebra. Stopping ops-zebra service on"
              "switch 1#########")

    # Execute the command to stop zebra on the Linux bash interface
    devIntRetStruct = switch1.DeviceInteract(command=zebra_stop_command_string)
    retCode = devIntRetStruct.get('returnCode')

    if retCode != 0:
        assert "Failed to stop zebra"

    LogOutput('info', "\n\n\n######### Changing some interface IP addresses"
              " after zebra has gone down on switch 1#########")

    # Re-configure IPv4 address on interface 1 on switch1
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk01'],
                                  addr="9.9.9.9", mask=24, config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to re-configure an ipv4 address"

    # Re-configure IPv6 address on interface 1 on switch1
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk01'],
                                  addr="999:999::9", mask=64, ipv6flag=True,
                                  config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to re-configure an ipv6 address"

    LogOutput('info', "\n\n\n######### Restarting zebra. Starting ops-zebra service on"
              "switch 1#########")

    # Execute the command to start zebra on the Linux bash interface
    devIntRetStruct = switch1.DeviceInteract(command=zebra_start_command_string)
    retCode = devIntRetStruct.get('returnCode')

    if retCode != 0:
        assert "Failed to start zebra"

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
    ExpRibDictIpv4StaticRoute1['4.4.4.1'] = dict()
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 123.0.0.1/32 and its next-hops.
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
    ExpRouteDictIpv4StaticRoute1['4.4.4.1'] = dict()
    ExpRouteDictIpv4StaticRoute1['4.4.4.1']['Distance'] = '1'
    ExpRouteDictIpv4StaticRoute1['4.4.4.1']['Metric'] = '0'
    ExpRouteDictIpv4StaticRoute1['4.4.4.1']['RouteType'] = 'static'

    # Populate the version of the route in kernel in the route dictionary
    # for the route 123.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute1 = dict()
    ExpDictIpv4KernelRoute1['Route'] = '123.0.0.1' + '/' + '32'
    ExpDictIpv4KernelRoute1['NumberNexthops'] = '3'
    ExpDictIpv4KernelRoute1['2'] = dict()
    ExpDictIpv4KernelRoute1['2']['Distance'] = ''
    ExpDictIpv4KernelRoute1['2']['Metric'] = ''
    ExpDictIpv4KernelRoute1['2']['RouteType'] = 'zebra'
    ExpDictIpv4KernelRoute1['3'] = dict()
    ExpDictIpv4KernelRoute1['3']['Distance'] = ''
    ExpDictIpv4KernelRoute1['3']['Metric'] = ''
    ExpDictIpv4KernelRoute1['3']['RouteType'] = 'zebra'
    ExpDictIpv4KernelRoute1['4.4.4.1'] = dict()
    ExpDictIpv4KernelRoute1['4.4.4.1']['Distance'] = ''
    ExpDictIpv4KernelRoute1['4.4.4.1']['Metric'] = ''
    ExpDictIpv4KernelRoute1['4.4.4.1']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 143.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute2 = dict()
    ExpDictIpv4KernelRoute2['Route'] = '143.0.0.1' + '/' + '32'
    ExpDictIpv4KernelRoute2['NumberNexthops'] = '1'
    ExpDictIpv4KernelRoute2['4.4.4.1'] = dict()
    ExpDictIpv4KernelRoute2['4.4.4.1']['Distance'] = ''
    ExpDictIpv4KernelRoute2['4.4.4.1']['Metric'] = ''
    ExpDictIpv4KernelRoute2['4.4.4.1']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 163.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute3 = dict()
    ExpDictIpv4KernelRoute3['Route'] = '163.0.0.1' + '/' + '32'
    ExpDictIpv4KernelRoute3['NumberNexthops'] = '1'
    ExpDictIpv4KernelRoute3['2'] = dict()
    ExpDictIpv4KernelRoute3['2']['Distance'] = ''
    ExpDictIpv4KernelRoute3['2']['Metric'] = ''
    ExpDictIpv4KernelRoute3['2']['RouteType'] = 'zebra'

    # Populate the expected RIB ("show rib") route dictionary for the
    # route a234:a234::1/128 and its next-hops.
    ExpRibDictIpv6StaticRoute1 = dict()
    ExpRibDictIpv6StaticRoute1['Route'] = 'a234:a234::1' + '/' + '128'
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
    # route a234:a234::1/128 and its next-hops.
    ExpRouteDictIpv6StaticRoute1 = ExpRibDictIpv6StaticRoute1

    # Populate the version of the route in kernel in the route dictionary
    # for the route a234:a234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute1 = dict()
    ExpDictIpv6KernelRoute1['Route'] = 'a234:a234::1' + '/' + '128'
    ExpDictIpv6KernelRoute1['NumberNexthops'] = '4'
    ExpDictIpv6KernelRoute1['1'] = dict()
    ExpDictIpv6KernelRoute1['1']['Distance'] = ''
    ExpDictIpv6KernelRoute1['1']['Metric'] = ''
    ExpDictIpv6KernelRoute1['1']['RouteType'] = 'zebra'
    ExpDictIpv6KernelRoute1['2'] = dict()
    ExpDictIpv6KernelRoute1['2']['Distance'] = ''
    ExpDictIpv6KernelRoute1['2']['Metric'] = ''
    ExpDictIpv6KernelRoute1['2']['RouteType'] = 'zebra'
    ExpDictIpv6KernelRoute1['3'] = dict()
    ExpDictIpv6KernelRoute1['3']['Distance'] = ''
    ExpDictIpv6KernelRoute1['3']['Metric'] = ''
    ExpDictIpv6KernelRoute1['3']['RouteType'] = 'zebra'
    ExpDictIpv6KernelRoute1['4'] = dict()
    ExpDictIpv6KernelRoute1['4']['Distance'] = ''
    ExpDictIpv6KernelRoute1['4']['Metric'] = ''
    ExpDictIpv6KernelRoute1['4']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 2234:2234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute2 = dict()
    ExpDictIpv6KernelRoute2['Route'] = '2234:2234::1' + '/' + '128'
    ExpDictIpv6KernelRoute2['NumberNexthops'] = '1'
    ExpDictIpv6KernelRoute2['4'] = dict()
    ExpDictIpv6KernelRoute2['4']['Distance'] = ''
    ExpDictIpv6KernelRoute2['4']['Metric'] = ''
    ExpDictIpv6KernelRoute2['4']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 3234:3234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute3 = dict()
    ExpDictIpv6KernelRoute3['Route'] = '3234:3234::1' + '/' + '128'
    ExpDictIpv6KernelRoute3['NumberNexthops'] = '1'
    ExpDictIpv6KernelRoute3['2'] = dict()
    ExpDictIpv6KernelRoute3['2']['Distance'] = ''
    ExpDictIpv6KernelRoute3['2']['Metric'] = ''
    ExpDictIpv6KernelRoute3['2']['RouteType'] = 'zebra'

    time.sleep(5)

    LogOutput('info', "\n\n\n######### Verifying the IPv4 static routes on "
              "switch 1#########")

    # Verify route 123.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute1, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute1, 'zebra')

    # Verify route 143.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute2, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute2, 'zebra')

    # Verify route 163.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute3, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute3, 'zebra')

    LogOutput('info', "\n\n\n######### Verifying the IPv6 static routes on "
              "switch 1#########")

    # Verify route a234:a234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute1, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute1, 'zebra')

    # Verify route 2234:2234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute2, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute2, 'zebra')

    # Verify route 3234:3234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute3, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute3, 'zebra')

    LogOutput('info', "\n\n\n######### Verification of "
              "IPv4 and IPv6 static routes on switch 1 passed after "
              "restart#########")


# This test restarts zebra process and checks if the routes and next-hops show
# correctly in the output of "show ip route/show rib" after zebra has restarted.
# Before zebra has come back up from restart, we restore interface addresses on
# the interfaces on which we changed the addresses on in the test case
# interface_addr_change_before_zebra_restart.
def interface_addr_restore_before_zebra_restart(**kwargs):

    switch1 = kwargs.get('switch1', None)
    switch2 = kwargs.get('switch2', None)

    switch1.commandErrorCheck = 0
    switch2.commandErrorCheck = 0

    zebra_stop_command_string = "systemctl stop ops-zebra"
    zebra_start_command_string = "systemctl start ops-zebra"

    LogOutput('info', "\n\n\n######### Restarting zebra and restoring "
              " some interface addresses on switch1.#########")

    LogOutput('info', "\n\n\n######### Restarting zebra. Stopping ops-zebra service on"
              "switch 1#########")

    # Execute the command to stop zebra on the Linux bash interface
    devIntRetStruct = switch1.DeviceInteract(command=zebra_stop_command_string)
    retCode = devIntRetStruct.get('returnCode')

    if retCode != 0:
        assert "Failed to stop zebra"

    LogOutput('info', "\n\n\n######### restoring some interface IP addresses"
              " after zebra has gone down on switch 1#########")

    # Re-configure IPv4 address on interface 1 on switch1
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk01'],
                                  addr="1.1.1.1", mask=24, config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to re-configure an ipv4 address"

    # Re-configure IPv6 address on interface 1 on switch1
    retStruct = InterfaceIpConfig(deviceObj=switch1,
                                  interface=switch1.linkPortMapping['lnk01'],
                                  addr="111:111::1", mask=64, ipv6flag=True,
                                  config=True)
    retCode = retStruct.returnCode()
    if retCode != 0:
        assert "Failed to re-configure an ipv6 address"

    LogOutput('info', "\n\n\n######### Restarting zebra. Starting ops-zebra service on"
              "switch 1#########")

    # Execute the command to start zebra on the Linux bash interface
    devIntRetStruct = switch1.DeviceInteract(command=zebra_start_command_string)
    retCode = devIntRetStruct.get('returnCode')

    if retCode != 0:
        assert "Failed to start zebra"

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
    ExpRibDictIpv4StaticRoute1['4.4.4.1'] = dict()
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['Distance'] = '1'
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['Metric'] = '0'
    ExpRibDictIpv4StaticRoute1['4.4.4.1']['RouteType'] = 'static'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 123.0.0.1/32 and its next-hops.
    ExpRouteDictIpv4StaticRoute1 = ExpRibDictIpv4StaticRoute1

    # Populate the version of the route in kernel in the route dictionary
    # for the route 123.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute1 = dict()
    ExpDictIpv4KernelRoute1['Route'] = '123.0.0.1' + '/' + '32'
    ExpDictIpv4KernelRoute1['NumberNexthops'] = '4'
    ExpDictIpv4KernelRoute1['1.1.1.2'] = dict()
    ExpDictIpv4KernelRoute1['1.1.1.2']['Distance'] = ''
    ExpDictIpv4KernelRoute1['1.1.1.2']['Metric'] = ''
    ExpDictIpv4KernelRoute1['1.1.1.2']['RouteType'] = 'zebra'
    ExpDictIpv4KernelRoute1['2'] = dict()
    ExpDictIpv4KernelRoute1['2']['Distance'] = ''
    ExpDictIpv4KernelRoute1['2']['Metric'] = ''
    ExpDictIpv4KernelRoute1['2']['RouteType'] = 'zebra'
    ExpDictIpv4KernelRoute1['3'] = dict()
    ExpDictIpv4KernelRoute1['3']['Distance'] = ''
    ExpDictIpv4KernelRoute1['3']['Metric'] = ''
    ExpDictIpv4KernelRoute1['3']['RouteType'] = 'zebra'
    ExpDictIpv4KernelRoute1['4.4.4.1'] = dict()
    ExpDictIpv4KernelRoute1['4.4.4.1']['Distance'] = ''
    ExpDictIpv4KernelRoute1['4.4.4.1']['Metric'] = ''
    ExpDictIpv4KernelRoute1['4.4.4.1']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 143.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute2 = dict()
    ExpDictIpv4KernelRoute2['Route'] = '143.0.0.1' + '/' + '32'
    ExpDictIpv4KernelRoute2['NumberNexthops'] = '1'
    ExpDictIpv4KernelRoute2['4.4.4.1'] = dict()
    ExpDictIpv4KernelRoute2['4.4.4.1']['Distance'] = ''
    ExpDictIpv4KernelRoute2['4.4.4.1']['Metric'] = ''
    ExpDictIpv4KernelRoute2['4.4.4.1']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 163.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute3 = dict()
    ExpDictIpv4KernelRoute3['Route'] = '163.0.0.1' + '/' + '32'
    ExpDictIpv4KernelRoute3['NumberNexthops'] = '1'
    ExpDictIpv4KernelRoute3['2'] = dict()
    ExpDictIpv4KernelRoute3['2']['Distance'] = ''
    ExpDictIpv4KernelRoute3['2']['Metric'] = ''
    ExpDictIpv4KernelRoute3['2']['RouteType'] = 'zebra'

    # Populate the expected RIB ("show rib") route dictionary for the
    # route a234:a234::1/128 and its next-hops.
    ExpRibDictIpv6StaticRoute1 = dict()
    ExpRibDictIpv6StaticRoute1['Route'] = 'a234:a234::1' + '/' + '128'
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
    # route a234:a234::1/128 and its next-hops.
    ExpRouteDictIpv6StaticRoute1 = ExpRibDictIpv6StaticRoute1

    # Populate the version of the route in kernel in the route dictionary
    # for the route a234:a234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute1 = dict()
    ExpDictIpv6KernelRoute1['Route'] = 'a234:a234::1' + '/' + '128'
    ExpDictIpv6KernelRoute1['NumberNexthops'] = '4'
    ExpDictIpv6KernelRoute1['1'] = dict()
    ExpDictIpv6KernelRoute1['1']['Distance'] = ''
    ExpDictIpv6KernelRoute1['1']['Metric'] = ''
    ExpDictIpv6KernelRoute1['1']['RouteType'] = 'zebra'
    ExpDictIpv6KernelRoute1['2'] = dict()
    ExpDictIpv6KernelRoute1['2']['Distance'] = ''
    ExpDictIpv6KernelRoute1['2']['Metric'] = ''
    ExpDictIpv6KernelRoute1['2']['RouteType'] = 'zebra'
    ExpDictIpv6KernelRoute1['3'] = dict()
    ExpDictIpv6KernelRoute1['3']['Distance'] = ''
    ExpDictIpv6KernelRoute1['3']['Metric'] = ''
    ExpDictIpv6KernelRoute1['3']['RouteType'] = 'zebra'
    ExpDictIpv6KernelRoute1['4'] = dict()
    ExpDictIpv6KernelRoute1['4']['Distance'] = ''
    ExpDictIpv6KernelRoute1['4']['Metric'] = ''
    ExpDictIpv6KernelRoute1['4']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 2234:2234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute2 = dict()
    ExpDictIpv6KernelRoute2['Route'] = '2234:2234::1' + '/' + '128'
    ExpDictIpv6KernelRoute2['NumberNexthops'] = '1'
    ExpDictIpv6KernelRoute2['4'] = dict()
    ExpDictIpv6KernelRoute2['4']['Distance'] = ''
    ExpDictIpv6KernelRoute2['4']['Metric'] = ''
    ExpDictIpv6KernelRoute2['4']['RouteType'] = 'zebra'

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

    # Populate the version of the route in kernel in the route dictionary
    # for the route 3234:3234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute3 = dict()
    ExpDictIpv6KernelRoute3['Route'] = '3234:3234::1' + '/' + '128'
    ExpDictIpv6KernelRoute3['NumberNexthops'] = '1'
    ExpDictIpv6KernelRoute3['2'] = dict()
    ExpDictIpv6KernelRoute3['2']['Distance'] = ''
    ExpDictIpv6KernelRoute3['2']['Metric'] = ''
    ExpDictIpv6KernelRoute3['2']['RouteType'] = 'zebra'

    time.sleep(5)

    LogOutput('info', "\n\n\n######### Verifying the IPv4 static routes on "
              "switch 1#########")

    # Verify route 123.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute1, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute1, 'zebra')

    # Verify route 143.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute2, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute2, 'zebra')

    # Verify route 163.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute3, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute3, 'zebra')

    LogOutput('info', "\n\n\n######### Verifying the IPv6 static routes on "
              "switch 1#########")

    # Verify route a234:a234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute1, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute1, 'zebra')

    # Verify route 2234:2234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute2, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute2, 'zebra')

    # Verify route 3234:3234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute3, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute3, 'zebra')

    LogOutput('info', "\n\n\n######### Verification of "
              "IPv4 and IPv6 static routes on switch 1 passed#########")


def all_configuration_deleted_before_zebra_restart(**kwargs):

    switch1 = kwargs.get('switch1', None)
    switch2 = kwargs.get('switch2', None)

    switch1.commandErrorCheck = 0
    switch2.commandErrorCheck = 0

    zebra_stop_command_string = "systemctl stop ops-zebra"
    zebra_start_command_string = "systemctl start ops-zebra"

    LogOutput('info', "\n\n\n######### Restarting zebra and deleting all"
              " route configuration on switch1.#########")

    LogOutput('info', "\n\n\n######### Restarting zebra. Stopping ops-zebra service on"
              "switch 1#########")

    # Execute the command to stop zebra on the Linux bash interface
    devIntRetStruct = switch1.DeviceInteract(command=zebra_stop_command_string)
    retCode = devIntRetStruct.get('returnCode')

    if retCode != 0:
        assert "Failed to stop zebra"

    # Un-configure IPv4 route 123.0.0.1/32 with 4 ECMP next-hops.
    retStruct = IpRouteConfig(deviceObj=switch1, route="123.0.0.1", mask=32,
                              nexthop="1.1.1.2", config=False)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv4 route"

    retStruct = IpRouteConfig(deviceObj=switch1, route="123.0.0.1", mask=32,
                              nexthop="2", config=False)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv4 route"

    retStruct = IpRouteConfig(deviceObj=switch1, route="123.0.0.1", mask=32,
                              nexthop="3", config=False)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv4 route"

    retStruct = IpRouteConfig(deviceObj=switch1, route="123.0.0.1", mask=32,
                              nexthop="4.4.4.1", config=False)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv4 route"

    # Un-configure IPv4 route 143.0.0.1/32 with 1 next-hop.
    retStruct = IpRouteConfig(deviceObj=switch1, route="143.0.0.1", mask=32,
                              nexthop="4.4.4.1", config=False)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv4 route"

    # Un-configure IPv4 route 163.0.0.1/32 with 1 next-hop.
    retStruct = IpRouteConfig(deviceObj=switch1, route="163.0.0.1", mask=32,
                              nexthop="2", config=False)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv4 route"

    # Un-configure IPv6 route a234:a234::1/128 with 4 ECMP next-hops.
    retStruct = IpRouteConfig(deviceObj=switch1, route="a234:a234::1",
                              mask=128, nexthop="1", config=False,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv6 route"

    retStruct = IpRouteConfig(deviceObj=switch1, route="a234:a234::1",
                              mask=128, nexthop="2", config=False,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv6 route"

    retStruct = IpRouteConfig(deviceObj=switch1, route="a234:a234::1",
                              mask=128, nexthop="3", config=False,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv6 route"

    retStruct = IpRouteConfig(deviceObj=switch1, route="a234:a234::1",
                              mask=128, nexthop="4", config=False,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv6 route"

    # Un-configure IPv6 route 2234:2234::1/128 with 1 next-hop.
    retStruct = IpRouteConfig(deviceObj=switch1, route="2234:2234::1",
                              mask=128, nexthop="4", config=False,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv6 route"

    # Un-configure IPv6 route 3234:3234::1/128 with 1 next-hop.
    retStruct = IpRouteConfig(deviceObj=switch1, route="3234:3234::1",
                              mask=128, nexthop="2", config=False,
                              ipv6flag=True)
    retCode = retStruct.returnCode()
    if retCode:
        assert "Failed to un-configure ipv6 route"

    LogOutput('info', "\n\n\n######### Restarting zebra. Starting ops-zebra service on"
              "switch 1#########")

    # Execute the command to start zebra on the Linux bash interface
    devIntRetStruct = switch1.DeviceInteract(command=zebra_start_command_string)
    retCode = devIntRetStruct.get('returnCode')

    if retCode != 0:
        assert "Failed to start zebra"

    # Populate the expected RIB ("show rib") route dictionary for the route
    # 123.0.0.1/32 and its next-hops.
    ExpRibDictIpv4StaticRoute1 = dict()
    ExpRibDictIpv4StaticRoute1['Route'] = '123.0.0.1' + '/' + '32'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 123.0.0.1/32 and its next-hops.
    ExpRouteDictIpv4StaticRoute1 = ExpRibDictIpv4StaticRoute1

    # Populate the version of the route in kernel in the route dictionary
    # for the route 123.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute1 = dict()
    ExpDictIpv4KernelRoute1['Route'] = '123.0.0.1' + '/' + '32'

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 143.0.0.1/32 and its next-hops.
    ExpRibDictIpv4StaticRoute2 = dict()
    ExpRibDictIpv4StaticRoute2['Route'] = '143.0.0.1' + '/' + '32'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 143.0.0.1/32 and its next-hops.
    ExpRouteDictIpv4StaticRoute2 = ExpRibDictIpv4StaticRoute2

    # Populate the version of the route in kernel in the route dictionary
    # for the route 143.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute2 = dict()
    ExpDictIpv4KernelRoute2['Route'] = '143.0.0.1' + '/' + '32'

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 163.0.0.1/32 and its next-hops.
    ExpRibDictIpv4StaticRoute3 = dict()
    ExpRibDictIpv4StaticRoute3['Route'] = '163.0.0.1' + '/' + '32'

    # Populate the expected FIB ("show ip route") route dictionary for the
    # route 163.0.0.1/32 and its next-hops.
    ExpRouteDictIpv4StaticRoute3 = ExpRibDictIpv4StaticRoute3

    # Populate the version of the route in kernel in the route dictionary
    # for the route 163.0.0.1/32 and its next-hops.
    ExpDictIpv4KernelRoute3 = dict()
    ExpDictIpv4KernelRoute3['Route'] = '163.0.0.1' + '/' + '32'

    # Populate the expected RIB ("show rib") route dictionary for the
    # route a234:a234::1/128 and its next-hops.
    ExpRibDictIpv6StaticRoute1 = dict()
    ExpRibDictIpv6StaticRoute1['Route'] = 'a234:a234::1' + '/' + '128'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route a234:a234::1/128 and its next-hops.
    ExpRouteDictIpv6StaticRoute1 = ExpRibDictIpv6StaticRoute1

    # Populate the version of the route in kernel in the route dictionary
    # for the route a234:a234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute1 = dict()
    ExpDictIpv6KernelRoute1['Route'] = 'a234:a234::1' + '/' + '128'

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 2234:2234::1/128 and its next-hops.
    ExpRibDictIpv6StaticRoute2 = dict()
    ExpRibDictIpv6StaticRoute2['Route'] = '2234:2234::1' + '/' + '128'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 2234:2234::1/128 and its next-hops.
    ExpRouteDictIpv6StaticRoute2 = ExpRibDictIpv6StaticRoute2

    # Populate the version of the route in kernel in the route dictionary
    # for the route 2234:2234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute2 = dict()
    ExpDictIpv6KernelRoute2['Route'] = '2234:2234::1' + '/' + '128'

    # Populate the expected RIB ("show rib") route dictionary for the
    # route 3234:3234::1/128 and its next-hops.
    ExpRibDictIpv6StaticRoute3 = dict()
    ExpRibDictIpv6StaticRoute3['Route'] = '3234:3234::1' + '/' + '128'

    # Populate the expected FIB ("show ipv6 route") route dictionary for the
    # route 3234:3234::1/128 and its next-hops.
    ExpRouteDictIpv6StaticRoute3 = ExpRibDictIpv6StaticRoute3

    # Populate the version of the route in kernel in the route dictionary
    # for the route 3234:3234::1/128 and its next-hops.
    ExpDictIpv6KernelRoute3 = dict()
    ExpDictIpv6KernelRoute3['Route'] = '3234:3234::1' + '/' + '128'

    time.sleep(5)

    LogOutput('info', "\n\n\n######### Verifying the IPv4 static routes on "
              "switch 1#########")

    # Verify route 123.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute1, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute1, 'zebra')

    # Verify route 143.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute2, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute2, 'zebra')

    # Verify route 163.0.0.1/32 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, True, ExpRouteDictIpv4StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv4StaticRoute3, 'static')
    verify_route_in_show_kernel_route(switch1, True,
                                      ExpDictIpv4KernelRoute3, 'zebra')

    LogOutput('info', "\n\n\n######### Verifying the IPv6 static routes on "
              "switch 1#########")

    # Verify route a234:a234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute1,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute1, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute1, 'zebra')

    # Verify route 2234:2234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute2,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute2, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute2, 'zebra')

    # Verify route 3234:3234::1/128 and next-hops in RIB, FIB and verify the
    # presence of all next-hops in running-config
    verify_route_in_show_route(switch1, False, ExpRouteDictIpv6StaticRoute3,
                               'static')
    verify_route_in_show_rib(switch1, ExpRibDictIpv6StaticRoute3, 'static')
    verify_route_in_show_kernel_route(switch1, False,
                                      ExpDictIpv6KernelRoute3, 'zebra')

    LogOutput('info', "\n\n\n######### Configuration and verification of "
              "IPv4 and IPv6 static routes on switch 1 passed#########")


# Set the maximum timeout for all the test cases
@pytest.mark.timeout(5000)


# Test class for testing zebra restartability.
class Test_zebra_restartability:

    def setup_class(cls):
        # Test object will parse command line and formulate the env
        Test_zebra_restartability.testObj = testEnviron(
                                                topoDict=topoDict)
        # Get topology object
        Test_zebra_restartability.topoObj = Test_zebra_restartability.testObj.topoObjGet()

    def teardown_class(cls):
        Test_zebra_restartability.topoObj.terminate_nodes()

    def test_add_static_routes(self):
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        dut02Obj = self.topoObj.deviceObjGet(device="dut02")
        add_static_routes(switch1=dut01Obj, switch2=dut02Obj)

    def test_restart_zebra_without_config_change(self):
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        dut02Obj = self.topoObj.deviceObjGet(device="dut02")
        restart_zebra_without_config_change(switch1=dut01Obj, switch2=dut02Obj)

    def test_restart_zebra_with_config_change(self):
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        dut02Obj = self.topoObj.deviceObjGet(device="dut02")
        restart_zebra_with_config_change(switch1=dut01Obj, switch2=dut02Obj)

    def test_config_change_after_zebra_restart(self):
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        dut02Obj = self.topoObj.deviceObjGet(device="dut02")
        config_change_after_zebra_restart(switch1=dut01Obj, switch2=dut02Obj)

    def test_interface_down_before_zebra_restart(self):
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        dut02Obj = self.topoObj.deviceObjGet(device="dut02")
        interface_down_before_zebra_restart(switch1=dut01Obj, switch2=dut02Obj)

    def test_interface_up_before_zebra_restart(self):
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        dut02Obj = self.topoObj.deviceObjGet(device="dut02")
        interface_up_before_zebra_restart(switch1=dut01Obj, switch2=dut02Obj)

    def test_interface_addr_change_before_zebra_restart(self):
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        dut02Obj = self.topoObj.deviceObjGet(device="dut02")
        interface_addr_change_before_zebra_restart(switch1=dut01Obj, switch2=dut02Obj)

    def test_interface_addr_restore_before_zebra_restart(self):
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        dut02Obj = self.topoObj.deviceObjGet(device="dut02")
        interface_addr_restore_before_zebra_restart(switch1=dut01Obj, switch2=dut02Obj)

    def test_all_configuration_deleted_before_zebra_restart(self):
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        dut02Obj = self.topoObj.deviceObjGet(device="dut02")
        all_configuration_deleted_before_zebra_restart(switch1=dut01Obj, switch2=dut02Obj)
