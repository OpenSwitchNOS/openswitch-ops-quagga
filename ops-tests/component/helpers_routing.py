# -*- coding: utf-8 -*-

# (c) Copyright 2015 Hewlett Packard Enterprise Development LP
#
# GNU Zebra is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2, or (at your option) any
# later version.
#
# GNU Zebra is distributed in the hope that it will be useful, but
# WITHoutput ANY WARRANTY; withoutput even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Zebra; see the file COPYING.  If not, write to the Free
# Software Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.


from time import sleep
from re import match


IPV4_STATIC_ROUTE = "ipv4_static_route"
IPV6_STATIC_ROUTE = "ipv6_static_route"
IPV4_ROUTE = "ip route"
IPV6_ROUTE = "ipv6 route"
RIB = "rib"


def route_exists(switch, next_hop, bgp_network):
    """
    Checks if route exists.

    :param switch: device to check.
    :type enode: topology.platforms.base.BaseNode
    :param str next_hop: IPv4 or IPv6 address to check on route:
     - IPv4 address to check on route:
     ``'192.168.20.20'``.
     - IPv6 address to check on route:
     ``'2001::1'``.
    :param str network: IPv4 or IPv6 address to check on route:
     - IPv4 address to check on route:
     ``'192.168.20.20'``.
     - IPv6 address to check on route:
     ``'2001::1'``.
    """
    route_exists = False
    route_max_wait_time = 300
    while route_max_wait_time > 0 and not route_exists:
        output = switch("do show ip bgp")
        lines = output.splitlines()
        for line in lines:
            if bgp_network in line and next_hop in line:
                route_exists = True
                break
        sleep(1)
        route_max_wait_time -= 1
    assert route_exists


def route_not_exists(switch, next_hop, bgp_network):
    """
    Checks if route does not exists.

    :param switch: device to check.
    :type enode: topology.platforms.base.BaseNode
    :param str next_hop: IPv4 or IPv6 address to check is not on route:
     - IPv4 address to check is not on route:
     ``'192.168.20.20'``.
     - IPv6 address to check is not on route:
     ``'2001::1'``.
    :param str network: IPv4 or IPv6 address to check is not on route:
     - IPv4 address to check is not on route:
     ``'192.168.20.20'``.
     - IPv6 address to check is not on route:
     ``'2001::1'``.
    """
    route_exists = True
    route_max_wait_time = 300
    while route_max_wait_time > 0 and route_exists:
        output = switch("do show ip bgp")
        lines = output.splitlines()
        for line in lines:
            if bgp_network in line and next_hop in line:
                break
        else:
            route_exists = False
        sleep(1)
        route_max_wait_time -= 1
    assert not route_exists


def wait_for_route(switch, next_hop, bgp_network, exists=True):
    """
    Checks the existance or non-existance of a route in a switch.

    :param switch: device to check.
    :type enode: topology.platforms.base.BaseNode
    :param str next_hop: IPv4 or IPv6 address to check on route:
    - IPv4 address to check on route:
    ``'192.168.20.20'``.
    - IPv6 address to check on route:
    ``'2001::1'``.
    :param str network: IPv4 or IPv6 address to check on route:
    - IPv4 address to check on route:
    ``'192.168.20.20'``.
    - IPv6 address to check on route:
    ``'2001::1'``.
    :param bool exists: True looks for existance and False for
    non-existance of a route.
    """
    if exists:
        route_exists(switch, next_hop, bgp_network)
    else:
        route_not_exists(switch, next_hop, bgp_network)


def get_route_and_nexthops_from_output(output, route, route_type):
    """
    Library function to get the show dump for a route in the command
    "show ip route/show ipv6 route/show rib".

    :param output    : Output of either of the show commands
                       "show ip route/show ipv6 route/show rib"
    :type output     : string
    :param route     : Route which is of the format "Prefix/Masklen"
    :type  route     : string
    :param route_type : Route type which can be "static/BGP"
    :type  route_type : string
    :return: string
    """
    found_route = False
    found_nexthop = False
    lines = output.splitlines()
    route_output = ''
    for line in lines:
        if not found_route:
            if route in line:
                found_route = True
                route_output = "{}{}\n".format(route_output, line)
        else:
            if 'via' in line and route_type in line:
                route_output = "{}{}\n".format(route_output, line)
                found_nexthop = True
            else:
                if not found_nexthop:
                    found_route = False
                    route_output = ''
                else:
                    break
    return route_output


