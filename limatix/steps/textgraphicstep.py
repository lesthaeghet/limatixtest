# important: indirectly uses dg_units (through dc_value)
# therefore main program should call dg_units.units_config("insert_basic_units")

import os
import sys

if "gi" in sys.modules:  # gtk3
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk as gtk
    from gi.repository import GObject as gobject
    from gi.repository import Gdk as gdk
    from gi.repository import GdkPixbuf

    INTERP_BILINEAR=GdkPixbuf.InterpType.BILINEAR
    pass
else : 
    # gtk2
    import gtk
    import gtk.gdk as gdk
    import gobject

    INTERP_BILINEAR=gdk.INTERP_BILINEAR
    
    pass

#sys.path.append("/home/sdh4/research/datacollect")
from .. import dc_value

from ..dc_gtksupp import build_from_file
from ..dc_gtksupp import dc_initialize_widgets

__pychecker__="no-import no-argsused"

# gtk superclass should be first of multiple inheritances
class textgraphicstep(gtk.HBox):
    __gtype_name__="textgraphicstep"
    __gproperties__ = {
        "image": (gobject.TYPE_STRING,
                     "Image file",
                     "Relative or absolute reference to image file",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags

        "width": (gobject.TYPE_INT,
                     "Image width",
                     "Image width to scale to. 0 means use orig size.",
                     0, # minimum value
                     1800, # maximum value
                     0, # default value 
                     gobject.PARAM_READWRITE), # flags


        "description": (gobject.TYPE_STRING,
                     "description of step",
                     "description of step",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags
        }
    __dcvalue_xml_properties={} # dictionary by property of dc_value class to be transmitted as a serialized  xmldoc
    __dcvalue_href_properties=frozenset(["image"]) # set of properties to be transmitted as an hrefvalue with the current directory as contextdir

    __proplist = ["image","width","description"]
    
    myprops=None
    checklist=None
    
    
    #searchdirs=None
    gladeobjdict=None
    
    def __init__(self,checklist,step,xmlpath):
        # paramhandler.__init__(self,super(adjustparamstep,self),self.__proplist)# .__gproperties__)
        # gtk.HBox.__init__(self) # Not supposed to call superclass __init__ method, just gobject __init__ according to    http://www.pygtk.org/articles/subclassing-gobject/sub-classing-gobject-in-python.htm  
        gobject.GObject.__init__(self)
        self.checklist=checklist

        self.myprops={"image": None, "width": None, "description": None}
        #self.resize(1,1)
        # self.set_property("size",1)

        (self.gladeobjdict,self.gladebuilder)=build_from_file(os.path.join(os.path.split(sys.modules[self.__module__].__file__)[0],"textgraphicstep.glade"))   
        
        #self.searchdirs=[]

        self.set_property("image",None)
        self.set_property("description","")
        self.set_property("width",0)

        #self.attach(self.gladeobjdict["adjustparamstep"],0,1,0,1,gtk.FILL,gtk.FILL,0,0)
        self.pack_start(self.gladeobjdict["textgraphicstep"],True,True,0)

        #self.gladeobjdict["commandbutton"].connect("clicked",self.changedcallback)

        self.gladeobjdict["step_descr_label"].set_selectable(True)


        pass

    def set_image(self,hrefval):
        #print("set_image1: %s" % (str(hrefval)))
        self.myprops["image"]=hrefval
        if hrefval is None or hrefval.isblank(): #  or len(self.searchdirs)==0:
            return

        #if str(hrefval)=="/usr/share/limatix/checklists/":
        #    import pdb as pythondb
        #    pythondb.set_trace()
        #print("set_image2: %s" % (str(hrefval)))

        path=hrefval.getpath() # absolute path or relative to our current directory
        
        if "gi" in sys.modules:  # gtk3
            rawpixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
                
            pass
        else : 
            #print("set_image3: %s" % (str(hrefval)))
            rawpixbuf = gdk.pixbuf_new_from_file(path)
            pass
        
        if self.myprops["width"] is not None and self.myprops["width"] != 0:

            height=int((rawpixbuf.get_height()*1.0/rawpixbuf.get_width())*self.myprops["width"])
            
            self.pixbuf=rawpixbuf.scale_simple(self.myprops["width"], height, INTERP_BILINEAR)
            pass
        else :
            self.pixbuf=rawpixbuf
            pass
        
        self.gladeobjdict["step_image"].set_from_pixbuf(self.pixbuf)

        self.gladeobjdict["step_image"].queue_resize()
        self.gladeobjdict["step_descr_label"].queue_resize()
        self.queue_resize()
        pass
    
    def do_set_property(self,property,value):
        # print "set_property(%s,%s)" % (property.name,str(value))
        if property.name=="image":
            hrefval=dc_value.hrefvalue(value,contexthref=self.checklist.xmldoc.getcontexthref())
            self.set_image(hrefval)
            pass
        elif property.name=="width":
            self.myprops[property.name]=value
            self.set_image(self.myprops["image"])
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
        if property.name=="image":
            return self.myprops["image"].attempt_relative_url(self.checklist.xmldoc.getcontexthref())
        
        return self.myprops[property.name]
    
    def dc_gui_init(self,guistate):
        # need next line if subclassing a dc_gui class
        # super(dg_readout).__dc_gui_init(self,io)
        

        #self.searchdirs.extend(guistate.searchdirs)

        self.set_image(self.myprops["image"])


        dc_initialize_widgets(self.gladeobjdict,guistate)

        pass

    #def resetchecklist(self):
    #    #self.gladeobjdict["commandbutton"].reset()
    #    pass
    pass


gobject.type_register(textgraphicstep)  # required since we are defining new properties/signals
