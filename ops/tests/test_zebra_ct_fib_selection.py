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

from opsvsi.docker import *
from opsvsi.opsvsitest import *
from opsvsiutils.systemutil import *
import pytest


class myTopo(Topo):
    """Custom Topology Example
        [2]S1[1]<--->[1]S2[2]
    """

    def build(self, hsts=0, sws=2, **_opts):
        self.sws = sws

        # Add list of switches
        for s in irange(1, sws):
            switch = self.addSwitch('s%s' % s)

        # Add links between nodes based on custom topo
        self.addLink('s1', 's2')


class fibSelectionCTTest(OpsVsiTest):

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
        s1 = self.net.switches[0]
        s2 = self.net.switches[1]

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

        # Add IPv4 static route on s1 and s2
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
        s1 = self.net.switches[0]
        s2 = self.net.switches[1]

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


@pytest.mark.skipif(True, reason="Skipping old tests")
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

    def __del__(self):
        del self.test
