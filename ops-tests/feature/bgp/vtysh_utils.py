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
# ##########################################################################


from time import sleep


vtysh_cr = "\r\n"
route_max_wait_time = 300


class SwitchVtyshUtils():
    @staticmethod
    def vtysh_cfg_cmd(switch, cfg_array, show_running_cfg=False,
                      show_results=False):
        switch("configure terminal")
        for cmd in cfg_array:
            result = switch(cmd)
        if show_results:
            print("### Config results: %s ###\n" % result)
        switch("end")

    @staticmethod
    def wait_for_route(switch, network, next_hop, condition=True,
                       print_routes=False):
        for i in range(route_max_wait_time):
            attempt = i + 1
            found = SwitchVtyshUtils.verify_bgp_route(switch, network,
                                                      next_hop, attempt,
                                                      print_routes)

            if found == condition:
                if condition:
                    result = "Route was found"
                else:
                    result = "Route was not found"

                print("### %s ###\n" % result)
                return found

            sleep(1)

        print("### Condition not met after %s seconds ###\n" %
              route_max_wait_time)
        return found

    @staticmethod
    def verify_bgp_route(switch, network, next_hop, attempt=1,
                         print_routes=False):
        print("### Verifying route on switch %s [attempt #%d] - Network: %s, "
              "Next-Hop: %s ###\n" %
              (switch.name, attempt, network, next_hop))

        routes = switch("show ip bgp")

        if print_routes:
            print("### Routes for switch %s ###\n" % switch.name)
            print("%s\n" % routes)

        routes = routes.split(vtysh_cr)

        for rte in routes:
            if (network in rte) and (next_hop in rte):
                return True

        routes = switch("show ipv6 bgp")

        if print_routes:
            print("### Routes for switch %s ###\n" % switch.name)
            print("%s\n" % routes)

        routes = routes.split(vtysh_cr)

        for rte in routes:
            if (network in rte) and (next_hop in rte):
                return True

        return False

    @staticmethod
    def verify_cfg_exist(switch, cfg_array):
        return SwitchVtyshUtils.verify_cfg_value(switch, cfg_array, '')

    @staticmethod
    def verify_cfg_value(switch, cfg_array, value):
        running_cfg = SwitchVtyshUtils.vtysh_get_running_cfg(switch)
        running_cfg = running_cfg.split(vtysh_cr)

        for rc in running_cfg:

            for c in cfg_array:
                if (c in rc) and (str(value) in rc):
                    return True

        return False

    @staticmethod
    def vtysh_get_running_cfg(switch):
        return switch("show running-config")

__all__ = ["SwitchVtyshUtils"]
