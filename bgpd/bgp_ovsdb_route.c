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
 * a) Inserts all BGP routes in the BGP local Route table needed for the show commands.
 * b) Announces best route by inserting in the global Route table.
 * c) Withdraws best route by deleting the entry from the global route table.
 * d) Deletes route from local BGP Route table.
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
#include "ovs/hash.h"
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

#define MAX_ARGC         10
#define MAX_ARG_LEN     256
#define PREFIX_MAXLEN    50
#define BGP_TXN_TIMEOUT   5

extern unsigned int idl_seqno;
extern const char *bgp_origin_str[];
extern const char *bgp_origin_long_str[];


VLOG_DEFINE_THIS_MODULE(bgp_ovsdb_route);

/* Structure definition for path attributes data (psd) column in the
 * OVSDB BGP_Route table. These fields are owned by bgpd and shared
 * with CLI daemon.
 */
typedef struct route_psd_bgp_s {
    int flags;
    const char *aspath;
    const char *origin;
    int local_pref;
    bool internal;
    bool ibgp;
    const char *uptime;
} route_psd_bgp_t;


enum txn_bgp_request {
    TXN_BGP_ADD,
    TXN_BGP_DEL,
    TXN_BGP_UPD_ANNOUNCE,
    TXN_BGP_UPD_WITHDRAW,
    TXN_BGP_UPD_ATTR
};

char *txn_bgp_request_str[]={
    "TXN_BGP_ADD",
    "TXN_BGP_DEL",
    "TXN_BGP_UPD_ANNOUNCE",
    "TXN_BGP_UPD_WITHDRAW",
    "TXN_BGP_UPD_ATTR"
};

struct bgp_ovsdb_txn {
    struct hmap_node hmap_node;
    int    request;
    struct ovsdb_idl_txn *txn;
    as_t   as_no;
    afi_t  afi;
    safi_t safi;
    struct prefix prefix;
    struct bgp_info *bgp_info;
    unsigned int info_attr_hash;
    time_t update_time;
};

void bgp_txn_init(void);
void bgp_txn_destroy(void);
void bgp_txn_insert(struct hmap_node *txn_node);
void bgp_txn_remove(struct hmap_node *txn_node);

static int
txn_command_result(enum ovsdb_idl_txn_status status, char *msg, char *pr)
{
    if ((status != TXN_SUCCESS) && (status != TXN_INCOMPLETE)) {
        VLOG_ERR("%s: Route table txn failure: %s, status %d\n",
                 __FUNCTION__, msg, status);
        return -1;
    }
    VLOG_DBG("%s %s txn sent, rc = %d\n",
             msg, pr, status);
    return 0;
}

/* Allocate a transaction recovery node, set it up and add to hmap */
#define HASH_DB_TXN(txn, req, p, info, asn, safi)                       \
    do {                                                                \
        char p_str[PREFIX_MAXLEN];                                      \
        struct bgp_ovsdb_txn *txn_rec = NULL;                           \
        txn_rec = xzalloc(sizeof (*txn_rec));                           \
        if (txn_rec == NULL) {                                          \
            VLOG_ERR("%s: %s\n",                                        \
                     __FUNCTION__, "Failed to insert txn to hash");     \
            ovsdb_idl_txn_destroy(txn);                                 \
            return -1;                                                  \
        }                                                               \
        txn_rec->request = req;                                         \
        txn_rec->txn = txn;                                             \
        memcpy (&txn_rec->prefix, p, sizeof (*p));                      \
        txn_rec->bgp_info = info;                                       \
        if (info->attr)  {                                              \
            txn_rec->info_attr_hash = attrhash_key_make(info->attr);    \
        }                                                               \
        txn_rec->as_no = asn;                                           \
        txn_rec->afi = family2afi(p->family);                           \
        txn_rec->safi = safi;                                           \
        txn_rec->update_time = time (NULL);                             \
        bgp_txn_insert(&txn_rec->hmap_node);                            \
        prefix2str(p, p_str, sizeof(p_str));                            \
        VLOG_INFO("Inserted txn prefix %s", p_str);                     \
        VLOG_INFO("Inserted txn at time %d", (int)txn_rec->update_time);\
    } while (0)

#define START_DB_TXN(txn, msg, req, p, info, asn, safi)                 \
    do {                                                                \
        enum ovsdb_idl_txn_status status;                               \
        txn = ovsdb_idl_txn_create(idl);                                \
        if (txn == NULL) {                                              \
            VLOG_ERR("%s: %s\n",                                        \
                     __FUNCTION__, msg);                                \
            return -1;                                                  \
        }                                                               \
        HASH_DB_TXN(txn, req, p, info, asn, safi);                      \
    } while (0)

#define END_DB_TXN(txn, msg, pr)                          \
    do {                                                  \
        enum ovsdb_idl_txn_status status;                 \
        status = ovsdb_idl_txn_commit(txn);               \
        return txn_command_result(status, msg, pr);       \
    } while (0)


/* used when NO error is detected but still need to terminate */
#define ABORT_DB_TXN(txn, msg)                                      \
    do {                                                            \
        ovsdb_idl_txn_destroy(txn);                                 \
        VLOG_ERR("%s: Aborting txn: %s\n", __FUNCTION__, msg);      \
        return CMD_SUCCESS;                                         \
    } while (0)

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
    int j;
    const struct ovsrec_vrf *ovs_vrf;

    OVSREC_VRF_FOR_EACH (ovs_vrf, idl) {
        for (j = 0; j < ovs_vrf->n_bgp_routers; j ++) {
            if (ovs_vrf->key_bgp_routers[j] == (int64_t)bgp->as) {
                return ovs_vrf;
            }
        }
    }
    return NULL;
}

static int
bgp_ovsdb_set_rib_path_attributes(struct smap *smap,
                                  struct bgp_info *info,
                                  struct bgp *bgp)
{
    struct attr *attr;
    struct peer *peer;
    time_t tbuf;

    attr = info->attr;
    peer = info->peer;

