# support for the standalone dg_checklist binary

import sys
import os 
import os.path


if not "gtk" in sys.modules:  # gtk3
    from gi.repository import Gtk as gtk
    from gi.repository import GObject as gobject
    from gi.repository import Gdk as gdk
    DELETE=None  # can't figure out what the event structure is supposed to contain, but None works OK.
    pass
else : 
    # gtk2
    import gobject
    import gtk
    import gtk.gdk as gdk
    DELETE=gdk.DELETE
    pass

import dc2_misc
import canonicalize_path
import checklist
import xmldoc
import checklistdb
import checklistdbwin

from dc_gtksupp import guistate as create_guistate


# global pointers to the checklistdbwindow and plandbwindow
checklistdbwindow=None
plandbwindow=None


# event handler for clicking on the checklists... menu item
def handle_openchecklists(event,paramdb,iohandler):
    global checklistdbwindow
    if checklistdbwindow is None:
        checklistdbwindow=checklistdbwin.checklistdbwin(None,None,None,popupchecklist,[paramdb,iohandler],True,False)
        checklistdbwindow.show()
        pass
    else:
        checklistdbwindow.liststoreupdate()
        checklistdbwindow.present()
        pass
    pass


def handle_openplans(event,paramdb,iohandler):
    global plandbwindow
    if plandbwindow is None:
        plandbwindow=checklistdbwin.checklistdbwin(None,None,None,popupchecklist,[paramdb,iohandler],False,True)
        plandbwindow.show()
        pass
    else:
        plandbwindow.liststoreupdate()
        plandbwindow.present()
        pass
    pass


def popupchecklist(canonicalpath,paramdb,iohandler):
    # like explogwindow.popupchecklist
    (chklistobj,canonfname)=dc2_misc.searchforchecklist(canonicalpath)

    if chklistobj is None:
        checklistobj=open_checklist(canonfname,paramdb,iohandler)
        pass
    else:
        # bring it to front 
        chklistobj.present()
        pass
    return chklistobj
    

def checklistmenu_realtime(event,canonicalpath,paramdb,iohandler):
    popupchecklist(canonicalpath,paramdb,iohandler)
    pass


def rebuildchecklistrealtimemenu(event,AllChecklists,AllPlans,MenuObject,MenuOrigEntries,paramdb,iohandler):

    openchecklists=checklistdb.getchecklists(None,None,None,None,allchecklists=AllChecklists,allplans=AllPlans)
    #sys.stderr.write("rebuildchecklistrealtimemenu(%s)\n" % (openchecklists))

    menuentries=MenuObject.get_children()
    
    #sys.stderr.write("AllPlans=%s; openchecklists=%s\n" % (str(AllPlans),str(openchecklists)))
        
    # total non-realtime menu entries is self.checklistmenuorigentries+len(self.checklistmenushortcuts)
    # remove all the later ones
    for cnt in range(MenuOrigEntries,len(menuentries)):
        MenuObject.remove(menuentries[cnt])
        pass
        
    # append a separator
    newitem=gtk.SeparatorMenuItem()
    MenuObject.append(newitem)
    newitem.show()
    
    for cnt in range(len(openchecklists)):
        if openchecklists[cnt].filename is None: # use mem:// url
            newitem=gtk.MenuItem(label=openchecklists[cnt].canonicalpath,use_underline=False)
        else:
            newitem=gtk.MenuItem(label=openchecklists[cnt].filename,use_underline=False)
            pass
        newitem.connect("activate",checklistmenu_realtime,openchecklists[cnt].canonicalpath,paramdb,iohandler)
        MenuObject.append(newitem)
        newitem.show()
        # sys.stderr.write("adding checklist menu item: %s\n" % (openchecklists[cnt].filename))
        pass
    pass



