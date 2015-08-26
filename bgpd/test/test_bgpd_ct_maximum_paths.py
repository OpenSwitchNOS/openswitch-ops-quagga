#
# !/usr/bin/python
#
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

import os
import sys
import time
import pytest
import subprocess
from halonvsi.docker import *
from halonvsi.halon import *
from halonutils.halonutil import *
from halonvsi.quagga import *
from vtyshutils import *
from bgpconfig import *

# Disabled since this test is a encapsulated by
# test_bgpd_ft_routemaps_with_hosts_ping.py test.

#
# This case tests the most basic configuration between two BGP instances by
# verifying that the advertised routes are received on both instances running
# BGP.
#
# The following commands are tested:
#   * router bgp <asn>
#   * bgp router-id <router-id>
#   * network <network>
#   * neighbor <peer> remote-as <asn>
#
# S1 [interface 1]<--->[interface 1] S2
#
BGP1_ASN            = "1"
BGP1_ROUTER_ID      = "9.0.0.1"
BGP1_NETWORK        = "11.0.0.0"

BGP2_ASN            = "2"
BGP2_ROUTER_ID      = "9.0.0.2"
BGP2_NETWORK        = "12.0.0.0"

BGP3_ASN            = "3"
BGP3_ROUTER_ID      = "9.0.0.3"
BGP3_NETWORK        = "12.0.0.0"

BGP4_ASN            = "4"
BGP4_ROUTER_ID      = "9.0.0.4"
BGP4_NETWORK        = "12.0.0.0"

BGP5_ASN            = "5"
BGP5_ROUTER_ID      = "9.0.0.5"
BGP5_NETWORK        = "12.0.0.0"

# S1 Neighbors
BGP1_NEIGHBOR1       = "10.10.10.2"
BGP1_NEIGHBOR1_ASN   = BGP2_ASN
BGP1_INTF1_IP        = "10.10.10.1"

BGP1_NEIGHBOR2       = "20.20.20.2"
BGP1_NEIGHBOR2_ASN   = BGP3_ASN
BGP1_INTF2_IP        = "20.20.20.1"

BGP1_NEIGHBOR3       = "30.30.30.2"
BGP1_NEIGHBOR3_ASN   = BGP4_ASN
BGP1_INTF3_IP        = "30.30.30.1"

# S2 Neighbors
BGP2_NEIGHBOR1       = "10.10.10.1"
BGP2_NEIGHBOR1_ASN   = BGP1_ASN
BGP2_INTF1_IP        = "10.10.10.2"

BGP2_NEIGHBOR2       = "40.40.40.2"
BGP2_NEIGHBOR2_ASN   = BGP5_ASN
BGP2_INTF2_IP        = "40.40.40.1"

# S3 Neighbors
BGP3_NEIGHBOR1       = "20.20.20.1"
BGP3_NEIGHBOR1_ASN   = BGP1_ASN
BGP3_INTF1_IP        = "20.20.20.2"

BGP3_NEIGHBOR2       = "50.50.50.2"
BGP3_NEIGHBOR2_ASN   = BGP5_ASN
BGP3_INTF2_IP        = "50.50.50.1"

# S4 neighbors
BGP4_NEIGHBOR1       = "30.30.30.1"
BGP4_NEIGHBOR1_ASN   = BGP1_ASN
BGP4_INTF1_IP        = "30.30.30.2"

BGP4_NEIGHBOR2       = "60.60.60.2"
BGP4_NEIGHBOR2_ASN   = BGP5_ASN
BGP4_INTF2_IP        = "60.60.60.1"

# S5 Neighbors
BGP5_NEIGHBOR1       = "40.40.40.1"
BGP5_NEIGHBOR1_ASN   = BGP2_ASN
BGP5_INTF1_IP        = "40.40.40.2"

BGP5_NEIGHBOR2       = "50.50.50.1"
BGP5_NEIGHBOR2_ASN   = BGP3_ASN
BGP5_INTF2_IP        = "50.50.50.2"

BGP5_NEIGHBOR3       = "60.60.60.1"
BGP5_NEIGHBOR3_ASN   = BGP4_ASN
BGP5_INTF3_IP        = "60.60.60.2"

BGP_INTF_IP_ARR = [ [BGP1_INTF1_IP, BGP1_INTF2_IP, BGP1_INTF3_IP],
                    [BGP2_INTF1_IP, BGP2_INTF2_IP],
                    [BGP3_INTF1_IP, BGP3_INTF2_IP],
                    [BGP4_INTF1_IP, BGP4_INTF2_IP],
                    [BGP5_INTF1_IP, BGP5_INTF2_IP, BGP5_INTF3_IP] ]

