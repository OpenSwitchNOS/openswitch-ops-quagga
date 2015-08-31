from halonvsi.docker import *
from halonvsi.halon import *
from halonutils.halonutil import *
from halonvsi.quagga import *

# Flags for defining what types of switches will be used for BGP testing.
# The "peer" is only applicable to tests that have more than one switch emulated
enableHalonSwitch = True
enablePeerHalonSwitch = True

BGP_CONVERGENCE_DELAY_S = 10

def getSwitchType(isHalon):
    if isHalon:
        return HalonSwitch
    else:
        return QuaggaSwitch

SWITCH_TYPE = getSwitchType(enableHalonSwitch)
PEER_SWITCH_TYPE = getSwitchType(enablePeerHalonSwitch)

class BgpConfig(object):
    def __init__(self, asn, routerid, network):
        self.neighbors = []
        self.networks = []
        self.routeMaps = []
        self.prefixLists = []

        self.asn = asn
        self.routerid = routerid

        self.addNetwork(network)

    def addNeighbor(self, neighbor):
        self.neighbors.append(neighbor)

    def addNetwork(self, network):
        self.networks.append(network)

    def addRouteMap(self, neighbor, prefix_list, dir, action='', metric=''):
        self.routeMaps.append([neighbor, prefix_list, dir, action, metric])

# Prefix-list configurations
class PrefixList(object):
    def __init__(self, name, seq_num, action, network, prefixLen):
        self.name = name
        self.seq_num = seq_num
        self.action = action
        self.network = network
        self.prefixLen = prefixLen
