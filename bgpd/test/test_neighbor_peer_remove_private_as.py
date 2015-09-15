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

#
# This case tests BGP to drop private AS numbers by verifying that the
# advertised routes are not received by BGP with public AS numbers.
#
# The following commands are tested:
#   * neighbor <peer> remove-private-AS
#
# S1 [interface 1]<--->[interface 1] S2 [interface 2]<--->[interface 1] S3
#
BGP1_ASN            = "1"
BGP1_ROUTER_ID      = "9.0.0.1"
BGP1_NETWORK        = "11.0.0.0"

BGP2_ASN            = "2"
BGP2_ROUTER_ID      = "9.0.0.2"
BGP2_NETWORK        = "12.0.0.0"

BGP3_ASN            = "65000"
BGP3_ROUTER_ID      = "29.0.0.3"
BGP3_NETWORK        = "13.0.0.0"

BGP1_NEIGHBOR       = BGP2_ROUTER_ID
BGP1_NEIGHBOR_ASN   = BGP2_ASN

BGP2_NEIGHBOR       = BGP1_ROUTER_ID
BGP2_NEIGHBOR_ASN   = BGP1_ASN

BGP2_NEIGHBOR1       = BGP3_ROUTER_ID
BGP2_NEIGHBOR_ASN1   = BGP3_ASN

BGP3_NEIGHBOR       = "29.0.0.4"
BGP3_NEIGHBOR_ASN   = BGP2_ASN

BGP_NETWORK_PL      = "8"
BGP_NETWORK_MASK    = "255.0.0.0"
BGP_ROUTER_IDS      = [BGP1_ROUTER_ID, BGP2_ROUTER_ID, BGP3_ROUTER_ID]

BGP1_CONFIG = ["router bgp %s" % BGP1_ASN,
               "bgp router-id %s" % BGP1_ROUTER_ID,
               "network %s/%s" % (BGP1_NETWORK, BGP_NETWORK_PL),
               "neighbor %s remote-as %s" % (BGP1_NEIGHBOR, BGP1_NEIGHBOR_ASN)]

BGP2_CONFIG = ["router bgp %s" % BGP2_ASN,
               "bgp router-id %s" % BGP2_ROUTER_ID,
               "network %s/%s" % (BGP2_NETWORK, BGP_NETWORK_PL),
               "neighbor %s remote-as %s" % (BGP2_NEIGHBOR, BGP2_NEIGHBOR_ASN),
               "neighbor %s remote-as %s" % (BGP2_NEIGHBOR1, BGP2_NEIGHBOR_ASN1),
               "neighbor %s remove-private-AS" % BGP2_NEIGHBOR,
               "neighbor %s remove-private-AS" % BGP2_NEIGHBOR]

BGP3_CONFIG = ["router bgp %s" % BGP3_ASN,
               "bgp router-id %s" % BGP3_ROUTER_ID,
               "network %s/%s" % (BGP3_NETWORK, BGP_NETWORK_PL),
               "neighbor %s remote-as %s" % (BGP3_NEIGHBOR, BGP3_NEIGHBOR_ASN)]

BGP_CONFIGS = [BGP1_CONFIG, BGP2_CONFIG, BGP3_CONFIG]

NUM_OF_SWITCHES = 3
NUM_HOSTS_PER_SWITCH = 0

SWITCH_PREFIX = "s"

class myTopo(Topo):
    def build (self, hsts=0, sws=3, **_opts):

        self.hsts = hsts
        self.sws = sws

        switch = self.addSwitch("%s1" % SWITCH_PREFIX)
        switch = self.addSwitch(name = "%s2" % SWITCH_PREFIX,
                                cls = SWITCH_TYPE,
                                **self.sopts)
        switch = self.addSwitch(name = "%s3" % SWITCH_PREFIX,
                                cls = PEER_SWITCH_TYPE,
                                **self.sopts)

        # Connect the switches
        for i in irange(2, sws):
            self.addLink("%s%s" % (SWITCH_PREFIX, i-1),
                         "%s%s" % (SWITCH_PREFIX, i))


