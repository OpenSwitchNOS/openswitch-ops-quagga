## Process this file with automake to produce Makefile.in.

AM_CPPFLAGS = -I.. -I$(top_srcdir) -I$(top_srcdir)/lib -I$(top_builddir)/lib
DEFS = @DEFS@ $(LOCAL_OPTS) -DSYSCONFDIR=\"$(sysconfdir)/\"
INSTALL_SDATA=@INSTALL@ -m 600

lib_LTLIBRARIES = libospf.la
libospf_la_LDFLAGS = -version-info 0:0:0

if ENABLE_OVSDB
sbin_PROGRAMS = ops-ospfd
else
sbin_PROGRAMS = ospfd
endif

libospf_la_SOURCES = \
	ospfd.c ospf_zebra.c ospf_interface.c ospf_ism.c ospf_neighbor.c \
	ospf_nsm.c ospf_dump.c ospf_network.c ospf_packet.c ospf_lsa.c \
	ospf_spf.c ospf_route.c ospf_ase.c ospf_abr.c ospf_ia.c ospf_flood.c \
	ospf_lsdb.c ospf_asbr.c ospf_routemap.c ospf_snmp.c \
	ospf_opaque.c ospf_te.c ospf_vty.c ospf_api.c ospf_apiserver.c
if ENABLE_OVSDB
libospf_la_SOURCES += ospf_ovsdb_if.c
endif

ospfdheaderdir = $(pkgincludedir)/ospfd

ospfdheader_HEADERS = \
	ospf_api.h ospf_asbr.h ospf_dump.h ospf_lsa.h ospf_lsdb.h \
	ospf_nsm.h ospf_ism.h ospf_opaque.h ospfd.h

noinst_HEADERS = \
	ospf_interface.h ospf_neighbor.h ospf_network.h ospf_packet.h \
	ospf_zebra.h ospf_spf.h ospf_route.h ospf_ase.h ospf_abr.h ospf_ia.h \
	ospf_flood.h ospf_snmp.h ospf_te.h ospf_vty.h ospf_apiserver.h
if ENABLE_OVSDB
noinst_HEADERS += ospf_ovsdb_if.h
endif


if ENABLE_OVSDB
ops_ospfd_SOURCES = ospf_main.c
ops_ospfd_LDADD = libospf.la ../lib/libzebra.la @LIBCAP@
ops_ospfd_LDADD += -lovscommon -lovsdb -lpthread -lsupportability
else
ospfd_SOURCES = ospf_main.c
ospfd_LDADD = libospf.la ../lib/libzebra.la @LIBCAP@
endif

EXTRA_DIST = OSPF-MIB.txt OSPF-TRAP-MIB.txt ChangeLog.opaque.txt

examplesdir = $(exampledir)
dist_examples_DATA = ospfd.conf.sample

