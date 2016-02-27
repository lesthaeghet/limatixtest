import os
import os.path
import sys

if "gi" in sys.modules:  # gtk3
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk as gtk
    from gi.repository import GObject as gobject
    pass
else : 
    # gtk2
    import gobject
    import gtk
    pass
    
from dc_gtksupp import build_from_file
from dc_gtksupp import dc_initialize_widgets

from dc_value import hrefvalue as hrefv


class steptemplate(gtk.HBox):
    __gtype_name__="steptemplate"
    # __gproperties__ = {}
    
    dc_gui_iohandlers=None
    gladeobjdict=None
    gladebuilder=None
    stepnumber=None
    stepdescr=None
    steptype=None
    stepobj=None
    #execcode=None
    params=None
    checklist=None
    xmlpath=None
    paramdb=None

    def __init__(self,stepnumber,stepdescr,steptype,params,checklist,xmlpath,paramdb):
        gobject.GObject.__init__(self)
        
        self.stepnumber=stepnumber
        self.stepdescr=stepdescr
        self.steptype=steptype
        # self.execcode=execcode
        self.params=params
        self.checklist=checklist
        self.xmlpath=xmlpath
        self.paramdb=paramdb

        # self.resize(1,1)
        
        (self.gladeobjdict,self.gladebuilder)=build_from_file(os.path.join(os.path.split(sys.modules[self.__module__].__file__)[0],"steptemplate.glade"))   

        self.gladeobjdict["numbertitle"].set_property("label","%d. %s" % (self.stepnumber,self.stepdescr))

        stepclass = None
        stepobjdict={}

        exec("from steps.%s import %s as stepclass" % (steptype,steptype),stepobjdict,stepobjdict)
        stepclass=stepobjdict["stepclass"]

        self.stepobj=stepclass(checklist,self,xmlpath)
        
        # self.gladeobjdict["steptemplatehbox"].add_with_properties(self.stepobj,"position",0) # step info goes between number and checkbutton (pos #0) 
        self.gladeobjdict["steptemplatehbox"].pack_start(self.stepobj,True,True,0) # step info goes between number and checkbutton (pos #0) 
        self.gladeobjdict["steptemplatehbox"].reorder_child(self.stepobj,0)
        
        self.pack_start(self.gladeobjdict["steptemplate"],True,True,0)

        ## create local variables accessible to exec code
        #execlocallist=list(self.gladeobjdict.items())
        #if hasattr(self.stepobj,"gladeobjdict"):
        #    execlocallist.extend(list(self.stepobj.gladeobjdict.items()))
        #    pass
        #
        #execlocallist.append(("stepobj",self.stepobj))
        #self.execlocaldict=dict(execlocallist)
        
        # print "%s\n%s" % (stepdescr,self.execcode)
        #exec("if True:\n%s" % (self.execcode),globals(),self.execlocaldict)
        for key in self.params:
            self.stepobj.set_property(key,self.params[key])
            pass

        pass
    
    def dc_gui_init(self,guistate):
        # need next line if subclassing a dc_gui class
        # super(dc_readout).__dc_gui_init(self,guistate)
        
        # self.gladeobjdict["setparam"].set_property("dg-paramdefault",self.myprops["dg-paramdefault"])

        
        self.dc_gui_iohandlers=guistate.iohandlers

        dc_initialize_widgets(self.gladeobjdict,guistate)
        self.stepobj.dc_gui_init(guistate)

        pass

    # called by checklist when a box is checked or unchecked
    # (checked is the new state)
    def handle_check(self,checked):
        # dispatch to stepboj if stepobj has a handle_check method
        if hasattr(self.stepobj,"handle_check"):
            self.stepobj.handle_check(checked)
            pass
        
        pass
    

    # called by checklist when checklist is set readonly or non-readonly
    def set_readonly(self,readonly):
        checkbutton=self.gladeobjdict["checkbutton"]
        checkbutton.set_sensitive(not(readonly))

        # call set_readonly() method of the step, if present
        if hasattr(self.stepobj,"set_readonly"):
            self.stepobj.set_readonly(readonly)
            pass
        
        pass
    
        
    
    def destroystep(self):
        if hasattr(self.stepobj,"destroystep"):
            self.stepobj.destroystep()
            pass
        pass

    def isconsistent(self,inconsistentlist):
        consistent=True

        for key in self.gladeobjdict:
            if hasattr(self.gladeobjdict[key],"isconsistent"):
                consistent=consistent and self.gladeobjdict[key].isconsistent(inconsistentlist)
                pass
            pass

        if hasattr(self.stepobj,"isconsistent"):
            consistent=consistent and self.stepobj.isconsistent(inconsistentlist)
            pass
        
        return consistent
    
    
    
    def resetchecklist(self):
        # called when this check list should be reset

        # clear check box
        self.gladeobjdict["checkbutton"].set_property("active",False)

        # Tell object ot reset itself if it can: 
        if hasattr(self.stepobj,"resetchecklist"):
            self.stepobj.resetchecklist()
            pass
        pass
    
    pass
        
gobject.type_register(steptemplate)  # required since we are defining new properties/signals

