"""
OpenSwitch Test for vlan related configurations.
"""

from vtysh_utils import SwitchVtyshUtils
import time
from pytest import mark

TOPOLOGY = """
# +-------+
# |  ops1 |
# +-------+

# Nodes
[type=openswitch name="OpenSwitch 1"] lf5
[type=openswitch name="Openswitch 2"] lf6
[type=openswitch name="Openswitch 3"] sp1
[type=openswitch name="Openswitch 4"] sp2
[type=openswitch name="Openswitch 5"] sp3
[type=openswitch name="Openswitch 6"] sp4

# Links
lf5:if49 -- sp1:if49
lf5:if50 -- sp2:if49
lf5:if51 -- sp3:if49
lf5:if52 -- sp4:if49

lf6:if49 -- sp1:if50
lf6:if50 -- sp2:if50
lf6:if51 -- sp3:if50
lf6:if52 -- sp4:if50
"""
# basic leaf and spine asn, router-id configuration

lf5_asn = "64100"
lf5_router_id = "172.50.99.1"
lf5_ip_add = ["172.20.15.2", "172.20.25.2", "172.20.35.2", "172.20.45.2"]

lf6_asn = "64101"
lf6_router_id = "172.60.99.1"
lf6_ip_add = ["172.20.16.2", "172.20.26.2", "172.20.36.2", "172.20.46.2"]

sp_asn = "64611"
sp1_router_id = "1.1.1.1"
sp2_router_id = "2.2.2.2"
sp3_router_id = "3.3.3.3"
sp4_router_id = "4.4.4.4"

sp_ip_add = [["172.20.15.1", "172.20.16.1"], ["172.20.25.1", "172.20.26.1"], [
    "172.20.35.1", "172.20.36.1"], ["172.20.45.1", "172.20.46.1"]]

sp_router_id = [sp1_router_id, sp2_router_id, sp3_router_id, sp4_router_id]
lf_router_id = [lf5_router_id, lf6_router_id]

bgp_ntwork_pl = "30"

lf_neighbor_asn = "64611"
sp_lf5_neighbor_asn = "64100"
sp_lf6_neighbor_asn = "64101"
lf_asn = [lf5_asn, lf6_asn]
# neighbor configuration for spine and leaf routers
num_of_spine = 4
num_of_leaf = 2

lf_ip_add = [lf5_ip_add, lf6_ip_add]

lf5_neighbor_id = []
lf6_neighbor_id = []

sp1_neighbor_id = []
sp2_neighbor_id = []
sp3_neighbor_id = []
sp4_neighbor_id = []


lf5_neighbor_id = ["172.20.15.1", "172.20.25.1", "172.20.35.1", "172.20.45.1"]
lf6_neighbor_id = ["172.20.16.1", "172.20.26.1", "172.20.36.1", "172.20.46.1"]
sp1_neighbor_id = ["172.20.15.2", "172.20.16.2"]
sp2_neighbor_id = ["172.20.25.2", "172.20.26.2"]
sp3_neighbor_id = ["172.20.35.2", "172.20.36.2"]
sp4_neighbor_id = ["172.20.45.2", "172.20.46.2"]


bgp_lf5_config = []
bgp_lf6_config = []
for i in range(0, num_of_spine):
    bgp_lf5_config.append(["router bgp %s" % "64100",
                           "bgp router-id %s" % lf5_router_id,
                           "neighbor %s remote-as %s" % (lf5_neighbor_id[i],
                                                         "64611")])
    bgp_lf6_config.append(["router bgp %s" % "64101",
                           "bgp router-id %s" % lf6_router_id,
                           "neighbor %s remote-as %s" % (lf6_neighbor_id[i],
                                                         "64611")])

bgp_lf_config = [bgp_lf5_config, bgp_lf6_config]

bgp_sp1_config = []
bgp_sp2_config = []
bgp_sp3_config = []
bgp_sp4_config = []
lf_asn = ["64100", "64101"]

# cinfiguring spine routers to leaf 5 router as a neighbor
for i in range(0, num_of_leaf):
    bgp_sp1_config.append(["router bgp %s" % "64611",
                           "bgp router-id %s" % "1.1.1.1",
                           "neighbor %s remote-as %s" % (sp1_neighbor_id[i],
                                                         lf_asn[i])])

    bgp_sp2_config.append(["router bgp %s" % "64611",
                           "bgp router-id %s" % "2.2.2.2",
                           "neighbor %s remote-as %s" % (sp2_neighbor_id[i],
                                                         lf_asn[i])])

    bgp_sp3_config.append(["router bgp %s" % "64611",
                           "bgp router-id %s" % "3.3.3.3",
                           "neighbor %s remote-as %s" % (sp3_neighbor_id[i],
                                                         lf_asn[i])])

    bgp_sp4_config.append(["router bgp %s" % "64611",
                           "bgp router-id %s" % "4.4.4.4",
                           "neighbor %s remote-as %s" % (sp4_neighbor_id[i],
                                                         lf_asn[i])])

