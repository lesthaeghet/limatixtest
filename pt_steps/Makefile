
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
	## Install of pt_steps is handled by setup.py in parent directory 
	#$(INSTALL) -d $(DCINSTDIR)/pt_steps
	#$(INSTALL) *.py $(DCINSTDIR)/pt_steps # uncomment once we actually have installable steps


