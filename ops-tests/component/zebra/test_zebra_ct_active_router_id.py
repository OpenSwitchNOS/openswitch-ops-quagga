# -*- coding: utf-8 -*-

# (c) Copyright 2016 Hewlett Packard Enterprise Development LP
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

from helpers_routing import (
    ZEBRA_TEST_SLEEP_TIME,
    ZEBRA_INIT_SLEEP_TIME
)
from time import sleep

TOPOLOGY = """
#
# +-------+
# |  sw1  |
# +-------+
#

# Nodes
[type=openswitch name="Switch 1"] sw1

"""

#  This is basic configuration required for the test, it verifies zebra
#  deamon is running and configures one interface with IPv4 address.
def configure_interface(sw1, step):
    interface_addr1 = "9.0.0.1"
    masklen = "8"

    step("1-Verifying zebra processes...")
    pid = sw1("pgrep -f zebra", shell='bash')
    pid = pid.strip()
    assert pid != "" and pid is not None

    step("2-Applying interface configurations")
    sw1("configure terminal")
    sw1("interface 1")
    sw1("no shutdown")
    sw1("ip address {}/{}".format(interface_addr1, masklen))
    sw1("exit")

    sleep(ZEBRA_TEST_SLEEP_TIME)


#  This test verifies active_router_id column in VRF table is same
#  as the interface 1 IPv4 address.
def verify_active_router_id(sw1, step):
    step("3-Verifying Active Router-ID is one of the interface ip")
    active_router_id1 = "9.0.0.1"
    output = sw1("ovsdb-client dump VRF", shell='bash')
    assert active_router_id1 in output


#  This test configures the loopback interface and verifies that
#  loopback IPv4 address is used as active_router_id.
def verify_loopback_interface(sw1, step):
    interface_addr1 = "9.0.0.1"
    masklen1 = "8"
    masklen2 = "24"
    loopback_ip = "10.0.1.3"
    active_router_id3 = "10.0.1.3"

    step("4-Verifying Loopback IP gets higher priority")
    sw1("configure terminal")
    sw1("interface 1")
    sw1("shutdown")
    sw1("no ip address {}/{}".format(interface_addr1, masklen1))
    sw1("exit")
    sw1("interface loopback 3")
    sw1("ip address {}/{}".format(loopback_ip, masklen2))
    sw1("exit")

    sleep(ZEBRA_TEST_SLEEP_TIME)

    output = sw1("ovsdb-client dump VRF", shell='bash')
    assert active_router_id3 in output


#  This test verifies that unconfiguring the loopback interface which
#  was used as active_router_id will change it to any other L3
#  interface IPv4 address.
def verify_unconfigure_loopback_interface(sw1, step):
    masklen1 = "8"
    masklen2 = "24"
    interface_addr1 = "9.0.0.1"
    loopback_ip = "10.0.1.3"
    active_router_id1 = "9.0.0.1"

    step("4-Verify deleting loopback interface")
    sw1("configure terminal")
    sw1("interface 1")
    sw1("no shutdown")
    sw1("ip address {}/{}".format(interface_addr1, masklen1))
    sw1("exit")
    sw1("interface loopback 3")
    sw1("no ip address {}/{}".format(loopback_ip, masklen2))
    sw1("exit")

    sleep(ZEBRA_TEST_SLEEP_TIME)

    output = sw1("ovsdb-client dump VRF", shell='bash')
    assert active_router_id1 in output


#  This test verifies that unconfiguring the L3 interface which was
#  used as an active_router_id changes it to any other available L3
#  interface IPv4 address
def verify_unconfigure_interface(sw1, step):
    interface_addr1 = "9.0.0.1"
    interface_addr2 = "11.0.0.2"
    active_router_id2 = "11.0.0.2"
    masklen = "8"

    step("5-Verify deleting one of the interface")
    sw1("configure terminal")
    sw1("interface 1")
    sw1("shutdown")
    sw1("no ip address {}/{}".format(interface_addr1, masklen))
    sw1("exit")
    sw1("interface 2")
    sw1("no shutdown")
    sw1("ip address {}/{}".format(interface_addr2, masklen))
    sw1("exit")

    sleep(ZEBRA_TEST_SLEEP_TIME)

    output = sw1("ovsdb-client dump VRF", shell='bash')
    assert active_router_id2 in output


#  This test verifies that if an active_router_id already present then
#  configuring aditional L3 interface will not change the active_router_id,
#  instead it keep on using the same active_router_id
def verify_no_change_for_new_added_interfaces(sw1, step):
    interface_addr1 = "9.0.0.1"
    interface_addr2 = "12.0.0.4"
    interface_lo_addr3 = "10.0.0.5"
    active_router_id2 = "11.0.0.2"
    masklen = "8"
    masklen2 = "24"

    step("6-Verify no change in active_router_id although we are adding new interfaces")
    sw1("configure terminal")
    sw1("interface 1")
    sw1("no shutdown")
    sw1("ip address {}/{}".format(interface_addr1, masklen))
    sw1("exit")
    sw1("interface 4")
    sw1("no shutdown")
    sw1("ip address {}/{}".format(interface_addr2, masklen))
    sw1("exit")
    sw1("interface loopback 5")
    sw1("ip address {}/{}".format(interface_lo_addr3, masklen2))
    sw1("exit")

    sleep(ZEBRA_TEST_SLEEP_TIME)

    output = sw1("ovsdb-client dump VRF", shell='bash')
    assert active_router_id2 in output


def test_zebra_ct_active_router_id(topology, step):
    sw1 = topology.get("sw1")
    assert sw1 is not None

    # Test case init time sleep
    sleep(ZEBRA_INIT_SLEEP_TIME)

    configure_interface(sw1, step)
    verify_active_router_id(sw1, step)
    verify_loopback_interface(sw1, step)
    verify_unconfigure_loopback_interface(sw1, step)
    verify_unconfigure_interface(sw1, step)
    verify_no_change_for_new_added_interfaces(sw1, step)
