/* bgp daemon ovsdb Route table integration.
 *
 * Hewlett-Packard Company Confidential (C) Copyright 2015 Hewlett-Packard Development Company, L.P.
 *
 * GNU Zebra is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2, or (at your option) any
 * later version.
 *
 * GNU Zebra is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with GNU Zebra; see the file COPYING.  If not, write to the Free
 * Software Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
 * 02111-1307, USA.
 *
 * File: bgp_ovsdb_route.c
 *
 * Purpose: This file interfaces with the OVSDB Route table to do the following:
 * a) Inserts all BGP routes in the Route table needed for the show commands.
 * b) Clears the protocol private flag for the best route.
 * c) Sets the protocol private flag for the old best route.
 * d) Deletes route from the Route table.
 */

#include <zebra.h>
#include "prefix.h"
#include "linklist.h"
#include "memory.h"
#include "command.h"
#include "stream.h"
#include "filter.h"
#include "str.h"
#include "log.h"
#include "routemap.h"
#include "buffer.h"
#include "sockunion.h"
#include "plist.h"
#include "thread.h"
#include "workqueue.h"
#include "bgpd/bgpd.h"
#include "bgpd/bgp_table.h"
#include "bgpd/bgp_route.h"
#include "bgpd/bgp_attr.h"
#include "bgpd/bgp_debug.h"
#include "bgpd/bgp_aspath.h"
#include "bgpd/bgp_regex.h"
#include "bgpd/bgp_mpath.h"
#include "bgpd/bgp_ovsdb_route.h"
#include "openvswitch/vlog.h"

extern struct ovsdb_idl *idl;
extern const char *bgp_origin_str[];
extern const char *bgp_origin_long_str[];
// HALON_TODO: Create a list of rib_txn later to keep track of txn status.
static struct ovsdb_idl_txn *rib_txn = NULL;

#define PREFIX_MAXLEN    50
VLOG_DEFINE_THIS_MODULE(bgp_ovsdb_route);

/* Structure definition for protocol specific data (psd) column in the
 * OVSDB Route table. These fields are owned by bgpd and shared
 * with CLI daemon.
 */
typedef struct route_psd_bgp_s {
    int flags;
    const char *aspath;
    const char *origin;
    int local_pref;
    const char *peer_id;
    bool internal;
    bool ibgp;
} route_psd_bgp_t;

static const char *
get_str_from_afi(u_char family)
{
    if (family == AF_INET)
        return "ipv4";
    else if (family == AF_INET6)
        return "ipv6";
    else
        return NULL;
}

static const char *
get_str_from_safi(safi_t safi)
{
    if (safi == SAFI_UNICAST)
        return "unicast";
    else if (safi == SAFI_MULTICAST)
        return "multicast";
    else if (safi == SAFI_MPLS_VPN)
        return "vpn";
    else
        return NULL;
}


const struct ovsrec_vrf*
bgp_ovsdb_get_vrf(struct bgp *bgp)
{
    const struct ovsrec_bgp_router *bgp_row = NULL;

    OVSREC_BGP_ROUTER_FOR_EACH(bgp_row, idl) {
        if (bgp_row->asn == (int64_t)bgp->as) {
            return bgp_row->vrf;
        }
    }
    return NULL;
}

static int
bgp_ovsdb_set_rib_protocol_specific_data(const struct ovsrec_route *rib,
                                         struct bgp_info *info,
                                         struct bgp *bgp)
{
    struct smap smap;
    struct attr *attr;
    struct peer *peer;

