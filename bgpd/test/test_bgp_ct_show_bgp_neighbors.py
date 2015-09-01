
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
#
# This test configures a bgp neighbor in a bgp router
# and verifies its existence and its configuration as
# it gets updated from the daemon side.
# The CLI creates the basic object but the daemon sets
# some state & statistics values.  The test verifies that this
# happens properly.
#
# We need only one switch for this test.
#

BGP_ROUTER_ASN =                "1"
BGP_NEIGHBOR_IPADDR =           "1.1.1.1"
BGP_NEIGHBOR_REMOTE_AS =        "1111"

BGP_NEIGHBOR_CONFIG = ["router bgp %s" % BGP_ROUTER_ASN,
                       "neighbor %s remote-as %s" \
                            % (BGP_NEIGHBOR_IPADDR, BGP_NEIGHBOR_REMOTE_AS)]

NO_BGP_NEIGHBOR_CONFIG = ["router bgp %s" % BGP_ROUTER_ASN,
                          "no neighbor %s" % BGP_NEIGHBOR_IPADDR]

SHOW_BGP_NEIGHBORS = "show bgp neighbors"

class myTopo(Topo):

    def build (self, hsts=0, sws=1, **_opts):
        self.hsts = hsts
        self.sws = sws
        self.switch = self.addSwitch("1")

class showBgpNeighborTest (HalonTest):

    def setupNet (self):
        self.net = Mininet(topo=myTopo(hsts = 0, sws = 1,
                                       hopts = self.getHostOpts(),
                                       sopts = self.getSwitchOpts()),
                                       switch = HalonSwitch,
                                       host = HalonHost,
                                       link = HalonLink,
                                       controller = None,
                                       build = True)
        self.switch = self.net.switches[0]

    def verify_neighbor_exists (self, show_output):
        if ((BGP_NEIGHBOR_IPADDR in show_output) and
            (BGP_NEIGHBOR_REMOTE_AS in show_output) and
            ("tcp_port_number" in show_output) and
            ("bgp-peer-keepalive_in-count" in show_output)):
                return True
        return False

    def add_bgp_neighbor_to_switch (self):
        info("\nsetting up switch with very basic BGP configuration\n")
        SwitchVtyshUtils.vtysh_cfg_cmd(self.switch, BGP_NEIGHBOR_CONFIG)
        info("switch configuration complete\n")

    def verify_bgp_neighbor_exists (self):
        info("verifying that the configured bgp neighbor exists\n")
        show_output = SwitchVtyshUtils.vtysh_cmd(self.switch, SHOW_BGP_NEIGHBORS)
        if (self.verify_neighbor_exists(show_output)):
                info("1st test passed\n")
        else:
            assert 0, "bgp neighbor does NOT exist"

    def delete_bgp_neighbor_from_switch (self):
        info("deleting bgp neighbor from the switch\n")
        SwitchVtyshUtils.vtysh_cfg_cmd(self.switch, NO_BGP_NEIGHBOR_CONFIG)

    def verify_bgp_neighbor_deleted (self):
        info("verifying that the previously configured bgp neighbor does NOT exist\n")
        show_output = SwitchVtyshUtils.vtysh_cmd(self.switch, SHOW_BGP_NEIGHBORS)
        if (self.verify_neighbor_exists(show_output)):
            assert 0, "bgp neighbor DOES exist"
        info("2nd test passed\n")
        info("all tests successfully passed\n")

#
# final "Test_" class
#
class Test_show_bgp_neighbor:

    # Create the Mininet topology based on mininet.
    test_var = showBgpNeighborTest()

    def setup (self):
        pass

    def teardown (self):
        pass

    def setup_class (cls):
        pass

    def teardown_class (cls):
        Test_show_bgp_neighbor.test_var.net.stop()

    def setup_method (self, method):
        pass

    def teardown_method (self, method):
        pass

    def __del__ (self):
        del self.test_var

    # the actual test function
    def test_show_bgp_neighbor (self):
        self.test_var.add_bgp_neighbor_to_switch()
        self.test_var.verify_bgp_neighbor_exists()
        self.test_var.delete_bgp_neighbor_from_switch()
        self.test_var.verify_bgp_neighbor_deleted()
