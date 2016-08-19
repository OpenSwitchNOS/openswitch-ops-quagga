"""
OpenSwitch Test for vlan related configurations.
"""

from vtysh_utils import SwitchVtyshUtils
import time
from pytest import mark

TOPOLOGY = """
# +-------+          +-------+
# |  sw1  |----sw2---|  sw3  |
# +-------+          +-------+

# Nodes
[type=openswitch name="OpenSwitch 1"] sw1
[type=openswitch name="Openswitch 2"] sw2
[type=openswitch name="Openswitch 3"] sw3


# Links
sw1:if01 -- sw2:if01
sw2:if02 -- sw3:if01
"""


# switch configurations..ASN,ROUTER-ID,IP ADD..
sw1_neighbor_id = []
sw2_neighbor_id = []
sw3_neighbor_id = []

# SWITCH 1
sw1_asn = sw2_neighbor_asn = "1"
sw1_router_id = "1.1.1.1"
sw1_ip_add = ["172.20.15.1"]
sw2_neighbor_id.append(sw1_ip_add[0])

# SWITCH 2
sw2_asn = sw1_neighbor_asn = sw3_neighbor_asn = "2"
sw2_router_id = "2.2.2.2"
sw2_ip_add = ["172.20.15.2", "172.20.16.1"]
sw1_neighbor_id.append(sw2_ip_add[0])
sw3_neighbor_id.append(sw2_ip_add[1])

# SWITCH 3
sw3_asn = sw2_neighbor_asn = sw4_neighbor_asn = "3"
sw3_router_id = "3.3.3.3"
sw3_ip_add = ["172.20.16.2"]
sw2_neighbor_id.append(sw3_ip_add[0])

bgp_network_pl = "24"


bgp_sw1_config = []
bgp_sw3_config = []


# sw1 ----> sw2
bgp_sw1_config.append(["router bgp %s" % sw1_asn,
                       "bgp router-id %s" % sw1_router_id,
                       "neighbor %s remote-as %s" % ("172.20.16.2", sw3_asn),
                       "neighbor 172.20.16.2 ebgp-multihop"])

# SWITCH 3 CONFIGS...
# sw3 ----> sw1
bgp_sw3_config.append(["router bgp %s" % sw3_asn,
                       "bgp router-id %s" % sw3_router_id,
                       "neighbor %s remote-as %s" % ("172.20.15.1", sw1_asn),
                       "neighbor 172.20.15.1 ebgp-multihop"])


def configure_switch_ips(step):
    step("\n########## Configuring switch IPs.. ##########\n")

    # configuring SWITCH 1...

    switch = switches[0]
    switch("configure terminal")
    switch("ip route 172.20.16.2/32 172.20.15.2")
    switch("interface %s" % switch.ports["if01"])
    switch("no shutdown")
    switch("ip address %s/%s" % (sw1_ip_add[0],
                                 bgp_network_pl))
    switch("end")

    # configuring SWITCH 2...
    switch = switches[1]
    switch("configure terminal")
    switch("interface %s" % switch.ports["if01"])
    switch("no shutdown")
    switch("ip address %s/%s" % (sw2_ip_add[0],
                                 bgp_network_pl))
    switch("end")

    switch = switches[1]
    switch("configure terminal")
    switch("interface %s" % switch.ports["if02"])
    switch("no shutdown")
    switch("ip address %s/%s" % (sw2_ip_add[1],
                                 bgp_network_pl))

    switch("end")

    # configuring SWITCH 3...
    switch = switches[2]
    switch("configure terminal")
    switch("ip route 172.20.15.1/32 172.20.16.1")
    switch("interface %s" % switch.ports["if01"])
    switch("no shutdown")
    switch("ip address %s/%s" % (sw3_ip_add[0],
                                 bgp_network_pl))
    switch("end")


def ping_result(step):
    step("\n Pinging the neighboring interfaces..\n")
    switch = switches[0]
    result = switch("ping 172.20.15.2 repetitions 2")
    assert "2 received" in result, "Error in pinging the interfaces."

    switch = switches[1]
    result = switch("ping 172.20.16.2 repetitions 2")
    assert "2 received" in result, "Error in pinging the interfaces."


def verify_bgp_running(step):
    step("\n########## Verifying bgp processes.. ##########\n")

    for switch in switches:
        pid = switch("pgrep -f bgpd", shell="bash").strip()
        assert (pid != ""), "bgpd process not running on switch %s" % \
            switch.name

        step("### bgpd process exists on switch %s ###\n" % switch.name)


def configure_bgp(step):
    step("\n########## Applying BGP configurations... ##########\n")

    # configuring bgp in switch 1...
    switch = switches[0]
    step("### Applying BGP config on switch %s ###\n" % switch.name)
    cmd = 0
    for i in range(0, len(bgp_sw1_config)):

        cfg_array = bgp_sw1_config[cmd]
        SwitchVtyshUtils.vtysh_cfg_cmd(switch, cfg_array)
        cmd += 1

    switch("end")

    # configuring bgp in switch 3...
    switch = switches[2]
    step("### Applying BGP config on switch %s ###\n" % switch.name)
    cmd = 0
    for i in range(0, len(bgp_sw3_config)):

        cfg_array = bgp_sw3_config[cmd]
        SwitchVtyshUtils.vtysh_cfg_cmd(switch, cfg_array)
        cmd += 1

    switch("end")


def verify_configs(step):
    step("\n########## Verifying all configurations.. ##########\n")

    # Verify bgp configs for SWITCH 1...
    switch = switches[0]
    for i in range(0, len(bgp_sw1_config)):
        bgp_cfg = bgp_sw1_config[i]

        for cfg in bgp_cfg:
            res = SwitchVtyshUtils.verify_cfg_exist(switch, [cfg])
            assert res, "Config \"%s\" was not correctly configured!" % cfg

    # verifying BGP configs on switch 3...
    switch = switches[2]
    for i in range(0, len(bgp_sw3_config)):
        bgp_cfg = bgp_sw3_config[i]

        for cfg in bgp_cfg:
            res = SwitchVtyshUtils.verify_cfg_exist(switch, [cfg])
            assert res, "Config \"%s\" was not correctly configured!" % cfg


def show_ip_bgp(step):
    bgp_switch = [switches[0], switches[2]]
    step("\nNow verifying sessions on switch 1 and switch 3.")
    for switch in bgp_switch:
        while(1):
            time.sleep(1)
            result = switch("show ip bgp summary")
            if(result.count("Established") == 1):
                break


@mark.timeout(600)
def test_bgp_ebgp_multihop(topology, step):
    global switches

    sw1 = topology.get('sw1')
    sw2 = topology.get('sw2')
    sw3 = topology.get('sw3')

    assert sw1 is not None
    assert sw2 is not None
    assert sw3 is not None

    switches = [sw1, sw2, sw3]

    sw1.name = "sw1"
    sw2.name = "sw2"
    sw3.name = "sw3"

    configure_switch_ips(step)
    ping_result(step)
    verify_bgp_running(step)
    configure_bgp(step)
    verify_configs(step)
    show_ip_bgp(step)