    attr = info->attr;
    peer = info->peer;
    smap_init(&smap);
    smap_add_format(&smap,
                    OVSDB_ROUTE_PROTOCOL_SPECIFIC_BGP_FLAGS,
                    "%d",
                    info->flags);
    smap_add(&smap,
             OVSDB_ROUTE_PROTOCOL_SPECIFIC_BGP_AS_PATH,
             aspath_print(info->attr->aspath));
    smap_add(&smap,
             OVSDB_ROUTE_PROTOCOL_SPECIFIC_BGP_ORIGIN,
             bgp_origin_str[info->attr->origin]);
    smap_add_format(&smap,
                    OVSDB_ROUTE_PROTOCOL_SPECIFIC_BGP_LOC_PREF,
                    "%d",
                    attr->local_pref);
    smap_add(&smap,
             OVSDB_ROUTE_PROTOCOL_SPECIFIC_BGP_PEER_ID,
             info->peer->host);
    // HALON_TODO: Check for confed flag later
    if (peer->sort == BGP_PEER_IBGP) {
        smap_add(&smap,
                 OVSDB_ROUTE_PROTOCOL_SPECIFIC_BGP_INTERNAL,
                 "true");
        smap_add(&smap,
                 OVSDB_ROUTE_PROTOCOL_SPECIFIC_BGP_IBGP,
                 "true");

    } else if ((peer->sort == BGP_PEER_EBGP && peer->ttl != 1)
               || CHECK_FLAG (peer->flags, PEER_FLAG_DISABLE_CONNECTED_CHECK)) {
        smap_add(&smap,
                 OVSDB_ROUTE_PROTOCOL_SPECIFIC_BGP_INTERNAL,
                 "true");
    } else {
        smap_add(&smap,
                 OVSDB_ROUTE_PROTOCOL_SPECIFIC_BGP_INTERNAL,
                 "false");
        smap_add(&smap,
                 OVSDB_ROUTE_PROTOCOL_SPECIFIC_BGP_IBGP,
                 "false");
    }
    ovsrec_route_set_protocol_specific(rib, &smap);
    smap_destroy(&smap);
    return 0;
}

static const struct ovsrec_nexthop*
bgp_ovsdb_lookup_nexthop(char *ip)
{
    const struct ovsrec_nexthop *row = NULL;
    if (!ip)
        assert(0);

    OVSREC_NEXTHOP_FOR_EACH(row, idl) {
        if (strcmp(ip, row->ip_address) == 0) {
            /* Match */
            return row;
        }
    }
    return NULL;
}

/*
 * This function sets nexthop entries for a route in Route table
 */
static int
bgp_ovsdb_set_rib_nexthop(struct ovsdb_idl_txn *txn,
                          const struct ovsrec_route *rib,
                          struct prefix *p,
                          struct bgp_info *info,
                          int nexthop_num)
{
    struct bgp_info *mpinfo;
    struct in_addr *nexthop;
    struct ovsrec_nexthop **nexthop_list;
    char nexthop_buf[INET6_ADDRSTRLEN];
    const struct ovsrec_nexthop *pnexthop = NULL;
    bool selected;
    char pr[PREFIX_MAXLEN];

    prefix2str(p, pr, sizeof(pr));
    nexthop = &info->attr->nexthop;
    if (nexthop->s_addr == 0) {
        VLOG_INFO("%s: Nexthop address is 0 for route %s\n",
                  __FUNCTION__, pr);
        return -1;
    }
    nexthop_list = xmalloc(sizeof *rib->nexthops * nexthop_num);
    // Set first nexthop
    inet_ntop(p->family, nexthop, nexthop_buf, sizeof(nexthop_buf));
    pnexthop = bgp_ovsdb_lookup_nexthop(nexthop_buf);
    if (!pnexthop) {
        pnexthop = ovsrec_nexthop_insert(txn);
        ovsrec_nexthop_set_ip_address(pnexthop, nexthop_buf);
        VLOG_DBG("Setting nexthop IP address %s\n", nexthop_buf);
    }
    selected = 1;
    ovsrec_nexthop_set_selected(pnexthop, &selected, 1);
    nexthop_list[0] = pnexthop;
    nexthop_list[0]->ip_address = xstrdup(nexthop_buf);

    int ii = 1;
    // Set multipath nexthops
    for(mpinfo = bgp_info_mpath_first (info); mpinfo;
        mpinfo = bgp_info_mpath_next (mpinfo))
        {
            // Update the nexthop table.
            nexthop = &mpinfo->attr->nexthop;
            inet_ntop(p->family, nexthop, nexthop_buf, sizeof(nexthop_buf));
            pnexthop = bgp_ovsdb_lookup_nexthop(nexthop_buf);
            if (!pnexthop) {
                pnexthop = ovsrec_nexthop_insert(txn);
                ovsrec_nexthop_set_ip_address(pnexthop, nexthop_buf);
                VLOG_DBG("Setting nexthop IP address %s, count %d\n",
                         nexthop_buf, ii);
            }
            selected = 1;
            ovsrec_nexthop_set_selected(pnexthop, &selected, 1);
            nexthop_list[ii] = pnexthop;
            nexthop_list[ii]->ip_address = xstrdup(nexthop_buf);
            ii++;
        }
    ovsrec_route_set_nexthops(rib, nexthop_list, nexthop_num);
    for (ii = 0; ii < nexthop_num; ii++)
        free(nexthop_list[ii]->ip_address);
    free(nexthop_list);
    return 0;
}

