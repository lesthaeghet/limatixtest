import os
import sys


if "gi" in sys.modules:  # gtk3
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk as gtk
    from gi.repository import Gdk as gdk
    from gi.repository import GObject as gobject
    from gi.repository import GdkPixbuf

    INTERP_BILINEAR=GdkPixbuf.InterpType.BILINEAR

    pass
else : 
    # gtk2
    import gobject
    import gtk
    import gtk.gdk as gdk

    INTERP_BILINEAR=gdk.INTERP_BILINEAR

    pass

import paramdb2 as pdb

try : 
    import dc_value
    pass
except:
    sys.stderr.write("imagereadout: unable to import dc_value class... widget will not operate correctly")
    dc_value=None
    pass


# WARNING: Not thread safe, in part because of 
#  changedinhibit flag

from dc_gtksupp import paramhandler

__pychecker__="no-import no-argsused no-constCond"

# gtk superclass should be first of multiple inheritances
class imagereadout(gtk.Image,paramhandler):
    __gtype_name__="imagereadout"
    __gproperties__ = {

        "paramname": (gobject.TYPE_STRING,
                     "paramdb2 parameter to view",
                     "paramdb2 parameter to view",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags

        "width": (gobject.TYPE_INT,
                     "width",
                     "maximum width to scale image to, or -1 for unset",
                     -1, # minimum value
                     50000, # maximum value... essentially infinite
                     -1, # default value 
                     gobject.PARAM_READWRITE), # flags
        
        "height": (gobject.TYPE_INT,
                  "height",
                  "maximum height to scale image to, or -1 for unset",
                  -1, # minimum value
                  50000, # maximum value... essentially infinite
                  -1, # default value 
                  gobject.PARAM_READWRITE), # flags

        }
    __proplist = ["paramname","width","height"] 

    __imagereadout_unique=None
    paramdb=None
    param=None
    errorflag=None
    fixed=None
    fixedvalue=None
    querypending=None
    lastimage=None

    newvalue_notify=None
    
    
    def __init__(self):

        gobject.GObject.__init__(self)
        paramhandler.__init__(self,super(imagereadout,self),self.__proplist)
        
        # gtk.HBox.__init__(self) # Not supposed to call superclass __init__ method, just gobject __init__ according to    http://www.pygtk.org/articles/subclassing-gobject/sub-classing-gobject-in-python.htm  
        # self.myprops["dg-paramsuffix"]=""

        self.fixed=False
        self.fixedvalue=None

        self.errorflag=False
        self.querypending=False  # queries started in dc_gui_init

        pass

    def set_fixed(self,fixed,fixedvalue=None,fixeddisplayfmt=None):
        if fixedvalue is None:
            # provide generic blank
            fixedvalue=dc_value.stringvalue("")
            pass
        wasfixed=self.fixed
        self.fixed=fixed
        if fixed:
            self.fixedvalue=fixedvalue
            pass

        if not wasfixed and fixed:
            # switch into fixed state: unsync_to_paramdb
            self.unsync_to_paramdb()
            pass
        if wasfixed and not fixed:
            # switch out of fixed state: sync_to_paramdb()
            self.sync_to_paramdb()
            pass
        
        
        self.update_image() # update image if appropriate
        pass

    def update_image(self):
        if self.fixed:
            image=self.fixedvalue
            pass
        else:
            image=self.param.dcvalue
            pass

        if image is self.lastimage:
            return # no need to update

        if image==lastimage:
            self.lastimage=image
            # still no need to update
            return

        # use numpy to convert PIL image to pixbuf
        if image is None:
            # blank case
            arr=np.zeros((2,2),dtype=np.uint8)
            pass
        else:
            arr=np.array(image)
            pass

        if "gi" in sys.modules:  # gtk3           
            pixbuf=GdkPixbuf.Pixbuf.new_from_array(arr,gdk.COLORSPACE_RGB,8)
            pass
        else:
            pixbuf=gdk.pixbuf_new_from_array(arr,gdk.COLORSPACE_RGB,8)
            pass
            

        width=pixbuf.get_width()
        height=pixbuf.get_width()

            
        aspect_ratio=float(width)/height

        if self.myprops["width"] >= 0 and self.myprops["height"] >= 0:
            # both width and height given
            height_from_width=self.myprops["width"]/aspect_ratio
            if height_from_width > self.myprops["height"]:
                # use aspect ratio and specified height
                scaleheight=self.myprops["height"]
                scalewidth=aspect_ratio*self.myprops["height"]
                pass
            else:
                # use aspect ratio and specified width
                scalewidth=self.myprops["width"]
                scaleheight=self.myprops["width"]/aspect_ratio
                pass
            pass
        elif self.myprops["width"] >= 0:
            # just width given
            # use aspect ratio and specified width
            scalewidth=self.myprops["width"]
            scaleheight=self.myprops["width"]/aspect_ratio
            pass
        elif self.myprops["height"] >= 0:
            # just height given
            # use aspect ratio and specified height
            scaleheight=self.myprops["height"]
            scalewidth=aspect_ratio*self.myprops["height"]
            pass
        else:
            # Nothing given... do not change size
            scalewidth=width
            scaleheight=height
            pass

        if scalewidth != width or scaleheight != height:
            pixbuf=pixbuf.scale_simple(scalewidth,scaleheight,INTERP_BILINEAR)
            pass
        
        self.set_from_pixbuf(pixbuf)
        
        self.lastimage=image
        pass
    
    
    def newvalue(self,param,condition):
        # (condition not used)
        if self.fixed:
            return

        self.update_image()        

        pass
    
    def dc_gui_init(self,guistate):
        # need next line if subclassing a dc_gui class
        # super(dc_readout).__dc_gui_init(self,guistate)

        

        if self.paramdb is None:  # allow manual initialization of paramdb, in case we are to use a non-default paramdb
            self.paramdb=guistate.paramdb
            pass
        self.__imagereadout_unique=[]



        pass

    def sync_to_paramdb(self):
        if self.myprops["paramname"] not in self.paramdb:
            raise ValueError("No parameter database entry for \"%s\". Does this file need to be viewed within datacollect, and are you using the correct .dcc file?" % (self.myprops["paramname"]))
        self.param=self.paramdb[self.myprops["paramname"]]

        self.newvalue_notify=self.param.addnotify(self.newvalue,pdb.param.NOTIFY_NEWVALUE,)

        pass

    def unsync_to_paramdb(self):
        self.param.remnotify(self.newvalue_notify)
        self.newvalue_notify=None
        pass
    

    pass


gobject.type_register(imagereadout)  # required since we are defining new properties/signals
