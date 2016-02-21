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

import paramdb2 as pdb

try : 
    sys.path.append('/home/sdh4/research/datacollect')
    import dc_value
    pass
except:
    sys.stderr.write("paragraphparam: unable to import dc_value class... widget will not operate correctly")
    dc_value=None
    pass


# WARNING: Not thread safe, in part because of 
#  changedinhibit flag

from dc_gtksupp import paramhandler

if hasattr(gtk,"StateType") and hasattr(gtk.StateType,"NORMAL"):
    # gtk3
    STATE_NORMAL=gtk.StateType.NORMAL
    STATE_PRELIGHT=gtk.StateType.PRELIGHT
    pass
else:
    STATE_NORMAL=gtk.STATE_NORMAL
    STATE_PRELIGHT=gtk.STATE_PRELIGHT
    pass

__pychecker__="no-import no-argsused no-constCond"

# gtk superclass should be first of multiple inheritances
class paragraphparam(gtk.ScrolledWindow,paramhandler):
    __gtype_name__="paragraphparam"
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

    __paragraphparam_unique=None
    textview=None # Textview wrapped within our scrollbar
    paramdb=None
    param=None
    requestident=None
    requestassignedcallback=None  # callback to generate after request completes
    querypending=None
    assignedvalue=None
    lastvalue=None # last value provided by controller
    errorflag=None
    state=None
    fixedvalue=None
    endmark=None # gtk.TextMark indicating end of textbuffer

    newvalue_notify=None
    changeinprogress_notify=None

    
    # values for state
    STATE_FOLLOWDG=0  # white, or orange (if last command was mismatch), or red (if last command was error), or green (if last command was match)  ... requestident should usually be None, querypending should be True, assignedvalue not valid
    STATE_ADJUSTING=1 # yellow... querypending should be False, requestident should usually be None, querypending should usually be False, assignedvalue not valid
    STATE_WAITING=2 # ltblue... querypending should be False, requestident shoudl be valid, assignedvalue valid
    STATE_FIXED=3 # fixed and hardwired to fixedvalue

    changedinhibit=None # Used to ignore change events triggered by  set_text... too bad Gtk doesn't  provide a better way to do this
    

    def __init__(self):
        gobject.GObject.__init__(self)


        paramhandler.__init__(self,super(paragraphparam,self),self.__proplist)# .__gproperties__)
        # gtk.HBox.__init__(self) # Not supposed to call superclass __init__ method, just gobject __init__ according to    http://www.pygtk.org/articles/subclassing-gobject/sub-classing-gobject-in-python.htm  
        # self.myprops["dg-paramsuffix"]=""

        # gtk3 defines Gtk.PolicyType
        if hasattr(gtk,"PolicyType") and hasattr(gtk.PolicyType,"AUTOMATIC"):
            self.set_policy(gtk.PolicyType.NEVER,gtk.PolicyType.ALWAYS)            
            pass
        else : 
            self.set_policy(gtk.POLICY_NEVER,gtk.POLICY_ALWAYS)
            pass
            
        self.textview=gtk.TextView()
        if hasattr(gtk,"WrapMode") and hasattr(gtk.WrapMode,"WORD"):
            self.textview.set_wrap_mode(gtk.WrapMode.WORD_CHAR)
            pass
        else : 
            self.textview.set_wrap_mode(gtk.WRAP_WORD_CHAR)
            pass

        self.textview.set_accepts_tab(False)
        self.add(self.textview)
        

        self.changedinhibit=False
        self.fixedvalue=None

        buf=self.textview.get_buffer()
        end_iter=buf.get_end_iter()
        self.endmark=buf.create_mark("End",end_iter,False)

        self.errorflag=False
        self.querypending=False  # queries started in dc_gui_init



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
            self.textview.get_buffer().set_property("text",self.fixedvalue.format(fixeddisplayfmt))
            self.changedinhibit=False
            pass

        elif self.state==self.STATE_FIXED:
            # if our state is set as fixed but we are no longer fixed
            self.set_state(self.STATE_FOLLOWDG) # go into follower state
            # update readout according to current param value

            #sys.stderr.write("paragraphparam: Following dg. self.param.dcvalue=%s\n" % (str(self.param.dcvalue)))
            #sys.stderr.write("paragraphparam: Following dg. self.paramdb[notes].dcvalue=%s\n" % (str(self.paramdb["notes"].dcvalue)))
            self.newvalue(self.param,None)
            
            pass
        pass

    

    def changeinprogress(self,param,condition): 
        pass

    def set_editable(self,val):
        sys.stderr.write("paragraphparam warning: attempt to set editable... not yet implemented!\n")
        pass

    
    def isconsistent(self,inconsistentlist):
        if self.state != self.STATE_FOLLOWDG and self.state != self.STATE_FIXED:
            inconsistentlist.append(self.param.xmlname)
            return False
        return True
    
    def newvalue(self,param,condition):
        
        if self.state==self.STATE_ADJUSTING or self.state==self.STATE_WAITING or self.state==self.STATE_FIXED:
            return
        
        self.changedinhibit=True
        self.textview.get_buffer().set_property("text",param.dcvalue.format(param.displayfmt))
        self.changedinhibit=False

        if self.lastvalue != param.dcvalue:
            self.lastvalue=param.dcvalue
            
            self.set_state(self.STATE_FOLLOWDG) # clear a color change resulting from a command 
            # print "not equal"
            pass
        
        pass
    
    def dc_gui_init(self,guistate):
        # need next line if subclassing a dc_gui class
        # super(dc_readout).__dc_gui_init(self,guistate)
        
        if self.paramdb is None:  # allow manual initialization of paramdb, in case we are to use a non-default paramdb
            self.paramdb=guistate.paramdb
            pass
        
        self.__paragraphparam_unique=[]

        if self.state is None: 
            self.set_state(self.STATE_FOLLOWDG) # trigger sync_to_paramdb
            pass

        
        #self.textview.connect("focus-out-event",self.pp_activate)
        self.textview.connect("key-press-event",self.pp_keypress)
        self.textview.get_buffer().connect("changed",self.pp_changed)

        pass

    def sync_to_paramdb(self):
        if self.myprops["paramname"] not in self.paramdb:
            raise ValueError("No parameter database entry for \"%s\". Does this file need to be viewed within datacollect, and are you using the correct .dcc file?" % (self.myprops["paramname"]))
        self.param=self.paramdb[self.myprops["paramname"]]

        self.lastvalue=self.param.dcvalue
        self.changeinprogress_notify=self.param.addnotify(self.changeinprogress,pdb.param.NOTIFY_CONTROLLER_REQUEST)
        self.newvalue_notify=self.param.addnotify(self.newvalue,pdb.param.NOTIFY_NEWVALUE,)

        self.changedinhibit=True
        self.textview.get_buffer().set_property("text",self.param.dcvalue.format(self.param.displayfmt))
        self.changedinhibit=False
        
        pass

    def unsync_to_paramdb(self):
        self.param.remnotify(self.changeinprogress_notify)
        self.changeinprogresss_notify=None

        self.param.remnotify(self.newvalue_notify)
        self.newvalue_notify=None
        pass
    
    def setbgcolor(self,color):
        colormap={"white" : "#ffffff",
                  "red"   : "#ff0000",
                  "yellow": "#ffff00",
                  "ltblue": "#80a0ff",
                  "magenta": "#ff00ff",
                  "green": "#00f000",
                  "orange": "#ff8000"}

        self.textview.modify_base(STATE_NORMAL,gdk.color_parse(colormap[color]))
        
        pass

    def pp_abort(self):
        # set to current value of underlying parameter
        if self.state==self.STATE_FIXED:
            return
        
        self.changedinhibit=True
        self.textview.get_buffer().set_property("text",self.param.dcvalue.format(self.param.displayfmt))
        self.changedinhibit=False
        self.lastvalue=self.param.dcvalue

        self.set_state(self.STATE_FOLLOWDG)
        pass
    
    def pp_keypress(self,obj,event):
        if self.state==self.STATE_FIXED:
            return False

        
        # print "event.keyval=%s" % (str(event.keyval))
        
        if event.keyval==0xff09:  # GDK_Tab 
            #print "Tab pressed\n"
            if self.state != self.STATE_FOLLOWDG:
                self.pp_activate()
                pass
            pass

        if event.keyval==0xff1b: # GDK_Escape
            # abort
            self.pp_abort()


            pass
        
        return False # returning True would eat the event


    def pp_programmaticallyappend_noactivate(self,text):
        # this is used to programatically append content WITHOUT
        # triggering an update to the parameter. 
        # Be sure to call pp_activate() when done.
        assert(self.state != self.STATE_FIXED)

        buf=self.textview.get_buffer()
        end_iter=buf.get_end_iter()
        buf.insert(end_iter,text)

        # make sure the end of the text is visible
        end_iter_new=buf.get_end_iter()
        buf.move_mark(self.endmark,end_iter_new)
        self.textview.scroll_mark_onscreen(self.endmark)
        pass


    # WARNING: pp_activate no longer suitable as gtk callback because of
    # assignedcallback parameter
    def pp_activate(self,assignedcallback=None):
        if self.state==self.STATE_FIXED:
            if assignedcallback is not None:
                assignedcallback(self,None)
                pass
            return

        # print "Loose focus... update controller"

        if self.state != self.STATE_ADJUSTING:
            # change callback never called... do nothing
            if assignedcallback is not None:
                assignedcallback(self,None)
                pass

            return

        
        self.set_state(self.STATE_WAITING)
        
        if self.requestident is not None:
            requestident=self.requestident
            self.requestident=None
            self.param.cancelrequest(requestident)
            pass

        
        self.assignedvalue=self.param.paramtype(self.textview.get_buffer().get_property("text"),defunits=self.param.defunits)
        
        self.requestident=self.param.requestval(self.assignedvalue,self.requestvalcallback)
        self.requestassignedcallback=assignedcallback
        pass
    
    def pp_changed(self,event):
        if self.state==self.STATE_FIXED: 
            return
        
        if not self.changedinhibit:
            # print "changed, event=%s!" % (str(event))
            self.set_state(self.STATE_ADJUSTING)
            pass
        
        pass
    
    def requestvalcallback(self,param,requestid,errorstr,result):
        
        if requestid != self.requestident:
            # spurious callback -- probably from command we were unable to cancel
            return

        if self.state != self.STATE_WAITING:
            return  # ignore result if we have moved on
    
        
        self.requestident=None

        if errorstr is not None:
            self.errorflag=True
            self.changedinhibit=True
            self.textview.get_buffer().set_property("text",errorstr)
            self.changedinhibit=False
            
            self.set_state(self.STATE_FOLLOWDG)
            self.assignedvalue=None
            if self.requestassignedcallback is not None:
                self.requestassignedcallback(self,None)
                pass
            
            pass
        else :
            self.errorflag=False
            
            self.changedinhibit=True
            self.textview.get_buffer().set_property("text",result.format(self.param.displayfmt))
            self.changedinhibit=False

            # resultobj=self.param.paramtype(result,defunits=self.param.defunits)

            if result == self.assignedvalue:
                self.set_state(self.STATE_FOLLOWDG,match=True)
                pass
            else :
                self.set_state(self.STATE_FOLLOWDG,mismatch=True)
                pass
            self.lastvalue=result
            
            if self.requestassignedcallback is not None:
                self.requestassignedcallback(self,result)
                pass
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


gobject.type_register(paragraphparam)  # required since we are defining new properties/signals
