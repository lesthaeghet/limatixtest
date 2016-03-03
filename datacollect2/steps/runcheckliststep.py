
# !!!*** Need to use new checklistdbwin to observe lists of subchecklists
# !!!*** Suggest more immediate way to reset private paramdb (perhaps restore and recreate?)
# !!!*** What to do with checklistdbwin when checklist is reset?

import os
import os.path
import sys
import subprocess
import tempfile

if "gi" in sys.modules:  # gtk3
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk as gtk
    from gi.repository import GObject as gobject
    pass
else : 
    # gtk2
    import gtk
    import gobject
    pass

import __main__

#sys.path.append("/home/sdh4/research/datacollect")
from lxml import etree
import dc_value
import paramdb2 as pdb
import xmldoc
import canonicalize_path
import checklistdb
import standalone_checklist

from dc_gtksupp import build_from_file
from dc_gtksupp import dc_initialize_widgets


__pychecker__="no-import no-argsused no-constattr"

if hasattr(gtk,"gtk_version") and (gtk.gtk_version[0] < 2 or (gtk.gtk_version[0]==2 and gtk.gtk_version[1] <= 24)):
    old_style_comboboxentry=True
    GtkComboBoxEntry=getattr(gtk,"ComboBoxEntry")
    pass
else: 
    # higher versions of gtk2, plus gtk3 (gtk3 uses gtk.MAJOR_VERSION and gtk.MINOR_VERSION instead of gtk.gtk_version)
    GtkComboBoxEntry=getattr(gtk,"ComboBoxText")
    old_style_comboboxentry=False
    pass

# list of dirs to search if checklistpath is blank
# non-absolute paths are relative to the path of the original (unfilled) checklist currently being run
#checklistdirs=['.','..','/databrowse/SOPs']


def href_exists(href):
    # Check to see if a referenced href exists.
    # Once we support http, etc. this will have to be rewritten

    hrefpath=href.getpath()
    return os.path.exists(hrefpath)


