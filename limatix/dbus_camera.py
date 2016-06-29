import sys
import os
import shutil
from lxml import etree
import traceback

if "gi" in sys.modules:  # gtk3
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk as gtk
    
    pass
else : 
    # gtk2
    import gtk

    pass

try: 
    import dbus
    import dbus.mainloop
    import dbus.mainloop.glib
except ImportError:
    dbus=None
    sys.stderr.write("Error importing dbus; dbus_camera support will not be available\n")
    pass

import xml.sax.saxutils

__pychecker__="no-argsused"

from . import dc_value

dbus_camera_name="edu.iastate.cnde.thermal.RicohCamera"
dbus_camera_path="/edu/iastate/cnde/thermal/RicohCamera"
dbus_camera_path_manual="/edu/iastate/cnde/thermal/RicohCamera_Manual"
newphoto_signal="newphoto"  # photo to be processed
processedphoto_signal="processedphoto"  # photo to be processed


def destroy_widget(obj,ev):
    obj.destroy()
    pass



class dbus_camera(object):
    system_bus=None
    dbusloop=None
    dbus_camera_newphoto_match=None
    dbus_camera_processedphoto_match=None
    hashhistory=None # Same hashhistory from the ricohcamera object
    explogwindow=None  # explogwindow -- None for ricohphoto program

    def __init__(self,hashhistory,explogwindow=None):

        if dbus is None:
            # import failed
            return 
        
        self.hashhistory=hashhistory
        self.explogwindow=explogwindow

        self.dbusloop=dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        
        self.system_bus = dbus.SystemBus()
        
        self.dbus_camera_newphoto_match=self.system_bus.add_signal_receiver(self.camera_newphoto_receiver,newphoto_signal,dbus_camera_name,None,dbus_camera_path)
        self.dbus_camera_newphoto_match=self.system_bus.add_signal_receiver(self.camera_newphoto_receiver,newphoto_signal,dbus_camera_name,None,dbus_camera_path_manual)

        self.dbus_camera_processedphoto_match=self.system_bus.add_signal_receiver(self.camera_processedphoto_receiver,processedphoto_signal,dbus_camera_name,None,dbus_camera_path)
        self.dbus_camera_processedphoto_match=self.system_bus.add_signal_receiver(self.camera_processedphoto_receiver,processedphoto_signal,dbus_camera_name,None,dbus_camera_path_manual)

        pass


    def camera_processedphoto_receiver(self,photopath,pmdpath,hashstr):
        sys.stderr.write("got processed photo\n")
        try :

            if hashstr in self.hashhistory:
                
                msgdialog=gtk.MessageDialog(type=gtk.MESSAGE_INFO,buttons=gtk.BUTTONS_CLOSE)
                msgdialog.set_markup(xml.sax.saxutils.escape("Received photo %s\nhash: %s" % (photopath,hashstr)))
                msgdialog.connect("response",destroy_widget)
                msgdialog.show()
                pass
            pass
        
        except:

            (exctype,excvalue)=sys.exc_info()[:2]
            sys.stderr.write("dbus_camera: %s processing photo input (%s,%s,%s): %s\n" % (str(exctype.__name__),photopath,pmdpath,hashstr,str(excvalue)))
            pass
        
        pass
    

    def camera_newphoto_receiver(self,photopath,pmdpath,hashstr):
        sys.stderr.write("got new photo\n")
        try :

            if hashstr in self.hashhistory:

                # read in PMD file
                # Use parser with remove_blank_text otherwise pretty_print                
                # won't work on output                       
                
                parser=etree.XMLParser(remove_blank_text=True)
                XMLtree=etree.parse(pmdpath,parser=parser)

                reqfilenamexpath=XMLtree.xpath("string(/dc:photometadata/dc:reqfilenamexpath)",namespaces={"dc":"http://limatix.org/datacollect"})
                
                self.explogwindow.explog.lock_ro()
                try : 
                    reqfilename=self.explogwindow.explog.xpath(reqfilenamexpath)
                    pass
                except: 
                    raise
                finally:
                    self.explogwindow.explog.unlock_ro()
                    pass


                dest=str(self.explogwindow.paramdb["dest"].dcvalue)

                num=1
                exists=True
                
                while exists:
                    filepath=os.path.join(dest,reqfilename % (num))

                    # abspath=os.path.abspath(filepath)
                    
                    if not filepath.endswith(".jpg"):
                        raise ValueError("Invalid file extension")
                    
                    newpmdpath=os.path.splitext(filepath)[0]+".pmd"
                    if not os.path.exists(filepath) and not os.path.exists(newpmdpath):
                        exists=False
                        pass
                    num+=1
                    if num > 999:
                        raise ValueError("Can not find unused filename")
                    pass
                
                photofilenameel=XMLtree.xpath("/dc:photometadata/dc:photofilename",namespaces={"dc":"http://limatix.org/datacollect"})[0]
                photofilenameel.text=os.path.split(filepath)[1]
                
                shutil.move(photopath,filepath)
                
                # Write out PMD
                outfh=open(newpmdpath,"wb")
                XMLtree.write(outfh,encoding='utf-8',pretty_print=True,xml_declaration=True)
                outfh.close()
                                
                # Add photo into paramdb element specified by dc:paramname element in XMLtree
                paramname=XMLtree.xpath("/dc:photometadata/dc:paramname",namespaces={"dc":"http://limatix.org/datacollect"})[0].text
                self.explogwindow.paramdb[paramname].requestval_sync(self.explogwindow.paramdb[paramname].dcvalue.copyandappend(dc_value.hrefvalue.from_rel_or_abs_path(".",filepath)))
                

                msgdialog=gtk.MessageDialog(type=gtk.MESSAGE_INFO,buttons=gtk.BUTTONS_CLOSE)
                msgdialog.set_markup(xml.sax.saxutils.escape("Received photo %s\nhash: %s" % (os.path.split(filepath)[1],hashstr)))
                msgdialog.connect("response",destroy_widget)
                msgdialog.show()

                
                pass
            pass
        
        except:

            (exctype,excvalue)=sys.exc_info()[:2]
            sys.stderr.write("dbus_camera: %s processing photo input (%s,%s,%s): %s\n" % (str(exctype.__name__),photopath,pmdpath,hashstr,str(excvalue)))
            traceback.print_exc()

            pass
        
        pass
    
    
    pass
    