static void
bgp_ovsdb_get_rib_protocol_specific_data(const struct ovsrec_route *rib_row,
                                         route_psd_bgp_t *data)
{
    assert(data);
    memset(data, 0, sizeof(*data));

    data->flags = smap_get_int(&rib_row->protocol_specific,
                               OVSDB_ROUTE_PROTOCOL_SPECIFIC_BGP_FLAGS, 0);
    data->aspath = smap_get(&rib_row->protocol_specific,
                            OVSDB_ROUTE_PROTOCOL_SPECIFIC_BGP_AS_PATH);
    data->origin = smap_get(&rib_row->protocol_specific,
                            OVSDB_ROUTE_PROTOCOL_SPECIFIC_BGP_ORIGIN);
    data->local_pref = smap_get_int(&rib_row->protocol_specific,
                                    OVSDB_ROUTE_PROTOCOL_SPECIFIC_BGP_LOC_PREF, 0);
    data->peer_id = smap_get(&rib_row->protocol_specific,
                             OVSDB_ROUTE_PROTOCOL_SPECIFIC_BGP_PEER_ID);
    const char *value;
    value = smap_get(&rib_row->protocol_specific,
                     OVSDB_ROUTE_PROTOCOL_SPECIFIC_BGP_INTERNAL);
    if (!strcmp(value, "true")) {
        data->internal = 1;
    } else {
        data->internal = 0;
    }
    value = smap_get(&rib_row->protocol_specific,
                     OVSDB_ROUTE_PROTOCOL_SPECIFIC_BGP_IBGP);
    if (!strcmp(value, "true")) {
        data->ibgp = 1;
    } else {
        data->ibgp = 0;
    }
    return;
}

const struct ovsrec_route*
bgp_ovsdb_lookup_rib_entry(struct prefix *p,
                           struct bgp_info *info,
                           struct bgp *bgp,
                           safi_t safi)
{
    const struct ovsrec_route *rib_row = NULL;
    char pr[PREFIX_MAXLEN];
    route_psd_bgp_t psd, *ppsd = &psd;
    const char *afi, *safi_str;
    const struct ovsrec_vrf *vrf = NULL;

    OVSREC_ROUTE_FOR_EACH(rib_row, idl) {
        if (strcmp(rib_row->from, OVSREC_ROUTE_FROM_BGP))
            continue;
        bgp_ovsdb_get_rib_protocol_specific_data(rib_row, ppsd);
        prefix2str(p, pr, sizeof(pr));

        afi= get_str_from_afi(p->family);
        if (!afi) {
            VLOG_ERR ("Invalid address family for route %s\n", pr);
            continue;
        }
        safi_str = get_str_from_safi(safi);
        if (!safi_str) {
            VLOG_ERR ("Invalid sub-address family for route %s\n", pr);
            continue;
        }
        if ((strcmp(pr, rib_row->prefix) == 0)
            && (strcmp(afi, rib_row->address_family) == 0)
            && (strcmp(safi_str, rib_row->sub_address_family) == 0)
            && ((vrf = bgp_ovsdb_get_vrf(bgp)) != NULL)
            && (strcmp(ppsd->peer_id, info->peer->host) == 0)) {
                /* Match */
                return rib_row;
            }
    }
    return NULL;
}
/*
 * This function withdraws previously announced route to Zebra.
 */
