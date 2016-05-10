#  Process this file with Automake to create Makefile.in
#
#  File: Makefile.am

AM_CFLAGS =  ${OPSCLI_CFLAGS}
AM_CFLAGS += -I${top_srcdir}/include
AM_CFLAGS += -I$(LOCAL_SYSROOT_DIR)/usr/local/include/ovs -DOPS

libdir=${prefix}/lib/cli/plugins

lib_LTLIBRARIES = libl3routes_cli.la

libl3routes_cli_la_SOURCES = l3routes_vty.c l3routes_vty.h vtysh_ovsdb_l3routes_context.c \
														 vtysh_ovsdb_l3routes_context.h
libl3routes_cli_la_LDFLAGS =  -avoid-version

install-exec-hook:
	@(cd $(DESTDIR)$(libdir) && $(RM) $(lib_LTLIBRARIES))
