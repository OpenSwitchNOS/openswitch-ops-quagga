/* Policy ovsdb integration.
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
 * File: policy_ovsdb.c
 *
 * Purpose: Policy functions for integrating with ovsdb.
 */


#include <stdio.h>
#include <zebra.h>
#include "linklist.h"
#include "memory.h"
#include "vector.h"
#include "prefix.h"
#include "routemap.h"
#include "command.h"
#include "vty.h"
#include "log.h"
#include "openvswitch/vlog.h"
#include "plist.h"
#include "routemap.h"
#include "vswitch-idl.h"
#include "policy_ovsdb.h"

#define MAX_ARGC   10
#define MAX_ARG_LEN  256
#define MTYPE_POLICY MTYPE_BUFFER

extern struct ovsdb_idl *idl;
static unsigned int idl_seqno;

VLOG_DEFINE_THIS_MODULE(policy_config);

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
int
policy_ovsdb_alloc_arg_list(char *** argv, int argcsize, int argvsize)
{
    int i;
    char ** parmv;

    *argv = NULL;
    parmv = xmalloc(sizeof (char *) * argcsize);
    if (!parmv)
        return 1;

    for (i = 0; i < argcsize; i ++)
      {
        parmv[i] = xmalloc(sizeof(char) * argvsize);
        if (!(parmv[i])) {
            policy_ovsdb_free_arg_list(&parmv, argcsize);
            return 1;
        }
      }
    *argv = parmv;
    return 0;
}

/*
 * route-map RM_TO_UPSTREAM_PEER permit 10
 */
/*
 * Read rt map config from ovsdb to argv
 */
void
policy_ovsdb_rt_map_get(struct ovsdb_idl *idl,
                        char **argv1, char **argvmatch, char **argvset,
                        int *argc1, int *argcmatch, int *argcset,
                        unsigned long *pref)
{
    struct ovsrec_route_map_entries * rt_map_first;
    struct ovsrec_route_map_entries * rt_map_next;
    int i, j;
    char *tmp;

    rt_map_first = ovsrec_route_map_entries_first(idl);
    if (rt_map_first == NULL) {
         VLOG_INFO("Nothing  configed\n");
         return;
    }
    /*
     * Any changes
     */
    if (!OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(rt_map_first, idl_seqno)
              && !OVSREC_IDL_ANY_TABLE_ROWS_MODIFIED(rt_map_first, idl_seqno)) {
        VLOG_INFO("No route_map changes");
        return;
    }
    /*
     * Find out the which row changed/inserted
     */
    if ( (OVSREC_IDL_ANY_TABLE_ROWS_MODIFIED(rt_map_first, idl_seqno)) ||
          (OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(rt_map_first, idl_seqno)) )
    {
        OVSREC_ROUTE_MAP_ENTRIES_FOR_EACH(rt_map_next, idl)
        {
            if ( (OVSREC_IDL_IS_ROW_INSERTED(rt_map_next, idl_seqno)) ||
                 (OVSREC_IDL_IS_ROW_MODIFIED(rt_map_next, idl_seqno))) {

                strcpy(argv1[RT_MAP_NAME], rt_map_next->route_map->name);
                strcpy(argv1[RT_MAP_ACTION], rt_map_next->action);
                if (pref)
                    *pref = rt_map_next->preference;
                strcpy(argv1[RT_MAP_DESCRIPTION], rt_map_next->description);
                *argc1 = RT_MAP_DESCRIPTION;

                for (i = 0, j = 0; i < MAX_ARGC && j < MAX_ARGC; i++ ) {
                    tmp  = smap_get(&rt_map_next->match, match_table[i].table_key);
                    if (tmp) {
                        strcpy(argvmatch[j++], match_table[i].cli_cmd);
                        strcpy(argvmatch[j++], tmp);
                    }
                }
                *argcmatch = i;

                for (i = 0, j = 0; i < MAX_ARGC && j < MAX_ARGC; i++ ) {
                    tmp  = smap_get(&rt_map_next->set, set_table[i].table_key);
                    if (tmp) {
                        strcpy(argvset[j++], set_table[i].cli_cmd);
                        strcpy(argvset[j++], tmp);
                    }
                }
                *argcset = i;
            }
        }
    }
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
        VLOG_INFO("%% Can't find rule.%s\n");
            return CMD_WARNING;
        case RMAP_COMPILE_ERROR:
            VLOG_INFO("%% Argument is malformed.%s\n");
            return CMD_WARNING;
        }
    }
    return CMD_SUCCESS;
}

/*
 * Route map set community on match
 */
