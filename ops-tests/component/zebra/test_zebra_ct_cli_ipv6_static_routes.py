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


def test_ipv6_static_route_config(topology, step):
    '''
    This test verifies various ipv6 static route configurations by validating
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

    step('### Test to verify IPv6 static routes ###')
    # Configure switch 1
    sw1('configure terminal')
    sw1('interface {sw1p1}'.format(**locals()))
    sw1('ipv6 address 2000::1/120')
    sw1('no shutdown')
    sw1('exit')
    sleep(5)
    sw1('interface {sw1p2}'.format(**locals()))
    sw1('ipv6 address 2001::1/120')
    sw1('no shutdown')
    sw1('exit')
    sleep(5)

    # Configure switch 2
    sw2('configure terminal')
    sw2('interface {sw2p1}'.format(**locals()))
    sw2('ipv6 address 2000::2/120')
    sw2('no shutdown')
    sw2('exit')
    sleep(5)
    sw2('interface {sw2p2}'.format(**locals()))
    sw2('ipv6 address 2002::1/120')
    sw2('no shutdown')
    sw2('exit')
    sleep(5)

    step('### Verify ip route configuration with nexthop address ###')
    sw1('ipv6 route 2002::/120 2000::2 2')
    sleep(1)
    ret = sw1('do show ipv6 route')

    assert '2002::/120' in ret and '2000::2' in ret and 'static' \
           in ret and '[2/0]' in ret, 'IPv6 route configuration failed'

    step('### Verify deletion of ipv6 route ###')
    sw1('no ipv6 route 2002::/120 2000::2 2')
    ret = sw1('do show ipv6 route')

    assert '2002::/120' not in ret and '2000::2' not in ret \
           and 'static' not in ret and '[2/0]' not in ret, \
           'Deletion of ipv6 route failed'

    step('### Verify prefix format ###')
    sw1('ipv6 route 2002:: 2000::2 2')
    ret = sw1('do show ipv6 route')

    assert '2002::/120' not in ret and '2000::2' not in ret \
           and 'static' not in ret and '[2/0]' not in ret, \
           'Prefix format verification failed'

    step('### Verify ipv6 route configuration with nexthop interface ###')
    sw1('ipv6 route 2002::/120 2 2')
    sleep(2)
    ret = sw1('do show ipv6 route')

    assert '2002::/120' in ret and '2,' in ret and 'static' in ret \
           and '[2/0]' in ret, 'IPv6 route configuration failed'

    step('### Verify deletion of ipv6 route with nexthop interface ###')
    sw1('no ipv6 route 2002::/120 2 2')
    ret = sw1('do show ipv6 route')

    assert '2002::/120' not in ret and 'static' not in ret \
           and '[2/0]' not in ret, 'Deletion of ipv6 routes failed'

    step('### Verify setting of default distance ###')
    sw1('ipv6 route 2002::/120 2000::2')
    sleep(2)
    ret = sw1('do show ipv6 route')

    assert '2002::/120' in ret and 'static' in ret and '[1/0],' \
           in ret, 'Default distance verification failed'

    step('### Verify setting of multiple nexthops for a given prefix ###')
    sw1('ipv6 route 2002::/120 1')
    sleep(2)
    sw1('ipv6 route 2002::/120 2')
    sleep(2)
    ret = sw1('do show ipv6 route')

    assert '2002::/120' in ret and '3 unicast next-hops' in ret \
           and '1,' in ret and '2,' in ret and '[1/0]' in ret, \
           'Multiple nexthops prefix verification failed'

    step(''' ### Verify if nexthop is not assigned locally to an interface '''
         '''as a primary ipv6 address ###\n''')
    sw1('ipv6 route 2002::/120 2001::1')
    ret = sw1('do show running-config')
    assert not 'ipv6 route 2002::/120 2001::1' in ret, \
            'Primary ipv6 address check for nexthop failed'

    step(''' ### Verify if nexthop is not assigned locally to an interface '''
         '''as a secondary ipv6 address ###\n''')
    sw1('interface {sw1p1}'.format(**locals()))
    sw1('ipv6 address 2000::3/120 secondary')
    sw1('exit')
    sw1('ipv6 route 2002::/120 2000::3')
    ret = sw1('do show running-config')
    assert not 'ipv6 route 2002::/120 2000::3' in ret, \
            'Secondary ipv6 address check for nexthop failed'
    sw1('interface {sw1p1}'.format(**locals()))
    sw1('no ipv6 address 2000::2/120 secondary')
    sw1('exit')

    step(''' ### Verify if multicast address cannot be assigned as a prefix'''
         ''' ###\n''')
    sw1('ipv6 route ff00::/128 2001::1')
    ret = sw1('do show running-config')
    assert not 'ipv6 route ff00::/128 2001::1' in ret, \
            'Multicast address check for prefix failed'

    step(''' ### Verify if multicast address cannot be assigned as a nexthop'''
         ''' ###\n''')
    sw1('ipv6 route 12ff::/128 ff00::1')
    ret = sw1('do show running-config')
    assert not 'ipv6 route 12ff::/128 ff00::1' in ret, \
            'Multicast address check for nexthop failed'

    step(''' ### Verify if linklocal address cannot be assigned as a prefix'''
         ''' ###\n''')
    sw1('ipv6 route fe80::/10 2001::1')
    ret = sw1('do show running-config')
    assert not 'ipv6 route ::1/128 2001::1' in ret, \
            'Linklocal address check for prefix failed'

    step(''' ### Verify if linklocal address cannot be assigned as a nexthop'''
         ''' ###\n''')
    sw1('ipv6 route 12ff::/128 fe80::')
    ret = sw1('do show running-config')
    assert not 'ipv6 route 12ff::/128 ::1' in ret, \
            'Linklocal address check for nexthop failed'

    step(''' ### Verify if loopback address cannot be assigned as a prefix'''
         ''' ###\n''')
    sw1('ipv6 route ::1/128 2001::1')
    ret = sw1('do show running-config')
    assert not 'ipv6 route ::1/128 2001::1' in ret, \
            'Loopback address check for prefix failed'

    step(''' ### Verify if loopback address cannot be assigned as a nexthop'''
         ''' ###\n''')
    sw1('ipv6 route 12ff::/128 ::1')
    ret = sw1('do show running-config')
    assert not 'ipv6 route 12ff::/128 ::1' in ret, \
            'Loopback address check for nexthop failed'

    step(''' ### Verify if unspecified address cannot be assigned as a '''
         '''nexthop ###\n''')
    sw1('ipv6 route 2002::/120 ::')
    ret = sw1('do show running-config')
    assert not 'ipv6 route 2002::/120 ::' in ret, \
            'Unspecified address check for nexthop failed'
