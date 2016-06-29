import sys
import os
import re
from lxml import etree


try:
    import dbus
    import dbus.mainloop
    import dbus.mainloop.glib
    pass
except ImportError:
    dbus=None
    pass
    
if "gi" in sys.modules:  # gtk3
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk as gtk
    
    pass
else : 
    # gtk2
    import gobject
    import gtk
    pass

from . import paramdb2

import xml.sax.saxutils

__pychecker__="no-import no-argsused"


dbus_barcode_name="edu.iastate.cnde.thermal.BarcodeReader"
dbus_barcode_path="/edu/iastate/cnde/thermal/barcode"
dbus_barcode_signal_name="read"


# This module supports reading data from a dbus-enabled barcode reader

def destroy_widget(obj,ev):
    obj.destroy()
    pass



class dc_dbus_barcode(object):
    paramdb=None
    system_bus=None
    barcode_match=None
    dbusloop=None

    def __init__(self,paramdb):
        if dbus is None:  # Import failed
            return 
        self.paramdb=paramdb

        self.dbusloop=dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        self.system_bus = dbus.SystemBus()
        
        self.barcode_match=self.system_bus.add_signal_receiver(self.barcode_receiver,dbus_barcode_signal_name,dbus_barcode_name,None,dbus_barcode_path)

        pass

    def barcode_receiver(self,barcodestring,typestring):
        try :
            
            # Check for abbreviated form <specimen/>C00-101
            matchobj=re.match(r"""<([^&#<>]+)/>([^<]*)""",barcodestring)
            # print matchobj
            if matchobj is not None:
                # print matchobj.groups()
                barcodexml=etree.Element(matchobj.group(1))
                barcodexml.text=matchobj.group(2)
                
                pass
            else :
                # full XML form
                barcodexml=etree.XML(barcodestring)
                # print barcodexml
                pass
            
            if barcodexml.tag in self.paramdb:
                value=self.paramdb[barcodexml.tag].paramtype.fromxml(None,barcodexml)
                if self.paramdb[barcodexml.tag].dcvalue.isblank():
                    self.paramdb[barcodexml.tag].requestval(value)
                    pass
                elif barcodexml.tag=="specimen" and str(self.paramdb[barcodexml.tag].dcvalue)=="disabled":
                    # <specimen> and the current value in paramdb is the special value "disabled"
                    # Do nothing.
                    pass
                elif self.paramdb[barcodexml.tag].dcvalue != value: 
                    warningdialog=gtk.MessageDialog(type=gtk.MESSAGE_WARNING,buttons=gtk.BUTTONS_OK)
                    warningdialog.set_markup(xml.sax.saxutils.escape("Warning: Barcode %s for non-blank field \"%s\" ignored" % (barcodestring,self.paramdb[barcodexml.tag].dcvalue)))
                    warningdialog.connect("response",destroy_widget)
                    warningdialog.show()
                    
                    pass
                
                pass
            else :
                warningdialog=gtk.MessageDialog(type=gtk.MESSAGE_WARNING,buttons=gtk.BUTTONS_OK)
                warningdialog.set_markup(xml.sax.saxutils.escape("Warning: Barcode %s for unknown field ignored.\n(Do you need to add it to your datacollect configuration file?)" % (barcodestring)))
                warningdialog.connect("response",destroy_widget)
                warningdialog.show()
                    
                pass
            
            pass
        except:

            (exctype,excvalue)=sys.exc_info()[:2]
            sys.stderr.write("dc_dbus: %s processing barcode input \"%s\": %s\n" % (str(exctype.__name__),barcodestring,str(excvalue)))
            pass
        
        pass
    
    
    
    pass
    