def get_route_from_show(sw1, route, route_type, show):
    """
    Library function to get the show dump for a route in the command
    "show ip route/show ipv6 route/show rib".

    :param sw1 : Device object
    :type  sw1 : topology.platforms.base.BaseNode
    :param route     : Route which is of the format "Prefix/Masklen"
    :type  route     : string
    :param routetype : Route type which can be "static/BGP"
    :type  routetype : string
    :param show : type of show to be checked
    :type show : string
    :return: Dictionary
            data keys
                Route - string set to route which is of the format
                        "Prefix/Masklen"
                NumberNexthops - string set to the number of next-hops
                                 of the route
                Next-hop - string set to the next-hop port or IP/IPv6
                           address as the key and a dictionary as value
                data keys
                    Distance:String whose numeric value is the administration
                             distance of the next-hop
                    Metric:String whose numeric value is the metric of the
                           next-hop
                    RouteType:String which is the route type of the next-hop
                              which is among "static/BGP"
    :returntype: dictionary
    """
    show_output = sw1("do show {}".format(show))
    route_output = get_route_and_nexthops_from_output(show_output,
                                                      route, route_type)
    route_dict = dict()
    route_dict['Route'] = route
    lines = route_output.splitlines()
    for line in lines:
        routeline = match("(.*)(%s)(,  )(\d+)( unicast next-hops)"
                          "".format(route), line)
        if routeline:
            route_dict['Route'] = routeline.group(2)
            route_dict['NumberNexthops'] = routeline.group(4)
        nexthop = match("(.+)via  ([0-9.:]+),  \[(\d+)/(\d+)\],  (.+)",
                        line)
        if nexthop:
            route_dict[nexthop.group(2)] = dict()
            route_dict[nexthop.group(2)]['Distance'] = nexthop.group(3)
            route_dict[nexthop.group(2)]['Metric'] = nexthop.group(4)
            aux_nexthop = nexthop.group(5).rstrip('\r')
            route_dict[nexthop.group(2)]['RouteType'] = aux_nexthop
    return route_dict


def verify_show(sw1, route, route_type, p_dict, show):
    """
    Library function tests whether a route ("prefix/mask-length") in the
    command "show ip route/show ipv6 route/show rib" exactly matches an
    expected route dictionary that is passed to this function. In case the
    route dictionary returned by 'get_route_from_show' is not the same as
    the expected route dictionary, then this function will fail.

    :param sw1 : Device object
    :type  sw1 : topology.platforms.base.BaseNode
    :param route : IPV4/IPV6 address that must be verified
    :type route : string
    :param p_dict: Expected route dictionary
    :type  p_dict: dictionary
    :param route_type : Route type which can be "static/BGP"
    :type  route_type : string
    :param show : type of show to be checked
    :type show : string
    """
    dict_from_show = get_route_from_show(sw1,
                                         route,
                                         route_type,
                                         show)
    for key in dict_from_show.keys():
        assert key in p_dict
        assert dict_from_show[key] == p_dict[key]


def verify_show_ip_route(sw1, route, route_type, p_dict):
    """
    Library function tests whether a route ("prefix/mask-length") in the
    command "show ip route" exactly matches an expected route dictionary
    that is passed to this function. It will be used as a wrapper to the
    function "verify_show".

    :param sw1 : Device object
    :type  sw1 : topology.platforms.base.BaseNode
    :param route : IPV4/IPV6 address that must be verified
    :type route : string
    :param p_dict: Expected route dictionary
    :type  p_dict: dictionary
    :param route_type : Route type which can be "static/BGP"
    :type  route_type : string
    """
    verify_show(sw1, route, route_type, p_dict, IPV4_ROUTE)


def verify_show_ipv6_route(sw1, route, route_type, p_dict):
    """
    Library function tests whether a route ("prefix/mask-length") in the
    command "show ipv6 route" exactly matches an expected route dictionary
    that is passed to this function. It will be used as a wrapper to the
    function "verify_show".

    :param sw1 : Device object
    :type  sw1 : topology.platforms.base.BaseNode
    :param route : IPV4/IPV6 address that must be verified
    :type route : string
    :param p_dict: Expected route dictionary
    :type  p_dict: dictionary
    :param route_type : Route type which can be "static/BGP"
    :type  route_type : string
    """
    verify_show(sw1, route, route_type, p_dict, IPV6_ROUTE)


