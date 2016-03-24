import sys
import os

if "gi" in sys.modules:  # gtk3
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk as gtk
    from gi.repository import GObject as gobject
    pass
else : 
    # gtk2
    import gtk
    import gobject
    pass
    
from . import dc_value
from . import paramdb2 as pdb

__pychecker__="no-argsused no-import"


def doubleunderscores(text):
    # Double-up underscores because single underscores are interpreted
    # by GTK as keyboard shortcuts
    output=unicode("")
    for char in text:
        if char=='_':
            output+='__'
            pass
        else :
            output += char
            pass
        pass
    return output

class viewableparam(object):
    paramname=None  # paramdb2 entry
    origrownum=None  # row number when originally layed out... invalid after sorting
    TreeRowRef=None  # gtk TreeRowReference
    notify=None # paramdb notify handle
    state=None # one of state values defined below

    pass


class paramdb2_editor(gtk.Window):
    paramdb=None
    liststore=None  # the gtk.ListStore that mirrors the paramdb database
    treeview=None  # TreeView that displays the ListStore

    params=None # dictionary of class viewableparam

    vbox=None # big vbox in our window

    # constants
    COLOR_WHITE="#ffffff"
    COLOR_RED="#ff0000"
    COLOR_GREEN="#00ff00"
    COLOR_YELLOW="#ffff00"
    COLUMN_NAME=0
    COLUMN_VALUE=1
    COLUMN_DEFUNITS=2
    COLUMN_CONTROLLER=3
    COLUMN_BGCOLOR=4
    STATE_FOLLOW=0
    STATE_WAITING=1
    

    def __init__(self,paramdb):
        gobject.GObject.__init__(self)
        self.paramdb=paramdb

        
        titles=["Param name","Param value","Default Units","Controller"]
        types=[gobject.TYPE_STRING,gobject.TYPE_STRING,gobject.TYPE_STRING,gobject.TYPE_STRING,gobject.TYPE_STRING]  # last entry is for background color
            
        self.liststore=gtk.ListStore(*types)

        self.params={}

        self.set_title("Paramdb2 Editor")

        self.set_property("default-width",600)
        self.set_property("default-height",700)

        # fill in a row for each entry
        rownum=0
        keylist=[key for key in self.paramdb.keys()]
        keylist.sort()
        for entry in keylist: 
            if entry in self.paramdb:
                cols=[]
                # first (0) column is name of paramdb entry
                cols.append(entry)
                # 2nd (1) column is value
                #cols.append(unicode(self.paramdb[entry].dcvalue))
                cols.append(self.paramdb[entry].dcvalue.format(self.paramdb[entry].displayfmt))
                # 3rd (2) column is  defunits
                cols.append(str(self.paramdb[entry].defunits))
                # 4th (3) column is controller
                cols.append(self.paramdb[entry].controller.__class__.__name__)
                # 5th (4) column is background color (hidden)
                cols.append(self.COLOR_WHITE)
                self.liststore.append(cols)
                

                param=viewableparam()
                param.paramname=entry
                param.origrownum=rownum
                
                param.notify=self.paramdb.addnotify(entry,self.rowupdate,pdb.param.NOTIFY_NEWVALUE,param)
                param.state=self.STATE_FOLLOW
                
                self.params[entry]=param
                
                rownum+=1
                pass
            pass
        
        
        self.treeview=gtk.TreeView(self.liststore)
            
        # Create columns
        for colnum in range(len(titles)):
            renderer=gtk.CellRendererText()
            # print "column: %s" % (titles[tagnum])
            if colnum==self.COLUMN_VALUE: # Value column
                renderer.set_property('editable', True)
                renderer.connect('edited',self.cell_edited_callback)
                pass
            column=gtk.TreeViewColumn(titles[colnum],renderer,text=colnum,background=self.COLUMN_BGCOLOR)  # background=self.COLUMN_BGCOLOR sets column number to extract background colorcursop
            column.set_resizable(True)
            column.set_max_width(300)
            
            column.set_sort_column_id(colnum)
            self.treeview.append_column(column)
            pass
        
        # self.add(self.treeview)

        # Create TreeRowReferences now that all entries are added
        for name in self.params:
            # gtk3 requires use of gtk.TreeRowReference.new and gtk.TreePath
            if hasattr(gtk.TreeRowReference,"new"):

                self.params[name].TreeRowRef=gtk.TreeRowReference.new(self.liststore,gtk.TreePath((self.params[name].origrownum,)))
                pass
            else: 
                self.params[name].TreeRowRef=gtk.TreeRowReference(self.liststore,(self.params[name].origrownum,))
                pass
                
            pass

        self.vbox=gtk.VBox()
        self.scrolled=gtk.ScrolledWindow()
        
        # gtk3 defines Gtk.PolicyType
        if hasattr(gtk,"PolicyType") and hasattr(gtk.PolicyType,"AUTOMATIC"):
            self.scrolled.set_policy(gtk.PolicyType.AUTOMATIC,gtk.PolicyType.ALWAYS)
            pass
        else :
            self.scrolled.set_policy(gtk.POLICY_AUTOMATIC,gtk.POLICY_ALWAYS)
            pass

        self.viewport=gtk.Viewport()
        if self.treeview is not None:
            self.viewport.add(self.treeview)
            pass
        
        self.scrolled.add(self.viewport)
        self.vbox.add(self.scrolled)
        self.add(self.vbox)

        self.connect("delete-event",self.closehandler)

        self.show_all()
        
        pass

    def cell_edited_callback(self,cellrenderer,path,new_text):
        # sys.stderr.write("Got cell_edited, path=%s, new_text=%s\n" % (str(path),new_text))
        # paramname is first column
        paramname=self.liststore.get_value(self.liststore.get_iter(path),0)

        # set color (column #4) to yellow
        self.liststore.set_value(self.liststore.get_iter(path),self.COLUMN_BGCOLOR,self.COLOR_YELLOW)
        self.params[paramname].state=self.STATE_WAITING

        # set text temporarily
        self.liststore.set_value(self.liststore.get_iter(path),self.COLUMN_VALUE,new_text)

        try :
            self.paramdb[paramname].requestvalstr(new_text,self.requestvalcallback)
            pass
        except: 
            self.liststore.set_value(self.liststore.get_iter(path),self.COLUMN_BGCOLOR,self.COLOR_RED)
            self.liststore.set_value(self.liststore.get_iter(path),self.COLUMN_VALUE,str(sys.exc_info()[1]))            
            self.params[paramname].state=self.STATE_FOLLOW
            
            pass
        # self.params[paramname].

        cursorpath=(int(path) + 1)
        if cursorpath == len(self.params.keys()):
            cursorpath=int(path)-1 
            if cursorpath < 0:
                cursorpath=0
                pass
            pass
        # set cursor to next row
        self.treeview.set_cursor(cursorpath)
        pass

    def requestvalcallback(self,pdbparam,requestid,errorstr,result):
        name=pdbparam.xmlname
        
        param=self.params[name]
        
        if errorstr is not None:
            self.liststore.set_value(self.liststore.get_iter(param.TreeRowRef.get_path()),self.COLUMN_VALUE,errorstr)            
            # set color (column #4) to red
            self.liststore.set_value(self.liststore.get_iter(param.TreeRowRef.get_path()),self.COLUMN_BGCOLOR,self.COLOR_RED)
            param.state=self.STATE_FOLLOW
            pass
        else :
            self.liststore.set_value(self.liststore.get_iter(param.TreeRowRef.get_path()),self.COLUMN_VALUE,result.format(pdbparam.displayfmt))            
            # set color (column #4) to GREEN
            self.liststore.set_value(self.liststore.get_iter(param.TreeRowRef.get_path()),self.COLUMN_BGCOLOR,self.COLOR_GREEN)
            param.state=self.STATE_FOLLOW
            pass

        pass

    def rowupdate(self,param,condition,viewableparam):
        #if param.xmlname=="strain_ov_displacement":
        #    sys.stderr.write("rowupdate; rownum=%d\n" % rownum)

        if viewableparam.state==self.STATE_FOLLOW:
            self.liststore.set_value(self.liststore.get_iter(viewableparam.TreeRowRef.get_path()),self.COLUMN_VALUE,param.dcvalue.format(param.displayfmt))
            # set color (column #4) to WHITE
            self.liststore.set_value(self.liststore.get_iter(viewableparam.TreeRowRef.get_path()),self.COLUMN_BGCOLOR,self.COLOR_WHITE)
            pass
            
        pass
    
        
    def closehandler(self,widget,event):
        # returns False to close, True to cancel
        
        for paramname in set(self.params.keys()):
            
            self.params[paramname].paramname=None
            self.params[paramname].TreeRowRef=None
            
            self.paramdb.remnotify(paramname,self.params[paramname].notify)
            self.params[paramname].notify=None

            del self.params[paramname]
            pass

        del self.paramdb
        del self.liststore
        del self.treeview        

        
        return False
    
    pass
