## Process this file with automake to produce Makefile.in.

AM_CPPFLAGS = -I.. -I$(top_srcdir) -I$(top_srcdir)/lib -I$(top_builddir)/lib
DEFS = @DEFS@ -DSYSCONFDIR=\"$(sysconfdir)/\" -DMULTIPATH_NUM=@MULTIPATH_NUM@
INSTALL_SDATA=@INSTALL@ -m 600
if ENABLE_OVSDB
SUBDIRS = cli
endif

LIBCAP = @LIBCAP@

ipforward = @IPFORWARD@
if_method = @IF_METHOD@
rt_method = @RT_METHOD@
rtread_method = @RTREAD_METHOD@
kernel_method = @KERNEL_METHOD@
ioctl_method = @IOCTL_METHOD@

otherobj = $(ioctl_method) $(ipforward) $(if_method) \
	$(rt_method) $(rtread_method) $(kernel_method)

if HAVE_NETLINK
othersrc = zebra_fpm_netlink.c
endif

AM_CFLAGS = $(PICFLAGS)
if ENABLE_OVSDB
AM_CFLAGS += -I $(LOCAL_SYSROOT_DIR)/usr/local/include/ovs
endif
AM_LDFLAGS = $(PILDFLAGS)

#
# ovsdb related files must have extra error checks (-Werror)
#
if ENABLE_OVSDB
zebra_ovsdb_if_LDADD = libzebra_ovsdb_if.a
noinst_LIBRARIES = libzebra_ovsdb_if.a
libzebra_ovsdb_if_a_SOURCES = zebra_ovsdb_if.c zebra_ovsdb_if.h \
  zebra_diagnostics.c zebra_diagnostics.h
libzebra_ovsdb_if_a_CFLAGS = $(AM_CFLAGS) -Werror
endif

if ENABLE_OVSDB
sbin_PROGRAMS = ops-zebra
cli_lib_LDADD = cli/libl3routes_cli.la
SUBDIRS = cli
else
sbin_PROGRAMS = zebra
endif

noinst_PROGRAMS = testzebra

zebra_SOURCES = \
	zserv.c main.c interface.c connected.c zebra_rib.c zebra_routemap.c \
	redistribute.c debug.c rtadv.c zebra_snmp.c zebra_vty.c \
	irdp_main.c irdp_interface.c irdp_packet.c router-id.c zebra_fpm.c \
	$(othersrc)

if ENABLE_OVSDB
ops_zebra_SOURCES = $(zebra_SOURCES)
SUBDIRS = cli
endif

testzebra_SOURCES = test_main.c zebra_rib.c interface.c connected.c debug.c \
	zebra_vty.c \
	kernel_null.c  redistribute_null.c ioctl_null.c misc_null.c

noinst_HEADERS = \
	connected.h ioctl.h rib.h rt.h zserv.h redistribute.h debug.h rtadv.h \
	interface.h ipforward.h irdp.h router-id.h kernel_socket.h \
	rt_netlink.h zebra_fpm.h zebra_fpm_private.h
if ENABLE_OVSDB
noinst_HEADERS += zebra_ovsdb_if.h
endif

if ENABLE_OVSDB
ops_zebra_LDADD = $(otherobj) libzebra_ovsdb_if.a ../lib/libzebra.la \
		  $(LIBCAP) -lovscommon -lovsdb -lpthread -lsupportability
ops_zebra_DEPENDENCIES = $(otherobj)
ops_zebra_DEPENDENCIES += libzebra_ovsdb_if.a
else
zebra_LDADD = $(otherobj) libzebra_ovsdb_if.a ../lib/libzebra.la $(LIBCAP)
zebra_DEPENDENCIES = $(otherobj)
endif

if ENABLE_OVSDB
testzebra_LDADD = libzebra_ovsdb_if.a ../lib/libzebra.la $(LIBCAP) -lsupportability
endif

EXTRA_DIST = if_ioctl.c if_ioctl_solaris.c if_netlink.c \
        if_sysctl.c ipforward_proc.c \
	ipforward_solaris.c ipforward_sysctl.c rt_netlink.c \
	rt_socket.c rtread_netlink.c rtread_sysctl.c \
	rtread_getmsg.c kernel_socket.c kernel_netlink.c \
	ioctl.c ioctl_solaris.c \
	GNOME-SMI GNOME-PRODUCT-ZEBRA-MIB

client : client_main.o ../lib/libzebra.la libzebra_ovsdb_if.a
	$(CC) -g -o client client_main.o libzebra_ovsdb_if.a \
	    ../liblzebra.la $(LIBS) $(LIB_IPV6)

quaggaconfdir = $(sysconfdir)

examplesdir = $(exampledir)
dist_examples_DATA = zebra.conf.sample
