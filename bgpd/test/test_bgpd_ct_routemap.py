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
# This test checks the following commands:
#   * ip prefix-list <prefix-list-name> seq <seq-num> (permit|deny) <prefix>
#   * route map <route-map-name> permit seq_num
#   *   description <description>
#   *   match ip address prefix-list <prefix-list>
#   *
#   * neighbor <neighbor-router-id> route-map <prefix-list> (in|out)
#
# Topology:
#   S1 [interface 1]<--->[interface 2] S2
#
# Configuration of BGP1:
# ----------------------------------------------------------------------------
# !
# router bgp 1
#  bgp router-id 8.0.0.1
#  network 9.0.0.0/8
#  network 10.0.0.0/8
#  neighbor 8.0.0.2 remote-as 2
#  neighbor 8.0.0.2 route-map BGP1_IN in
# !
# ip prefix-list BGP1_IN seq 5 deny 12.0.0.0/8
# ip prefix-list BGP1_IN seq 10 permit 11.0.0.0/8
# !
# route-map BGP1_IN permit 5
#  description Testing Route Map Description
#  match ip address prefix-list BGP1_IN
#  set metric 1000
# !
#
# Configuration of BGP2:
# ----------------------------------------------------------------------------
# !
# router bgp 2
#  bgp router-id 8.0.0.2
#  network 11.0.0.0/8
#  network 12.0.0.0/8
#  network 13.0.0.0/8
#  neighbor 8.0.0.1 remote-as 1
#  neighbor 8.0.0.1 route-map BGP2_OUT out
# !
# ip prefix-list BGP2_OUT seq 5 deny 13.0.0.0/8
# ip prefix-list BGP2_OUT seq 10 permit 11.0.0.0/8
# !
# route-map BGP2_OUT permit 5
#  description Testing Route Map Description
#  match ip address prefix-list BGP2_OUT
#  set metric 1000
#!
#
# Expected routes of BGP1:
# ----------------------------------------------------------------------------
# BGP table version is 0, local router ID is 8.0.0.1
# Status codes: s suppressed, d damped, h history, * valid, > best, i - internal,
#               r RIB-failure, S Stale, R Removed
# Origin codes: i - IGP, e - EGP, ? - incomplete
#
#    Network          Next Hop            Metric LocPrf Weight Path
# *> 9.0.0.0          0.0.0.0                  0         32768 i
# *> 10.0.0.0         0.0.0.0                  0         32768 i
# *> 11.0.0.0         8.0.0.2               1000             0 2 i
#
# Expected routes of BGP2:
# ----------------------------------------------------------------------------
# BGP table version is 0, local router ID is 8.0.0.2
# Status codes: s suppressed, d damped, h history, * valid, > best, i - internal,
#               r RIB-failure, S Stale, R Removed
# Origin codes: i - IGP, e - EGP, ? - incomplete
#
#    Network          Next Hop            Metric LocPrf Weight Path
# *> 9.0.0.0          8.0.0.1                  0             0 1 i
# *> 10.0.0.0         8.0.0.1                  0             0 1 i
# *> 11.0.0.0         0.0.0.0                  0         32768 i
# *> 12.0.0.0         0.0.0.0                  0         32768 i
# *> 13.0.0.0         0.0.0.0                  0         32768 i


NUM_OF_SWITCHES = 2
NUM_HOSTS_PER_SWITCH = 0
SWITCH_PREFIX = "s"

DEFAULT_PL = "8"
DEFAULT_NETMASK = "255.0.0.0"

