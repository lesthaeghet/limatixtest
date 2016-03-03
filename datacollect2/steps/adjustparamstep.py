# important: indirectly uses dg_units (through dc_value)
# therefore main program should call dg_units.units_config("insert_basic_units")

import os
import sys
import traceback

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

debug=False  # set to true to enable more debug output

# gtk superclass should be first of multiple inheritances
class adjustparamstep(gtk.HBox):
    __gtype_name__="adjustparamstep"
    __gproperties__ = {
        "dg-param": (gobject.TYPE_STRING,
                     "Dataguzzler parameter to monitor",
                     "Name of dataguzzler parameterto monitor ",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags


        "dg-adjustparam": (gobject.TYPE_STRING,
                     "Dataguzzler parameter to adjust (default to dg-param if empty)",
                     "Name of dataguzzler parameter to adjust (default to dg-param if empty)",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags


        "dg-paramdefault": (gobject.TYPE_STRING,
                     "dataguzzler parameter default value",
                     "Dataguzzler parameter default value",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags

        "dc-valuetype": (gobject.TYPE_STRING,
                     "datacollect value type",
                     "Datacollect value type (class defined in dc_value)",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags

        "dc-valuethreshold": (gobject.TYPE_DOUBLE,
                     "datacollect value threshold",
                     "Datacollect value equality comparison threshold",
                     0.0, # minimum value
                     float("Inf"), # maximum value
                     0.0, # default value 
                     gobject.PARAM_READWRITE), # flags

        "dc-valuedefunits": (gobject.TYPE_STRING,
                     "datacollect value default units",
                     "Datacollect value default units for numeric parameters. Should match units as interpreted by Dataguzzler. For string parameters set this to IGNORECASE to use case insensitive string comparisions)",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags

        "description": (gobject.TYPE_STRING,
                     "description of step",
                     "description of step",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags
        }
    __proplist = ["dg-param","dg-adjustparam","dg-paramdefault","dc-valuetype","dc-valuethreshold","dc-valuedefunits","description"]
    
    myprops=None

    # "dg-param" might be TRIG:MODE
    
                      
    gladeobjdict=None
    
    def __init__(self,checklist,step,xmlpath):
        # paramhandler.__init__(self,super(adjustparamstep,self),self.__proplist)# .__gproperties__)
        # gtk.HBox.__init__(self) # Not supposed to call superclass __init__ method, just gobject __init__ according to    http://www.pygtk.org/articles/subclassing-gobject/sub-classing-gobject-in-python.htm  
        gobject.GObject.__init__(self)

        self.myprops={ "dg-param": "", "dg-adjustparam": ""}
        #self.resize(1,1)
        # self.set_property("size",1)

        (self.gladeobjdict,self.gladebuilder)=build_from_file(os.path.join(os.path.split(sys.modules[self.__module__].__file__)[0],"adjustparamstep.glade"))   

        
        self.set_property("dg-param","")
        self.set_property("dg-paramdefault","")
        self.set_property("dc-valuetype","")
        self.set_property("dc-valuedefunits","")
        self.set_property("description","")
        self.set_property("dg-adjustparam","")

        #self.attach(self.gladeobjdict["adjustparamstep"],0,1,0,1,gtk.FILL,gtk.FILL,0,0)
        self.pack_start(self.gladeobjdict["adjustparamstep"],True,True,0)

        self.gladeobjdict["setparam"].connect("changed",self.changedcallback)
        self.gladeobjdict["readout"].connect("changed",self.changedcallback)
        self.gladeobjdict["step_descr_label"].set_selectable(True)

        pass
    
    def do_set_property(self,property,value):
        # print "set_property(%s,%s)" % (property.name,str(value))
        if property.name=="dg-param":
            self.myprops[property.name]=value
            self.gladeobjdict["readout_label"].set_property("label","  "+value+"  ")
            self.gladeobjdict["readout"].set_property("dg-param",value+"?")

            if self.myprops["dg-adjustparam"]=="":
                self.gladeobjdict["adjustparam_label"].set_property("label","  "+self.myprops["dg-param"]+"  ")
                self.gladeobjdict["setparam"].set_property("dg-param",self.myprops["dg-param"])
                pass
            else : 
                self.gladeobjdict["adjustparam_label"].set_property("label","  "+self.myprops["dg-adjustparam"]+"  ")
                self.gladeobjdict["setparam"].set_property("dg-param",self.myprops["dg-adjustparam"])
                pass

            pass
        elif property.name=="dg-adjustparam":
            self.myprops[property.name]=value
            
            if value=="":
                self.gladeobjdict["adjustparam_label"].set_property("label","  "+self.myprops["dg-param"]+"  ")
                self.gladeobjdict["setparam"].set_property("dg-param",self.myprops["dg-param"])
                pass
            else : 
                self.gladeobjdict["adjustparam_label"].set_property("label","  "+value+"  ")
                self.gladeobjdict["setparam"].set_property("dg-param",value)
                pass
            
            pass
        elif property.name=="dg-paramdefault":
            self.myprops[property.name]=value
            self.gladeobjdict["setparam"].set_property("dg-paramdefault",value)
            pass

        elif property.name=="description":
            self.myprops[property.name]=value
            #self.gladeobjdict["step_descr_label"].set_property("label","    "+value.replace("\n","\n    ")+"  ")
            self.gladeobjdict["step_descr_label"].set_markup(value)
            pass

        elif property.name=="dc-valuetype":
            self.myprops[property.name]=value
            pass

        elif property.name=="dc-valuedefunits":
            self.myprops[property.name]=value
            pass
        elif property.name=="dc-valuethreshold":
            self.myprops[property.name]=value
            pass

        else :
            raise IndexError("Bad property name %s" % (property.name))
        pass

    def do_get_property(self,property,value):
        return self.myprops[property.name]
    
    def dc_gui_init(self,guistate):
        # need next line if subclassing a dc_gui class
        # super(dg_readout).__dc_gui_init(self,guistate)
        
        self.gladeobjdict["setparam"].set_property("dg-paramdefault",self.myprops["dg-paramdefault"])



        dc_initialize_widgets(self.gladeobjdict,guistate)

        pass

    
    def changedcallback(self,event):
        equal=False
        
        try :
            valueclass=dc_value.value
            
            exec "valueclass=dc_value.%svalue" % (self.myprops["dc-valuetype"])
            
            valueset=valueclass(self.gladeobjdict["setparam"].get_text(),self.myprops["dc-valuedefunits"])
            
            valuereadout=valueclass(self.gladeobjdict["readout"].get_text(),self.myprops["dc-valuedefunits"])
            
        
            if self.myprops["dc-valuetype"]=="numericunits":
                if abs(valueset.value()-valuereadout.value()) < self.myprops["dc-valuethreshold"]:
                    equal=True
                    pass
                pass
            elif self.myprops["dc-valuetype"]=="string":
                # print "%s vs. %s" % (valueset.str,valuereadout.str)
                if self.myprops["dc-valuedefunits"]=="IGNORECASE":
                    equal =  (valueset.str.upper()==valuereadout.str.upper())
                    pass
                else :
                    equal =  (valueset.str==valuereadout.str)
                    pass
                pass
            else : 
                # print "%s vs. %s" % (valueset,valuereadout)
                equal =  (valueset==valuereadout)
                pass
            pass
        except: 
            if debug: 
                traceback.print_exc()
                pass
            pass
        
        if equal: 
            self.gladeobjdict["readout"].setbgcolor("green")           
            pass
        else :
            self.gladeobjdict["readout"].setbgcolor("red")            
            pass
        
        pass

    pass


gobject.type_register(adjustparamstep)  # required since we are defining new properties/signals