    smap_add_format(smap,
                    OVSDB_BGP_ROUTE_PATH_ATTRIBUTES_FLAGS,
                    "%d",
                    info->flags);
    smap_add(smap,
             OVSDB_BGP_ROUTE_PATH_ATTRIBUTES_AS_PATH,
             aspath_print(info->attr->aspath));
    smap_add(smap,
             OVSDB_BGP_ROUTE_PATH_ATTRIBUTES_ORIGIN,
             bgp_origin_str[info->attr->origin]);
    smap_add_format(smap,
                    OVSDB_BGP_ROUTE_PATH_ATTRIBUTES_LOC_PREF,
                    "%d",
                    attr->local_pref);
    // HALON_TODO: Check for confed flag later
    if (peer->sort == BGP_PEER_IBGP) {
        smap_add(smap,
                 OVSDB_BGP_ROUTE_PATH_ATTRIBUTES_INTERNAL,
                 "true");
        smap_add(smap,
                 OVSDB_BGP_ROUTE_PATH_ATTRIBUTES_IBGP,
                 "true");

    } else if ((peer->sort == BGP_PEER_EBGP && peer->ttl != 1)
               || CHECK_FLAG (peer->flags, PEER_FLAG_DISABLE_CONNECTED_CHECK)) {
        smap_add(smap,
                 OVSDB_BGP_ROUTE_PATH_ATTRIBUTES_INTERNAL,
                 "true");
    } else {
        smap_add(smap,
                 OVSDB_BGP_ROUTE_PATH_ATTRIBUTES_INTERNAL,
                 "false");
        smap_add(smap,
                 OVSDB_BGP_ROUTE_PATH_ATTRIBUTES_IBGP,
                 "false");
    }
#ifdef HAVE_CLOCK_MONOTONIC
    tbuf = time(NULL) - (bgp_clock() - info->uptime);
#else
    tbuf = info->uptime;
#endif
    smap_add(smap,
             OVSDB_BGP_ROUTE_PATH_ATTRIBUTES_UPTIME,
             ctime(&tbuf));
    return 0;
}

static const struct ovsrec_nexthop*
bgp_ovsdb_lookup_nexthop(char *ip)
{
    const struct ovsrec_nexthop *row = NULL;
    if (!ip)
        assert(0);

    OVSREC_NEXTHOP_FOR_EACH(row, idl) {
        if (row->ip_address)
        {
            if (strcmp(ip, row->ip_address) == 0) {
                /* Match */
                return row;
            }
        }
    }
    return NULL;
}

static const struct ovsrec_bgp_nexthop*
bgp_ovsdb_lookup_local_nexthop(char *ip)
{
    const struct ovsrec_bgp_nexthop *row = NULL;
    if (!ip)
        assert(0);

    OVSREC_BGP_NEXTHOP_FOR_EACH(row, idl) {
        if (row->ip_address)
        {
            if (strcmp(ip, row->ip_address) == 0) {
                /* Match */
                return row;
            }
        }
    }
    return NULL;
}

/*
 * This function sets nexthop entries for a route in global nexthop table.
 */
static int
bgp_ovsdb_set_rib_nexthop(struct ovsdb_idl_txn *txn,
                          const struct ovsrec_route *rib,
                          struct prefix *p,
                          struct bgp_info *info,
                          int nexthop_num,
                          safi_t safi)
{
    struct bgp_info *mpinfo;
    struct in_addr *nexthop;
    struct ovsrec_nexthop **nexthop_list;
    char nexthop_buf[INET6_ADDRSTRLEN];
    const struct ovsrec_nexthop *pnexthop = NULL;
    bool selected;
    char pr[PREFIX_MAXLEN];
    const char *safi_str;

    prefix2str(p, pr, sizeof(pr));
    safi_str = get_str_from_safi(safi);
    if (strcmp(safi_str, "unicast")) {
        VLOG_ERR ("Invalid sub-address family %s for nexthop\n", safi_str);
        return -1;
    }
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
        ovsrec_nexthop_set_type(pnexthop, safi_str);
    }
    selected = 1;
    ovsrec_nexthop_set_selected(pnexthop, &selected, 1);
    nexthop_list[0] = (struct ovsrec_nexthop*) pnexthop;
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
                ovsrec_nexthop_set_type(pnexthop, safi_str);
            }
            selected = 1;
            ovsrec_nexthop_set_selected(pnexthop, &selected, 1);
            nexthop_list[ii] = (struct ovsrec_nexthop*) pnexthop;
            nexthop_list[ii]->ip_address = xstrdup(nexthop_buf);
            ii++;
        }
    ovsrec_route_set_nexthops(rib, nexthop_list, nexthop_num);
    for (ii = 0; ii < nexthop_num; ii++)
        free(nexthop_list[ii]->ip_address);
    free(nexthop_list);
    return 0;
}


/*
 * This function sets nexthop entries for a route in Route table
 */
static int
bgp_ovsdb_set_local_rib_nexthop(struct ovsdb_idl_txn *txn,
                                const struct ovsrec_bgp_route *rib,
                                struct prefix *p,
                                struct bgp_info *info,
                                int nexthop_num,
                                safi_t safi)
{
    struct bgp_info *mpinfo;
    struct in_addr *nexthop;
    struct ovsrec_bgp_nexthop **nexthop_list;
    char nexthop_buf[INET6_ADDRSTRLEN];
    const struct ovsrec_bgp_nexthop *pnexthop = NULL;
    char pr[PREFIX_MAXLEN];
    const char *safi_str;

    prefix2str(p, pr, sizeof(pr));
    safi_str = get_str_from_safi(safi);
    if (strcmp(safi_str, "unicast")) {
        VLOG_ERR ("Invalid sub-address family %s for nexthop\n", safi_str);
        return -1;
    }
    nexthop = &info->attr->nexthop;
    if (nexthop->s_addr == 0) {
        VLOG_INFO("%s: Nexthop address is 0 for route %s\n",
                  __FUNCTION__, pr);
        return -1;
    }
    nexthop_list = xmalloc(sizeof *rib->bgp_nexthops * nexthop_num);
    // Set first nexthop
    inet_ntop(p->family, nexthop, nexthop_buf, sizeof(nexthop_buf));
    pnexthop = bgp_ovsdb_lookup_local_nexthop(nexthop_buf);
    if (!pnexthop) {
        pnexthop = ovsrec_bgp_nexthop_insert(txn);
        ovsrec_bgp_nexthop_set_ip_address(pnexthop, nexthop_buf);
        VLOG_DBG("Setting local nexthop IP address %s\n", nexthop_buf);
        ovsrec_bgp_nexthop_set_type(pnexthop, safi_str);
    }
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
            pnexthop = bgp_ovsdb_lookup_local_nexthop(nexthop_buf);
            if (!pnexthop) {
                pnexthop = ovsrec_bgp_nexthop_insert(txn);
                ovsrec_bgp_nexthop_set_ip_address(pnexthop, nexthop_buf);
                VLOG_DBG("Setting local nexthop IP address %s, count %d\n",
                         nexthop_buf, ii);
                ovsrec_bgp_nexthop_set_type(pnexthop, safi_str);
            }
            nexthop_list[ii] = pnexthop;
            nexthop_list[ii]->ip_address = xstrdup(nexthop_buf);
            ii++;
        }
    ovsrec_bgp_route_set_bgp_nexthops(rib, nexthop_list, nexthop_num);
    for (ii = 0; ii < nexthop_num; ii++)
        free(nexthop_list[ii]->ip_address);
    free(nexthop_list);
    return 0;
}

