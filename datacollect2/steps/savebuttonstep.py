# Step with a savebutton for saving a specified datacollect param
# with the perform_save() method
#
# Works only in datacollect mode. Must be late enough 
# in the checklist that checklist filename has already been determined


import os
import sys
import posixpath

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

import dg_file as dgf
import dg_comm as dgc
import paramdb2 as pdb

import dc_value
import dc2_misc

from buttonreadoutstep import buttonreadoutstep
import canonicalize_path

class simpleobj:
    name=None
    pass

__pychecker__="no-import no-argsused"

# gtk superclass should be first of multiple inheritances
class savebuttonstep(buttonreadoutstep):
    __gtype_name__="savebuttonstep"
    __gproperties__ = {

        "paramname": (gobject.TYPE_STRING,
                  "parameter",
                  "datacollect parameter to show and to use for save. The named parameter should store an hrefvalue with a controller that supports the perform_save method. Only this parameter is shown in the readout (the others are invisible)",
                  "", # default value 
                gobject.PARAM_READWRITE), # flags
        "paramname2": (gobject.TYPE_STRING,
                  "second parameter",
                  "second datacollect parameter to show and to use for save. The named parameter should store an hrefvalue with a controller that supports the perform_save method",
                  "", # default value 
                gobject.PARAM_READWRITE), # flags
        "paramname3": (gobject.TYPE_STRING,
                  "third parameter",
                  "third datacollect parameter to show and to use for save. The named parameter should store an hrefvalue with a controller that supports the perform_save method",
                  "", # default value 
                gobject.PARAM_READWRITE), # flags

        "intermediate": (gobject.TYPE_BOOLEAN,
                  "intermediate parameter setting",
                  "Intermediate parameter setting: Intermediate step parameters are saved to the XML checklist file when the step is checked, and the widgets freeze when the checklist is read-only or once the checkbox ix checked",
                   False, # default value 
                  gobject.PARAM_READWRITE), # flags

        # also "buttonlabel" and "description" properties
        # inherited from buttonreadoutstep
        
        }

    __dcvalue_xml_properties={} # dictionary by property of dc_value class to be transmitted as a serialized  xmldoc
    __dcvalue_href_properties=frozenset([]) # set of properties to be transmitted as an hrefvalue with the checklist context as contexthref

    paramnotify=None
    paramnotify2=None
    paramnotify3=None
    
    # self.paramdb and self.dc_gui_io defined by buttonreadoutstep, set by buttonreadoutstep's dc_gui_init()

                      
    def __init__(self,checklist,step,xmlpath):
        buttonreadoutstep.__init__(self,checklist,step,xmlpath)
        # paramhandler.__init__(self,super(adjustparamstep,self),self.__proplist)# .__gproperties__)
        # gobject.GObject.__init__(self)

        self.myprops["paramname"]=""
        self.myprops["paramname2"]=""
        self.myprops["paramname3"]=""
        self.myprops["intermediate"]=False
        self.set_property("readoutparam",self.myprops["paramname"])
        self.set_property("buttonlabel","Save DGS Snapshot")
        self.set_property("intermediate",False)

        pass    

    def destroystep(self):
        if len(self.myprops["paramname"]) > 0:
            self.paramdb.remnotify(self.myprops["paramname"],self.paramnotify)
            pass
        if len(self.myprops["paramname2"]) > 0:
            self.paramdb.remnotify(self.myprops["paramname2"],self.paramnotify2)
            pass
        if len(self.myprops["paramname3"]) > 0:
            self.paramdb.remnotify(self.myprops["paramname3"],self.paramnotify3)
            pass
        self.paramnotify=None
        self.paramnotify2=None
        self.paramnotify3=None
        pass


    def dc_gui_init(self,guistate):
        # Set up notifications...

        # call superclass
        buttonreadoutstep.dc_gui_init(self,guistate)

        if len(self.myprops["paramname"]) > 0:
            self.paramnotify=self.paramdb.addnotify(self.myprops["paramname"],self.changedcallback,pdb.param.NOTIFY_NEWVALUE)
            pass
        if len(self.myprops["paramname2"]) > 0:
            self.paramnotify2=self.paramdb.addnotify(self.myprops["paramname2"],self.changedcallback,pdb.param.NOTIFY_NEWVALUE)
            pass
        if len(self.myprops["paramname3"]) > 0:
            self.paramnotify3=self.paramdb.addnotify(self.myprops["paramname3"],self.changedcallback,pdb.param.NOTIFY_NEWVALUE)
            pass
        pass

    def do_set_property(self,gproperty,value):
        
        #print "set_property(%s,%s)" % (gproperty.name,str(value))
        if gproperty.name=="paramname":
            # print "paramname=%s" % value
            self.myprops["paramname"]=value
            
            #import pdb as pythondb 
            #pythondb.set_trace()
            nameobj=simpleobj()
            nameobj.name="readoutparam"
            buttonreadoutstep.do_set_property(self,nameobj,value)
            pass
        elif gproperty.name=="paramname2":
            # print "paramname=%s" % value
            self.myprops["paramname2"]=value
            pass
        elif gproperty.name=="paramname3":
            # print "paramname=%s" % value
            self.myprops["paramname3"]=value
            pass
        elif gproperty.name=="intermediate":
            # print "paramname=%s" % value
            self.myprops["intermediate"]=value
            pass
        else :
            #sys.stderr.write("calling buttonreadoutstep set_property()\n")
            buttonreadoutstep.do_set_property(self,gproperty,value)
            pass
        pass

    def do_get_property(self,property):
        if property.name == "paramname":
            return self.myprops["paramname"]
        if property.name == "paramname2":
            return self.myprops["paramname2"]
        if property.name == "paramname3":
            return self.myprops["paramname3"]
        if property.name == "intermediate":
            return self.myprops["intermediate"]
        return buttonreadoutstep.do_get_property(self,property)
    

    def do_save_param_datacollect(self,paramname):
        if paramname is None or paramname=="":
            return
        
        desthref=self.paramdb["dest"].dcvalue

        # suggest a filename
        chklistfilename=self.checklist.xmldoc.filehref.get_bare_unquoted_filename()
        chklistbasename=posixpath.splitext(chklistfilename)[0]
        filename="%s_%s.%s" % (chklistbasename,paramname,self.paramdb[paramname].save_extension)
        savefilehref=dc_value.hrefvalue(quote(filename),contexthref=desthref)

        #import pdb as pythondb
        #pythondb.set_trace()
        
            
        if (os.path.exists(savefilehref.getpath())) :
            if hasattr(gtk,"MessageType") and hasattr(gtk.MessageType,"WARNING"):
                # gtk3
                existsdialog=gtk.MessageDialog(type=gtk.MessageType.ERROR,buttons=gtk.ButtonsType.NONE)
                pass
            else : 
                existsdialog=gtk.MessageDialog(type=gtk.MESSAGE_ERROR,buttons=gtk.BUTTONS_NONE)
                pass
                    
            existsdialog.set_markup("Error: File %s exists." % (savefilehref.getpath()))
            existsdialog.add_button("Overwrite",1)
            existsdialog.add_button("Cancel operation",0)
            
            existsdialogval=existsdialog.run()
            
            existsdialog.destroy()

            if existsdialogval==0:
                # Cancel
                return

            pass

        #import pdb as pythondb
        #pythondb.set_trace()

        self.paramdb[paramname].perform_save(savefilehref)


        pass

    def do_save_param_nondatacollect(self,paramname,desthref):

        defname=""
        
        if self.checklist.ok_set_filename():
            defname=os.path.splitext(self.checklist.requestedfilename())[0]+self.paramdb[self.myprops["paramname"]].save_extension
            
            pass
        
        
        Chooser=gtk.FileChooserDialog(title="Save as...",action=gtk.FILE_CHOOSER_ACTION_SAVE,buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_SAVE,gtk.RESPONSE_OK))
        Chooser.set_modal(True)
        Chooser.set_current_name(defname)
        Chooser.set_current_folder(desthref.getpath())
        Chooser.set_do_overwrite_confirmation(True)
        
        datafilter=gtk.FileFilter()
        datafilter.set_name(self.paramdb[self.myprops["paramname"]].save_extension.upper() + " files")
        datafilter.add_pattern("*." + self.paramdb[self.myprops["paramname"]].save_extension)
        Chooser.add_filter(datafilter)
        
        response=Chooser.run()
        outfilename=Chooser.get_filename()
        Chooser.hide()
        Chooser.destroy()
        
        if response != gtk.RESPONSE_OK:
            return 
        
        # datafilename should be relative to desthref
        save_relpath=canonicalize_path.relative_path_to(desthref.getpath(),outfilename)
        
        
        savefilehref=dc_value.hrefvalue(pathname2url(save_relpath),contexthref=desthref)
        
        
        self.paramdb[paramname].perform_save(savefilehref)

        
        pass


    def buttoncallback(self,*args):
        if self.checklist.readonly:
            return
        if self.is_fixed():  # determined by buttonreadoutstep superclass
            return
        #if not self.checklist.checknotcurrent():
        #    return
        
        
        # In datacollectmode the checklist autosaves once enough steps
        # have been checked to determine the filename, so we have to be
        # past this point
        if self.checklist.datacollectmode:
            if self.checklist.xmldoc.filehref is None:
                raise ValueError("Save button step is too early -- checklist not yet saved to a file, so impossible to determine filename")

            for paramname in [self.myprops["paramname"],self.myprops["paramname2"],self.myprops["paramname3"]]:
                self.do_save_param_datacollect(paramname)
                pass

            pass
        else :
            # not datacollect mode...
            # determine filename automatically if possible, but ask user

            self.checklist.xmldoc.lock_ro()
            try :             
                destelement=self.checklist.xmldoc.xpathsingle("chx:dest")
                desthref=dc_value.hrefvalue.fromxml(self.checklist.xmldoc,destelement)
            finally:
                self.checklist.xmldoc.unlock_ro()
                pass
            

            for paramname in [self.myprops["paramname"],self.myprops["paramname2"],self.myprops["paramname3"]]:
                self.do_save_param_nondatacollect(paramname,desthref)
                pass
            pass

        #self.update_xml()
        #self.set_fixed()
        #self.setbuttonbgcolor("green") # indicate that we have been pushed
        
        pass

    def is_fixed(self): # note overridden by savebuttonstep
        if self.paramdb is None: 
            return True # fixed during initialization

        # param readout is NEVER fixed when parameter intermediate is False
        # ... non-intermediate params are saved in the experiment log, 
        # not in the checklist
        if not self.myprops["intermediate"]:
            return False

        # param readout is fixed when checklist is marked as
        # readonly or when checkbox is checked. 
        return self.checklist.readonly or self.step.gladeobjdict["checkbutton"].get_property("active")


    # override set_fixed() so underlying widget is ALWAYS fixed
    def set_fixed(self):
        fixed=self.is_fixed()
        (value,displayfmt)=self.value_from_xml()
        # sys.stderr.write("savebuttonstep: set_fixed: %s\n" % (str(value)))
        self.gladeobjdict["readout"].set_fixed(fixed,value,displayfmt)
        self.gladeobjdict["pushbutton"].set_sensitive(not fixed)
        if not fixed:
            self.update_xml()
            pass
        
        pass

    def changedcallback(self,param,condition):
        if not self.is_fixed():
            self.setbuttonbgcolor("green") # indicate that we have been pushed
            self.update_xml()
            pass

        pass

    def value_from_xml(self): 
        
        if not "paramname" in self.myprops:
            # not fully initialized
            return ("",None)
        
        # same as value_from_xml from dc_paramstep but iterates over paramnames... 
        # Since the text box is read-only and this is just used for the 
        
        retval=dc_value.stringvalue("")
        retfmt=None
        
        for paramname in ("paramname","paramname2","paramname3"):
            (gotvalue,gotdisplayfmt)=(dc_value.stringvalue(""),None)
            if self.myprops[paramname] is not None:
                (gotvalue,gotdisplayfmt)=dc2_misc.stepwidget_value_from_xml(self,self.myprops[paramname])
                pass
            if paramname=="paramname":
                retval=gotvalue
                retfmt=gotdisplayfmt
                pass
            pass

        # We only show the first param 

        return (retval,retfmt)
    
    
    def update_xml(self):   # ... save as update_xml from dc_paramstep but iterates over params
        if self.is_fixed():
            return

        # only intermediate params are saved to the checklist XML
        if not self.myprops["intermediate"]:
            return

        if self.guistate is None or self.paramdb is None:
            return
        
        for paramname in ("paramname","paramname2","paramname3"):
            if self.myprops[paramname] != None and len(self.myprops[paramname]) > 0:
                newvalue=self.paramdb[self.myprops[paramname]].dcvalue
                dc2_misc.stepwidget_update_xml(self,self.myprops[paramname],newvalue)
                pass

            pass
        return
        

    def resetchecklist(self):
        buttonreadoutstep.resetchecklist(self)
        
        self.setbuttonbgcolor("gray") # indicate that we have not been pushed
        # reset parameter values
        #if self.paramdb is not None:
        #    if self.myprops["paramname"] is not None and len(self.myprops["paramname"]) > 0:
        #        self.paramdb[self.myprops["paramname"]].requestvalstr_sync("")
        #        pass
        #    if self.myprops["paramname2"] is not None and len(self.myprops["paramname2"]) > 0:
        #        self.paramdb[self.myprops["paramname2"]].requestvalstr_sync("")
        #        pass
        #    if self.myprops["paramname3"] is not None and len(self.myprops["paramname3"]) > 0:
        #        self.paramdb[self.myprops["paramname3"]].requestvalstr_sync("")
        #        pass
        #    pass
        
        # clear

        #self.update_xml()
        self.set_fixed()
        
        pass
    pass


gobject.type_register(savebuttonstep)  # required since we are defining new properties/signals
