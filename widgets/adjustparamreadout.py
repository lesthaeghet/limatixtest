import os
import sys


if not "gtk" in sys.modules:  # gtk3
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
    sys.stderr.write("adjustparamreadout: unable to import dc_value class... widget will not operate correctly")
    dc_value=None
    pass


# WARNING: Not thread safe, in part because of 
#  changedinhibit flag

from dc_gtksupp import paramhandler

__pychecker__="no-import no-argsused no-constCond"

# gtk superclass should be first of multiple inheritances
class adjustparamreadout(gtk.Entry,paramhandler):
    __gtype_name__="adjustparamreadout"
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

    __adjustparamreadout_unique=None
    dc_gui_io=None
    paramdb=None
    param=None
    requestident=None
    querypending=None
    assignedvalue=None
    lastvalue=None # last value provided by controller
    errorflag=None
    state=None

    # values for state
    STATE_FOLLOWDG=0  # white, or orange (if last command was mismatch), or red (if last command was error), or green (if last command was match)  ... requestident should usually be None, querypending should be True, assignedvalue not valid
    STATE_ADJUSTING=1 # yellow... querypending should be False, requestident should usually be None, querypending should usually be False, assignedvalue not valid
    STATE_WAITING=2 # ltblue... querypending should be False, requestident shoudl be valid, assignedvalue valid

    changedinhibit=None # Used to ignore change events triggered by  set_text... too bad Gtk doesn't  provide a better way to do this
    

    def __init__(self):

        gobject.GObject.__init__(self)
        paramhandler.__init__(self,super(adjustparamreadout,self),self.__proplist)
        
        # gtk.HBox.__init__(self) # Not supposed to call superclass __init__ method, just gobject __init__ according to    http://www.pygtk.org/articles/subclassing-gobject/sub-classing-gobject-in-python.htm  
        # self.myprops["dg-paramsuffix"]=""

        self.changedinhibit=False


        self.errorflag=False
        self.querypending=False  # queries started in dc_gui_init
        self.set_state(self.STATE_FOLLOWDG)

        pass
    
    def isconsistent(self,inconsistentlist):
        if self.state != self.STATE_FOLLOWDG:
            inconsistentlist.append(self.param.xmlname)
            pass
        
        return self.state==self.STATE_FOLLOWDG
    


    def changeinprogress(self,param,condition): 
        pass
    
    def newvalue(self,param,condition):
        if self.state==self.STATE_ADJUSTING or self.state==self.STATE_WAITING:
            return
        self.changedinhibit=True
        self.set_text(param.dcvalue.format(param.displayfmt))
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
        
        self.dc_gui_io=guistate.io

        if self.paramdb is None:  # allow manual initialization of paramdb, in case we are to use a non-default paramdb
            self.paramdb=guistate.paramdb
            pass

        
        if self.myprops["paramname"] not in self.paramdb:
            raise ValueError("No parameter database entry for \"%s\". Does this file need to be viewed within datacollect, and are you using the correct .dcc file?" % (self.myprops["paramname"]))
        self.param=self.paramdb[self.myprops["paramname"]]
        self.lastvalue=self.param.dcvalue

        self.param.addnotify(self.changeinprogress,pdb.param.NOTIFY_CONTROLLER_REQUEST)
        self.param.addnotify(self.newvalue,pdb.param.NOTIFY_NEWVALUE,)

        self.__adjustparamreadout_unique=[]



        self.set_text(self.param.dcvalue.format(self.param.displayfmt))



        self.connect("key-press-event",self.apr_keypress)
        self.connect("activate",self.apr_activate)
        self.connect("changed",self.apr_changed)

        pass


    def setbgcolor(self,color):
        colormap={"white" : "#ffffff",
                  "red"   : "#ff0000",
                  "yellow": "#ffff00",
                  "ltblue": "#80a0ff",
                  "magenta": "#ff00ff",
                  "green": "#00f000",
                  "orange": "#ff8000"}

        if hasattr(gtk,"StateType") and hasattr(gtk.StateType,"NORMAL"):
            # gtk3
            self.modify_base(gtk.StateType.NORMAL,gdk.color_parse(colormap[color]))
            pass
        else:
            self.modify_base(gtk.STATE_NORMAL,gdk.color_parse(colormap[color]))
            pass
        pass
        
    def apr_keypress(self,obj,event):
        
        # print "event.keyval=%s" % (str(event.keyval))
        
        if event.keyval==0xff09:  # GDK_Tab 
            #print "Tab pressed\n"
            if self.state != self.STATE_FOLLOWDG:
                self.apr_activate(None)
                pass
            
            pass

        if event.keyval==0xff1b: # GDK_Escape
            # abort
            
            # set to current value of underlying parameter
            self.changedinhibit=True
            self.set_text(self.param.dcvalue.format(self.param.displayfmt))
            self.changedinhibit=False
            self.lastvalue=self.param.dcvalue

            self.set_state(self.STATE_FOLLOWDG)


            pass
        
        return False # returning True would eat the event


    def apr_activate(self,event):

        # print "activate!"
        #print "issue command %s %s" % (self.myprops["dg-param"],self.get_text())
        self.set_state(self.STATE_WAITING)
        
        if self.requestident is not None:
            requestident=self.requestident
            self.requestident=None
            self.param.cancelrequest(requestident)
            pass

        self.assignedvalue=self.param.paramtype(self.get_text(),defunits=self.param.defunits)
        
        # print "requestval; self.state=%d self.assignedvalue=%s" % (self.state,str(type(self.assignedvalue.val)))
        self.requestident=self.param.requestval(self.assignedvalue,self.requestvalcallback)
        # print "requestident=%s" % (str(self.requestident))
        pass
    
    def apr_changed(self,event):
        if not self.changedinhibit:
            # print "changed, event=%s!" % (str(event))
            self.set_state(self.STATE_ADJUSTING)
            pass
        
        pass
    
    def requestvalcallback(self,param,requestid,errorstr,result):
        # print "adjustparam requestvalcallback. self.state=%d" % (self.state)
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
            self.set_text(errorstr)
            self.changedinhibit=False
            
            self.set_state(self.STATE_FOLLOWDG)
            self.assignedvalue=None
            pass
        else :
            self.errorflag=False
            
            self.changedinhibit=True
            self.set_text(result.format(param.displayfmt))
            self.changedinhibit=False

            # resultobj=self.param.paramtype(result,defunits=self.param.defunits)
            
            # print str(type(result))
            # print str(type(self.assignedvalue))
            # print str(type(result.val))
            # print str(type(self.assignedvalue.val))
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
        self.state=state
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
        else:
            assert(0)
            pass
        
        pass

    pass


gobject.type_register(adjustparamreadout)  # required since we are defining new properties/signals
