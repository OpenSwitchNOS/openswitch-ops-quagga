/* AS path filter list.
   Copyright (C) 1999 Kunihiro Ishiguro

This file is part of GNU Zebra.

GNU Zebra is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 2, or (at your option) any
later version.

GNU Zebra is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with GNU Zebra; see the file COPYING.  If not, write to the Free
Software Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
02111-1307, USA.  */

#ifndef _QUAGGA_BGP_FILTER_H
#define _QUAGGA_BGP_FILTER_H

enum as_filter_type
{
  AS_FILTER_DENY,
  AS_FILTER_PERMIT
};

/* To-Do: Move the following as_list_type_t & as_list definitions into the
 *        ENABLE_OVSDB macro */
typedef enum as_list_type
{
  AS_LIST_TYPE_STRING,
  AS_LIST_TYPE_NUMBER
} as_list_type_t;

/* AS path filter list. */
struct as_list
{
  char *name;

  enum as_list_type type;

  struct as_list *next;
  struct as_list *prev;

  struct as_filter *head;
  struct as_filter *tail;
};

extern void bgp_filter_init (void);
extern void bgp_filter_reset (void);

extern enum as_filter_type as_list_apply (struct as_list *, void *);

extern struct as_list *as_list_lookup (const char *);
extern void as_list_add_hook (void (*func) (void));
extern void as_list_delete_hook (void (*func) (void));

#ifdef ENABLE_OVSDB
/* List of AS filter list. */
struct as_list_list
{
  struct as_list *head;
  struct as_list *tail;
};

/* AS path filter master. */
struct as_list_master
{
  /* List of access_list which name is number. */
  struct as_list_list num;

  /* List of access_list which name is string. */
  struct as_list_list str;

  /* Hook function which is executed when new access_list is added. */
  void (*add_hook) (void);

  /* Hook function which is executed when access_list is deleted. */
  void (*delete_hook) (void);
};

/* Element of AS path filter. */
struct as_filter
{
  struct as_filter *next;
  struct as_filter *prev;

  enum as_filter_type type;

  regex_t *reg;
  char *reg_str;
};


extern void as_list_filter_add (struct as_list *aslist, struct as_filter *asfilter);

extern void as_filter_free (struct as_filter *asfilter);

extern int as_list_dup_check (struct as_list *, struct as_filter *);

extern struct as_list * as_list_get (const char *name);

extern struct as_filter * as_filter_make (regex_t *reg, const char *reg_str, enum as_filter_type type);

extern void as_list_filter_delete (struct as_list *aslist, struct as_filter *asfilter);

extern struct as_list_master * as_list_master_get();
#endif

#endif /* _QUAGGA_BGP_FILTER_H */