const struct ovsrec_bgp_route*
bgp_ovsdb_lookup_local_rib_entry(struct prefix *p,
                                 struct bgp_info *info,
                                 struct bgp *bgp,
                                 safi_t safi)
{
    const struct ovsrec_bgp_route *rib_row = NULL;
    char pr[PREFIX_MAXLEN];
    const char *afi, *safi_str;
    const struct ovsrec_vrf *vrf = NULL;

    OVSREC_BGP_ROUTE_FOR_EACH(rib_row, idl) {
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
            && (strcmp(rib_row->peer, info->peer->host) == 0)) {
            /* Match */
            return rib_row;
        }
    }
    return NULL;
}

static void
bgp_ovsdb_get_rib_path_attributes(const struct ovsrec_bgp_route *rib_row,
                                  route_psd_bgp_t *data)
{
    assert(data);
    memset(data, 0, sizeof(*data));

    data->flags = smap_get_int(&rib_row->path_attributes,
                               OVSDB_BGP_ROUTE_PATH_ATTRIBUTES_FLAGS, 0);
    data->aspath = smap_get(&rib_row->path_attributes,
                            OVSDB_BGP_ROUTE_PATH_ATTRIBUTES_AS_PATH);
    data->origin = smap_get(&rib_row->path_attributes,
                            OVSDB_BGP_ROUTE_PATH_ATTRIBUTES_ORIGIN);
    data->local_pref = smap_get_int(&rib_row->path_attributes,
                                    OVSDB_BGP_ROUTE_PATH_ATTRIBUTES_LOC_PREF, 0);
    const char *value;
    value = smap_get(&rib_row->path_attributes,
                     OVSDB_BGP_ROUTE_PATH_ATTRIBUTES_INTERNAL);
    if (!strcmp(value, "true")) {
        data->internal = 1;
    } else {
        data->internal = 0;
    }
    value = smap_get(&rib_row->path_attributes,
                     OVSDB_BGP_ROUTE_PATH_ATTRIBUTES_IBGP);
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
            && ((vrf = bgp_ovsdb_get_vrf(bgp)) != NULL)) {
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
                             safi_t safi)

{
    const struct ovsrec_route *rib_row = NULL;
    char pr[PREFIX_MAXLEN];
    struct ovsdb_idl_txn *txn = NULL;
    int flags;

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
    START_DB_TXN(txn, "Failed to create route table txn",
                 TXN_BGP_UPD_WITHDRAW, p, info, bgp->as, safi);
    // Clear route
    ovsrec_route_delete(rib_row);
    END_DB_TXN(txn, "withdraw route", pr);
}

/*
 * This function deletes a BGP route from Route table.
 */
int
bgp_ovsdb_delete_local_rib_entry(struct prefix *p,
                                 struct bgp_info *info,
                                 struct bgp *bgp,
                                 safi_t safi)
{
    const struct ovsrec_bgp_route *rib_row = NULL;
    char pr[PREFIX_MAXLEN];
    struct ovsdb_idl_txn *txn = NULL;

    prefix2str(p, pr, sizeof(pr));
    VLOG_DBG("%s: Deleting route %s, flags %d\n",
             __FUNCTION__, pr, info->flags);
    rib_row = bgp_ovsdb_lookup_local_rib_entry(p, info, bgp, safi);
    if (!rib_row) {
        VLOG_ERR("%s: Failed to find route %s in Route table\n",
                 __FUNCTION__, pr);
        return -1;
    }
// Disable check to allow route to be deleted regardless of flag.
//     if (CHECK_FLAG(info->flags, BGP_INFO_SELECTED)) {
//         VLOG_ERR("%s:BGP info flag is set to selected, cannot \
// remove route %s",
//                  __FUNCTION__, pr);
//         return -1;
//     }
    START_DB_TXN(txn, "Failed to create route table txn",
                 TXN_BGP_DEL, p, info, bgp->as, safi);
    // Delete route from RIB
    ovsrec_bgp_route_delete(rib_row);
    END_DB_TXN(txn, "delete route", pr);
}

/*
 * This function announces best selected route to Zebra
 */
