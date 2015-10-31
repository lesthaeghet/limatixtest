# important: indirectly uses dg_units (through dc_value)
# therefore main program should call dg_units.units_config("insert_basic_units")

import os
import sys
import traceback
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

debug=False  # set to true to enable more debug output
__pychecker__="no-import no-argsused"

# gtk superclass should be first of multiple inheritances
class multiparamstep(gtk.HBox):
    __gtype_name__="multiparamstep"
    __gproperties__ = {
        "dg-param1": (gobject.TYPE_STRING,
                     "Dataguzzler parameter",
                     "Name of dataguzzler parameter",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags

        "dg-paramdefault1": (gobject.TYPE_STRING,
                     "dataguzzler parameter default value",
                     "Dataguzzler parameter default value",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags

        "dc-valuetype1": (gobject.TYPE_STRING,
                     "datacollect value type",
                     "Datacollect value type (class defined in dc_value)",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags

        "dc-valuethreshold1": (gobject.TYPE_DOUBLE,
                     "datacollect value threshold",
                     "Datacollect value equality comparison threshold",
                     0.0, # minimum value
                     float("Inf"), # maximum value
                     0.0, # default value 
                     gobject.PARAM_READWRITE), # flags

        "dc-valuedefunits1": (gobject.TYPE_STRING,
                     "datacollect value default units",
                     "Datacollect value default units for numeric parameters. Should match units as interpreted by Dataguzzler. For string parameters set this to IGNORECASE to use case insensitive string comparisions)",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags

        "dg-param2": (gobject.TYPE_STRING,
                     "Dataguzzler parameter",
                     "Name of dataguzzler parameter",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags

        "dg-paramdefault2": (gobject.TYPE_STRING,
                     "dataguzzler parameter default value",
                     "Dataguzzler parameter default value",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags

        "dc-valuetype2": (gobject.TYPE_STRING,
                     "datacollect value type",
                     "Datacollect value type (class defined in dc_value)",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags

        "dc-valuethreshold2": (gobject.TYPE_DOUBLE,
                     "datacollect value threshold",
                     "Datacollect value equality comparison threshold",
                     0.0, # minimum value
                     float("Inf"), # maximum value
                     0.0, # default value 
                     gobject.PARAM_READWRITE), # flags

        "dc-valuedefunits2": (gobject.TYPE_STRING,
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
    __proplist = ["dg-param1","dg-paramdefault1","dc-valuetype1","dc-valuethreshold1","dc-valuedefunits1","description1","dg-param2","dg-paramdefault2","dc-valuethreshold1","dc-valuetype2","dc-valuedefunits2","description2"]
    
    myprops=None
    
    # "dg-param" might be TRIG:MODE
    
                      
    dc_gui_io=None
    gladeobjdict=None
    
    def __init__(self,checklist,step,xmlpath):
        # paramhandler.__init__(self,super(adjustparamstep,self),self.__proplist)# .__gproperties__)
        # gtk.HBox.__init__(self) # Not supposed to call superclass __init__ method, just gobject __init__ according to    http://www.pygtk.org/articles/subclassing-gobject/sub-classing-gobject-in-python.htm  
        gobject.GObject.__init__(self)

        self.myprops={}
        #self.resize(1,1)
        # self.set_property("size",1)

        (self.gladeobjdict,self.gladebuilder)=build_from_file(os.path.join(os.path.split(sys.modules[self.__module__].__file__)[0],"multiparamstep.glade"))   
        
        self.set_property("dg-param1","")
        self.set_property("dg-paramdefault1","")
        self.set_property("dc-valuetype1","")
        self.set_property("dc-valuedefunits1","")
        self.set_property("dg-param2","")
        self.set_property("dg-paramdefault2","")
        self.set_property("dc-valuetype2","")
        self.set_property("dc-valuedefunits2","")
        self.set_property("description","")

        #self.attach(self.gladeobjdict["multiparamstep"],0,1,0,1,gtk.FILL,gtk.FILL,0,0)
        self.pack_start(self.gladeobjdict["multiparamstep"],True,True,0)

        self.gladeobjdict["setparam1"].connect("changed",self.changedcallback)
        self.gladeobjdict["readout1"].connect("changed",self.changedcallback)

        self.gladeobjdict["setparam2"].connect("changed",self.changedcallback)
        self.gladeobjdict["readout2"].connect("changed",self.changedcallback)

        self.gladeobjdict["step_descr_label"].set_selectable(True)

        pass
    
    def do_set_property(self,property,value):
        # print "set_property(%s,%s)" % (property.name,str(value))
        if property.name=="dg-param1":
            self.myprops[property.name]=value
            self.gladeobjdict["param_label1"].set_property("label","  "+value+"  ")
            self.gladeobjdict["setparam1"].set_property("dg-param",value)
            self.gladeobjdict["readout1"].set_property("dg-param",value+"?")
            pass
        
        elif property.name=="dg-paramdefault1":
            self.myprops[property.name]=value
            self.gladeobjdict["setparam1"].set_property("dg-paramdefault",value)
            pass

        elif property.name=="dc-valuetype1":
            self.myprops[property.name]=value
            pass

        elif property.name=="dc-valuedefunits1":
            self.myprops[property.name]=value
            pass
        elif property.name=="dc-valuethreshold1":
            self.myprops[property.name]=value
            pass
        elif property.name=="dg-param2":
            self.myprops[property.name]=value
            self.gladeobjdict["param_label2"].set_property("label","  "+value+"  ")
            self.gladeobjdict["setparam2"].set_property("dg-param",value)
            self.gladeobjdict["readout2"].set_property("dg-param",value+"?")
            pass
        
        elif property.name=="dg-paramdefault2":
            self.myprops[property.name]=value
            self.gladeobjdict["setparam2"].set_property("dg-paramdefault",value)
            pass

        elif property.name=="dc-valuetype2":
            self.myprops[property.name]=value
            pass

        elif property.name=="dc-valuedefunits2":
            self.myprops[property.name]=value
            pass
        elif property.name=="dc-valuethreshold2":
            self.myprops[property.name]=value
            pass

        elif property.name=="description":
            self.myprops[property.name]=value
            #self.gladeobjdict["step_descr_label"].set_property("label","    "+value.replace("\n","\n    ")+"  ")  
            self.gladeobjdict["step_descr_label"].set_markup(value)  
            pass


        else :
            raise IndexError("Bad property name %s" % (property.name))
        pass

    def do_get_property(self,property,value):
        return self.myprops[property.name]
    
    def dc_gui_init(self,guistate):
        # need next line if subclassing a dc_gui class
        # super(dg_readout).__dc_gui_init(self,guistate)
        
        self.gladeobjdict["setparam1"].set_property("dg-paramdefault",self.myprops["dg-paramdefault1"])

        self.gladeobjdict["setparam2"].set_property("dg-paramdefault",self.myprops["dg-paramdefault2"])


        self.dc_gui_io=guistate.io

        dc_initialize_widgets(self.gladeobjdict,guistate)

        pass

    
    def changedcallback(self,event):
        equal=False
        
        try :
            valueclass1=dc_value.value
            
            exec "valueclass1=dc_value.%svalue" % (self.myprops["dc-valuetype1"])

            valueset1=valueclass1(self.gladeobjdict["setparam1"].get_text(),self.myprops["dc-valuedefunits1"])
            
            valuereadout1=valueclass1(self.gladeobjdict["readout1"].get_text(),self.myprops["dc-valuedefunits1"])
            
            if self.myprops["dc-valuetype1"]=="numericunits":
                if abs(valueset1.value()-valuereadout1.value()) < self.myprops["dc-valuethreshold1"]:
                    equal=True
                    pass
                pass
            elif self.myprops["dc-valuetype1"]=="string":
                if self.myprops["dc-valuedefunits1"]=="IGNORECASE":
                    equal =  (valueset1.str.upper()==valuereadout1.str.upper())
                    pass
                else :
                    equal =  (valueset1.str==valuereadout1.str)
                    pass
                pass
            else : 
                equal =  (valueset1==valuereadout1)
                pass
            pass
        except :
            if debug: 
                traceback.print_exc()
                pass
            
            pass

        if equal: 
            self.gladeobjdict["readout1"].setbgcolor("green")           
            pass
        else :
            self.gladeobjdict["readout1"].setbgcolor("red")            
            pass
        

        equal=False
        
        try : 
            valueclass2=dc_value.value
            exec "valueclass2=dc_value.%svalue" % (self.myprops["dc-valuetype2"])
            valueset2=valueclass2(self.gladeobjdict["setparam2"].get_text(),self.myprops["dc-valuedefunits2"])
            
            valuereadout2=valueclass2(self.gladeobjdict["readout2"].get_text(),self.myprops["dc-valuedefunits2"])
            
            if self.myprops["dc-valuetype2"]=="numericunits":
                if abs(valueset2.value()-valuereadout2.value()) < self.myprops["dc-valuethreshold2"]:
                    equal=True
                    pass
                pass
            elif self.myprops["dc-valuetype2"]=="string":
                if self.myprops["dc-valuedefunits2"]=="IGNORECASE":
                    equal =  (valueset2.str.upper()==valuereadout2.str.upper())
                    pass
                else :
                    equal =  (valueset2.str==valuereadout2.str)
                    pass
                pass
            else : 
                equal =  (valueset2==valuereadout2)
                pass
            pass
        except: 
            if debug: 
                traceback.print_exc()
                pass
            
            pass
        
        if equal: 
            self.gladeobjdict["readout2"].setbgcolor("green")           
            pass
        else :
            self.gladeobjdict["readout2"].setbgcolor("red")            
            pass
        
        pass

    pass


gobject.type_register(multiparamstep)  # required since we are defining new properties/signals
