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


TOPOLOGY = """
#
# +-------+
# |  sw1  |
# +-------+
#

# Nodes
[type=openswitch name="Switch 1"] sw1

"""
from time import sleep

def configure_two_interfaces(sw1, step):
    interface1 = "9.0.0.1"
    pl = "8"

    step("1-Verifying zebra processes...")
    pid = sw1("pgrep -f zebra", shell='bash')
    pid = pid.strip()
    assert pid != "" and pid is not None

    step("2-Applying interface configurations")
    sw1("configure terminal")
    sw1("interface 1")
    sw1("no shutdown")
    sw1("ip address {}/{}".format(interface1, pl))
    sw1("exit")
    sleep(1)

def verify_active_router_id(sw1, step):
    step("3-Verifying Active Router-ID is one of the interface ip")
    active_router_id1 = "9.0.0.1"
    output = sw1("ovsdb-client dump VRF", shell='bash')
    assert active_router_id1 in output

def verify_loopback_interface(sw1, step):
    pl = "24"
    step("4-Verifying Loopback IP gets more priority")
    loopback_ip = "9.0.1.3"
    active_router_id3 = "9.0.1.3"
    sw1("configure terminal")
    sw1("interface loopback 3")
    sw1("ip address {}/{}".format(loopback_ip, pl))
    sw1("exit")
    sleep(1)
    output = sw1("ovsdb-client dump VRF", shell='bash')
    assert active_router_id3 in output

def verify_unconfigure_loopback_interface(sw1, step):
    pl = "24"
    loopback_ip = "9.0.1.3"
    active_router_id1 = "9.0.0.1"
    step("4-Verify deleting loopback interface")
    sw1("configure terminal")
    sw1("interface loopback 3")
    sw1("no ip address {}/{}".format(loopback_ip, pl))
    sw1("exit")
    sleep(1)
    output = sw1("ovsdb-client dump VRF", shell='bash')
    assert active_router_id1 in output

def verify_unconfigure_interface(sw1, step):
    interface1 = "9.0.0.1"
    interface2 = "9.0.0.2"
    active_router_id2 = "9.0.0.2"
    pl = "8"
    step("5-Verify deleting one of the interface")
    sw1("configure terminal")
    sw1("interface 1")
    sw1("shutdown")
    sw1("no ip address {}/{}".format(interface1, pl))
    sw1("exit")
    sw1("interface 2")
    sw1("no shutdown")
    sw1("ip address {}/{}".format(interface2, pl))
    sw1("exit")
    sleep(1)
    output = sw1("ovsdb-client dump VRF", shell='bash')
    assert active_router_id2 in output

def test_zebra_ct_active_router_id(topology, step):
    sw1 = topology.get("sw1")
    assert sw1 is not None
    configure_two_interfaces(sw1, step)
    verify_active_router_id(sw1, step)
    verify_loopback_interface(sw1, step)
    verify_unconfigure_loopback_interface(sw1, step)
    verify_unconfigure_interface(sw1, step)
