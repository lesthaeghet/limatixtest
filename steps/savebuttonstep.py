# Step with a savebutton for saving a specified datacollect param
# with the perform_save() method
#
# Works only in datacollect mode. Must be late enough 
# in the checklist that checklist filename has already been determined


import os
import sys

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

import dc_value

from buttonreadoutstep import buttonreadoutstep

__pychecker__="no-import no-argsused"

# gtk superclass should be first of multiple inheritances
class savebuttonstep(buttonreadoutstep):
    __gtype_name__="savebuttonstep"
    __gproperties__ = {

        "paramname": (gobject.TYPE_STRING,
                  "parameter",
                  "datacollect parameter to show and to use for save. Should be an hrefvalue with a controller that supports the perform_save method",
                  "", # default value 
                gobject.PARAM_READWRITE), # flags

        # also "buttonlabel" and "description" properties
        # inherited from buttonreadoutstep
        
        }
    checklist=None
    xmlpath=None

    # self.paramdb and self.dc_gui_io defined by buttonreadoutstep, set by buttonreadoutstep's dc_gui_init()

                      
    def __init__(self,checklist,step,xmlpath):
        buttonreadoutstep.__init__(self,checklist,step,xmlpath)
        # paramhandler.__init__(self,super(adjustparamstep,self),self.__proplist)# .__gproperties__)
        # gobject.GObject.__init__(self)

        self.checklist=checklist
        self.xmlpath=xmlpath
        
        self.set_property("readoutparam",self.paramname)
        self.set_property("buttonlabel","Save DGS Snapshot")

        pass    


    def do_set_property(self,property,value):
        # print "set_property(%s,%s)" % (property.name,str(value))
        if property.name=="paramname":
            # print "paramname=%s" % value
            self.paramname=value
            buttonreadoutstep.set_property(self,"readoutparam",value)
            pass
        else :
            buttonreadoutstep.set_property(self,property.name,value)
            pass
        pass

    def do_get_property(self,property):
        if property.name == "paramname":
            return self.paramname
        return buttonreadoutstep.get_property(self,propery.name)
    


    def buttoncallback(self,*args):
        if self.checklist.readonly:
            return
        if self.is_fixed():  # determined by buttonreadoutstep superclass
            return
        if not self.checklist.checknotcurrent():
            return
        
        self.checklist.xmldoc.lock_ro()
        try :             
            destelement=self.checklist.xmldoc.xpathsingle("chx:dest")
            desthref=dc_value.hrefvalue.fromxml(self.checklist.xmldoc,destelement)
        finally:
            self.checklist.xmldoc.unlock_ro()
            pass
        
        # In datacollectmode the checklist autosaves once enough steps
        # have been checked to determine the filename, so we have to be
        # past this point
        if self.checklist.datacollectmode:
            if self.checklist.filehref is None:
                raise ValueError("Save DGS step is too early -- checklist not yet saved to a file, so impossible to determine filename")
            (chklistbasename,chklistext)=os.path.splitext(self.checklist.chklistfile)

            # suggest a filename
            chklistfilename=self.checklist.filehref.get_bare_unquoted_filename()
            chklistbasename=posixpath.splitext(self.checklist.filehref)[0]
            filename="%s_%s.%s" % (chklistbasename,self.paramname,self.paramdb[self.paramname].save_extension)
            savefilehref=dc_value.hrefvalue(quote(filename),contexthref=desthref)
        
            
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

            pass
        else :
            # not datacollect mode...
            # determine filename automatically if possible, but ask user
            defname=""

            if self.checklist.ok_set_filename():
                defname=os.path.splitext(self.checklist.requestedfilename())[0]+self.paramdb[self.paramname].save_extension
                
                pass
            

            Chooser=gtk.FileChooserDialog(title="Save as...",action=gtk.FILE_CHOOSER_ACTION_SAVE,buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_SAVE,gtk.RESPONSE_OK))
            Chooser.set_modal(True)
            Chooser.set_current_name(defname)
            Chooser.set_current_folder(desthref.getpath())
            Chooser.set_do_overwrite_confirmation(True)
            
            datafilter=gtk.FileFilter()
            datafilter.set_name(self.paramdb[self.paramname].save_extension.upper() + " files")
            datafilter.add_pattern("*." + self.paramdb[self.paramname].save_extension)
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
            


            pass

        self.paramdb[self.paramname].perform_save(savefilehref)

        self.update_xml()
        
        self.setbuttonbgcolor("green") # indicate that we have been pushed
        
        pass

    def value_from_xml(self): # same as value_from_xml from dc_paramstep
        gotvalue=None
        gotdisplayfmt=None
        # xml_attribute=self.guistate.paramdb[self.myprops["paramname"]].xml_attribute

        self.checklist.xmldoc.lock_ro()
        try: 
            xmltag=self.checklist.xmldoc.restorepath(self.xmlpath)
            for child in xmltag:
                childtag=self.checklist.xmldoc.gettag(child)
                if childtag=="dc:"+self.myprops["paramname"] or childtag==self.myprops["paramname"]:
                    if self.guistate is not None and self.guistate.paramdb is not None:
                        # Use type specified in paramdb if possible
                        paramtype=self.guistate.paramdb[self.myprops["paramname"]].paramtype
                        pass
                    else:
                        # pull type from XML
                        paramtype=dc_value.xmlextractvalueclass(self.checklist.xmldoc,child)
                        #sys.stderr.write("element %s: paramtype=%s\n" % (etree.tostring(child),str(paramtype)))
                        pass

                    gotvalue=paramtype.fromxml(self.checklist.xmldoc,child)  # xml_attribute=xml_attribute)
                    gotdisplayfmt=dc_value.xmlextractdisplayfmt(self.checklist.xmldoc,child)
                    break
                pass
            pass
        except: 
            raise
        finally:
            self.checklist.xmldoc.unlock_ro()
            pass
        return (gotvalue,gotdisplayfmt)

    
    def update_xml(self):   # ... save as update_xml from dc_paramstep
        if self.is_fixed():
            return

        if self.guistate is None or self.guistate.paramdb is None:
            return
        
        newvalue=self.guistate.paramdb[self.myprops["paramname"]].dcvalue
        # xml_attribute=self.guistate.paramdb[self.myprops["paramname"]].xml_attribute
        gottag=False
        
        if self.checklist.xmldoc is None:
            try: 
                assert(0)
                pass
            except: 
                #import pdb as pythondb
                #pythondb.post_mortem()
                raise
                pass
            
        #print "Param Name:  %s" % (self.myprops["paramname"])          
        
        # chxstate="checked" in self.xmltag.attrib and self.xmltag.attrib["checked"]=="true"
        # if chxstate: 
        #     # once checked, inhibit updates
        #     
        #     pass
        # else : 
        #     # otherwise copy current state into xmltag
        self.checklist.xmldoc.lock_rw()
        try:
            xmltag=self.checklist.xmldoc.restorepath(self.xmlpath)
            if not newvalue.isblank():
                for child in xmltag:
                    childtag=self.checklist.xmldoc.gettag(child)
                    if childtag=="dc:"+self.myprops["paramname"] or childtag==self.myprops["paramname"]:
                        newvalue.xmlrepr(self.checklist.xmldoc,child) # ,xml_attribute=xml_attribute)
                        dc_value.xmlstoredisplayfmt(self.checklist.xmldoc,child,self.guistate.paramdb[self.myprops["paramname"]].displayfmt)
                        dc_value.xmlstorevalueclass(self.checklist.xmldoc,child,self.guistate.paramdb[self.myprops["paramname"]].paramtype)
                        gottag=True
                        break
                    pass
                if not gottag: 
                    # need to create tag
                    newchild=self.checklist.xmldoc.addelement(xmltag,"dc:"+self.myprops["paramname"])
                    newvalue.xmlrepr(self.checklist.xmldoc,newchild) #xml_attribute=xml_attribute)
                    dc_value.xmlstoredisplayfmt(self.checklist.xmldoc,newchild,self.guistate.paramdb[self.myprops["paramname"]].displayfmt)
                    pass
                pass
            else:
                # newvalue is blank
                # ... remove dc:<paramname> tags from checklist entry
                for child in xmltag:
                    childtag=self.checklist.xmldoc.gettag(child)
                    if childtag=="dc:"+self.myprops["paramname"] or childtag==self.myprops["paramname"]:
                        self.checklist.xmldoc.remelement(child)
                        pass
                    pass
                

                pass
        except: 
            raise
        finally:
            self.checklist.xmldoc.unlock_rw()
            pass
        return newvalue


    def resetchecklist(self):
        buttonreadoutstep.resetchecklist(self)

        self.setbuttonbgcolor("gray") # indicate that we have not been pushed
        # reset dgsfile name
        self.paramdb[self.paramname].requestvalstr_sync("")
        # clear

        self.update_xml()
        
        pass
    pass


gobject.type_register(savebuttonstep)  # required since we are defining new properties/signals
