#!/usr/bin/python

# (c) Copyright 2015 Hewlett Packard Enterprise Development LP
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

from opstestfw import *
from opstestfw.switch.CLI import *
from opstestfw.switch.OVS import *
import re
import pprint

def get_route_from_show_kernel_route(**kwargs):

    """
    Library function to get the show dump for a route in the linux
    command "ip -6 route/ip -6 route" in swns namespace.

    :param deviceObj : Device object
    :type  deviceObj : object
    :param if_ipv4   : If the route passed is IPv4 or IPv6 route. If
                       the route passed in IPv4, then if_ipv4 should
                       be 'True' otherwise it should be 'False'
    :type  if_ipv4   : boolean
    :param route     : Route which is of the format "Prefix/Masklen"
    :type  route     : string
    :param routetype : Route type which can be "static/BGP"
    :type  routetype : string
    :return: returnStruct Object
            buffer
            data keys
                Route - string set to route which is of the format
                        "Prefix/Masklen"
                NumberNexthops - string set to the number of next-hops
                                 of the route
                Next-hop - string set to the next-hop port or IP/IPv6
                           address as the key and a dictionary as value
                data keys
                    Distance - String whose numeric value is the administration
                               distance of the next-hop
                    Metric - String whose numeric value is the metric of the
                             next-hop
                    RouteType - String which is the route type of the next-hop
                                which is among "static/BGP"
    :returnType: object
    """
    overallBuffer = []
    deviceObj = kwargs.get('deviceObj', None)
    if_ipv4 = kwargs.get('if_ipv4', True)
    route = kwargs.get('route', None)
    routetype = kwargs.get('routetype', None)

    # If Device object is not passed, we need to error out
    if deviceObj is None:
        opstestfw.LogOutput('error',
                            "Need to pass switch device object deviceObj "
                            "to this routine")
        returnCls = opstestfw.returnStruct(returnCode=1)
        return returnCls

    # If route object is not passed, we need to error out
    if route is None:
        opstestfw.LogOutput('error',
                            "Need to pass route to this routine")
        returnCls = opstestfw.returnStruct(returnCode=1)
        return returnCls

    # If route type object is not passed, we need to error out
    if routetype is None:
        opstestfw.LogOutput('error',
                            "Need to pass route type to this routine")
        returnCls = opstestfw.returnStruct(returnCode=1)
        return returnCls

    # if 'if_ipv4' is 'True', then the command to be executed is
    # "ip route list <route>" otherwise the command is
    # "ip -6 route list <route>"
    if if_ipv4 is True:
        kernel_route_command = "ip netns exec swns ip route list " + route
    else:
        kernel_route_command = "ip netns exec swns ip -6 route list " + route

    # Execute the "command" on the Linux bash interface
    devIntRetStruct = deviceObj.DeviceInteract(command=kernel_route_command)
    retCode = devIntRetStruct.get('returnCode')
    kernel_route_buffer = devIntRetStruct.get('buffer')

    if retCode != 0:
        assert "Failed to dump the kernel route"

    # Initialize the return route dictionary
    RouteDict = dict()

    # Add the prefix and the mask length of the route in the return
    # dictionary
    RouteDict['Route'] = route

    # Split the route into prefix and mask length
    [prefix, masklen] = route.split('/')

    # If the route is 10.0.0.0/32 or 123::1/128, then it appears in
    # kernel "ip route/ip -6 route" as:-
    # 10.0.0.0/32 -> 10.0.0.0
    # 123::1/128 -> 123::1
    #
    # If the route is 10.0.0.0/34 or 123:1::/64, then it appears in
    # kernel "ip route/ip -6 route" as:-
    # 10.0.0.0/24 -> 10.0.0.0/24
    # 123:1::/64 -> 123:1::/64
    #
    #That's why the logic below is put to handle this case.
    route_string = ""
    if if_ipv4 == True:
        if int(masklen) >= 32:
            route_string = prefix
        else:
            route_string = route
    else:
        if int(masklen) >= 128:
            route_string = prefix
        else:
            route_string = route

    lines = kernel_route_buffer.split('\n')

    nexthop_number = 0
    if_route_found = False

    # populate the return route distionary
    for line in lines:

        commandLine = re.match("ip netns exec swns ip", line)

        if commandLine:
            continue

        routeline = re.match("(%s)(.*)(proto %s)" %(route_string, routetype), line)

        nexthop_string = ""

        if routeline:

            if_route_found = True

            nexthopipline = re.match("(.*)via (.*)( )dev(.*)", line)

            if nexthopipline:
                nexthop_string = nexthopipline.group(2)
            else :
                nexthopifline = re.match("(.*)dev (\d+) (.*)", line)

                if nexthopifline:
                    nexthop_string = nexthopifline.group(2)

        nexthopipline = re.match("(.*)nexthop via (.*)( )dev(.*)", line)

        if nexthopipline:
            nexthop_string = nexthopipline.group(2)

        nexthopifline = re.match("(.*)nexthop dev (\d+) (.*)", line)

        if nexthopifline:
            nexthop_string = nexthopifline.group(2)

        if len(nexthop_string) > 0 and if_route_found == True:

            RouteDict[nexthop_string.rstrip(' ')] = dict()
            RouteDict[nexthop_string.rstrip(' ')]['Distance'] = ""
            RouteDict[nexthop_string.rstrip(' ')]['Metric'] = ""
            RouteDict[nexthop_string.rstrip(' ')]['RouteType'] = routetype

            nexthop_number = nexthop_number + 1

    if nexthop_number > 0:
        RouteDict['NumberNexthops'] = str(nexthop_number)

    # Walk through all the lines of the route output for the route and
    # Return results in the form of the structure 'returnCls'
    bufferString = ""
    for curLine in overallBuffer:
        bufferString += str(curLine)
    returnCls = returnStruct(
        returnCode=0,
        buffer=bufferString,
        data=RouteDict)
    return returnCls


