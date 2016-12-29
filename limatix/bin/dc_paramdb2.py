#! /usr/bin/env python

import sys
import os
import os.path
import string
import datetime
import socket
import subprocess


if "--gtk3" in sys.argv or sys.version_info[0] >= 3:  # gtk3
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk as gtk
    pass
else :  # gtk2
    import gobject
    import gtk
    pass

if hasattr(gtk,"ResponseType") and hasattr(gtk.ResponseType,"OK"):
    # gtk3
    RESPONSE_OK=gtk.ResponseType.OK
    RESPONSE_CANCEL=gtk.ResponseType.CANCEL
    RESPONSE_NO=gtk.ResponseType.NO
    RESPONSE_YES=gtk.ResponseType.YES
else :
    RESPONSE_OK=gtk.RESPONSE_OK
    RESPONSE_CANCEL=gtk.RESPONSE_CANCEL
    RESPONSE_NO=gtk.RESPONSE_NO
    RESPONSE_YES=gtk.RESPONSE_YES
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
#
#if os.path.exists(os.path.join(installeddir,"../lib/checklist.py")):
#    installeddir=os.path.join(installeddir,"../")
#    pass
#elif os.path.exists(os.path.join(installeddir,"../gui2/lib/checklist.py")):
#    installeddir=os.path.join(installeddir,"../gui2")
#    pass

#sys.path.append(installeddir)
#sys.path.append(os.path.join(installeddir,"lib/"))

from limatix.dc_value import numericunitsvalue as numericunitsv
from limatix.dc_value import stringvalue as stringv
from limatix.dc_value import photosvalue as photosv

from limatix.dc_dbus_barcode import dc_dbus_barcode

#import dg_io 
from limatix import paramdb2 as pdb
from limatix import paramdb2_editor
from limatix import dc2_misc
from limatix import paramdbfile

from limatix.dc_gtksupp import build_from_file
from limatix.dc_gtksupp import dc_initialize_widgets
from limatix.dc_gtksupp import import_widgets
from limatix.dc_gtksupp import guistate as create_guistate

from limatix.dc_dbus_paramserver import dc_dbus_paramserver


def createparamserver():
    global paramserver
    if paramserver is None:
        paramserver=dc_dbus_paramserver(paramdb,None)
        pass
    pass


def open_gui(fname):
    (gladeobjdict,builder)=build_from_file(fname)
    dc_initialize_widgets(gladeobjdict,guistate)
    
    
    win=gladeobjdict["guiwindow"]

    win.set_title(os.path.split(fname)[1])
    gui=(gladeobjdict,builder,win)
    guiwins.append(gui)
    
    # win.connect("delete-event",self.handle_gui_close,gui)
    win.show_all()
    

    
    pass

def handle_gui_close(*args):
    sys.exit(0)
    pass

def handle_savedpd(event,paramdb,guis,configfiles):
    if hasattr(gtk,"FileChooserAction") and hasattr(gtk.FileChooserAction,"OPEN"):
        # gtk3
        saveparamschooser=gtk.FileChooserDialog(title="Save parameters",action=gtk.FileChooserAction.SAVE,buttons=(gtk.STOCK_CANCEL,gtk.ResponseType.CANCEL,gtk.STOCK_SAVE,gtk.ResponseType.OK))
        pass
    else : 
        saveparamschooser=gtk.FileChooserDialog(title="Save parameters",action=gtk.FILE_CHOOSER_ACTION_SAVE,buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_SAVE,gtk.RESPONSE_OK))
        pass
    #saveparamschooser.set_current_folder(os.path.abspath(os.path.join(thisdir, '..', 'conf')))
    dpdfilter=gtk.FileFilter()
    dpdfilter.set_name("Datacollect parameter database (*.dpd) files")
    dpdfilter.add_pattern("*.dpd")
    saveparamschooser.add_filter(dpdfilter)
    
    checkboxvbox=gtk.VBox()
    
    nonsettablecheckbox=gtk.CheckButton("Include non-settable fields")
    checkboxvbox.pack_start(nonsettablecheckbox)
        
    dcccheckbox=gtk.CheckButton("Include dcc files")
    dcccheckbox.set_active(True)
    checkboxvbox.pack_start(dcccheckbox)

    guicheckbox=gtk.CheckButton("Include guis")
    guicheckbox.set_active(True)
    checkboxvbox.pack_start(guicheckbox)


    saveparamschooser.set_extra_widget(checkboxvbox)
    
    checkboxvbox.show_all()
    #saveparamschooser.add_button("FooButton",5)
    
    result=saveparamschooser.run()
    fname=saveparamschooser.get_filename()
    saveparamschooser.destroy()
    
    if result==RESPONSE_OK:
            
        # load config file here...
        # imp.load_source("datacollect_config",fname)
        paramdbfile.save_params(configfiles, guis,paramdb,fname,None,None,non_settable=nonsettablecheckbox.get_active(),dcc=dcccheckbox.get_active(),gui=guicheckbox.get_active(),chx=False,xlg=False)
            

        
        pass
    
    pass



