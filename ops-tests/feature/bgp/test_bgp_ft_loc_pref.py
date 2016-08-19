"""
OpenSwitch Test for vlan related configurations.
"""

from vtysh_utils import SwitchVtyshUtils
import time
from pytest import mark

TOPOLOGY = """
#     ---+      +-----------------------+     +-------+
#     sw1| -----|--sw2-----sw3-----sw4--|-----|---sw1 |
#     ---+      +-----------------------+     +-------+

# Nodes
[type=openswitch name="OpenSwitch 1"] sw1
[type=openswitch name="Openswitch 2"] sw2
[type=openswitch name="Openswitch 3"] sw3
[type=openswitch name="Openswitch 4"] sw4


# Links
sw1:if01 -- sw2:if01
sw2:if02 -- sw3:if01
sw3:if02 -- sw4:if01
sw4:if02 -- sw1:if02
"""


# switch configurations..ASN,ROUTER-ID,IP ADD..
sw1_neighbor_id = []
sw2_neighbor_id = []
sw3_neighbor_id = []
sw4_neighbor_id = []
neighbor_id = [sw1_neighbor_id, sw2_neighbor_id,
               sw3_neighbor_id, sw4_neighbor_id]

# SWITCH 1
sw1_asn = sw2_neighbor_asn = "1"
sw1_router_id = "1.1.1.1"
sw1_ip_add = ["172.20.15.1", "172.20.18.2"]
sw2_neighbor_id.append(sw1_ip_add[0])
sw4_neighbor_id.append(sw1_ip_add[1])

# SWITCH 2
sw2_asn = sw1_neighbor_asn = sw3_neighbor_asn = "2"
sw2_router_id = "2.2.2.2"
sw2_ip_add = ["172.20.15.2", "172.20.16.1"]
sw1_neighbor_id.append(sw2_ip_add[0])
sw3_neighbor_id.append(sw2_ip_add[1])

# SWITCH 3
sw3_asn = sw2_neighbor_asn = sw4_neighbor_asn = "2"
sw3_router_id = "3.3.3.3"
sw3_ip_add = ["172.20.16.2", "172.20.17.1"]
sw2_neighbor_id.append(sw3_ip_add[0])
sw4_neighbor_id.append(sw3_ip_add[1])

# SWITCH 4
sw4_asn = sw3_neighbor_asn = "2"
sw4_router_id = "4.4.4.4"
sw4_ip_add = ["172.20.17.2", "172.20.18.1"]
sw3_neighbor_id.append(sw4_ip_add[0])
sw1_neighbor_id.append(sw4_ip_add[1])
bgp_network_pl = "24"


bgp_sw1_config = []
bgp_sw2_config = []
bgp_sw3_config = []
bgp_sw4_config = []

bgp_config = [bgp_sw1_config, bgp_sw2_config, bgp_sw3_config, bgp_sw4_config]

# sw1 ----> sw2
bgp_sw1_config.append(["router bgp %s" % sw1_asn,
                       "bgp router-id %s" % sw1_router_id,
                       "neighbor %s remote-as %s" % (sw1_neighbor_id[0],
                                                     sw2_asn)])

bgp_sw1_config[0].insert(2, "network 11.0.0.0/24")

bgp_sw1_config.append(["router bgp %s" % sw1_asn,
                       "bgp router-id %s" % sw1_router_id,
                       "neighbor %s remote-as %s" % (sw1_neighbor_id[1],
                                                     sw4_asn)])

# SWITCH 2 CONFIGS...
# sw2 ----> sw1
bgp_sw2_config.append(["router bgp %s" % sw2_asn,
                       "bgp router-id %s" % sw2_router_id,
                       "neighbor %s remote-as %s" % (sw2_neighbor_id[0],
                                                     sw1_asn)])

# sw2 ----> sw3
bgp_sw2_config.append(["router bgp %s" % sw2_asn,
                       "bgp router-id %s" % sw2_router_id,
                       "neighbor %s remote-as %s" % (sw2_neighbor_id[1],
                                                     sw3_asn),
                       "neighbor 172.20.15.1 route-map set-loc-pref in"])

# SWITCH 3 CONFIGS...
# sw3 ----> sw2
bgp_sw3_config.append(["router bgp %s" % sw3_asn,
                       "bgp router-id %s" % sw3_router_id,
                       "neighbor %s remote-as %s" % (sw3_neighbor_id[0],
                                                     sw2_asn)])

# sw3 ----> sw4
bgp_sw3_config.append(["router bgp %s" % sw3_asn,
                       "bgp router-id %s" % sw3_router_id,
                       "neighbor %s remote-as %s" % (sw3_neighbor_id[1],
                                                     sw4_asn)])

# SWITCH 4 CONFIGS...
bgp_sw4_config.append(["router bgp %s" % sw4_asn,
                       "bgp router-id %s" % sw4_router_id,
                       "neighbor %s remote-as %s" % (sw4_neighbor_id[0],
                                                     sw1_asn),
                       "neighbor 172.20.18.2 route-map set-loc-pref in"])