bgp_sp_config = [bgp_sp1_config, bgp_sp2_config,
                 bgp_sp3_config, bgp_sp4_config]


def configure_switch_ips(step):
    step("\n########## Configuring switch IPs.. ##########\n")
    num = 0
    # configuring IPs for leaf switches AND configuring their 4 interfaces
    for switch in switches[:num_of_leaf]:
        # Configure the IPs between the switches
        port = 49
        for i in range(num_of_spine):
            switch("configure terminal")
            switch("interface %s" % switch.ports["if%s" % str(port + i)])
            switch("no shutdown")
            switch("ip address %s/%s" % (lf_ip_add[num][i],
                                         bgp_ntwork_pl))
            switch("end")
        num += 1

    # now configuring 4 spine switches and their 4*2 interfaces

    num = 0
    for switch in switches[num_of_leaf:]:
        port = 49
        for i in range(num_of_leaf):
            switch("configure terminal")
            switch("interface %s" % switch.ports["if%s" % str(49 + i)])
            switch("no shutdown")
            switch("ip address %s/%s" % (sp_ip_add[num][i],
                                         bgp_ntwork_pl))
            switch("end")
        num += 1


def verify_bgp_running(step):
    step("\n########## Verifying bgp processes.. ##########\n")

    for switch in switches:
        pid = switch("pgrep -f bgpd", shell="bash").strip()
        assert (pid != ""), "bgpd process not running on %s" % switch.name
        step("### bgpd process exists on switch %s ###\n" % switch.name)


def get_ping_hosts_result(step):
    step("\n Pinging the interfaces....\n")
    for i in range(0, 4):
        switch = switches[0]
        result = switch("ping %s repetitions 2" % lf5_neighbor_id[i])
        assert "2 received" in result, "Not able to ping the interfaces."
        switch = switches[1]
        switch("ping %s repetitions 2" % lf6_neighbor_id[i])
        assert "2 received" in result, "Not able to ping the interfaces."


def configure_bgp(step):
    step("\n########## Applying BGP configurations... ##########\n")

    # configure 2 leaf switches and making 4 spine switches its neighbor
    num = 0
    for switch in switches[:num_of_leaf]:

        for i in range(num_of_spine):
            step("### Applying BGP config on switch %s ###\n" % switch.name)
            cfg_array = bgp_lf_config[num][i]
            SwitchVtyshUtils.vtysh_cfg_cmd(switch, cfg_array)
        num += 1

    num = 0
    for switch in switches[num_of_leaf:]:

        for i in range(num_of_leaf):
            step("### Applying BGP config on switch %s ###\n" % switch.name)
            cfg_array = bgp_sp_config[num][i]
            SwitchVtyshUtils.vtysh_cfg_cmd(switch, cfg_array)
        num += 1


def verify_configs(step):
    step("\n########## Verifying all configurations.. ##########\n")

    # Verify bgp configs for leaf switches
    for i in range(0, len(bgp_lf_config)):
        switch = switches[i]
        for j in bgp_lf_config[i]:
            bgp_cfg = j[0]

            for cfg in bgp_cfg:
                res = SwitchVtyshUtils.verify_cfg_exist(switch, [cfg])
                assert res, "Config \"%s\" was not correctly configured!" % cfg

    for i in range(0, len(bgp_sp_config)):
        switch = switches[i + 2]
        for j in bgp_sp_config[i]:
            bgp_cfg = j[0]

            for cfg in bgp_cfg:
                res = SwitchVtyshUtils.verify_cfg_exist(switch, [cfg])
                assert res, "Config \"%s\" was not correctly configured!" % cfg


def verify_sessions(step):
    for switch in switches[:2]:
        while(1):
            time.sleep(1)
            result = switch("show ip bgp summary")
            if(result.count("Established") == 4):
                break

    for switch in switches[2:]:
        while(1):
            time.sleep(1)
            result = switch("show ip bgp summary")
            if(result.count("Established") == 2):
                break


@mark.timeout(600)
def test_bgp_scale(topology, step):
    global switches

    lf5 = topology.get('lf5')
    lf6 = topology.get('lf6')
    sp1 = topology.get('sp1')
    sp2 = topology.get('sp2')
    sp3 = topology.get('sp3')
    sp4 = topology.get('sp4')

    assert lf5 is not None
    assert lf6 is not None
    assert sp1 is not None
    assert sp2 is not None
    assert sp3 is not None
    assert sp4 is not None

    switches = [lf5, lf6, sp1, sp2, sp3, sp4]

    lf5.name = "lf5"
    lf6.name = "lf6"
    sp1.name = "sp1"
    sp2.name = "sp2"
    sp3.name = "sp3"
    sp4.name = "sp4"

    configure_switch_ips(step)
    get_ping_hosts_result(step)
    verify_bgp_running(step)
    configure_bgp(step)
    verify_configs(step)
    verify_sessions(step)