int
bgp_ovsdb_announce_rib_entry(struct prefix *p,
                             struct bgp_info *info,
                             struct bgp *bgp,
                             safi_t safi)
{
    const struct ovsrec_route *rib = NULL;
    struct ovsdb_idl_txn *txn = NULL;
    char pr[PREFIX_MAXLEN];
    const char *afi, *safi_str;
    int64_t flags = 0;
    int64_t distance = 0, nexthop_num;
    const struct ovsrec_vrf *vrf = NULL;
    struct smap smap;

    prefix2str(p, pr, sizeof(pr));
    afi= get_str_from_afi(p->family);
    if (!afi) {
        VLOG_ERR ("Invalid address family for route %s\n", pr);
        return -1;
    }
    safi_str = get_str_from_safi(safi);
    if (!safi_str) {
        VLOG_ERR ("Invalid sub-address family for route %s\n", pr);
        return -1;
    }
    // Lookup VRF
    vrf = bgp_ovsdb_get_vrf(bgp);
    if (!vrf) {
        VLOG_ERR("VRF entry not found for this route %s, BGP router ASN %d\n",
                 pr, bgp->as);
        return -1;
    }

    START_DB_TXN(txn, "Failed to create route table txn",
                 TXN_BGP_UPD_ANNOUNCE, p, info, bgp->as, safi);
    rib = bgp_ovsdb_lookup_rib_entry(p, info, bgp, safi);
    if (!rib) {
        VLOG_DBG("Inserting route %s\n", pr);
        rib = ovsrec_route_insert(txn);
        ovsrec_route_set_prefix(rib, pr);
        VLOG_INFO("%s: setting prefix %s\n", __FUNCTION__, pr);
        ovsrec_route_set_address_family(rib, afi);
        ovsrec_route_set_sub_address_family(rib, safi_str);
        ovsrec_route_set_from(rib, "BGP");
        // Set VRF
        ovsrec_route_set_vrf(rib, vrf);
        distance = bgp_distance_apply (p, info, bgp);
        VLOG_DBG("distance %d\n", distance);
        if (distance) {
            ovsrec_route_set_distance(rib, (const int64_t *)&distance, 1);
        }
        ovsrec_route_set_metric(rib, (const int64_t *)&info->attr->med, 1);
    } else {
        VLOG_DBG("Found route %s, updating ...\n", pr);
    }
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
        bgp_ovsdb_set_rib_nexthop(txn, rib, p, info, nexthop_num, safi);
    }

    smap_init(&smap);
    bgp_ovsdb_set_rib_path_attributes(&smap, info, bgp);
    smap_destroy(&smap);
    END_DB_TXN(txn, "announced route", pr);
}


/*
 * This function adds BGP route to BGP Route table
 */
int
bgp_ovsdb_add_local_rib_entry(struct prefix *p,
                              struct bgp_info *info,
                              struct bgp *bgp,
                              safi_t safi)
{
    const struct ovsrec_bgp_route *rib = NULL;
    struct ovsdb_idl_txn *txn = NULL;
    char pr[PREFIX_MAXLEN];
    const char *afi, *safi_str;
    int64_t flags = 0;
    int64_t distance = 0, nexthop_num;
    const struct ovsrec_vrf *vrf = NULL;
    struct smap smap;

    prefix2str(p, pr, sizeof(pr));
    afi= get_str_from_afi(p->family);
    if (!afi) {
        VLOG_ERR ("Invalid address family for route %s\n", pr);
        return -1;
    }
    safi_str = get_str_from_safi(safi);
    if (!safi_str) {
        VLOG_ERR ("Invalid sub-address family for route %s\n", pr);
        return -1;
    }
    // Lookup VRF
    vrf = bgp_ovsdb_get_vrf(bgp);
    if (!vrf) {
        VLOG_ERR("VRF entry not found for this route %s, BGP router ASN %d\n",
                 pr, bgp->as);
        return -1;
    }

    START_DB_TXN(txn, "Failed to create bgp route table txn",
                 TXN_BGP_ADD, p, info, bgp->as, safi);
    rib = ovsrec_bgp_route_insert(txn);

    ovsrec_bgp_route_set_prefix(rib, pr);
    VLOG_INFO("%s: setting prefix %s\n", __FUNCTION__, pr);
    ovsrec_bgp_route_set_address_family(rib, afi);
    ovsrec_bgp_route_set_sub_address_family(rib, safi_str);
    // Set Peer
    ovsrec_bgp_route_set_peer(rib, info->peer->host);

    distance = bgp_distance_apply (p, info, bgp);
    VLOG_DBG("distance %d\n", distance);
    if (distance) {
        ovsrec_bgp_route_set_distance(rib, (const int64_t *)&distance, 1);
    }
    ovsrec_bgp_route_set_metric(rib, (const int64_t *)&info->attr->med, 1);
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
        bgp_ovsdb_set_local_rib_nexthop(txn, rib, p, info, nexthop_num, safi);
    }
    // Set VRF
    ovsrec_bgp_route_set_vrf(rib, vrf);
    // Set path attributes
    smap_init(&smap);
    bgp_ovsdb_set_rib_path_attributes(&smap, info, bgp);
    ovsrec_bgp_route_set_path_attributes(rib, &smap);
    smap_destroy(&smap);

    END_DB_TXN(txn, "added route to local RIB, prefix:", pr);
}

/* Function updates flags for a route in local RIB */
int
bgp_ovsdb_update_local_rib_entry_attributes(struct prefix *p,
                                            struct bgp_info *info,
                                            struct bgp *bgp,
                                            safi_t safi)
{
    const struct ovsrec_bgp_route *rib_row = NULL;
    char pr[PREFIX_MAXLEN];
    struct ovsdb_idl_txn *txn = NULL;
    struct smap smap;

    prefix2str(p, pr, sizeof(pr));
    VLOG_DBG("%s: Updating flags for route %s, flags %d\n",
             __FUNCTION__, pr, info->flags);
    rib_row = bgp_ovsdb_lookup_local_rib_entry(p, info, bgp, safi);
    if (!rib_row) {
        VLOG_ERR("%s: Failed to find route %s in Route table\n",
                 __FUNCTION__, pr);
        return -1;
    }
    VLOG_DBG("%s: Found route %s from peer %s\n",
             __FUNCTION__, pr, info->peer->host);
    START_DB_TXN(txn, "Failed to create route table txn",
                 TXN_BGP_UPD_ATTR, p, info, bgp->as, safi);
    smap_init(&smap);
    bgp_ovsdb_set_rib_path_attributes(&smap, info, bgp);
    ovsrec_bgp_route_set_path_attributes(rib_row, &smap);
    smap_destroy(&smap);
    END_DB_TXN(txn, "update route", pr);
}

static struct hmap bgp_ovsdb_txn_hmap =
              HMAP_INITIALIZER(&bgp_ovsdb_txn_hmap);

