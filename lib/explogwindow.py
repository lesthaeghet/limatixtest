import subprocess
import os
import os.path
import sys
import string
import copy
import json
import urllib
import pdb as pythondb

import paramdbfile

if hasattr(string,"maketrans"):
    maketrans=string.maketrans
    pass
else:
    maketrans=str.maketrans
    pass


import traceback
# import imp
if not "gtk" in sys.modules:  # gtk3
    from gi.repository import Gtk as gtk
    from gi.repository import GObject as gobject
    from gi.repository import Gdk as gdk
    DELETE=None  # can't figure out what the event structure is supposed to contain, but None works OK.
    pass
else : 
    # gtk2
    import gobject
    import gtk
    import gtk.gdk as gdk
    DELETE=gdk.DELETE
    pass
import xml.sax.saxutils

from dc_gtksupp import build_from_file
from dc_gtksupp import dc_initialize_widgets
from dc_dbus_paramserver import dc_dbus_paramserver

import canonicalize_path

import paramdb2 as pdb
import checklist
import dc2_misc

import xmldoc
import dc_value as dcv
import xmlexplog
import paramdb2_editor
import checklistdb
import checklistdbwin

import ricohcamera


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

__pychecker__="no-argsused no-import"


class dummy(object):
    pass
thisdir=os.path.split(sys.modules[dummy.__module__].__file__)[0]


