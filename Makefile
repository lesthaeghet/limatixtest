
include defs.mk


DIST_FILES=.


PUBEXCLUDE=--exclude .hg --exclude limatix/canonicalize_path/.hg  --exclude limatix/dc_lxml_treesync/.hg


PYSUBDIRS=widgets steps
CHXSUBDIRS=checklists


SUBDIRS=pt_steps xslt #matlab



PROGS=dc_checklist dc_glade datacollect2 dc_paramdb2 dc_ricohphoto processtrak dc_checkprovenance dc_xlg2dpd dc_chx2chf dc_getpath


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
	rm -f *.bak *~ core.* *.o *.pyc a.out octave-core *.pycheck limatix/widgets/*~ limatix/steps/*~ limatix/widgets/core.* limatix/steps/core.* limatix/widgets/*.pyc limatix/steps/*.pyc checklists/*~ plans/*~ limatix/widgets/glade-3/*~ limatix/widgets/glade-3/glade_catalogs/*~ limatix/widgets/glade-3/glade_catalogs/*.pyc limatix/widgets/glade-3/glade_modules/*~ limatix/widgets/glade-3/glade_modules/*.pyc limatix/*~ limatix/core.* limatix/*.o limatix/*.pyc limatix/a.out limatix/octave-core limatix/*.pycheck conf/*~ conf/core.* conf/*.bak conf/*.pyc doc/*.bak doc/*.pyc doc/*~ doc/processtrak_example/*~ doc/processtrak_example/*.pyc doc/processtrak_example/creston_jan2016/*.png  doc/processtrak_example/creston_jan2016/*.kml doc/processtrak_example/*.xlp doc/processtrak_example/creston_jan2016_out.ods  doc/processtrak_example/.creston*.bak*  limatix/bin/*~ limatix/bin/*.bak limatix/bin/*.pyc
	rm -rf lib/__pycache__ steps/__pycache__ widgets/__pycache__ doc/processtrak_example/__pycache__
	rm -rf build/
	rm -rf dist/
	rm -rf limatix.egg-info

distclean: clean
	@for i in $(SUBDIRS) ; do if [ -d $$i ] && [ -f $$i/Makefile ] ; then $(MAKE) $(MFLAGS) -C $$i distclean ; fi done

realclean: distclean


depend:
	@for i in $(SUBDIRS) ; do if [ -d $$i ] && [ -f $$i/Makefile ] ; then $(MAKE) $(MFLAGS) -C $$i depend ; fi done

install:
	( for i in $(PROGS) ; do rm -f $(PREFIX)/bin/$$i ; done )
ifneq ($(PYTHON2.6), /none)
	$(PYTHON2.6) ./setup.py install --prefix=$(PREFIX) 
endif
ifneq ($(PYTHON2.7), /none)
	$(PYTHON2.7) ./setup.py install --prefix=$(PREFIX) 
endif
ifneq ($(PYTHON3), /none)
	$(PYTHON3) ./setup.py install --prefix=$(PREFIX) 
endif
ifneq ($(DEFAULTPY), /none)
	$(DEFAULTPY) ./setup.py install --prefix=$(PREFIX) 
	$(DEFAULTPY) ./setup.py install_data # --prefix=$(PREFIX) 
endif


	#	$(INSTALL) -d $(DCINSTDIR)
	#rm -f $(PREFIX)/limatix
	#ln -s $(DCINSTDIR) $(PREFIX)/limatix
	#$(INSTALL) -d $(DCINSTDIR)/lib
	#$(INSTALL) -d $(DCINSTDIR)/conf
	#$(INSTALL) -d $(DCINSTDIR)/doc
	#$(INSTALL) -d $(DCINSTDIR)/bin
	#@for i in $(PYSUBDIRS) ; do if [ -d $$i ] ; then $(INSTALL) -d $(DCINSTDIR)/$$i/ ; echo $$i/*.py $$i/*.glade ; $(INSTALL) $$i/*.py $$i/*.glade $(DCINSTDIR)/$$i/; fi done
	#@for i in $(CHXSUBDIRS) ; do if [ -d $$i ] ; then $(INSTALL) -d $(DCINSTDIR)/$$i/ ; echo $$i/*.chx ; $(INSTALL) $$i/*.chx $(DCINSTDIR)/$$i/ ; $(INSTALL) $$i/*.png $(DCINSTDIR)/$$i/ ; fi done	
	#$(INSTALL) -d $(DCINSTDIR)/glade-3
	#$(INSTALL) glade-3/*.txt $(DCINSTDIR)/glade-3/
	#$(INSTALL) -d $(DCINSTDIR)/glade-3/glade_catalogs
	#$(INSTALL) glade-3/glade_catalogs/* $(DCINSTDIR)/glade-3/glade_catalogs/
	#$(INSTALL) -d $(DCINSTDIR)/glade-3/glade_modules
	#$(INSTALL) glade-3/glade_modules/* $(DCINSTDIR)/glade-3/glade_modules/
	#$(INSTALL) README.txt $(DCINSTDIR)/
	#$(INSTALL) lib/*.glade $(DCINSTDIR)/lib
	#$(INSTALL) lib/*.py $(DCINSTDIR)/lib
	#$(INSTALL) conf/*.glade $(DCINSTDIR)/conf
	#$(INSTALL) conf/*.dcc $(DCINSTDIR)/conf
	#$(INSTALL) doc/* $(DCINSTDIR)/doc
	#( for i in $(PROGS) ; do $(INSTALL) bin/$$i $(DCINSTDIR)/bin/ ; done )
	#( for i in $(PROGS) ; do rm -f $(PREFIX)/bin/$$i ; ln -s $(DCINSTDIR)/bin/$$i $(PREFIX)/bin/$$i ; done )



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

	tar -cvzf /tmp/realclean-limatix-`cat VERSION`.tar.gz $(DIST_FILES)

	tar $(PUBEXCLUDE) -cvzf /tmp/realclean-limatix-pub-`cat VERSION`.tar.gz $(DIST_FILES)

	@for archive in  limatix-`cat VERSION` limatix-pub-`cat VERSION`  ; do mkdir /tmp/$$archive ; tar -C /tmp/$$archive  -x -f /tmp/realclean-$$archive.tar.gz ; make -C /tmp/$$archive all ; make -C /tmp/$$archive distclean ; tar -C /tmp -c -v -z -f /home/sdh4/research/software/archives/$$archive.tar.gz $$archive ; done

	mv VERSION VERSIONtmp
	awk -F . '{ print $$1 "." $$2 "." $$3+1 "-devel"}' <VERSIONtmp >VERSION  # increment version number and add trailing-devel
	rm -f VERSIONtmp
	rm -f VERSIONDATE
