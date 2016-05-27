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


from ..widgets.dc_wraplabel import dc_wraplabel

__pychecker__="no-import no-argsused"

# key parameter is "label" 
class textstep(dc_wraplabel):
    __gtype_name__="textstep"
    __gproperties__ = {
        "description": (gobject.TYPE_STRING,
                     "description of step",
                     "description of step",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags
        }

    description=None

    def __init__(self,checklist,step,xmlpath):
        self.description=""
        # gobject.GObject.__init__(self)
        # because we are derived from a python class with critical initialization, we MUST call the __init__ method
        dc_wraplabel.__init__(self)

        self.set_property("xalign",0.0)
        self.set_property("xpad",12)
        self.set_selectable(True)
        
        pass

    def do_set_property(self,property,value):
        if property.name=="description":
            self.description=value
            #self.set_property("label","    %s" % (value.replace("\n","\n   ")))
            self.set_markup(value)

            pass
        else :
            raise IndexError("Unknown property %s" % (property.name))
        
        pass

    def do_get_property(self,property):
        if property.name=="description":
            return self.description
        else : 
            raise IndexError("Unknown property %s" % (property.name))

        pass
    
    def dc_gui_init(self,guistate):
        pass

    

    pass

gobject.type_register(textstep)  # required since we are defining new properties/signals
