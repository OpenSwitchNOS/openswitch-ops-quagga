# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016 Hewlett Packard Enterprise Development LP
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

"""
Component test to verify zebra diagnostic commands.
"""

TOPOLOGY = """
#
#
# +-------+
# +  sw1  +
# +-------+
#
#

# Nodes
[type=openswitch name="Switch 1"] sw1

"""

def test_zebra_diag_dump(topology, step):
    '''
    This test verifies various diagnostic commands related to zebra daemon
    by verifying if the output of the commands have the expected keywords.
    '''
    sw1 = topology.get('sw1')

    assert sw1 is not None

    step('### Testing output of "ovs-appctl -t ops-zebra zebra/dump rib" ###')
    output = sw1("ovs-appctl -t ops-zebra zebra/dump rib", shell="bash")
    assert '-------- Zebra internal IPv4 routes dump: --------' in output
    assert '-------- Zebra internal IPv6 routes dump: --------' in output

    step('### Testing output of "ovs-appctl -t ops-zebra zebra/dump kernel-routes" ###')
    output = sw1("ovs-appctl -t ops-zebra zebra/dump kernel-routes", shell="bash")
    assert '-------- Kernel IPv4 routes dump: --------' in output
    assert '-------- Kernel IPv6 routes dump: --------' in output

    step('### Testing output of "ovs-appctl -t ops-zebra zebra/dump l3-port-cache" ###')
    output = sw1("ovs-appctl -t ops-zebra zebra/dump l3-port-cache", shell="bash")
    assert '-------- Zebra L3 port cache dump: --------' in output
    assert 'Walking the L3 port cache to print all L3 ports in permanent cache' in output
    assert 'Walking the L3 port cache to print all L3 ports in temporary cache' in output

    step('### Testing output of "ovs-appctl -t ops-zebra zebra/dump memory" ###')
    output = sw1("ovs-appctl -t ops-zebra zebra/dump memory", shell="bash")
    assert '-------- Zebra memory dump: --------' in output

    step('### Testing output of CLI command "diag-dump route-manager basic" ###')
    output = sw1('diag-dump route-manager basic')
    assert '-------- Zebra internal IPv4 routes dump: --------' in output
    assert '-------- Zebra internal IPv6 routes dump: --------' in output
    assert '-------- Kernel IPv4 routes dump: --------' in output
    assert '-------- Kernel IPv6 routes dump: --------' in output
    assert 'Walking the L3 port cache to print all L3 ports in permanent cache' in output
    assert 'Walking the L3 port cache to print all L3 ports in temporary cache' in output
    assert '-------- Zebra memory dump: --------' in output