class bgpTest (HalonTest):
    def setupNet (self):
        self.net = Mininet(topo=myTopo(hsts = NUM_HOSTS_PER_SWITCH,
                                       sws = NUM_OF_SWITCHES,
                                       hopts = self.getHostOpts(),
                                       sopts = self.getSwitchOpts()),
                                       switch = PEER_SWITCH_TYPE,
                                       host = HalonHost,
                                       link = HalonLink,
                                       controller = None,
                                       build = True)

    def configure_switch_ips (self):
        info("\nConfiguring switch IPs..")

        i = 0
        for switch in self.net.switches:
            # Configure the IPs between the switches
            if isinstance(switch, HalonSwitch):
                switch.cmd("ovs-vsctl add-vrf-port vrf_default 1")
                switch.cmdCLI("configure terminal")
                switch.cmdCLI("interface 1")
                switch.cmdCLI("ip address %s/%s" % (BGP_ROUTER_IDS[i], BGP_NETWORK_PL))
                switch.cmdCLI("exit")
                switch.cmd("/usr/bin/ovs-vsctl set interface 1 user_config:admin=up")
                if i == 1:
                    switch.cmd("ovs-vsctl add-vrf-port vrf_default 2")
                    switch.cmdCLI("configure terminal")
                    switch.cmdCLI("interface 2")
                    switch.cmdCLI("ip address %s/%s" % ("29.0.0.4", BGP_NETWORK_PL))
                    switch.cmdCLI("exit")
                    switch.cmd("/usr/bin/ovs-vsctl set interface 2 user_config:admin=up")
            else:
                switch.setIP(ip=BGP_ROUTER_IDS[i], intf="%s-eth1" % switch.name)
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

    def unconfigure_bgp (self):
        info("Unconfiguring remove private AS for BGP2...\n")

        switch = self.net.switches[1]

        cfg_array = []
        cfg_array.append("router bgp %s" % BGP2_ASN)
        cfg_array.append("no neighbor %s remove-private-AS" % BGP2_NEIGHBOR)

        SwitchVtyshUtils.vtysh_cfg_cmd(switch, cfg_array)

    def verify_neighbor_remove_private_AS (switch, network, next_hop, path):
        routes = SwitchVtyshUtils.vtysh_cmd(switch, "sh ip bgp").split(VTYSH_CR)
        found = False
        for rte in routes:
            # Try to match our advertised route first
            if rte.find(network) >= 0:
                if rte.find(next_hop) >= 0:
                    if rte.find(path) >= 0:
                        found = True
                        break;
        return found

    def verify_neighbor_remove_private_AS (self):
        info("Verifying neighbor peer remove-private AS : positive case\n")
        sleep(50)
        switch = self.net.switches[0]
        found = SwitchVtyshUtils.verify_neighbor_remove_private_AS(switch,
                BGP3_NETWORK, BGP2_ROUTER_ID, BGP3_ASN)
        assert found == False, "Path %s not found on %s" % \
            (BGP3_ASN, switch.name)

    def verify_no_neighbor_remove_private_AS (self):
        info("Verifying no neighbor peer remove-private AS : positive case\n")
        sleep(50)
        switch = self.net.switches[0]
        found = SwitchVtyshUtils.verify_neighbor_remove_private_AS(switch,
                BGP3_NETWORK, BGP2_ROUTER_ID, BGP3_ASN)
        assert found == True, "Path %s not found on %s" % \
            (BGP3_ASN, switch.name)

@pytest.mark.skipif(True, reason="Does not cleanup dockers fully")
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
        self.test_var.verify_neighbor_remove_private_AS()
        self.test_var.unconfigure_bgp()
        self.test_var.verify_no_neighbor_remove_private_AS()
