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
# |  hs1  |
# +---^---+
#     |
#     |
# +---v---+       +-------+
# |  sw1  <------->  hs2  |
# +---^---+       +-------+
#     |
#     |
# +---v---+
# |  hs3  |
# +-------+

# Nodes
[type=openswitch name="Switch 1"] sw1
[type=host name="Host 1"] hs1
[type=host name="Host 2"] hs2
[type=host name="Host 3"] hs3

# Links
sw1:if01 -- hs1:eth1
sw1:if02 -- hs2:eth1
sw1:if03 -- hs3:eth1
"""


def l3_route(sw1, hs1, hs2, hs3, step):
    # pinging from host to host
    for int in sw1.ports:
        with sw1.libs.vtysh.ConfigInterface(int) as cnf:
            cnf.no_shutdown()
        if int == "if01":
            with sw1.libs.vtysh.ConfigSubinterface(int, "10") as cnf:
                cnf.no_shutdown()
    with sw1.libs.vtysh.ConfigVlan("100") as cnf:
                cnf.no_shutdown()

    for i in range(2, 4):
        with sw1.libs.vtysh.ConfigInterface('if0{}'.format(i)) as cnf:
            cnf.no_routing()
            cnf.vlan_access("100")

    # configure Ip on the host
    hs2.libs.ip.interface("eth1", "172.168.1.2/24", up=True)
    hs3.libs.ip.interface("eth1", "172.168.1.3/24", up=True)
    hs2.libs.ping.ping(1, "172.168.1.3")
    sleep(2)
    ping = hs2.libs.ping.ping(10, "172.168.1.3")
    step("ping workstation 2 to workstation 3 return \
                       JSON:\n" + str(ping))
    assert ping["transmitted"] == 10 and ping["received"] >= 7

    # pinging from work station to switch 1
    with sw1.libs.vtysh.ConfigSubinterface('if01', "10") as cnf:
        cnf.ip_address("192.168.1.1/24")
        cnf.encapsulation_dot1_q("100")
    # configure Ip on the host
    hs1.libs.ip.add_link_type_vlan("eth1", "eth1.100", "100")
    hs1.libs.ip.sub_interface("eth1", "100", "192.168.1.2/24", up=True)

    hs1.libs.ping.ping(1, "192.168.1.1")
    sleep(2)
    output = hs1.libs.ping.ping(10, "192.168.1.1")
    step("IPv4 Ping from workstation 1 to switch 1 return \
                       JSON:\n" + str(output))

    assert output["received"] >= 7 and output["transmitted"] == 10

    with sw1.libs.vtysh.ConfigSubinterface('if01', "10") as cnf:
        cnf.encapsulation_dot1_q("200")
    sleep(2)
    output = hs1.libs.ping.ping(10, "192.168.1.1")
    step("IPv4 Ping from workstation 1 to sw1 return JSON:\n" + str(output))
    assert output["received"] != output["transmitted"]

    # after eemoving dot1 encapsulation trying to ping host-switch
    with sw1.libs.vtysh.ConfigSubinterface('if01', "10") as cnf:
        cnf.no_encapsulation_dot1_q("200")
    sleep(2)
    output = hs1.libs.ping.ping(10, "192.168.1.1")

    step("IPv4 Ping from workstation1 to switch 1 return \
                       JSON:\n" + str(output))
    assert output["received"] == 0


def test_layer3_ft_verify_sub_intf_l2vlan(topology, step):
    sw1 = topology.get('sw1')
    assert sw1 is not None
    hs1 = topology.get('hs1')
    assert hs1 is not None
    hs2 = topology.get('hs2')
    assert hs2 is not None
    hs3 = topology.get('hs3')
    assert hs3 is not None
    l3_route(sw1, hs1, hs2, hs3, step)
