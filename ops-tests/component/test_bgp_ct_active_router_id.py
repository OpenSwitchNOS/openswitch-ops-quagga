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


def test_bgp_ct_active_router_id(topology, step):
    sw1 = topology.get("sw1")
    assert sw1 is not None
    bgp_asn = "10"
    bgp_interface1 = "9.0.0.1"
    bgp_interface2 = "9.0.0.2"
    bgp_network = "11.0.0.0"
    bgp_pl = "8"

    step("1-Verifying bgp processes...")
    pid = sw1("pgrep -f bgpd", shell='bash')
    pid = pid.strip()
    assert pid != "" and pid is not None

    step("2-Applying BGP configurations without router id")
    sw1("configure terminal")
    sw1("router bgp {}".format(bgp_asn))
    sw1("network {}/{}".format(bgp_network, bgp_pl))
    sw1("exit")
    sw1("interface 1")
    sw1("no shutdown")
    sw1("ip address {}/{}".format(bgp_interface1, bgp_pl))
    sw1("exit")
    sw1("interface 2")
    sw1("no shutdown")
    sw1("ip address {}/{}".format(bgp_interface2, bgp_pl))
    sw1("exit")
    sw1("end")

    bgp_router_id1 = "9.0.0.1"
    bgp_router_id2 = "9.0.0.2"
    step("3-Verifying BGP Router-ID is one of the interface ip")
    output = sw1("show ip bgp summary")
    assert bgp_router_id1 in output or bgp_router_id2 in output

    step("4-Verify removing interface changes the BGP router-id")
    sw1("configure terminal")
    sw1("interface 1")
    sw1("shutdown")
    sw1("no ip address {}/{}".format(bgp_interface1, bgp_pl))
    sw1("exit")
    sw1("end")
    output = sw1("show ip bgp summary")
    assert bgp_router_id2 in output

    step("5-Verify configuring BGP router-id gets more precedence")
    user_cfg_bgp_router_id = "9.0.0.3"
    sw1("configure terminal")
    sw1("router bgp {}".format(bgp_asn))
    sw1("bgp router-id {}".format(user_cfg_bgp_router_id))
    sw1("exit")
    sw1("end")
    output = sw1("show ip bgp summary")
    assert user_cfg_bgp_router_id in output

    step("6-Verify unconfiguring BGP router-id sets it to null")
    sw1("configure terminal")
    sw1("router bgp {}".format(bgp_asn))
    sw1("no bgp router-id")
    sw1("exit")
    sw1("end")
    output = sw1("show ip bgp summary")
    assert "0.0.0.0" in output
