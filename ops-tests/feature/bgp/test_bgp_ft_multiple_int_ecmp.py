# -*- coding: utf-8 -*-
# (C) Copyright 2016 Hewlett Packard Enterprise Development LP
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
##########################################################################

"""
OpenSwitch Test for vlan related configurations.
"""

from pytest import mark
from vtysh_utils import SwitchVtyshUtils
import time

TOPOLOGY = """
# +-------+
# |  ops1 |
# +-------+

# Nodes
[type=openswitch name="OpenSwitch 1"] ops1
[type=openswitch name="Openswitch 2"] ops2
[type=openswitch name="Openswitch 3"] ops3


# Links
ops1:if01 -- ops2:if01
ops1:if02 -- ops2:if02
ops1:if03 -- ops3:if01
ops1:if04 -- ops3:if02
"""


bgp1_asn = "1"

bgp2_asn = "2"
bgp2_network = ["12.0.0.0", "22.0.0.0"]

bgp3_asn = "3"
bgp3_network = ["13.0.0.0", "23.0.0.0"]

bgp_network_pl = "8"
bgp_network_mask = "255.0.0.0"

switches = []

bgp1_ip_add = ["8.0.0.1", "9.0.0.1", "10.0.0.1", "11.0.0.1"]
bgp1_neighbor_asn = ["2", "3"]

bgp2_ip_add = ["8.0.0.2", "9.0.0.2"]
bgp3_ip_add = ["10.0.0.3", "11.0.0.3"]
bgp2_neighbor_asn = bgp3_neighbor_asn = ["1"]

bgp1_config = ["router bgp %s" % bgp1_asn,
               "maximum-paths 4",
               "neighbor %s remote-as %s" % (bgp2_ip_add[0],
                                             bgp1_neighbor_asn[0]),
               "neighbor %s remote-as %s" % (bgp2_ip_add[1],
                                             bgp1_neighbor_asn[0]),
               "neighbor %s remote-as %s" % (bgp3_ip_add[0],
                                             bgp1_neighbor_asn[1]),
               "neighbor %s remote-as %s" % (bgp3_ip_add[1],
                                             bgp1_neighbor_asn[1])]

bgp2_config = ["router bgp %s" % bgp2_asn,
               "network %s/%s" % (bgp2_network[0], bgp_network_pl),
               "network %s/%s" % (bgp2_network[1], bgp_network_pl),
               "neighbor %s remote-as %s" % (bgp1_ip_add[0],
                                             bgp2_neighbor_asn[0]),
               "neighbor %s remote-as %s" % (bgp1_ip_add[1],
                                             bgp2_neighbor_asn[0])]

bgp3_config = ["router bgp %s" % bgp3_asn,
               "network %s/%s" % (bgp3_network[0], bgp_network_pl),
               "network %s/%s" % (bgp3_network[1], bgp_network_pl),
               "neighbor %s remote-as %s" % (bgp1_ip_add[2],
                                             bgp3_neighbor_asn[0]),
               "neighbor %s remote-as %s" % (bgp1_ip_add[3],
                                             bgp3_neighbor_asn[0])]

bgp_configs = [bgp1_config, bgp2_config, bgp3_config]

num_of_switches = 3
num_hosts_per_switch = 0

switch_prefix = "s"


def configure_switch_ips(step):
    step("\n########## Configuring switch IPs.. ##########\n")

    switch = switches[0]
    for i in range(0, 4):
        switch("configure terminal")
        switch("interface %s" % switch.ports["if0%s" % str(i+1)])
        switch("no shutdown")
        switch("ip address %s/%s" % (bgp1_ip_add[i],
                                     bgp_network_pl))
        switch("end")

    # Configuring switch 2 IPs
    switch = switches[1]
    i = 0
    for i in range(0, 2):
        switch("configure terminal")
        switch("interface %s" % switch.ports["if0%s" % str(i+1)])
        switch("no shutdown")
        switch("ip address %s/%s" % (bgp2_ip_add[i], bgp_network_pl))
        switch("end")

    # Configuring switch 3 IPs
    switch = switches[2]
    i = 0
    for i in range(0, 2):
        switch("configure terminal")
        switch("interface %s" % switch.ports["if0%s" % str(i+1)])
        switch("no shutdown")
        switch("ip address %s/%s" % (bgp3_ip_add[i], bgp_network_pl))
        switch("end")


def verify_bgp_running(step):
    step("\n########## Verifying bgp processes.. ##########\n")

    for switch in switches:
        pid = switch("pgrep -f bgpd", shell="bash").strip()
        assert (pid != ""), "bgpd process not running on switch %s" % \
            switch.name

        step("### bgpd process exists on switch %s ###\n" % switch.name)


def configure_bgp(step):
    step("\n########## Applying BGP configurations... ##########\n")

    i = 0
    for switch in switches:
        step("### Applying BGP config on switch %s ###\n" % switch.name)
        cfg_array = bgp_configs[i]
        i += 1

        SwitchVtyshUtils.vtysh_cfg_cmd(switch, cfg_array)


def verify_configs(step):
    step("\n########## Verifying all configurations.. ##########\n")

    for i in range(0, len(bgp_configs)):
        bgp_cfg = bgp_configs[i]
        switch = switches[i]

        for cfg in bgp_cfg:
            res = SwitchVtyshUtils.verify_cfg_exist(switch, [cfg])
            assert res, "Config \"%s\" was not correctly configured!" % cfg


def verify_sessions(step):
    step("\n Verifying BGP sessions from switch 1..\n")
    while(1):
        switch = switches[0]
        time.sleep(1)
        result = switch("show ip bgp summary")
        if("Established" in result):
            if(result.count("Established") == 4):
                break


def verify_ecmp(step):
    step("\nVerifying ecmp....\n")
    switch = switches[0]
    while(1):
        time.sleep(1)
        result = switch("show ip bgp")
        print(result.split())
        networks = ["12.0.0.0/8", "13.0.0.0/8", "22.0.0.0/8", "23.0.0.0/8"]
        if("Total number of entries 8" in result):
            for ip in networks:
                index1 = result.index(ip)
                index2 = result[index1:].index(ip)
                best_path = False
                multipath = False
                if(result[index1-1] == "*>"):
                    if(result[index2-1] == "*="):
                        best_path = True
                        multipath = True
                elif(result[index1-1] == "*="):
                    if(result[index2-1] == "*>"):
                        best_path = True
                        multipath = True
            break
    if not (best_path and multipath):
        assert "multipaths not established"


@mark.timeout(600)
def test_bgp_ft_basic_bgp_route_advertise(topology, step):
    global switches

    ops1 = topology.get('ops1')
    ops2 = topology.get('ops2')
    ops3 = topology.get('ops3')

    assert ops1 is not None
    assert ops2 is not None
    assert ops3 is not None

    switches = [ops1, ops2, ops3]

    ops1.name = "ops1"
    ops2.name = "ops2"
    ops3.name = "ops3"

    configure_switch_ips(step)
    verify_bgp_running(step)
    configure_bgp(step)
    verify_configs(step)
    verify_sessions(step)
    verify_ecmp(step)
