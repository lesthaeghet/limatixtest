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

include defs.mk


DIST_FILES=.


PUBEXCLUDE=--exclude .hg 


PYSUBDIRS=widgets steps
CHXSUBDIRS=checklists


SUBDIRS=dcp_steps  #matlab



PROGS=dc_checklist dc_glade datacollect2 dc_paramdb2 dc_ricohphoto dc_process dc_checkprovenance dc_xlg2dpd dc_chx2chf dc_getpath


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
	rm -f *.bak *~ core.* *.o *.pyc a.out octave-core *.pycheck widgets/*~ steps/*~ widgets/core.* steps/core.* widgets/*.pyc steps/*.pyc checklists/*~ glade-3/*~ glade-3/glade_catalogs/*~ glade-3/glade_catalogs/*.pyc glade-3/glade_modules/*~ glade-3/glade_modules/*.pyc lib/*~ lib/core.* lib/*.o lib/*.pyc lib/a.out lib/octave-core lib/*.pycheck conf/*~ conf/core.* conf/*.bak conf/*.pyc doc/*.bak doc/*.pyc doc/*~ bin/*~ bin/*.bak bin/*.pyc
	rm -rf lib/__pycache__ steps/__pycache__ widgets/__pycache__

distclean: clean
	@for i in $(SUBDIRS) ; do if [ -d $$i ] && [ -f $$i/Makefile ] ; then $(MAKE) $(MFLAGS) -C $$i distclean ; fi done

realclean: distclean


depend:
	@for i in $(SUBDIRS) ; do if [ -d $$i ] && [ -f $$i/Makefile ] ; then $(MAKE) $(MFLAGS) -C $$i depend ; fi done

install:
	@for i in $(SUBDIRS) ; do if [ -d $$i ] && [ -f $$i/Makefile ] ; then $(MAKE) $(MFLAGS) -C $$i install ; fi done
	$(INSTALL) -d $(DCINSTDIR)
	rm -f $(PREFIX)/datacollect2
	ln -s $(DCINSTDIR) $(PREFIX)/datacollect2
	$(INSTALL) -d $(DCINSTDIR)/lib
	$(INSTALL) -d $(DCINSTDIR)/conf
	$(INSTALL) -d $(DCINSTDIR)/doc
	$(INSTALL) -d $(DCINSTDIR)/bin
	@for i in $(PYSUBDIRS) ; do if [ -d $$i ] ; then $(INSTALL) -d $(DCINSTDIR)/$$i/ ; echo $$i/*.py $$i/*.glade ; $(INSTALL) $$i/*.py $$i/*.glade $(DCINSTDIR)/$$i/; fi done
	@for i in $(CHXSUBDIRS) ; do if [ -d $$i ] ; then $(INSTALL) -d $(DCINSTDIR)/$$i/ ; echo $$i/*.chx ; $(INSTALL) $$i/*.chx $(DCINSTDIR)/$$i/ ; $(INSTALL) $$i/*.png $(DCINSTDIR)/$$i/ ; fi done	
	$(INSTALL) -d $(DCINSTDIR)/glade-3
	$(INSTALL) glade-3/*.txt $(DCINSTDIR)/glade-3/
	$(INSTALL) -d $(DCINSTDIR)/glade-3/glade_catalogs
	$(INSTALL) glade-3/glade_catalogs/* $(DCINSTDIR)/glade-3/glade_catalogs/
	$(INSTALL) -d $(DCINSTDIR)/glade-3/glade_modules
	$(INSTALL) glade-3/glade_modules/* $(DCINSTDIR)/glade-3/glade_modules/
	$(INSTALL) README.txt $(DCINSTDIR)/
	$(INSTALL) lib/*.glade $(DCINSTDIR)/lib
	$(INSTALL) lib/*.py $(DCINSTDIR)/lib
	$(INSTALL) conf/*.glade $(DCINSTDIR)/conf
	$(INSTALL) conf/*.dcc $(DCINSTDIR)/conf
	$(INSTALL) doc/* $(DCINSTDIR)/doc
	( for i in $(PROGS) ; do $(INSTALL) bin/$$i $(DCINSTDIR)/bin/ ; done )
	( for i in $(PROGS) ; do rm -f $(PREFIX)/bin/$$i ; ln -s $(DCINSTDIR)/bin/$$i $(PREFIX)/bin/$$i ; done )



checklib:
	@for i in lib/*.py ; do $(PYCHECKER) --only --limit=30 $$i ; done 

checksteps:
	( export PYTHONPATH=lib/:widgets/:$$PYTHONPATH ; for i in steps/*.py ; do $(PYCHECKER) --only --limit=30 $$i ; done  )


checkwidgets:
	( export PYTHONPATH=lib/:$$PYTHONPATH ;for i in widgets/*.py ; do $(PYCHECKER) --only --limit=30 $$i ; done )

commit: realclean
	hg addremove
	hg commit


dist:
	mv VERSION VERSIONtmp
	sed 's/-[^-]*$$//' <VERSIONtmp >VERSION    # remove trailing -devel
	date "+%B %d, %Y" >VERSIONDATE
	rm -f VERSIONtmp

	$(MAKE) $(MFLAGS) commit
	$(MAKE) $(MFLAGS) all
	$(MAKE) $(MFLAGS) realclean
	hg tag -f `cat VERSION`

	tar -cvzf /tmp/realclean-datacollect2-`cat VERSION`.tar.gz $(DIST_FILES)

	tar $(PUBEXCLUDE) -cvzf /tmp/realclean-datacollect2-pub-`cat VERSION`.tar.gz $(DIST_FILES)

	@for archive in  datacollect2-`cat VERSION` datacollect2-pub-`cat VERSION`  ; do mkdir /tmp/$$archive ; tar -C /tmp/$$archive  -x -f /tmp/realclean-$$archive.tar.gz ; make -C /tmp/$$archive all ; make -C /tmp/$$archive distclean ; tar -C /tmp -c -v -z -f /home/sdh4/research/software/archives/$$archive.tar.gz $$archive ; done

	mv VERSION VERSIONtmp
	awk -F . '{ print $$1 "." $$2 "." $$3+1 "-devel"}' <VERSIONtmp >VERSION  # increment version number and add trailing-devel
	rm -f VERSIONtmp
	rm -f VERSIONDATE
