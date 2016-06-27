# This connects the push button to assigning a blank string value
# to the specified parameter. 


import os
import sys

if "gi" in sys.modules:  # gtk3
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk as gtk
    from gi.repository import Gdk as gdk
    from gi.repository import GObject as gobject
    pass
else : 
    # gtk2
    import gtk
    import gtk.gdk as gdk
    import gobject
    pass

#sys.path.append("/home/sdh4/research/datacollect")
from .. import dc_value

from ..dc_gtksupp import build_from_file
from ..dc_gtksupp import dc_initialize_widgets


if hasattr(gtk,"StateType") and hasattr(gtk.StateType,"NORMAL"):
    # gtk3
    STATE_NORMAL=gtk.StateType.NORMAL
    STATE_PRELIGHT=gtk.StateType.PRELIGHT
    pass
else:
    STATE_NORMAL=gtk.STATE_NORMAL
    STATE_PRELIGHT=gtk.STATE_PRELIGHT
    pass



__pychecker__="no-import no-argsused"

# gtk superclass should be first of multiple inheritances
class buttonstep(gtk.HBox):
    __gtype_name__="buttonstep"
    __gproperties__ = {

        "param": (gobject.TYPE_STRING,
                       "parameter",
                       "parameter to assign blank value to when button pressed",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags

        "value": (gobject.TYPE_STRING,
                  "value",
                  "value to assign to parameter database entry when button is pressed",
                  "", # default value 
                gobject.PARAM_READWRITE), # flags

        "buttonlabel": (gobject.TYPE_STRING,
                       "Button label",
                       "Label to put on the button",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags


        "description": (gobject.TYPE_STRING,
                     "description of step",
                     "description of step",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags
        }
    __proplist = ["param","value","buttonlabel","description"]
    
    myprops=None
    checklist=None
    step=None
    
    dc_gui_io=None
    paramdb=None
    gladeobjdict=None
    guistate=None
    xmlpath=None
    
    def __init__(self,checklist,step,xmlpath):
        # paramhandler.__init__(self,super(adjustparamstep,self),self.__proplist)# .__gproperties__)
        # gtk.HBox.__init__(self) # Not supposed to call superclass __init__ method, just gobject __init__ according to    http://www.pygtk.org/articles/subclassing-gobject/sub-classing-gobject-in-python.htm  
        gobject.GObject.__init__(self)

        self.myprops={}
        self.checklist=checklist
        self.step=step
        self.xmlpath=xmlpath
        #import pdb as pythondb
        #pythondb.set_trace()
        (self.gladeobjdict,self.gladebuilder)=build_from_file(os.path.join(os.path.split(sys.modules[self.__module__].__file__)[0],"buttonstep.glade"))   
        
        self.set_property("description","")
        self.set_property("buttonlabel","")
        self.set_property("param","")
        self.set_property("value","")

        self.set_fixed()
        self.pack_start(self.gladeobjdict["buttonstep"],True,True,0)

        self.gladeobjdict["pushbutton"].connect("clicked",self.buttoncallback)
        self.gladeobjdict["step_descr_label"].set_selectable(True)

        pass
    
    def buttoncallback(self,*args):
        # issue requestval to param
        self.paramdb[self.myprops["param"]].requestvalsync_str(self.myprops["value"])
        pass
    

    def do_set_property(self,property,value):
        #sys.stderr.write("got buttonreadoutste.get_property()\n")
        # print "set_property(%s,%s)" % (property.name,str(value))
        if property.name=="buttonlabel":
            self.myprops[property.name]=value
            self.gladeobjdict["pushbutton"].set_property("label",value)
            pass
        elif property.name=="param":
            self.myprops[property.name]=value
            pass
        elif property.name=="value":
            self.myprops[property.name]=value
            pass
        
        elif property.name=="description":
            self.myprops[property.name]=value
            #self.gladeobjdict["step_descr_label"].set_property("label",value)  
            self.gladeobjdict["step_descr_label"].set_markup(value)  
            pass
        else :
            raise IndexError("Bad property name %s" % (property.name))
        pass

    def do_get_property(self,property):
        return self.myprops[property.name]
    
    def dc_gui_init(self,guistate):
        # need next line if subclassing a dc_gui class
        # super(dg_readout).__dc_gui_init(self,io)
        
        self.guistate=guistate
        self.paramdb=guistate.paramdb
        self.dc_gui_io=guistate.iohandlers

        dc_initialize_widgets(self.gladeobjdict,guistate)

        pass

    def is_fixed(self): # note overridden by savebuttonstep
        # param readout is fixed when checklist is marked as
        # readonly or when checkbox is checked. 
        return self.checklist.readonly or self.step.gladeobjdict["checkbutton"].get_property("active")

    def set_fixed(self):   # note: overridden by savebuttonstep
        fixed=self.is_fixed()
        #self.gladeobjdict["readout"].set_editable(False) # readout only
        
        if fixed: 
            (value,displayfmt)=self.value_from_xml() # must be implemented by subclass
            #self.gladeobjdict["readout"].set_fixed(True,value,displayfmt)
            pass
        else:
            self.update_xml()  # must be implemented by subclass
            pass
        
        pass

    
    def set_readonly(self,readonly):
        self.set_fixed()
        pass
    
    def handle_check(self,checked):
        # automagically called by steptemplate when checkbox is checked or unchecked
        self.set_fixed()
        pass

    def resetchecklist(self):
        # self.gladeobjdict["pushbutton"].reset()
        pass

    def isconsistent(self,inconsistentlist):
        consistent=True
        for key in self.gladeobjdict:
            if hasattr(self.gladeobjdict[key],"isconsistent"):
                consistent=consistent and self.gladeobjdict[key].isconsistent(inconsistentlist)
                pass
            pass
        return consistent
    


    def setbuttonbgcolor(self,colorname):
        colormap={"white" : "#cccccc",
                  "red"   : "#dd0000",
                  "yellow": "#dddd00",
                  "ltblue": "#80a0c0",
                  "magenta": "#cc00cc",
                  "green": "#00dd00",
                  "orange": "#cc7000",
                  "gray": "#aaaaaa"}
        colormap_active={"white" : "#ffffff",
                         "red"   : "#ff6666",
                         "yellow": "#ffff66",
                         "ltblue": "#a0c0ff",
                         "magenta": "#ff00ff",
                         "green": "#66ff66",
                         "ltblue": "#a0c0ff",
                         "orange": "#ff9000",
                         "gray":   "#ffffff"}
        
        self.gladeobjdict["pushbutton"].modify_bg(STATE_NORMAL,gdk.color_parse(colormap[colorname]))
        self.gladeobjdict["pushbutton"].modify_bg(STATE_PRELIGHT,gdk.color_parse(colormap_active[colorname]))
        
        pass


    pass


gobject.type_register(buttonstep)  # required since we are defining new properties/signals
