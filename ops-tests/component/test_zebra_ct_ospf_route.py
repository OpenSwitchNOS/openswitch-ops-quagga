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
OpenSwitch Test for Zebra OSPF route installation
"""
from time import sleep
import re

TOPOLOGY = """
# +-------+
# |  ops1 |
# +-------+

# Nodes
[type=openswitch name="OpenSwitch 1"] ops1

# Links
ops1:if01
"""

INT1 = "1"
VRF_NAME = "vrf_default"
MAX_WAIT_TIME = 60
MAX_WAIT_INT_TIME = 10
VTYSH_CR = '\r\n'


def wait_for_interface_up(ops1):
    for i in range(MAX_WAIT_INT_TIME):
        int_status_ops1 = ops1.libs.vtysh.show_interface('1')
        admin_state = int_status_ops1['admin_state']
        int_state = int_status_ops1['interface_state']
        if admin_state == 'up' and int_state == 'up':
            return True
        sleep(1)

    return False


def verify_route(ops1):
    rts = ops1("/sbin/ip netns exec swns route -n", shell="bash")
    nh_ip = "10.10.10.11 "
    nh_iface = "1"
    routes = rts.split(VTYSH_CR)
    for route in routes:
        if nh_ip in route:
            if nh_iface in route:
                return True

    return False


def ospf_wait_for_route(ops1, step):
    step("Checking route installed by zebra")
    wait_time = MAX_WAIT_TIME
    for i in range(wait_time):
        found = verify_route(ops1)
        if found is True:
            return True

        sleep(1)

    return False


def get_vrf_uuid(switch, vrf_name, step):
    """
    This function takes a switch and a vrf_name as inputs and returns
    the uuid of the vrf.

    """
    step("Getting uuid for the vrf {vrf_name}".format(**locals()))
    ovsdb_command = "list vrf {vrf_name}".format(**locals())
    vrf_buffer = switch(ovsdb_command, shell="vsctl")

    lines = vrf_buffer.split('\n')
    vrf_uuid = None
    for line in lines:
        vrf_uuid = re.match("(.*)_uuid( +): (.*)", line)

        if vrf_uuid is not None:
            break

    assert vrf_uuid is not None,\
        'Getting VRF UUID - Failed'

    return vrf_uuid.group(3).rstrip('\r')


def get_port_uuid(switch, port_name, step):
    """
    This function takes a switch and a vrf_name as inputs and returns
    the uuid of the vrf.

    """
    step("Getting uuid for the port {port_name}".format(**locals()))
    ovsdb_command = "list port {port_name}".format(**locals())
    port_buffer = switch(ovsdb_command, shell="vsctl")
    lines = port_buffer.split('\n')
    port_uuid = None
    for line in lines:
        port_uuid = re.match("(.*)_uuid( +): (.*)", line)

        if port_uuid is not None:
            break

    assert port_uuid is not None,\
        'Getting Port UUID - Failed'

    return port_uuid.group(3).rstrip('\r')


def test_zebra_ospf_route(topology, step):
    ops1 = topology.get('ops1')
    assert ops1 is not None

    step("Test OSPF route installation by zebra")
    step("Configuring Interface {}".format(INT1))
    with ops1.libs.vtysh.ConfigInterface('if01') as ctx:
        ctx.no_shutdown()
        ctx.ip_address("10.10.10.1/24")

    vrf_uuid = get_vrf_uuid(ops1, VRF_NAME, step)
    port_uuid = get_port_uuid(ops1, INT1, step)
    assert wait_for_interface_up(ops1),\
        "Invalid interface {} state".format(INT1)

    ospf_route_command = "ovsdb-client transact \'[ \"OpenSwitch\",\
         {\
             \"op\" : \"insert\",\
             \"table\" : \"Nexthop\",\
             \"row\" : {\
                 \"ip_address\" : \"10.10.10.11\",\
                \"ports\":[\"uuid\",\"%s\"],\
                 \"selected\": true\
             },\
             \"uuid-name\" : \"nh01\"\
         },\
        {\
            \"op\" : \"insert\",\
            \"table\" : \"Route\",\
            \"row\" : {\
                     \"prefix\":\"192.168.1.0/24\",\
                     \"from\":\"ospf\",\
                     \"vrf\":[\"uuid\",\"%s\"],\
                     \"address_family\":\"ipv4\",\
                     \"sub_address_family\":\"unicast\",\
                     \"distance\":110,\
                     \"nexthops\" : [\
                     \"set\",\
                     [\
                         [\
                             \"named-uuid\",\
                             \"nh01\"\
                         ]\
                     ]]\
                     }\
        }\
        ]\'" % (port_uuid, vrf_uuid)
    ops1(ospf_route_command, shell="bash")
    ret = ospf_wait_for_route(ops1, step)
    assert ret is True,\
        'Test OSPF route installation by zebra - Failed'
    ospf_route_command = "ovsdb-client transact \'[ \"OpenSwitch\",\
        {\
            \"op\" : \"delete\",\
            \"table\" : \"Route\",\
             \"where\":[[\"prefix\",\"==\",\"192.168.1.0/24\"],\
             [\"from\",\"==\",\"ospf\"]]\
        }\
        ]\'"
    ops1(ospf_route_command, shell="bash")
    ret = ospf_wait_for_route(ops1, step)
    assert ret is False,\
        'Test OSPF route Deletion by zebra - Failed'
