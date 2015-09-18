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
# The following commands are tested:
#   * router bgp <asn>
#   * bgp router-id <router-id>
#   * network <network>
#   * no router bgp
#
# S1 [interface 1]
#
BGP_ASN            = "1"
BGP_ROUTER_ID      = "9.0.0.1"
BGP_NETWORK        = "11.0.0.0"
BGP_NEIGHBOR       = "9.0.0.2"
BGP_NEIGHBOR_ASN   = "2"
BGP_NETWORK_PL      = "8"
BGP_NETWORK_MASK    = "255.0.0.0"

BGP_CONFIG = ["router bgp %s" % BGP_ASN,
              "bgp router-id %s" % BGP_ROUTER_ID,
              "network %s/%s" % (BGP_NETWORK, BGP_NETWORK_PL)]

NUM_OF_SWITCHES = 1
NUM_HOSTS_PER_SWITCH = 0

SWITCH_PREFIX = "s"

class myTopo(Topo):
    def build (self, hsts=0, sws=1, **_opts):

        self.hsts = hsts
        self.sws = sws

        switch = self.addSwitch("%s1" % SWITCH_PREFIX)

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

    def verify_bgp_running (self):
        info("\n########## Verifying bgp processes.. ##########\n")

        switch = self.net.switches[0]

        pid = switch.cmd("pgrep -f bgpd").strip()
        assert (pid != ""), "bgpd process not running on switch"

        info("### bgpd process exists on switch ###\n")

    def configure_bgp (self):
        info("\n########## Applying BGP configurations... ##########\n")

        switch = self.net.switches[0]

        info("### Applying BGP config ###\n")
        SwitchVtyshUtils.vtysh_cfg_cmd(switch, BGP_CONFIG)

    def configure_neighbor (self):
        info("\n########## Configuring a neighbor ##########\n")

        switch = self.net.switches[0]

        cfg_array = []
        cfg_array.append("router bgp %s" % BGP_ASN)
        cfg_array.append("neighbor %s remote-as %s" % (BGP_NEIGHBOR,
                                                       BGP_NEIGHBOR_ASN))

        SwitchVtyshUtils.vtysh_cfg_cmd(switch, cfg_array)

    def unconfigure_bgp (self):
        info("\n########## Unconfiguring BGP... ##########\n")

        switch = self.net.switches[0]

        cfg_array = []
        cfg_array.append("no router bgp %s" % BGP_ASN)

        SwitchVtyshUtils.vtysh_cfg_cmd(switch, cfg_array)

    def verify_configs (self):
        info("\n########## Verifying all configurations.. ##########\n")

        bgp_cfg = BGP_CONFIG
        switch = self.net.switches[0]

        for cfg in bgp_cfg:
            res = SwitchVtyshUtils.verify_cfg_exist(switch, [cfg])
            assert res, "Config \"%s\" was not correctly configured!" % cfg

    def verify_bgp_route (self):
        info("\n########## Verifying route exists ##########\n")

        network = BGP_NETWORK
        next_hop = "0.0.0.0"
        switch = self.net.switches[0]
        found = SwitchVtyshUtils.wait_for_route(switch,
                                                network, next_hop)

        assert found, "Could not find route (%s -> %s) on %s" % \
                      (network, next_hop, switch.name)

    def verify_bgp_route_removed (self):
        info("\n########## Verifying route removed ##########\n")

        verify_route_exists = False
        network = BGP_NETWORK
        next_hop = "0.0.0.0"
        switch = self.net.switches[0]
        found = SwitchVtyshUtils.wait_for_route(switch,
                                                network, next_hop,
                                                verify_route_exists)

        assert not found, "Route still exists (%s -> %s) on %s" % \
                          (network, next_hop, switch.name)

@pytest.mark.skipif(True, reason="Disabled until no router bgp works")
class Test_bgpd_router_bgp:
    def setup (self):
        pass

    def teardown (self):
        pass

    def setup_class (cls):
        Test_bgpd_router_bgp.test_var = bgpTest()

    def teardown_class (cls):
        Test_bgpd_router_bgp.test_var.net.stop()

    def setup_method (self, method):
        pass

    def teardown_method (self, method):
        pass

    def __del__ (self):
        del self.test_var

    def test_bgp_full (self):
        self.test_var.verify_bgp_running()
        self.test_var.configure_bgp()
        self.test_var.verify_configs()
        self.test_var.verify_bgp_route()
        self.test_var.unconfigure_bgp()
        self.test_var.verify_bgp_route_removed()
        self.test_var.configure_bgp()
        self.test_var.configure_neighbor()
        self.test_var.verify_bgp_route()
        self.test_var.verify_bgp_route_removed()
