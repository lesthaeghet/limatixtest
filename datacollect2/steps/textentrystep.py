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
from .. import dc_value

from ..dc_gtksupp import build_from_file
from ..dc_gtksupp import dc_initialize_widgets

__pychecker__="no-import no-argsused"

# gtk superclass should be first of multiple inheritances
class textentrystep(gtk.HBox):
    __gtype_name__="textentrystep"
    __gproperties__ = {
        "initialtext": (gobject.TYPE_STRING,
                     "initialtext",
                     "Initial text (on reset) for textentry",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags
        "text": (gobject.TYPE_STRING,
                 "text",
                 "Text value for textentry",
                 "", # default value 
                 gobject.PARAM_READWRITE), # flags
        
        "width": (gobject.TYPE_INT,
                  "Text box width",
                  "Requested text box with, in characters",
                  0, # minimum value, equivalent to unspecified
                  100, # maximum value
                  0, # default value 
                  gobject.PARAM_READWRITE), # flags
        
        
        "description": (gobject.TYPE_STRING,
                        "description of step",
                        "description of step",
                        "", # default value 
                        gobject.PARAM_READWRITE), # flags
        }
    __proplist = ["initialtext","text","width","description"]
    
    myprops=None

    checklist=None
    step=None
    xmlpath=None
                      
    searchdirs=None
    gladeobjdict=None

    changedinhibit=None
    
    def __init__(self,checklist,step,xmlpath):
        # paramhandler.__init__(self,super(adjustparamstep,self),self.__proplist)# .__gproperties__)
        # gtk.HBox.__init__(self) # Not supposed to call superclass __init__ method, just gobject __init__ according to    http://www.pygtk.org/articles/subclassing-gobject/sub-classing-gobject-in-python.htm  
        gobject.GObject.__init__(self)

        self.myprops={"initialtext": None, "text": None, "width": None, "description": None}
        #self.resize(1,1)
        # self.set_property("size",1)

        (self.gladeobjdict,self.gladebuilder)=build_from_file(os.path.join(os.path.split(sys.modules[self.__module__].__file__)[0],"textentrystep.glade"))   
        
        # self.gladeobjdict["step_textentry"].connect("size-request",self.te_reqsize)

        self.changedinhibit=False
        self.searchdirs=None
        self.checklist=checklist
        self.step=step
        self.xmlpath=xmlpath

        self.set_property("initialtext","")
        self.set_property("description","")
        self.set_property("width",0)

        self.pack_start(self.gladeobjdict["textentrystep"],True,True,0)

        self.gladeobjdict["step_textentry"].connect("changed",self.changedcallback)

        self.gladeobjdict["step_descr_label"].set_selectable(True)


        pass

    def set_initialtext(self,value):
        self.myprops["initialtext"]=value

        pass


    def text_from_xml(self):
        text=""
        self.checklist.xmldoc.lock_ro()
        try:
            xmltag=self.checklist.xmldoc.restorepath(self.xmlpath)

            textparamnodes=self.checklist.xmldoc.xpathcontext(xmltag,"chx:parameter[@name='text']")
            if len(textparamnodes) > 0:
                textparamnode=textparamnodes[0]
                
                text=self.checklist.xmldoc.gettext(textparamnode)
                
                pass
            

            pass
        finally:
            self.checklist.xmldoc.unlock_ro()
            pass
        
        return text

    def update_widget(self):
        self.changedinhibit=True
        self.gladeobjdict["step_textentry"].set_text(self.myprops["text"])
        self.changedinhibit=False
        pass
    
    def update_xml(self):
        value=self.myprops["text"]

        self.checklist.xmldoc.lock_rw()
        try : 
            xmltag=self.checklist.xmldoc.restorepath(self.xmlpath)
            textparamnodes=self.checklist.xmldoc.xpathcontext(xmltag,"chx:parameter[@name='text']")
            if len(textparamnodes) < 1:
                # need to add a node
                textparamnode=self.checklist.xmldoc.addelement(xmltag,"chx:parameter")
                self.checklist.xmldoc.setattr(textparamnode,"name","text")
                self.checklist.xmldoc.setattr(textparamnode,"type","str")
                pass
            else:
                textparamnode=textparamnodes[0]
                pass
                
            self.checklist.xmldoc.settext(textparamnode,self.myprops["text"])
        
            # we can't use list.index() to find which step we are because 
            # that uses equality (==) not equivalence (is) 
            stepindex=[ cnt for cnt in range(len(self.checklist.steps)) if self.checklist.steps[cnt] is self.step]
        
            if len(stepindex) > 0:
                # stepindex will be empty in initial load before this step is
                # added to the list. In this case we probably don't want to 
                # log anyway. 
                self.checklist.addlogentry("Text Field on Item %d Updated" % (stepindex[0]+1),item=stepindex[0]+1,action="updatetext",value=self.myprops["text"])
                pass

            # sys.stderr.write(etree.tostring(self.xmltag)+'\n')
            pass
        except:
            raise
        finally: 
            self.checklist.xmldoc.unlock_rw()
            pass

        pass
    
    def do_set_property(self,property,value):
        # print "set_property(%s,%s)" % (property.name,str(value))
        if property.name=="initialtext":
            self.set_initialtext(value)
            pass
        elif property.name=="text":
            self.myprops["text"]=value
            self.update_widget()
            pass
        elif property.name=="width":
            self.myprops[property.name]=value
            self.gladeobjdict["step_textentry"].set_width_chars(value)
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
        

        self.searchdirs=guistate.searchdirs

        #self.set_initialtext(self.myprops["initialtext"])
        
        self.set_fixed()
        
        dc_initialize_widgets(self.gladeobjdict,guistate)

        pass

    def is_fixed(self):
        # param readout is fixed when checklist is marked as
        # readonly or when checkbox is checked. 
        return self.checklist.readonly or self.step.gladeobjdict["checkbutton"].get_property("active")
    

    def set_fixed(self):
        fixed=self.is_fixed()
        self.gladeobjdict["step_textentry"].set_sensitive(not(fixed))
        if fixed:
            self.update_widget()
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
        


    def changedcallback(self,event):
        if self.changedinhibit:
            return
        
        if not self.is_fixed():
            self.myprops["text"]=self.gladeobjdict["step_textentry"].get_text()
            self.update_xml()
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
        assert(not self.is_fixed())
        self.myprops["text"]=self.myprops["initialtext"]

        self.update_widget()
        self.update_xml()

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


gobject.type_register(textentrystep)  # required since we are defining new properties/signals
