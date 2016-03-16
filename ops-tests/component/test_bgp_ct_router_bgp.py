# -*- coding: utf-8 -*-

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

from time import sleep

TOPOLOGY = """
# +-------+
# |       |     +-------+
# |  hsw1  <----->  sw1  |
# |       |     +-------+
# +-------+

# Nodes
[type=openswitch name="Switch 1"] sw1
[type=host name="Host 1"] hsw1

# Links
hsw1:if01 -- sw1:if01
"""


def test_bgp_ct_router_bgp(topology, step):
    sw1 = topology.get("sw1")
    assert sw1 is not None
    bgp_asn = "1"
    bgp_router_id = "9.0.0.1"
    bgp_network = "11.0.0.0"
    bgp_neighbor = "9.0.0.2"
    bgp_neighbor_asn = "2"
    bgp_network_pl = "8"
    bgp_config = ["router bgp {}".format(bgp_asn),
                  "bgp router-id {}".format(bgp_router_id),
                  "network {}/{}".format(bgp_network, bgp_network_pl),
                  "neighbor {} remote-as {}".format(bgp_neighbor,
                                                    bgp_neighbor_asn)]
    step("1-Verifying bgp processes...")
    pid = sw1("pgrep -f bgpd", shell='bash')
    pid = pid.strip()
    assert pid != "" and pid is not None
    step("2-Applying BGP configurations...")
    sw1("configure terminal")
    for config in bgp_config:
        sw1(config)
    step("3-Verifying all the BGP configurations...")
    output = sw1("do show running-config")
    for config in bgp_config:
        assert config in output
    step("4-Verifying routes...")
    next_hop = "0.0.0.0"
    route_exists = False
    route_max_wait_time = 300
    output = sw1("do show ip bgp")
    while route_max_wait_time > 0 and not route_exists:
        lines = output.split("\n")
        for line in lines:
            if bgp_network in line and next_hop in line:
                print("Line:", line)
                route_exists = True
                break
        sleep(1)
        route_max_wait_time -= 1
        print("Wait time:", route_max_wait_time)
    assert route_exists
    step("5-Unconfiguring bgp network")
    sw1("no network {}/{}".format(bgp_network, bgp_network_pl))
    step("6-Verifying routes removed...")
    route_exists = True
    route_max_wait_time = 300
    output = sw1("do show ip bgp")
    while route_max_wait_time > 0 and route_exists:
        lines = output.split("\n")
        for line in lines:
            if bgp_network in line and next_hop in line:
                print("Line:", line)
                break
        else:
            route_exists = False
        sleep(1)
        route_max_wait_time -= 1
        print("Wait time:", route_max_wait_time)
    assert not route_exists
