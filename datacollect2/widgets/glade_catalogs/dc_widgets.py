import os
import os.path
import sys
import gobject
import gtk

#class dummy(object):
#    pass

#sys.path.append('/home/sdh4/research/dataguzzler/gui2') #!!!fixme

#sys.path.append(os.path.join(os.path.split(sys.modules[dummy.__module__].__file__)[0],"../../widgets"))
#sys.path.append(os.path.join(os.path.split(sys.modules[dummy.__module__].__file__)[0],"../../lib"))
#sys.path.append(os.path.join(os.path.split(sys.modules[dummy.__module__].__file__)[0],"../.."))

from datacollect2 import dc_gtksupp

dc_gtksupp.import_widgets()

#from adjustparamreadout import adjustparamreadout
#from labelled_adjustparamreadout import labelled_adjustparamreadout
#from selectableparamreadout import selectableparamreadout
#from labelled_selectableparamreadout import labelled_selectableparamreadout
#from paragraphparam import paragraphparam
#from excitationparam import excitationparam
#from imagereadout import imagereadout

#from dc_wraplabel import dc_wraplabel

#from explogmethodbutton import explogmethodbutton  # Seems to Have Been Moved To Trash

# TO ADD A NEW WIDGET
#  1.  Add from xxx import yyy statement above
#  2.  In dg_gui_catalog.xml create new glade-widget-class
#  3.  In dg_gui_catalog.xml add new glade-widget-class-ref to the glade-widget-group

#import dg_io


# use these next lines when porting to gtk3
#from gi.repository import GLib
#from gi.repository import Gtk
