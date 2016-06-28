

import os
import sys
#import fcntl
import shutil
import pty
import threading
import subprocess
import posixpath

from lxml import etree

try:
    from Queue import Queue, Empty
    pass
except ImportError:
    from queue import Queue, Empty  # python 3.x
    pass

try: 
    from shlex import quote as quoteshell # new (python 3) location
    pass
except ImportError:
    from pipes import quote as quoteshell# deprecated location
    pass

try: 
    import builtins  # python3
    pass
except ImportError: 
    import __builtin__ as builtins # python2
    pass


if not hasattr(builtins,"basestring"):
    basestring=str  # python3
    pass


if "gi" in sys.modules:  # gtk3
    import gi
    gi.require_version('Gtk','3.0')
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


if hasattr(gdk,"BUTTON_PRESS"):  # gtk2
    EventType_BUTTON_PRESS=gdk.BUTTON_PRESS
    pass
else: # gtk3
    EventType_BUTTON_PRESS=gdk.EventType.BUTTON_PRESS
    pass


if hasattr(gtk,"MESSAGE_ERROR"):
    MessageType_ERROR=gtk.MESSAGE_ERROR
    pass
else:
    MessageType_ERROR=gtk.MessageType.ERROR
    pass

if hasattr(gtk,"BUTTONS_OK"):
    ButtonsType_OK=gtk.BUTTONS_OK
    pass
else:
    ButtonsType_OK=gtk.ButtonsType.OK
    pass


try:
    # py2.x
    from urllib import pathname2url
    from urllib import url2pathname
    from urllib import quote as quoteurl
    from urllib import unquote as unquoteurl
    from urlparse import urlparse
    from urlparse import urlunparse
    from urlparse import urljoin    
    pass
except ImportError:
    # py3.x
    from urllib.request import pathname2url
    from urllib.request import url2pathname
    from urllib.parse import quote as quoteurl
    from urllib.parse import unquote as unquoteurl
    from urllib.parse import urlparse
    from urllib.parse import urlunparse
    from urllib.parse import urljoin
    pass


#from .. import canonicalize_path
from ..dc_gtksupp import build_from_file
from ..dc_gtksupp import dc_initialize_widgets
from .. import dc2_misc
from .. import dc_value

__pychecker__="no-import no-argsused"

xpathnamespaces={"dc":"http://thermal.cnde.iastate.edu/datacollect","dcv":"http://limatix.org/dcvalue"}


# TODO : Should add an "abort script" button and status field

def href_exists(href):
    # Check to see if a referenced href exists.
    # Once we support http, etc. this will have to be rewritten

    hrefpath=href.getpath()
    return os.path.exists(hrefpath)


