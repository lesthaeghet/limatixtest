# TODO:Use hash history and an extra dbus signal to pop up a dialog
# when a photo is received

# Camera configuration 
# --------------------
# * Supports Ricoh G700SE camera
# * Camera must have a memo file with a single empty entry "barcode"
# * Camera wireless must be configured to ftp to appropriate destination
# * "Card Sequence Number" in setup menu should be set to ON. This makes
#   the camera keep incrementing photo numbers rather than reset. 
#   STILL NEED TO DO THIS
# * Camera should be in Camera Memo Mode 1, so that a single temporary
#   memo is used
# * Quick send mode: Auto 
# * Memo Menu: Memo Warning should be ON (STILL NEED TO DO)
# * FTP Send menu: Recommend PASV mode

import os
import os.path
import sys
try: 
    import cStringIO # python 2
    pass
except: 
    from io import StringIO # python 3
    pass

import array
import string
import traceback
if "gi" in sys.modules:  # gtk3
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk as gtk
    from gi.repository import Gdk as gdk
    from gi.repository import GObject as gobject
    from gi.repository import GdkPixbuf
    from gi.repository import Gio
    from gi.repository import GLib
    pass
else : 
    # gtk2
    import gobject
    import gtk
    import gtk.gdk as gdk
    pass
    
import numpy as np
from lxml import etree

import dg_timestamp

from PIL import Image


from .readablehash import readablehash
from .dc_gtksupp import build_from_file
from .dc_gtksupp import dc_initialize_widgets

from .dc_value import numericunitsvalue as numericunitsv
from .dc_value import stringvalue as stringv

from .dbus_camera import dbus_camera

from . import paramdb2 as pdb

try : 
    import qrcode # requires python-qrcode package https://github.com/lincolnloop/python-qrcode
    pass
except: 
    sys.stderr.write("ricohcamera.py: Error importing qrcode module. Make sure python-qrcode package is installed https://github.com/lincolnloop/python-qrcode\n")
    pass


__pychecker__="no-import no-argsused"


class dummy(object):
    pass
thisdir=os.path.split(sys.modules[dummy.__module__].__file__)[0]



DC='{http://limatix.org/datacollect}'

xpathnamespaces={ 
    #'chx': 'http://limatix.org/checklist',
    'dc': 'http://limatix.org/datacollect',
    #'dcv': 'http://limatix.org/dcvalue',
    }


# This module is use to generate a window with a QR code that is passed
# to a Ricoh G700SE camera, which FTP's an image that is in turn 
# dispatched to the specified destination