def verify_show_rib(sw1, route, route_type, p_dict):
    """
    Library function tests whether a route ("prefix/mask-length") in the
    command "show rib" exactly matches an expected route dictionary that is
    passed to this function. It will be used as a wrapper to the function
    "verify_show".

    :param sw1 : Device object
    :type  sw1 : topology.platforms.base.BaseNode
    :param route : IPV4/IPV6 address that must be verified
    :type route : string
    :param p_dict: Expected route dictionary
    :type  p_dict: dictionary
    :param route_type : Route type which can be "static/BGP"
    :type  route_type : string
    """
    verify_show(sw1, route, route_type, p_dict, RIB)


def if_config_in_running_config(**kwargs):
    """
    Library function to checks whether a given configuration exists
    in the "show running-config" output or not. If the configuration
    exists in the "show running-config", then this function returns 'True'
    otherwise this function will return 'False'.

    :param sw1 : Device object
    :type  sw1 : topology.platforms.base.BaseNode
    :param configtype : Configuration type that the user wants to tests
                        in the "show running-config" output. This should
                        be a string. The configtype can be only one of
                        the following string:-
                        IPv4 static route configuration: "ipv4_static_route"
                        IPv6 static route configuration: "ipv6_static_route"
    :type configtype: string
    :param route     : Route which is of the format "Prefix/Masklen"
    :type  route     : string
    :param nexthop   : Nexthop which is of the format "IP/IPv6 address" or
                       "Port number"
    :type nexthop    : string
    :param distance  : Administration distance of the route
    :type distance   : string
    :return type: Boolean
    """
    sw1 = kwargs.get('sw1', None)
    config_type = kwargs.get('config_type', None)
    running_config_string = ''
    if config_type is IPV4_STATIC_ROUTE or config_type is IPV6_STATIC_ROUTE:
        route = kwargs.get('route', None)
        nexthop = kwargs.get('nexthop', None)
        distance = kwargs.get('distance', None)
        if config_type is IPV4_STATIC_ROUTE:
            if distance is None:
                running_config_string = 'ip route {} {}'.format(route,
                                                                nexthop)
            else:
                running_config_string = 'ip route {} {} {}'.format(route,
                                                                   nexthop,
                                                                   distance)
        else:
            if distance is None:
                running_config_string = 'ipv6 route {} {}'.format(route,
                                                                  nexthop)
            else:
                running_config_string = 'ipv6 route {} {} '
                '{}'.format(route,
                            nexthop,
                            distance)
    show_running_config = sw1("do show running-config")
    show_running_config_lines = show_running_config.split('\n')
    found = False
    for line in show_running_config_lines:
        if running_config_string in line:
            found = True
            break
    return found


def route_and_nexthop_in_show_running_config(**kwargs):
    """
    Library function tests whether a static route with "prefix/mask-length",
    next-hop and administration distance does not exists in the command
    "show running-config". If such a static route configuration exists in the
    output of "show running-config" output, then this function fails this will
    return False, otherwise True.

    :param sw1 : Device object
    :type  sw1 : topology.platforms.base.BaseNode
    :param if_ipv4   : If the route passed is IPv4 or IPv6 route. If
                       the route passed in IPv4, then if_ipv4 should
                       be 'True' otherwise it should be 'False'
    :type  if_ipv4   : boolean
    :param route     : route is of the format "prefix/mask-length"
    :type  route     : string
    :param nexthop   : Nexthop which is of the format "IP/IPv6 address" or
                       "Port number"
    :type nexthop    : string
    :param distance  : Administration distance of the route
    :type distance   : string
    :return type : Boolean
    """
    sw1 = kwargs.get('sw1', None)
    if_ipv4 = kwargs.get('if_ipv4', None)
    route = kwargs.get('route', None)
    nexthop = kwargs.get('nexthop', None)
    distance = kwargs.get('distance', None)
    if if_ipv4 is True:
        return if_config_in_running_config(sw1=sw1,
                                           config_type=IPV4_STATIC_ROUTE,
                                           route=route,
                                           nexthop=nexthop,
                                           distance=distance)
    else:
        return if_config_in_running_config(sw1=sw1,
                                           config_type=IPV6_STATIC_ROUTE,
                                           route=route,
                                           nexthop=nexthop,
                                           distance=distance)

__all__ = ["wait_for_route", "verify_show_ip_route",
           "verify_show_ipv6_route", "verify_show_rib",
           "route_and_nexthop_in_show_running_config"]
