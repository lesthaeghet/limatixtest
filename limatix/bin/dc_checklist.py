#! /usr/bin/env python

import sys
import os
import os.path
import posixpath
import string
import datetime
import traceback

try:
    # py2.x
    from urllib import pathname2url
    from urllib import url2pathname
    from urllib import quote
    from urllib import unquote
    pass
except ImportError:
    # py3.x
    from urllib.request import pathname2url
    from urllib.request import url2pathname
    from urllib.parse import quote
    from urllib.parse import unquote
    pass


if "--gtk3" in sys.argv or sys.version_info[0] >= 3:  # gtk3
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk as gtk
    from gi.repository import GObject as gobject
    
    pass
else :  # gtk2
    import gobject
    import gtk
    pass

from limatix import lm_units
lm_units.units_config("insert_basic_units")


class dummy(object):
    pass

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
#sys.path.append(os.path.join(installeddir,"steps/"))


from limatix.dc_value import numericunitsvalue as numericunitsv
from limatix.dc_value import stringvalue as stringv
from limatix.dc_value import datesetvalue as datesetv
from limatix.dc_value import accumulatingdatesetvalue as accumulatingdatesetv
from limatix.dc_dbus_barcode import dc_dbus_barcode

from limatix import checklist
from limatix import xmldoc

dg_io=None
try:
    import dg_io
    pass
except ImportError:
    pass

from limatix import dc_value
from limatix import paramdb2 as pdb
from limatix import dc2_misc
from limatix import standalone_checklist

from limatix.dc_gtksupp import build_from_file
from limatix.dc_gtksupp import dc_initialize_widgets
from limatix.dc_gtksupp import import_widgets
from limatix.dc_gtksupp import guistate as create_guistate

# from steptemplate import steptemplate

# magic imports required for any object types to be instantiated by gtk.builder
# replace by call to import_widgets
#from dataguzzler_readout import dg_readout
#from dataguzzler_setparam import dg_setparam
#from dataguzzler_commandbutton import dg_commandbutton

if "gobject" in sys.modules:  # only for GTK2
    gobject.threads_init()
    pass
    
import_widgets()

def createparamserver():
    # dummy, as dg_checklist does not support parameter serving
    pass


def main(args=None):
    if args is None:
        args=sys.argv
        pass
    
    fname=None
    argc=1
    date=None
    connect_dg=False
    configfiles=[]   # note... this list is accessed from runcheckliststep so that the same config files can be passed to the sub-checklist

    while argc < len(args):
        arg=args[argc]
        
        if arg=="-d":
            connect_dg=True
            pass
        elif arg=="--date":
            argc+=1
            date=args[argc]
            pass
        
        elif arg=="-f":
            argc+=1
            configfiles.append(args[argc])
            pass
        elif arg=="--gtk3":
            # arg handled with imports, above
            pass
        elif arg=='-h' or arg=="--help":
            print("""Usage: %s [-f <config.dcc>] [--date 201x-xx-xx] [-d] checklist.chx (or plan.plx)...
            
Flags:
  -f config.dcc       Load datacollect config
  -d                  Connect to dataguzzler
  --gtk3              Use gtk3 instead of gtk2
""" % (args[0]))
            sys.exit(0)
            pass
        elif arg[0]=='-':
            raise ValueError("Unknown command line switch %s" % (arg))
        else :
            fname=arg
            pass
        argc+=1
        pass
    
    if fname is None:
        sys.stderr.write("Must provide at least one positional parameter. -h for help\n")
        sys.exit(1)
        pass
        
    iohandlers={}  #=dg_io.io()
    if connect_dg:
        if dg_io is not None:
            dg_io.addhandler(iohandlers)
            pass
        else:
            sys.stderr.write("dc_checklist: dg_io not available (ImportError)\n")
            pass
        pass
    
    paramdb=pdb.paramdb(iohandlers)
    
    # define parameters
    # paramdb.addparam("clinfo",stringv,build=lambda param: xmldoc.synced(param))  # clinfo auto-added to checklist-private paramdb
    paramdb.addparam("specimen",stringv,build=lambda param: xmldoc.synced(param))
    paramdb.addparam("perfby",stringv,build=lambda param: xmldoc.synced(param))
    #paramdb.addparam("date",stringv,build=lambda param: xmldoc.synced(param))
    #paramdb.addparam("date",datesetv,build=lambda param: xmldoc.synced_accumulating_dates(param))
    paramdb.addparam("date",accumulatingdatesetv,build=lambda param: xmldoc.synced(param))
    # paramdb.addparam("dest",stringv,build=lambda param: xmldoc.synced(param)) # clinfo auto-added to checklist-private paramdb
    paramdb.addparam("notes",stringv,build=lambda param: xmldoc.synced(param))
    
    # FIXES: 
    #  * Some of above parameters could be capable of syncing with dataguzzler, BUT
    #  * If they are, when you load a completed checklist, it may load the new parameters in (!)
    #  * Which may not be what you expect or want, especially if it is someone else who is running
    #    dataguzzler on that computer. 
    #  * So if this change is made, should require an explicit command line argument in order to 
    #    connect to dataguzzler. 
    
    # auto-set date 
    if date is not None:
        paramdb["date"].requestvalstr_sync(date)
        pass
    elif paramdb["date"].dcvalue.isblank():
        curdate=datetime.date.today()
        paramdb["date"].requestvalstr_sync(curdate.isoformat())
        pass
    



    for configfile in configfiles:
        dc2_misc.load_config(configfile,paramdb,iohandlers,createparamserver)
        #configfh=file(configfile)
        #configstr=configfh.read()
        #exec(configstr,globals(),{"paramdb":paramdb,"dgio":iohandler,"createparamserver":createparamserver})
        #configfh.close()
        pass
    
    
    
    # Connect to dbus (barcode reader)
    dbuslink=dc_dbus_barcode(paramdb)
    
    
    # create context from fname and directory
    (direc,filename)=os.path.split(fname)

    if direc=="":
        direc="."
        pass
    filehref=dc_value.hrefvalue(pathname2url(fname),contexthref=dc_value.hrefvalue(pathname2url(direc)+posixpath.sep,contexthref=dc_value.hrefvalue("./")))
    
    try: 
        standalone_checklist.open_checklist(filehref,paramdb,iohandlers)
        pass
    except:
        (exctype,excvalue)=sys.exc_info()[:2]
        sys.stderr.write("%s opening checklist: %s\n" % (exctype.__name__,str(excvalue)))
        traceback.print_exc()
        import pdb as pythondb
        pythondb.post_mortem()
        pass
 
    gtk.main()
    pass