def main(args=None):
    if args is None:
        args=sys.argv
        pass
    positionals=[]
    guis=[]
    configfiles=[]
    explogfile=None
    appendlog=False
    dpdfiles=[]
    paramupdates=[]
    
    argc=1

    while argc < len(args):
        arg=args[argc]
        
        if arg=="-f":
            argc+=1
            configfiles.append(args[argc])
            pass
        elif arg=="-g":
            argc+=1
            guis.append(args[argc])
            pass
        elif arg=="-d":
            argc+=1
            dpdfiles.append(args[argc])
            pass
        elif arg=='-h' or arg=="--help":
            print("""Usage: %s [--gtk3] [-f <config.dcc>]  [-g gui.glade] ...
        
Flags:
  -f <config.dcc>     Open this config file (multiple OK)
  -g <gui.glade>      Open this gui (multiple OK)
  -d <params.dpd>     Load parameters from this .dpd file (multiple OK)
""" % (args[0]))
            sys.exit(0)
            pass
        elif arg=="--gtk3":
            pass  # handled at import stage, above
        elif arg[0]=='-':
            raise ValueError("Unknown command line switch %s" % (arg))
        else :
            positionals.append(arg)
            pass
        argc+=1
        pass
    
    if len(positionals) > 0:
        raise ValueError("Too many positional parameters (see -h for command line help")



    if "gobject" in sys.modules:  # only for GTK2
        gobject.threads_init()
        pass
    
    import_widgets()
    
    
    
    iohandlers={}  #=dg_io.io()

    paramdb=pdb.paramdb(iohandlers)
    
    
    # define universal parameters
    
    # parameters that are supposed to go in the summary need to have an adddoc() call in explogwindow.syncexplog
    #  and a corresponding remdoc call in explogwindow.unsyncexplog
    
    paramdb.addparam("hostname",stringv)
    paramdb.addparam("specimen",stringv)
    paramdb.addparam("perfby",stringv)
    paramdb.addparam("date",stringv)
    
    paramdb.addparam("notes",stringv) 
    

    # auto-set date 
    if paramdb["date"].dcvalue.isblank():
        curdate=datetime.datetime.now()
        paramdb["date"].requestvalstr_sync(curdate.isoformat().split("T")[0])
        pass
    # print str(paramdb["date"].dcvalue)
    
    dc2_misc.set_hostname(paramdb)

    # Connect to dbus (barcode reader)
    dbuslink=dc_dbus_barcode(paramdb)
    

    ## Create dbus paramserver
    #paramserver=dc_dbus_paramserver(paramdb,explogwin.checklists)
    # paramserver is now created within createparamserver() on demand by the dcc file and stored as a member of explogwin
    paramserver=None

    
    guistate=create_guistate(iohandlers,paramdb) # can add search directories as additional parameters here [os.path.split(fname)[0]])

    
    for dpdfile in dpdfiles: 
        (dpdconfigfiles,dpdguis,dpdchxfiles,dpdplans,dpdexplog,dpdparamupdates,dpdSingleSpecimen)=paramdbfile.load_params(dpdfile)
        configfiles.extend(dpdconfigfiles)
        guis.extend(dpdguis)
        #checklists.extend(dpdchxfiles)
        #plans.extend(dpdplans)
        paramupdates.append(dpdparamupdates)
        
        
        for configfile in configfiles: 
            dc2_misc.load_config(configfile,paramdb,iohandlers,createparamserver)
            pass
        
        pass
        
    dpdlog=[]
    for paramupdate in paramupdates:
        dpdlog.extend(paramdbfile.apply_paramdb_updates(paramupdate,paramdb))
        pass

    for (paramname,status,val1,val2) in dpdlog:
        if status=="dangerous":
            sys.stderr.write("Warning loading %s: Dangerous parameter %s ignored\n" % (dpdfile,paramname))
            pass
        elif status=="mismatch":
            sys.stderr.write("Warning loading %s: Parameter %s request mismatch (requested: %s; actual: %s)\n" % (dpdfile,paramname,str(val1),str(val2)))
            pass
        elif status=="error":
            sys.stderr.write("Warning loading %s: Parameter %s request error (requested: %s)\n" % (dpdfile,paramname,str(val1)))
            pass
        elif status!="match":
            raise ValueError("Unknown status message loading paramdb from %s" % (dpdfile))
    
        pass
    
    guiwins=[]
    
    
    for gui in guis:
        open_gui(gui)
        pass
    

    # open paramdb2 editor
    editor=paramdb2_editor.paramdb2_editor(paramdb)
    editor.connect("delete-event",handle_gui_close)
    
    MenuBar=gtk.MenuBar()
    
    FileMenuItem=gtk.MenuItem("File")
    MenuBar.append(FileMenuItem)
    FileMenu=gtk.Menu()
    FileMenuItem.set_submenu(FileMenu)
    SaveDPDMenuItem=gtk.MenuItem("Save params...")
    SaveDPDMenuItem.connect("activate",handle_savedpd,paramdb,guis,configfiles)
    FileMenu.append(SaveDPDMenuItem)
    editor.vbox.pack_start(MenuBar,expand=False,fill=True)
    editor.vbox.reorder_child(MenuBar,0)
    MenuBar.show_all()
    
    gtk.main()

    pass