void
bgp_txn_init(void) {
    hmap_init(&bgp_ovsdb_txn_hmap);
}

void
bgp_txn_destroy(void) {
    hmap_destroy(&bgp_ovsdb_txn_hmap);
}

void
bgp_txn_insert(struct hmap_node *txn_node) {
    hmap_insert(&bgp_ovsdb_txn_hmap, txn_node, hash_pointer(txn_node, 0));
}

void
bgp_txn_remove(struct hmap_node *txn_node) {
    hmap_remove(&bgp_ovsdb_txn_hmap, txn_node);
}

/*
 * Check if an OVSDB route exists for a given BGP route transaction
 * in local RIB table.
 * The reason for this verification is that BGP and OVSDB can get
 * out of sync
 */
static bool
bgp_txn_local_route_found(struct bgp_ovsdb_txn *txn)
{
    struct bgp *bgp = bgp_lookup(txn->as_no, NULL);

    if (bgp && bgp_ovsdb_lookup_local_rib_entry(&txn->prefix,
                                                txn->bgp_info,
                                                bgp,
                                                txn->safi)) {
        return true;
    } else {
        return false;
    }
}

/*
 * Check if an OVSDB route exists for a given BGP route transaction
 * in Global Route table.
 * The reason for this verification is that BGP and OVSDB can get
 * out of sync
 */
static bool
bgp_txn_route_found(struct bgp_ovsdb_txn *txn)
{
    struct bgp *bgp = bgp_lookup(txn->as_no, NULL);

    if (bgp && bgp_ovsdb_lookup_rib_entry(&txn->prefix,
                                          txn->bgp_info,
                                          bgp,
                                          txn->safi)) {
        return true;
    } else {
        return false;
    }
}

/*
 * Traverse bgp_info link list off of bgp_node and look for
 * a bgp_info match as well as an attribute hash match
 */
static bool
bgp_info_found(struct bgp *bgp, struct bgp_ovsdb_txn *txn)
{
    struct bgp_node *rn;
    struct bgp_info *ri;

    rn = bgp_node_get (bgp->rib[txn->afi][txn->safi], &txn->prefix);
    for (ri = rn->info; ri; ri = ri->next) {
        /* compare transaction's bgp_info to bgp's */
        if ( (ri == txn->bgp_info) &&
        /* compare attribute hash */
             (ri->attr &&
             (txn->info_attr_hash == attrhash_key_make(ri->attr))))
            return true;
    }
    return false;
}

/*
 * Free up a transaction entry
 * out of sync
 */
static void
bgp_txn_free(struct bgp_ovsdb_txn *txn)
{
    ovsdb_idl_txn_destroy(txn->txn);
    bgp_txn_remove (&txn->hmap_node);
    free(txn);
}

/*
 * Log unexpected transaction completion
 */
static void
bgp_txn_log(struct bgp_ovsdb_txn *txn, int status)
{
    char prefix_str[PREFIX_MAXLEN];

    prefix2str(&txn->prefix, prefix_str, sizeof(prefix_str));
    VLOG_DBG("Active Transaction for route %s at time %d status=%d",
              prefix_str, txn->update_time, status);
}

/*
 *
 * Invoke HMAP_FOR_EACH (txn, txn_node, &bgp_ovsdb_txn_hmap)
 * to walk over all outstanding transactions in list {
 *    if ( transaction complete successfully ) {
 *          ovsdb_idl_txn_destroy()
 *          bgp_txn_remove (txn_node)
 *    } else
 *    if ( transaction incompete and !timeout ) {
 *          VLOG_DBG
 *          skip txn
 *    } else
 *    if ( (ADD_REQ ||
 *          ADD_UPD_ANNOUNCE ||
 *          ADD_UPD_WITHDRAW ||
 *          ADD_UPD_FLAGS) &&
 *          bgp_route_lookup(txn_node) ) {
 *          add/update route in OVSDB
 *          ovsdb_idl_txn_destroy()
 *          bgp_txn_remove (txn_node)
 *    } else
 *    if ( DEL_REQ && !bgp_route_lookup(txn_node) ) {
 *          delete route from OVSDB
 *          ovsdb_idl_txn_destroy()
 *          bgp_txn_remove (txn_node)
 *    } else
 *          VLOG_ERR
 *          ovsdb_idl_txn_destroy()
 *          bgp_txn_remove (txn_node)
 *    }
 * }
 *
 */
