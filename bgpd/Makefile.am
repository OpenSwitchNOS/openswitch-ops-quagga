## Process this file with automake to produce Makefile.in.

AM_CPPFLAGS = -I.. -I$(top_srcdir) -I$(top_srcdir)/lib -I$(top_builddir)/lib
DEFS = @DEFS@ -DSYSCONFDIR=\"$(sysconfdir)/\"
INSTALL_SDATA=@INSTALL@ -m 600

AM_CFLAGS = $(PICFLAGS)
if ENABLE_OVSDB
AM_CFLAGS += -I $(LOCAL_SYSROOT_DIR)/usr/local/include/ovs
endif
AM_LDFLAGS = $(PILDFLAGS)

noinst_LIBRARIES = libbgp.a
if ENABLE_OVSDB
noinst_LIBRARIES += libbgp_ovsdb.a
endif
sbin_PROGRAMS = bgpd

libbgp_a_SOURCES = \
	bgpd.c bgp_fsm.c bgp_aspath.c bgp_community.c bgp_attr.c \
	bgp_debug.c bgp_route.c bgp_zebra.c bgp_open.c bgp_routemap.c \
	bgp_packet.c bgp_network.c bgp_filter.c bgp_regex.c bgp_clist.c \
	bgp_dump.c bgp_snmp.c bgp_ecommunity.c bgp_mplsvpn.c bgp_nexthop.c \
	bgp_damp.c bgp_table.c bgp_advertise.c bgp_mpath.c

#
# enable extra error checking (-Werror) for ovsdb files
#
if ENABLE_OVSDB
libbgp_a_SOURCES += bgp_ovsdb_if.c bgp_ovsdb_route.c bgp_backend_functions.c
libbgp_ovsdb_a_CFLAGS = $(AM_CFLAGS) -Werror
else
libbgp_a_SOURCES += bgp_vty.c
endif

noinst_HEADERS = \
	bgp_aspath.h bgp_attr.h bgp_community.h bgp_debug.h bgp_fsm.h \
	bgp_network.h bgp_open.h bgp_packet.h bgp_regex.h bgp_route.h \
	bgpd.h bgp_filter.h bgp_clist.h bgp_dump.h bgp_zebra.h \
	bgp_ecommunity.h bgp_mplsvpn.h bgp_nexthop.h bgp_damp.h bgp_table.h \
	bgp_advertise.h bgp_snmp.h bgp_vty.h bgp_mpath.h
if ENABLE_OVSDB
noinst_HEADERS += bgp_ovsdb_if.h bgp_ovsdb_route.h
endif

bgpd_SOURCES = bgp_main.c
bgpd_LDADD = libbgp.a ../lib/libzebra.la @LIBCAP@ @LIBM@
if ENABLE_OVSDB
bgpd_LDADD += libbgp_ovsdb.a -lovscommon -lovsdb -lpthread
endif

if VTYSH
CLEANFILES = bgp_vtysh_sources.c
bgp_vtysh_sources.c: Makefile
	cat $(libbgp_a_SOURCES) $(bgpd_SOURCES) > $@
endif

examplesdir = $(exampledir)
dist_examples_DATA = bgpd.conf.sample bgpd.conf.sample2

EXTRA_DIST = BGP4-MIB.txt