# gtk superclass should be first of multiple inheritances
class runcheckliststep(gtk.HBox):
    __gtype_name__="runcheckliststep"
    __gproperties__ = {

        #"checklistname": (gobject.TYPE_STRING,
        #               "Checklist name",
        #               "checklist name",
        #             "", # default value 
        #             gobject.PARAM_READWRITE), # flags

        #"checklistpath": (gobject.TYPE_PYOBJECT,
        #               "Checklist path",
        #               "checklist path; use default path if blank",
        #               #"", # default value 
        #               gobject.PARAM_READWRITE), # flags
        "standardchecklist": (gobject.TYPE_STRING,
                       "Standard checklist",
                       "Checklist will be copied into place",
                       "", # default value 
                       gobject.PARAM_READWRITE), # flags

        "customchecklist": (gobject.TYPE_STRING,
                       "Custom checklist",
                       "Checklist will be run in-place",
                       "", # default value 
                       gobject.PARAM_READWRITE), # flags
        


        "description": (gobject.TYPE_STRING,
                     "description of step",
                     "description of step",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags
        }
    #__proplist = ["checklistname","checklistpath","description"]
    __proplist = ["standardchecklist","customchecklist","description"]

    # set of properties to be transmitted as an hrefvalue with the checklist context as contexthref
    __dcvalue_href_properties=frozenset([ "standardchecklist",
                                          "customchecklist"])

    myprops=None

                      
    dc_gui_iohandlers=None
    paramdb=None
    gladeobjdict=None
    xmlpath=None

    statusreadout=None
    childntry=None  # GtkEntry child
    liststore=None
    status=None
    cell=None

    private_paramdb=None
    subchecklists_registered=None  # boolean: is private_paramdb["subchecklists"] registered with adddoc?

    
    # parentcl_dest=None # used for adddoc() and remdoc() -- now just use contextdir of parent checklist filename itself

    closed=None # flag that the checklist we are in has closed
    
    def __init__(self,checklist,step,xmlpath):
        # paramhandler.__init__(self,super(adjustparamstep,self),self.__proplist)# .__gproperties__)
        # gtk.HBox.__init__(self) # Not supposed to call superclass __init__ method, just gobject __init__ according to    http://www.pygtk.org/articles/subclassing-gobject/sub-classing-gobject-in-python.htm  
        gobject.GObject.__init__(self)
        self.checklist=checklist
        self.xmlpath=xmlpath
        self.subchecklists_registered=False
        
        self.myprops={}
        self.closed=False


        contextdir=None
        if self.checklist.xmldoc.filename is not None:
            contextdir=os.path.split(self.checklist.xmldoc.filename)[0]
            pass


        self.private_paramdb=pdb.paramdb(None) # private paramdb to store checklists that are started by this step
        self.private_paramdb.addparam("subchecklists",dc_value.xmltreevalue,build=lambda param: xmldoc.synced(param,tag_index_paths_override={"{http://thermal.cnde.iastate.edu/datacollect}checklist":"@{http://www.w3.org/1999/xlink}href"}),hide_from_meas=True)

            
        # register our private paramdb with checklistdb
        checklistdb.register_paramdb(self.private_paramdb,"subchecklists",contextdir,False)

        self.checklist.xmldoc.lock_ro()
        try:
            xmltag=self.checklist.xmldoc.restorepath(self.xmlpath)
            self.checklists_element_etxpath=canonicalize_path.getelementetxpath(self.checklist.xmldoc.doc,xmltag)+"/{http://thermal.cnde.iastate.edu/checklist}subchecklists"
            pass
        finally:
            self.checklist.xmldoc.unlock_ro()
            pass
            
        # our "dest" is contextdir -- location where we are saving
        self.parentcl_new_filename(self.checklist,None,None,None)  # call adddoc()

        self.checklist.addclosenotify(self.parentcl_close)
        self.checklist.addresetnotify(self.parentcl_reset)  # Note: this could be in resetchecklist() as an alternative
        self.checklist.addfilenamenotify(self.parentcl_new_filename)

        # NOTE: parallel removes must be in parentcl_close()
        checklistdb.requestopennotify(self.checklistopened)
        #checklistdb.requestfilenamenotify(self.update_status)
        #checklistdb.requestresetnotify(self.update_status)
        #checklistdb.requestdonenotify(self.update_status)

        

        (self.gladeobjdict,self.gladebuilder)=build_from_file(os.path.join(os.path.split(sys.modules[self.__module__].__file__)[0],"runcheckliststep.glade"))   
        
        self.set_property("description","")
        #self.set_property("checklistname","")
        #self.set_property("checklistpath","")
        self.set_property("standardchecklist","")
        self.set_property("customchecklist","")

        self.pack_start(self.gladeobjdict["runcheckliststep"],True,True,0)

        self.gladeobjdict["pushbutton"].connect("clicked",self.buttoncallback)
        self.gladeobjdict["printbutton"].connect("clicked",self.printcallback)
        self.gladeobjdict["step_descr_label"].set_selectable(True)

        #if self.checklist.datacollect_explogwin is not None:
        #    # in datacollect... can monitor sub-checklist progress
        if True:
            vbox=gtk.VBox()
            statuslabel=gtk.Label(" Status: ")
            self.gladeobjdict["runcheckliststep"].pack_start(statuslabel,False,False,0)

            self.statusreadout=GtkComboBoxEntry()
            if old_style_comboboxentry: 
                # need to manually create liststore,  & cell
                # We are creating three columns in the list store
                #   0 - Filename
                #   1 - Text Description of Completion Status
                #   2 - Foreground Color
                # This is a work around for a strange issue that prevents
                # setting the color of the field set by set_text_column and
                # getting a callback when it is used.
                self.liststore=gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
                self.statusreadout.set_model(self.liststore)
                self.cell=gtk.CellRendererText()
                self.statusreadout.set_text_column(0)
                # self.statusreadout.set_entry_text_column(0) Not Actually Needed
                self.statusreadout.pack_start(self.cell, False)
                self.statusreadout.add_attribute(self.cell,'text',1)
                self.statusreadout.add_attribute(self.cell,'foreground',2)
                self.statusreadout.set_active(-1)
                pass
            else : 
                self.statusreadout.set_entry_text_column(0)
                pass
            
            vbox.pack_start(self.statusreadout,True,False,0)
            self.gladeobjdict["runcheckliststep"].pack_start(vbox,True,True,0)
            self.statusreadout.connect('changed',self.changedcallback)
            pass

        # find any of our sub-checklists that are already open, and see if they are ours, so we can be notified when they reset, etc. 
        # with checklistdb

        if self.checklist.xmldoc.filename is not None:
            contextdir=os.path.split(self.checklist.xmldoc.filename)[0]

            subchecklists=checklistdb.getchecklists(contextdir,self.private_paramdb,"subchecklists",None)
            # go through our subchecklists
            for subchecklist in subchecklists:
                if subchecklist.checklist is None:
                    continue
                # use same routine we call when a checklist is opened
                self.checklistopened(subchecklist.checklist)
                pass
            pass
            
            
    

        pass

    def set_readonly(self,readonly):
        # NOTE: checkliststep data is not locked when the step is checked,
        # only when the entire checklist is marked as readonly
        if readonly:
            if self.subchecklists_registered:

                self.private_paramdb["subchecklists"].controller.remdoc(self.checklist.xmldoc,xmlpath=None,ETxmlpath=self.checklists_element_etxpath)
                self.subchecklists_registered=False
                pass
            pass
        else :
            if not(self.subchecklists_registered) and self.checklist.xmldoc.filename is not None:
                self.private_paramdb["subchecklists"].controller.adddoc(self.checklist.xmldoc,xmlpath=None,ETxmlpath=self.checklists_element_etxpath)
                self.subchecklists_registered=True
                pass
            pass
        pass
    
    
    def checklistopened(self,possiblesubchecklist):
        # This is called when ANY checklist or plan is opened. 
        # We have to detect if it is one of ours and call addresetnotify
        # addfilenamenotify, adddonenotify 
        # so that we will be notified of updates

        if self.checklist.xmldoc.filename is None:
            # Not allowed to add sub-checklists until we have a name
            return
        
        contextdir=os.path.split(self.checklist.xmldoc.filename)[0]

        checklistsdoc=self.private_paramdb["subchecklists"].dcvalue.get_xmldoc(nsmap={"dc": "http://thermal.cnde.iastate.edu/datacollect","xlink":"http://www.w3.org/1999/xlink"},contextdir=contextdir)  # should be a <dc:checklists> tag containing <dc:checklist> tags. 
        
        if checklistdb.checklist_in_param(possiblesubchecklist.get_filehref(),checklistsdoc):
            

            possiblesubchecklist.addresetnotifyifneeded(self.subreset)  # This must be after checklistnotify (above) so that our reset routine gets called after checklistdb's, so that we see the result of the reset on the checklistdb
            possiblesubchecklist.addfilenamenotifyifneeded(self.gotsubchecklist)
            possiblesubchecklist.adddonenotifyifneeded(self.subdone)


            pass
        pass


    
    def do_set_property(self,property,value):
        # print "set_property(%s,%s)" % (property.name,str(value))
        if property.name=="checklistname":
            #self.myprops[property.name]=value
            #self.gladeobjdict["pushbutton"].set_property("label","Open %s" % (value))
            #self.gladeobjdict["printbutton"].set_property("label","Print %s" % (value))
            pass
        elif property.name=="checklistpath":
            #self.myprops[property.name]=value
            pass
        elif property.name=="standardchecklist":
            self.myprops[property.name]=value
            if len(value) > 0:
                self.gladeobjdict["pushbutton"].set_property("label","Open %s" % (os.path.split(value)[1]))
                self.gladeobjdict["printbutton"].set_property("label","Print %s" % (os.path.split(value)[1]))
                pass
            pass
        elif property.name=="customchecklist":
            self.myprops[property.name]=value
            if len(value) > 0:
                self.gladeobjdict["pushbutton"].set_property("label","Open %s" % (os.path.split(value)[1]))
                self.gladeobjdict["printbutton"].set_property("label","Print %s" % (os.path.split(value)[1]))
                pass
            
            pass
        
        elif property.name=="description":
            self.myprops[property.name]=value
            #self.gladeobjdict["step_descr_label"].set_property("label",value)  
            self.gladeobjdict["step_descr_label"].set_markup(value)  
            pass
        else :
            raise IndexError("Bad property name %s" % (property.name))
        pass

    def do_get_property(self,property,value):
        return self.myprops[property.name]
    
    def dc_gui_init(self,guistate):
        # need next line if subclassing a dc_gui class
        # super(dg_readout).__dc_gui_init(self,io)
        
        
        self.paramdb=guistate.paramdb
        self.dc_gui_iohandlers=guistate.iohandlers

        dc_initialize_widgets(self.gladeobjdict,guistate)

        if self.statusreadout is not None:

            if hasattr(self.statusreadout,"child"):
                self.childntry=self.statusreadout.child
                pass
            else :
                self.childntry=self.statusreadout.get_child()
                # print "self.get_children()=",self.get_children()
                pass

            self.childntry.set_editable(False)
            pass

        self.update_status()

        pass

    def parentcl_new_filename(self,checklist,origfilename,name,oldfilename):
        #self.parentcl_dest=dest

        if oldfilename is not None and self.subchecklists_registered:
            self.private_paramdb["subchecklists"].controller.remdoc(self.checklist.xmldoc,xmlpath=None,ETxmlpath=self.checklists_element_etxpath)
            pass
        self.subchecklists_registered=False

        if self.checklist.xmldoc.filename is not None and not self.checklist.readonly: 


            # our "dest" is contextdir -- location where we are saving
            self.private_paramdb["subchecklists"].controller.adddoc(self.checklist.xmldoc,xmlpath=None,ETxmlpath=self.checklists_element_etxpath)
            self.subchecklists_registered=True
            # register remdoc with checklist close and with checklist reset. Will also need to adddoc when filename is set. 
            pass

  
        # re-register our private paramdb with checklistdb with the new contextdir
        contextdir=None
        if self.checklist.xmldoc.filename is not None:
            contextdir=os.path.split(self.checklist.xmldoc.filename)[0]
            pass
            
        checklistdb.register_paramdb(self.private_paramdb,"subchecklists",contextdir,False)
            

        pass


    def parentcl_close(self,checklist):
        # We go away because our parent checklist is closed. 
        # ... must remdoc our private_paramdb
        self.closed=True

        # go through children and remove notifies
        contextdir=self.checklist.xmldoc.getcontextdir()

        checklists=checklistdb.getchecklists(contextdir,self.private_paramdb,"subchecklists")
        for checklistentry in checklists:
            if checklistentry.checklist is not None:
                checklistentry.checklist.removeresetnotify(self.subreset)
                checklistentry.checklist.removefilenamenotify(self.gotsubchecklist)
                checklistentry.checklist.removedonenotify(self.subdone)
                pass
            pass

        # unregister our private_paramdb
        checklistdb.unregister_paramdb(self.private_paramdb,"subchecklists",None,False)
        
        
        #self.checklist.xmldoc.lock_rw()
        # Don't think we actually need to lock here... not doing any writing
        #try:
        #    # our "dest" is contextdir -- location where we are saving

        if self.checklist.xmldoc.filename is not None and self.subchecklists_registered:
            # only adddoc'd if we have a filename, because we needed a filename to have a context location
            self.private_paramdb["subchecklists"].controller.remdoc(self.checklist.xmldoc,xmlpath=None,ETxmlpath=self.checklists_element_etxpath)
            
            pass
        self.subchecklists_registered=False
        #finally:
        #    self.checklist.xmldoc.unlock_rw()
        #    pass
        # clear paramdb entry
        self.private_paramdb["subchecklists"].requestvalstr_sync("")
        del self.private_paramdb["subchecklists"] # flag to checklistdb that this paramdb is no longer valid
        del self.private_paramdb

        # remove our checklistdb notifies
        checklistdb.removeopennotify(self.checklistopened)
        #checklistdb.removefilenamenotify(self.update_status)
        #checklistdb.removeresetnotify(self.update_status)
        #checklistdb.removedonenotify(self.update_status)

        pass

    def parentcl_reset(self,checklist,oldfilename):
        # don't actually need to remdoc(), because we would just need to add it back right away.
        # and this way, the requestvalstr_sync() properly clears it out. 

        #self.checklist.xmldoc.lock_rw()
        #try:
        #    self.private_paramdb["subchecklists"].controller.remdoc(self.checklist.xmldoc,xmlpath=None,ETxmlpath=self.checklists_element_etxpath)
        #    pass
        #finally:
        #    self.checklist.xmldoc.unlock_rw()
        #    pass



        # clear paramdb entry
        #import pdb as pythondb
        #pythondb.set_trace()
        if oldfilename is not None:
            subchecklistdb=self.private_paramdb["subchecklists"].dcvalue.get_xmldoc(contextdir=os.path.split(oldfilename)[0])
            # remove all elements
        
            subchecklistdb.remelements(subchecklistdb.xpath("*"))

            # sys.stderr.write("subchecklistdb=%s\n" % (etree.tostring(subchecklistdb.doc,pretty_print=True)))

            # apply updated (now empty) list of checklists
            self.private_paramdb["subchecklists"].requestval_sync(dc_value.xmltreevalue(subchecklistdb))
            pass
        
        self.update_status()
        pass


    def resetchecklist(self):

        

        pass

    def isconsistent(self,inconsistentlist):
        consistent=True
        for key in self.gladeobjdict:
            if hasattr(self.gladeobjdict[key],"isconsistent"):
                consistent=consistent and self.gladeobjdict[key].isconsistent(inconsistentlist)
                pass
            pass
        return consistent


    # most gotsubchecklist functionality now covered by checklistdb...
    
    def gotsubchecklist(self,checklistobj,origfilename,fname,oldfilename):
        self.update_status()
        pass

    # def gotsubchecklist(self,checklistobj,origfilename,dest,fname):
    #    # This is called when the sub-checklist gets a filename
    #    # record the sub-checklist name in our element
    #
    #    self.checklist.xmldoc.lock_rw()
    #    try : 
    #        xmltag=self.checklist.xmldoc.restorepath(self.xmlpath)
    #        subchecklists=self.checklist.xmldoc.findcontext(xmltag,"chx:subchecklists")
    #        if subchecklists is None:
    #            subchecklists=self.checklist.xmldoc.addelement(xmltag,"chx:subchecklists")
    #            pass
    #        
    #        fname = os.path.basename(fname)
    #        check = self.checklist.xmldoc.xpath("chx:subchecklist[text()='%s']" % (fname), contextnode=subchecklists)
    #
    #        if len(check) == 0:
    #            subchecklist=self.checklist.xmldoc.addelement(subchecklists,"chx:subchecklist")
    #            self.checklist.xmldoc.setattr(subchecklist,"origfilename",origfilename)
    #            self.checklist.xmldoc.setattr(subchecklist,"done",'false')
    #            if isinstance(dest,basestring):
    #                path = dest
    #            else:
    #                path = checklistobj.xmldoc.gettext(dest)
    #            self.checklist.xmldoc.setattr(subchecklist,"dest",path)
    #            self.checklist.xmldoc.settext(subchecklist,fname)
    #        pass
    #    except:
    #        raise
    #    finally:
    #        self.checklist.xmldoc.unlock_rw()
    #        pass
    #
    #    self.update_status()
    #
    #    # self.checklist.xmldoc.flush()
    #
    #    pass
        
    def update_status(self):
        # self.checklist.xmldoc.lock_ro()
        # try:
        # get our sub-checklists
        # import pdb as pythondb
        #try:
        if self.closed:
            return

        if self.statusreadout is None:
            return  # no status readout in bare checklist mode

        contextdir=self.checklist.xmldoc.getcontextdir()

        checklists=checklistdb.getchecklists(contextdir,self.private_paramdb,"subchecklists",None)
        # sys.stderr.write("checklists=%s\n" % (str(checklists)))
        #except:
        #    pythondb.post_mortem()

        numstarted=len(checklists)
        numcompleted=len([checklistentry for checklistentry in checklists if checklistentry.is_done])
        
        # xmltag = self.checklist.xmldoc.restorepath(self.xmlpath)
        # self.numstarted = len(self.checklist.xmldoc.xpath('chx:subchecklists/dc:checklist', contextnode=xmltag))
        # self.numcompleted = len(self.checklist.xmldoc.xpath('chx:subchecklists/dc:checklist[@done="true"]', contextnode=xmltag))
        # checklists = self.checklist.xmldoc.xpath('chx:subchecklists/chx:subchecklist', contextnode=xmltag)
        # Create New List Store
        self.liststore=gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.statusreadout.set_model(self.liststore)
        
        #for item in checklists:
        #    if self.checklist.xmldoc.getattr(item, "done") == "true":
        #        self.liststore.append([unicode(self.checklist.xmldoc.gettext(item)), ' (Complete)', 'green'])
        #    else:
        #        self.liststore.append([unicode(self.checklist.xmldoc.gettext(item)), ' (Incomplete)', 'red'])
        
        for checklistentry in checklists:
            name=checklistentry.filename
            if name is None:
                name=checklistentry.canonicalpath
                pass
            if checklistentry.is_done: 
                self.liststore.append([name, ' (Complete)', 'green'])
            else:
                self.liststore.append([name, ' (Incomplete)', 'red'])
                pass
            pass
        
            # except:
            # raise
        # finally:
        #    self.checklist.xmldoc.unlock_ro()
        self.status="%d start/%d done" % (numstarted,numcompleted)
        
        if self.childntry is not None:
            self.childntry.set_text(self.status)

        pass


    def subdone(self,checklist,oldfilename):
        # self.checklist.xmldoc.lock_rw()
        # try : 
        #    xmltag = self.checklist.xmldoc.restorepath(self.xmlpath)
        #    subchecklists = self.checklist.xmldoc.findcontext(xmltag,"chx:subchecklists")
        #    # Must Use XPath To Check And Ensure We Only Have One Element
        #    subchecklist = self.checklist.xmldoc.xpath("chx:subchecklist[text()='%s']" % (checklist.chklistfile), contextnode=subchecklists)
        #    if len(subchecklist) != 1:
        #        raise Exception("Multiple Sub Checklists Exist With The Same Filename")
        #    subchecklist = subchecklist[0]
        #    self.checklist.xmldoc.setattr(subchecklist,"done","true")
        #    pass
        #except:
        #    raise
        #finally:
        #    self.checklist.xmldoc.unlock_rw()
        #    pass
        self.update_status()
        pass
    
    def subreset(self,checklist,oldfilename):
        # sys.stderr.write("subreset\n")
        self.update_status()
        pass

    def changedcallback(self,*args):
        
        checklistfile = self.childntry.get_text()
        #print checklistfile
        # dest = ""
        if checklistfile == self.status:
            # Not Actually Changed
            pass
        else:
            # self.checklist.xmldoc.lock_ro()
            # try:
            subchecklist=[ entry for entry in checklistdb.getchecklists(os.path.split(self.checklist.xmldoc.filename)[0],self.private_paramdb,"subchecklists",None) if entry.filename ==checklistfile or entry.canonicalpath==checklistfile]


            #    xmltag = self.checklist.xmldoc.restorepath(self.xmlpath)
            #    subchecklists = self.checklist.xmldoc.findcontext(xmltag,"chx:subchecklists")               
            #    subchecklist = self.checklist.xmldoc.xpath("chx:subchecklist[text()='%s']" % (checklistfile), contextnode=subchecklists)
            
            if len(subchecklist) > 1:
                raise Exception("Multiple Sub Checklists Exist With The Same Filename")

            if len(subchecklist) > 1:
                raise Exception("Sub Checklists Filename %s not found" % (checklistfile))
            subchecklist = subchecklist[0]
            # except:
            #    raise
            #finally:
            #    self.checklist.xmldoc.unlock_ro()
            #    pass
            # dest=str(self.paramdb["dest"].dcvalue)
            # subchecklist=self.checklist.datacollect_explogwin.popupchecklist(os.path.join(dest,checklistfile))
            if self.checklist.datacollect_explogwin is not None:
                # datacollect mode
                subchecklistobj=self.checklist.datacollect_explogwin.popupchecklist(subchecklist.canonicalpath)
                pass
            else:
                standalone_checklist.popupchecklist(subchecklist.canonicalpath,self.paramdb,self.dc_gui_iohandlers)
                pass
            ## notify checklist with our private paramdb
            #contextdir=os.path.split(self.checklist.xmldoc.filename)[0]
            #checklistdb.checklistnotify(subchecklistobj,contextdir,self.private_paramdb,"subchecklists")
            #
            #subchecklistobj.addresetnotifyifneeded(self.subreset)  # This must be after checklistnotify (above) so that our reset routine gets called after checklistdb's, so that we see the result of the reset on the checklistdb
            #subchecklistobj.addfilenamenotifyifneeded(self.gotsubchecklist)
            #subchecklistobj.adddonenotifyifneeded(self.subdone)

            self.update_status()
        pass
    

    def buttoncallback(self,*args):
        checklistfile=None
        inplace=False

        if self.checklist.xmldoc.filename is None:
            nofiledialog=gtk.MessageDialog(type=gtk.MESSAGE_ERROR,buttons=gtk.BUTTONS_OK)
            nofiledialog.set_markup("Error: This checklist needs a filename before a subchecklist can be opened. Please use \"Save\" button to give it a filename (if applicable).")
            nofiledialog.run()
            nofiledialog.destroy()
            return

        if self.myprops["customchecklist"] != "":
            # use a custom checklist... destdir is the same 
            # location as the custom checklist
            checklisthref=dc_value.hrefvalue(self.myprops["customchecklist"],self.checklist.getcontexthref())
            inplace=True
            pass
        elif self.myprops["standardchecklist"] != "":
            # use a standard checklist... destdir is the same 
            # location as our checklist
            checklisthref=dc_value.hrefvalue(self.myprops["standardchecklist"],self.checklist.getcontexthref())

            ## search path for checklistfile
            #if not os.path.isabs(checklistfile):
            #    if os.path.exists(os.path.join(destdir,checklistfile)):
            #        checklistfile=os.path.join(destdir,checklistfile)
            #        pass
            #    else: 
            #        for checklistdir in checklistdirs:
            #            if os.path.exists(os.path.join(checklistdir,checklistfile)):
            #                checklistfile=os.path.join(checklistdir,checklistfile)
            #                break
            #            pass
            #        pass
            #    pass
            
            
            pass

            

        #if self.myprops["checklistpath"]=="":        
        #    reldir=os.path.split(self.checklist.origfilename)[0]
        #    for chklistdir in checklistdirs:
        #        if not os.path.isabs(chklistdir):
        #            checklistdir=os.path.join(reldir,chklistdir)
        #            pass
        #        if os.path.exists(os.path.join(checklistdir,self.myprops["checklistname"])):
        #            checklistfile=os.path.join(checklistdir,self.myprops["checklistname"])
        #            break
        #        pass
        #
        #    pass
        #else :
        #    checklistfile=os.path.join(self.myprops["checklistpath"],self.myprops["checklistname"])
        #    pass
        
        if checklisthref is None or not href_exists(checklisthref):
            nofiledialog=gtk.MessageDialog(type=gtk.MESSAGE_ERROR,buttons=gtk.BUTTONS_OK)
            nofiledialog.set_markup("Error: Requested checklist file %s not found" % (str(checklisthref)))
            nofiledialog.run()
            nofiledialog.destroy()
            return
        
        
        if self.checklist.datacollect_explogwin is not None:
            # Using datacollect... have datacollect open the checklist
            #dest=str(self.paramdb["dest"].dcvalue)
            
            subchecklist=self.checklist.datacollect_explogwin.open_checklist(checklistfile,inplace=inplace)
            # set parent attribute
            subchecklist.set_parent(self.checklist.xmldoc.get_filehref())
            checklistdb.addchecklisttoparamdb(subchecklist,self.private_paramdb,"subchecklists")

            

            # register checklist with our private paramdb in checklistdb
            #contextdir=os.path.split(self.checklist.xmldoc.filename)[0]
            #import pdb as pythondb
            #pythondb.set_trace()
            #checklistdb.checklistnotify(subchecklist,contextdir,self.private_paramdb,"subchecklists")

            # other notifies
            subchecklist.addresetnotifyifneeded(self.subreset)  # This must be after checklistnotify (above) so that our reset routine gets called after checklistdb's, so that we see the result of the reset on the checklistdb
            subchecklist.addfilenamenotifyifneeded(self.gotsubchecklist)
            subchecklist.adddonenotifyifneeded(self.subdone)
            self.update_status()
            pass
        else :
            # run new copy of the same dg_checklist binary
            
            #checklist_binary=os.path.abspath(getattr(__main__,"__file__")) # use getattr so pychecker doesn't complain about __file__
            #
            #params=[checklist_binary]

            #for configfile in getattr(__main__,"configfiles"):
            #    params.append('-f')
            #    params.append(os.path.abspath(configfile))
            #    pass
            
            #params.append(checklistfile)
            #
            #subprocess.Popen(params)



            subchecklist=standalone_checklist.open_checklist(checklisthref,self.paramdb,self.dc_gui_iohandlers)
            # set parent attribute

            subchecklist.set_parent(self.checklist.xmldoc.get_filehref())

            # register checklist with our private paramdb in checklistdb
            checklistdb.addchecklisttoparamdb(subchecklist,self.private_paramdb,"subchecklists")
            
            

            #import pdb as pythondb
            #pythondb.set_trace()
            #checklistdb.checklistnotify(subchecklist,contextdir,self.private_paramdb,"subchecklists")

            # other notifies
            subchecklist.addresetnotifyifneeded(self.subreset)  # This must be after checklistnotify (above) so that our reset routine gets called after checklistdb's, so that we see the result of the reset on the checklistdb
            subchecklist.addfilenamenotifyifneeded(self.gotsubchecklist)
            subchecklist.adddonenotifyifneeded(self.subdone)
            self.update_status()
            
            pass

        pass


    def printcallback(self,*args):
        assert(0)
        ###**** Needs updating
        #self.update_status()
        checklisthref=None
        if self.myprops["checklistpath"]=="":        
            reldir=os.path.split(self.checklist.origfilename)[0]
            for chklistdir in checklistdirs:
                if not os.path.isabs(chklistdir):
                    checklistdir=os.path.join(reldir,chklistdir)
                    pass
                if os.path.exists(os.path.join(checklistdir,self.myprops["checklistname"])):
                    checklistfile=os.path.join(checklistdir,self.myprops["checklistname"])
                    break
                pass

            pass
        else :
            checklistfile=os.path.join(self.myprops["checklistpath"],self.myprops["checklistname"])
            pass

        if checklistfile is None or not os.path.exists(checklistfile):
            nofiledialog=gtk.MessageDialog(type=gtk.MESSAGE_ERROR,buttons=gtk.BUTTONS_OK)
            nofiledialog.set_markup("Error: Requested checklist file %s not found" % (checklistfile))
            nofiledialog.run()
            nofiledialog.destroy()
            return
        
        ## Change Direcotry to Temp Directory
        ###***!!! Shouldn't ever call os.getcwd except in a subprocess context!!!
        #cwd = os.getcwd()
        #tmpdir = tempfile.mkdtemp()
        #os.chdir(tmpdir)

        # Get Specimen, Perfby, Date, Dest from Current Checklist
        specimen = str(self.checklist.paramdb["specimen"].dcvalue)
        perfby = str(self.checklist.paramdb["perfby"].dcvalue)
        date = str(self.checklist.paramdb["date"].dcvalue)
        dest = str(self.checklist.private_paramdb["dest"].dcvalue)

        # Run chx2pdf
        subprocess.check_call(['/usr/local/bin/chx2pdf', checklistfile, specimen, perfby, date, dest], stdout=sys.stdout.fileno(), stderr=sys.stderr.fileno())

        # Check for Output
        outfile = os.path.join(tmpdir, os.path.splitext(os.path.basename(checklistfile))[0] + '.pdf')

        # Trigger Launch of xdg-open
        if os.path.exists(outfile):
            subprocess.Popen(['xdg-open', outfile])
        else:
            raise IOError("Error Opening PDF File %s" % outfile)

        # Change Directory Back
        os.chdir(cwd)

        pass   

    pass


gobject.type_register(runcheckliststep)  # required since we are defining new properties/signals
