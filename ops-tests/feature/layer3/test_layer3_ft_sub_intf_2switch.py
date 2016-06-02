# -*- coding: utf-8 -*-

# (c) Copyright 2015 Hewlett Packard Enterprise Development LP
#
# GNU Zebra is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2, or (at your option) any
# later version.
#
# GNU Zebra is distributed in the hope that it will be useful, but
# WITHoutput ANY WARRANTY; withoutput even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Zebra; see the file COPYING.  If not, write to the Free
# Software Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.

from time import sleep

# Topology definition. the topology contains two back to back switches
# having four links between them.


TOPOLOGY = """
# +-------+
# |  sw1  |
# +---^---+
#     |
#     |
# +---v---+       +-------+
# |  sw2  <------->  hs1  |
# +---^---+       +-------+
#     |
#     |
# +---v---+
# |  hs2  |
# +-------+

# Nodes
[type=openswitch name="Switch 1"] sw1
[type=openswitch name="Switch 2"] sw2
[type=host name="Host 1"] hs1
[type=host name="Host 2"] hs2

# Links
sw1:if01 -- sw2:if01
sw2:if02 -- hs1:eth1
sw2:if03 -- hs2:eth1
"""


def l3_route(**kwargs):
    sw1 = kwargs.get('sw1', None)
    sw2 = kwargs.get('sw2', None)
    hs1 = kwargs.get('hs1', None)
    hs2 = kwargs.get('hs2', None)
    step = kwargs.get('step', None)

    with sw1.libs.vtysh.ConfigInterface("if01") as cnf:
        cnf.no_shutdown()
        cnf.ip_address("20.0.1.2/24")

    with sw1.libs.vtysh.ConfigSubinterface("if01", "100") as cnf:
        cnf.no_shutdown()
        cnf.ip_address("192.168.1.2/24")
        cnf.encapsulation_dot1_q("100")

    with sw1.libs.vtysh.ConfigSubinterface("if01", "200") as cnf:
        cnf.no_shutdown()
        cnf.ip_address("182.158.1.2/24")
        cnf.encapsulation_dot1_q("200")

    with sw2.libs.vtysh.ConfigInterface("if01") as cnf:
        cnf.no_shutdown()

    with sw2.libs.vtysh.ConfigVlan("100") as cnf:
        cnf.no_shutdown()

    with sw2.libs.vtysh.ConfigVlan("200") as cnf:
        cnf.no_shutdown()

    with sw2.libs.vtysh.ConfigInterface("if01") as cnf:
        cnf.no_routing()
        cnf.vlan_trunk_allowed("100")
        cnf.vlan_trunk_allowed("200")

    with sw2.libs.vtysh.ConfigInterface("if02") as cnf:
        cnf.no_shutdown()

    with sw2.libs.vtysh.ConfigInterface("if03") as cnf:
        cnf.no_shutdown()

    with sw2.libs.vtysh.ConfigInterface("if02") as cnf:
        cnf.no_routing()
        cnf.vlan_access("100")

    with sw2.libs.vtysh.ConfigInterface("if03") as cnf:
        cnf.no_routing()
        cnf.vlan_access("200")

    hs1.libs.ip.interface("eth1", "192.168.1.1/24", up=True)
    # configure Ip on the host
    hs1.libs.ip.add_route("182.158.1.0/24", "192.168.1.2")

    hs2.libs.ip.interface("eth1", "182.158.1.1/24", up=True)
    hs2.libs.ip.add_route("192.168.1.0/24", "182.158.1.2")

    step("Pinging between workstation1 and sw1")

    hs1.libs.ping.ping(1, "182.158.1.1")
    sleep(15)
    output = hs1.libs.ping.ping(10, "182.158.1.1")

    step("IPv4 Ping from workstation 1 to sw1 return JSON:\n" + str(output))

    assert output['transmitted'] == 10 and output['received'] >= 7


def device_clean_up(**kwargs):
    sw1 = kwargs.get('sw1', None)
    sw2 = kwargs.get('sw2', None)
    hs1 = kwargs.get('hs1', None)
    hs2 = kwargs.get('hs2', None)
    step = kwargs.get('step', None)

    with sw1.libs.vtysh.ConfigSubinterface("if01", "100") as cnf:
        cnf.shutdown()
        cnf.no_ip_address("192.168.1.2/24")
        cnf.no_encapsulation_dot1_q("100")

    with sw1.libs.vtysh.ConfigSubinterface("if01", "200") as cnf:
        cnf.shutdown()
        cnf.no_ip_address("182.158.1.2/24")
        cnf.no_encapsulation_dot1_q("200")

    step("vlan reconfiguring ")
    with sw2.libs.vtysh.Configure() as cnf:
        cnf.no_vlan("100")
        cnf.no_vlan("200")

    with sw2.libs.vtysh.ConfigInterface("if01") as cnf:
        cnf.no_routing()
        cnf.no_vlan_trunk_allowed("100")
        cnf.no_vlan_trunk_allowed("200")

    with sw2.libs.vtysh.ConfigInterface("if02") as cnf:
        cnf.shutdown()
        cnf.no_routing()
        cnf.no_vlan_access("100")

    with sw2.libs.vtysh.ConfigInterface("if03") as cnf:
        cnf.shutdown()
        cnf.no_routing()
        cnf.no_vlan_access("200")

    # configure Ip on the host
    hs1.libs.ip.interface("eth1", "192.168.1.1/24", up=False)

    hs2.libs.ip.interface("eth1", "182.158.1.1/24", up=False)


def test_layer3_ft_sub_intf_2switch(topology, step):
    sw1 = topology.get("sw1")
    assert sw1 is not None
    sw2 = topology.get("sw2")
    assert sw2 is not None
    hs1 = topology.get("hs1")
    assert hs1 is not None
    hs2 = topology.get("hs2")
    assert hs2 is not None
    l3_route(sw1=sw1, sw2=sw2, hs1=hs1, hs2=hs2, step=step)


def t_device_clean_up(topology, step):
    step("Reverting the configuration")
    sw1 = topology.get("sw1")
    assert sw1 is not None
    sw2 = topology.get("sw2")
    assert sw2 is not None
    hs1 = topology.get("hs1")
    assert hs1 is not None
    hs2 = topology.get("hs2")
    assert hs2 is not None
    device_clean_up(sw1=sw1, sw2=sw2, hs1=hs1, hs2=hs2, step=step)
