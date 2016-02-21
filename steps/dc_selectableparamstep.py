# important: indirectly uses dg_units (through dc_value)
# therefore main program should call dg_units.units_config("insert_basic_units")

import os
import sys

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

from lxml import etree

#sys.path.append("/home/sdh4/research/datacollect")
import paramdb2 as pdb
import dc_value

from dc_gtksupp import build_from_file
from dc_gtksupp import dc_initialize_widgets
__pychecker__="no-import no-argsused"

# gtk superclass should be first of multiple inheritances
class dc_selectableparamstep(gtk.HBox):
    __gtype_name__="dc_selectableparamstep"
    __gproperties__ = {
        "paramname": (gobject.TYPE_STRING,
                     "paramdb2 parameter to set",
                     "paramdb2 parameter to set",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags

         "labelmarkup": (gobject.TYPE_STRING,
                     "Markup string for the label",
                     "Markup string for the label",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags

        
        # "width": (gobject.TYPE_INT,
        #           "Text box width",
        #           "Requested text box with, in characters",
        #           0, # minimum value, equivalent to unspecified
        #           100, # maximum value
        #           0, # default value 
        #           gobject.PARAM_READWRITE), # flags
        
        
        "description": (gobject.TYPE_STRING,
                        "description of step",
                        "description of step",
                        "", # default value 
                        gobject.PARAM_READWRITE), # flags
        }
    __proplist = ["paramname","labelmarkup","description"]
    
    myprops=None

    checklist=None
    xmlpath=None
    guistate=None

    paramnotify=None
                      
    gladeobjdict=None
    
    def __init__(self,checklist,step,xmlpath):
        # paramhandler.__init__(self,super(adjustparamstep,self),self.__proplist)# .__gproperties__)
        # gtk.HBox.__init__(self) # Not supposed to call superclass __init__ method, just gobject __init__ according to    http://www.pygtk.org/articles/subclassing-gobject/sub-classing-gobject-in-python.htm  
        gobject.GObject.__init__(self)

        self.myprops={"paramname": None, "labelmarkup": None, "description": None}

        (self.gladeobjdict,self.gladebuilder)=build_from_file(os.path.join(os.path.split(sys.modules[self.__module__].__file__)[0],"dc_selectableparamstep.glade"))   
        
        # self.gladeobjdict["step_textentry"].connect("size-request",self.te_reqsize)

        self.xmlpath=xmlpath
        self.checklist=checklist

        self.set_property("paramname","")
        self.set_property("labelmarkup","")
        self.set_property("description","")

        self.pack_start(self.gladeobjdict["dc_selectableparamstep"],True,True,0)

        # self.gladeobjdict["step_adjustparam"].connect("changed",self.changedcallback)

        self.gladeobjdict["step_descr_label"].set_selectable(True)


        pass

    def do_set_property(self,property,value):
        # print "set_property(%s,%s)" % (property.name,str(value))
        if property.name=="paramname":
            # print "paramname=%s" % value
            self.myprops[property.name]=value
            self.gladeobjdict["step_adjustparam"].set_property("paramname",value)
            pass
        elif property.name=="labelmarkup":
            self.myprops[property.name]=value
            self.gladeobjdict["step_adjustparam"].set_property("labelmarkup",value+" ")
            pass
        elif property.name=="description":
            self.myprops[property.name]=value
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
        
        self.guistate=guistate
        
        self.set_fixed()  # set to fixed value from xml file if appropriate prior to sub-widget initialization
        dc_initialize_widgets(self.gladeobjdict,guistate)


        self.changedcallback(None,None) #  update xml
       
        
        self.paramnotify=self.guistate.paramdb.addnotify(self.myprops["paramname"],self.changedcallback,pdb.param.NOTIFY_NEWVALUE)

        pass
    
    def destroystep(self):
        self.guistate.paramdb.remnotify(self.myprops["paramname"],self.paramnotify)
        self.paramnotify=None
        pass
    
    def is_fixed(self):
        # param readout is fixed when checklist is marked as
        # readonly or when checkbox is checked. 
        return self.checklist.readonly or self.step.gladeobjdict["checkbutton"].get_property("active")
    

    def set_fixed(self):
        fixed=self.is_fixed()
        (value,displayfmt)=self.value_from_xml()
        self.gladeobjdict["step_adjustparam"].set_fixed(fixed,value,displayfmt)
        if not fixed:
            self.update_xml()
            pass
        pass
    
    def handle_check(self,checked):
        # automagically called by steptemplate when checkbox is checked or unchecked
        self.set_fixed()
        pass

    
    def set_readonly(self,readonly):
        # automagically called by step when checklist readonly state
        # changes.
        self.set_fixed()
        pass
        

    def changedcallback(self,param,condition):
        if not self.is_fixed():
            self.update_xml()
            pass
        pass
    
    def value_from_xml(self):
        gotvalue=None
        gotdisplayfmt=None
        #xml_attribute=self.guistate.paramdb[self.myprops["paramname"]].xml_attribute

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
                        pass
                    gotvalue=paramtype.fromxml(self.checklist.xmldoc,child)
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
    
    def update_xml(self):
        if self.is_fixed():
            return
        
        if self.guistate is None or self.guistate.paramdb is None:
            return

        newvalue=self.guistate.paramdb[self.myprops["paramname"]].dcvalue
        #xml_attribute=self.guistate.paramdb[self.myprops["paramname"]].xml_attribute
        gottag=False
        
        #chxstate="checked" in self.xmltag.attrib and self.xmltag.attrib["checked"]=="true"
        #if chxstate: 
        #    # once checked, inhibit updates
        #    
        #    pass
        #else : 
        #    # otherwise copy current state into xmltag
        self.checklist.xmldoc.lock_rw()
        try : 
            xmltag=self.checklist.xmldoc.restorepath(self.xmlpath)
            for child in xmltag:
                childtag=self.checklist.xmldoc.gettag(child)
                if childtag=="dc:"+self.myprops["paramname"] or childtag==self.myprops["paramname"]:
                    newvalue.xmlrepr(self.checklist.xmldoc,child) #xml_attribute=xml_attribute)
                    dc_value.xmlstoredisplayfmt(self.checklist.xmldoc,child,self.guistate.paramdb[self.myprops["paramname"]].displayfmt)
                    dc_value.xmlstorevalueclass(self.checklist.xmldoc,child,self.guistate.paramdb[self.myprops["paramname"]].paramtype)
                    gottag=True
                    break
                pass
            if not gottag: 
                # need to create tag
                newchild=self.checklist.xmldoc.addelement(xmltag,"dc:"+self.myprops["paramname"])
                newvalue.xmlrepr(self.checklist.xmldoc,newchild) # xml_attribute=xml_attribute)
                dc_value.xmlstoredisplayfmt(self.checklist.xmldoc,newchild,self.guistate.paramdb[self.myprops["paramname"]].displayfmt)
                pass
            pass
        except:
            raise
        finally: 
            self.checklist.xmldoc.unlock_rw()
            pass
        pass
    
    # def te_reqsize(self,obj,requisition):
    #
    #     gtk.Entry.do_size_request(self.gladeobjdict["step_textentry"],requisition)
    #
    #     # For some reason gtk.Entry asks for a crazy size sometimes (?)
    #     # Here we bound the request to 200px wide
    #     if requisition.width > 200:
    #         requisition.width=200
    #         pass
    #     # print requisition.width
    #     pass
    


    def resetchecklist(self):

        self.changedcallback(None,None) # Go back into updating mode

        pass


    def isconsistent(self,inconsistentlist):
        consistent=True
        for key in self.gladeobjdict:
            if hasattr(self.gladeobjdict[key],"isconsistent"):
                consistent=consistent and self.gladeobjdict[key].isconsistent(inconsistentlist)
                pass
            pass
        return consistent
    
    
    
    pass


gobject.type_register(dc_selectableparamstep)  # required since we are defining new properties/signals