int
bgp_ovsdb_withdraw_rib_entry(struct prefix *p,
                             struct bgp_info *info,
                             struct bgp *bgp,
                             safi_t safi,
                             bool create_txn)
{
    const struct ovsrec_route *rib_row = NULL;
    char pr[PREFIX_MAXLEN];
    struct ovsdb_idl_txn *txn = NULL;
    enum ovsdb_idl_txn_status status;
    int flags;
    bool prot_priv;

    if (create_txn) {
        txn = ovsdb_idl_txn_create(idl);
        if (!txn) {
            VLOG_ERR("%s: Failed to create new transaction for Route table\n",
                     __FUNCTION__);
            return -1;
        }
    } else {
        txn = rib_txn;
    }
    prefix2str(p, pr, sizeof(pr));
    VLOG_DBG("%s: Withdrawing route %s, flags %d\n",
             __FUNCTION__, pr, info->flags);
    rib_row = bgp_ovsdb_lookup_rib_entry(p, info, bgp, safi);
    if (!rib_row) {
        VLOG_ERR("%s: Failed to find route %s in Route table\n",
                 __FUNCTION__, pr);
        return -1;
    }
    if (CHECK_FLAG(info->flags, BGP_INFO_SELECTED)) {
        VLOG_ERR("%s:BGP info flag is set to selected, cannot withdraw route %s",
                 __FUNCTION__, pr);
        return -1;
    }
    // Clear RIB flag
    prot_priv = 1;
    ovsrec_route_set_protocol_private(rib_row, &prot_priv, 1);
    bgp_ovsdb_set_rib_protocol_specific_data(rib_row, info, bgp);

    if (create_txn) {
        status = ovsdb_idl_txn_commit(txn);
        ovsdb_idl_txn_destroy(txn);
        if ((status != TXN_SUCCESS) && (status != TXN_INCOMPLETE)) {
            VLOG_ERR("%s: Failed to withdraw route %s, status %d\n",
                     __FUNCTION__, pr, status);
            return -1;
        } else {
            VLOG_DBG("Route %s withdraw txn sent, rc = %d\n",
                     pr, status);
        }
    }
    return 0;
}

/*
 * This function announces a route to zebra.
 */
int
bgp_ovsdb_announce_rib_entry(struct prefix *p,
                             struct bgp_info *info,
                             struct bgp *bgp,
                             safi_t safi,
                             bool create_txn)
{
    const struct ovsrec_route *rib_row = NULL;
    char pr[PREFIX_MAXLEN];
    struct ovsdb_idl_txn *txn = NULL;
    enum ovsdb_idl_txn_status status;
    int flags;
    bool proto_priv;


    if (create_txn) {
        txn = ovsdb_idl_txn_create(idl);
        if (!txn) {
            VLOG_ERR("%s: Failed to create new transaction for Route table\n",
                     __FUNCTION__);
            return -1;
        }
    } else {
        txn = rib_txn;
    }
    prefix2str(p, pr, sizeof(pr));
    VLOG_INFO("%s: Announcing route %s, flags %d\n",
              __FUNCTION__, pr, info->flags);
    rib_row = bgp_ovsdb_lookup_rib_entry(p, info, bgp, safi);
    if (!rib_row) {
        VLOG_ERR("%s: Failed to find route %s in Route table\n",
                 __FUNCTION__, pr);
        return -1;
    }
    VLOG_DBG("%s: Found route %s from peer %s\n",
             __FUNCTION__, pr, info->peer->host);
    if (!CHECK_FLAG(info->flags, BGP_INFO_SELECTED)) {
        VLOG_ERR("%s:BGP info flag is not set to selected, cannot \
announce route %s",
                 __FUNCTION__, pr);
        return -1;
    }
    // Clear private flag
    proto_priv = 0;
    ovsrec_route_set_protocol_private(rib_row, &proto_priv, 1);
    bgp_ovsdb_set_rib_protocol_specific_data(rib_row, info, bgp);

    if (create_txn) {
        status = ovsdb_idl_txn_commit(txn);
        ovsdb_idl_txn_destroy(txn);
        if ((status != TXN_SUCCESS) && (status != TXN_INCOMPLETE)) {
            VLOG_ERR("%s: Failed to announce route %s, status %d\n",
                     __FUNCTION__, pr, status);
            return -1;
        } else {
            VLOG_DBG("Route %s announce txn sent, rc = %d\n",
                     pr, status);
        }
    }
    return 0;
}

/*
 * This function deletes a BGP route from Route table.
 */
