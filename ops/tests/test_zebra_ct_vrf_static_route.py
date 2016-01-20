#!/usr/bin/env python

# Copyright (C) 2016 Hewlett Packard Enterprise Development LP
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

import pytest
import re
from opstestfw import *
from opstestfw.switch.CLI import *
from opstestfw.switch import *

#
# The purpose of this test is to verify
# if VRF static routes are configured and unconfigured correctly
# and the route table is getting updated accordingly.
# For this test, we need below topology
#
#       +---+----+
#       |        |
#       +switch1 |
#       |(Client)|
#       |        |
#       +---+----+
#

# Topology definition
topoDict = {"topoExecution": 1000,
            "topoTarget": "dut01",
            "topoDevices": "dut01",
            "topoFilters": "dut01:system-category:switch"}


def vrf_static_routes(dut01):

    retStruct = dut01.VtyshShell(enter=True)
    retCode = retStruct.returnCode()
    assert retCode == 0, "Failed to enter vtysh prompt"

    red_vrf = None

    #configure vrf
    LogOutput('info', "Configuring VRF")
    dut01.DeviceInteract(command="configure terminal")
    devIntReturn = dut01.DeviceInteract(command="vrf red")
    retCode = devIntReturn.get('returnCode')
    assert retCode == 0, "VRF config failed"
    dut01.DeviceInteract(command="exit")

    #attach interface to vrf
    LogOutput('info', "Attaching interface to VRF")
    dut01.DeviceInteract(command="configure terminal")
    devIntReturn = dut01.DeviceInteract(command="interface 1")
    devIntReturn = dut01.DeviceInteract(command="vrf attach red")
    retCode = devIntReturn.get('returnCode')
    assert retCode == 0, "VRF Interface attach config failed"
    devIntReturn = dut01.DeviceInteract(command="ip add 22.22.22.1/24")
    retCode = devIntReturn.get('returnCode')
    assert retCode == 0, "VRF Interface ip config failed"
    devIntReturn = dut01.DeviceInteract(command="no shut")
    retCode = devIntReturn.get('returnCode')
    assert retCode == 0, "VRF Interface config failed"
    dut01.DeviceInteract(command="exit")

    #configure static route
    LogOutput('info', "configuring VRF static routes")

    devIntReturn = dut01.DeviceInteract(command="ip route 10.10.10.0/24 22.22.22.2 vrf red")
    retCode = devIntReturn.get('returnCode')
    assert retCode == 0, "VRF static config failed"

    dut01.DeviceInteract(command="exit")
    LogOutput('info', "VRF static routes configured")

    #verify static route configured
    out = dut01.DeviceInteract(command="sh running")
    retBuffer = out.get('buffer')
    LogOutput('info', retBuffer)
    assert 'ip route 10.10.10.0/24 22.22.22.2 vrf red' in retBuffer, \
    "VRF static routes running config - failed"
    LogOutput('info', "VRF static routes running config - passed")

    out = dut01.DeviceInteract(command="sh ip route vrf red")
    retBuffer = out.get('buffer')
    LogOutput('info', retBuffer)
    assert 'via  22.22.22.2,  [1/0],  static' in retBuffer, \
    " VRF static routes not configured - failed"
    LogOutput('info', "VRF static routes configured - passed")

    out = dut01.DeviceInteract(command="sh rib vrf red")
    retBuffer = out.get('buffer')
    LogOutput('info', retBuffer)
    assert '*via  22.22.22.2,  [1/0],  static' in retBuffer, \
    "VRF static rib routes not configured - failed"
    LogOutput('info', "VRF static rib routes configured - passed")

    #verify route configured in kernel
    out = dut01.DeviceInteract(command="start-shell")
    retCode = out.get('returnCode')
    assert retCode == 0, "Failed to enter shell prompt"

    buff = dut01.DeviceInteract(command="ip netns")
    out = buff.get('buffer')
    lines = out.split('\n')
    for line in lines:
        if "nonet" not in line and "swns" not in  \
                line and "netns" not in line and "default" not in line:
          red_vrf = line.strip()
          LogOutput('info', "### Got namespace "+ str(red_vrf) +" ###")
          break


    assert red_vrf is not None, "Failed to get namespace from kernel"

    out = dut01.DeviceInteract(command="ip netns exec " + red_vrf + \
                                         " route -n ")
    retBuffer = out.get('buffer')
    LogOutput('info', retBuffer)

    assert '10.10.10.0      22.22.22.2      255.255.255.0   UG' in \
      out.get('buffer'), "Failed to configure static route in Kernel"

    LogOutput('info', "Static route configured in Kernel -- passed")

    devIntRetStruct = dut01.DeviceInteract(command="exit")
    retCode = devIntRetStruct.get('returnCode')
    assert retCode == 0, "Failed to come out of shell"


    #no attach interface from vrf
    LogOutput('info', "Removing interface from VRF")
    dut01.DeviceInteract(command="configure terminal")
    devIntReturn = dut01.DeviceInteract(command="interface 1")
    devIntReturn = dut01.DeviceInteract(command="no vrf attach red")
    retCode = devIntReturn.get('returnCode')
    assert retCode == 0, "VRF Interface no attach config failed"
    dut01.DeviceInteract(command="exit")
    dut01.DeviceInteract(command="exit")

    out = dut01.DeviceInteract(command="sh ip route vrf red")
    retBuffer = out.get('buffer')
    LogOutput('info', retBuffer)
    assert 'via  22.22.22.2,  [1/0],  static' not in retBuffer, \
    "VRF static routes present in route table - failed"
    LogOutput('info', "VRF static routes not present in route table - passed")

    out = dut01.DeviceInteract(command="sh rib vrf red")
    retBuffer = out.get('buffer')
    LogOutput('info', retBuffer)
    assert '*via  22.22.22.2,  [1/0],  static' not in retBuffer, \
    "VRF static routes present in rib table - failed"
    LogOutput('info', "VRF static routes not present in rib table - passed")

    #verify route unconfigured in kernel
    out = dut01.DeviceInteract(command="start-shell")
    retCode = out.get('returnCode')
    assert retCode == 0, "Failed to enter shell prompt"

    assert red_vrf is not None, "Failed to get namespace from kernel"

    out = dut01.DeviceInteract(command="ip netns exec " + red_vrf + \
                                         " route -n ")
    retBuffer = out.get('buffer')
    LogOutput('info', retBuffer)

    assert '10.10.10.0      22.22.22.2      255.255.255.0   UG' not in \
      out.get('buffer'), "Failed to unconfigure static route in Kernel"

    LogOutput('info', "Static route unconfigured in Kernel -- passed")

    devIntRetStruct = dut01.DeviceInteract(command="exit")
    retCode = devIntRetStruct.get('returnCode')
    assert retCode == 0, "Failed to come out of shell"

    #attach interface to back to vrf
    LogOutput('info', "Attaching interface to VRF")
    dut01.DeviceInteract(command="configure terminal")
    devIntReturn = dut01.DeviceInteract(command="interface 1")
    devIntReturn = dut01.DeviceInteract(command="vrf attach red")
    retCode = devIntReturn.get('returnCode')
    assert retCode == 0, "VRF Interface attach config failed"
    devIntReturn = dut01.DeviceInteract(command="ip add 22.22.22.1/24")
    retCode = devIntReturn.get('returnCode')
    assert retCode == 0, "VRF Interface ip config failed"
    devIntReturn = dut01.DeviceInteract(command="no shut")
    retCode = devIntReturn.get('returnCode')
    assert retCode == 0, "VRF Interface config failed"
    dut01.DeviceInteract(command="exit")

    #configure static route
    LogOutput('info', "configuring VRF static routes")

    devIntReturn = dut01.DeviceInteract(command="ip route 10.10.10.0/24 22.22.22.2 vrf red")
    retCode = devIntReturn.get('returnCode')
    assert retCode == 0, "VRF static config failed"

    dut01.DeviceInteract(command="exit")
    LogOutput('info', "VRF static routes configured")

    #verify db tables
    out = dut01.DeviceInteract(command="sh ip route vrf red")
    retBuffer = out.get('buffer')
    LogOutput('info', retBuffer)
    assert 'via  22.22.22.2,  [1/0],  static' in retBuffer, \
    " VRF static routes not configured - failed"
    LogOutput('info', "VRF static routes configured - passed")

    out = dut01.DeviceInteract(command="sh rib vrf red")
    retBuffer = out.get('buffer')
    LogOutput('info', retBuffer)
    assert '*via  22.22.22.2,  [1/0],  static' in retBuffer, \
    "VRF static rib routes not configured - failed"
    LogOutput('info', "VRF static rib routes configured - passed")

    #verify route configured in kernel
    out = dut01.DeviceInteract(command="start-shell")
    retCode = out.get('returnCode')
    assert retCode == 0, "Failed to enter shell prompt"

    assert red_vrf is not None, "Failed to get namespace from kernel"

    out = dut01.DeviceInteract(command="ip netns exec " + red_vrf + \
                                         " route -n ")
    retBuffer = out.get('buffer')
    LogOutput('info', retBuffer)

    assert '10.10.10.0      22.22.22.2      255.255.255.0   UG' in \
      out.get('buffer'), "Failed to configure static route in Kernel"

    LogOutput('info', "Static route configured in Kernel -- passed")

    devIntRetStruct = dut01.DeviceInteract(command="exit")
    retCode = devIntRetStruct.get('returnCode')
    assert retCode == 0, "Failed to come out of shell"

    #unconfigure static route
    LogOutput('info', "===Unconfiguring VRF static routes===")

    dut01.DeviceInteract(command="configure terminal")
    devIntReturn = dut01.DeviceInteract(command="no ip route 10.10.10.0/24 22.22.22.2 vrf red")
    retCode = devIntReturn.get('returnCode')
    assert retCode == 0, "VRF static unconfig failed"

    dut01.DeviceInteract(command="exit")
    LogOutput('info', "VRF static routes unconfigured")

    out = dut01.DeviceInteract(command="sh running")
    retBuffer = out.get('buffer')
    LogOutput('info', retBuffer)
    assert 'ip route 10.10.10.0/24 22.22.22.2 vrf red' not in retBuffer, \
    "VRF static routes present in running config - failed"
    LogOutput('info', "VRF static routes not present running config - passed")

    out = dut01.DeviceInteract(command="sh ip route vrf red")
    retBuffer = out.get('buffer')
    LogOutput('info', retBuffer)
    assert 'via  22.22.22.2,  [1/0],  static' not in retBuffer, \
    "VRF static routes present in route table - failed"
    LogOutput('info', "VRF static routes not present in route table - passed")

    out = dut01.DeviceInteract(command="sh rib vrf red")
    retBuffer = out.get('buffer')
    LogOutput('info', retBuffer)
    assert '*via  22.22.22.2,  [1/0],  static' not in retBuffer, \
    "VRF static routes present in rib table - failed"
    LogOutput('info', "VRF static routes not present in rib table - passed")

    #verify route unconfigured in kernel
    out = dut01.DeviceInteract(command="start-shell")
    retCode = out.get('returnCode')
    assert retCode == 0, "Failed to enter shell prompt"

    assert red_vrf is not None, "Failed to get namespace from kernel"

    out = dut01.DeviceInteract(command="ip netns exec " + red_vrf + \
                                         " route -n ")
    retBuffer = out.get('buffer')
    LogOutput('info', retBuffer)

    assert '10.10.10.0      22.22.22.2      255.255.255.0   UG' not in \
      out.get('buffer'), "Failed to unconfigure static route in Kernel"

    LogOutput('info', "Static route unconfigured in Kernel -- passed")

    devIntRetStruct = dut01.DeviceInteract(command="exit")
    retCode = devIntRetStruct.get('returnCode')
    assert retCode == 0, "Failed to come out of shell"

@pytest.mark.skipif(True, reason="Skipping VRF static route CT temporarily till"
                    " all code changes related to VRF are merged.")
class Test_vrf_static_routes:
    def setup_class(cls):
        # Test object will parse command line and formulate the env
        Test_vrf_static_routes.testObj =\
            testEnviron(topoDict=topoDict, defSwitchContext="vtyShell")
        #    Get topology object
        Test_vrf_static_routes.topoObj = \
            Test_vrf_static_routes.testObj.topoObjGet()

    def teardown_class(cls):
        Test_vrf_static_routes.topoObj.terminate_nodes()

    def test_feature(self):
        dut01Obj = self.topoObj.deviceObjGet(device="dut01")
        vrf_static_routes(dut01Obj)
