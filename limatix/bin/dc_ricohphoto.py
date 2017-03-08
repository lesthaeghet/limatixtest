#! /usr/bin/env python

import sys
import os
import os.path
import string
import datetime

if "--gtk3" in sys.argv or sys.version_info[0] >= 3:  # gtk3
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk as gtk
    pass
else :  # gtk2
    import gobject
    import gtk
    pass

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
#
#sys.path.append(installeddir)
#sys.path.append(os.path.join(installeddir,"lib/"))

from limatix.dc_value import numericunitsvalue as numericunitsv
from limatix.dc_value import stringvalue as stringv
from limatix.dc_value import photosvalue as photosv

from limatix import paramdb2 as pdb

from limatix.dc_gtksupp import import_widgets
from limatix.dc_gtksupp import guistate as create_guistate

from limatix.dc_dbus_barcode import dc_dbus_barcode


from limatix import ricohcamera

if "gobject" in sys.modules:  # only for GTK2
    gobject.threads_init()
    pass

import_widgets()


def newsdbdest(param,condition):
    # set parameters if in specimendatabase mode
    paramdb=param.parent 
    paramdb["dest"].requestvalstr_sync("specimens/%s_files/" % (str(paramdb["specimen"].dcvalue)))
    
    pass

def newfilename(param,condition):
    # set parameters if in specimendatabase mode
    paramdb=param.parent
    paramdb["reqfilename"].requestvalstr_sync("%s_%s_.jpg" % (str(paramdb["specimen"].dcvalue),str(paramdb["date"].dcvalue)))
    pass


def closehandler(widget,event):
    # called with close box
    
    sys.exit(0)
    
    return False

def main(args=None):
    if args is None:
        args=sys.argv
        pass
    
    global paramdb 
    paramdb=pdb.paramdb(None)
    
    paramdb.addparam("specimen",stringv)
    paramdb.addparam("perfby",stringv)
    paramdb.addparam("date",stringv)
    paramdb.addparam("dest",stringv)
    paramdb.addparam("reqfilename",stringv)
    
    # auto-set date 
    if paramdb["date"].dcvalue.isblank():
        curdate=datetime.datetime.now()
        paramdb["date"].requestvalstr_sync(curdate.isoformat().split("T")[0])
        pass
    
    

    # command line parameters
    argc=1
    
    mode="default"

    while argc < len(args):
        if args[argc]=="-sdb":
            # specimen database mode
            mode="specimendatabase"
            pass
        elif args[argc]=="-s":
            # Set specimen
            argc+=1
            paramdb["specimen"].requestvalstr_sync(args[argc])
            
            pass
        elif args[argc]=="-h" or args[argc]=="--help":
            # print usage: 
            print("Usage: ricohphoto [-sdb] [-s <specimen>] [--gtk3]")
            print(" ")
            print(" -sdb enables specimen database mode")
            
            pass 
        elif args[argc]=="--gtk3":
            pass # handled above, with imports
        elif args[argc][0]=="-":
            raise ValueError("Unknown argument: %s" % (args[argc]))
        
        argc+=1
        pass
    
    
    # Automatically create/update dest and filename fields
    if mode=="specimendatabase":
        paramdb.addnotify("specimen",newsdbdest,pdb.param.NOTIFY_NEWVALUE)    
        #newsdbdest(None, None)
        paramdb["dest"].requestvalstr_sync("specimens/%s_files/" % (str(paramdb["specimen"].dcvalue)))
        pass
    else :
        paramdb["dest"].requestvalstr_sync(os.getcwd()) 
        
        pass
    
    paramdb.addnotify("specimen",newfilename,pdb.param.NOTIFY_NEWVALUE)
    paramdb.addnotify("date",newfilename,pdb.param.NOTIFY_NEWVALUE)
    #newfilename(None,None)
    paramdb["reqfilename"].requestvalstr_sync("%s_%s_.jpg" % (str(paramdb["specimen"].dcvalue),str(paramdb["date"].dcvalue)))
    



    guistate=create_guistate(None,paramdb) # can add search directories as additional parameters here [os.path.split(fname)[0]])

    # Connect to dbus (barcode reader)
    dbuslink=dc_dbus_barcode(paramdb)


    ricohwindow=ricohcamera.ricohphotorequest(paramdb,None,gladefile="ricohphoto.glade")
    ricohwindow.connect("delete-event",closehandler)
    
    
    ricohwindow.dc_gui_init(guistate)



    ricohwindow.show_all()



    gtk.main()
	
    pass
