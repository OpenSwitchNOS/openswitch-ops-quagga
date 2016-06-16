# -*- coding: utf-8 -*-

# (c) Copyright 2015-2016 Hewlett Packard Enterprise Development LP
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
# +-------+      +-------+
# |  sw1  <------>  sw2  |
# +-------+      +-------+

# Nodes
[type=openswitch name="Switch 1"] sw1
[type=openswitch name="Switch 2"] sw2

# Links
sw1:if01 -- sw2:if01
"""


def test_zebra_ct_fib_selection(topology, step):
    sw1 = topology.get("sw1")
    sw2 = topology.get("sw2")

    # Test case init time sleep
    sleep(ZEBRA_INIT_SLEEP_TIME)

    step('1-Configuring the topology')

    # Configure switch sw1
    sw1("configure terminal")

    # Configure interface 1 on switch sw1
    sw1("interface 1")
    sw1("ip address 10.0.10.1/24")
    sw1("ipv6 address 2000::1/120")
    sw1("exit")

    # Configure interface 2 on switch sw1
    sw1("interface 2")
    sw1("ip address 10.0.20.1/24")
    sw1("ipv6 address 2001::1/120")
    sw1("exit")

    # Configure switch sw2
    sw2("configure terminal")

    # Configure interface 1 on switch sw2
    sw2("interface 1")
    sw2("ip address 10.0.10.2/24")
    sw2("ipv6 address 2000::2/120")
    sw2("exit")

    # Configure interface 2 on switch sw2
    sw2("interface 2")
    sw2("ip address 10.0.30.1/24")
    sw2("ipv6 address 2002::1/120")
    sw2("exit")

    # Add IPv4 static route on sw1 and sw2
    sw1("ip route 10.0.30.0/24 10.0.10.2")
    sw2("ip route 10.0.20.0/24 10.0.10.1")

    # Add IPv6 static route on sw1 and sw2
    sw1("ipv6 route 2002::0/120 2000::2")
    sw2("ipv6 route 2001::0/120 2000::1")

    # Turning on the interfaces
    sw1("set interface 1 user_config:admin=up", shell='vsctl')
    sw1("set interface 2 user_config:admin=up", shell='vsctl')
    sw2("set interface 1 user_config:admin=up", shell='vsctl')
    sw2("set interface 2 user_config:admin=up", shell='vsctl')

    sleep(ZEBRA_TEST_SLEEP_TIME)

    step('2-Verify static routes are selected for fib')

    # Parse the "ovsdb-client dump" output and extract the lines between
    # "Route table" and "Route_Map table". This section will have all the
    # Route table entries. Then parse line by line to match the contents
    dump = sw1("ovsdb-client dump", shell='bash')
    lines = dump.split('\n')
    check = False
    for line in lines:
        if check:
            if 'static' in line and 'unicast' in line and \
               '10.0.30.0/24' in line:
                assert 'true' in line
            elif 'static' in line and 'unicast' in line and \
                 '2002::/120' in line:
                assert 'true' in line
        if 'Route table' in line:
            check = True
        if 'Route_Map table' in line:
            check = False
