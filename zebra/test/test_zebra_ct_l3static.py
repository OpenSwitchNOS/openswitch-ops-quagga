#!/usr/bin/python

# Copyright (C) 2015 Hewlett Packard Enterprise Development LP
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

from mininet.net import *
from mininet.topo import *
from mininet.node import *
from mininet.link import *
from mininet.cli import *
from mininet.log import *
from mininet.util import *
from subprocess import *
from halonvsi.docker import *
from halonvsi.halon import *
from halonutils.halonutil import *
import select

class demoTest( HalonTest ):

    """override the setupNet routine to create custom Topo.
    pass the global variables switch,host,link to mininet topo
    as HalonSwitch,HalonHost,HalonLink
    """

    def setupNet(self):
        self.net = Mininet(topo=SingleSwitchTopo(k=0,
                                                 hopts=self.getHostOpts(),
                                                 sopts=self.getSwitchOpts()),
                                                 switch=HalonSwitch,
                                                 host=HalonHost,
                                                 link=HalonLink, controller=None,
                                                 build=True)

    def test_ipv4(self):
        info("\n=====================================================================\n")
        info("*** Tests To Verify IPv4 Static Routes")
        info("\n=====================================================================\n")
        s1 = self.net.switches[ 0 ]
        intf_check = 0

        s1.cmdCLI("configure terminal")
        time.sleep(1)

        info('---> TEST: To verify correct setting of prefix and ip route\n')
        info('*** CMD: ip route 1.1.1.1/8 2.2.2.2 2 ***\n')
        s1.cmdCLI("ip route 1.1.1.1/8 2.2.2.2 2")
        time.sleep(1)

        info('*** CMD: do show ip route ***\n')
        ret = s1.cmdCLI("do show ip route")
        time.sleep(1)

        if '1.1.1.1/8' in ret and '2.2.2.2' in ret and 'static' in ret and '[2/0]' in ret:
            info('*** CMD_RESULT: ipv4 static route  configured successfully\n\n')
        else:
            assert 0, ('CMD_RESULT: ipv4 static route configuration failed')

        info('---> TEST: To verify correct deletion of ip route\n')
        info('*** CMD: no ip route 1.1.1.1/8 2.2.2.2 2 ***\n')
        s1.cmdCLI("no ip route 1.1.1.1/8 2.2.2.2 2")
        time.sleep(1)
        info('*** CMD: do show ip route ***\n')
        ret = s1.cmdCLI("do show ip route")
        time.sleep(1)

        if 'No ip routes configured' in ret:
            info('*** CMD_RESULT: ipv4 static route  deleted successfully\n\n')
        else:
            assert 0, ('CMD_RESULT: ipv4 static route deletion failed')

        info('---> TEST: To verify correct prefix format\n')
        info('*** CMD: ip route 1.1.1.1 2.2.2.2 2 ***\n')
        s1.cmdCLI("ip route 1.1.1.1 2.2.2.2 2")
        time.sleep(1)
        info('*** CMD: do show ip route ***\n')
        ret = s1.cmdCLI("do show ip route")
        time.sleep(1)

        if 'No ip routes configured' in ret:
            info('*** CMD_RESULT: ipv4 static route  command failure. Test succeeded\n\n')
        else:
            assert 0, ('CMD_RESULT: ipv4 static route command success. Test failed')

        info('---> TEST: To verify correct setting of interface in Nexthop table\n')
        info('*** CMD: interface 2 ***\n')
        s1.cmdCLI("interface 2")
        info('*** CMD: vrf attach vrf_default ***\n')
        s1.cmdCLI("vrf attach vrf_default")
        info('*** CMD: exit ***\n')
        s1.cmdCLI("exit")
        info('*** CMD: ip route 1.1.1.1/8 2 2 ***\n')
        s1.cmdCLI("ip route 1.1.1.1/8 2 2")
        time.sleep(1)
        info('*** CMD: do show ip route ***\n')
        ret = s1.cmdCLI("do show ip route")
        time.sleep(1)

        for index, word in enumerate(ret.split(" ")):
            if index == 13 and word == '2,':
                intf_check = 1

        if intf_check == 1:
            info('*** CMD_RESULT: ipv4 static route  Nexthop interface correct set\n\n')
        else:
            assert 0, ('CMD_RESULT: ipv4 static route Nexthop interface not correctly set')

        info('---> TEST: To verify correct deletion of ip route from Route and Nexthop\n')
        info('*** CMD: no ip route 1.1.1.1/8 2 2 ***\n')
        s1.cmdCLI("no ip route 1.1.1.1/8 2 2")
        time.sleep(1)
        info('*** CMD: do show ip route ***\n')
        ret = s1.cmdCLI("do show ip route")
        time.sleep(1)

        if 'No ip routes configured' in ret:
            info('*** CMD_RESULT: ipv4 static route  deleted successfully\n\n')
        else:
            assert 0, ('CMD_RESULT: ipv4 static route deletion failed')

        info('---> TEST: To verify correct setting of ip address in Nexthop table\n')
        info('*** CMD: ip route 1.1.1.1/8 2.2.2.2 2 ***\n')
        s1.cmdCLI("ip route 1.1.1.1/8 2.2.2.2 2")
        time.sleep(1)
        info('*** CMD: do show ip route ***\n')
        ret = s1.cmdCLI("do show ip route")
        time.sleep(1)

        for index, word in enumerate(ret.split(" ")):
            if index == 13 and word == '2.2.2.2,':
                intf_check = 1

        if intf_check == 1:
            info('*** CMD_RESULT: ipv4 static route  Nexthop IP correctly set\n\n')
        else:
            assert 0, ('CMD_RESULT: ipv4 static route Nexthop IP not correctly set')

        info('---> TEST: To verify correct setting of distance\n')
        info('*** CMD: ip route 1.1.1.1/8 3.3.3.3 3 ***\n')
        s1.cmdCLI("ip route 1.1.1.1/8 3.3.3.3 3")
        time.sleep(1)
        info('*** CMD: do show ip route ***\n')
        ret = s1.cmdCLI("do show ip route")
        time.sleep(1)

        for index, word in enumerate(ret.split(" ")):
            if index == 15 and word == '[3/0]':
                intf_check = 1

        if intf_check == 1:
            info('*** CMD_RESULT: ipv4 static route  distance correctly set\n\n')
        else:
            assert 0, ('CMD_RESULT: ipv4 static route distance not correctly set')

        info('---> TEST: To verify correct setting of default distance\n')
        info('*** CMD: ip route 1.1.1.1/8 4.4.4.4 ***\n')
        s1.cmdCLI("ip route 1.1.1.1/8 4.4.4.4")
        time.sleep(1)
        info('*** CMD: do show ip route ***\n')
        ret = s1.cmdCLI("do show ip route")
        time.sleep(1)

        for index, word in enumerate(ret.split(" ")):
            if index == 15 and word == '[1/0]':
                intf_check = 1

        if intf_check == 1:
            info('*** CMD_RESULT: ipv4 static route  distance correctly set\n\n')
        else:
            assert 0, ('CMD_RESULT: ipv4 static route distance not correctly set')

    def test_ipv6(self):
        info("\n=====================================================================\n")
        info("*** Tests To Verify IPv6 Static Routes")
        info("\n=====================================================================\n")
        s1 = self.net.switches[ 0 ]
        intf_check = 0

        info('---> TEST: To verify correct setting of prefix and ip route\n')
        info('*** CMD: ipv6 route 1001:2001::1/64  1001:2001::2 2 ***\n')
        s1.cmdCLI("ipv6 route 1001:2001::1/64 1001:2001::2 2")
        time.sleep(1)

        info('*** CMD: do show ipv6 route ***\n')
        ret = s1.cmdCLI("do show ipv6 route")
        time.sleep(1)

        if '1001:2001::1/64' in ret and '1001:2001::2' in ret and 'static' in ret and '[2/0]' in ret:
            info('*** CMD_RESULT: ipv6 static route  configured successfully\n\n')
        else:
            assert 0, ('CMD_RESULT: ipv6 static route configuration failed')

        info('---> TEST: To verify correct deletion of ip route\n')
        info('*** CMD: no ipv6 route 1001:2001::1/64 1001:2001::2 2 ***\n')
        s1.cmdCLI("no ipv6 route 1001:2001::1/64 1001:2001::2 2")
        time.sleep(1)
        info('*** CMD: do show ipv6 route ***\n')
        ret = s1.cmdCLI("do show ipv6 route")
        time.sleep(1)

        if 'No ipv6 routes configured' in ret:
            info('*** CMD_RESULT: ipv6 static route  deleted successfully\n\n')
        else:
            assert 0, ('CMD_RESULT: ipv6 static route deletion failed')

        info('---> TEST: To verify correct prefix format\n')
        info('*** CMD: ipv6 route 1001:2001::1 1001:2001::2 2 ***\n')
        s1.cmdCLI("ipv6 route 1001:2001::1 1001:2001::2 2")
        time.sleep(1)
        info('*** CMD: do show ipv6 route ***\n')
        ret = s1.cmdCLI("do show ipv6 route")
        time.sleep(1)

        if 'No ipv6 routes configured' in ret:
            info('*** CMD_RESULT: ipv6 static route  command failure. Test succeeded\n\n')
        else:
            assert 0, ('CMD_RESULT: ipv6 static route command success. Test failed')

        info('---> TEST: To verify correct setting of interface in Nexthop table\n')
        info('*** CMD: ipv6 route 1001:2001::1/64 2 2 ***\n')
        s1.cmdCLI("ipv6 route 1001:2001::1/64 2 2")
        time.sleep(1)
        info('*** CMD: do show ipv6 route ***\n')
        ret = s1.cmdCLI("do show ipv6 route")
        time.sleep(1)

        for index, word in enumerate(ret.split(" ")):
            if index == 13 and word == '2,':
                intf_check = 1

        if intf_check == 1:
            info('*** CMD_RESULT: ipv6 static route  Nexthop interface correct set\n\n')
        else:
            assert 0, ('CMD_RESULT: ipv6 static route Nexthop interface not correctly set')

        info('---> TEST: To verify correct deletion of ipv6 route from Route and Nexthop\n')
        info('*** CMD: no ipv6 route 1001:2001::1/64 2 2 ***\n')
        s1.cmdCLI("no ipv6 route 1001:2001::1/64 2 2")
        time.sleep(1)
        info('*** CMD: do show ipv6 route ***\n')
        ret = s1.cmdCLI("do show ipv6 route")
        time.sleep(1)

        if 'No ipv6 routes configured' in ret:
            info('*** CMD_RESULT: ipv6 static route  deleted successfully\n\n')
        else:
            assert 0, ('CMD_RESULT: ipv6 static route deletion failed')

        info('---> TEST: To verify correct setting of ipv6 address in Nexthop table\n')
        info('*** CMD: ipv6 route 1001:2001::1/64 1001:2001::2 2 ***\n')
        s1.cmdCLI("ipv6 route 1001:2001::1/64 1001:2001::2 2")
        time.sleep(1)
        info('*** CMD: do show ipv6 route ***\n')
        ret = s1.cmdCLI("do show ipv6 route")
        time.sleep(1)

        for index, word in enumerate(ret.split(" ")):
            if index == 13 and word == '1001:2001::1/64,':
                intf_check = 1

        if intf_check == 1:
            info('*** CMD_RESULT: ipv6 static route  Nexthop IP correctly set\n\n')
        else:
            assert 0, ('CMD_RESULT: ipv6 static route Nexthop IP not correctly set')

        info('---> TEST: To verify correct setting of distance\n')
        info('*** CMD: ipv6 route 1001:2001::1/64 1001:3001::3 3 ***\n')
        s1.cmdCLI("ipv6 route 1001:2001::1/64 1001:3001::3 3")
        time.sleep(1)
        info('*** CMD: do show ipv6 route ***\n')
        ret = s1.cmdCLI("do show ipv6 route")
        time.sleep(1)

        for index, word in enumerate(ret.split(" ")):
            if index == 15 and word == '[3/0]':
                intf_check = 1

        if intf_check == 1:
            info('*** CMD_RESULT: ipv6 static route  distance correctly set\n\n')
        else:
            assert 0, ('CMD_RESULT: ipv6 static route distance not correctly set')

        info('---> TEST: To verify correct setting of default distance\n')
        info('*** CMD: ipv6 route 1001:2001::1/64 1001:3001::3 ***\n')
        s1.cmdCLI("ipv6 route 1001:2001::1/64 1001:3001::3")
        time.sleep(1)
        info('*** CMD: do show ipv6 route ***\n')
        ret = s1.cmdCLI("do show ipv6 route")
        time.sleep(1)

        for index, word in enumerate(ret.split(" ")):
            if index == 15 and word == '[1/0]':
                intf_check = 1

        if intf_check == 1:
            info('*** CMD_RESULT: ipv6 static route  distance correctly set\n\n')
        else:
            assert 0, ('CMD_RESULT: ipv6 static route distance not correctly set')

    def test_show_running_config(self):
        info("\n=====================================================================\n")
        info("*** Tests To Verify 'show running-config' for IPv4 and IPv6 Static Routes")
        info("\n=====================================================================\n")
        s1 = self.net.switches[ 0 ]
        intf_check = 0
        clilist = []

        s1.cmdCLI("configure terminal")
        time.sleep(1)
        info('\n***Adding Ipv4 Routes\n')
        info('*** CMD: ip route 10.10.10.10/8 20.20.20.20 ***\n')
        s1.cmdCLI("ip route 10.10.10.10/8 20.20.20.20")
        clilist.append('ip route 10.10.10.10/8 20.20.20.20')
        time.sleep(1)
        info('*** CMD: ip route 30.30.30.30/8 40.40.40.40 15 ***\n')
        s1.cmdCLI("ip route 30.30.30.30/8 40.40.40.40 15")
        clilist.append('ip route 30.30.30.30/8 40.40.40.40 15')
        time.sleep(1)
        s1.cmdCLI("interface 25")
        s1.cmdCLI("vrf attach vrf_default")
        s1.cmdCLI("ip address 50.50.50.60")
        s1.cmdCLI("exit")
        info('*** CMD: ip route 50.50.50.50/8 25***\n')
        s1.cmdCLI("ip route 50.50.50.50/8 25")
        clilist.append('ip route 50.50.50.50/8 25')
        time.sleep(1)
        s1.cmdCLI("interface 26")
        s1.cmdCLI("vrf attach vrf_default")
        s1.cmdCLI("ip address 60.60.60.70")
        s1.cmdCLI("exit")
        info('*** CMD: ip route 60.60.60.60/8 26 26***\n')
        s1.cmdCLI("ip route 60.60.60.60/8 26 26")
        clilist.append('ip route 60.60.60.60/8 26 26')
        time.sleep(1)

        info('\n***Adding Ipv6 Routes\n')
        info('*** CMD: ipv6 route 2001::1/120  2001::2***\n')
        s1.cmdCLI("ipv6 route 2001::1/120 2001::2")
        clilist.append('ipv6 route 2001::1/120 2001::2')
        time.sleep(1)
        info('*** CMD: ipv6 route 2002::1/120  2002::2 12 ***\n')
        s1.cmdCLI("ipv6 route 2002::1/120 2002::2 12")
        clilist.append('ipv6 route 2002::1/120 2002::2 12')
        time.sleep(1)
        s1.cmdCLI("interface 13")
        s1.cmdCLI("vrf attach vrf_default")
        s1.cmdCLI("ipv6 address 2003::2")
        s1.cmdCLI("exit")
        info('*** CMD: ipv6 route 2003::1/120 13  ***\n')
        s1.cmdCLI("ipv6 route 2003::1/120 13")
        clilist.append('ipv6 route 2003::1/120 13')
        time.sleep(1)
        s1.cmdCLI("interface 14")
        s1.cmdCLI("vrf attach vrf_default")
        s1.cmdCLI("ip address 2004::2")
        s1.cmdCLI("exit")
        info('*** CMD: ipv6 route 2004::1/120 14 14  ***\n')
        s1.cmdCLI("ipv6 route 2004::1/120 14 14")
        clilist.append('ipv6 route 2004::1/120 14 14')
        time.sleep(1)

        out = s1.cmdCLI("do show running-config")
        lines = out.split('\n')
        found = 0
        for line in lines:
            if line in clilist:
                found = found + 1

        if found == 8:
            print "\n****** show running-config succss ******\n"
            return True
        else:
            assert 0, "\nERROR: show running-config command failure"

class Test_vtysh_static_routes:

    # Create a test topology.
    test = demoTest()

    def teardown_class(cls):
        # Stop the Docker containers, and
        Test_vtysh_static_routes.test.net.stop()

    def test_ipv4(self):
        self.test.test_ipv4()

    def test_ipv6(self):
        self.test.test_ipv6()

    def test_show_running_config(self):
        self.test.test_show_running_config()
        #CLI(self.test.net)

    def __del__(self):
        del self.test
