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


def route_exists(switch, next_hop, bgp_network):
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
    if exists:
        route_exists(switch, next_hop, bgp_network)
    else:
        route_not_exists(switch, next_hop, bgp_network)


def get_route_and_nexthops_from_output(output, route, route_type):
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
    dict_from_show = get_route_from_show(sw1,
                                         route,
                                         route_type,
                                         show)
    for key in dict_from_show.keys():
        assert key in p_dict
        assert dict_from_show[key] == p_dict[key]


def if_config_in_running_config(**kwargs):
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

__all__ = ["wait_for_route", "verify_show",
           "route_and_nexthop_in_show_running_config"]