static int skip_txn=0;
void
bgp_txn_complete_processing(void)
{
    struct bgp_ovsdb_txn *txn;
    struct bgp *bgp;
    enum   ovsdb_idl_txn_status status;
    char prefix_str[PREFIX_MAXLEN];

    HMAP_FOR_EACH (txn, hmap_node, &bgp_ovsdb_txn_hmap) {
        /* Get commit status for transaction */
        status = ovsdb_idl_txn_commit(txn->txn);

        prefix2str(&txn->prefix, prefix_str, sizeof(prefix_str));

        /* log transaction */
        bgp_txn_log(txn, status);

        /* Clean up an free txn on success */
        if ((status == TXN_SUCCESS) || (status == TXN_UNCHANGED) ||
            (status == TXN_ABORTED) || (status == TXN_ERROR)) {
            if (status != TXN_SUCCESS) {
                bgp_txn_log(txn, status);
            }
            bgp_txn_free(txn);
            continue;
        }
        /* If incomplete but no timeout allow more time to complete */
        if ((status == TXN_INCOMPLETE) &&
            ((time(NULL) - txn->update_time) < BGP_TXN_TIMEOUT)) {
            VLOG_DBG("Route transaction incomplete as=%d prefix=%s time=%ll",
                     txn->as_no, prefix_str, txn->update_time);
            continue;
        }
        /*
         * Handle all error cases
         */

        /* Get bgp pointer correspending to as_no */
        bgp = bgp_lookup(txn->as_no, NULL);
        if (bgp == NULL) {
            bgp_txn_free(txn);
            VLOG_ERR("Route transaction bgp mismatch as=%d prefix=%s",
                     txn->as_no, prefix_str);
            continue;
        }
        /* Search bgp route info linked list for txn->bgp_info */
        if (!bgp_info_found(bgp, txn)) {
            bgp_txn_free(txn);
            VLOG_ERR("Route transaction bgp_info mismatch as=%d prefix=%s",
                     txn->as_no, prefix_str);
            continue;
        }

        /* In case the transaction is inconsistent with OVSDB,
           don't add/update */

        if ((txn->request == TXN_BGP_ADD) &&
            !bgp_txn_local_route_found(txn)) {
            /* add route in OVSDB route table */
            bgp_ovsdb_add_local_rib_entry(&txn->prefix,
                                          txn->bgp_info, bgp, txn->safi);
            bgp_txn_free(txn);
        } else
        if ((txn->request == TXN_BGP_UPD_ANNOUNCE) &&
            bgp_txn_route_found(txn)) {
            /* announce route in OVSDB route table */
            bgp_ovsdb_announce_rib_entry(&txn->prefix,
                                         txn->bgp_info, bgp, txn->safi);
            bgp_txn_free(txn);
        } else
        if ((txn->request == TXN_BGP_UPD_WITHDRAW) &&
            bgp_txn_route_found(txn)) {
            /* withdraw route from OVSDB route table */
            bgp_ovsdb_withdraw_rib_entry(&txn->prefix,
                                         txn->bgp_info, bgp, txn->safi);
            bgp_txn_free(txn);
        } else
        if ((txn->request == TXN_BGP_UPD_ATTR) &&
            bgp_txn_local_route_found(txn)) {
            /* update route flags in OVSDB route table */
            bgp_ovsdb_update_local_rib_entry_attributes(&txn->prefix,
                                                        txn->bgp_info, bgp, txn->safi);
            bgp_txn_free(txn);
        } else
        if ((txn->request == TXN_BGP_DEL) &&
            bgp_txn_local_route_found(txn)) {
            /* delete route from OVSDB route table */
            bgp_ovsdb_delete_local_rib_entry(&txn->prefix,
                                             txn->bgp_info, bgp, txn->safi);
            bgp_txn_free(txn);
        } else {
            /* Fall back - if can't recover free up txn */
            prefix2str(&txn->prefix, prefix_str, sizeof(prefix_str));
            VLOG_ERR("Route request %s recovey failure as=%d prefix=%s",
                     txn_bgp_request_str[txn->request],
                     txn->as_no, prefix_str);
            bgp_txn_free(txn);
        }
    }
}



struct lookup_entry {
   int index;
   char *cli_cmd;
   char *table_key;
};

/*
 * Translation table from ovsdb to guagga
 */
const struct lookup_entry match_table[]={
  {MATCH_PREFIX, "ip address prefix-list", "prefix_list"},
  {0, NULL, NULL},
};

const struct lookup_entry set_table[]={
  {SET_COMMUNITY, "community", "community"},
  {SET_METRIC, "metric", "metric"},
  {0, NULL, NULL},
};

/*
 * Free memory allocated for argv list
 */
void
policy_ovsdb_free_arg_list(char ***parmv, int argcsize)
{
    int i;
    char ** argv = *parmv;

    if (argv == NULL) return;

    for (i = 0; i < argcsize; i ++)
    {
        if (argv[i]) {
            free(argv[i]);
            argv[i] = NULL;
        }
    }
    free(argv);
    argv = NULL;
    *parmv = argv;
}

/*
 * Allocate memory for argv list
 */
char **
policy_ovsdb_alloc_arg_list(int argcsize, int argvsize)
{
    int i;
    char ** parmv = NULL;

    parmv = xmalloc(sizeof (char *) * argcsize);
    if (!parmv)
        return NULL;

    for (i = 0; i < argcsize; i ++)
      {
        parmv[i] = xmalloc(sizeof(char) * argvsize);
        if (!(parmv[i])) {
            policy_ovsdb_free_arg_list(&parmv, argcsize);
            return NULL;
        }
      }

    return parmv;
}

void
policy_rt_map_read_ovsdb_apply_deletion (struct ovsdb_idl *idl)
{
  const struct ovsrec_route_map *ovs_map, *ovs_first;
  int matched = 0;
  struct route_map * map;

  /* route map */
  ovs_first = ovsrec_route_map_first(idl);
  if (ovs_first && !OVSREC_IDL_ANY_TABLE_ROWS_DELETED(ovs_first, idl_seqno)) {
    VLOG_DBG("No route map rows were deleted");
    return;
  }

  for (map = route_map_master.head; map; map = map->next) {
    matched = 0;
    OVSREC_ROUTE_MAP_FOR_EACH(ovs_map, idl) {
      if (strcmp (map->name, ovs_map->name) == 0) {
        matched = 1;
        break;
      }
    }
    if (!matched) {
      route_map_delete (map);
    }
  }
}

void
policy_rt_map_entry_read_ovsdb_apply_deletion (struct ovsdb_idl *idl)
{
  const struct ovsrec_route_map_entry *ovs_first;
  const struct ovsrec_route_map *ovs_map;
  struct route_map_index *index;
  struct route_map * map;
  int matched = 0;
  int i;

  /* route map entry */
  ovs_first = ovsrec_route_map_entry_first(idl);
  if (ovs_first && !OVSREC_IDL_ANY_TABLE_ROWS_DELETED(ovs_first, idl_seqno)) {
    VLOG_DBG("No route map entry rows were deleted");
    return;
  }

  OVSREC_ROUTE_MAP_FOR_EACH(ovs_map, idl) {
    map = route_map_lookup_by_name(ovs_map->name);
    for (index = map->head; index; index = index->next) {
      matched = 0;
      for (i = 0; i < ovs_map->n_route_map_entries; i ++) {
        if (index->pref == ovs_map->key_route_map_entries[i]) {
          matched = 1;
          break;
        }
      }
      if (!matched) {
        route_map_index_delete (index, 1);
      }
    }
  }
}


/*
 * route-map RM_TO_UPSTREAM_PEER permit 10
 */
/*
 * Read rt map config from ovsdb to argv
 */
