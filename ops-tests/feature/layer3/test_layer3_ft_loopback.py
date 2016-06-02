#!/usr/bin/env python

# Copyright (C) 2015-2016 Hewlett Packard Enterprise Development LP)
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


from time import sleep


TOPOLOGY = """
# +-------+     +--------+
# |  hs1  <----->  ops1  |
# +-------+     +--------+

# Nodes
[type=openswitch] sw1
[type=host] hs1

# Links
hs1:eth1 -- sw1:if01
"""


# Hardcode loopback interface, interface ID not valid for all platforms
interface_loopback_id = "10"


def loopback_l3(sw1, host, step):
    step("Loopback l3 reachability test")
    with sw1.libs.vtysh.ConfigInterfaceLoopback(interface_loopback_id) as cnf:
        cnf.ip_address("192.168.1.5/24")

    with sw1.libs.vtysh.ConfigInterface('if01') as cnf:
        cnf.no_shutdown()
        cnf.ip_address("192.168.2.1/24")

    # configure Ip on the host
    host.libs.ip.interface("eth1", "192.168.2.3/24", up=True)

    host.libs.ip.add_route("192.168.1.0/24", "192.168.2.1")

    step("Pinging between workstation1 and sw1")

    sleep(20)
    output = host.libs.ping.ping(10, "192.168.1.5")
    step("IPv4 Ping from workstation 1 to sw1 return JSON:\n" +
         str(output))
    assert output['transmitted'] is 10 and output['received'] >= 7


def negative_l3_reach(sw1, host, step):
    step("Loopback negative l3 reachability test")
    with sw1.libs.vtysh.Configure() as cnf:
        cnf.no_interface_loopback(interface_loopback_id)

    step("Pinging between workstation1 and sw1 ")

    sleep(20)
    output = host.libs.ping.ping(10, "192.168.1.5")

    step("IPv4 Ping from workstation 1 to sw1 return JSON:\n" +
         str(output))
    host.libs.ip.interface("eth1", up=False)
    assert output['transmitted'] is 10 and output['received'] is 0


def test_layer3_ft_loopback(topology, step):
    sw1 = topology.get("sw1")
    assert sw1 is not None
    host = topology.get("hs1")
    assert host is not None
    loopback_l3(sw1, host, step)
    negative_l3_reach(sw1, host, step)
