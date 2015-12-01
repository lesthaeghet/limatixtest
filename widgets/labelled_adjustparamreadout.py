import os
import sys

if not "gtk" in sys.modules:  # gtk3
    from gi.repository import Gtk as gtk
    from gi.repository import Gdk as gdk
    from gi.repository import GObject as gobject
    pass
else : 
    # gtk2
    import gobject
    import gtk
    import gtk.gdk as gdk
    pass


from adjustparamreadout import adjustparamreadout

__pychecker__="no-import no-argsused"


class labelled_adjustparamreadout(gtk.HBox):
    __gtype_name__="labelled_adjustparamreadout"
    __gproperties__= {
         "paramname": (gobject.TYPE_STRING,
                     "paramdb2 parameter to set",
                     "paramdb2 parameter to set",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags
         
         "editable": (gobject.TYPE_BOOLEAN,
                      "Should the entry be editable?",
                      "Should the entry be editable?",
                      True,
                      gobject.PARAM_READWRITE),
         "labelmarkup": (gobject.TYPE_STRING,
                     "Markup string for the label",
                     "Markup string for the label",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags
         
         }

    dc_gui_io=None
    label=None # label object
    labelmarkup=None
    entry=None # adjustparamreadout object
    
    def __init__(self):
        gobject.GObject.__init__(self)
        # gtk.HBox.__init__(self)
        

        self.label=gtk.Label()

        # self.labelmarkup=self.get_property("labelmarkup")
        #print "FOO",self.labelmarkup
        #sys.stdout.flush()

        if self.labelmarkup is None: 
            self.labelmarkup=""
            pass
        self.label.set_markup(self.labelmarkup+" ")


        self.entry=adjustparamreadout()
        #self.entry.set_property("paramname",self.get_property("paramname"))
        #self.entry.set_property("editable",self.get_property("editable"))
        self.pack_start(self.label,False,False,0)
        self.pack_start(self.entry,True,True,0)

        pass

    def isconsistent(self,inconsistentlist):
        return self.entry.isconsistent(inconsistentlist)
      
    def do_set_property(self,property,value):
        if property.name=="paramname" or property.name=="editable":
            self.entry.set_property(property.name,value)
            pass
        elif property.name=="labelmarkup":
            self.labelmarkup=value
            self.label.set_markup(value+" ")
            pass
        else :
            raise ValueError("Invalid property %s" % (property.name))
        pass

    def do_get_property(self,property):
        if property.name=="paramname" or property.name=="editable":
            return self.entry.get_property(property.name)
            
        elif property.name=="labelmarkup":
            return self.labelmarkup
        else :
            raise ValueError("Invalid property %s" % (property.name))
        pass
    
    
    def dc_gui_init(self,guistate):
        self.dc_gui_io=guistate.io
        self.entry.dc_gui_init(guistate)

        
        pass


gobject.type_register(labelled_adjustparamreadout)  # required since we are defining new properties/signals

#print "LAPR","gtk" in sys.modules
#sys.stdout.flush()
        