void
policy_rt_map_do_change (struct ovsdb_idl *idl,
                        char **argv1, char **argvmatch, char **argvset)
{
  const struct ovsrec_route_map * ovs_map;
  struct ovsrec_route_map_entry * ovs_entry;
  unsigned long pref;
  const char *tmp;
  int argc1, argcmatch, argcset;
  int i, j;

  /*
   * Read from ovsdb
   */
  OVSREC_ROUTE_MAP_FOR_EACH(ovs_map, idl) {
      strcpy(argv1[RT_MAP_NAME], ovs_map->name);
      argc1 = RT_MAP_NAME;

      for (i = 0; i < ovs_map->n_route_map_entries; i ++) {
          ovs_entry = ovs_map->value_route_map_entries[i];
          if ( !(OVSREC_IDL_IS_ROW_INSERTED(ovs_entry, idl_seqno)) &&
                 !(OVSREC_IDL_IS_ROW_MODIFIED(ovs_entry, idl_seqno))) {
              continue;
          }
          strcpy(argv1[RT_MAP_ACTION], ovs_entry->action);
          argc1 = RT_MAP_ACTION;
          pref = ovs_map->key_route_map_entries[i];

          if (ovs_entry->description) {
              strcpy(argv1[RT_MAP_DESCRIPTION], ovs_entry->description);
              argc1 = RT_MAP_DESCRIPTION;
          }

          for (i = 0, j = 0; match_table[i].table_key; i++ ) {
              tmp  = smap_get(&ovs_entry->match, match_table[i].table_key);
              if (tmp) {
                  strcpy(argvmatch[j++], match_table[i].cli_cmd);
                  strcpy(argvmatch[j++], tmp);
              }
          }
          argcmatch = j;

          for (i = 0, j = 0; set_table[i].table_key; i++ ) {
              tmp  = smap_get(&ovs_entry->set, set_table[i].table_key);
              if (tmp) {
                  strcpy(argvset[j++], set_table[i].cli_cmd);
                  strcpy(argvset[j++], tmp);
              }
          }
          argcset = j;
          /*
           * programming back end
           */
          policy_rt_map_apply_changes (idl, argv1, argvmatch, argvset,
                        argc1, argcmatch, argcset, pref);
      }
  }
}


int
policy_rt_map_read_ovsdb_apply_changes (struct ovsdb_idl *idl)
{
  int permit;
  unsigned long pref = 0;
  struct route_map *map;
  struct route_map_index *index;
  int i;
  char **argv1;
  char **argvmatch;
  char **argvset;
  int ret;
  const struct ovsrec_route_map_entry * rt_map_first;
  const struct ovsrec_route_map_entry * rt_map_next;
  int j;
  char *tmp;
  struct smap_node *node;
  const struct ovsrec_route_map * ovs_map, *ovs_first;
  const struct ovsrec_route_map_entry * ovs_entry;


  /*
   * handle route map deletion
   */
  policy_rt_map_read_ovsdb_apply_deletion (idl);
  /*
   * handle route map entry deletion
   */
  policy_rt_map_entry_read_ovsdb_apply_deletion (idl);

 /* handle route map insert/change case */
  rt_map_first = ovsrec_route_map_entry_first(idl);
  if (rt_map_first == NULL) {
      VLOG_INFO("Nothing configed for route map\n");
      return CMD_SUCCESS;
  }

  if ( !(OVSREC_IDL_ANY_TABLE_ROWS_MODIFIED(rt_map_first, idl_seqno)) &&
         !(OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(rt_map_first, idl_seqno)) ) {
      VLOG_INFO("Nothing changed for route map\n");
      return CMD_SUCCESS;
  }

  /*
   * alloc three argv lists
   */
  if (!(argv1 = policy_ovsdb_alloc_arg_list(MAX_ARGC, MAX_ARG_LEN)) ||
       !(argvmatch = policy_ovsdb_alloc_arg_list(MAX_ARGC, MAX_ARG_LEN)) ||
         !(argvset = policy_ovsdb_alloc_arg_list(MAX_ARGC, MAX_ARG_LEN))) {
      VLOG_INFO("Memory allocation failed for working buffer\n");
      return CMD_SUCCESS;
  }

  policy_rt_map_do_change(idl, argv1, argvmatch, argvset);

  policy_ovsdb_free_arg_list(&argv1, MAX_ARGC);
  policy_ovsdb_free_arg_list(&argvmatch, MAX_ARGC);
  policy_ovsdb_free_arg_list(&argvset, MAX_ARGC);

  return CMD_SUCCESS;
}

/*
 * Log info
 */
int
policy_ovsdb_rt_map_vlog(int ret)
{
    if (ret)
    {
        switch (ret)
        {
        case RMAP_RULE_MISSING:
        VLOG_INFO("%% Can't find rule.\n");
            return CMD_WARNING;
        case RMAP_COMPILE_ERROR:
            VLOG_INFO("%% Argument is malformed.\n");
            return CMD_WARNING;
        }
    }
    return CMD_SUCCESS;
}

/*
 * Set up route map at the back end
 * Read from ovsdb, then program back end policy route map
 *
 * Specific cli command:
 * route-map RM_TO_UPSTREAM_PEER permit 10
 */
int
policy_rt_map_apply_changes (struct ovsdb_idl *idl,
                        const char **argv1, char **argvmatch, char **argvset,
                        int argc1, int argcmatch, int argcset,
                        unsigned long pref)
{
  int permit;
  struct route_map *map;
  struct route_map_index *index;
  int i;
  int ret;

  if (! argc1)
      return CMD_SUCCESS;

  /* Get route map. */
  map = route_map_get (argv1[RT_MAP_NAME]);

  /* Permit check. */
  if (strncmp (argv1[RT_MAP_ACTION], "permit", strlen (argv1[RT_MAP_ACTION])) == 0)
    permit = RMAP_PERMIT;
  else if (strncmp (argv1[RT_MAP_ACTION], "deny", strlen (argv1[RT_MAP_ACTION])) == 0)
    permit = RMAP_DENY;
  else {
      return CMD_SUCCESS;
  }

  /* Preference check. */
  if (pref == ULONG_MAX) {
      return CMD_SUCCESS;
  }
  if (pref == 0 || pref > 65535) {
      return CMD_SUCCESS;
  }

  index = route_map_index_get (map, permit, pref);

  if (argc1 == RT_MAP_DESCRIPTION) {
      if (index->description)
        XFREE (MTYPE_TMP, index->description);
      index->description = argv_concat (&argv1[RT_MAP_DESCRIPTION], 1, 0);
  }

  /*
   * Add route map match command
   */
  for (i = 0; i < argcmatch; i += 2) {
      ret = route_map_add_match (index, argvmatch[i], argvmatch[i+1]);
      /* log if error */
      ret = policy_ovsdb_rt_map_vlog(ret);
  }

  /*
   * Add route map set command
   */
  for (i = 0; i < argcset; i += 2) {
      ret = route_map_add_set (index, argvset[i], argvset[i+1]);
      ret = policy_ovsdb_rt_map_vlog(ret);
  }

  return CMD_SUCCESS;
}

