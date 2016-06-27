import sys

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

import dc_value

namespaces={
        "dc": "http://thermal.cnde.iastate.edu/datacollect",
        "dcv": "http://thermal.cnde.iastate.edu/dcvalue",
        "chx": "http://thermal.cnde.iastate.edu/checklist",
        }

def simplifytag(tagname):
    for key in namespaces: 
        longns="{"+namespaces[key]+"}"
        if tagname.startswith(longns):
            return key+":"+tagname[len(longns):]
        pass
    return tagname

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


class viewautoexp(gtk.Window):
    xmldoc=None
    xmlpath=None
    liststore=None
    treeview=None

    def __init__(self,xmldoc,xmlpath):
        # xmldoc should be locked when you call the constructor !!!
        gobject.GObject.__init__(self)
        self.xmldoc=xmldoc
        self.xmlpath=xmlpath
        xmltag=self.xmldoc.restorepath(self.xmlpath)
        
        meastags=self.xmldoc.xpathcontext(xmltag,"dc:autoexp/dc:automeas")
        
        # print meastags
        
        types=[]
        units=[]
        titles=[]
        tags=[]
        if len(meastags) > 0:

            firsttag=meastags[0]
            for element in firsttag:
                tags.append(element.tag)
                if "{http://thermal.cnde.iastate.edu/dcvalue}units" in element.attrib:
                    types.append(gobject.TYPE_FLOAT)
                    #types.append(float)
                    units.append(element.attrib["{http://thermal.cnde.iastate.edu/dcvalue}units"])
                    titles.append("%s (%s)" % (doubleunderscores(simplifytag(element.tag)),doubleunderscores(units[-1])))
                    # print "title: %s (%s)" % (element.tag,units[-1])
                    pass
                else:
                    types.append(gobject.TYPE_STRING)
                    #types.append(str)
                    units.append(None)
                    titles.append(doubleunderscores(simplifytag(element.tag)))
                    pass
                

                pass
            
            self.liststore=gtk.ListStore(*types)

            for meastag in meastags:
                cols=[]
                for tagnum in range(len(tags)):
                    tag=tags[tagnum]
                    typ=types[tagnum]
                    unit=units[tagnum]
                    tagel=meastag.find(tag)
                    if typ==gobject.TYPE_STRING:
                        cols.append(tagel.text)
                        pass
                    else : # numericunits
                        val=dc_value.numericunitsvalue.fromxml(xmldoc,tagel)
                        # print "units=%s" % (unit)
                        floatval=val.value(units=unit)
                        cols.append(floatval)
                        pass
                    pass
                    
                self.liststore.append(cols)
                pass
            self.treeview=gtk.TreeView(self.liststore)
            
            # Create columns
            for tagnum in range(len(tags)):
                renderer=gtk.CellRendererText()
                # print "column: %s" % (titles[tagnum])
                column=gtk.TreeViewColumn(titles[tagnum],renderer,text=tagnum)
                column.set_sort_column_id(tagnum)
                self.treeview.append_column(column)
                pass
            
            # self.add(self.treeview)
            
            
            pass
        
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
        self.add(self.scrolled)
        self.show_all()
        
        pass

    pass
