import os
import sys

if "gi" in sys.modules:  # gtk3
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk as gtk
    from gi.repository import Gdk as gdk
    from gi.repository import GObject as gobject
    pass
else : 
    # gtk2
    import gobject
    import gtk
    import gtk.gdk as gdk
    pass

from .. import paramdb2 as pdb

try : 
    from .. import dc_value
    pass
except:
    sys.stderr.write("selectableparamreadout: unable to import dc_value class... widget will not operate correctly")
    dc_value=None
    pass

__pychecker__="no-import no-argsused no-constCond no-constattr"

if hasattr(gtk,"gtk_version") and (gtk.gtk_version[0] < 2 or (gtk.gtk_version[0]==2 and gtk.gtk_version[1] <= 24)):
    old_style_comboboxentry=True
    GtkComboBoxEntry=getattr(gtk,"ComboBoxEntry")
    pass
else: 
    # higher versions of gtk2, plus gtk3 (gtk3 uses gtk.MAJOR_VERSION and gtk.MINOR_VERSION instead of gtk.gtk_version)
    GtkComboBoxEntry=getattr(gtk,"ComboBoxText")
    old_style_comboboxentry=False
    pass


# WARNING: Not thread safe, in part because of 
#  changedinhibit flag

from ..dc_gtksupp import paramhandler

if hasattr(gtk,"StateType") and hasattr(gtk.StateType,"NORMAL"):
    # gtk3
    STATE_NORMAL=gtk.StateType.NORMAL
    STATE_PRELIGHT=gtk.StateType.PRELIGHT
    pass
else:
    STATE_NORMAL=gtk.STATE_NORMAL
    STATE_PRELIGHT=gtk.STATE_PRELIGHT
    pass



# gtk superclass should be first of multiple inheritances