/*
 * ip prefix-list PL_ADVERTISE_DOWNSTREAM seq 5 permit {{ dummy0.network }}
 *
 * Get prefix configuration from ovsdb database
 */
int
policy_prefix_list_apply_changes (struct ovsdb_idl *idl,
                        char **argv1, char **argvseq,
                        int argc1, int argcseq,
                        unsigned long seqnum)
{
  int ret;
  enum prefix_list_type type;
  struct prefix_list *plist;
  struct prefix_list_entry *pentry;
  struct prefix_list_entry *dup;
  struct prefix p;
  int any = 0;
  int lenum = 0;
  int genum = 0;
  afi_t afi = AFI_IP;

  if (!argc1)
        return CMD_SUCCESS;

  /* Get prefix_list with name. */
  plist = prefix_list_get (afi, argv1[PREFIX_LIST_NAME]);

  /* Check filter type. */
  if (strncmp ("permit", argv1[PREFIX_LIST_ACTION], 1) == 0)
    type = PREFIX_PERMIT;
  else if (strncmp ("deny", argv1[PREFIX_LIST_ACTION], 1) == 0)
    type = PREFIX_DENY;
  else {
        return CMD_SUCCESS;
  }

  /* "any" is special token for matching any IPv4 addresses.  */
  if (afi == AFI_IP) {
      if (strncmp ("any", argv1[PREFIX_LIST_PREFIX],
                 strlen (argv1[PREFIX_LIST_PREFIX])) == 0) {
          ret = str2prefix_ipv4 ("0.0.0.0/0", (struct prefix_ipv4 *) &p);
          genum = 0;
          lenum = IPV4_MAX_BITLEN;
          any = 1;
      } else
        ret = str2prefix_ipv4 (argv1[PREFIX_LIST_PREFIX], (struct prefix_ipv4 *) &p);

      if (ret <= 0) {
           return CMD_SUCCESS;
      }
 }

  /* Make prefix entry. */
  pentry = prefix_list_entry_make (&p, type, seqnum, lenum, genum, any);

  /* Check same policy. */
  dup = prefix_entry_dup_check (plist, pentry);

  if (dup) {
      prefix_list_entry_free (pentry);
      return CMD_SUCCESS;
  }

  /* Install new filter to the access_list. */
  prefix_list_entry_add (plist, pentry);

  return CMD_SUCCESS;
}

int
policy_prefix_list_read_ovsdb_apply_changes (struct ovsdb_idl *idl)
{
  int ret;
  enum prefix_list_type type;
  struct prefix_list *plist;
  struct prefix_list_entry *pentry;
  struct prefix_list_entry *dup;
  struct prefix p;
  int any = 0;
  int seqnum = -1;
  int lenum = 0;
  int genum = 0;
  afi_t afi = AFI_IP;
  char **argv1;
  char **argvseq;
  int argc1 = -1 , argcseq = -1;
  const struct ovsrec_prefix_list_entry * prefix_first;
  char *tmp;
  const struct ovsrec_prefix_list * ovs_plist;
  struct ovsrec_prefix_list_entry * ovs_entry;
  int i;

  prefix_first = ovsrec_prefix_list_entry_first(idl);
  if (prefix_first == NULL) {
       VLOG_INFO("Nothing  prefix list configed\n");
     return CMD_SUCCESS;
  }

  if ( !(OVSREC_IDL_ANY_TABLE_ROWS_MODIFIED(prefix_first, idl_seqno)) &&
     !(OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(prefix_first, idl_seqno)) ) {
     VLOG_INFO("Nothing changed for prefix list \n");
     return CMD_SUCCESS;
  }
  /*
   * allocate two argv lists
   */
  if (!(argv1 = policy_ovsdb_alloc_arg_list(MAX_ARGC, MAX_ARG_LEN)) ||
         !(argvseq = policy_ovsdb_alloc_arg_list(MAX_ARGC, MAX_ARG_LEN))) {
     return CMD_SUCCESS;
  }
  /*
   * Read ovsdb and apply changes
   */
  OVSREC_PREFIX_LIST_FOR_EACH(ovs_plist, idl) {
    strcpy(argv1[PREFIX_LIST_NAME], ovs_plist->name);
    argc1 = PREFIX_LIST_NAME;
    for (i = 0; i < ovs_plist->n_prefix_list_entries; i ++) {
        ovs_entry = ovs_plist->value_prefix_list_entries[i];
        if ( !(OVSREC_IDL_IS_ROW_INSERTED(ovs_entry, idl_seqno)) &&
               !(OVSREC_IDL_IS_ROW_MODIFIED(ovs_entry, idl_seqno))) {
            continue;
        }
        VLOG_INFO("prefix list configed modified \n");
        strcpy(argv1[PREFIX_LIST_ACTION], ovs_entry->action);
        strcpy(argv1[PREFIX_LIST_PREFIX], ovs_entry->prefix);
        argc1 = PREFIX_LIST_PREFIX + 1;
        seqnum = ovs_plist->key_prefix_list_entries[i];
        argcseq =1 ;

        policy_prefix_list_apply_changes (idl, argv1, argvseq,
                        argc1, argcseq, seqnum);
    }
 }

  policy_ovsdb_free_arg_list(&argv1, MAX_ARGC);
  policy_ovsdb_free_arg_list(&argvseq, MAX_ARGC);
  return CMD_SUCCESS;
}