class myTopo(Topo):
    def build (self, hsts=0, sws=2, **_opts):
        self.hsts = hsts
        self.sws = sws

        switch = self.addSwitch("%s1" % SWITCH_PREFIX)
        switch = self.addSwitch(name = "%s2" % SWITCH_PREFIX,
                                cls = PEER_SWITCH_TYPE,
                                **self.sopts)

        # Link the switches
        for i in range(1, NUM_OF_SWITCHES):
            self.addLink("%s%s" % (SWITCH_PREFIX, i),
                         "%s%s" % (SWITCH_PREFIX, i+1))

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
        info("\nConfiguring switch IPs..")

        i = 0
        for switch in self.net.switches:
            bgp_cfg = self.bgpConfigArr[i]

            # Configure the IPs between the switches
            if isinstance(switch, HalonSwitch):
                switch.cmd("ovs-vsctl add-vrf-port vrf_default 1")
                switch.cmdCLI("configure terminal")
                switch.cmdCLI("interface 1")
                switch.cmdCLI("ip address %s/%s" % (bgp_cfg.routerid, DEFAULT_PL))
                switch.cmdCLI("exit")
                switch.cmd("/usr/bin/ovs-vsctl set interface 1 user_config:admin=up")
            else:
                switch.setIP(ip=bgp_cfg.routerid, intf="%s-eth1" % switch.name)

            i += 1

    def setup_bgp_config (self):
        info("Setup of BGP configurations...\n")

        # Create BGP configurations
        self.bgpConfig1 = BgpConfig("1", "8.0.0.1", "9.0.0.0")
        self.bgpConfig2 = BgpConfig("2", "8.0.0.2", "11.0.0.0")

        # Add additional network for the BGPs.
        self.bgpConfig1.addNetwork("10.0.0.0")
        self.bgpConfig2.addNetwork("12.0.0.0")
        self.bgpConfig2.addNetwork("13.0.0.0")

        # Add the neighbors for each BGP config
        self.bgpConfig1.addNeighbor(self.bgpConfig2)
        self.bgpConfig2.addNeighbor(self.bgpConfig1)

        self.bgpConfigArr = [self.bgpConfig1, self.bgpConfig2]

        # Configure "deny" for "in" of the second network of BGP2 from BGP1
        neighbor = self.bgpConfig1.neighbors[0]
        network = neighbor.networks[1]
        prefixList = PrefixList("BGP%s_IN" % self.bgpConfig1.asn, 5, "deny",
                                network, DEFAULT_PL)

        self.bgpConfig1.prefixLists.append(prefixList)
        self.bgpConfig1.addRouteMap(neighbor, prefixList, "in",
                                    "permit", "1000")

        # Configure so that the other route can be permitted
        network = neighbor.networks[0]
        prefixList = PrefixList("BGP%s_IN" % self.bgpConfig1.asn, 10, "permit",
                                network, DEFAULT_PL)

        self.bgpConfig1.prefixLists.append(prefixList)

        # Configure so that the third network of BGP2 will not be advertised out
        # to BGP1. Deny "out"
        neighbor = self.bgpConfig2.neighbors[0]
        network = self.bgpConfig2.networks[2]
        prefixList = PrefixList("BGP%s_OUT" % self.bgpConfig2.asn, 5, "deny",
                                network, DEFAULT_PL)

        self.bgpConfig2.prefixLists.append(prefixList)
        self.bgpConfig2.addRouteMap(neighbor, prefixList,
                                    "out", "permit", "1000")

        # Configure so that the other route can be permitted
        network = self.bgpConfig2.networks[0]
        prefixList = PrefixList("BGP%s_OUT" % self.bgpConfig2.asn, 10, "permit",
                                network, DEFAULT_PL)

        self.bgpConfig2.prefixLists.append(prefixList)

    def apply_bgp_config (self):
        info("Applying BGP configurations...\n")
        self.all_cfg_array = []

        i = 0
        for bgp_cfg in self.bgpConfigArr:
            cfg_array = []

            # Add any prefix-lists
            self.add_prefix_list_configs(bgp_cfg, cfg_array)

            # Add route-map configs
            self.add_route_map_configs(bgp_cfg, cfg_array)

            SwitchVtyshUtils.vtysh_cfg_cmd(self.net.switches[i], cfg_array)

            del cfg_array[:]

            # Initiate BGP configuration
            cfg_array.append("router bgp %s" % bgp_cfg.asn)
            cfg_array.append("bgp router-id %s" % bgp_cfg.routerid)

            # Add the networks this bgp will be advertising
            for network in bgp_cfg.networks:
                cfg_array.append("network %s/%s" % (network, DEFAULT_PL))

            # Add the neighbors of this switch
            for neighbor in bgp_cfg.neighbors:
                cfg_array.append("neighbor %s remote-as %s" %
                                 (neighbor.routerid, neighbor.asn))

            # Add the neighbor route-maps configs
            self.add_neighbor_route_map_configs(bgp_cfg, cfg_array)

            SwitchVtyshUtils.vtysh_cfg_cmd(self.net.switches[i], cfg_array)

            # Add the configuration arrays to an array so that it can be used
            # for verification later.
            self.all_cfg_array.append(cfg_array)

            i += 1

    def add_route_map_configs(self, bgp_cfg, cfg_array):
        for routeMap in bgp_cfg.routeMaps:
            prefixList = routeMap[1]
            action = routeMap[3]
            metric = routeMap[4]

            cfg_array.append("route-map %s %s %d" %
                             (prefixList.name, action,
                              prefixList.seq_num))

            cfg_array.append("description Testing Route Map Description")

            cfg_array.append("match ip address prefix-list %s" %
                             prefixList.name)

            cfg_array.append("set metric %s" % metric)

    def add_prefix_list_configs(self, bgp_cfg, cfg_array):
        # Add any prefix-lists
        for prefixList in bgp_cfg.prefixLists:
            cfg_array.append("ip prefix-list %s seq %d %s %s/%s" %
                             (prefixList.name, prefixList.seq_num,
                              prefixList.action, prefixList.network,
                              prefixList.prefixLen))

    def add_neighbor_route_map_configs(self, bgp_cfg, cfg_array):
        # Add the route-maps
        for routeMap in bgp_cfg.routeMaps:
            neighbor = routeMap[0]
            prefixList = routeMap[1]
            dir = routeMap[2]

            cfg_array.append("neighbor %s route-map %s %s" %
                             (neighbor.routerid, prefixList.name, dir))

    def verify_bgp_running (self):
        info("Verifying bgp processes..\n")

        for switch in self.net.switches:
            pid = switch.cmd("pgrep -f bgpd").strip()
            assert (pid != ""), "bgpd process not running on switch %s" % \
                                switch.name

            info("bgpd process exists on switch %s\n" % switch.name)
        info("\n")

    def verify_bgp_configs (self):
        info("Verifying all configurations..\n")

        i = 0
        for switch in self.net.switches:
            bgp_cfg_array = self.all_cfg_array[i]

            for cfg in bgp_cfg_array:
                res = SwitchVtyshUtils.verify_cfg_exist(switch, [cfg])
                assert res, "Config \"%s\" was not correctly configured!" % cfg

            i += 1

    def verify_bgp_routes (self):
        info("Verifying routes...\n")

        # Let BGP converge for a bit..
        sleep(BGP_CONVERGENCE_DELAY_S)

        # For each bgp, verify that it is indeed advertising itself
        self.verify_advertised_routes()

        # For each switch, verify the number of routes received
        self.verify_routes_received()

    def verify_advertised_routes(self):
        info("Verifying advertised routes...\n")

        i = 0
        for bgp_cfg in self.bgpConfigArr:
            switch = self.net.switches[i]

            next_hop = "0.0.0.0"

            for network in bgp_cfg.networks:
                found = SwitchVtyshUtils.verify_bgp_route(switch, network,
                                                          next_hop)

                assert found, "Could not find route (%s -> %s) on %s" % \
                              (network, next_hop, switch.name)

            i += 1

    def verify_routes_received(self):
        info("Verifying routes received...\n")

        i = 0
        for bgp_cfg in self.bgpConfigArr:
            switch = self.net.switches[i]
            neighbor = bgp_cfg.neighbors[0]
            next_hop = neighbor.routerid

            routesReceived = 0
            for network in neighbor.networks:
                found = SwitchVtyshUtils.verify_bgp_route(switch, network,
                                                          next_hop)

                if found:
                    routesReceived += 1

            info(SwitchVtyshUtils.vtysh_cmd(switch, "sh ip bgp"))

            # For bgp 1, should have received 1 route. For bgp 2, should receive
            # both routes.
            successful = False
            if i == 0:
                if routesReceived == 1:
                    successful = True
            else:
                if routesReceived == 2:
                    successful = True

            assert successful, \
                   "Incorrect number of routes (%d) on switch %s" \
                    % (routesReceived, switch.name)

            i += 1

    def verify_metric_value(self):
        info("Verifying set metrics...\n")

        # Verify metric for the expected route for BGP1
        switch = self.net.switches[0]

        # Network 1 of BGP2 is the permitted route
        network = self.bgpConfig2.networks[0]
        next_hop = self.bgpConfig2.routerid
        routemap = self.bgpConfig1.routeMaps[0]
        metric = routemap[4]

        matching = False

        routes = SwitchVtyshUtils.vtysh_cmd(switch, "sh ip bgp").split(VTYSH_CR)

        for rte in routes:
            if rte.find(network) >= 0:
                if rte.find(next_hop) >= 0:
                    info("Found related route with config:\n")
                    info("%s\n" % rte)

                    if rte.find(metric) >= 0:
                        matching = True
                        break;

        assert matching, "Metric not matching for %s" % switch.name

@metricmetricmetricmetricmetricpytest.mark.skipif(True, reason="Does not cleanup dockers fully")
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
        self.test_var.setup_bgp_config()
        self.test_var.configure_switch_ips()
        self.test_var.verify_bgp_running()
        self.test_var.apply_bgp_config()
        # self.test_var.verify_bgp_configs()
        self.test_var.verify_bgp_routes()
        self.test_var.verify_metric_value()