### For some reason if we instantiate this directly from a glade file
# We get weird failures (search for CellView, below)
# but it all works OK if instantiated indirectly, through a labelled_selectableparamreadout (!?) 
class selectableparamreadout(GtkComboBoxEntry,paramhandler):
    __gtype_name__="selectableparamreadout"
    __gproperties__ = {
        # set command will be dg-param plus a space plus parameter
        # query command will be dg-param plus a question mark.

        "paramname": (gobject.TYPE_STRING,
                     "paramdb2 parameter to set",
                     "paramdb2 parameter to set",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags

        # "dg-paramsuffix": (gobject.TYPE_STRING,
        #              "suffix on dataguzzler parameter to set",
        #              "Suffix on Dataguzzler parameter to set. Include leading space if you need one",
        #             "", # default value 
        #             gobject.PARAM_READWRITE), # flags
        
        # "dg-paramdefault": (gobject.TYPE_STRING,
        #             "dataguzzler parameter default value",
        #             "Dataguzzler parameter default value",
        #             "", # default value 
        #             gobject.PARAM_READWRITE), # flags
        }
    __proplist = ["paramname"] 

    __selectableparamreadout_unique=None
    paramdb=None
    param=None
    requestident=None
    querypending=None
    assignedvalue=None
    lastvalue=None # last value provided by controller
    errorflag=None
    state=None
    fixedvalue=None
    liststore=None # part of combobox
    cell=None # Part of combobox
    optionlen=0

    newvalue_notify=None
    changeinprogress_notify=None
    newoptions_notify=None
    
    childntry=None  # GtkEntry child

    # values for state
    STATE_FOLLOWDG=0  # white, or orange (if last command was mismatch), or red (if last command was error), or green (if last command was match)  ... requestident should usually be None, querypending should be True, assignedvalue not valid
    STATE_ADJUSTING=1 # yellow... querypending should be False, requestident should usually be None, querypending should usually be False, assignedvalue not valid
    STATE_WAITING=2 # ltblue... querypending should be False, requestident shoudl be valid, assignedvalue valid
    STATE_FIXED=3 # fixed and hardwired to fixedvalue

    changedinhibit=None # Used to ignore change events triggered by  set_text... too bad Gtk doesn't  provide a better way to do this
    

    def __init__(self):
        if not "gtk" in sys.modules: 
            # gtk3 -- must use superclass constructor
            GtkComboBoxEntry.__init__(self,has_entry=True)
            pass
        else : 
            gobject.GObject.__init__(self)
            pass

        paramhandler.__init__(self,super(selectableparamreadout,self),self.__proplist)# .__gproperties__)
        # gtk.HBox.__init__(self) # Not supposed to call superclass __init__ method, just gobject __init__ according to    http://www.pygtk.org/articles/subclassing-gobject/sub-classing-gobject-in-python.htm  
        # self.myprops["dg-paramsuffix"]=""

        if not old_style_comboboxentry and "gtk" in sys.modules: 
            # not old style and using gtk2
            self.set_property("has-entry",True)
            pass
        
        
        self.changedinhibit=False
        self.fixedvalue=None

        if old_style_comboboxentry: 
            # need to manually create liststore,  & cell
            self.liststore=gtk.ListStore(gobject.TYPE_STRING)
            self.set_model(self.liststore)
            #self.cell=gtk.CellRendererText()
            #self.pack_start(self.cell,True,True,0)
            #self.add_attribute(self.cell,'text',0)
            self.set_text_column(0)
            pass
        else : 
            self.set_entry_text_column(0)
            pass


        self.errorflag=False
        self.querypending=False  # queries started in dc_gui_init

        # print "self.get_children()=",self.get_children()

        pass

    def set_fixed(self,fixed,fixedvalue=None,fixeddisplayfmt=None):
        if fixedvalue is None:
            # provide generic blank
            fixedvalue=dc_value.stringvalue("")
            pass

        if fixed:
            self.fixedvalue=fixedvalue       
            self.set_state(self.STATE_FIXED)
            self.changedinhibit=True
            self.childntry.set_text(self.fixedvalue.format(fixeddisplayfmt))
            self.changedinhibit=False
            pass

        elif self.state==self.STATE_FIXED:
            # if our state is set as fixed but we are no longer fixed
            self.set_state(self.STATE_FOLLOWDG) # go into follower state
            # update readout according to current param value
            self.newvalue(self.param,None)
            
            pass
        pass


    def isconsistent(self,inconsistentlist):
        if self.state != self.STATE_FOLLOWDG and self.state != self.STATE_FIXED:
            inconsistentlist.append(self.param.xmlname)
            return False
        return True
    
    def newoptions(self, param, condition):
        self.append_text('')
        param.requestvalstr('')
        for i in range(0,self.optionlen+1):
            self.remove_text(1)
        if self.param.options is not None:
            for option in self.param.options:
                self.append_text(unicode(option))
                pass
            pass
            self.optionlen = len(self.param.options)
        else:
            self.optionlen = 0
        pass

    def changeinprogress(self,param,condition): 
        pass
    
    def newvalue(self,param,condition):
        if self.state==self.STATE_ADJUSTING or self.state==self.STATE_WAITING or self.state==self.STATE_FIXED:
            return
        self.changedinhibit=True
        self.childntry.set_text(param.dcvalue.format(param.displayfmt))
        self.changedinhibit=False


        # print "param=%s" % (param.xmlname)
        # print "param.dcvalue=%s" % (str(param.dcvalue))
        # print "self.lastvalue=%s" % (str(self.lastvalue))

        
        if self.lastvalue != param.dcvalue:
            self.lastvalue=param.dcvalue
            self.set_state(self.STATE_FOLLOWDG) # clear a color change resulting from a command
            
            # print "not equal"
            pass

        pass
    
    def dc_gui_init(self,guistate):
        # need next line if subclassing a dc_gui class
        # super(dc_readout).__dc_gui_init(self,guistate)
        
        
        # gtk2 provides an "child" attribute
        # in gtk3 we have to use the get_child() method
        if hasattr(self,"child"):
            self.childntry=self.child
            pass
        else :
            self.childntry=self.get_child()
            # print "self.get_children()=",self.get_children()
            pass

        assert(self.childntry is not None)

        assert(not(str(self.childntry).startswith("<CellView"))) # Child should be an Entry, not a CellView. CellView is symptomatic of gtk3 bug when this is included directly from a gladefile
        
        

        
        if self.paramdb is None:  # allow manual initialization of paramdb, in case we are to use a non-default paramdb
            self.paramdb=guistate.paramdb
            pass

        if self.state is None:
            self.set_state(self.STATE_FOLLOWDG) # trigger sync_to_paramdb
            pass

        

        self.__selectableparamreadout_unique=[]


        if self.childntry is not None:
            self.childntry.connect("key-press-event",self.apr_keypress)
            
            self.childntry.connect("activate",self.apr_activate) 
            self.childntry.connect("changed",self.apr_changed)
            pass
            
        self.connect("changed",self.spr_changed)

        pass


    def sync_to_paramdb(self):
        if self.myprops["paramname"] not in self.paramdb:
            raise ValueError("No parameter database entry for \"%s\". Does this file need to be viewed within datacollect, and are you using the correct .dcc file?" % (self.myprops["paramname"]))
        self.param=self.paramdb[self.myprops["paramname"]]
        self.lastvalue=self.param.dcvalue

        self.changeinprogress_notify=self.param.addnotify(self.changeinprogress,pdb.param.NOTIFY_CONTROLLER_REQUEST)
        self.newvalue_notify=self.param.addnotify(self.newvalue,pdb.param.NOTIFY_NEWVALUE,)
        self.newoptions_notify=self.param.addnotify(self.newoptions,pdb.param.NOTIFY_NEWOPTIONS)

        # set up options
        for i in range(0,self.optionlen+1):
            self.remove_text(1)
        if self.param.options is not None:
            for option in self.param.options:
                self.append_text(unicode(option))
                pass
            pass
            self.optionlen = len(self.param.options)
        else:
            self.optionlen = 0
            pass
        
        if self.childntry is not None:
            self.changedinhibit=True
            self.childntry.set_text(self.param.dcvalue.format(self.param.displayfmt))
            self.changedinhibit=False
            pass
        pass

    def unsync_to_paramdb(self):
        self.param.remnotify(self.changeinprogress_notify)
        self.changeinprogress_notify=None

        self.param.remnotify(self.newvalue_notify)
        self.newvalue_notify=None

        self.param.remnotify(self.newoptions_notify)
        self.newoptions_notify=None

        pass

        
    
    def setbgcolor(self,color):
        colormap={"white" : "#ffffff",
                  "red"   : "#ff0000",
                  "yellow": "#ffff00",
                  "ltblue": "#80a0ff",
                  "magenta": "#ff00ff",
                  "green": "#00f000",
                  "orange": "#ff8000"}

        if self.childntry is not None:
            self.childntry.modify_base(STATE_NORMAL,gdk.color_parse(colormap[color]))
            pass
        pass
        
    def apr_keypress(self,obj,event):
        if self.state == self.STATE_FIXED:
            return
        
        # print "event.keyval=%s" % (str(event.keyval))
        
        if event.keyval==0xff09:  # GDK_Tab 
            #print "Tab pressed\n"
            if self.state != self.STATE_FOLLOWDG:
                self.apr_activate(None)
                pass
            
            pass

        if event.keyval==0xff1b: # GDK_Escape
            # abort
        
            self.changedinhibit=True
            self.childntry.set_text(param.dcvalue.format(param.displayfmt))
            self.changedinhibit=False
            self.lastvalue=self.param.dcvalue
            self.errorflag=False
            
            self.set_state(self.STATE_FOLLOWDG)
            pass
        
        return False # returning True would eat the event


    def apr_activate(self,event):
        if self.state==self.STATE_FIXED:
            return
        # entry has been activated. Also triggered by new combo box pulldown 
        # print "activate!"
        #print "issue command %s %s" % (self.myprops["dg-param"],self.get_text())
        self.set_state(self.STATE_WAITING)
        
        if self.requestident is not None:
            requestident=self.requestident
            self.requestident=None
            self.param.cancelrequest(requestident)
            pass

        self.assignedvalue=self.param.paramtype(self.get_active_text(),defunits=self.param.defunits)
        
        # print "requestval; self.state=%d self.assignedvalue=%s" % (self.state,str(type(self.assignedvalue.val)))
        self.requestident=self.param.requestval(self.assignedvalue,self.requestvalcallback)
        # print "requestident=%s" % (str(self.requestident))
        pass
    
    def spr_changed(self,event): 
        if self.state == self.STATE_FIXED:
            return
        # combo box changed
        # print "Combobox changed. Get_active()=%s" % (str(self.get_active()))
        
        active=self.get_active()
        
        if active >= 0: 
            # user selected a discrete item (otherwise we handle it through child.activate() -> apr_activate
            self.apr_activate(event)
            pass
    

        pass

    def apr_changed(self,event):
        if self.state == self.STATE_FIXED:
            return
        # entry has changed
        if not self.changedinhibit:
            # print "changed, event=%s!" % (str(event))
            self.set_state(self.STATE_ADJUSTING)
            pass
        
        pass
    
    def requestvalcallback(self,param,requestid,errorstr,result):
        # print "requestvalcallback. self.state=%d" % (self.state)
        if requestid != self.requestident:
            # print "requestid=%s requestident=%s" % (str(requestid),str(self.requestident))
            # spurious callback -- probably from command we were unable to cancel
            return

        if self.state != self.STATE_WAITING:
            return  # ignore result if we have moved on
        
        # print "executing callback"
        
        self.requestident=None

        if errorstr is not None:
            self.errorflag=True
            self.changedinhibit=True
            self.childntry.set_text(errorstr)
            self.changedinhibit=False
            
            self.set_state(self.STATE_FOLLOWDG)
            self.assignedvalue=None
            pass
        else :
            self.errorflag=False
            
            self.changedinhibit=True
            self.childntry.set_text(result.format(self.param.displayfmt))
            self.changedinhibit=False

            # resultobj=self.param.paramtype(result,defunits=self.param.defunits)
            
            #print str(type(result))
            #print str(type(self.assignedvalue))
            #print str(type(result.val))
            #print str(type(self.assignedvalue.val))
            if result == self.assignedvalue:
                self.set_state(self.STATE_FOLLOWDG,match=True)
                pass
            else :
                self.set_state(self.STATE_FOLLOWDG,mismatch=True)
                pass
            self.lastvalue=result
            
            pass
        return False
    
    def set_state(self,state,match=False,mismatch=False):
        if self.state is not None and self.state != self.STATE_FIXED and state==self.STATE_FIXED:
            # switch into fixed state: unsync_to_paramdb
            self.unsync_to_paramdb()
            pass
        elif (self.state is None or self.state == self.STATE_FIXED) and state != self.STATE_FIXED:
            # switch out of no state or fixed state: sync_to_paramdb
            self.sync_to_paramdb()
            pass
        self.state=state

        if self.state!=self.STATE_FIXED:
            self.set_sensitive(True)
            pass
        
        if self.state==self.STATE_FOLLOWDG:

            if self.errorflag:
                self.setbgcolor("red")
                pass
            elif match:
                self.setbgcolor("green")
                pass
            elif mismatch:
                self.setbgcolor("orange")
                pass
            else:
                self.setbgcolor("white")
                pass
            
            pass
        elif self.state==self.STATE_ADJUSTING:
            self.setbgcolor("yellow")
            pass
        elif self.state==self.STATE_WAITING:
            self.setbgcolor("ltblue")
            pass
        elif self.state==self.STATE_FIXED:
            self.set_sensitive(False)
            pass
        else:
            assert(0)
            pass
        
        pass

    pass


gobject.type_register(selectableparamreadout)  # required since we are defining new properties/signals
