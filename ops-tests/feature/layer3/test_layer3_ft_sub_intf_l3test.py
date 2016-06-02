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
# +-------+       +-------+
# |  sw1  <------->  hs1  |
# +-------+       +-------+

# Nodes
[type=openswitch name="Switch 1"] sw1
[type=host name="Host 1"] hs1

# Links
sw1:if01 -- hs1:eth1
"""


def sub_interface(**kwargs):
    sw1 = kwargs.get('sw1', None)
    hs1 = kwargs.get('hs1', None)
    step = kwargs.get('step', None)
    step("Positive l3 reachability test with admin state up")

    with sw1.libs.vtysh.ConfigInterface("if01") as cnf:
        cnf.no_shutdown()
        cnf.ip_address("10.0.0.1/8")

    with sw1.libs.vtysh.ConfigSubinterface("if01", "1") as cnf:
        cnf.no_shutdown()

    with sw1.libs.vtysh.ConfigSubinterface("if01", "2") as cnf:
        cnf.no_shutdown()

    # with sw1.libs.vtysh.ConfigInterface("if01") as cnf:
    #     cnf.routing()

    with sw1.libs.vtysh.ConfigSubinterface("if01", "1") as cnf:
        cnf.ip_address("20.0.0.1/8")
        cnf.encapsulation_dot1_q("100")

    hs1.libs.ip.add_link_type_vlan("eth1", "eth1.100", "100")
    # configure Ip on the host
    hs1.libs.ip.sub_interface("eth1", "100", "20.0.0.2/8", up=True)
    hs1.libs.ping.ping(1, "20.0.0.1")
    sleep(20)
    output = hs1.libs.ping.ping(10, "20.0.0.1")

    step("IPv4 Ping from workstation 1 to sw1 return \
                       JSON:\n" + str(output))

    assert output['received'] >= 7 and output['transmitted'] == 10

    step("Negative l3 reachability test \
                       with admin state down.")

    with sw1.libs.vtysh.ConfigSubinterface("if01", "1") as cnf:
        cnf.shutdown()

    step("shutting down interface 1.1")
    hs1.libs.ping.ping(1, "20.0.0.1")
    sleep(2)
    output = hs1.libs.ping.ping(10, "20.0.0.1")

    step("IPv4 Ping from workstation 1 to sw1 return \
               JSON:\n" + str(output))

    assert output['received'] != output['transmitted']

    # pinging with ipv6 address
    with sw1.libs.vtysh.ConfigSubinterface("if01", "2") as cnf:
        cnf.ipv6_address("2000::23/64")
    output = sw1("get port 1.2 ip6_address", shell='vsctl')

    assert "2000::23/64" in output

    with sw1.libs.vtysh.ConfigSubinterface("if01", "2") as cnf:
        cnf.encapsulation_dot1_q("12")
    hs1.libs.ip.add_link_type_vlan("eth1", "eth1.12", "12")
    hs1.libs.ip.sub_interface("eth1", "12", "2000::9/64", up=True)

    hs1.libs.ping.ping(1, "2000::23")
    sleep(2)
    output = hs1.libs.ping.ping(10, "2000::23")
    step("IPv6 Ping from workstation 1 to sw1 return \
                       JSON:\n" + str(output))

    assert output['transmitted'] == 10 and output['received'] >= 7

    # changing the vlan id in sub interface and
    # checking whether ping is success
    with sw1.libs.vtysh.ConfigSubinterface("if01", "2") as cnf:
        cnf.encapsulation_dot1_q("17")

    sleep(2)
    output = hs1.libs.ping.ping(10, "2000::23")
    step("IPv6 Ping from workstation 1 to sw1 return \
                       JSON:\n" + str(output))

    assert output['transmitted'] != output['received']


def device_clean_up(**kwargs):
    sw1 = kwargs.get('sw1', None)
    hs1 = kwargs.get('hs1', None)
    step = kwargs.get('step', None)
    step("Device Cleanup")

    with sw1.libs.vtysh.ConfigSubinterface("if01", "1") as cnf:
        cnf.shutdown()
        cnf.no_ip_address("192.168.1.1/24")
        cnf.no_encapsulation_dot1_q("100")

    # configure Ip on the host
    hs1.libs.ip.sub_interface("eth1", "100", "192.168.1.2/24", up=False)


def test_layer3_ft_sub_intf_l3test(topology, step):
    sw1 = topology.get("sw1")
    assert sw1 is not None
    hs1 = topology.get("hs1")
    assert hs1 is not None
    sub_interface(sw1=sw1, hs1=hs1, step=step)


def t_device_clean_up(topology, step):
    sw1 = topology.get("sw1")
    assert sw1 is not None
    hs1 = topology.get("hs1")
    assert hs1 is not None
    device_clean_up(sw1=sw1, hs1=hs1, step=step)
