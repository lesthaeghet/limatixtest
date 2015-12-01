# NOTE: This is intended to be subclassed, not used directly.
# This connects the push button to an undefined method called
# "buttoncallback"

# The sub-class needs to define a "buttoncallback" method to 
# handle the button click...



import os
import sys

if not "gtk" in sys.modules:  # gtk3
    from gi.repository import Gtk as gtk
    from gi.repository import GObject as gobject
    pass
else : 
    # gtk2
    import gtk
    import gobject
    pass

#sys.path.append("/home/sdh4/research/datacollect")
import dc_value

from dc_gtksupp import build_from_file
from dc_gtksupp import dc_initialize_widgets

__pychecker__="no-import no-argsused"

# gtk superclass should be first of multiple inheritances
class buttontextareastep(gtk.HBox):
    __gtype_name__="buttontextareastep"
    __gproperties__ = {

        "readoutparam": (gobject.TYPE_STRING,
                       "readout parameter",
                       "parameter to show",
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
    __proplist = ["readoutparam","buttonlabel","description"]
    
    myprops=None

                      
    dc_gui_io=None
    paramdb=None
    gladeobjdict=None
    
    def __init__(self,checklist,step,xmlpath):
        # paramhandler.__init__(self,super(adjustparamstep,self),self.__proplist)# .__gproperties__)
        # gtk.HBox.__init__(self) # Not supposed to call superclass __init__ method, just gobject __init__ according to    http://www.pygtk.org/articles/subclassing-gobject/sub-classing-gobject-in-python.htm  
        gobject.GObject.__init__(self)

        self.myprops={}

        (self.gladeobjdict,self.gladebuilder)=build_from_file(os.path.join(os.path.split(sys.modules[self.__module__].__file__)[0],"buttontextareastep.glade"))   
        
        self.set_property("description","")
        self.set_property("buttonlabel","")
        self.set_property("readoutparam","")

        self.gladeobjdict["textarea"].set_editable(False) # readout only

        self.pack_start(self.gladeobjdict["buttontextareastep"],True,True,0)

        self.gladeobjdict["pushbutton"].connect("clicked",self.buttoncallback)
        self.gladeobjdict["step_descr_label"].set_selectable(True)

        pass

    def buttoncallback(self,*args):
        raise ValueError("Invalid call to superclass buttoncallback()")
    
    def do_set_property(self,property,value):
        # print "set_property(%s,%s)" % (property.name,str(value))
        if property.name=="buttonlabel":
            self.myprops[property.name]=value
            self.gladeobjdict["pushbutton"].set_property("label",value)
            pass
        elif property.name=="readoutparam":
            self.myprops[property.name]=value
            self.gladeobjdict["textarea"].set_property("paramname",value)
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
        # super(dc_readout).__dc_gui_init(self,io)
        
        
        self.paramdb=guistate.paramdb
        self.dc_gui_io=guistate.io

        dc_initialize_widgets(self.gladeobjdict,guistate)

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
    
    pass


gobject.type_register(buttontextareastep)  # required since we are defining new properties/signals
