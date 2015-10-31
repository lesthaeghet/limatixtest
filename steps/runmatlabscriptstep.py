import os
import sys

if not "gtk" in sys.modules:  # gtk3
    from gi.repository import Gtk as gtk
    from gi.repository import GObject as gobject
    pass
else : 
    # gtk2
    import gtk
    import gobject
    pass


from runscriptstep import runscriptstep

class runmatlabscriptstep(runscriptstep):
    __gtype_name__="runmatlabscriptstep"
    __gproperties__ = {       
        # inherits properties scriptlog, buttonlabel, viewautoexp, description
        "matlabfuncall": (gobject.TYPE_STRING,
                          "matlab function call to make",
                          "matlabfuncall should have a \'%(id)s\' where the id should be substituted and a \'%(basename)s\' where the base of the output file name should be substituted note: current directoy will be the destination location and files should be output there.",
                    "", # default value 
                          gobject.PARAM_READWRITE), # flags
        "matlabfundir": (gobject.TYPE_STRING,
                         "directory in which matlab function is defined",
                         "directory in which matlab function is defined; will be prepended to MATLABPATH",
                         "", # default value 
                          gobject.PARAM_READWRITE), # flags
        }
    matlabfuncall=None
    matlabfundir=None
    
    def __init__(self,checklist,step,xmlpath):
        runscriptstep.__init__(self,checklist,step,xmlpath)
        if self.matlabfuncall is None:
            self.matlabfuncall=""
            pass

        if self.matlabfundir is None:
            self.matlabfundir=""
            pass

        
        pass

    def do_set_property(self,property,value):
        if property.name=="matlabfuncall":
            self.matlabfuncall=value
            self.set_property('command','matlab -nosplash -nodesktop -r \"%s ; exit\"' % (self.matlabfuncall))
            pass
        elif property.name=="matlabfundir":
            self.matlabfundir=value
            self.environstr="export \"MATLABPATH=%s:$MATLABPATH\" ; " % (self.matlabfundir)
            if "MATLABPATH" in os.environ:
                self.environadd={"MATLABPATH": "%s:%s" % (self.matlabfundir,os.environ["MATLABPATH"])}
                pass
            else : 
                self.environadd={"MATLABPATH": self.matlabfundir}
                pass
            
            pass
        else :
            return runscriptstep.do_set_property(self,property,value)
        pass

    def do_get_property(self,property,value):
        if property.name=="matlabfuncall":
            return self.matlabfuncall
        elif property.name=="matlabfundir":
            return self.matlabfundir
        else :
            return runscriptstep.do_get_property(self,property,value)
        pass

    pass

gobject.type_register(runmatlabscriptstep)  # required since we are defining new properties/signals