class explogwindow(gtk.Window):
    gladefile=None
    paramdb=None
    SingleSpecimen=None
    # autoflush=None
    # autoresync=None

    explog=None

    gladeobjdict=None
    builder=None
    dc_gui_io=None
    about_dialog=None
    guistate=None

    experiment=None  # Current experiment window
    checklists=None  # list of checklists and plans currently open
    guis=None  # list of guis currently open. Each is a tuple (gladeobjdict,builder,win)

    checklistdbwin=None # checklistdbwin object for browsing checklists in the experiment log

    paramserver=None  # dc_dbus_paramserver.dc_dbus_paramserver object

    configfnames=None # list of loaded config files
    configstr=None # archive of the config file as we read it .

    dest=None # destination directory for dgs, settings, chf files, etc. 


    checklistmenushortcuts=None # dictionary of menuitems, added as shortcuts to the checklist menu, indexed by file name
    checklistmenuorigentries=None # original count of glade menu entries
    
    checklistmenurealtimeentries=None

    def __init__(self,gladefile,paramdb,SingleSpecimen):
        gobject.GObject.__init__(self)

        self.gladefile=gladefile
        self.paramdb=paramdb
        self.SingleSpecimen=SingleSpecimen
        # self.autoflush=True
        # self.autoresync=True

        self.configfnames=[]
        self.configstr=""
        self.guis=[]
        self.checklistmenushortcuts={}

        self.explog=xmlexplog.explog(None,self.dc_gui_io,self.paramdb,use_locking=True,debug=False) # ,autoflush=self.autoflush,autoresync=self.autoresync)
        try: 
            self.syncexplog()
            pass
        finally:
            self.explog.unlock_rw() # free-up automatic log on open
            pass

        (self.gladeobjdict,self.builder)=build_from_file(self.gladefile)
        self.checklistmenuorigentries=len(self.gladeobjdict["explogchecklistmenu"].get_children())

        # Add reset specimen button or specimen textentry, depending 
        # on whether we are in single specimen mode

        if SingleSpecimen:
            SpecimenWidget=self.gladeobjdict["SpecBox"]
            pass
        else :
            SpecimenWidget=self.gladeobjdict["ResetSpecimenButton"]
            pass
        self.gladeobjdict["ParamBox"].pack_start(SpecimenWidget,True,True,0)
        self.gladeobjdict["ParamBox"].reorder_child(SpecimenWidget,1)
        
        self.add(self.gladeobjdict["explog"])

        self.about_dialog=self.gladeobjdict["aboutdialog"]


        self.experiment=None
        self.checklists=[]
        

        # disable opening gui
        # self.gladeobjdict["explogguiopen"].set_sensitive(False)
        self.gladeobjdict["explogchecklistopen"].set_sensitive(False)

        # disable file picking until config loaded
        self.gladeobjdict["explogfilenew"].set_sensitive(False)
        self.gladeobjdict["explogfileopen"].set_sensitive(False)

        
        

        # self.builder.connect_signals(self)
        self.gladeobjdict["explogfilenew"].connect("activate",self.choose_newexplog)
        self.gladeobjdict["explogfileopen"].connect("activate",self.choose_openexplog)
        self.gladeobjdict["explogfileloadconfig"].connect("activate",self.choose_loadconfig)
        self.gladeobjdict["explogfilesaveparams"].connect("activate",self.choose_saveparams)
        self.gladeobjdict["explogquit"].connect("activate",self.quit)
        self.connect("delete-event",self.closehandler)
        self.gladeobjdict["explogguiopen"].connect("activate",self.choose_opengui)
        self.gladeobjdict["explogguiopenparamdbeditor"].connect("activate",self.openparamdbeditor)
        self.gladeobjdict["explogguiexpphotograph"].connect("activate",self.expphotograph)
        self.gladeobjdict["explogguimeasphotograph"].connect("activate",self.measphotograph)
        self.gladeobjdict["explogchecklistopen"].connect("activate",self.choose_openchecklist)
        self.gladeobjdict["explogchecklists"].connect("activate",self.choose_openchecklists)

        self.gladeobjdict["explogplanopen"].connect("activate",self.choose_openplan)
        self.gladeobjdict["explogaboutmenu"].connect("activate",self.aboutdialog)
        self.gladeobjdict["aboutdialog"].connect("delete-event",self.hideaboutdialog)
        self.gladeobjdict["aboutdialog"].connect("response",self.hideaboutdialog)
        self.gladeobjdict["ResetSpecimenButton"].connect("clicked",self.reset_specimen)

        
        # request notifications when a new checklist is opened or reset, so we can rebuild our menu
        checklistdb.requestopennotify(self.rebuildchecklistrealtimemenu)
        checklistdb.requestresetnotify(self.rebuildchecklistrealtimemenu)
        checklistdb.requestclosenotify(self.rebuildchecklistrealtimemenu)

        self.assign_title()


        pass

    def reset_specimen(self,*args):
        sys.stderr.write("Got reset_specimen()\n")
        self.paramdb["specimen"].requestvalstr_sync("")
        
        return True

    def openparamdbeditor(self,*args):
        
        paramdb2_editor.paramdb2_editor(self.paramdb)
        
        pass

    def syncexplog(self):

        # pythondb.set_trace()
        dest=self.paramdb["dest"].dcvalue.value()
        if self.SingleSpecimen:
            self.paramdb["specimen"].controller.adddoc(self.explog,dest,"dc:summary/dc:specimen")
            pass

        # put selected parameters in the summary
        # don't forget to put parallel remdoc entries in unsyncexplog
        self.paramdb["perfby"].controller.adddoc(self.explog,dest,"dc:summary/dc:perfby")
        self.paramdb["date"].controller.adddoc(self.explog,dest,"dc:summary/dc:date")
        self.paramdb["expnotes"].controller.adddoc(self.explog,dest,"dc:summary/dc:expnotes")
        self.paramdb["goal"].controller.adddoc(self.explog,dest,"dc:summary/dc:goal")
        self.paramdb["reldest"].controller.adddoc(self.explog,dest,"dc:summary/dc:reldest")
        self.paramdb["expphotos"].controller.adddoc(self.explog,dest,"dc:summary/dc:expphotos")
        self.paramdb["hostname"].controller.adddoc(self.explog,dest,"dc:summary/dc:hostname")
        self.paramdb["measnum"].controller.adddoc(self.explog,dest,"dc:summary/dc:measnum")
        self.paramdb["checklists"].controller.adddoc(self.explog,dest,"dc:summary/dc:checklists")
        self.paramdb["plans"].controller.adddoc(self.explog,dest,"dc:summary/dc:plans")

        if self.explog.filename is not None:
            # Re-register checklists and plans with checklistdb, with contextdir set
            checklistdb.register_paramdb(self.paramdb,"checklists",os.path.split(self.explog.filename)[0],False)
            checklistdb.register_paramdb(self.paramdb,"plans",os.path.split(self.explog.filename)[0],True)
            pass
        pass

    def unsyncexplog(self,ignoreerror=False):
        try : 
            dest=self.paramdb["dest"].dcvalue.value()

            if self.SingleSpecimen:
                self.paramdb["specimen"].controller.remdoc(self.explog,dest,"dc:summary/dc:specimen")
                pass
            
            self.paramdb["perfby"].controller.remdoc(self.explog,dest,"dc:summary/dc:perfby")
            self.paramdb["date"].controller.remdoc(self.explog,dest,"dc:summary/dc:date")
            self.paramdb["expnotes"].controller.remdoc(self.explog,dest,"dc:summary/dc:expnotes")
            self.paramdb["goal"].controller.remdoc(self.explog,dest,"dc:summary/dc:goal")
            self.paramdb["reldest"].controller.remdoc(self.explog,dest,"dc:summary/dc:reldest")
            self.paramdb["expphotos"].controller.remdoc(self.explog,dest,"dc:summary/dc:expphotos")
            self.paramdb["hostname"].controller.remdoc(self.explog,dest,"dc:summary/dc:hostname")
            self.paramdb["measnum"].controller.remdoc(self.explog,dest,"dc:summary/dc:measnum")
            self.paramdb["checklists"].controller.remdoc(self.explog,dest,"dc:summary/dc:checklists")
            self.paramdb["plans"].controller.remdoc(self.explog,dest,"dc:summary/dc:plans")

            pass
        except:
            if not ignoreerror:
                raise
            pass
        pass
    
    

    def assign_title(self):
        if self.explog.filename is None:
            self.set_title("Experiment log (no file)")
            pass
        else:
            self.set_title(os.path.split(self.explog.filename)[-1])
            pass
        
        pass
    
    def dc_gui_init(self,guistate):
        # need next line if subclassing a dc_gui class
        # super(dc_readout).__dc_gui_init(self,guistate)
        
        self.guistate=guistate
        
        self.dc_gui_io=guistate.io
        self.explog.set_dgio(self.dc_gui_io)
        
        dc_initialize_widgets(self.gladeobjdict,guistate)
        
        pass


    def suggestname(self):
        suggestion=""
        
        goaltext=self.gladeobjdict["goalentry"].textview.get_buffer().get_property("text")
        goaltranstab=maketrans("\r\n ,:/.#@$%^&*()[]{}\|;\'\"<>?`~\t","\n\n"+("_"*29))
        translated=goaltext.translate(goaltranstab)
        suggestion=translated.split("\n")[0]

        
        if self.SingleSpecimen and not self.paramdb["specimen"].dcvalue.isblank() :
            if len(suggestion) > 0:
                suggestion += "_"
                pass
            suggestion+=str(self.paramdb["specimen"].dcvalue)
            pass

        if not self.paramdb["date"].dcvalue.isblank():
            if (len(suggestion) > 0):
                suggestion+= "_"
                pass
            suggestion+=str(self.paramdb["date"].dcvalue)
            pass
        suggestion+=".xlg"
        
            
        return suggestion

    def set_dest(self):
        (direc,fname)=os.path.split(self.explog.filename)
        (fbase,ext)=os.path.splitext(fname)

        self.paramdb["reldest"].requestvalstr_sync(fbase+"_files")
        self.paramdb["dest"].requestvalstr_sync(os.path.join(direc,fbase+"_files"))
        if not os.path.exists(str(self.paramdb["dest"].dcvalue)):
            os.mkdir(str(self.paramdb["dest"].dcvalue))
            pass
        
        pass

    def choose_newexplog(self,event):
        if hasattr(gtk,"FileChooserAction") and hasattr(gtk.FileChooserAction,"OPEN"):
            # gtk3
            newexplogchooser=gtk.FileChooserDialog(title="New experiment log",action=gtk.FileChooserAction.SAVE,buttons=(gtk.STOCK_CANCEL,gtk.ResponseType.CANCEL,gtk.STOCK_NEW,gtk.ResponseType.OK))
            pass
        else : 
            newexplogchooser=gtk.FileChooserDialog(title="New experiment log",action=gtk.FILE_CHOOSER_ACTION_SAVE,buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_NEW,gtk.RESPONSE_OK))
            pass

        newexplogchooser.set_current_name(self.suggestname())
        xlgfilter=gtk.FileFilter()
        xlgfilter.set_name("Experiment log files")
        xlgfilter.add_pattern("*.xlg")
        newexplogchooser.add_filter(xlgfilter)

        result=newexplogchooser.run()
        fname=newexplogchooser.get_filename()
        newexplogchooser.destroy()

        if result==RESPONSE_OK:
            self.new_explog(fname)
        
            pass
        
        pass

    def new_explog(self,fname,parentchecklistpath=None):
        # parentchecklistpath, if given, should be 
        # relative to the directory fname is in. 

        if (os.path.exists(fname)) :
            if hasattr(gtk,"MessageType") and hasattr(gtk.MessageType,"WARNING"):
                # gtk3
                existsdialog=gtk.MessageDialog(type=gtk.MessageType.ERROR,buttons=gtk.ButtonsType.OK)
                pass
            else : 
                existsdialog=gtk.MessageDialog(type=gtk.MESSAGE_ERROR,buttons=gtk.BUTTONS_OK)
                pass

            existsdialog.set_markup("Error: File %s exists.\nWill not overwrite\n(Try -a option if you want to append to an existing experiment log)" % (fname))
            existsdialog.run()
            existsdialog.destroy()
            return

        self.explog.setfilename(fname)
        # self.explog.shouldbeunlocked()

        self.unsyncexplog()  # need to restart synchronization once dest has changed

        self.set_dest()

        self.syncexplog()
        
        if self.explog.filename is not None:
            # Re-register checklists and plans with checklistdb, with contextdir set
            checklistdb.register_paramdb(self.paramdb,"checklists",os.path.split(self.explog.filename)[0],False)
            checklistdb.register_paramdb(self.paramdb,"plans",os.path.split(self.explog.filename)[0],True)
            pass


        
        self.paramdb["explogname"].requestvalstr_sync(os.path.split(fname)[-1])
        
        # self.explog.flush()
        
        # turn on experiment and checklist menu items 
        self.gladeobjdict["explogguiopen"].set_sensitive(True)
        self.gladeobjdict["explogchecklistopen"].set_sensitive(True)
        
        # turn off file new/open menu items
        self.gladeobjdict["explogfilenew"].set_sensitive(False)
        self.gladeobjdict["explogfileopen"].set_sensitive(False)

        # # turn off ability to load more config files
        # self.gladeobjdict["explogfileloadconfig"].set_sensitive(False)

        
        self.assign_title()
        
        # define parent, if given
        if parentchecklistpath is not None:
            self.explog.lock_rw()
            try:
                # for a new experiment log there should be no
                # existing dc:parent tag
                assert(len(self.explog.xpath("dc:parent"))==0)

                # create new dc:parent tag in root of explog
                parentel=self.explog.addelement(None,"dc:parent")
                # add xlink:href attribute
                self.explog.setattr(parentel,"xlink:href",urllib.pathname2url(parentchecklistpath))
                self.explog.setattr(parentel,"xlink:arcrole","http://thermal.cnde.iastate.edu/linktoparent")
                pass
            finally: 
                self.explog.unlock_rw()
                pass
            pass
        
        self.log_config()
        

        pass
    

    def choose_openexplog(self,event):
        if hasattr(gtk,"FileChooserAction") and hasattr(gtk.FileChooserAction,"OPEN"):
            # gtk3
            openexplogchooser=gtk.FileChooserDialog(title="Open experiment log",action=gtk.FileChooserAction.OPEN,buttons=(gtk.STOCK_CANCEL,gtk.ResponseType.CANCEL,gtk.STOCK_OPEN,gtk.ResponseType.OK))
            pass
        else : 
            openexplogchooser=gtk.FileChooserDialog(title="Open experiment log",action=gtk.FILE_CHOOSER_ACTION_OPEN,buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
            pass
            
        #openexplogchooser.set_current_name(self.suggestname())
        xlgfilter=gtk.FileFilter()
        xlgfilter.set_name("Experiment log files")
        xlgfilter.add_pattern("*.xlg")
        openexplogchooser.add_filter(xlgfilter)

        result=openexplogchooser.run()
        fname=openexplogchooser.get_filename()
        openexplogchooser.destroy()
        
        if result==RESPONSE_OK:
            self.open_explog(fname)
            pass
        pass

    def open_explog(self,fname):
        
        if (not os.path.exists(fname)) :
            if hasattr(gtk,"MessageType") and hasattr(gtk.MessageType,"WARNING"):
                # gtk3
                existsdialog=gtk.MessageDialog(type=gtk.MessageType.ERROR,buttons=gtk.ButtonsType.OK)
                pass
            else : 
                existsdialog=gtk.MessageDialog(type=gtk.MESSAGE_ERROR,buttons=gtk.BUTTONS_OK)
                pass
            existsdialog.set_markup("Error: File %s does not exist." % (fname))
            existsdialog.run()
            existsdialog.destroy()
            return
        try : 
            self.unsyncexplog()
            self.explog.close()
            self.explog=xmlexplog.explog(fname,self.dc_gui_io,self.paramdb,oldfile=True,use_locking=True) # autoflush=self.autoflush,autoresync=self.autoresync)            

            self.set_dest()

            try: 
                self.syncexplog()
                pass
            finally:
                self.explog.unlock_rw() # free-up automatic log on open
                pass

            self.paramdb["explogname"].requestvalstr_sync(os.path.split(fname)[-1])


            pass
        except : 
            
            self.unsyncexplog(ignoreerror=True)
            
            (exctype,excvalue)=sys.exc_info()[:2]
            if hasattr(gtk,"MessageType") and hasattr(gtk.MessageType,"WARNING"):
                # gtk3
                exceptdialog=gtk.MessageDialog(type=gtk.MessageType.ERROR,buttons=gtk.ButtonsType.OK)
                pass
            else : 
                exceptdialog=gtk.MessageDialog(type=gtk.MESSAGE_ERROR,buttons=gtk.BUTTONS_OK)
                pass

            exceptdialog.set_markup("<b>Error opening/syncing with file %s.</b>\n%s: %s\n%s\nMust exit." % (xml.sax.saxutils.escape(fname),xml.sax.saxutils.escape(str(exctype.__name__)),xml.sax.saxutils.escape(str(excvalue)),xml.sax.saxutils.escape(str(traceback.format_exc()))))
            exceptdialog.run()
            exceptdialog.destroy()
            sys.exit(1)
            pass
        
        # turn on experiment and checklist menu items 
        self.gladeobjdict["explogguiopen"].set_sensitive(True)
        self.gladeobjdict["explogchecklistopen"].set_sensitive(True)
        
        # turn off file new/open menu items
        self.gladeobjdict["explogfilenew"].set_sensitive(False)
        self.gladeobjdict["explogfileopen"].set_sensitive(False)

        # # turn off ability to load more config files
        # self.gladeobjdict["explogfileloadconfig"].set_sensitive(False)
            
        self.assign_title()
        
        self.log_config()
        pass
    
    
    def log_config(self):
        self.explog.lock_rw()
        try: 
            configel=self.explog.addelement(None,"dc:configstr")
            configel.attrib["fnames"]=json.dumps(self.configfnames)
            
            self.explog.settext(configel,self.configstr)
            pass
        except:
            raise
        finally:
            self.explog.unlock_rw()
            pass

        pass

    def choose_loadconfig(self,event):
        if hasattr(gtk,"FileChooserAction") and hasattr(gtk.FileChooserAction,"OPEN"):
            # gtk3
            loadconfigchooser=gtk.FileChooserDialog(title="Load config file",action=gtk.FileChooserAction.OPEN,buttons=(gtk.STOCK_CANCEL,gtk.ResponseType.CANCEL,gtk.STOCK_OPEN,gtk.ResponseType.OK))
            pass
        else : 
            loadconfigchooser=gtk.FileChooserDialog(title="Load config file",action=gtk.FILE_CHOOSER_ACTION_OPEN,buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
            pass
        #openexplogchooser.set_current_name(self.suggestname())
        loadconfigchooser.set_current_folder(os.path.abspath(os.path.join(thisdir, '..', 'conf')))
        dccfilter=gtk.FileFilter()
        dccfilter.set_name("Datacollect config (*.dcc) files")
        dccfilter.add_pattern("*.dcc")
        loadconfigchooser.add_filter(dccfilter)

        result=loadconfigchooser.run()
        fname=loadconfigchooser.get_filename()
        loadconfigchooser.destroy()
        
        if result==RESPONSE_OK:

            if (not os.path.exists(fname)) :
                
                if hasattr(gtk,"MessageType") and hasattr(gtk.MessageType,"WARNING"):
                    # gtk3
                    existsdialog=gtk.MessageDialog(type=gtk.MessageType.ERROR,buttons=gtk.ButtonsType.OK)
                    pass
                else : 
                    existsdialog=gtk.MessageDialog(type=gtk.MESSAGE_ERROR,buttons=gtk.BUTTONS_OK)
                    pass
                existsdialog.set_markup("Error: File %s does not exist." % (fname))
                existsdialog.run()
                existsdialog.destroy()
                return
            # load config file here...
            # imp.load_source("datacollect_config",fname)
            self.load_config(fname)

            pass
        
        pass


    def choose_saveparams(self,event):
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

        chxcheckbox=gtk.CheckButton("Include root checklists")
        chxcheckbox.set_active(True)
        checkboxvbox.pack_start(chxcheckbox)

        xlgcheckbox=gtk.CheckButton("Include experiment log info")
        xlgcheckbox.set_active(True)
        checkboxvbox.pack_start(xlgcheckbox)

        saveparamschooser.set_extra_widget(checkboxvbox)
        
        checkboxvbox.show_all()
        #saveparamschooser.add_button("FooButton",5)

        result=saveparamschooser.run()
        fname=saveparamschooser.get_filename()
        saveparamschooser.destroy()
        
        if result==RESPONSE_OK:

            # load config file here...
            # imp.load_source("datacollect_config",fname)
            paramdbfile.save_params(self.configfnames, [gui[3] for gui in self.guis],self.paramdb,fname,self.explog.filename,self.SingleSpecimen,non_settable=nonsettablecheckbox.get_active(),dcc=dcccheckbox.get_active(),gui=guicheckbox.get_active(),chx=chxcheckbox.get_active(),xlg=xlgcheckbox.get_active())
            

            pass
        
        pass



    def createparamserver(self):
        if self.paramserver is None:
            self.paramserver=dc_dbus_paramserver(self.paramdb,self.checklists)
            pass
        pass
    

    def load_config(self,fname):
        
        output=dc2_misc.load_config(fname,self.paramdb,self.dc_gui_io,self.createparamserver)

        self.configstr+="\n"+output+"\n"

        # turn off load config menu items
        # self.gladeobjdict["explogfileloadconfig"].set_sensitive(False)

        # turn on file new/open menu items
        self.gladeobjdict["explogfilenew"].set_sensitive(True)
        self.gladeobjdict["explogfileopen"].set_sensitive(True)

        self.configfnames.append(canonicalize_path.canonicalize_path(fname))

        pass
    


    def closehandler(self,widget,event):
        # returns False to close, True to cancel

        if self.experiment is not None:
            if hasattr(gtk,"MessageType") and hasattr(gtk.MessageType,"WARNING"):
                # gtk3
                experimentchoice=gtk.MessageDialog(type=gtk.MessageType.QUESTION,buttons=gtk.ButtonsType.YES_NO)
                pass
            else : 
                experimentchoice=gtk.MessageDialog(type=gtk.MESSAGE_QUESTION,buttons=gtk.BUTTONS_YES_NO)
                pass

            experimentchoice.set_markup("Experiment still in progress\n(experiment window still open).\nExit anyway?")
            experimentchoiceval=experimentchoice.run()
            experimentchoice.destroy()
            if experimentchoiceval==RESPONSE_NO:
                return True
            pass
        
        if len(self.checklists) > 0:
            if hasattr(gtk,"MessageType") and hasattr(gtk.MessageType,"WARNING"):
                checklistchoice=gtk.MessageDialog(type=gtk.MessageType.QUESTION,buttons=gtk.ButtonsType.YES_NO)
                # gtk3
                pass
            else : 
                checklistchoice=gtk.MessageDialog(type=gtk.MESSAGE_QUESTION,buttons=gtk.BUTTONS_YES_NO)
                pass
            checklistchoice.set_markup("Checklists still in progress\nExit anyway?")
            checklistchoiceval=checklistchoice.run()
            checklistchoice.destroy()
            if checklistchoiceval==RESPONSE_NO:
                return True
            
            pass
        
        sys.exit(0)
        return False
    
    def quit(self,event):
        # let closehandler take care of it. 
        if not self.emit("delete-event",gdk.Event(DELETE)):
            self.destroy()  
            pass
        
        pass

    def choose_opengui(self,event):

        if hasattr(gtk,"FileChooserAction") and hasattr(gtk.FileChooserAction,"OPEN"):
            # gtk3
            guichooser=gtk.FileChooserDialog(title="Open GUI",action=gtk.FileChooserAction.OPEN,buttons=(gtk.STOCK_CANCEL,gtk.ResponseType.CANCEL,gtk.STOCK_OPEN,gtk.ResponseType.OK))
            pass
        else : 
            guichooser=gtk.FileChooserDialog(title="Open GUI",action=gtk.FILE_CHOOSER_ACTION_OPEN,buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
            pass
        guichooser.set_current_folder(os.path.abspath(os.path.join(thisdir, '..', 'conf')))        
        gladefilter=gtk.FileFilter()
        gladefilter.set_name("Glade files")
        gladefilter.add_pattern("*.glade")
        guichooser.add_filter(gladefilter)


        result=guichooser.run()
        fname=guichooser.get_filename()
        guichooser.destroy()
        
        if result==RESPONSE_OK:
            
            self.open_gui(fname)
            pass

        pass

    def open_gui(self,fname):
        
        (gladeobjdict,builder)=build_from_file(fname)
        dc_gui_initialize_widgets(gladeobjdict,self.guistate)
        
        
        win=gladeobjdict["guiwindow"]

        # Only set the title if the glade file doesn't specify it
        if win.get_title() == "" or win.get_title() is None:
            win.set_title(os.path.split(fname)[1])
        
        gui=(gladeobjdict,builder,win,fname)
        self.guis.append(gui)
        
        win.connect("delete-event",self.handle_gui_close,gui)
        win.show_all()
        
        pass

    def expphotograph(self,event):
        filenamexpath="concat(substring-before(dc:paramdb('explogname'),'.xlg'),'_expphoto-%.3d.jpg')"
        
        photorequest=ricohcamera.ricohphotorequest(self.paramdb,"expphotos",reqfilenamexpath=filenamexpath,explogwindow=self)
        
        photorequest.dc_gui_init(self.guistate)
        photorequest.show_all()
        
        pass

    def measphotograph(self,event):
        # xpath conditional mirror xmlexplog get_measnum() method. See http://stackoverflow.com/questions/971067/is-there-an-if-then-else-statement-in-xpath
        # use dc:formatintegermindigits (defined in paramdb2.py) to demand a minimum number of digits for an integer 
        # filenamexpath="concat(dc:paramdb('explogname'),'_meas',format-number(number(concat(/dc:experiment/dc:measurement[last()]/dc:measnum,substring('-1',1,number(count(/dc:experiment/dc:measurement) &lt; 1)*2)))+1,'####'),'_photo-%.3d.jpg')"
        filenamexpath="concat(dc:paramdb('explogname'),'_meas',dc:formatintegermindigits(number(concat(/dc:experiment/dc:measurement[last()]/dc:measnum,substring('-1',1,number(count(/dc:experiment/dc:measurement) < 1)*2)))+1,4),'_photo-%.3d.jpg')"
        
        photorequest=ricohcamera.ricohphotorequest(self.paramdb,"measphotos",filenamexpath,self)
        
        photorequest.dc_gui_init(self.guistate)
        photorequest.show_all()
        
        pass

    def choose_openchecklists(self,event):
        # open the checklists (checklistdbwin) window
        if self.explog.filename is None:
            return
        if self.checklistdbwin is None:
            contextdir=os.path.split(self.explog.filename)[0]

            self.checklistdbwin=checklistdbwin.checklistdbwin(contextdir,self.paramdb,"checklists",self.popupchecklist,[],True,True)
            self.checklistdbwin.show()
            pass
        else:
            self.checklistdbwin.liststoreupdate()
            self.checklistdbwin.present()
            pass
        pass

    def choose_openchecklist(self,event):
        
        if hasattr(gtk,"FileChooserAction") and hasattr(gtk.FileChooserAction,"OPEN"):
            # gtk3
            checklistchooser=gtk.FileChooserDialog(title="Open checklist",action=gtk.FileChooserAction.OPEN,buttons=(gtk.STOCK_CANCEL,gtk.ResponseType.CANCEL,gtk.STOCK_OPEN,gtk.ResponseType.OK))
            pass
        else : 
            checklistchooser=gtk.FileChooserDialog(title="Open checklist",action=gtk.FILE_CHOOSER_ACTION_OPEN,buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
            pass
            
        chxfilter=gtk.FileFilter()
        chxfilter.set_name("Checklist files")
        chxfilter.add_pattern("*.chx")
        checklistchooser.add_filter(chxfilter)

        chffilter=gtk.FileFilter()
        chffilter.set_name("Filled checklist files")
        chffilter.add_pattern("*.chf")
        checklistchooser.add_filter(chffilter)

        result=checklistchooser.run()
        fname=checklistchooser.get_filename()
        checklistchooser.destroy()
        
        if result==RESPONSE_OK:
            self.addtochecklistmenu(fname)
            self.open_checklist(fname)

            pass
        
        pass


    def rebuildchecklistrealtimemenu(self,checklistjunk):
        openchecklists=checklistdb.getchecklists(None,None,None,None,allchecklists=True)
        menuentries=self.gladeobjdict["explogchecklistmenu"].get_children()
        
        # total non-realtime menu entries is self.checklistmenuorigentries+len(self.checklistmenushortcuts)
        # remove all the later ones
        for cnt in range(self.checklistmenuorigentries+len(self.checklistmenushortcuts),len(menuentries)):
            self.gladeobjdict["explogchecklistmenu"].remove(menuentries[cnt])
            pass

        # append a separator
        newitem=gtk.SeparatorMenuItem()
        self.gladeobjdict["explogchecklistmenu"].append(newitem)
        newitem.show()

        for cnt in range(len(openchecklists)):
            if openchecklists[cnt].filename is None: # use mem:// url
                newitem=gtk.MenuItem(label=openchecklists[cnt].canonicalpath,use_underline=False)
            else:
                newitem=gtk.MenuItem(label=openchecklists[cnt].filename,use_underline=False)
                pass
            newitem.connect("activate",self.checklistmenu_realtime,openchecklists[cnt].canonicalpath)
            self.gladeobjdict["explogchecklistmenu"].append(newitem)
            newitem.show()
            # sys.stderr.write("adding checklist menu item: %s\n" % (openchecklists[cnt].filename))
            pass
        pass

    def addtochecklistmenu(self,fname):
        if fname in self.checklistmenushortcuts: 
            # already present
            return

        Item=gtk.MenuItem(label=fname,use_underline=False)
        Item.set_name("prevchecklist_%s" % (fname))
        Item.connect("activate",self.checklistmenu_prevchecklist,fname)
        self.checklistmenushortcuts[fname]=Item
        
        menuentries=self.gladeobjdict["explogchecklistmenu"].get_children()
        for cnt in range(len(self.checklistmenushortcuts)):
            # sys.stderr.write("cnt=%d; origentries=%d len(menuentries)=%d len(shortcuts)=%d\n" % (cnt,self.checklistmenuorigentries,len(menuentries),len(self.checklistmenushortcuts)))
            if cnt==len(self.checklistmenushortcuts)-1 or menuentries[self.checklistmenuorigentries+cnt].get_name() > Item.get_name():
                # add item here
                self.gladeobjdict["explogchecklistmenu"].insert(Item,self.checklistmenuorigentries+cnt)
                break
                pass
            pass



        pass

    def checklistmenu_realtime(self,event,canonicalname):

        self.popupchecklist(canonicalname)
        
        return True

    def checklistmenu_prevchecklist(self,event,fname):
        self.open_checklist(fname)
        
        return True


    def open_checklist_parent(self,chklist):
        
        # does this checklist have a parent that we should open too? 
        parent=chklist.get_parent() # returns hrefv

        #sys.stderr.write("open_checklist_parent: parent=%s\n" % (parent))

        if parent is not None and parent.getpath("/") is not None:
            # parentcontextdir=chklist.xmldoc.getcontextdir()
            # if parentcontextdir is None:
            #    # assume it is in dest..
            #     parentcontextdir=str(self.paramdb["dest"].dcvalue)
            #    pass
                
            #if not os.path.isabs(parent):
            #    parentpath=os.path.join(parentcontextdir,parent)
            #    pass
            #else:
            #    parentpath=parent
            #    pass

            #sys.stderr.write("open_checklist_parent: parentpath=%s\n" % (parentpath))

            # check if parent is already open in-memory
            (parentclobj,parentcanonfname)=dc2_misc.searchforchecklist(parent.getpath("/"))
            # sys.stderr.write("parentcanonfname=%s\n" % (parentcanonfname))

            #sys.stderr.write("open_checklist_parent: parentcanonfname=%s\n" % (parentcanonfname))

            if parentclobj is None:
                # if not, open the parent checklist
                if os.path.splitext(parentcanonfname)[1].lower()==".plx" or os.path.splitext(parentcanonfname)[1].lower()==".plf":
                    self.open_plan(parentcanonfname)
                else : 
                    self.open_checklist(parentcanonfname)
                pass
            pass
        pass


    def open_checklist(self,fname,inplace=False):

        
        
        if inplace:
            chklist=checklist.checklist(fname,self.paramdb,datacollect_explog=self.explog,datacollect_explogwin=self,destoverride=os.path.split(fname)[0])
            pass
        else:
            chklist=checklist.checklist(fname,self.paramdb,datacollect_explog=self.explog,datacollect_explogwin=self,destoverride=str(self.paramdb["dest"].dcvalue))
            pass

            
        self.checklists.append(chklist)
        
        chklist.dc_gui_init(self.guistate)

        contextdir=os.path.split(self.explog.filename)[0]

        self.open_checklist_parent(chklist) # open our parent, if necessary

        checklistdb.addchecklisttoparamdb(chklist,self.paramdb,"checklists")
        checklistdb.newchecklistnotify(chklist,False)

        # checklistdb.checklistnotify(chklist,contextdir,self.paramdb,"checklists")
        # chklist.xmldoc.shouldbeunlocked()
        

        self.explog.shouldbeunlocked()
        
        win=chklist.getwindow()
        win.connect("delete-event",self.handle_checklist_close,chklist)
        win.show_all()
        
        return chklist


    def popupchecklist(self,fname):
        # bring up checklist if it is open
        # otherwise open it
        (chklistobj,canonfname)=dc2_misc.searchforchecklist(fname)

        if chklistobj is None:
            # open the checklist
            if os.path.splitext(fname)[1].lower()==".plx" or os.path.splitext(fname)[1].lower()==".plf":
                return self.open_plan(fname)
            else : 
                return self.open_checklist(fname)
            pass
        else:
            # bring it to front 
            chklistobj.present()
            return chklistobj
            

        pass

    def choose_openplan(self,event):
        
        if hasattr(gtk,"FileChooserAction") and hasattr(gtk.FileChooserAction,"OPEN"):
            # gtk3
            checklistchooser=gtk.FileChooserDialog(title="Open plan",action=gtk.FileChooserAction.OPEN,buttons=(gtk.STOCK_CANCEL,gtk.ResponseType.CANCEL,gtk.STOCK_OPEN,gtk.ResponseType.OK))
            pass
        else : 
            checklistchooser=gtk.FileChooserDialog(title="Open plan",action=gtk.FILE_CHOOSER_ACTION_OPEN,buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
            pass
            
        plxfilter=gtk.FileFilter()
        plxfilter.set_name("Plan checklist files")
        plxfilter.add_pattern("*.plx")
        checklistchooser.add_filter(plxfilter)

        plffilter=gtk.FileFilter()
        plffilter.set_name("Filled checklist files")
        plffilter.add_pattern("*.plf")
        checklistchooser.add_filter(plffilter)

        result=checklistchooser.run()
        fname=checklistchooser.get_filename()
        checklistchooser.destroy()
        
        if result==RESPONSE_OK:
            self.open_plan(fname)

            pass
        
        pass


    def open_plan(self,fname):

        
        chklist=checklist.checklist(fname,self.paramdb,datacollect_explog=self.explog,datacollect_explogwin=self,destoverride=str(self.paramdb["dest"].dcvalue))
            
        self.checklists.append(chklist)
        
        chklist.dc_gui_init(self.guistate)
        
        contextdir=os.path.split(self.explog.filename)[0]

        checklistdb.addchecklisttoparamdb(chklist,self.paramdb,"plans")
        checklistdb.newchecklistnotify(chklist,False)

        # checklistdb.checklistnotify(chklist,contextdir,self.paramdb,"plans",True)
        
        win=chklist.getwindow()
        win.connect("delete-event",self.handle_checklist_close,chklist)
        win.show_all()
        
        pass

    

    def isconsistent(self,inconsistentlist):
        # checks consistency for GUIs but NOT checklists
        consistent=True
        for key in self.gladeobjdict:
            if hasattr(self.gladeobjdict[key],"isconsistent"):
                consistent=consistent and self.gladeobjdict[key].isconsistent(inconsistentlist)
                pass
            pass

        for gui in self.guis:
            gladeobjdict=gui[0]
            for key in gladeobjdict:
                if hasattr(gladeobjdict[key],"isconsistent"):
                    consistent=consistent and gladeobjdict[key].isconsistent(inconsistentlist)
                    pass
                pass
            pass

        # for checklist in self.checklists:
        #    consistent=consistent and checklist.isconsistent(inconsistentlist)
        #    pass
        
        return consistent
    
    def handle_checklist_close(self,param1,param2,chklist):
        chklist.destroy()
        self.checklists.remove(chklist)
        
        pass

    def handle_gui_close(self,param1,param2,gui):
        gui[2].destroy()
        self.guis.remove(gui)
        
        pass

    def aboutdialog(self,event):
        self.about_dialog.present()
        
        pass

    def hideaboutdialog(self,arg1,arg2=None):
        self.about_dialog.hide()
        return True


    pass