BGP_NETWORK_PL      = "8"
BGP_NETWORK_MASK    = "255.0.0.0"
BGP_ROUTER_IDS      = [BGP1_ROUTER_ID, BGP2_ROUTER_ID, BGP3_ROUTER_ID, BGP4_ROUTER_ID, BGP5_ROUTER_ID]

BGP_MAX_PATHS = 5

BGP1_CONFIG = ["router bgp %s" % BGP1_ASN,
               "bgp router-id %s" % BGP1_ROUTER_ID,
               "network %s/%s" % (BGP1_NETWORK, BGP_NETWORK_PL),
               "neighbor %s remote-as %s" % (BGP1_NEIGHBOR1, BGP1_NEIGHBOR1_ASN),
               "neighbor %s remote-as %s" % (BGP1_NEIGHBOR2, BGP1_NEIGHBOR2_ASN),
               "neighbor %s remote-as %s" % (BGP1_NEIGHBOR3, BGP1_NEIGHBOR3_ASN),
               "maximum-paths %d" % BGP_MAX_PATHS]

BGP2_CONFIG = ["router bgp %s" % BGP2_ASN,
               "bgp router-id %s" % BGP2_ROUTER_ID,
               #"network %s/%s" % (BGP2_NETWORK, BGP_NETWORK_PL),
               "neighbor %s remote-as %s" % (BGP2_NEIGHBOR1, BGP2_NEIGHBOR1_ASN),
               "neighbor %s remote-as %s" % (BGP2_NEIGHBOR2, BGP2_NEIGHBOR2_ASN)]

BGP3_CONFIG = ["router bgp %s" % BGP3_ASN,
               "bgp router-id %s" % BGP3_ROUTER_ID,
               #"network %s/%s" % (BGP3_NETWORK, BGP_NETWORK_PL),
               "neighbor %s remote-as %s" % (BGP3_NEIGHBOR1, BGP3_NEIGHBOR1_ASN),
               "neighbor %s remote-as %s" % (BGP3_NEIGHBOR2, BGP3_NEIGHBOR2_ASN)]

BGP4_CONFIG = ["router bgp %s" % BGP4_ASN,
               "bgp router-id %s" % BGP4_ROUTER_ID,
               #"network %s/%s" % (BGP4_NETWORK, BGP_NETWORK_PL),
               "neighbor %s remote-as %s" % (BGP4_NEIGHBOR1, BGP4_NEIGHBOR1_ASN),
               "neighbor %s remote-as %s" % (BGP4_NEIGHBOR2, BGP4_NEIGHBOR2_ASN)]

BGP5_CONFIG = ["router bgp %s" % BGP5_ASN,
               "bgp router-id %s" % BGP5_ROUTER_ID,
               "network %s/%s" % (BGP5_NETWORK, BGP_NETWORK_PL),
               "neighbor %s remote-as %s" % (BGP5_NEIGHBOR1, BGP5_NEIGHBOR1_ASN),
               "neighbor %s remote-as %s" % (BGP5_NEIGHBOR2, BGP5_NEIGHBOR2_ASN),
               "neighbor %s remote-as %s" % (BGP5_NEIGHBOR3, BGP5_NEIGHBOR3_ASN)]

BGP_CONFIGS = [BGP1_CONFIG, BGP2_CONFIG, BGP3_CONFIG, BGP4_CONFIG, BGP5_CONFIG]

NUM_OF_SWITCHES = 5
NUM_HOSTS_PER_SWITCH = 0

SWITCH_PREFIX = "s"

class myTopo(Topo):
    def build (self, hsts=0, sws=5, **_opts):

        self.hsts = hsts
        self.sws = sws

        switch = self.addSwitch("%s1" % SWITCH_PREFIX)
        switch = self.addSwitch(name = "%s2" % SWITCH_PREFIX,
                                cls = PEER_SWITCH_TYPE,
                                **self.sopts)
        switch = self.addSwitch(name = "%s3" % SWITCH_PREFIX,
                                cls = PEER_SWITCH_TYPE,
                                **self.sopts)
        switch = self.addSwitch(name = "%s4" % SWITCH_PREFIX,
                                cls = PEER_SWITCH_TYPE,
                                **self.sopts)
        switch = self.addSwitch(name = "%s5" % SWITCH_PREFIX,
                                cls = PEER_SWITCH_TYPE,
                                **self.sopts)

        # Connect the switches
        for i in irange(2, sws-1):
            self.addLink("%s1" % SWITCH_PREFIX,
                         "%s%s" % (SWITCH_PREFIX, i))

        for i in irange(2, sws-1):
            self.addLink("%s5" % SWITCH_PREFIX,
                         "%s%s" % (SWITCH_PREFIX, i))