def verify_route_in_show_kernel_route(switch, if_ipv4, ExpRouteDictKernelRoute,
                                      RouteType):
    """
    Library function tests whether a route ("prefix/mask-length") in the
    linux command "ip route/ip -6 route" exactly matches an expected route
    dictionary that is passed to this function. In case the route dictionary
    returned by 'get_route_from_show_kernel_route()' is not same as the expected
    route dictionary, then this function will fail the test case by calling assert().

    :param deviceObj : Device object
    :type  deviceObj : object
    :param if_ipv4   : If the route passed is IPv4 or IPv6 route. If
                       the route passed in IPv4, then if_ipv4 should
                       be 'True' otherwise it should be 'False'
    :type  if_ipv4   : boolean
    :param ExpRouteDictStaticRoute: Expected route dictionary
    :type  ExpRouteDictStaticRoute: dictionary
    :param routetype : Route type which is zebra
    :type  routetype : string
    """

    LogOutput('info', "\nCheck kernel route table for "
              + ExpRouteDictKernelRoute['Route'])

    # Get the actual route dictionary for the route
    retStruct = get_route_from_show_kernel_route(deviceObj=switch, if_ipv4=if_ipv4, route=ExpRouteDictKernelRoute['Route'],
                                          routetype=RouteType)

    # If there was error getting the actual route dictionary, then assert and
    # fail the test case
    retCode = retStruct.returnCode()
    assert retCode == 0, "Failed to get the dictionary for route " + ExpRouteDictKernelRoute['Route'] + " and route type " + RouteType

    # Get the actual route dictionary from the returned object
    ActualRouteDictKernelRoute = retStruct.data

    # Print the actual and expected route dictionaries for debugging purposes
    LogOutput('info', "\nThe expected kernel route dictionary is: "
              + str(pprint.pprint(ExpRouteDictKernelRoute, width=1)))
    LogOutput('info', "\nThe actual kernel route dictionary is: "
              + str(pprint.pprint(ActualRouteDictKernelRoute, width=1)))

    # Assert if the two route dictionaries are not equal
    assert cmp(ExpRouteDictKernelRoute, ActualRouteDictKernelRoute) == 0, "Verfication failed for the route " + ExpRouteDictKernelRoute['Route']
