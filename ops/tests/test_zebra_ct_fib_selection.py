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

from opsvsi.docker import *
from opsvsi.opsvsitest import *
from opsvsiutils.systemutil import *

class myTopo( Topo ):
    """Custom Topology Example
        [2]S1[1]<--->[1]S2[2]
    """

    def build(self, hsts=0, sws=2, **_opts):
        self.sws = sws

        #Add list of switches
        for s in irange(1, sws):
            switch = self.addSwitch( 's%s' %s)

        #Add links between nodes based on custom topo
        self.addLink('s1', 's2')

class fibSelectionCTTest( OpsVsiTest ):

    def setupNet(self):
        host_opts = self.getHostOpts()
        switch_opts = self.getSwitchOpts()
        fib_topo = myTopo(hsts=0, sws=2, hopts=host_opts, sopts=switch_opts)
        self.net = Mininet(fib_topo, switch=VsiOpenSwitch,
                           host=Host, link=OpsVsiLink,
                           controller=None, build=True)

    def testConfigure(self):
        info('\n########## Test zebra selection of fib routes ##########\n')
        info('\n### Configuring the topology ###\n')
        s1 = self.net.switches[ 0 ]
        s2 = self.net.switches[ 1 ]

        # Configure switch s1
        s1.cmdCLI("configure terminal")

        # Configure interface 1 on switch s1
        s1.cmdCLI("interface 1")
        s1.cmdCLI("ip address 10.0.10.1/24")
        s1.cmdCLI("ipv6 address 2000::1/120")
        s1.cmdCLI("exit")

        # Configure interface 2 on switch s1
        s1.cmdCLI("interface 2")
        s1.cmdCLI("ip address 10.0.20.1/24")
        s1.cmdCLI("ipv6 address 2001::1/120")
        s1.cmdCLI("exit")

        info('### Switch s1 configured ###\n')

        # Configure switch s2
        s2.cmdCLI("configure terminal")

        # Configure interface 1 on switch s2
        s2.cmdCLI("interface 1")
        s2.cmdCLI("ip address 10.0.10.2/24")
        s2.cmdCLI("ipv6 address 2000::2/120")
        s2.cmdCLI("exit")

        # Configure interface 2 on switch s2
        s2.cmdCLI("interface 2")
        s2.cmdCLI("ip address 10.0.30.1/24")
        s2.cmdCLI("ipv6 address 2002::1/120")
        s2.cmdCLI("exit")

        info('### Switch s2 configured ###\n')

        #Add IPv4 static route on s1 and s2
        s1.cmdCLI("ip route 10.0.30.0/24 10.0.10.2")
        s2.cmdCLI("ip route 10.0.20.0/24 10.0.10.1")

        # Add IPv6 static route on s1 and s2
        s1.cmdCLI("ipv6 route 2002::0/120 2000::2")
        s2.cmdCLI("ipv6 route 2001::0/120 2000::1")

        info('### Static routes configured on s1 and s2 ###\n')

        s1.ovscmd("/usr/bin/ovs-vsctl set interface 1 user_config:admin=up")
        s1.ovscmd("/usr/bin/ovs-vsctl set interface 2 user_config:admin=up")

        s2.ovscmd("/usr/bin/ovs-vsctl set interface 1 user_config:admin=up")
        s2.ovscmd("/usr/bin/ovs-vsctl set interface 2 user_config:admin=up")

        info('### Configuration on s1 and s2 complete ###\n')

    def testFibSelection(self):
        info('\n\n### Verify static routes are selected for fib ###\n')
        s1 = self.net.switches[ 0 ]
        s2 = self.net.switches[ 1 ]

        # Parse the "ovsdb-client dump" output and extract the lines between
        # "Route table" and "Route_Map table". This section will have all the
        # Route table entries. Then parse line by line to match the contents
        dump = s1.cmd("ovsdb-client dump")
        lines = dump.split('\n')
        check = False
        for line in lines:
            if check:
                if ('static' in line and 'unicast' in line and
                '10.0.30.0/24' in line and 'true' in line):
                    print '\nIPv4 route selected for FIB. Success!\n'
                    print line
                    print '\n'
                elif ('static' in line and 'unicast' in line and
                '10.0.30.0/24' in line):
                    print line
                    assert 0, 'IPv4 route selection failed'
                elif ('static' in line and 'unicast' in line and
                '2002::/120' in line and 'true' in line):
                    print '\nIPv6 route selected for FIB. Success!\n'
                    print line
                    print '\n'
                elif ('static' in line and 'unicast' in line
                and '2002::/120' in line):
                    print line
                    assert 0, 'IPv6 route selection failed'
            if 'Route table' in line:
                check = True
            if 'Route_Map table' in line:
                check = False

        info('########## Test Passed ##########\n')

class Test_zebra_fib_selection:

    def setup_class(cls):
        Test_zebra_fib_selection.test = fibSelectionCTTest()

    def teardown_class(cls):
        # Stop the Docker containers, and
        # mininet topology
        Test_zebra_fib_selection.test.net.stop()

    def test_testConfigure(self):
        # Function to configure the topology
        self.test.testConfigure()

    def test_testZebra(self):
        # Function to test zebra fib selection
        self.test.testFibSelection()
        #CLI(self.test.net)

    def __del__(self):
        del self.test
