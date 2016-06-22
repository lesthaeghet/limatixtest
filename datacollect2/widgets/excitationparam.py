import os
import os.path
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

from ..dc_value import numericunitsvalue as numericunitsv
from ..dc_value import stringvalue as stringv
from ..dc_value import excitationparamsvalue as excitationparamsv
# import dc_value


# WARNING: Not thread safe, in part because of 
#  changedinhibit flag

from ..dc_gtksupp import paramhandler
from ..dc_gtksupp import build_from_file
from ..dc_gtksupp import dc_initialize_widgets
from ..dc_gtksupp import guistate as gs_guistate

if hasattr(gtk,"StateType") and hasattr(gtk.StateType,"NORMAL"):
    # gtk3
    STATE_NORMAL=gtk.StateType.NORMAL
    STATE_PRELIGHT=gtk.StateType.PRELIGHT
    pass
else:
    STATE_NORMAL=gtk.STATE_NORMAL
    STATE_PRELIGHT=gtk.STATE_PRELIGHT
    pass


__pychecker__="no-import no-argsused"


class dummy(object):
    pass
thisdir=os.path.split(sys.modules[dummy.__module__].__file__)[0]



# gtk superclass should be first of multiple inheritances
class excitationparam(gtk.HBox,paramhandler):
    __gtype_name__="excitationparam"
    __gproperties__ = {
        # set command will be dg-param plus a space plus parameter
        # query command will be dg-param plus a question mark.

        "paramname": (gobject.TYPE_STRING,
                     "paramdb2 parameter to set",
                     "paramdb2 parameter to set (usually \'excitation\')",
                     "excitation", # default value 
                     gobject.PARAM_READWRITE), # flags

         "labelmarkup": (gobject.TYPE_STRING,
                     "Markup string for the label",
                     "Markup string for the label",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags

        "hide-type": (gobject.TYPE_BOOLEAN,
                     "Should type field be hidden?",
                     "Should type field be hidden?",
                     False, # default value 
                     gobject.PARAM_READWRITE), # flags

        "hide-wfm": (gobject.TYPE_BOOLEAN,
                     "Should wfm field be hidden?",
                     "Should wfm field be hidden?",
                     False, # default value 
                     gobject.PARAM_READWRITE), # flags

        "hide-f0": (gobject.TYPE_BOOLEAN,
                     "Should f0 field be hidden?",
                     "Should f0 field be hidden?",
                     False, # default value 
                     gobject.PARAM_READWRITE), # flags

        "hide-f1": (gobject.TYPE_BOOLEAN,
                     "Should f1 field be hidden?",
                     "Should f1 field be hidden?",
                     False, # default value 
                     gobject.PARAM_READWRITE), # flags

        "hide-t0": (gobject.TYPE_BOOLEAN,
                     "Should t0 field be hidden?",
                     "Should t0 field be hidden?",
                     False, # default value 
                     gobject.PARAM_READWRITE), # flags

        "hide-t1": (gobject.TYPE_BOOLEAN,
                     "Should t1 field be hidden?",
                     "Should t1 field be hidden?",
                     False, # default value 
                     gobject.PARAM_READWRITE), # flags

        "hide-t2": (gobject.TYPE_BOOLEAN,
                     "Should t2 field be hidden?",
                     "Should t2 field be hidden?",
                     False, # default value 
                     gobject.PARAM_READWRITE), # flags

        "hide-t3": (gobject.TYPE_BOOLEAN,
                     "Should t3 field be hidden?",
                     "Should t3 field be hidden?",
                     False, # default value 
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
    __proplist = ["paramname","labelmarkup", "hide-type","hide-wfm","hide-f0","hide-f1","hide-t0","hide-t1","hide-t2","hide-t3"] 

    paramdb=None
    param=None
    lastvalue=None # last value provided by controller
    errorflag=None

    private_paramdb=None
    controller=None # excitationparamscontroller

    gladeobjdict=None
    builder=None
    

    def __init__(self):
        gobject.GObject.__init__(self)
        paramhandler.__init__(self,super(excitationparam,self),self.__proplist)
        # gtk.HBox.__init__(self) # Not supposed to call superclass __init__ method, just gobject __init__ according to    http://www.pygtk.org/articles/subclassing-gobject/sub-classing-gobject-in-python.htm  
        # self.myprops["dg-paramsuffix"]=""



        self.errorflag=False


        (self.gladeobjdict,self.builder)=build_from_file(os.path.join(thisdir,"excitationparam.glade"))
        
        self.pack_start(self.gladeobjdict["excitationparam"],True,True,0)

        pass
    

    def isconsistent(self,inconsistentlist):
        consistent=True
        for key in self.gladeobjdict:
            if hasattr(self.gladeobjdict[key],"isconsistent"):
                consistent=consistent and self.gladeobjdict[key].isconsistent(inconsistentlist)
                pass
            pass
        
        return consistent
    

    
    def dc_gui_init(self,guistate):
        # need next line if subclassing a dc_gui class
        # super(dc_readout).__dc_gui_init(self,guistate)
        

        if self.paramdb is None:  # allow manual initialization of paramdb, in case we are to use a non-default paramdb
            self.paramdb=guistate.paramdb
            pass
        
        # print "FOO!"
        # set no_show_all property for all widgets we are supposed to hide.
        for key in self.gladeobjdict:
            # print "Consider %s %s" % (key,str("hide-"+key in self.myprops))
            # if "hide-"+key in self.myprops:
                # print "Value=%s" % (str(self.myprops["hide-"+key]))
            if "hide-"+key in self.myprops and self.myprops["hide-"+key]:
                # print "Hide %s" % (key)
                self.gladeobjdict[key].set_no_show_all(True)
                pass
            pass

        self.gladeobjdict["type"].set_property("labelmarkup",self.myprops["labelmarkup"]+" ")

        # sys.stdout.flush()
        # raise ValueError(dc_gui_init)
        
        # self.gladeobjdict["wfm"].set_no_show_all(True)
    
        if self.myprops["paramname"] not in self.paramdb:
            raise ValueError("No parameter database entry for \"%s\". Does this file need to be viewed within datacollect, and are you using the correct .dcc file?" % (self.myprops["paramname"]))
        self.param=self.paramdb[self.myprops["paramname"]]
        self.lastvalue=self.param.dcvalue

        # self.param.addnotify(self.changeinprogress,pdb.param.NOTIFY_CONTROLLER_REQUEST)
        # self.param.addnotify(self.newvalue,pdb.param.NOTIFY_NEWVALUE,)
        


        # private paramdb is a private database of just the internal parameters of the excitation. 
        self.private_paramdb=pdb.paramdb(None)

        self.controller=excitationparamscontroller(self.private_paramdb,self.param)

        self.private_paramdb.addparam("type",stringv,build=self.controller.addparam,options=["SWEEP","BURST"])
        self.private_paramdb.addparam("wfm",stringv,build=self.controller.addparam)
        self.private_paramdb.addparam("f0",numericunitsv,defunits="Hz",displayfmt="%.1f",build=self.controller.addparam)
        self.private_paramdb.addparam("f1",numericunitsv,defunits="Hz",displayfmt="%.1f",build=self.controller.addparam)
        self.private_paramdb.addparam("t0",numericunitsv,defunits="s",build=self.controller.addparam)
        self.private_paramdb.addparam("t1",numericunitsv,defunits="s",build=self.controller.addparam)
        self.private_paramdb.addparam("t2",numericunitsv,defunits="s",build=self.controller.addparam)
        self.private_paramdb.addparam("t3",numericunitsv,defunits="s",build=self.controller.addparam)

        self.controller.newvalue(self.param,pdb.param.NOTIFY_NEWVALUE)

        substate=gs_guistate(None,self.private_paramdb,guistate.searchdirs)

        dc_initialize_widgets(self.gladeobjdict,substate)
        
        

        #self.connect("key-press-event",self.apr_keypress)
        #self.connect("activate",self.apr_activate)
        #self.connect("changed",self.apr_changed)

        pass


    
    # def newvalue(self,param,condition):

    #    # propagate new value out to controller
    #    self.controller.newvalue(param.dcvalue)

    #     if self.lastvalue != param.dcvalue:
    #         self.lastvalue=param.dcvalue
            
    #         # self.set_state(self.STATE_FOLLOWDG) # clear a color change resulting from a command 
    #        # print "not equal"
    #         pass

    #    pass
    

    def setbgcolor(self,color):
        colormap={"white" : "#ffffff",
                  "red"   : "#ff0000",
                  "yellow": "#ffff00",
                  "ltblue": "#80a0ff",
                  "magenta": "#ff00ff",
                  "green": "#00f000",
                  "orange": "#ff8000"}

        self.modify_base(STATE_NORMAL,gdk.color_parse(colormap[color]))
        pass
        
    

    pass



class excitationparamscontroller(object):
    # Simple class for controlling a sub-parameters of the excitation settings
    controlparams=None
    id=None
    state=None  # see CONTROLLER_STATE defines in definition of param class
    numpending=None
    excparamdb=None # private paramdb of excitation settings
    excparam=None # public param of excitation. Should be of type excitationparamsvalue

    def __init__(self,excparamdb,excparam):
        self.controlparams={}
        self.id=id(self)
        self.state=excparam.CONTROLLER_STATE_QUIESCENT
        self.numpending=0
        self.excparamdb=excparamdb
        self.excparam=excparam

        self.excparam.addnotify(self.newvalue,pdb.param.NOTIFY_NEWVALUE)

        pass


    def addparam(self,param):
        self.controlparams[param.xmlname]=param

        return self

    def requestvalcallback(self,controlparam,requestid,errorstr,newvalue,*cbargs):
        # print "excitationcallback: newvalue=%s" % (str(newvalue))
        self.numpending -= 1
        if (self.numpending==0):
            self.state=controlparam.CONTROLLER_STATE_QUIESCENT
            pass

        if errorstr is not None:
            if len(cbargs) > 1:
                subparam=cbargs[0]
                clientcallback=cbargs[1]
                clientcallback(subparam,requestid,errorstr,None,*cbargs[2:])
                pass
            pass
        
        # assignment of sub-params is handled by newvalue()
        # for key in self.controlparams:
        #     curparam=self.controlparams[key]
        #     curval=getattr(newvalue,key)

        #     curparam.assignval(curparam.paramtype(curval,units=curparam.defunits),self.id)
        #     pass
        
        if len(cbargs) > 1:
            subparam=cbargs[0]
            clientcallback=cbargs[1]
            clientcallback(subparam,requestid,None,subparam.dcvalue,*cbargs[2:])
            pass
        
        return False
 
    # requestval is a request that this parameter take on the requested value
    # (This is an asynchronous request. Will get callback when complete)
    # returns request identifier that can be used to cancel request 
    # callback(param,requestid,errorstr,newvalue,*cbargs)
    def requestval(self,param,newvalue,*cbargs):

        # extract excparamdb into simple dict
        paramdict={}
        for key in self.excparamdb:
            privateentryvalue=self.excparamdb[key].dcvalue
            if hasattr(privateentryvalue,"valuedefunits"):
                paramdict[key]=privateentryvalue.valuedefunits()
                pass
            else : 
                paramdict[key]=str(privateentryvalue)
                pass
                           
            pass
        privateentryvalue=newvalue
        if hasattr(privateentryvalue,"valuedefunits"):
            paramdict[param.xmlname]=privateentryvalue.valuedefunits()
            pass
        else : 
            paramdict[key]=str(privateentryvalue)
            pass
        
        
        # pass on request to excparam
        fullvalue=self.excparam.paramtype(paramdict)
        requestid=self.excparam.requestval(fullvalue,self.requestvalcallback,param,*cbargs)
        self.state=param.CONTROLLER_STATE_REQUEST_PENDING
        self.numpending+=1
        return requestid
    

    def cancelrequest(self,param,requestid): 
        # returns True if successfully canceled
        canceled=self.excparam.cancelrequest(requestid)
        if canceled: 
            self.numpending -= 1
            if (self.numpending==0):
                self.state=param.CONTROLLER_STATE_QUIESCENT
                pass
            pass
        
        return canceled

    def newvalue(self,param,condition):

        # This is called in response to a new value of excparam
        newvalue=param.dcvalue
        for key in self.controlparams:
            curparam=self.controlparams[key]
            curval=getattr(newvalue,key)
            
            curparam.assignval(curparam.paramtype(curval,defunits=curparam.defunits),self.id)
            pass
        
        
        pass

    pass




gobject.type_register(excitationparam)  # required since we are defining new properties/signals
