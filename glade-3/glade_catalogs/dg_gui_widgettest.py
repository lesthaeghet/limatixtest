import os
import gobject
import gtk
#from gi.repository import GLib
#from gi.repository import Gtk
# gtk=Gtk

def mycallback(obj):
    print "got callback. obj.testparam=%s" % (str(obj.testparam))
    return True

# see: http://www.pygtk.org/articles/subclassing-gobject/sub-classing-gobject-in-python.htm
class dg_value(gtk.HBox):
    __gtype_name__ = 'dg_value'
    __gproperties__ = {
        "testparam": (gobject.TYPE_INT,
                      "testparam nickname",
                      "testparam description",
                      -50, # min value
                      60, # max value
                      0, # default value
                      gobject.PARAM_READWRITE) # flags
        
        }

    testparam=None
    
    entry=None

    def __init__(self):
        # gtk.HBox.__init__(self) # Not supposed to call superclass __init__ method, just gobject __init__ according to    http://www.pygtk.org/articles/subclassing-gobject/sub-classing-gobject-in-python.htm  
        gobject.GObject.__init__(self)
        self.testparam=0
        self.entry=gtk.Entry()
        self.entry.set_width_chars(10)
        self.entry.set_text(str(self.testparam))
        self.entry.set_editable(True)
        
        self.pack_start(self.entry)
        gobject.timeout_add(1000,mycallback,self)


        #self.frame = gtk.Frame()
        #self.pack_start(self.frame)
        #self._bb = gtk.HButtonBox()
        #self._bb.set_layout(gtk.BUTTONBOX_END)
        #self._bb.pack_start(gtk.Button(stock=gtk.STOCK_CLOSE))
        #self.pack_start(self._bb, expand=False)

        pass

    def do_set_property(self,property,value):
        # turns out if subclassing from a C widget, don't need
        # to pass on to super class. 
        #if property.name=="testparam":
            self.testparam=value
        #    pass
        #else :
        #    gtk.HBox.do_set_property(self,property,value)
        #    pass
        #pass
    
    def do_get_property(self,property):
        if property.name=="testparam":
            return self.testparam
        else :
            return gtk.HBox.do_get_property(self,property)
        pass
    
    pass


gobject.type_register(dg_value)  # required since we are defining new properties/signals