def insert_menu(chklist,paramdb,iohandler):

    MenuBar=gtk.MenuBar()

    ChecklistMenuItem=gtk.MenuItem("Checklist")
    MenuBar.append(ChecklistMenuItem)
    ChecklistMenu=gtk.Menu()
    ChecklistMenuItem.set_submenu(ChecklistMenu)
    ChecklistsMenuItem=gtk.MenuItem("Checklists...")
    ChecklistsMenuItem.connect("activate",handle_openchecklists,paramdb,iohandler)
    ChecklistMenu.append(ChecklistsMenuItem)

    PlanMenuItem=gtk.MenuItem("Plan")
    MenuBar.append(PlanMenuItem)
    PlanMenu=gtk.Menu()
    PlanMenuItem.set_submenu(PlanMenu)
    PlansMenuItem=gtk.MenuItem("Plans...")
    PlansMenuItem.connect("activate",handle_openplans,paramdb,iohandler)
    PlanMenu.append(PlansMenuItem)


    chklist.gladeobjdict["UpperVBox"].pack_start(MenuBar,expand=False,fill=True)
    chklist.gladeobjdict["UpperVBox"].reorder_child(MenuBar,0) # move it to the top

    # add rebuild requests... for ChecklistMenu
    checklistdb.requestopennotify(rebuildchecklistrealtimemenu,True,False,ChecklistMenu,1,paramdb,iohandler)
    checklistdb.requestdonenotify(rebuildchecklistrealtimemenu,True,False,ChecklistMenu,1,paramdb,iohandler)
    checklistdb.requestresetnotify(rebuildchecklistrealtimemenu,True,False,ChecklistMenu,1,paramdb,iohandler)
    checklistdb.requestclosenotify(rebuildchecklistrealtimemenu,True,False,ChecklistMenu,1,paramdb,iohandler)

    # add rebuild requests... for PlanMenu
    checklistdb.requestopennotify(rebuildchecklistrealtimemenu,False,True,PlanMenu,1,paramdb,iohandler)
    checklistdb.requestdonenotify(rebuildchecklistrealtimemenu,False,True,PlanMenu,1,paramdb,iohandler)
    checklistdb.requestresetnotify(rebuildchecklistrealtimemenu,False,True,PlanMenu,1,paramdb,iohandler)
    checklistdb.requestclosenotify(rebuildchecklistrealtimemenu,False,True,PlanMenu,1,paramdb,iohandler)
    

    pass

def open_checklist_parent(chklist,paramdb,iohandler):
    # does this checklist have a parent that we should open too? 
    parent=chklist.get_parent()  # returns hrefvalue object

    if parent is not None and parent.getpath() is not None:
        # check if parent is already open in-memory
        (parentclobj,parentcanonfname)=dc2_misc.searchforchecklist(parent.getpath())
        
        if parentclobj is None:
            # if not, open the parent checklist
            self.open_checklist(parentcanonfname,paramdb,iohandler)
            pass
        pass
    pass
    

def handle_checklist_close(param1,param2,chklist):
    chklist.destroy()
    if len(checklistdb.getchecklists(None,None,None,None,allchecklists=True,allplans=True)) == 0:
        # nothing left open! 
        sys.exit(0)
        pass
    return False

def open_checklist(fname,paramdb,iohandler,destoverride=None):
    chklist=checklist.checklist(fname,paramdb,destoverride=destoverride)

    # insert menu
    insert_menu(chklist,paramdb,iohandler)


    # each checklist opened has its own private guistate

    guistate=create_guistate(iohandler,paramdb,[os.path.split(fname)[0]])
    
    
    chklist.dc_gui_init(guistate)

    open_checklist_parent(chklist,paramdb,iohandler) # open our parent, if necessary

    
    if fname.endswith(".plx") or fname.endswith(".plf"):
        checklistdb.newchecklistnotify(chklist,True)
        pass
    else:
        checklistdb.newchecklistnotify(chklist,False)
        pass

        
    win=chklist.getwindow()
    win.connect("delete-event",handle_checklist_close,chklist)    
    win.show_all()

    return chklist
