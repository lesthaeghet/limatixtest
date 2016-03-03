
# Modified from:   http://git.gnome.org/browse/meld/plain/meld/ui/wraplabel.py

# Copyright (c) 2005 VMware, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Python translation from wrapLabel.{cc|h} by Gian Mario Tagliaretti

import sys

if "gi" in sys.modules:  # gtk3
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk as gtk
    from gi.repository import Gdk as gdk
    from gi.repository import GObject as gobject
    from gi.repository import Pango as pango
    pass
else : 
    # gtk2
    import gobject
    import gtk
    import gtk.gdk as gdk
    import pango
    pass


__pychecker__="no-import no-argsused"

class dc_wraplabel(gtk.Label):
    __gtype_name__ = 'dc_wraplabel'

    def __init__(self, str=None):
        # gtk.Label.__init__(self)  # Not supposed to call superclass __init__ method, just gobject __init__ according to    http://www.pygtk.org/articles/subclassing-gobject/sub-classing-gobject-in-python.htm  
        gobject.GObject.__init__(self)


        self.__wrap_width = 0
        self.layout = self.get_layout()
        if hasattr(pango,"WrapMode") and hasattr(pango.WrapMode,"WORD"):
            # gtk3
            self.layout.set_wrap(pango.WrapMode.WORD)
            pass
        else : 
            self.layout.set_wrap(pango.WRAP_WORD)
            pass
            
        if str != None:
            self.set_text(str)

        self.set_alignment(0.0, 0.0)

    def do_size_request(self, requisition):
        layout = self.get_layout()
        width, height = layout.get_pixel_size()
        requisition.width = 170
        requisition.height = height
        pass

    def do_get_preferred_width(self):
        # used by python3 and above
        Req=gtk.Requisition()
        self.do_size_request(Req)
        return (Req.width,Req.width)

    def do_get_preferred_height(self):
        # used by python3 and above
        Req=gtk.Requisition()
        self.do_size_request(Req)
        return (Req.height,Req.height)

    def do_size_allocate(self, allocation):
        gtk.Label.do_size_allocate(self, allocation)
        self.__set_wrap_width(allocation.width)

    def set_text(self, str):
        gtk.Label.set_text(self, str)
        self.__set_wrap_width(self.__wrap_width)

    def set_markup(self, str):
        gtk.Label.set_markup(self, str)
        self.__set_wrap_width(self.__wrap_width)

    def __set_wrap_width(self, width):
        if width == 0:
            return
        layout = self.get_layout()
        layout.set_width((width - 2*self.get_property("xpad"))* pango.SCALE)
        if self.__wrap_width != width:
            self.__wrap_width = width
            self.queue_resize()


gobject.type_register(dc_wraplabel)  # required if we define new properties/signals
