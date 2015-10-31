

import os
import sys
import fcntl
import shutil
import pty
import threading
import subprocess
import urllib
from lxml import etree

try:
    from Queue import Queue, Empty
    pass
except ImportError:
    from queue import Queue, Empty  # python 3.x
    pass

try: 
    from shlex import quote # new (python 3) location
    pass
except ImportError:
    from pipes import quote # deprecated location
    pass

if not hasattr(sys.modules["__builtin__"],"basestring"):
    basestring=str  # python3
    pass


if not "gtk" in sys.modules:  # gtk3
    from gi.repository import Gtk as gtk
    from gi.repository import GObject as gobject
    from gi.repository import Gdk as gdk
    pass
else : 
    # gtk2
    import gtk
    import gtk.gdk as gdk
    import gobject
    pass

import canonicalize_path
from dc_gtksupp import build_from_file
from dc_gtksupp import dc_initialize_widgets
import dc2_misc

__pychecker__="no-import no-argsused"

xpathnamespaces={"dc":"http://thermal.cnde.iastate.edu/datacollect","dcv":"http://thermal.cnde.iastate.edu/dcvalue"}


# TODO : Should add an "abort script" button and status field


# gtk superclass should be first of multiple inheritances
class rundatacollectstep(gtk.HBox):
    __gtype_name__="rundatacollectstep"
    __gproperties__ = {       
        "description": (gobject.TYPE_STRING,
                     "description of step",
                     "description of step",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags
        "buttonlabel": (gobject.TYPE_STRING,
                        "Text for the button label",
                        "Text for the button label",
                        "", # default value 
                        gobject.PARAM_READWRITE), # flags
        "datacollectconfig": (gobject.TYPE_STRING,
                              "Datacollect configuration file to use",
                              "Datacollect configuration file to use",
                              "", # default value 
                              gobject.PARAM_READWRITE), # flags
        "datacollectconfig2": (gobject.TYPE_STRING,
                              "Second datacollect configuration file to use",
                              "Second datacollect configuration file to use",
                              "", # default value 
                              gobject.PARAM_READWRITE), # flags
        "datacollectconfig3": (gobject.TYPE_STRING,
                              "Third datacollect configuration file to use",
                              "Third datacollect configuration file to use",
                              "", # default value 
                              gobject.PARAM_READWRITE), # flags
        "dcparamdb": (gobject.TYPE_STRING,
                     "Datacollect paramdb (.dpd) file to load settings and parameters from",
                     "Datacollect paramdb (.dpd) file to load settings and parameters from",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags
        "planfile": (gobject.TYPE_STRING,
                     "Plan (.plx) file to run... maybe path relative to this filled checklist",
                     "Plan (.plx) file to run... maybe path relative to this filled checklist",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags
        "suffix": (gobject.TYPE_STRING,
                     "Suffix on planfile for THIS LOG (before .xlg). i.e. planfile_suffix.xlg and planfile_suffix.plf",
                     "Suffix on planfile for THIS LOG (before .xlg). i.e. planfile_suffix.xlg and planfile_suffix.plf",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags
        "gui": (gobject.TYPE_STRING,
                "Gui (.glade) to open (optional)",
                "Gui (.glade) to open (optional)",
                "", # default value 
                gobject.PARAM_READWRITE), # flags
        "gui2": (gobject.TYPE_STRING,
                "Second gui (.glade) to open (optional)",
                "Second gui (.glade) to open (optional)",
                "", # default value 
                gobject.PARAM_READWRITE), # flags
        "gui3": (gobject.TYPE_STRING,
                "Third gui (.glade) to open (optional)",
                "Third gui (.glade) to open (optional)",
                "", # default value 
                gobject.PARAM_READWRITE), # flags
        "multispecimen": (gobject.TYPE_BOOLEAN,
                          "multi-specimen mode for new datacollect (true/false)",
                          "multi-specimen mode for new datacollect (true/false)",
                          False, # default value 
                     gobject.PARAM_READWRITE), # flags
        
        }
    checklist=None
    xmlpath=None

    description=None
    buttonlabel=None
    datacollectconfig=None
    datacollectconfig2=None
    datacollectconfig3=None
    dcparamdb=None
    planfile=None
    suffix=None
    gui=None
    gui2=None
    gui3=None
    multispecimen=None


    xlgparsed=None
    xlgtime=None
    plfparsed=None
    plftime=None
    
                      
    def __init__(self,checklist,step,xmlpath):
        gobject.GObject.__init__(self)

        (self.gladeobjdict,self.gladebuilder)=build_from_file(os.path.join(os.path.split(sys.modules[self.__module__].__file__)[0],"rundatacollectstep.glade"))   

        self.checklist=checklist
        self.xmlpath=xmlpath

        if self.description is None:
            self.description=""
            pass
        
        if self.buttonlabel is None:
            self.buttonlabel=""
            pass

        if self.datacollectconfig is None:
            self.datacollectconfig=""
            pass

        if self.datacollectconfig2 is None:
            self.datacollectconfig2=""
            pass

        if self.datacollectconfig3 is None:
            self.datacollectconfig3=""
            pass
        
        if self.dcparamdb is None:
            self.dcparamdb=""
            pass

        if self.planfile is None:
            self.planfile=""
            pass

        if self.suffix is None:
            self.suffix=""
            pass

        if self.gui is None:
            self.gui=""
            pass

        if self.gui2 is None:
            self.gui2=""
            pass

        if self.gui3 is None:
            self.gui3=""
            pass

        if self.multispecimen is None:
            self.multispecimen=False
            pass


        self.pack_start(self.gladeobjdict["rundatacollectstep"],True,True,0)

        self.gladeobjdict["pushbutton"].connect("clicked",self.buttoncallback)
        self.gladeobjdict["step_descr_label"].set_selectable(True)
        
        # We implement custom tooltips on the push button to indicate
        # status. 
        self.gladeobjdict["pushbutton"].set_has_tooltip(True)
        self.gladeobjdict["pushbutton"].connect("query-tooltip",self.button_tooltip)

        # connect button-press-event so we can implement copy of the tooltip data to the clipboard
        self.gladeobjdict["pushbutton"].connect("button-press-event",self.button_mousepress)
        
        gobject.timeout_add(2000,self.update_status)

        pass    

    def update_status(self):
        if self.checklist.paramdb is None:
            # checklist has been destroyed... no need for status anymore
            return False


        if len(self.planfile)==0:
            status="No planfile"
            pass
        elif (not os.path.isabs(self.planfile) and self.checklist.xmldoc.filename is None):
            status="Planfile relative to undetermined checklist location"
        else :
            planfile=self.planfile
            if not os.path.isabs(planfile):
                planfile=os.path.join(os.path.split(self.checklist.xmldoc.filename)[0],planfile)
                pass

            basename=os.path.splitext(planfile)[0]            
            basefilename=os.path.split(basename)[1]

            if self.suffix=="":
                suffix=""
                pass
            else :
                suffix="_%s" % (self.suffix)
                pass
            
            xlgfile=basename+suffix+".xlg"
            xlgdir=basename+suffix+"_files"
            
            filledplan=os.path.join(xlgdir,basefilename+suffix+".plf")
            
            if not os.path.exists(xlgfile) or not os.path.exists(filledplan):
                status="No output files"
                pass
            else :
                # update parsed copy of experiment log if needed
                xlgtime=os.stat(xlgfile).st_mtime                
                if xlgtime != self.xlgtime:
                    self.xlgtime=xlgtime
                    try: 
                        self.xlgparsed=None
                        self.xlgparsed=etree.parse(xlgfile)
                        pass
                    except:
                        pass
                    pass

                plftime=os.stat(filledplan).st_mtime
                if plftime != self.plftime:
                    self.plftime=plftime
                    try: 
                        self.plfparsed=None
                        self.plfparsed=etree.parse(filledplan)
                        pass
                    except:
                        pass
                    pass

                if os.path.exists(xlgfile):
                    # store in checklist
                    self.checklist.xmldoc.lock_rw()
                    try:
                        xmltag=self.checklist.xmldoc.restorepath(self.xmlpath)
                        dcexplogels=self.checklist.xmldoc.xpathcontext(xmltag,"dc:explog")
                        if len(dcexplogels)==0:
                            explogel=self.checklist.xmldoc.addelement(xmltag,"dc:explog")
                            pass
                        else: 
                            explogel=dcexplogels[0]
                            pass

                        # set <dc:explog xlink:href="..."> attribute if it's not already set
                        url=urllib.pathname2url(canonicalize_path.relative_path_to(self.checklist.xmldoc.getcontextdir(),xlgfile))
                        if self.checklist.xmldoc.getattr(explogel,"xlink:href","") != url:
                            self.checklist.xmldoc.setattr(explogel,"xlink:href",url)
                            pass
                        pass
                    finally:
                        self.checklist.xmldoc.unlock_rw()
                        pass
                        
                    pass

                if os.path.exists(filledplan):
                    # store in checklist
                    self.checklist.xmldoc.lock_rw()
                    try:
                        xmltag=self.checklist.xmldoc.restorepath(self.xmlpath)
                        dcchecklistsels=self.checklist.xmldoc.xpathcontext(xmltag,"dc:checklists")
                        if len(dcchecklistsels)==0:
                            dcchecklistsel=self.checklist.xmldoc.addelement(xmltag,"dc:checklists")
                            pass
                        else: 
                            dcchecklistsel=dcchecklistsels[0]
                            pass
                        
                        dcchecklistels=self.checklist.xmldoc.xpathcontext(dcchecklistsel,"dc:checklist")
                        if len(dcchecklistels)==0:
                            dcchecklistel=self.checklist.xmldoc.addelement(dcchecklistsel,"dc:checklist")
                            pass
                        else: 
                            dcchecklistel=dcchecklistels[0]
                            pass
                        
                        
                        # set <dc:checklist xlink:href="..."> attribute if it's not already set
                        url=urllib.pathname2url(canonicalize_path.relative_path_to(self.checklist.xmldoc.getcontextdir(),filledplan))
                        if self.checklist.xmldoc.getattr(dcchecklistel,"xlink:href","") != url:
                            self.checklist.xmldoc.setattr(dcchecklistel,"xlink:href",url)
                            pass
                        pass
                    finally:
                        self.checklist.xmldoc.unlock_rw()
                        pass
                        
                    pass

                if self.plfparsed is None or self.xlgparsed is None:
                    status="corrupt or changing files"
                    pass
                plfchecked=self.plfparsed.xpath('count(/chx:checklist/chx:checkitem[@checked="true"])',namespaces={'chx':'http://thermal.cnde.iastate.edu/checklist'})
                plftotal=self.plfparsed.xpath('count(/chx:checklist/chx:checkitem)',namespaces={'chx':'http://thermal.cnde.iastate.edu/checklist'})

                xlgmeas=self.xlgparsed.xpath('count(/dc:experiment/dc:measurement)',namespaces={'dc':'http://thermal.cnde.iastate.edu/datacollect'})
                
                status="%d/%d steps; %d meas." % (plfchecked,plftotal,xlgmeas)
                pass
            pass
        
        self.gladeobjdict["statusreadout"].set_text(status)
        return True

    def do_set_property(self,property,value):
        if property.name=="description":
            self.description=value
            self.gladeobjdict["step_descr_label"].set_markup(value)  
            pass
        elif property.name=="buttonlabel":
            self.buttonlabel=value
            self.gladeobjdict["pushbutton"].set_label(self.buttonlabel)
            pass
        elif property.name=="datacollectconfig":
            self.datacollectconfig=value
            pass
        elif property.name=="datacollectconfig2":
            self.datacollectconfig2=value
            pass
        elif property.name=="datacollectconfig3":
            self.datacollectconfig3=value
            pass
        elif property.name=="dcparamdb":
            self.dcparamdb=value
            pass
        elif property.name=="planfile":
            self.planfile=value
            pass
        elif property.name=="suffix":
            self.suffix=value
            pass
        elif property.name=="gui":
            self.gui=value
            pass
        elif property.name=="gui2":
            self.gui2=value
            pass
        elif property.name=="gui3":
            self.gui3=value
            pass
        elif property.name=="multispecimen":
            # sys.stderr.write("set multispecimen property to %s!\n" % (str(value)))
            if isinstance(value,basestring):
                raise ValueError("Attempt to set boolean value of %s with a string %s" % (property.name,value)) 
            self.multispecimen=bool(value)
            pass
        else :
            raise ValueError("Unknown property: %s" % (property.name))
        pass
    
    def do_get_property(self,property):
        if property.name=="description":
            return self.description
        elif property.name=="buttonlabel":
            return self.buttonlabel
        elif property.name=="datacollectconfig":
            return self.datacollectconfig
        elif property.name=="datacollectconfig2":
            return self.datacollectconfig2
        elif property.name=="datacollectconfig3":
            return self.datacollectconfig3
        elif property.name=="dcparamdb":
            return self.dcparamdb
        elif property.name=="planfile":
            return self.planfile
        elif property.name=="suffix":
            return self.suffix
        elif property.name=="gui":
            return self.gui
        elif property.name=="gui2":
            return self.gui2
        elif property.name=="gui3":
            return self.gui3
        elif property.name=="multispecimen":
            return self.multispecimen
        else :
            raise ValueError("Unknown property %s" % (property.name))
        pass


    def dc_gui_init(self,guistate):
        # need next line if subclassing a dc_gui class
        # super(dg_readout).__dc_gui_init(self,io)
        
        
        self.paramdb=guistate.paramdb
        self.dc_gui_io=guistate.io

        dc_initialize_widgets(self.gladeobjdict,guistate)

        pass
    

    def determine_command(self):



        commandlist=[]
        mkdir=None
        cpsrc=None
        cpdest=None
        cpparent=None

        if self.checklist.xmldoc.filename is None or len(self.planfile)==0:

            #if len(self.planfile)==0 or (not os.path.isabs(self.planfile) and self.checklist.xmldoc.filename is None):
            return (None,None,None,None,['datacollect2'],'datacollect2')

        planfile=self.planfile
        # sys.stderr.write("self.planfile=%s\n" % (self.planfile))
        if not os.path.isabs(planfile):
            planfile=os.path.join(os.path.split(self.checklist.xmldoc.filename)[0],planfile)
            pass
        # sys.stderr.write("planfile=%s\n" % (planfile))

        basename=os.path.splitext(planfile)[0]
        basefilename=os.path.split(basename)[1]

        if self.suffix=="":
            suffix=""
            pass
        else :
            suffix="_%s" % (self.suffix)
            pass
        xlgfile=basename+suffix+".xlg"
        xlgdir=basename+suffix+"_files"

        # sys.stderr.write("xlgdir=%s\n" % (xlgdir))
        # sys.stderr.write("xlgfile=%s\n" % (xlgfile))

        filledplan=os.path.join(xlgdir,basefilename+suffix+".plf")

        if not os.path.exists(xlgdir):
            mkdir=xlgdir
            pass
        
        
        if not os.path.exists(filledplan):
            cpparent=canonicalize_path.relative_path_to(".",self.checklist.xmldoc.filename)
            cpsrc=canonicalize_path.relative_path_to(".",planfile)
            cpdest=canonicalize_path.relative_path_to(".",filledplan)
            pass
        

        commandlist.append('datacollect2')

        if self.multispecimen:
            commandlist.append('-m')
            pass
        else:
            commandlist.append('-s')
            pass

        if len(self.dcparamdb) > 0:
            commandlist.append('-d')
            commandlist.append(self.dcparamdb)
            pass

        if len(self.datacollectconfig) > 0:
            commandlist.append('-f')
            commandlist.append(self.datacollectconfig)
            pass 

        if len(self.datacollectconfig2) > 0:
            commandlist.append('-f')
            commandlist.append(self.datacollectconfig2)
            pass 

        if len(self.datacollectconfig3) > 0:
            commandlist.append('-f')
            commandlist.append(self.datacollectconfig3)
            pass 

        if os.path.exists(xlgfile):
            commandlist.append('-a')
            pass
            
        commandlist.append(xlgfile)

        commandlist.append('--parent')
        xlgfilecontextdir=os.path.split(xlgfile)[0]
        commandlist.append(canonicalize_path.relative_path_to(xlgfilecontextdir,self.checklist.xmldoc.filename))
        
        commandlist.append('-p')
        commandlist.append(filledplan)

        if len(self.gui) > 0:
            commandlist.append('-g')
            commandlist.append(self.gui)
            pass

        if len(self.gui2) > 0:
            commandlist.append('-g')
            commandlist.append(self.gui2)
            pass

        if len(self.gui3) > 0:
            commandlist.append('-g')
            commandlist.append(self.gui3)
            pass

        # create full shell-compatible command
        fullcmd=""
        if mkdir is not None:
            fullcmd+="mkdir %s ; " % (quote(mkdir))
            pass

        if cpsrc is not None:
            fullcmd+="dc_chx2chf %s %s %s ; " % (quote(cpparent),quote(cpsrc),quote(cpdest))
            pass

        fullcmd+=" ".join([quote(term) for term in commandlist])

        return (mkdir,cpparent,cpsrc,cpdest,commandlist,fullcmd)

    def button_tooltip(self,item,x,y, keyboard_mode, tooltip):
        fullcmd=self.determine_command()[5]
        tooltip.set_text(fullcmd+"\n(Press right mouse button to copy to clipboard)")
        return True

    def button_mousepress(self,obj,event):
        # sys.stderr.write("event.type=0x%x event.button=0x%x\n" % (event.type,event.button))

        if event.type==gdk.BUTTON_PRESS and event.button==3:
            clipstring=self.determine_command()[5]

            clipboard=gtk.Clipboard(gdk.display_get_default(),"PRIMARY")
            clipboard.set_text(clipstring,-1)
            clipboard.store()
            clipboard=gtk.Clipboard(gdk.display_get_default(),"CLIPBOARD")
            clipboard.set_text(clipstring,-1)
            clipboard.store()
        
            return True # eat event
        else :
            return False
        pass

    
    def buttoncallback(self,*args):
        # fork off process; fork off reader thread that uses gobject.timeout_add() to pass data back every few seconds. Then triggers scriptcompletecallback when done. 
        # command should have a "%(id)s" where the id should be substituted 
        # and a %(basename)s where the base of the output file name should
        # be substituted
        # note: current directoy will be the destination location and files
        # should be output there. 
        # sys.stderr.write("Got buttoncallback... forking suprocess and starting thread\n");

        (mkdir,cpparent,cpsrc,cpdest,commandlist,fullcmd)=self.determine_command()

        if mkdir is not None:
            os.mkdir(mkdir)
            pass
        
        #if cpsrc is not None:
        #    shutil.copyfile(cpsrc,cpdest)
        #    pass
        if cpparent is not None:
            dc2_misc.chx2chf(".",cpparent,".",cpsrc,".",cpdest)
            pass
        

        try : 
            # sys.stderr.write("commandlist=%s\n" % (str(self.determine_command()[4])))
            subprocess.Popen(commandlist,close_fds=True)
            pass
        except : 
            exc_type,exc_value,tb = sys.exc_info()
            sys.stderr.write("child_traceback=%s\n" % (str(exc_value.child_traceback)))
            raise
        
        
        return True
    

 
    def resetchecklist(self):
        # clear out any dc:autoexp tags that have been added 
        # autoexps=self.xmltag.xpath('dc:autoexp',namespaces=xpathnamespaces)
        # for autoexp in autoexps:
        #     autoexp.getparent().remove(autoexp)
        #     pass
        
        pass


    pass


gobject.type_register(rundatacollectstep)  # required since we are defining new properties/signals