static int
policy_ovsdb_rt_map_set_community(char ** argv, int argc,
                         struct route_map_index *index)
{
    int i;
    int first = 0;
    int additive = 0;
    struct buffer *b;
    struct community *com = NULL;
    char *str;
    char *argstr;
    int ret;

    b = buffer_new (1024);

    for (i = 0; i < argc; i++)
    {
      if (strncmp (argv[i], "additive", strlen (argv[i])) == 0)
        {
          additive = 1;
          continue;
        }

      if (first)
        buffer_putc (b, ' ');
      else
        first = 1;


      if (first)
        buffer_putc (b, ' ');
      else
        first = 1;

      if (strncmp (argv[i], "internet", strlen (argv[i])) == 0)
        {
          buffer_putstr (b, "internet");
          continue;
        }
      if (strncmp (argv[i], "local-AS", strlen (argv[i])) == 0)
        {
          buffer_putstr (b, "local-AS");
          continue;
        }
      if (strncmp (argv[i], "no-a", strlen ("no-a")) == 0
          && strncmp (argv[i], "no-advertise", strlen (argv[i])) == 0)
        {
          buffer_putstr (b, "no-advertise");
          continue;
        }
      if (strncmp (argv[i], "no-e", strlen ("no-e"))== 0
          && strncmp (argv[i], "no-export", strlen (argv[i])) == 0)
        {
          buffer_putstr (b, "no-export");
          continue;
        }
      buffer_putstr (b, argv[i]);
    }
    buffer_putc (b, '\0');

    /* Fetch result string then compile it to communities attribute.  */
    str = buffer_getstr (b);
    buffer_free (b);

    if (str)
    {
      com = community_str2com (str);
      XFREE (MTYPE_TMP, str);
    }

    /* Can't compile user input into communities attribute.  */
    if (! com)
    {
      return CMD_WARNING;
    }

    /* Set communites attribute string.  */
    str = community_str (com);

    if (additive)
    {
      argstr = XCALLOC (MTYPE_TMP, strlen (str) + strlen (" additive") + 1);
      strcpy (argstr, str);
      strcpy (argstr + strlen (str), " additive");
      ret = route_map_add_set (index, "community", argstr);
      ret = policy_ovsdb_rt_map_vlog(ret);
      XFREE (MTYPE_TMP, argstr);
    } else
    {
      ret = route_map_add_set (index, "community", str);
    }

    community_free (com);
    return ret;
}

/*
 * Set up route map at the back end
 * Read from ovsdb, then program back end policy route map
 *
 * Specific cli command:
 * route-map RM_TO_UPSTREAM_PEER permit 10
 */
