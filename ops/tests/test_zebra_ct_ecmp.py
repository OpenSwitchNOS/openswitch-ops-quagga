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
    10.1
    H1[h1-eth0]<--->[1]S1[3]<---------------->[1]S4[3]<--->[h3-eth0]H3
                       ||                        ||               70.1
    H2[h2-eth0]<--->[2]S1[4]<---------------->[2]S4
    20.1
    """

    def build(self, hsts=3, sws=2, **_opts):
        self.hsts = hsts
        self.sws = sws

        # Add list of hosts
        for h in irange(1, hsts):
            host = self.addHost('h%s' % h)

        # Add list of switches
        for s in irange(1, sws):
            switch = self.addSwitch('s%s' % s)

        # Add links between nodes based on custom topo
        self.addLink('h1', 's1')
        self.addLink('h2', 's1')
        self.addLink('s1', 's2')
        self.addLink('s1', 's2')
        self.addLink('s2', 'h3')


class ecmpStaticRouteTest(OpsVsiTest):

    def setupNet(self):
        host_opts = self.getHostOpts()
        switch_opts = self.getSwitchOpts()
        ecmp_topo = myTopo(hsts=3, sws=2, hopts=host_opts, sopts=switch_opts)
        self.net = Mininet(ecmp_topo, switch=VsiOpenSwitch,
                           host=Host, link=OpsVsiLink,
                           controller=None, build=True)

        info('\n########## Configuring the topology ##########\n')

    def testSWConfigure(self):
        info('\n########## Configuring Switches ##########\n')
        s1 = self.net.switches[0]
        s2 = self.net.switches[1]
        h1 = self.net.hosts[0]
        h2 = self.net.hosts[1]
        h3 = self.net.hosts[2]

        s1.ovscmd("/usr/bin/ovs-vsctl set interface 1 user_config:admin=up")
        time.sleep(1)
        s1.ovscmd("/usr/bin/ovs-vsctl set interface 2 user_config:admin=up")
        time.sleep(1)
        s1.ovscmd("/usr/bin/ovs-vsctl set interface 3 user_config:admin=up")
        time.sleep(1)
        s1.ovscmd("/usr/bin/ovs-vsctl set interface 4 user_config:admin=up")

        time.sleep(1)
        s2.ovscmd("/usr/bin/ovs-vsctl set interface 1 user_config:admin=up")
        time.sleep(1)
        s2.ovscmd("/usr/bin/ovs-vsctl set interface 2 user_config:admin=up")
        time.sleep(1)
        s2.ovscmd("/usr/bin/ovs-vsctl set interface 3 user_config:admin=up")

        info('admin up configured on switches\n')

        # Configure switch s1
        info('\n########## Configuring SW1 ##########\n')
        s1.cmdCLI("configure terminal")

        # Configure interface 1 on switch s1
        s1.cmdCLI("interface 1")
        s1.cmdCLI("ip address 10.0.10.2/24")
        s1.cmdCLI("exit")

        # Configure interface 2 on switch s1
        s1.cmdCLI("interface 2")
        s1.cmdCLI("ip address 10.0.20.2/24")
        s1.cmdCLI("exit")

        # Configure interface 3 on switch s1
        s1.cmdCLI("interface 3")
        s1.cmdCLI("ip address 10.0.30.1/24")
        s1.cmdCLI("exit")

        # Configure interface 4 on switch s1
        s1.cmdCLI("interface 4")
        s1.cmdCLI("ip address 10.0.40.1/24")
        s1.cmdCLI("exit")

        # Add IPv4 static route on s1 and s2
        s1.cmdCLI("ip route 10.0.70.0/24 10.0.30.2")
        s1.cmdCLI("ip route 10.0.70.0/24 10.0.40.2")

        # Add second ecmp IPv4 static route on s1 and s2
        #s1.cmdCLI("ip route 10.0.70.0/24 10.0.40.2")
        info('sw1 configured\n')

        # Configure switch s2
        s2.cmdCLI("configure terminal")

        # Configure interface 1 on switch s2
        s2.cmdCLI("interface 1")
        s2.cmdCLI("ip address 10.0.30.2/24")
        s2.cmdCLI("exit")

        # Configure interface 2 on switch s2
        s2.cmdCLI("interface 2")
        s2.cmdCLI("ip address 10.0.40.2/24")
        s2.cmdCLI("exit")
        info('sw2 configured\n')

        # Configure interface 3 on switch s4
        s2.cmdCLI("interface 3")
        s2.cmdCLI("ip address 10.0.70.2/24")
        s2.cmdCLI("exit")
        info('sw4 configured\n')

        s2.cmdCLI("ip route 10.0.10.0/24 10.0.30.1")
        s2.cmdCLI("ip route 10.0.10.0/24 10.0.40.1")
        time.sleep(1)
        s2.cmdCLI("ip route 10.0.20.0/24 10.0.30.1")
        s2.cmdCLI("ip route 10.0.20.0/24 10.0.40.1")
        info('static route on sw2 configured\n')

        info('Verify ecmp routes on sw1 and sw4 .....\n')

    def testHostConfigure(self):
        info('\n########## Configuring hosts ##########\n')
        h1 = self.net.hosts[0]
        h2 = self.net.hosts[1]
        h3 = self.net.hosts[2]

        # Configure host 1
        h1.cmd("ip addr add 10.0.10.1/24 dev h1-eth0")
        h1.cmd("ip addr del 10.0.0.1/8 dev h1-eth0")

        info('host1 configured\n')

        # Configure host 2
        h2.cmd("ip addr add 10.0.20.1/24 dev h2-eth0")
        h2.cmd("ip addr del 10.0.0.2/8 dev h2-eth0")

        info('host2 configured\n')

        # Configure host 3
        h3.cmd("ip addr add 10.0.70.1/24 dev h3-eth0")
        h3.cmd("ip addr del 10.0.0.3/8 dev h3-eth0")

        info('host3 configured\n')

        # Add V4 default gateway on hosts h1 and h2
        h1.cmd("ip route add 10.0.30.0/24 via 10.0.10.2")
        h1.cmd("ip route add 10.0.40.0/24 via 10.0.10.2")
        h1.cmd("ip route add 10.0.70.0/24 via 10.0.10.2")

        h2.cmd("ip route add 10.0.30.0/24 via 10.0.20.2")
        h2.cmd("ip route add 10.0.40.0/24 via 10.0.10.2")
        h2.cmd("ip route add 10.0.70.0/24 via 10.0.20.2")

        h3.cmd("ip route add 10.0.10.0/24 via 10.0.70.2")
        h3.cmd("ip route add 10.0.20.0/24 via 10.0.70.2")
        h3.cmd("ip route add 10.0.30.0/24 via 10.0.70.2")
        h3.cmd("ip route add 10.0.40.0/24 via 10.0.70.2")

        info('\n########## Configuration complete ##########\n')

    def testV4(self):
        info('\n########## IPv4 Ping test ##########\n')
        h1 = self.net.hosts[0]
        h2 = self.net.hosts[1]
        h3 = self.net.hosts[2]
        # Ping host3 from host1
        info('\n### Ping host3 from host1 ###\n')
        ret = h1.cmd("ping -c 1 10.0.70.1")

        status = parsePing(ret)

        # return code means whether the test is successful
        if status:
            info('Ping Passed!\n\n')
        else:
            info('Ping Failed!\n\n')
            # return False

        # Ping host3 from host2
        info('\n### Ping host3 from host2 ###\n')
        ret = h2.cmd("ping -c 1 10.0.70.1")

        status = parsePing(ret)

        # return code means whether the test is successful
        if status:
            info('Ping Passed!\n\n')
        else:
            info('Ping Failed!\n\n')

        info('\n########## IPv4 ECMP test completed ##########\n')
        info('\nVerify TCPDUMP on SW2 to confirm ecmp load balance\n')

    def testV4_route_delete(self):
        h1 = self.net.hosts[0]
        h2 = self.net.hosts[1]
        h3 = self.net.hosts[2]
        s1 = self.net.switches[0]

        info('\n######### Verify deletion of IPv4 static routes ##########\n')
        # Ping host3 from host1
        info('\n### Ping host3 from host1 ###\n')
        ret = h1.cmd("ping -c 1 10.0.70.1")

        status = parsePing(ret)

        # return code means whether the test is successful
        if status:
            info('Ping Passed!\n\n')
        else:
            info('Ping Failed!\n\n')

        # Delete IPv4 route on switch1 towards host2 network
        info('\n### Delete ip route on sw1 to h3 network ###\n')
        s1.cmdCLI("configure terminal")
        s1.cmdCLI("no ip route 10.0.70.0/24 10.0.40.2")
        s1.cmdCLI("no ip route 10.0.70.0/24 10.0.30.2")

        # Ping host1 from host2
        time.sleep(3)
        info('\n### Ping host3 from host1, it should fail ###\n')
        ret = h1.cmd("ping -c 1 10.0.30.1")

        status = parsePing(ret)
        # Test successful if ping fails
        if not status:
            info('Success: Ping Failed!\n\n')
        else:
            info('Failed: Ping Successful!\n\n')
            # return False

        info('\n########## IPv4 ECMP route delete test completed ##########\n')


@pytest.mark.skipif(True, reason="Skipping old tests")
class Test_zebra_ecmp_static_routes_ft:

    def setup_class(cls):
        Test_zebra_ecmp_static_routes_ft.test = ecmpStaticRouteTest()

    def teardown_class(cls):
        # Stop the Docker containers, and
        # mininet topology
        Test_zebra_ecmp_static_routes_ft.test.net.stop()

    def test_testSWConfigure(self):
        # Function to configure the topology
        self.test.testSWConfigure()

    def test_testHostConfigure(self):
        # Function to configure the topology
        self.test.testHostConfigure()

    def test_testV4(self):
        # Function to test V4 ping
        self.test.testV4()

    def test_testV4_route_delete(self):
        # Function to test V4 route delete
        self.test.testV4_route_delete()

    def __del__(self):
        del self.test
