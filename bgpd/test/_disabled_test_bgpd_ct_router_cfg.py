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

# Disabled since this test is a very basic test for verifying configuration;
# however, Halon currently doesn't support 'show running-config' command.
# Can be enabled and extended later.

#
# Only one switch emulated for testing simple BGP configurations through vtysh.
# This test checks the following commands:
#   * router bgp <asn>
#   * no router bgp <asn>
#
# Topology:
#   S1 [interface 1]
#

BGP_ASN = "1"
NUM_OF_SWITCHES = 1
NUM_HOSTS_PER_SWITCH = 0
SWITCH_PREFIX = "s"

BGP_ROUTER_ID = "9.0.0.1"

class myTopo(Topo):
    def build (self, hsts=0, sws=2, **_opts):

        self.hsts = hsts
        self.sws = sws

        for i in irange(1, sws):
            switch = self.addSwitch("%s%s" % (SWITCH_PREFIX, i))

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
        info("Verifying bgp processes..\n")

        switch = self.net.switches[0]
        pid = switch.cmd("pgrep -f bgpd").strip()
        assert (pid != ""), "bgpd process not running on switch %s" % \
                            switch.name

        info("bgpd process exists on switch %s\n" % switch.name)
        info("\n")

    def configure_bgp (self):
        info("Configuring BGP...\n")

        switch = self.net.switches[0]
        cfg_array = []
        cfg_array.append("router bgp %s" % BGP_ASN)

        # Append network so that we can utilize "sh ip bgp" for verification
        cfg_array.append("bgp router-id %s" % BGP_ROUTER_ID)
        cfg_array.append("network 11.0.0.0/8")

        SwitchVtyshUtils.vtysh_cfg_cmd(switch, cfg_array)

    def unconfigure_bgp (self):
        info("Unconfiguring BGP...\n")

        switch = self.net.switches[0]
        cfg_array = []
        cfg_array.append("no router bgp %s" % BGP_ASN)

        SwitchVtyshUtils.vtysh_cfg_cmd(switch, cfg_array)

    def verify_router_bgp_asn (self):
        info("Verifying BGP configured..\n")

        res = self.does_router_bgp_exist(BGP_ROUTER_ID)
        assert res, "Config \"%s\" not correctly configured!"

        info("Config was correctly configured.\n")
        info("\n")

    def verify_no_router_bgp_asn (self):
        info("Verifying BGP unconfigured..\n")

        res = self.does_router_bgp_exist(BGP_ROUTER_ID)
        assert res == False, "Config was not removed!"

        info("Config was successfully removed.\n")
        info("\n")

    def does_router_bgp_exist (self, val):
        # For now, using verification via "sh ip bgp" command since
        # "sh running-config" is not yet implemented.
        if 0:
            res = self.router_bgp_exists_via_sh_running_config()
        else:
            res = self.router_bgp_exists_via_sh_ip_bgp(val)

        return res

    def router_bgp_exists_via_sh_running_config (self):
        switch = self.net.switches[0]
        res = SwitchVtyshUtils.verify_cfg_exist(switch, ["router bgp"])

        return res

    def router_bgp_exists_via_sh_ip_bgp (self, val):
        switch = self.net.switches[0]

        output = SwitchVtyshUtils.vtysh_cmd(switch, "sh ip bgp")

        # The output should contain information about the router-id if
        # configurations exist
        if output.find(val) >= 0:
            res = True
        else:
            res = False

        return res

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

    def test_bgp_full (self):
        self.test_var.verify_bgp_running()
        self.test_var.configure_bgp()
        self.test_var.verify_router_bgp_asn()
        self.test_var.unconfigure_bgp()
        self.test_var.verify_no_router_bgp_asn()
