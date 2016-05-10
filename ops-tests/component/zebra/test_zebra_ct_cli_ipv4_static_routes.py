# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from time import sleep
from re import match
from re import findall

TOPOLOGY = """
#
#
# +-------+     +-------+
# +  sw1  <----->  sw2  +
# +-------+     +-------+
#
#

# Nodes
[type=openswitch name="Switch 1"] sw1
[type=openswitch name="Switch 2"] sw2

# Links
sw1:if01 -- sw2:if01
sw1:if02
sw1:if03
sw1:if04
sw2:if02

"""


def test_ipv4_static_route_config(topology, step):
    '''
    This test verifies various ipv4 static route configurations by validating
    both the postive and the negative test cases with default/non-default
    configurations.
    '''
    sw1 = topology.get('sw1')
    sw2 = topology.get('sw2')

    assert sw1 is not None
    assert sw2 is not None

    sw1p1 = sw1.ports['if01']
    sw1p2 = sw1.ports['if02']
    sw1p3 = sw1.ports['if03']
    sw1p4 = sw1.ports['if04']
    sw2p1 = sw2.ports['if01']
    sw2p2 = sw2.ports['if02']

    step('### Test to verify IPv4 static routes ###')
    # Configure switch 1
    sw1('configure terminal')
    sw1('interface {sw1p1}'.format(**locals()))
    sw1('ip address 192.168.1.1/24')
    sw1('no shutdown')
    sw1('exit')
    sleep(5)
    sw1('interface {sw1p2}'.format(**locals()))
    sw1('ip address 192.168.2.1/24')
    sw1('no shutdown')
    sw1('exit')
    sleep(5)

    # Configure switch 2
    sw2('configure terminal')
    sw2('interface {sw2p1}'.format(**locals()))
    sw2('ip address 192.168.1.2/24')
    sw2('no shutdown')
    sw2('exit')
    sleep(5)
    sw2('interface {sw2p2}'.format(**locals()))
    sw2('ip address 192.168.3.1/24')
    sw2('no shutdown')
    sw2('exit')
    sleep(5)

    step('### Verify ip route configuration with nexthop address ###')
    sw1('ip route 192.168.3.0/24 192.168.1.2 2')
    sleep(2)
    ret = sw1('do show ip route')

    assert '192.168.3.0/24' in ret and '192.168.1.2' in ret \
           and 'static' in ret and '[2/0]' in ret, \
           'IP route configuration failed'

    step('### Verify deletion of ip route with nexthop address ###')
    sw1('no ip route 192.168.3.0/24 192.168.1.2 2')
    ret = sw1('do show ip route')

    assert '192.168.3.0/24' not in ret and '192.168.1.2' not in ret \
           and 'static' not in ret and '[2/0]' not in ret, \
           'Deletion of ip route failed'

    step('### Verify prefix format ###')
    sw1('ip route 192.168.3.0 192.168.1.2 2')
    ret = sw1('do show ip route')

    assert '192.168.3.0/24' not in ret and '192.168.1.2' not in ret \
           and 'static' not in ret and '[2/0]' not in ret, \
           'Prefix format verification failed'

    step('### Verify ip route configuration with nexthop interface ###')
    sw1('ip route 192.168.3.0/24 2 2')
    sleep(2)
    ret = sw1('do show ip route')
    assert '192.168.3.0/24' in ret and '2,' in ret and 'static' \
           in ret and '[2/0]' in ret, 'IP route configuration failed'

    step('### Verify deletion of ip route with nexthop interface ###')
    sw1('no ip route 192.168.3.0/24 2 2')
    ret = sw1('do show ip route')

    assert '192.168.3.0/24' not in ret and 'static' not in ret \
           and '[2/0]' not in ret, 'Deletion of ip route failed'

    step('### Verify setting of default distance ###')
    sw1('ip route 192.168.3.0/24 192.168.1.2')
    ret = sw1('do show ip route')

    assert '192.168.3.0/24' in ret and '192.168.1.2' in ret \
           and 'static' in ret and '[1/0]' in ret, \
           'Default distance verification failed'

    step('### Verify setting of multiple nexthops for a given prefix ###')
    sw1('ip route 192.168.3.0/24 1')
    sleep(2)
    sw1('ip route 192.168.3.0/24 2')
    sleep(2)
    ret = sw1('do show ip route')

    assert '192.168.3.0/24' in ret and '3 unicast next-hops' in ret \
           and '1,' in ret and '2,' in ret and '[1/0]' in ret \
           and 'static' in ret, 'Multiple nexthops verification failed'

    step('''### Verify if nexthop is not assigned locally to an interface as'''
         ''' a primary ip address ###''')
    sw1('ip route 192.168.3.0/24 192.168.2.1')
    ret = sw1('do show ip route')

    assert not 'ip route 192.168.3.0/24 192.168.2.1' in ret, \
          'Primary ip address check for nexthop failed'

    step(''' ### Verify if nexthop is not assigned locally to an '''
         '''interface as a secondary ip address ###\n''')
    sw1('interface {sw1p1}'.format(**locals()))
    sw1('ip address 192.168.2.2/24 secondary')
    sw1('exit')
    sw1('ip route 192.168.3.0/24 192.168.2.2')
    ret = sw1('do show running-config')
    assert not 'ip route 192.168.3.0/24 192.168.2.2'in ret, \
            'Secondary ip address check for nexthop failed'
    sw1('interface {sw1p1}'.format(**locals()))
    sw1('no ip address 192.168.2.2/24 secondary')
    sw1('exit')

    step(''' ### Verify if broadcast address cannot be assigned as a prefix '''
         ''' ###\n''')
    sw1('ip route 255.255.255.255/32 255.255.255.1')
    ret = sw1('do show running-config')
    assert not 'ip route 255.255.255.255/32 255.255.255.1' in ret, \
            'Broadcast address check for prefix failed'

    step(''' ### Verify if broadcast address cannot be assigned as a '''
          '''nexthop ###\n''')
    sw1('ip route 255.255.255.0/24 255.255.255.255')
    ret = sw1('do show running-config')
    assert not 'ip route 255.255.255.0/24 255.255.255.255' in ret, \
            'Broadcast address check for nexthop failed'

    step(''' ### Verify if multicast starting address range cannot be '''
         ''' assigned as a prefix ###\n''')
    sw1('ip route 224.10.1.0/24 223.10.1.1')
    ret = sw1('do show running-config')
    assert not 'ip route 224.10.1.0/24 223.10.1.1' in ret, \
            'Multicast address check for prefix failed'

    step(''' ### Verify if multicast starting address range cannot be '''
         '''assigned as a nexthop ###\n''')
    sw1('ip route 223.10.1.0/24 224.10.1.1')
    ret = sw1('do show running-config')
    assert not 'ip route 223.10.1.0/24 224.10.1.1' in ret, \
            'Multicast address check for nexthop failed'

    step(''' ### Verify if multicast ending address range cannot be '''
         '''assigned as a prefix ###\n''')
    sw1('ip route 239.10.1.0/24 223.10.1.1')
    ret = sw1('do show running-config')
    assert not 'ip route 239.10.1.0/24 223.10.1.1' in ret, \
            'Multicast address check for prefix failed'

    step(''' ### Verify if multicast ending address range cannot be '''
         '''assigned as a nexthop ###\n''')
    sw1('ip route 223.10.1.0/24 239.10.1.1')
    ret = sw1('do show running-config')
    assert not 'ip route 223.10.1.0/24 239.10.1.1' in ret, \
            'Multicast address check for nexthop failed'

    step(''' ### Verify if loopback address cannot be assigned as a prefix'''
         ''' ###\n''')
    sw1('ip route 127.10.1.0/24 128.1.1.1')
    ret = sw1('do show running-config')
    assert not 'ip route 127.10.1.0/24 128.1.1.1' in ret, \
            'Loopback address check for prefix failed'

    step(''' ### Verify if loopback address cannot be assigned as a nexthop'''
         ''' ###\n''')
    sw1('ip route 128.10.1.0/24 127.10.1.10')
    ret = sw1('do show running-config')
    assert not 'ip route 128.10.1.0/24 127.10.1.10' in ret, \
            'Loopback address check for nexthop failed'

    step(''' ### Verify if unspecified address cannot be assigned as a '''
         '''nexthop ###\n''')
    sw1('ip route 128.10.1.0/24 0.0.0.0')
    ret = sw1('do show running-config')
    assert not 'ip route 128.10.1.0/24 0.0.0.0' in ret, \
            'Unspecified address check for nexthop failed'