int
bgp_ovsdb_delete_rib_entry(struct prefix *p,
                           struct bgp_info *info,
                           struct bgp *bgp,
                           safi_t safi,
                           bool create_txn)
{
    const struct ovsrec_route *rib_row = NULL;
    char pr[PREFIX_MAXLEN];
    struct ovsdb_idl_txn *txn = NULL;
    enum ovsdb_idl_txn_status status;

    if (create_txn) {
        txn = ovsdb_idl_txn_create(idl);
        if (!txn) {
            VLOG_ERR("%s: Failed to create new transaction for Route table\n",
                     __FUNCTION__);
            return -1;
        }
    } else {
        txn = rib_txn;
    }
    prefix2str(p, pr, sizeof(pr));
    VLOG_DBG("%s: Deleting route %s, flags %d\n",
             __FUNCTION__, pr, info->flags);
    rib_row = bgp_ovsdb_lookup_rib_entry(p, info, bgp, safi);
    if (!rib_row) {
        VLOG_ERR("%s: Failed to find route %s in Route table\n",
                 __FUNCTION__, pr);
        return -1;
    }
    if (CHECK_FLAG(info->flags, BGP_INFO_SELECTED)) {
        VLOG_ERR("%s:BGP info flag is set to selected, cannot \
remove route %s",
                 __FUNCTION__, pr);
        return -1;
    }
    // Delete route from RIB
    ovsrec_route_delete(rib_row);
    if (create_txn) {
        status = ovsdb_idl_txn_commit(txn);
        ovsdb_idl_txn_destroy(txn);
        if ((status != TXN_SUCCESS) && (status != TXN_INCOMPLETE)) {
            VLOG_ERR("%s: Failed to remove route %s, status %d\n",
                     __FUNCTION__, pr, status);
            return -1;
        } else {
            VLOG_DBG("Route %s delete txn sent, rc = %d\n",
                     pr, status);
        }
    }
    return 0;
}

/*
 * This function adds BGP route to Route table
 */
int
bgp_ovsdb_add_rib_entry(struct prefix *p,
                        struct bgp_info *info,
                        struct bgp *bgp,
                        safi_t safi,
                        bool create_txn)
{
    const struct ovsrec_route *rib = NULL;
    struct ovsdb_idl_txn *txn = NULL;
    char pr[PREFIX_MAXLEN];
    const char *afi, *safi_str;
    int64_t flags = 0;
    int64_t distance = 0, nexthop_num;
    const struct ovsrec_vrf *vrf = NULL;
    enum ovsdb_idl_txn_status status;
    bool prot_priv = 0;

    if (create_txn) {
        txn = ovsdb_idl_txn_create(idl);
        if (!txn) {
            VLOG_ERR("%s: Failed to create new transaction for Route table\n",
                     __FUNCTION__);
            return -1;
        }
    } else {
        txn = rib_txn;
    }
    rib = ovsrec_route_insert(txn);
    prefix2str(p, pr, sizeof(pr));
    ovsrec_route_set_prefix(rib, pr);
    VLOG_INFO("%s: setting prefix %s\n", __FUNCTION__, pr);

    afi= get_str_from_afi(p->family);
    if (!afi) {
        VLOG_ERR ("Invalid address family for route %s\n", pr);
        return -1;
    }
    ovsrec_route_set_address_family(rib, afi);
    safi_str = get_str_from_safi(safi);
    if (!safi_str) {
        VLOG_ERR ("Invalid sub-address family for route %s\n", pr);
        return -1;
    }
    ovsrec_route_set_sub_address_family(rib, safi_str);
    ovsrec_route_set_from(rib, "BGP");

    distance = bgp_distance_apply (p, info, bgp);
    VLOG_DBG("distance %d\n", distance);
    if (distance) {
        ovsrec_route_set_distance(rib, (const int64_t *)&distance, 1);
    }
    ovsrec_route_set_metric(rib, (const int64_t *)&info->attr->med, 1);
    // Nexthops
    struct in_addr *nexthop = &info->attr->nexthop;
    if (nexthop->s_addr == 0) {
        VLOG_INFO("%s: Nexthop address is 0 for route %s\n",
                  __FUNCTION__, pr);
    } else {
        nexthop_num = 1 + bgp_info_mpath_count (info);
        VLOG_DBG("Setting nexthop num %d, metric %d, bgp_info_flags 0x%x\n",
                 nexthop_num, info->attr->med, info->flags);
        // Nexthop list
        bgp_ovsdb_set_rib_nexthop(txn, rib, p, info, nexthop_num);
    }

    if (CHECK_FLAG(info->flags, BGP_INFO_SELECTED)) {
        prot_priv = 0;
    } else {
        prot_priv = 1;
    }
    ovsrec_route_set_protocol_private(rib, &prot_priv, 1);

    // Set up VRF
    vrf = bgp_ovsdb_get_vrf(bgp);
    if (!vrf) {
        VLOG_ERR("VRF entry not found for this route %s, BGP router ASN %d\n",
                 pr, bgp->as);
        return -1;
    }
    ovsrec_route_set_vrf(rib, vrf);
    // Set protocol specific data
    bgp_ovsdb_set_rib_protocol_specific_data(rib, info, bgp);
    if (create_txn) {
        status = ovsdb_idl_txn_commit(txn);
        // HALON_TODO: Need to handle txn error recovery.
        ovsdb_idl_txn_destroy(txn);
        if ((status != TXN_SUCCESS) && (status != TXN_INCOMPLETE)) {
            VLOG_ERR("%s: Failed to add route %s, status %d\n",
                     __FUNCTION__, pr, status);
            return -1;
        } else {
            VLOG_DBG("Route %s add txn sent, rc = %d\n",
                     pr, status);
        }
    }
    return 0;
}

