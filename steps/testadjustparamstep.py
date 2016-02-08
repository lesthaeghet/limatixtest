import sys


if "--gtk3" in sys.argv or sys.version_info[0] >= 3:  # gtk3
    from gi.repository import Gtk as gtk
    from gi.repository import GObject as gobject
    pass
else : 
    # gtk2
    import gtk
    import gobject
    pass


import dg_io

sys.path.append('.')
sys.path.append('..')
sys.path.append('../widgets')

from dataguzzler_readout import dg_readout
from dataguzzler_setparam import dg_setparam
from adjustparamstep import adjustparamstep
import dc_gtksupp

iohandler=dg_io.io()

aps=adjustparamstep(None,None,None)
aps.set_property("dg-param","TRIG:MODE")
aps.set_property("dg-paramdefault","INTERNAL")
aps.set_property("dc-valuetype","stringvalue")
aps.set_property("dc-valuedefunits","IGNORECASE")
aps.set_property("description","test step  ")


aps.dc_gui_init(dc_gtksupp.guistate(iohandler,[]))
win=gtk.Window(gtk.WINDOW_TOPLEVEL)
win.add(aps)
win.show_all()
gtk.main()