####*** IMPORTANT... SHOULD USE FILENAMENOTIFY ABILITIES TO
#### UPDATE HREF PARAMS (DEFINED RELATIVE TO CHECKLIST.XMLDOC.GETCONTEXTHREF())
#### WHEN FILENAME IS CHANGED. 


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
                     "Plan (.plx) file to run... relative paths OK, but must be relative to THIS file",
                     "Plan (.plx) file to run... relative paths OK, but must be relative to THIS file",
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

    # set of properties to be transmitted as an hrefvalue with the checklist context as contexthref
    __dcvalue_href_properties=frozenset([ "datacollectconfig",
                                          "datacollectconfig2",
                                          "datacollectconfig3",
                                          "dcparamdb",
                                          "planfile",
                                          "gui",
                                          "gui2",
                                          "gui3"])
    
    
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
            self.datacollectconfig=dc_value.hrefvalue("")
            pass

        if self.datacollectconfig2 is None:
            self.datacollectconfig2=dc_value.hrefvalue("")
            pass

        if self.datacollectconfig3 is None:
            self.datacollectconfig3=dc_value.hrefvalue("")
            pass
        
        if self.dcparamdb is None:
            self.dcparamdb=dc_value.hrefvalue("")
            pass

        if self.planfile is None:
            self.planfile=dc_value.hrefvalue("")
            pass

        if self.suffix is None:
            self.suffix=""
            pass

        if self.gui is None:
            self.gui=dc_value.hrefvalue("")
            pass

        if self.gui2 is None:
            self.gui2=dc_value.hrefvalue("")
            pass

        if self.gui3 is None:
            self.gui3=dc_value.hrefvalue("")
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


        if self.planfile.isblank():
            status="No planfile"
            pass
        #elif (self.checklist.xmldoc.filehref is None):
        #    status="Planfile relative to undetermined checklist location"
        else :
            
            #planhref=dc_value.hrefvalue(self.planfile,self.checklist.xmldoc.getcontexthref())
            planhrefcontext=self.planfile.leafless()
            planfilebarefilename=self.planfile.get_bare_unquoted_filename()
            basename=posixpath.splitext(planfilebarefilename)[0]
            
            if self.suffix=="":
                suffix=""
                pass
            else :
                suffix="_%s" % (self.suffix)
                pass
            
            xlghref=dc_value.hrefvalue(quoteurl(basename+suffix+".xlg"),planhrefcontext)
            xlgdir=dc_value.hrefvalue(quoteurl(basename+suffix+"_files/"),planhrefcontext)
            
            
            filledplanhref=dc_value.hrefvalue(quoteurl(basename+suffix+".plf"),xlgdir)
            
            if not href_exists(xlghref) or not href_exists(filledplanhref):
                status="No output files"
                pass
            else :
                # update parsed copy of experiment log if needed
                xlgtime=os.stat(xlghref.getpath()).st_mtime                
                if xlgtime != self.xlgtime:
                    self.xlgtime=xlgtime
                    try: 
                        self.xlgparsed=None
                        self.xlgparsed=etree.parse(xlghref.getpath())
                        pass
                    except:
                        pass
                    pass

                plftime=os.stat(filledplanhref.getpath()).st_mtime
                if plftime != self.plftime:
                    self.plftime=plftime
                    try: 
                        self.plfparsed=None
                        self.plfparsed=etree.parse(filledplanhref.getpath())
                        pass
                    except:
                        pass
                    pass

                if href_exists(xlghref) and not self.checklist.readonly:
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
                        xlghref.xmlrepr(self.checklist.xmldoc,explogel)
                        pass
                    finally:
                        self.checklist.xmldoc.unlock_rw()
                        pass
                        
                    pass

                if os.path.exists(filledplanhref.getpath()) and not self.checklist.readonly:
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
                        filledplanhref.xmlrepr(self.checklist.xmldoc,dcchecklistel)
                        pass
                    finally:
                        self.checklist.xmldoc.unlock_rw()
                        pass
                        
                    pass

                if self.plfparsed is None or self.xlgparsed is None:
                    status="corrupt or changing files"
                    #sys.stderr.write("corrupt or changing files: self.plfparsed=%s; self.xlgparsed=%s\n" % (str(self.plfparsed),str(self.xlgparsed)))
                    pass
                else : 
                    plfchecked=self.plfparsed.xpath('count(/chx:checklist/chx:checkitem[@checked="true"])',namespaces={'chx':'http://limatix.org/checklist'})
                    plftotal=self.plfparsed.xpath('count(/chx:checklist/chx:checkitem)',namespaces={'chx':'http://limatix.org/checklist'})

                    xlgmeas=self.xlgparsed.xpath('count(/dc:experiment/dc:measurement)',namespaces={'dc':'http://limatix.org/datacollect'})
                    
                    status="%d/%d steps; %d meas." % (plfchecked,plftotal,xlgmeas)
                    pass
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
            hrefval=dc_value.hrefvalue(value,contexthref=self.checklist.xmldoc.getcontexthref())
            self.datacollectconfig=hrefval
            pass
        elif property.name=="datacollectconfig2":
            hrefval=dc_value.hrefvalue(value,contexthref=self.checklist.xmldoc.getcontexthref())
            self.datacollectconfig2=hrefval
            pass
        elif property.name=="datacollectconfig3":
            hrefval=dc_value.hrefvalue(value,contexthref=self.checklist.xmldoc.getcontexthref())
            self.datacollectconfig3=hrefval
            pass
        elif property.name=="dcparamdb":
            hrefval=dc_value.hrefvalue(value,contexthref=self.checklist.xmldoc.getcontexthref())
            self.dcparamdb=hrefval
            pass
        elif property.name=="planfile":
            hrefval=dc_value.hrefvalue(value,contexthref=self.checklist.xmldoc.getcontexthref())
            self.planfile=hrefval
            pass
        elif property.name=="suffix":
            self.suffix=value
            pass
        elif property.name=="gui":
            hrefval=dc_value.hrefvalue(value,contexthref=self.checklist.xmldoc.getcontexthref())
            self.gui=hrefval
            pass
        elif property.name=="gui2":
            hrefval=dc_value.hrefvalue(value,contexthref=self.checklist.xmldoc.getcontexthref())
            self.gui2=hrefval
            pass
        elif property.name=="gui3":
            hrefval=dc_value.hrefvalue(value,contexthref=self.checklist.xmldoc.getcontexthref())
            self.gui3=hrefval
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
            return self.myprops[property.name].attempt_relative_url(self.checklist.xmldoc.getcontexthref())
        elif property.name=="datacollectconfig2":
            return self.myprops[property.name].attempt_relative_url(self.checklist.xmldoc.getcontexthref())
        elif property.name=="datacollectconfig3":
            return self.myprops[property.name].attempt_relative_url(self.checklist.xmldoc.getcontexthref())
        elif property.name=="dcparamdb":
            return self.myprops[property.name].attempt_relative_url(self.checklist.xmldoc.getcontexthref())
        elif property.name=="planfile":
            return self.myprops[property.name].attempt_relative_url(self.checklist.xmldoc.getcontexthref())
        elif property.name=="suffix":
            return self.suffix
        elif property.name=="gui":
            return self.myprops[property.name].attempt_relative_url(self.checklist.xmldoc.getcontexthref())
        elif property.name=="gui2":
            return self.myprops[property.name].attempt_relative_url(self.checklist.xmldoc.getcontexthref())
        elif property.name=="gui3":
            return self.myprops[property.name].attempt_relative_url(self.checklist.xmldoc.getcontexthref())
        elif property.name=="multispecimen":
            return self.multispecimen
        else :
            raise ValueError("Unknown property %s" % (property.name))
        pass


    def dc_gui_init(self,guistate):
        # need next line if subclassing a dc_gui class
        # super(dg_readout).__dc_gui_init(self,io)
        
        
        self.paramdb=guistate.paramdb

        dc_initialize_widgets(self.gladeobjdict,guistate)

        pass
    

    def determine_command(self):



        commandlist=[]
        mkdir=None
        cpsrc=None
        cpdest=None
        cpparent=None

        if self.checklist.xmldoc.filehref is None or self.planfile.isblank():

            #if len(self.planfile)==0 or (not os.path.isabs(self.planfile) and self.checklist.xmldoc.filename is None):
            return (None,None,None,None,['datacollect2'],'datacollect2')

        planfile=self.planfile
        # sys.stderr.write("self.planfile=%s\n" % (self.planfile))

        basename=posixpath.splitext(planfile.get_bare_unquoted_filename())[0]
        basefilename=os.path.split(basename)[1]
        basecontext=planfile.leafless()
        
        if self.suffix=="":
            suffix=""
            pass
        else :
            suffix="_%s" % (self.suffix)
            pass
        xlgfilename=basename+suffix+".xlg"
        xlgdirname=basename+suffix+"_files/"
        filledplanname=basename+suffix+".plf"

        xlgfilehref=dc_value.hrefvalue(quoteurl(xlgfilename),contexthref=basecontext)
        xlgdirhref=dc_value.hrefvalue(quoteurl(xlgdirname),contexthref=basecontext)
        filledplanhref=dc_value.hrefvalue(quoteurl(filledplanname),contexthref=xlgdirhref)
        
        
        # sys.stderr.write("xlgdir=%s\n" % (xlgdir))
        # sys.stderr.write("xlgfile=%s\n" % (xlgfile))

        
        if not href_exists(xlgdirhref):
            mkdir=xlgdirhref.getpath()
            pass
        
        
        if not href_exists(filledplanhref):
            cpparent=self.checklist.xmldoc.filehref # canonicalize_path.relative_path_to(".",self.checklist.xmldoc.filename)
            cpsrc=planfile # canonicalize_path.relative_path_to(".",planfile)
            cpdest=filledplanhref #canonicalize_path.relative_path_to(".",filledplan)
            pass
        

        commandlist.append('datacollect2')

        if self.multispecimen:
            commandlist.append('-m')
            pass
        else:
            commandlist.append('-s')
            pass

        if not self.dcparamdb.isblank():
            commandlist.append('-d')
            commandlist.append(self.dcparamdb.getpath())
            pass

        if not self.datacollectconfig.isblank():
            commandlist.append('-f')
            commandlist.append(self.datacollectconfig.getpath())
            pass 

        if not self.datacollectconfig2.isblank():
            commandlist.append('-f')
            commandlist.append(self.datacollectconfig2.getpath())
            pass 

        if not self.datacollectconfig3.isblank():
            commandlist.append('-f')
            commandlist.append(self.datacollectconfig3.getpath())
            pass 

        if not href_exists(xlgfilehref):
            commandlist.append('-n')
            pass
            
        commandlist.append(xlgfilehref.getpath())

        commandlist.append('--parent')
        #xlgfilecontextdir=os.path.split(xlgfile)[0]
        commandlist.append(self.checklist.xmldoc.filehref.attempt_relative_url(xlgfilehref.leafless()))  #canonicalize_path.relative_path_to(xlgfilecontextdir,self.checklist.xmldoc.filename))
        
        commandlist.append('-p')
        commandlist.append(filledplanhref.getpath())

        if not self.gui.isblank():
            commandlist.append('-g')
            commandlist.append(self.gui.getpath())
            pass

        if not self.gui2.isblank():
            commandlist.append('-g')
            commandlist.append(self.gui2.getpath())
            pass

        if not self.gui3.isblank():
            commandlist.append('-g')
            commandlist.append(self.gui3.getpath())
            pass


        # create full shell-compatible command
        fullcmd=""
        if mkdir is not None:
            fullcmd+="mkdir %s ; " % (quoteshell(mkdir))
            pass

        if cpsrc is not None:
            fullcmd+="dc_chx2chf %s %s %s ; " % (quoteshell(cpparent.getpath()),quoteshell(cpsrc.getpath()),quoteshell(cpdest.getpath()))
            pass

        fullcmd+=" ".join([quoteshell(term) for term in commandlist])

        return (mkdir,cpparent,cpsrc,cpdest,commandlist,fullcmd)

    def button_tooltip(self,item,x,y, keyboard_mode, tooltip):
        fullcmd=self.determine_command()[5]
        tooltip.set_text(fullcmd+"\n(Press right mouse button to copy to clipboard)")
        return True

    def button_mousepress(self,obj,event):
        # sys.stderr.write("event.type=0x%x event.button=0x%x\n" % (event.type,event.button))

        if event.type==EventType_BUTTON_PRESS and event.button==3:
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
        if self.checklist.xmldoc.filehref is None:
            nofiledialog=gtk.MessageDialog(type=MessageType_ERROR,buttons=ButtonsType_OK)
            nofiledialog.set_markup("Error: This checklist needs a filename before a subchecklist can be opened. Please check a box or use the \"Save\" button to give it a filename (if applicable).")
            nofiledialog.run()
            nofiledialog.destroy()
            return

        (mkdir,cpparent,cpsrc,cpdest,commandlist,fullcmd)=self.determine_command()

        if mkdir is not None:
            os.mkdir(mkdir)
            pass
        
        #if cpsrc is not None:
        #    shutil.copyfile(cpsrc,cpdest)
        #    pass
        if cpparent is not None:
            dc2_misc.chx2chf(cpparent,cpsrc,cpdest)
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
