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
#   * router bgp <asn> # This is required, for testing the primary case;
#   * bgp router-id <router-id-value>
#
# Topology:
#   S1 [interface 1]
#

BGP_ASN = "1"
BGP_KEEPALIVE_TIMER = 10
BGP_HOLDTIME_TIMER = 30
NUM_OF_SWITCHES = 1
NUM_HOSTS_PER_SWITCH = 0
SWITCH_PREFIX = "s"

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

    def verify_bgp_timers (self):
        config = "timers bgp"
        info("Verifying \"%s\"..\n" % config)

        switch = self.net.switches[0]

        timers = "%d %d" % (BGP_KEEPALIVE_TIMER, BGP_HOLDTIME_TIMER)

        cfg_array = []
        cfg_array.append("router bgp %s" % BGP_ASN)
        cfg_array.append("%s %s" % (config, timers))

        SwitchVtyshUtils.vtysh_cfg_cmd(switch, cfg_array)
        res = SwitchVtyshUtils.verify_cfg_value(switch, [config], timers)
        assert res, "Config \"%s\" was not correctly configured!" % config

        info("Config \"%s\" was correctly configured.\n" % config)
        info("\n")

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

    def test_bgp_full (self):
        self.test_var.verify_bgp_running()
        self.test_var.verify_bgp_timers()