# class ricohphotorequest represents the window that shows the QR code
class ricohphotorequest(gtk.Window):
    gladefile=None
    paramdb=None
    private_paramdb=None
    paramname=None
    filename=None
    qrxml=None
    qrxmlstring=None
    qrxmlhash=None
    qrstring=None
    hashhistory=None

    gladeobjdict=None
    builder=None
    #dc_gui_io=None
    guistate=None

    reqfilenamexpath=None

    commentnotify=None
    specimennotify=None
    perfbynotify=None
    datenotify=None
    destnotify=None
    reqfilenamenotify=None

    dbuscamera=None # dbus_camera.dbus_camera object... this is persistent and available to respond to incoming photos, even after the ricohcamera window is gone. 

    def __init__(self,paramdb,paramname,reqfilenamexpath=None,explogwindow=None,gladefile="ricohcamera.glade"):
        # reqfilenamexpath should be an xpath expression that evaluates to a 
        # string representing the desired filename. It will be applied to the experiment log.
        # It should include a '%.3d' representing where the file index number should go.
        # if reqfilenamexpath is not provided, it is presumed there is a 
        # paramdb entry called "reqfilename" (again with a %d) that has the filename which should be appended to dest
        # if reqfilenamexpath is provided, explogwindow should be provided, as the back link is necessary for processing by dbus_camera


        # paramname is datacollect parameter that should accumulate the photos
        
        gobject.GObject.__init__(self)


        self.gladefile=gladefile
        self.paramdb=paramdb
        self.private_paramdb=pdb.paramdb(None)
        self.private_paramdb.addparam("comments",stringv)
        # self.private_paramdb["comments"].requestvalstr_sync("enter comments here")
        self.hashhistory={}
        
        self.paramname=paramname

        self.reqfilenamexpath=reqfilenamexpath


        (self.gladeobjdict,self.builder)=build_from_file(os.path.join(thisdir,self.gladefile))
        
        self.gladeobjdict["commententry"].paramdb=self.private_paramdb

        self.set_title("Take photo with Ricoh camera")
        self.build_qr()
        

        # NOTE: addnotifies must be paird with remnotifies when the window is destroyed
        self.commentnotify=self.private_paramdb["comments"].addnotify(self.newparams,self.private_paramdb["comments"].NOTIFY_NEWVALUE)
        self.specimennotify=self.paramdb["specimen"].addnotify(self.newparams,self.paramdb["specimen"].NOTIFY_NEWVALUE)
        self.perfbynotify=self.paramdb["perfby"].addnotify(self.newparams,self.paramdb["specimen"].NOTIFY_NEWVALUE)
        self.datenotify=self.paramdb["date"].addnotify(self.newparams,self.paramdb["date"].NOTIFY_NEWVALUE)
        self.destnotify=self.paramdb["dest"].addnotify(self.newparams,self.paramdb["dest"].NOTIFY_NEWVALUE)
        if self.reqfilenamexpath is None:
            self.reqfilenamenotify=self.paramdb["reqfilename"].addnotify(self.newparams,self.paramdb["reqfilename"].NOTIFY_NEWVALUE)
            pass
        


        self.add(self.gladeobjdict["ricohcamera"])


        self.dbuscamera=dbus_camera(self.hashhistory,explogwindow)

        pass
    
    def closehandler(self,obj,ev):
        self.hide()

        self.private_paramdb["comments"].remnotify(self.commentnotify)
        self.paramdb["specimen"].remnotify(self.specimennotify)
        self.paramdb["perfby"].remnotify(self.perfbynotify)
        self.paramdb["date"].remnotify(self.datenotify)
        self.paramdb["dest"].remnotify(self.destnotify)
        if self.reqfilenamexpath is None:
            self.paramdb["reqfilename"].remnotify(self.reqfilenamenotify)
            pass
        
        self.commentnotify=None
        self.specimennotify=None
        self.perfbynotify=None
        self.datenotify=None
        self.destnotify=None
        self.reqfilenamenotify=None


        self.gladefile=None
        self.paramdb=None
        self.private_paramdb=None
        self.paramname=None
        self.filename=None
        self.qrxml=None
        self.qrxmlstring=None
        self.qrxmlhash=None
        self.qrstring=None
        self.gladeobjdict=None
        self.builder=None
        self.dc_gui_io=None
        self.guistate=None
        self.hashhistory=None
        self.dbuscamera=None # dbuscamera object will be persistant because of dbus's reference
        self.destroy()

        
        return True

    def build_qr(self):
        # Should probably modify this to use xmldoc. 
        self.qrxml=etree.Element(DC+"photometadata",nsmap=xpathnamespaces)
        
        

        specimentag=etree.Element(DC+"specimen")
        self.paramdb["specimen"].dcvalue.xmlrepr(None,specimentag)
        self.qrxml.append(specimentag)

        perfbytag=etree.Element(DC+"perfby")
        self.paramdb["perfby"].dcvalue.xmlrepr(None,perfbytag)
        self.qrxml.append(perfbytag)

        datetag=etree.Element(DC+"date")
        self.paramdb["date"].dcvalue.xmlrepr(None,datetag)
        self.qrxml.append(datetag)

        desttag=etree.Element(DC+"dest")
        self.paramdb["dest"].dcvalue.xmlrepr(None,desttag)
        self.qrxml.append(desttag)

        if self.reqfilenamexpath is not None:
            filenametag=etree.Element(DC+"reqfilenamexpath")
            filenametag.text=self.reqfilenamexpath
            self.qrxml.append(filenametag)
            pass
        else :
            filenametag=etree.Element(DC+"reqfilename")
            self.paramdb["reqfilename"].dcvalue.xmlrepr(None,filenametag)
            self.qrxml.append(filenametag)
            pass

        if self.paramname is not None:
            paramnametag=etree.Element(DC+"paramname")
            paramnametag.text=self.paramname
            self.qrxml.append(paramnametag)
            pass


        commenttag=etree.Element(DC+"comment")
        commenttag.text=str(self.private_paramdb["comments"].dcvalue)
        self.qrxml.append(commenttag)
        
        timestamptag=etree.Element(DC+"reqtimestamp")
        timestamp=dg_timestamp.roundtosecond(dg_timestamp.now()).isoformat()
        timestamptag.text=timestamp
        self.qrxml.append(timestamptag)
        
        self.qrxmlstring=etree.tostring(self.qrxml,pretty_print=True,encoding='utf-8')
        self.qrxmlhash=readablehash(self.qrxmlstring)
        self.hashhistory[self.qrxmlhash]=None  # store hash long-term

        self.qrstring=self.qrxmlhash+self.qrxmlstring

        labeltext=""
        labeltext+="specimen: %s\n" % (str(self.paramdb["specimen"].dcvalue))
        labeltext+="perfby: %s\n" % (str(self.paramdb["perfby"].dcvalue))
        labeltext+="date: %s\n" % (str(self.paramdb["date"].dcvalue))
        labeltext+="dest: %s\n" % (str(self.paramdb["dest"].dcvalue))
        if self.reqfilenamexpath is not None:
            labeltext+="reqfilenamexpath: %s\n" % (self.reqfilenamexpath)
            pass
        else :
            labeltext+="reqfilename: %s\n" % (str(self.paramdb["reqfilename"].dcvalue))
            pass
        if self.paramname is not None:
            labeltext+="paramname: %s\n" % (self.paramname)
            pass
        labeltext+="reqtimestamp: %s\n" % (timestamp)
        labeltext+="hash: %s\n" % (self.qrxmlhash)
        # labeltext+="len: %d\n" % (len(self.qrxmlstring))

        self.gladeobjdict["QRtextlabel"].set_text(labeltext)
        
        
        


        img=qrcode.make(self.qrstring)

        #fh=file("/tmp/out.png","w")
        #img.save(fh)
        #fh.close()
        
        origsize=img._img.size

        scaledimg=img._img.resize((origsize[0]/2,origsize[1]/2))
        
        rgbimg=scaledimg.convert("RGB")
        #print rgbimg

        arr3=np.array(rgbimg)
        #print arr3
        #print arr3.shape
        #print arr3.dtype


        if not "gtk" in sys.modules: 
            # gtk3

            # mega-hack because GdkPixbuf.Pixbuf.new_from_data is inoperable:

            # Use PIL to dump a PNG representation in a StringIO buffer. 
            SIO=cStringIO.StringIO()
            rgbimg.save(SIO,format='PNG')
            
            # Read this buffer with a Gio.MemoryInputStream()
            Stream=Gio.MemoryInputStream.new_from_bytes(GLib.Bytes.new(SIO.getvalue()))
            SIO.close()
            
            #pixbuf=GdkPixbuf.Pixbuf.new_from_data(self.QRstore, GdkPixbuf.Colorspace.RGB, False, 8, arr3.shape[0],arr3.shape[1],arr3.shape[0]*3,None,None)
            # Create the pixbuf from the MemoryInputStream
            pixbuf=GdkPixbuf.Pixbuf.new_from_stream(Stream,None)

            pass
        else : 
            pixbuf=gdk.pixbuf_new_from_array(arr3, gdk.COLORSPACE_RGB, 8)
            pass
            
        self.gladeobjdict["QRimage"].set_from_pixbuf(pixbuf)
        
        pass

    def newparams(self,param,condition):
        self.build_qr()

        pass


    def dc_gui_init(self,guistate):
        # need next line if subclassing a dc_gui class
        # super(dc_readout).__dc_gui_init(self,guistate)
        
        self.guistate=guistate
        
        # self.dc_gui_io=guistate.io
        
        dc_initialize_widgets(self.gladeobjdict,guistate)
        
        self.connect("delete-event",self.closehandler)
        
        pass
    
    pass
