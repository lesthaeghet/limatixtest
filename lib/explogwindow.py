import subprocess
import os
import os.path
import posixpath
import sys
import string
import copy
import json
import urllib
import pdb as pythondb

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


import paramdbfile

if hasattr(string,"maketrans"):
    maketrans=string.maketrans
    pass
else:
    maketrans=str.maketrans
    pass


import traceback
# import imp
if "gi" in sys.modules:  # gtk3
    import gi
    gi.require_version('Gtk','3.0')
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

chx_nsmap={ "dc": "http://thermal.cnde.iastate.edu/datacollect", "xlink": "http://www.w3.org/1999/xlink", "dcv":"http://thermal.cnde.iastate.edu/dcvalue", "chx": "http://thermal.cnde.iastate.edu/checklist"}

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
    dc_gui_iohandlers=None
    about_dialog=None
    guistate=None

    experiment=None  # Current experiment window
    checklists=None  # list of checklists and plans currently open
    guis=None  # list of guis currently open. Each is a tuple (gladeobjdict,builder,win)

    checklistdbwin=None # checklistdbwin object for browsing checklists in the experiment log

    paramserver=None  # dc_dbus_paramserver.dc_dbus_paramserver object

    configfhrefs=None # list of loaded config files (dcv.hrefvalue)
    configfstrs=None # list of archives of the config file as we read it .

    dest=None # destination directory for dgs, settings, chf files, etc. 


    checklistmenushortcuts=None # dictionary of menuitems, added as shortcuts to the checklist menu, indexed by href
    checklistmenuorigentries=None # original count of glade menu entries
    
    checklistmenurealtimeentries=None

    def __init__(self,gladefile,paramdb,SingleSpecimen):
        gobject.GObject.__init__(self)

        self.gladefile=gladefile
        self.paramdb=paramdb
        self.SingleSpecimen=SingleSpecimen
        # self.autoflush=True
        # self.autoresync=True

        self.configfhrefs=[]
        self.configfstrs=[]
        self.guis=[]
        self.checklistmenushortcuts={}

        self.explog=None
        #self.explog=xmlexplog.explog(None,self.dc_gui_iohandlers,self.paramdb,use_locking=True,debug=False) # ,autoflush=self.autoflush,autoresync=self.autoresync)
        #try: 
        #    self.syncexplog()
        #    pass
        #finally:
        #    self.explog.unlock_rw() # free-up automatic log on open
        #    pass

        (self.gladeobjdict,self.builder)=build_from_file(self.gladefile)
        self.checklistmenuorigentries=len(self.gladeobjdict["explogchecklistmenu"].get_children())

        # Add reset specimen button or specimen textentry, depending 
        # on whether we are in single specimen mode

        
        self.add(self.gladeobjdict["explog"])

        self.about_dialog=self.gladeobjdict["aboutdialog"]
        self.SetSingleSpecimenGui()

        self.experiment=None
        self.checklists=[]
        

        # disable opening gui until config loaded
        # self.gladeobjdict["explogguiopen"].set_sensitive(False)
        self.gladeobjdict["explogcentralchecklistopen"].set_sensitive(False)
        self.gladeobjdict["explogcustomchecklistopen"].set_sensitive(False)

        # disable config loading until file picked
        self.gladeobjdict["explogfileloadcentralconfig"].set_sensitive(False)
        self.gladeobjdict["explogfileloadcustomconfig"].set_sensitive(False)

        
        

        # self.builder.connect_signals(self)
        self.gladeobjdict["explogfilenew"].connect("activate",self.choose_newexplog)
        self.gladeobjdict["explogfileopen"].connect("activate",self.choose_openexplog)
        self.gladeobjdict["explogfileloadcentralconfig"].connect("activate",self.choose_loadcentralconfig)
        self.gladeobjdict["explogfileloadcustomconfig"].connect("activate",self.choose_loadcustomconfig)
        self.gladeobjdict["explogfilesaveparams"].connect("activate",self.choose_saveparams)
        self.gladeobjdict["explogquit"].connect("activate",self.quit)
        self.connect("delete-event",self.closehandler)
        self.gladeobjdict["explogguiopen"].connect("activate",self.choose_opengui)
        self.gladeobjdict["explogguiopenparamdbeditor"].connect("activate",self.openparamdbeditor)
        self.gladeobjdict["explogguiexpphotograph"].connect("activate",self.expphotograph)
        self.gladeobjdict["explogguimeasphotograph"].connect("activate",self.measphotograph)
        self.gladeobjdict["explogcentralchecklistopen"].connect("activate",self.choose_opencentralchecklist)
        self.gladeobjdict["explogcustomchecklistopen"].connect("activate",self.choose_opencustomchecklist)
        self.gladeobjdict["explogchecklists"].connect("activate",self.choose_openchecklists)

        self.gladeobjdict["explogplanopen"].connect("activate",self.choose_openplan)
        self.gladeobjdict["explogaboutmenu"].connect("activate",self.aboutdialog)
        self.gladeobjdict["explogdebugmenu"].connect("activate",self.debug_pm)
        self.gladeobjdict["aboutdialog"].connect("delete-event",self.hideaboutdialog)
        self.gladeobjdict["aboutdialog"].connect("response",self.hideaboutdialog)
        self.gladeobjdict["ResetSpecimenButton"].connect("clicked",self.reset_specimen)

        
        # request notifications when a new checklist is opened or reset, so we can rebuild our menu
        checklistdb.requestopennotify(self.rebuildchecklistrealtimemenu)
        checklistdb.requestresetnotify(self.rebuildchecklistrealtimemenu)
        checklistdb.requestfilenamenotify(self.rebuildchecklistrealtimemenu)
        checklistdb.requestclosenotify(self.rebuildchecklistrealtimemenu)

        self.assign_title()


        pass

    def ChooseSingleSpecimen(self):
        if hasattr(gtk,"MessageType") and hasattr(gtk.MessageType,"WARNING"):
            # gtk3
            specimenchoice=gtk.MessageDialog(type=gtk.MessageType.QUESTION,buttons=gtk.ButtonsType.NONE)
            pass
        else : 
            specimenchoice=gtk.MessageDialog(type=gtk.MESSAGE_QUESTION,buttons=gtk.BUTTONS_NONE)
            pass
        specimenchoice.set_markup("Will the experiment involve a single specimen or multiple specimens?")
        specimenchoice.add_button("Single specimen",1)
        specimenchoice.add_button("Multiple specimens", 2)
        specimenchoiceval=specimenchoice.run()
        specimenchoice.destroy()
    
        if specimenchoiceval==1:
            self.SingleSpecimen=True
            pass
        elif specimenchoiceval==2:
            self.SingleSpecimen=False
            pass
        else :
            raise ValueError("Invalid response from specimen choice dialog")

        pass
    
    def SetSingleSpecimenGui(self):
        SBParent=self.gladeobjdict["SpecBox"].get_parent()
        if SBParent is self.gladeobjdict["ParamBox"]:
            self.gladeobjdict["ParamBox"].remove(self.gladeobjdict["SpecBox"])
            pass

        RSBParent=self.gladeobjdict["ResetSpecimenButton"].get_parent()
        if RSBParent is self.gladeobjdict["ParamBox"]:
            self.gladeobjdict["ParamBox"].remove(self.gladeobjdict["ResetSpecimenButton"])
            pass

        
        if self.SingleSpecimen is None or self.SingleSpecimen:
            SpecimenWidget=self.gladeobjdict["SpecBox"]
            pass
        else :
            SpecimenWidget=self.gladeobjdict["ResetSpecimenButton"]
            pass
        self.gladeobjdict["ParamBox"].pack_start(SpecimenWidget,True,True,0)
        self.gladeobjdict["ParamBox"].reorder_child(SpecimenWidget,1)


    def reset_specimen(self,*args):
        #sys.stderr.write("Got reset_specimen()\n")
        self.paramdb["specimen"].requestvalstr_sync("")
        
        return True

    def openparamdbeditor(self,*args):
        
        paramdb2_editor.paramdb2_editor(self.paramdb)
        
        pass

    def syncexplog(self):

        # pythondb.set_trace()
        if self.SingleSpecimen:
            self.paramdb["specimen"].controller.adddoc(self.explog,"dc:summary/dc:specimen")
            pass

        # put selected parameters in the summary
        # controllers are instantiated in datacollect2
        # also update "not synced" in paramdbfile.py if this list changes
        # don't forget to put parallel remdoc entries in unsyncexplog
        self.paramdb["perfby"].controller.adddoc(self.explog,"dc:summary/dc:perfby")
        self.paramdb["date"].controller.adddoc(self.explog,"dc:summary/dc:date")
        self.paramdb["dest"].controller.adddoc(self.explog,"dc:summary/dc:dest")
        self.paramdb["expnotes"].controller.adddoc(self.explog,"dc:summary/dc:expnotes")
        self.paramdb["goal"].controller.adddoc(self.explog,"dc:summary/dc:goal")
        self.paramdb["expphotos"].controller.adddoc(self.explog,"dc:summary/dc:expphotos")
        self.paramdb["hostname"].controller.adddoc(self.explog,"dc:summary/dc:hostname")
        self.paramdb["measnum"].controller.adddoc(self.explog,"dc:summary/dc:measnum")
        self.paramdb["checklists"].controller.adddoc(self.explog,"dc:summary/dc:checklists")
        self.paramdb["plans"].controller.adddoc(self.explog,"dc:summary/dc:plans")

        if self.explog.filehref is not None:
            # Re-register checklists and plans with checklistdb, with contexthref set
            checklistdb.register_paramdb(self.paramdb,"checklists",self.explog.filehref,False)
            checklistdb.register_paramdb(self.paramdb,"plans",self.explog.filehref,True)
            pass
        pass

    def unsyncexplog(self,ignoreerror=False):
        try : 

            if self.SingleSpecimen:
                self.paramdb["specimen"].controller.remdoc(self.explog,"dc:summary/dc:specimen")
                pass
            
            self.paramdb["perfby"].controller.remdoc(self.explog,"dc:summary/dc:perfby")
            self.paramdb["date"].controller.remdoc(self.explog,"dc:summary/dc:date")
            self.paramdb["dest"].controller.remdoc(self.explog,"dc:summary/dc:dest")
            self.paramdb["expnotes"].controller.remdoc(self.explog,"dc:summary/dc:expnotes")
            self.paramdb["goal"].controller.remdoc(self.explog,"dc:summary/dc:goal")
            self.paramdb["expphotos"].controller.remdoc(self.explog,"dc:summary/dc:expphotos")
            self.paramdb["hostname"].controller.remdoc(self.explog,"dc:summary/dc:hostname")
            self.paramdb["measnum"].controller.remdoc(self.explog,"dc:summary/dc:measnum")
            self.paramdb["checklists"].controller.remdoc(self.explog,"dc:summary/dc:checklists")
            self.paramdb["plans"].controller.remdoc(self.explog,"dc:summary/dc:plans")

            pass
        except:
            if not ignoreerror:
                raise
            pass
        pass
    
    

    def assign_title(self):
        if self.explog is None or self.explog.filehref is None:
            self.set_title("Experiment log (no file)")
            pass
        else:
            self.set_title(self.explog.filehref.get_bare_unquoted_filename())
            pass
        
        pass
    
    def dc_gui_init(self,guistate):
        # need next line if subclassing a dc_gui class
        # super(dc_readout).__dc_gui_init(self,guistate)
        
        self.guistate=guistate
        
        self.dc_gui_iohandlers=guistate.iohandlers
        if self.explog is not None:
            self.explog.set_iohandlers(self.dc_gui_iohandlers)
            pass
        
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
        contexthref=self.explog.filehref.leafless()
        filepart=self.explog.filehref.get_bare_unquoted_filename()
        
        (fbase,ext)=posixpath.splitext(filepart)

        
        
        self.paramdb["dest"].requestval_sync(dcv.hrefvalue(quote(fbase+"_files/"),contexthref=contexthref))
        
        physdir=self.paramdb["dest"].dcvalue.getpath()
        if not os.path.exists(physdir):
            os.mkdir(physdir)
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
        newexplogchooser.set_current_folder(".")
        xlgfilter=gtk.FileFilter()
        xlgfilter.set_name("Experiment log files")
        xlgfilter.add_pattern("*.xlg")
        newexplogchooser.add_filter(xlgfilter)

        result=newexplogchooser.run()
        fname=newexplogchooser.get_filename()
        newexplogchooser.destroy()

        href=dcv.hrefvalue(pathname2url(fname))
        
        if result==RESPONSE_OK:
            self.new_explog(href)
        
            pass
        
        pass

    def new_explog(self,href,parentchecklistpath=None):
        # parentchecklistpath, if given, should be 
        # relative to the directory fname is in. 

        if (checklist.href_exists(href)) :
            if hasattr(gtk,"MessageType") and hasattr(gtk.MessageType,"WARNING"):
                # gtk3
                existsdialog=gtk.MessageDialog(type=gtk.MessageType.ERROR,buttons=gtk.ButtonsType.OK)
                pass
            else : 
                existsdialog=gtk.MessageDialog(type=gtk.MESSAGE_ERROR,buttons=gtk.BUTTONS_OK)
                pass

            existsdialog.set_markup("Error: URL %s exists.\nWill not overwrite\n(Try -a option if you want to append to an existing experiment log)" % (str(href)))
            existsdialog.run()
            existsdialog.destroy()
            return

        if self.SingleSpecimen is None:
            # Need to choose Single Specimen/Multi-Specimen mode
            self.ChooseSingleSpecimen()
            pass
        
        # self.explog.setfilename(fname)
        # self.explog.shouldbeunlocked()
        
        # self.unsyncexplog()  # need to restart synchronization once dest has changed

        self.explog=xmlexplog.explog(href,self.dc_gui_iohandlers,self.paramdb,use_locking=True,debug=False) # ,autoflush=self.autoflush,autoresync=self.autoresync)
        try: 
            pass
        finally:
            self.explog.unlock_rw() # free-up automatic log on open
            pass

        self.explog.set_iohandlers(self.dc_gui_iohandlers)
        
        self.set_dest()

        self.syncexplog()
        
        if self.explog.filehref is not None:
            # Re-register checklists and plans with checklistdb, with contexthref set
            checklistdb.register_paramdb(self.paramdb,"checklists",self.explog.filehref,False)
            checklistdb.register_paramdb(self.paramdb,"plans",self.explog.filehref,True)
            pass


        filepart=href.get_bare_unquoted_filename()

        self.paramdb["explogname"].requestvalstr_sync(filepart)
        
        # self.explog.flush()
        

        # enable config loading
        self.gladeobjdict["explogfileloadcentralconfig"].set_sensitive(True)
        self.gladeobjdict["explogfileloadcustomconfig"].set_sensitive(True)

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
        
        

        pass


    def load_params_from_latest_explog_measurement(self):
        # Yes, we should load parameters
        toassign=[]  # assign parameters as (paramdbname,dcvalue,log message) to a list
        # so we can run the assignment later, without the experiment log locked
        self.explog.lock_ro()
        try:
            measelements=self.explog.xpath("dc:measurement[last()]")
            if len(measelements) > 0:
                measelement=measelements[0]
                
                # iterate over all children of the dc:measurement tag
                for meastag in self.explog.children(measelement):
                    tag=self.explog.gettag(meastag)
                    (prefix,dctag)=tag.split(":")
                    if prefix != "dc":
                        continue # silently ignore prefixes not in the dc: namespace

                    if dctag=="measnum" or dctag=="notes" or dctag=="recordmeastimestamp" or dctag=="hostname" or dctag=="measchecklist" or dctag=="date":
                        # silently ignore measnum, notes, timestamp, hostname, measchecklist, and date
                        continue

                    if not dctag in self.paramdb:
                        toassign.append((None,None,"Tag %s not in the parameter database (ignored)" % (tag)))
                        continue
                    
                    if self.paramdb[dctag].dangerous:
                        dangerousvalue=self.paramdb[dctag].paramtype.fromxml(self.explog,meastag,defunits=self.paramdb[dctag].defunits)
                        toassign.append((None,None,"Tag %s not assigned value %s because parameter database entry marked as dangerous (ignored)" % (tag,str(dangerousvalue))))
                        continue
                    
                    
                    dcvalue=self.paramdb[dctag].paramtype.fromxml(self.explog,meastag,defunits=self.paramdb[dctag].defunits)
                    toassign.append((dctag,dcvalue,"Assigning \"%s\" to parameter %s..." % (str(dcvalue),dctag)))
                    pass
                
                            
                pass
            pass
        finally:
            self.explog.unlock_ro()
            pass
        
        loadparamsmsg=""
        # perform assignments and generate message
        for (dctag,dcvalue,message) in toassign:
            if dctag is None:
                loadparamsmsg += message+"\n"
                pass
            else:
                loadparamsmsg += message
                try: 
                    self.paramdb[dctag].requestval_sync(dcvalue)
                    loadparamsmsg+=" value \"%s\" " % (str(self.paramdb[dctag].dcvalue))
                    if self.paramdb[dctag].dcvalue==dcvalue:
                        loadparamsmsg+="(match)\n"
                        pass
                    else:
                        loadparamsmsg+="<b>(mismatch)</b>\n"
                        pass
                    pass
                except:
                    (exctype,excvalue)=sys.exc_info()[:2]
                    loadparamsmsg+="%s in requestval: %s\n" % (str(exctype.__name__),str(excvalue))
                    loadparamsmsg+=xml.sax.saxutils.escape(traceback.format_exc())
                    pass
                
                pass
            
            pass
        if hasattr(gtk,"MessageType") and hasattr(gtk.MessageType,"WARNING"):
            # gtk3            
            infodialog=gtk.MessageDialog(type=gtk.MessageType.INFO,buttons=gtk.ButtonsType.OK)
            pass
        else:
            infodialog=gtk.MessageDialog(type=gtk.MESSAGE_INFO,buttons=gtk.BUTTONS_OK)
            pass
        infodialog.set_markup(loadparamsmsg)
        infodialog.run()
        infodialog.destroy()
        
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

            # if no config files loaded, then autoloadconfig
            autoloadconfig=len(self.configfhrefs)==0
            
            
            self.open_explog(fname,autoloadconfig=autoloadconfig)
            pass
        pass

    def open_explog(self,href,autoloadconfig=False):
        
        if (not checklist.href_exists(href)) :
            if hasattr(gtk,"MessageType") and hasattr(gtk.MessageType,"WARNING"):
                # gtk3
                existsdialog=gtk.MessageDialog(type=gtk.MessageType.ERROR,buttons=gtk.ButtonsType.OK)
                pass
            else : 
                existsdialog=gtk.MessageDialog(type=gtk.MESSAGE_ERROR,buttons=gtk.BUTTONS_OK)
                pass
            existsdialog.set_markup("Error: File at URL %s does not exist." % (str(href)))
            existsdialog.run()
            existsdialog.destroy()
            return

        if self.SingleSpecimen is None and not autoloadconfig:
            # Need to choose Single Specimen/Multi-Specimen mode
            self.ChooseSingleSpecimen()
            pass
        
        try :
            if self.explog is not None:
                self.unsyncexplog()
                self.explog.close()
                pass
            self.explog=xmlexplog.explog(href,self.dc_gui_iohandlers,self.paramdb,oldfile=True,use_locking=True) # autoflush=self.autoflush,autoresync=self.autoresync)            

            try: 
                # self.set_dest()  -- since dest will already exist from prior call, sync operation below will set dest. 
                self.explog.set_iohandlers(self.dc_gui_iohandlers)

                # attempt to auto-load config, if applicable
                if autoloadconfig:
                    if self.SingleSpecimen is None:
                        # identify Single specimen mode based on file
                        summaryspecimens=self.explog.xpath("dc:summary/dc:specimen")
                        # if dc:specimen specified in summary: SingleSpecimen=True
                        self.SingleSpecimen = len(summaryspecimens)!=0
                        self.SetSingleSpecimenGui()
                        pass
                    
                    dc_configfiles=self.explog.xpath("dc:config[last()]/dc:configfile")
                    for dc_configfile in dc_configfiles:
                        configfhref=dcv.hrefvalue.fromxml(self.explog,dc_configfile)
                        self.load_config(configfhref)
                        pass

                    has_measelements = len(self.explog.xpath("dc:measurement[last()]")) > 0

                    pass

                self.syncexplog()
                pass
            finally:
                self.explog.unlock_rw() # free-up automatic log on open
                pass

            # Go through all checklists and plans, find those not marked 'done', and open them if possible
            checklistentries=checklistdb.getchecklists(self.explog.getcontexthref(),self.paramdb,"checklists",None,allchecklists=True)
            planentries=checklistdb.getchecklists(self.explog.getcontexthref(),self.paramdb,"plans",None,allplans=True)

            allentries=[]
            allentries.extend(checklistentries)
            allentries.extend(planentries)
            for entry in allentries:
                # Open checklists that are not already open, that have a url and that are not mem:// URLs
                if not entry.is_open and entry.filehref is not None and not entry.filehref.ismem(): 
                    chxdoc=xmldoc.xmldoc.loadhref(entry.filehref,chx_nsmap,readonly=True)
                    is_done = chxdoc.getattr(chxdoc.getroot(),"done",defaultvalue="false")=="true"
                    if not is_done:
                        if entry in planentries:
                            self.open_plan(entry.filehref)
                            pass
                        else:
                            self.open_checklist(entry.filehref)
                            pass
                        pass
                    pass
                pass
            filepart=entry.filehref.get_bare_unquoted_filename()

            self.paramdb["explogname"].requestvalstr_sync(filepart)
            
                
                

            if autoloadconfig and has_measelements:
                # offer to load parameters from most recent experiment log entry
                if hasattr(gtk,"MessageType") and hasattr(gtk.MessageType,"WARNING"):
                    # gtk3
                    loadparamsdialog=gtk.MessageDialog(type=gtk.MessageType.QUESTION,buttons=gtk.ButtonsType.YES_NO)
                    pass
                else:
                    loadparamsdialog=gtk.MessageDialog(type=gtk.MESSAGE_QUESTION,buttons=gtk.BUTTONS_YES_NO)
                    pass
                loadparamsdialog.set_markup("Loaded experiment log URL %s.\nAttempt to load non-dangerous parameters from most recent experiment log entry?" % (str(href)))
                loadparamsanswer=loadparamsdialog.run()
                loadparamsdialog.destroy()
                
                if ((hasattr(gtk,"ResponseType") and hasattr(gtk.ResponseType,"YES")
                    and loadparamsanswer==gtk.ResponseType.YES) or # gtk3
                    (hasattr(gtk,"RESPONSE_YES") and loadparamsanswer==gtk.RESPONSE_YES)):

                    self.load_params_from_latest_explog_measurement()
                    pass
                
                pass


            pass
        except : 
            
            self.unsyncexplog(ignoreerror=True)
            
            (exctype,excvalue)=sys.exc_info()[:2]
            if hasattr(gtk,"MessageType") and hasattr(gtk.MessageType,"WARNING"):
                # gtk3
                exceptdialog=gtk.MessageDialog(type=gtk.MessageType.ERROR,buttons=gtk.ButtonsType.NONE)
                pass
            else : 
                exceptdialog=gtk.MessageDialog(type=gtk.MESSAGE_ERROR,buttons=gtk.BUTTONS_NONE)
                pass

            exceptdialog.set_markup("<b>Error opening/syncing with URL %s.</b>\n%s: %s\n%s\nMust exit." % (xml.sax.saxutils.escape(str(href)),xml.sax.saxutils.escape(str(exctype.__name__)),xml.sax.saxutils.escape(str(excvalue)),xml.sax.saxutils.escape(str(traceback.format_exc()))))
            exceptdialog.add_button("Debug",1)
            exceptdialog.add_button("Exit",0)
            exceptdialogval=exceptdialog.run()
            exceptdialog.destroy()
            if exceptdialogval > 0:
                import pdb as pythondb
                print("exception: %s: %s" % (exctype.__name__,str(excvalue)))
                sys.stderr.write(traceback.format_exc())
                pythondb.post_mortem()

                pass
            sys.exit(1)
            pass
        

        # enable config loading
        self.gladeobjdict["explogfileloadcentralconfig"].set_sensitive(True)
        self.gladeobjdict["explogfileloadcustomconfig"].set_sensitive(True)

        # turn off file new/open menu items
        self.gladeobjdict["explogfilenew"].set_sensitive(False)
        self.gladeobjdict["explogfileopen"].set_sensitive(False)

        # # turn off ability to load more config files
        # self.gladeobjdict["explogfileloadconfig"].set_sensitive(False)

        

        # # turn off ability to load more config files
        # self.gladeobjdict["explogfileloadconfig"].set_sensitive(False)
            
        self.assign_title()
        
        pass
    
    
    def log_config(self):

        pass

    def choose_loadcustomconfig(self,event):
        return self.choose_loadconfig(event,central=False)

    def choose_loadcentralconfig(self,event):
        return self.choose_loadconfig(event,central=True)
    
    def choose_loadconfig(self,event,central):
        if hasattr(gtk,"FileChooserAction") and hasattr(gtk.FileChooserAction,"OPEN"):
            # gtk3
            loadconfigchooser=gtk.FileChooserDialog(title="Load config file",action=gtk.FileChooserAction.OPEN,buttons=(gtk.STOCK_CANCEL,gtk.ResponseType.CANCEL,gtk.STOCK_OPEN,gtk.ResponseType.OK))
            pass
        else : 
            loadconfigchooser=gtk.FileChooserDialog(title="Load config file",action=gtk.FILE_CHOOSER_ACTION_OPEN,buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
            pass
        #openexplogchooser.set_current_name(self.suggestname())
        if central: 
            loadconfigchooser.set_current_folder(os.path.abspath(os.path.join(thisdir, '..', 'conf')))
            pass
        else:
            if self.explog is not None:
                loadconfigchooser.set_current_folder(self.explog.getcontexthref().getpath())
                pass
            else:
                loadconfigchooser.set_current_folder(".")
                pass
            
            pass
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

            # sys.stderr.write("fname=%s" % (fname))
            
            if central:
                # central config files are always referred to
                # via absolute path
                fname=canonicalize_path.canonicalize_path(fname)
                href=dcv.hrefvalue(pathname2url(fname))
                pass
            else:
                # custom config files are always referred to
                # via relative path
                fname=canonicalize_path.relative_path_to(self.explog.getcontexthref().getpath(),fname)
                href=dcv.hrefvalue(pathname2url(fname),contexthref=self.explog.getcontexthref())
                pass
            
            #sys.stderr.write("fname=%s" % (fname))
            
            self.load_config(href)
            
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

        syncedcheckbox=gtk.CheckButton("Include parameters synced to experiment log")
        syncedcheckbox.set_active(False)
        checkboxvbox.pack_start(syncedcheckbox)

        saveparamschooser.set_extra_widget(checkboxvbox)
        
        checkboxvbox.show_all()
        #saveparamschooser.add_button("FooButton",5)

        result=saveparamschooser.run()
        fname=saveparamschooser.get_filename()
        saveparamschooser.destroy()
        
        if result==RESPONSE_OK:

            # load config file here...
            # imp.load_source("datacollect_config",fname)
            paramdbfile.save_params(self.configfhrefs, [gui[3] for gui in self.guis],self.paramdb,fname,self.explog.filehref,self.SingleSpecimen,non_settable=nonsettablecheckbox.get_active(),dcc=dcccheckbox.get_active(),gui=guicheckbox.get_active(),chx=chxcheckbox.get_active(),xlg=xlgcheckbox.get_active(),synced=syncedcheckbox.get_active())
            

            pass
        
        pass



    def createparamserver(self):
        if self.paramserver is None:
            self.paramserver=dc_dbus_paramserver(self.paramdb,self.checklists)
            pass
        pass
    

    def load_config(self,href):
        
        output=dc2_misc.load_config(href,self.paramdb,self.dc_gui_iohandlers,self.createparamserver)


        # turn off load config menu items
        # self.gladeobjdict["explogfileloadconfig"].set_sensitive(False)


        # turn on experiment and checklist menu items 
        self.gladeobjdict["explogguiopen"].set_sensitive(True)
        self.gladeobjdict["explogcustomchecklistopen"].set_sensitive(True)
        self.gladeobjdict["explogcentralchecklistopen"].set_sensitive(True)

        self.explog.lock_rw()
        try:
            if len(self.configfstrs)==0:
                # new element
                configel=self.explog.addelement(None,"dc:config")
                pass
            else :
                configel=self.explog.xpathsingle("dc:config[last()]")
                pass
            
            self.configfstrs.append(output)
            self.configfhrefs.append(href)

            # save hrefvalues for configfiles in dc:configfile tag
            configftag=self.explog.addelement(configel,"dc:configfile")
            href.xmlrepr(self.explog,configftag)
            self.explog.settext(configftag,output)
            pass
        finally:
            self.explog.unlock_rw()
            pass
        

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
        dc_initialize_widgets(gladeobjdict,self.guistate)
        
        
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
        if self.explog.filehref is None:
            return
        if self.checklistdbwin is None:

            self.checklistdbwin=checklistdbwin.checklistdbwin(self.explog.filehref,self.paramdb,"checklists",self.popupchecklist,[],True,True)
            self.checklistdbwin.show()
            pass
        else:
            self.checklistdbwin.liststoreupdate()
            self.checklistdbwin.present()
            pass
        pass

    def choose_opencentralchecklist(self,event):
        return self.choose_openchecklist(event,central=True)

    def choose_opencustomchecklist(self,event):
        return self.choose_openchecklist(event,central=False)

    
    def choose_openchecklist(self,event,central):
        
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

        if central:
            checklistchooser.set_current_folder(os.path.abspath(os.path.join(thisdir, '..', 'checklists')))
            pass
        else:
            if self.explog is not None:
                checklistchooser.set_current_folder(self.explog.getcontexthref().getpath())
                pass
            else:
                checklistchooser.set_current_folder(".")
                pass
            pass
        
        result=checklistchooser.run()
        fname=checklistchooser.get_filename()
        checklistchooser.destroy()
        
        if result==RESPONSE_OK:
            
            if central:
                # central checklists are always referred to
                # via absolute path
                
                #fname=canonicalize_path.canonicalize_path(fname)
                fnamehref=dcv.hrefvalue(pathname2url(fname))
                pass
            else:
                # custom checklists are always referred to
                # via relative path
                fnamehref=dcv.hrefvalue(pathname2url(canonicalize_path.relative_path_to(self.explog.getcontexthref().getpath(),fname)),self.explog.getcontexthref())
                pass
            
            
            self.addtochecklistmenu(fnamehref)
            self.open_checklist(fnamehref)

            pass
        
        pass


    def rebuildchecklistrealtimemenu(self,*junkargs):
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
            newitem=gtk.MenuItem(label=openchecklists[cnt].filehref.absurl(),use_underline=False)
            newitem.connect("activate",self.checklistmenu_realtime,openchecklists[cnt].filehref)
            self.gladeobjdict["explogchecklistmenu"].append(newitem)
            newitem.show()
            # sys.stderr.write("adding checklist menu item: %s\n" % (openchecklists[cnt].filename))
            pass
        pass

    def addtochecklistmenu(self,href):
        if href in self.checklistmenushortcuts: 
            # already present
            return

        Item=gtk.MenuItem(label=href.absurl(),use_underline=False)
        Item.set_name("prevchecklist_%s" % (href.absurl()))
        Item.connect("activate",self.checklistmenu_prevchecklist,href)
        self.checklistmenushortcuts[href]=Item
        
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

    def checklistmenu_realtime(self,event,href):

        self.popupchecklist(href)
        
        return True

    def checklistmenu_prevchecklist(self,event,href):
        self.open_checklist(href)
        
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
            (parentclobj,parenthref)=dc2_misc.searchforchecklist(parent)
            # sys.stderr.write("parentcanonfname=%s\n" % (parentcanonfname))

            #sys.stderr.write("open_checklist_parent: parentcanonfname=%s\n" % (parentcanonfname))

            if parentclobj is None:

                filepart=parenthref.get_bare_unquoted_filename()
                if posixpath.splitext(filepart)[1].lower=="plx" or posixpath.splitext(filepart)[1].lower=="plf":
                    self.open_plan(parenthref)
                else : 
                    self.open_checklist(parenthref)
                pass
            pass
        pass


    def open_checklist(self,href,inplace=False):

        
        
        if inplace:
            chklist=checklist.checklist(href,self.paramdb,datacollect_explog=self.explog,datacollect_explogwin=self,filledhref=href.leafless())
            pass
        else:
            chklist=checklist.checklist(href,self.paramdb,datacollect_explog=self.explog,datacollect_explogwin=self)
            pass

            
        self.checklists.append(chklist)
        
        chklist.dc_gui_init(self.guistate)

        #contextdir=os.path.split(self.explog.filename)[0]

        self.open_checklist_parent(chklist) # open our parent, if necessary

        checklistdb.addchecklisttoparamdb(chklist,self.paramdb,"checklists")
        checklistdb.newchecklistnotify(chklist,False)

        # checklistdb.checklistnotify(chklist,contextdir,self.paramdb,"checklists")
        # chklist.xmldoc.shouldbeunlocked()
        

        self.explog.shouldbeunlocked()
        
        win=chklist.getwindow()
        win.connect("delete-event",self.handle_checklist_close,chklist)
        win.show()
        
        return chklist


    def popupchecklist(self,href):
        # bring up checklist if it is open
        # otherwise open it
        (chklistobj,hrefobj)=dc2_misc.searchforchecklist(href)

        if chklistobj is None and not hrefobj.ismem():
            # open the checklist
            filepart=href.get_bare_unquoted_filename()
            if posixpath.splitext(filepart)[1].lower=="plx" or posixpath.splitext(filepart)[1].lower=="plf":
                return self.open_plan(href)
            else : 
                return self.open_checklist(href)
            pass
        elif chklistobj is not None:
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

        if self.explog is not None:
            checklistchooser.set_current_folder(self.explog.getcontexthref().getpath())
            pass
        else:
            checklistchooser.set_current_folder(".")
            pass
        
    
        result=checklistchooser.run()
        fname=checklistchooser.get_filename()
        checklistchooser.destroy()
        

        if result==RESPONSE_OK:
            # plans are always referred to
            # via relative path
            fnamehref=dcv.hrefvalue(pathname2url(canonicalize_path.relative_path_to(self.explog.getcontexthref().getpath(),fname)),self.explog.getcontexthref())
            
            self.open_plan(fnamehref)

            pass
        
        pass


    def open_plan(self,href):

        
        chklist=checklist.checklist(href,self.paramdb,datacollect_explog=self.explog,datacollect_explogwin=self)
            
        self.checklists.append(chklist)
        
        chklist.dc_gui_init(self.guistate)
        
        #contextdir=os.path.split(self.explog.filename)[0]

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

    def debug_pm(self,event):
        import pdb as pythondb

        pythondb.pm() # run debugger on most recent unhandled exception
        
        pass

    def hideaboutdialog(self,arg1,arg2=None):
        self.about_dialog.hide()
        return True


    pass
