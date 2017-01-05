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

include ../../defs.mk

BASHSRCS=datacollect2 processtrak paramdb2

all:

clean:
	rm -f *~ core.* *.o a.out octave-core

distclean: clean

realclean: distclean

depend:

install:
	$(INSTALL) -d $(PREFIX)/etc/bash_completion.d
	for srcfile in $(BASHSRCS) ; do $(INSTALL) -m 644 $$srcfile $(PREFIX)/etc/bash_completion.d ; done
