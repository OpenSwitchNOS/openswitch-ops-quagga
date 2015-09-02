from halonvsi.halon import *

VTYSH_CR = '\r\n'

class SwitchVtyshUtils(object):
    @staticmethod
    def vtysh_cmd(switch, cmd):
        if isinstance(switch, HalonSwitch):
            return switch.cmdCLI(cmd)
        else:
            return switch.cmd("vtysh -c \"%s\"" % cmd)

    @staticmethod
    def vtysh_get_running_cfg(switch):
        return SwitchVtyshUtils.vtysh_cmd(switch, "sh running-config")

    @staticmethod
    def vtysh_print_running_cfg(switch):
        info(SwitchVtyshUtils.vtysh_get_running_cfg(switch))

    # Method for executing the configuration command in vtysh on an array of
    # configurations. Input must be an array of configurations, such as:
    #   ["router bgp 1", "bgp router-id 1.1.1.1"]
    @staticmethod
    def vtysh_cfg_cmd(switch, cfg_array, show_running_cfg=False):
        if isinstance(switch, HalonSwitch):
            SwitchVtyshUtils.vtysh_cfg_cmd_halon(switch, cfg_array)
        else:
            SwitchVtyshUtils.vtysh_cfg_cmd_quagga(switch, cfg_array)

        if show_running_cfg:
            SwitchVtyshUtils.vtysh_print_running_cfg(switch)

    @staticmethod
    def vtysh_cfg_cmd_quagga(switch, cfg_array):
        exec_cmd = ' -c "configure term"'

        for cfg in cfg_array:
            exec_cmd += " -c \"%s\"" % cfg

        switch.cmd("vtysh %s" % exec_cmd)

    @staticmethod
    def vtysh_cfg_cmd_halon(switch, cfg_array):
        switch.cmdCLI('configure term')

        for cfg in cfg_array:
            switch.cmdCLI(cfg)

        switch.cmdCLI('end')

    # This method takes in an array of the config that we're verifying the value
    # for. For example, if we are trying to verify the remote-as of neighbor:
    #    neighbor <router-id> remote-as <value>
    #
    # The input array should be ["neighbor", "remote-as"]. This will allow the
    # caller to avoid having to include the router-id. If the user wanted to
    # verify the remote-as value for a specific router-id, however, then the
    # user can construct the cfg_array as:
    #   ["neighbor", <router-id>, "remote-as"]
    @staticmethod
    def verify_cfg_value(switch, cfg_array, value):
        running_cfg = SwitchVtyshUtils.vtysh_get_running_cfg(switch).split(VTYSH_CR)
        result = False

        for rc in running_cfg:
            info(rc)
            matches = True

            for c in cfg_array:
                if rc.find(c) < 0:
                    matches = False
                    break;

            if matches:
                if rc.find(str(value)) >= 0:
                    result = True
                    break;
                else:
                    result = False

        return result

    # Method for verifying if a configuration exists in the running-config.
    # The input is a configuration array. For example, if the user wants to
    # verify the configuration exists:
    #   neighbor <router-id> remote-as <value>
    #
    # The user can check if remote-as exists for a specific neighbor by passing
    # in a config array of:
    #   ["neighbor", <router-id>, "remote-as"]
    #
    # If the user doesn't want to check for a specific router-id, then the
    # following array can be passed-in:
    #   ["neighbor", "remote-as"]
    @staticmethod
    def verify_cfg_exist(switch, cfg_array):
        return SwitchVtyshUtils.verify_cfg_value(switch, cfg_array, '')

    @staticmethod
    def verify_bgp_route (switch, network, next_hop):
        info("Verifying route - Network: %s, Next-Hop: %s\n" %
             (network, next_hop))

        routes = SwitchVtyshUtils.vtysh_cmd(switch, "sh ip bgp").split(VTYSH_CR)

        found = False
        for rte in routes:
            # Try to match our advertised route first
            if rte.find(network) >= 0:
                if rte.find(next_hop) >= 0:
                    found = True
                    break;
        return found

    @staticmethod
    def verify_show_ip_bgp_route (switch, network, next_hop):
        info("Verifying - show ip bgp route - Network: %s, Next-Hop: %s\n" %
             (network, next_hop))
        routes = SwitchVtyshUtils.vtysh_cmd(switch, "sh ip bgp %s" % network).split(VTYSH_CR)

        found = False
        for rte in routes:
            # Try to match our advertised route first
            if rte.find(network) >= 0:
                if rte.find(next_hop) >= 0:
                    found = True
                    break;

        return found