int
policy_ovsdb_rt_map(struct ovsdb_idl *idl)
{
  int permit;
  unsigned long pref;
  struct route_map *map;
  struct route_map_index *index;
  char *endptr = NULL;
  int i;
  char **argv1;
  char **argvmatch;
  char **argvset;
  int argc1, argcmatch, argcset;
  int ret;

  /*
   * alloc three argv lists
   */
  if(policy_ovsdb_alloc_arg_list(&argv1, MAX_ARGC, MAX_ARG_LEN) ||
            policy_ovsdb_alloc_arg_list(&argvmatch, MAX_ARGC, MAX_ARG_LEN) ||
            policy_ovsdb_alloc_arg_list(*argvset, MAX_ARGC, MAX_ARG_LEN)) {
        return CMD_SUCCESS;
  }

  /*
   * Read config from ovsdb into argv list
   */
  pref = 0;
  policy_ovsdb_rt_map_get(idl, argv1, argvmatch, argvset,
                            &argc1, &argcmatch, &argvset, &pref);
  /*
   * Program backend
   * RT_MAP_DESCRIPTION
   */

  /* Get route map. */
  map = route_map_get (argv1[RT_MAP_NAME]);

  /* Permit check. */
  if (strncmp (argv1[RT_MAP_ACTION], "permit", strlen (argv1[RT_MAP_ACTION])) == 0)
    permit = RMAP_PERMIT;
  else if (strncmp (argv1[RT_MAP_ACTION], "deny", strlen (argv1[RT_MAP_ACTION])) == 0)
    permit = RMAP_DENY;
  else
    {
        goto RETERROR;
    }

  /* Preference check. */
  if (pref == ULONG_MAX)
  {
        goto RETERROR;
  }
  if (pref == 0 || pref > 65535)
  {
      goto RETERROR;
  }

  index = route_map_index_get (map, permit, pref);
    /*
     * Add route map match command
     */
  for (i = 0; i < argvmatch; i += 2) {
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
RETERROR:
  policy_ovsdb_free_arg_list(&argv1, MAX_ARGC);
  policy_ovsdb_free_arg_list(&argvmatch, MAX_ARGC);
  policy_ovsdb_free_arg_list(&argvset, MAX_ARGC);

  return CMD_SUCCESS;
}

/*
 * ip prefix-list PL_ADVERTISE_DOWNSTREAM seq 5 permit {{ dummy0.network }}
 *
 * Get prefix configuration from ovsdb database
 */
void
policy_ovsdb_prefix_list_read(struct ovsdb_idl *idl,
                        char **argv1, char **argvseq,
                        int *argc1, int *argcseq,
                        int *seqnum)
{
    struct ovsrec_prefix_list_entries * prefix_first;
    struct ovsrec_prefix_list_entries * prefix_next;
    char *tmp;

    prefix_first = ovsrec_prefix_list_entries_first(idl);
    if (prefix_first == NULL) {
         VLOG_INFO("Nothing  configed\n");
         return;
    }
    /*
     * Any changes
     */
    if (!OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(prefix_first, idl_seqno)
              && !OVSREC_IDL_ANY_TABLE_ROWS_MODIFIED(prefix_first, idl_seqno)) {
        VLOG_INFO("No route_map changes");
        return;
    }

    if ( (OVSREC_IDL_ANY_TABLE_ROWS_MODIFIED(prefix_first, idl_seqno)) ||
       (OVSREC_IDL_ANY_TABLE_ROWS_INSERTED(prefix_first, idl_seqno)) )
    {
        OVSREC_PREFIX_LIST_ENTRIES_FOR_EACH(prefix_next, idl)
        {
            if ( (OVSREC_IDL_IS_ROW_INSERTED(prefix_next, idl_seqno)) ||
                 (OVSREC_IDL_IS_ROW_MODIFIED(prefix_next, idl_seqno)))
            {
                strcpy(argv1[PREFIX_LIST_NAME], prefix_next->prefix_list->name);
                strcpy(argv1[PREFIX_LIST_ACTION], prefix_next->action);
                strcpy(argv1[PREFIX_LIST_PREFIX], prefix_next->prefix);
                *argc1 = PREFIX_LIST_PREFIX + 1;

                if(seqnum)
                    *seqnum = prefix_next->sequence;
                *argcseq =1 ;
            }
        }
    }
}

/*
 * Set up prefix list at the backend
 */
int
policy_ovsdb_prefix_list_get (struct ovsdb_idl *idl)
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
  int argc1 = 0 , argcseq = 0;


    /*
     * alloc two argv lists
     */
    if(policy_ovsdb_alloc_arg_list(&argv1, MAX_ARGC, MAX_ARG_LEN) ||
            policy_ovsdb_alloc_arg_list(&argvseq, MAX_ARGC, MAX_ARG_LEN)) {
        return CMD_SUCCESS;
    }

    /*
     * get prefix arg list from ovsdb
     */
    policy_ovsdb_prefix_list_read(idl, argv1, argvseq, &argc1, &argcseq, &seqnum);


  /* Get prefix_list with name. */
  plist = prefix_list_get (afi, argv1[PREFIX_LIST_NAME]);

  /* Check filter type. */
  if (strncmp ("permit", argv1[PREFIX_LIST_ACTION], 1) == 0)
    type = PREFIX_PERMIT;
  else if (strncmp ("deny", argv1[PREFIX_LIST_ACTION], 1) == 0)
    type = PREFIX_DENY;
  else
    {
        goto RETERROR;
    }

  /* "any" is special token for matching any IPv4 addresses.  */
  if (afi == AFI_IP)
    {
      if (strncmp ("any", argv1[PREFIX_LIST_PREFIX], strlen (argv1[PREFIX_LIST_PREFIX])) == 0)
        {
          ret = str2prefix_ipv4 ("0.0.0.0/0", (struct prefix_ipv4 *) &p);
          genum = 0;
          lenum = IPV4_MAX_BITLEN;
          any = 1;
        }
      else
        ret = str2prefix_ipv4 (argv1[PREFIX_LIST_PREFIX], (struct prefix_ipv4 *) &p);

      if (ret <= 0)
        {
           goto RETERROR;
        }
    }

  /* Make prefix entry. */
  pentry = prefix_list_entry_make (&p, type, seqnum, lenum, genum, any);

  /* Check same policy. */
  dup = prefix_entry_dup_check (plist, pentry);

  if (dup)
    {
      prefix_list_entry_free (pentry);
        goto RETERROR;
    }

  /* Install new filter to the access_list. */
  prefix_list_entry_add (plist, pentry);

RETERROR:
  policy_ovsdb_free_arg_list(&argv1, MAX_ARGC);
  policy_ovsdb_free_arg_list(&argvseq, MAX_ARGC);

  return CMD_SUCCESS;
}
