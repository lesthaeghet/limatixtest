#    Dataguzzler: A Platform for High Performance Laboratory Data Acquisition 
#    Copyright (C) 2005-2006 Iowa State University
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
#    As a special exception, third party data acquisition libraries
#    or hardware drivers may be treated as if they were a major component
#    of the operating system; therefore the special exception in GPLV2,
#    section 3 applies to them.

include ../defs.mk

SUBDIRS=bash_completions

all:
	@for i in $(SUBDIRS) ; do $(MAKE) $(MFLAGS) -C $$i ; done

clean:
	@for i in $(SUBDIRS) ; do $(MAKE) $(MFLAGS) -C $$i clean; done
	rm -f *~ core.* *.o a.out octave-core

distclean: clean

realclean: distclean

depend:
	@for i in $(SUBDIRS) ; do $(MAKE) $(MFLAGS) -C $$i depend; done

install:
	$(INSTALL) -d $(PREFIX)/share
	$(INSTALL) -d $(PREFIX)/share/applications
	$(INSTALL) -d $(PREFIX)/share/mime
	$(INSTALL) -d $(PREFIX)/share/mime/packages
	$(INSTALL) -m 644 dc_glade.desktop $(PREFIX)/share/applications
	$(INSTALL) -m 644 datacollect2.desktop $(PREFIX)/share/applications
	update-desktop-database
	update-mime-database $(PREFIX)/share/mime
	@for i in $(SUBDIRS) ; do $(MAKE) $(MFLAGS) -C $$i install; done



