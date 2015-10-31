# NOTE: This is intended to be subclassed, not used directly.
# This connects the push button to an undefined method called
# "buttoncallback"

# The sub-class needs to define a "buttoncallback" method to 
# handle the button click...



import os
import sys
# import gobject

if not "gtk" in sys.modules:  # gtk3
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
import dc_value

from dc_gtksupp import build_from_file
from dc_gtksupp import dc_initialize_widgets



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
class buttonresetvaluesstep(gtk.HBox):
    __gtype_name__="buttonresetvaluesstep"
    __gproperties__ = {


        "buttonlabel": (gobject.TYPE_STRING,
                       "Button label",
                       "Label to put on the button",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags

        "resetparam1": (gobject.TYPE_STRING,
                       "Parameter 1 to reset",
                       "Parameter 1 to reset",
                        "", # default value 
                        gobject.PARAM_READWRITE), # flags

        "paramvaluestr1": (gobject.TYPE_STRING,
                           "Parameter 1 reset value string",
                           "Parameter 1 reset value string",
                           "", # default value 
                           gobject.PARAM_READWRITE), # flags

        "resetparam2": (gobject.TYPE_STRING,
                       "Parameter 2 to reset",
                       "Parameter 2 to reset",
                        "", # default value 
                        gobject.PARAM_READWRITE), # flags

        "paramvaluestr2": (gobject.TYPE_STRING,
                           "Parameter 2 reset value string",
                           "Parameter 2 reset value string",
                           "", # default value 
                           gobject.PARAM_READWRITE), # flags

        "resetparam3": (gobject.TYPE_STRING,
                       "Parameter 3 to reset",
                       "Parameter 3 to reset",
                        "", # default value 
                        gobject.PARAM_READWRITE), # flags

        "paramvaluestr3": (gobject.TYPE_STRING,
                           "Parameter 3 reset value string",
                           "Parameter 3 reset value string",
                           "", # default value 
                           gobject.PARAM_READWRITE), # flags

        "resetparam4": (gobject.TYPE_STRING,
                       "Parameter 4 to reset",
                       "Parameter 4 to reset",
                        "", # default value 
                        gobject.PARAM_READWRITE), # flags

        "paramvaluestr4": (gobject.TYPE_STRING,
                           "Parameter 4 reset value string",
                           "Parameter 4 reset value string",
                           "", # default value 
                           gobject.PARAM_READWRITE), # flags

        "resetparam5": (gobject.TYPE_STRING,
                       "Parameter 5 to reset",
                       "Parameter 5 to reset",
                        "", # default value 
                        gobject.PARAM_READWRITE), # flags

        "paramvaluestr5": (gobject.TYPE_STRING,
                           "Parameter 5 reset value string",
                           "Parameter 5 reset value string",
                           "", # default value 
                           gobject.PARAM_READWRITE), # flags

        "resetparam6": (gobject.TYPE_STRING,
                       "Parameter 6 to reset",
                       "Parameter 6 to reset",
                        "", # default value 
                        gobject.PARAM_READWRITE), # flags

        "paramvaluestr6": (gobject.TYPE_STRING,
                           "Parameter 6 reset value string",
                           "Parameter 6 reset value string",
                           "", # default value 
                           gobject.PARAM_READWRITE), # flags


        "resetparam7": (gobject.TYPE_STRING,
                       "Parameter 7 to reset",
                       "Parameter 7 to reset",
                        "", # default value 
                        gobject.PARAM_READWRITE), # flags

        "paramvaluestr7": (gobject.TYPE_STRING,
                           "Parameter 7 reset value string",
                           "Parameter 7 reset value string",
                           "", # default value 
                           gobject.PARAM_READWRITE), # flags

        "resetparam8": (gobject.TYPE_STRING,
                       "Parameter 8 to reset",
                       "Parameter 8 to reset",
                        "", # default value 
                        gobject.PARAM_READWRITE), # flags

        "paramvaluestr8": (gobject.TYPE_STRING,
                           "Parameter 8 reset value string",
                           "Parameter 8 reset value string",
                           "", # default value 
                           gobject.PARAM_READWRITE), # flags

        "resetparam9": (gobject.TYPE_STRING,
                       "Parameter 9 to reset",
                       "Parameter 9 to reset",
                        "", # default value 
                        gobject.PARAM_READWRITE), # flags

        "paramvaluestr9": (gobject.TYPE_STRING,
                           "Parameter 9 reset value string",
                           "Parameter 9 reset value string",
                           "", # default value 
                           gobject.PARAM_READWRITE), # flags


        "description": (gobject.TYPE_STRING,
                     "description of step",
                     "description of step",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags
        }
    __proplist = ["buttonlabel","description",
                  "resetparam1","paramvaluestr1",
                  "resetparam2","paramvaluestr2",
                  "resetparam3","paramvaluestr3",
                  "resetparam4","paramvaluestr4",
                  "resetparam5","paramvaluestr5",
                  "resetparam6","paramvaluestr6",
                  "resetparam7","paramvaluestr7",
                  "resetparam8","paramvaluestr8",
                  "resetparam9","paramvaluestr9",
    ]
    
    myprops=None

                      
    dc_gui_io=None
    paramdb=None
    gladeobjdict=None
    
    def __init__(self,checklist,step,xmlpath):
        # paramhandler.__init__(self,super(adjustparamstep,self),self.__proplist)# .__gproperties__)
        # gtk.HBox.__init__(self) # Not supposed to call superclass __init__ method, just gobject __init__ according to    http://www.pygtk.org/articles/subclassing-gobject/sub-classing-gobject-in-python.htm  
        gobject.GObject.__init__(self)

        self.myprops={}

        (self.gladeobjdict,self.gladebuilder)=build_from_file(os.path.join(os.path.split(sys.modules[self.__module__].__file__)[0],"buttonresetvaluesstep.glade"))   
        
        self.set_property("description","")
        self.set_property("buttonlabel","")

        self.pack_start(self.gladeobjdict["buttonresetvaluesstep"],True,True,0)

        self.gladeobjdict["pushbutton"].connect("clicked",self.buttoncallback)
        self.gladeobjdict["step_descr_label"].set_selectable(True)

        pass
    
    def buttoncallback(self,*args):
        # reset request values from self.paramdb
        
        for key in self.myprops: 
            if key.startswith("resetparam"):
                paramname=self.myprops[key]

                if paramname not in self.paramdb:
                    
                    sys.stderr.write("buttonresetvaluesstep: Error resetting parameter %s: Parameter unknown\n" % (key))
                    pass
                    
                valuename="paramvaluestr"+key[10:]
                if valuename not in self.myprops: 
                    sys.stderr.write("buttonresetvaluesstep: Error resetting parameter %s: No value string provided\n" % (key))
                    continue
                
                valuestr=self.myprops[valuename]
                
                self.paramdb[paramname].requestvalstr_sync(valuestr)
                pass
                
            pass
        
        self.setbuttonbgcolor("green") # indicate that we have been pushed

        pass
    
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



    def do_set_property(self,property,value):
        # print "set_property(%s,%s)" % (property.name,str(value))
        if property.name=="buttonlabel":
            self.myprops[property.name]=value
            self.gladeobjdict["pushbutton"].set_property("label",value)
            pass
        
        elif property.name=="description":
            self.myprops[property.name]=value
            #self.gladeobjdict["step_descr_label"].set_property("label",value)  
            self.gladeobjdict["step_descr_label"].set_markup(value)  
            pass
        elif property.name.startswith("resetparam"):
            self.myprops[property.name]=value            
            pass
        elif property.name.startswith("paramvaluestr"):
            self.myprops[property.name]=value            
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
        self.dc_gui_io=guistate.io

        dc_initialize_widgets(self.gladeobjdict,guistate)

        pass

    def resetchecklist(self):

        self.setbuttonbgcolor("gray") # indicate that we have not been pushed
        
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


gobject.type_register(buttonresetvaluesstep)  # required since we are defining new properties/signals
