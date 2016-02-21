# NOTE: This is intended to be subclassed, not used directly.
# This connects the push button to an undefined method called
# "buttoncallback"

# The sub-class needs to define a "buttoncallback" method to 
# handle the button click...



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

#sys.path.append("/home/sdh4/research/datacollect")
import dc_value

from dc_gtksupp import build_from_file
from dc_gtksupp import dc_initialize_widgets

__pychecker__="no-import no-argsused"

# gtk superclass should be first of multiple inheritances
class savemeasurementstep(gtk.HBox):
    __gtype_name__="savemeasurementstep"
    __gproperties__ = {


        "description": (gobject.TYPE_STRING,
                     "description of step",
                     "description of step",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags
        }
    __proplist = ["description"]
    
    myprops=None

    checklist=None
                      
    paramdb=None
    gladeobjdict=None
    
    def __init__(self,checklist,step,xmlpath):
        # paramhandler.__init__(self,super(adjustparamstep,self),self.__proplist)# .__gproperties__)
        # gtk.HBox.__init__(self) # Not supposed to call superclass __init__ method, just gobject __init__ according to    http://www.pygtk.org/articles/subclassing-gobject/sub-classing-gobject-in-python.htm  
        gobject.GObject.__init__(self)

        self.myprops={}

        self.checklist=checklist

        (self.gladeobjdict,self.gladebuilder)=build_from_file(os.path.join(os.path.split(sys.modules[self.__module__].__file__)[0],"savemeasurementstep.glade"))   
        self.myprops["description"]=""
        

        if not self.checklist.datacollectmode:
            raise ValueError("Save measurement step not valid except in datacollect mode")

        #if self.checklist.done_is_save_measurement:
        #    raise ValueError("Save measurement step not valid when done button means \"save measurement\". Remove dc:done_is_save_measurement=true from <checklist> tag.")
        

        self.pack_start(self.gladeobjdict["savemeasurementstep"],True,True,0)

        self.gladeobjdict["pushbutton"].connect("clicked",self.buttoncallback)
        self.gladeobjdict["step_descr_label"].set_selectable(True)

        pass
    
    def buttoncallback(self,*args):

        # Make sure everything is consistent, etc. 
        if not self.checklist.verify_save():
            return
        
        # Save measurement
        self.checklist.save_measurement()

        # increment measnum
        self.paramdb["measnum"].requestval_sync(dc_value.integervalue(self.paramdb["measnum"].dcvalue.value()+1))
        pass


        # Make button insensitive
        self.gladeobjdict["pushbutton"].set_sensitive(False)
        pass


    def do_set_property(self,property,value):
        # print "set_property(%s,%s)" % (property.name,str(value))
        
        if property.name=="description":
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

        dc_initialize_widgets(self.gladeobjdict,guistate)

        pass

    def resetchecklist(self):

        # Make button sensitive
        self.gladeobjdict["pushbutton"].set_sensitive(True)

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


gobject.type_register(savemeasurementstep)  # required since we are defining new properties/signals