bgp_sw4_config.append(["router bgp %s" % sw4_asn,
                       "bgp router-id %s" % sw4_router_id,
                       "neighbor %s remote-as %s" % (sw4_neighbor_id[1],
                                                     sw2_asn)])


def configure_switch_ips(step):
    step("\n########## Configuring switch IPs.. ##########\n")

    # configuring SWITCH 1...

    switch = switches[0]
    switch("configure terminal")
    switch("interface %s" % switch.ports["if01"])
    switch("no shutdown")
    switch("ip address %s/%s" % (sw1_ip_add[0],
                                 bgp_network_pl))
    switch("end")

    switch = switches[0]
    switch("configure terminal")
    switch("interface %s" % switch.ports["if02"])
    switch("no shutdown")
    switch("ip address %s/%s" % (sw1_ip_add[1],
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
    switch("route-map set-loc-pref permit 10")
    switch("set local-preference 410")
    switch("end")

    # configuring SWITCH 3...
    switch = switches[2]
    switch("configure terminal")
    switch("interface %s" % switch.ports["if01"])
    switch("no shutdown")
    switch("ip address %s/%s" % (sw3_ip_add[0],
                                 bgp_network_pl))
    switch("end")

    switch = switches[2]
    switch("configure terminal")
    switch("interface %s" % switch.ports["if02"])
    switch("no shutdown")
    switch("ip address %s/%s" % (sw3_ip_add[1],
                                 bgp_network_pl))
    switch("end")

    # configuring SWITCH 4...
    switch = switches[3]
    switch("configure terminal")
    switch("interface %s" % switch.ports["if01"])
    switch("no shutdown")
    switch("ip address %s/%s" % (sw4_ip_add[0],
                                 bgp_network_pl))
    switch("route-map set-loc-pref permit 10")
    switch("set local-preference 510")
    switch("end")

    switch = switches[3]
    switch("configure terminal")
    switch("interface %s" % switch.ports["if02"])
    switch("no shutdown")
    switch("ip address %s/%s" % (sw4_ip_add[1],
                                 bgp_network_pl))
    switch("end")


def get_ping_hosts_result(step):
    i = 0
    for switch in switches:
        result = switch("ping %s repetitions 2" % neighbor_id[i][0])
        assert "2 received" in result, "Could not ping interface %s \
            from switch %s " % (neighbor_id[i][0], str(switch))
        result = switch("ping %s repetitions 2" % neighbor_id[i][1])
        assert "2 received" in result, "Could not ping interface %s \
            from switch %s " % (neighbor_id[i][1], str(switch))

        i += 1


def verify_bgp_running(step):
    step("\n########## Verifying bgp processes.. ##########\n")

    for switch in switches:
        pid = switch("pgrep -f bgpd", shell="bash").strip()
        assert (pid != ""), "bgpd process not running on \
            switch %s" % switch.name
        step("### bgpd process exists on switch %s ###\n" % switch.name)


def configure_bgp(step):
    step("\n########## Applying BGP configurations... ##########\n")

    num = 0
    for switch in switches:
        step("### Applying BGP config on switch %s ###\n" % switch.name)
        for i in range(0, len(bgp_config[num])):
            cfg_array = bgp_config[num][i]
            SwitchVtyshUtils.vtysh_cfg_cmd(switch, cfg_array)
        num += 1


def verify_configs(step):
    step("\n########## Verifying all configurations.. ##########\n")

    num = 0
    for switch in switches:
        for i in range(0, len(bgp_config[num])):
            bgp_cfg = bgp_config[num][i]

        for cfg in bgp_cfg:
            res = SwitchVtyshUtils.verify_cfg_exist(switch, [cfg])
            assert res, "Config \"%s\" was not correctly configured!" % cfg
        num += 1


def check_best_path(step):
    step("\n Verifying bgp session between neighbor switches.....\n")

    for switch in switches:
        while(1):
            time.sleep(1)
            result = switch("show ip bgp summary")
            if(result.count("Established") == 2):
                break

    while(1):
        switch = switches[2]
        time.sleep(1)
        result = switch("sh ip bgp")
        result = result.split()
        if("*>i11.0.0.0/24" in result):
            index = result.index("*>i11.0.0.0/24")
            if(result[index + 1] == sw4_neighbor_id[0] and
                    result[index + 3] == "510"):
                break


@mark.timeout(600)
def test_bgp_loc_pref(topology, step):
    global switches

    sw1 = topology.get('sw1')
    sw2 = topology.get('sw2')
    sw3 = topology.get('sw3')
    sw4 = topology.get('sw4')

    assert sw1 is not None
    assert sw2 is not None
    assert sw3 is not None
    assert sw4 is not None

    switches = [sw1, sw2, sw3, sw4]

    sw1.name = "sw1"
    sw2.name = "sw2"
    sw3.name = "sw3"
    sw4.name = "sw4"

    configure_switch_ips(step)
    get_ping_hosts_result(step)
    verify_bgp_running(step)
    configure_bgp(step)
    verify_configs(step)
    check_best_path(step)