class bgpTest (HalonTest):
    def setupNet (self):
        self.net = Mininet(topo=myTopo(hsts = NUM_HOSTS_PER_SWITCH,
                                       sws = NUM_OF_SWITCHES,
                                       hopts = self.getHostOpts(),
                                       sopts = self.getSwitchOpts()),
                           switch = SWITCH_TYPE,
                           host = HalonHost,
                           link = HalonLink,
                           controller = None,
                           build = True)

    def configure_switch_ips (self):
        info("\nConfiguring switch IPs..\n")

        i = 0
        for switch in self.net.switches:
            # Configure the IPs between the switches
            j = 1;
            for ip_addr in BGP_INTF_IP_ARR[i]:
                info("BGP_INTF_IP_ARR[%d] : %s\n" % (i, BGP_INTF_IP_ARR[i]))
                info("ip_addr : %s\n" % ip_addr)
                if isinstance(switch, HalonSwitch):
                    #switch.cmd("ovs-vsctl add-vrf-port vrf_default %d" % j)
                    switch.cmdCLI("configure terminal")
                    switch.cmdCLI("interface %d" % j)
                    self.setLogLevel('debug')
                    switch.cmdCLI("ip address %s/%s" % (ip_addr, BGP_NETWORK_PL))
                    switch.cmdCLI("exit")
                    #switch.cmd("/usr/bin/ovs-vsctl set interface %d user_config:admin=up"% j)
                else:
                    switch.setIP(ip=ip_addr, intf="%s-eth%d" % (switch.name,j))
                j += 1
            i += 1


    def verify_bgp_running (self):
        info("\nVerifying bgp processes..\n")

        for switch in self.net.switches:
            pid = switch.cmd("pgrep -f bgpd").strip()
            assert (pid != ""), "bgpd process not running on switch %s" % \
                                switch.name

            info("bgpd process exists on switch %s\n" % switch.name)

        info("\n")

    def configure_bgp (self):
        info("\nConfiguring bgp on all switches..\n")

        i = 0
        for switch in self.net.switches:
            cfg_array = BGP_CONFIGS[i]
            i += 1

            SwitchVtyshUtils.vtysh_cfg_cmd(switch, cfg_array)

    def verify_bgp_routes (self):
        info("\nVerifying bgp routes..\n")

        # Wait some time to let BGP converge
        sleep(BGP_CONVERGENCE_DELAY_S)

        self.verify_bgp_route(self.net.switches[0], BGP2_NETWORK,
                              BGP2_ROUTER_ID)
        self.verify_bgp_route(self.net.switches[0], BGP3_NETWORK,
                              BGP3_ROUTER_ID)
        self.verify_bgp_route(self.net.switches[0], BGP4_NETWORK,
                              BGP4_ROUTER_ID)
        self.verify_bgp_route(self.net.switches[0], BGP5_NETWORK,
                              BGP5_ROUTER_ID)

    def verify_configs (self):
        info("\nVerifying all configurations..\n")

        for i in range(0, len(BGP_CONFIGS)):
            bgp_cfg = BGP_CONFIGS[i]
            switch = self.net.switches[i]

            for cfg in bgp_cfg:
                res = SwitchVtyshUtils.verify_cfg_exist(switch, [cfg])
                assert res, "Config \"%s\" was not correctly configured!" % cfg

    def verify_bgp_route (self, switch, network, next_hop):
        found = SwitchVtyshUtils.verify_bgp_route(switch, network,
                                                  next_hop)

        assert found, "Could not find route (%s -> %s) on %s" % \
                      (network, next_hop, switch.name)

#@pytest.mark.skipif(True, reason="Does not cleanup dockers fully")
class Test_bgp:
    def setup (self):
        pass

    def teardown (self):
        pass

    def setup_class (cls):
        Test_bgp.test_var = bgpTest()

    def teardown_class (cls):
        Test_bgp.test_var.net.stop()

    def setup_method (self, method):
        pass

    def teardown_method (self, method):
        pass

    def __del__ (self):
        del self.test_var

    # the actual test function
    def test_bgp_full (self):
        self.test_var.configure_switch_ips()
        self.test_var.verify_bgp_running()
        self.test_var.configure_bgp()
        # self.test_var.verify_configs()
	#sleep(10000)
        CLI(self.test_var.net)
        self.test_var.verify_bgp_routes()
