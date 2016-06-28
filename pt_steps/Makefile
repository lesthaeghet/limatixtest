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

SUBDIRS=  #matlab



PROGS=

all:
	@for i in $(SUBDIRS) ; do if [ -d $$i ] && [ -f $$i/Makefile ] ; then $(MAKE) $(MFLAGS) -C $$i ; fi done




#$(TOPYCHECK:.py=.pycheck)
#ifeq ($(PYCHECKER), /none)
#	@echo "WARNING: pychecker not found (install from pychecker.sourceforge.net)"
#endif


#%.pycheck: %.py
#	$(PYCHECKER) --only $<
#	touch $@

clean:
	@for i in $(SUBDIRS) ; do if [ -d $$i ] && [ -f $$i/Makefile ] ; then $(MAKE) $(MFLAGS) -C $$i clean; fi done
	rm -f *.bak *~ core.* *.o *.pyc a.out octave-core 

distclean: clean
	@for i in $(SUBDIRS) ; do if [ -d $$i ] && [ -f $$i/Makefile ] ; then $(MAKE) $(MFLAGS) -C $$i distclean ; fi done

realclean: distclean


depend:
	@for i in $(SUBDIRS) ; do if [ -d $$i ] && [ -f $$i/Makefile ] ; then $(MAKE) $(MFLAGS) -C $$i depend ; fi done

install:
	@for i in $(SUBDIRS) ; do if [ -d $$i ] && [ -f $$i/Makefile ] ; then $(MAKE) $(MFLAGS) -C $$i install ; fi done
	#$(INSTALL) -d $(DCINSTDIR)/  # Directory should already exist
	$(INSTALL) -d $(DCINSTDIR)/pt_steps
	#$(INSTALL) *.py $(DCINSTDIR)/pt_steps # uncomment once we actually have installable steps


