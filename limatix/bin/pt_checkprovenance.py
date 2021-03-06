#! /usr/bin/env python
from __future__ import print_function

import sys

import os
import os.path
import socket
import copy
import inspect
import numbers
import traceback


#import cProfile

#if "--gtk3" in sys.argv or sys.version_info[0] >= 3:  # gtk3
#    from gi.repository import Gtk as gtk
#    pass
#else :  # gtk2
#    import gobject
#    import gtk
#    pass

import shutil
import datetime

from limatix import lm_units
lm_units.units_config("insert_basic_units")

#class dummy(object):
#    pass

## trace symbolic link to find installed directory
#thisfile=sys.modules[dummy.__module__].__file__
#if os.path.islink(thisfile):
#    installedfile=os.readlink(thisfile)
#    if not os.path.isabs(installedfile):
#        installedfile=os.path.join(os.path.dirname(thisfile),installedfile)
#        pass
#    pass
#else:
#    installedfile=thisfile
#    pass

#installeddir=os.path.dirname(installedfile)

#if os.path.exists(os.path.join(installeddir,"../lib/checklist.py")):
#    installeddir=os.path.join(installeddir,"../")
#    pass
#elif os.path.exists(os.path.join(installeddir,"../gui2/lib/checklist.py")):
#    installeddir=os.path.join(installeddir,"../gui2")
#    pass

#sys.path.append(installeddir)
#sys.path.append(os.path.join(installeddir,"lib/"))

import limatix.dc_value as dcv
import limatix.provenance as provenance
from limatix import xmldoc

def usage():
    print ("""Usage: %s file.xlp
      
Flags:
    -h,--help:      This help
    -v:             Verbose output (list contents of errors)
    """ % (sys.argv[0]))
    pass


def main(args=None):
    if args is None:
        args=sys.argv
        pass
    
    argc=1
    positionals=[]
    verbose=False

    while argc < len(args):
        arg=args[argc]
        if arg=="-h" or arg=="--help":
            usage()
            sys.exit(0)
            pass
        elif arg=="-v":
            verbose=True
            pass
        else: 
            positionals.append(arg)
            pass
        argc+=1
        pass

        
    if len(positionals) > 1:
        raise ValueError("Too many positional parameters (see -h for command line help")

    if len(positionals) < 1: 
        usage()
        sys.exit(0)
        pass
    
    xlpfile=positionals[0]
    xlp=xmldoc.xmldoc.loadfile(xlpfile,use_locking=True)
    xlp.disable_locking()  # locking is just to prevent messing with the file during
    # our initial read
    
    # For profiling
    #cProfile.run("(docdict,processdict,processdictbypath,processdictbyusedelement,elementdict,globalmessagelists,totalmessagelists)=provenance.checkallprovenance(xlp)")

    (docdict,processdict,processdictbypath,processdictbyusedelement,elementdict,globalmessagelists,totalmessagelists)=provenance.checkallprovenance(xlp)

    suggestions=provenance.suggest(docdict,processdict,processdictbypath,processdictbyusedelement,elementdict,globalmessagelists,totalmessagelists)


    print("\nProvenance summary:\n   %d errors, %d warnings, %d info, %d additional, %d suggestions" % (len(totalmessagelists["error"]),len(totalmessagelists["warning"]),len(totalmessagelists["info"]),len(totalmessagelists["none"]),len(suggestions)))
    if verbose:
        print("\n\nErrors")
        print("------")
        for message in totalmessagelists["error"]:
            print(message)
            pass
        
        print("\n\nWarnings")
        print("--------")
        for message in totalmessagelists["warning"]:
            print(message)
            pass
        
        print("\n\nInformational")
        print("--------------")
        for message in totalmessagelists["info"]:
            print(message)
            pass
        
        print("\n\nAdditional")
        print("-----------")
        for message in totalmessagelists["none"]:
            print(message)
            pass
        print("")

        pass

    print("\nSuggestions")
    print("------------")
    for (suggestiontext,suggestioncommand) in suggestions:
        print("%s\n   %s\n" % (suggestiontext,suggestioncommand))
        pass
    print("")


    pass
