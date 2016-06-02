# -*- coding: utf-8 -*-
# (C) Copyright 2016 Hewlett Packard Enterprise Development LP
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
##########################################################################


class BgpConfig():
    def __init__(self, asn, routerid, network):
        self.neighbors = []
        self.networks = []
        self.routemaps = []
        self.prefixlists = []
        self.prefixlistentries = []
        self.asn = asn
        self.routerid = routerid

        self.add_network(network)

    def add_neighbor(self, neighbor):
        self.neighbors.append(neighbor)

    def add_network(self, network):
        self.networks.append(network)

    def add_route_map(self, neighbor, prefix_list, dir, action='', metric='',
                      community=''):
        self.routemaps.append([neighbor, prefix_list, dir, action,
                               metric, community])


class PrefixList(object):
    def __init__(self, name, seq_num, action, network, prefixlen):
        self.name = name
        self.seq_num = seq_num
        self.action = action
        self.network = network
        self.prefixlen = prefixlen

__all__ = ["BgpConfig", "PrefixList"]