void
bgp_ovsdb_rib_txn_create(void)
{
    struct ovsdb_idl_txn *txn;

    if (rib_txn) {
        return;
    }
    txn = ovsdb_idl_txn_create(idl);
    if (!txn) {
        VLOG_ERR("%s: Failed to create new transaction for Route table\n",
                 __FUNCTION__);
        assert(0);
    }
    rib_txn = txn;
}

int
bgp_ovsdb_rib_txn_commit(void)
{
    enum ovsdb_idl_txn_status status;

    if (!rib_txn) {
        VLOG_ERR("Trying to commit txn w/o creating txn\n");
        return;
    }
    status = ovsdb_idl_txn_commit(rib_txn);
    ovsdb_idl_txn_destroy(rib_txn);
    rib_txn = NULL;
    if (status != TXN_SUCCESS) {
        VLOG_ERR("%s: Failed to commit Route transactions, status %d\n",
                 __FUNCTION__, status);
        return -1;
    }
    return 0;
}

int
bgp_ovsdb_update_flags(struct prefix *p,
                       struct bgp_info *info,
                       struct bgp *bgp,
                       safi_t safi,
                       bool create_txn)
{
    const struct ovsrec_route *rib_row = NULL;
    char pr[PREFIX_MAXLEN];
    struct ovsdb_idl_txn *txn = NULL;
    enum ovsdb_idl_txn_status status;

    if (create_txn) {
        txn = ovsdb_idl_txn_create(idl);
        if (!txn) {
            VLOG_ERR("%s: Failed to create new transaction for Route table\n",
                     __FUNCTION__);
            return -1;
        }
    } else {
        txn = rib_txn;
    }

    prefix2str(p, pr, sizeof(pr));
    VLOG_DBG("%s: Updating flags for route %s, flags %d\n",
             __FUNCTION__, pr, info->flags);
    rib_row = bgp_ovsdb_lookup_rib_entry(p, info, bgp, safi);
    if (!rib_row) {
        VLOG_ERR("%s: Failed to find route %s in Route table\n",
                 __FUNCTION__, pr);
        return -1;
    }
    VLOG_DBG("%s: Found route %s from peer %s\n",
             __FUNCTION__, pr, info->peer->host);
    bgp_ovsdb_set_rib_protocol_specific_data(rib_row, info, bgp);
    if (create_txn) {
        status = ovsdb_idl_txn_commit(txn);
        ovsdb_idl_txn_destroy(txn);
        if ((status != TXN_SUCCESS) && (status != TXN_INCOMPLETE)) {
            VLOG_ERR("%s: Failed to announce route %s, status %d\n",
                     __FUNCTION__, pr, status);
            return -1;
        } else {
            VLOG_DBG("Route %s update protocol specific data txn sent, rc = %d\n",
                     pr, status);
        }
    }
    return 0;
}
