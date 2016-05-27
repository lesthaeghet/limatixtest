

import os
import sys
import copy
#import fcntl
import pty
import threading
import subprocess

from .. import viewautoexp
from .. import dc_value

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # python 3.x


if "gi" in sys.modules:  # gtk3
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk as gtk
    from gi.repository import Gdk as gdk
    from gi.repository import GObject as gobject
    pass
else : 
    # gtk2
    import gtk
    import gtk.gdk as gdk
    import gobject
    pass

from buttontextareastep import buttontextareastep

__pychecker__="no-import no-argsused"



# TODO : Should add an "abort script" button and status field

controlcharfilter={
    # this maps control characters which are not permitted in XML to None
    0x00: None,
    0x01: None,
    0x02: None,
    0x03: None,
    0x04: None,
    0x05: None,
    0x06: None,
    0x07: None,
    0x08: None,
    # 0x9 (tab) is permitted
    # 0xA (linefeed) is permitted
    0x0B: None,
    0x0C: None,
    # 0xD (carriage return) is permitted
    0x0E: None,
    0x0F: None,
    0x10: None,
    0x11: None,
    0x12: None,
    0x13: None,
    0x14: None,
    0x15: None,
    0x16: None,
    0x17: None,
    0x18: None,
    0x19: None,
    0x1A: None,
    0x1B: None,
    0x1C: None,
    0x1D: None,
    0x1E: None,
    0x1F: None,
    }

# Control char filtering according to XML 1.0 spec, section 2.2 (Characters),
# definition of Character Range. 
# n.b. We could (should?) also enforce the other missing segments: 
# 0xD800-0xDFFF and 0xFFFE-0xFFFF
def filter_controlchars(line):
    line=unicode(line)
    return line.translate(controlcharfilter)
    


# gtk superclass should be first of multiple inheritances
class runscriptstep(buttontextareastep):
    __gtype_name__="runscriptstep"
    __gproperties__ = {       
        "scriptlog": (gobject.TYPE_STRING,
                       "parameter to store script output log",
                       "parameter to store script output log",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags
        "buttonlabel": (gobject.TYPE_STRING,
                       "Text for the button label",
                       "Text for the button label",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags
        "command": (gobject.TYPE_STRING,
                       "command to run",
                       "command should have a \"%(id)s\" where the id should be substituted and a %(basename)s where the base of the output file name should be substituted note: current directoy will be the destination location and files should be output there.",
                     "", # default value 
                     gobject.PARAM_READWRITE), # flags
        "viewautoexp": (gobject.TYPE_BOOLEAN,
                        "Should there be a button to view the autoexp/automeas tags?",
                        "Enable button to view autoexp/automeas",
                        False, # default value 
                        gobject.PARAM_READWRITE), # flags

        # Also inherits "buttonlabel" property
        }
    checklist=None
    buttonlabel=None
    xmlpath=None
    scriptlog=None
    command=None
    readonlydialogrunning=None
    queue=None  # Queue for lines coming in from subprocess
    subprocess_pobj=None # valid only in STATE_RUNNING

    environstr=None  # not assigned in this class... defined so that subclasses (i.e. runmatlabscriptstep) can insert extra command text
    environadd=None  # not assigned in this class... a mapping that will update the current environment when command is run

    viewautoexp=None
    viewautoexpbutton=None

    state=None  # should be STATE_IDLE, STATE_RUNNING, or STATE_DONE

    STATE_IDLE=0  # ready to run
    STATE_RUNNING=1 # subprocess is running
    STATE_DONE=2    # subprocess has run; ready for reset

    # self.paramdb  defined by buttontextareastep, set by buttontextareastep's dc_gui_init()

                      
    def __init__(self,checklist,step,xmlpath):
        buttontextareastep.__init__(self,checklist,step,xmlpath)
        # paramhandler.__init__(self,super(adjustparamstep,self),self.__proplist)# .__gproperties__)
        # gobject.GObject.__init__(self)

        self.checklist=checklist
        self.xmlpath=xmlpath
        self.readonlydialogrunning=False
        if self.scriptlog is None:
            self.scriptlog=""
            pass
        if self.command is None:
            self.command=""
            pass

        if self.buttonlabel is None:
            self.buttonlabel=""
            pass

        if self.viewautoexp is None:
            self.viewautoexp=False
            pass

        if self.environstr is None:
            self.environstr=""
            pass

        if self.environadd is None:
            self.environadd={}
            pass

        self.queue=Queue()
        self.state=self.STATE_IDLE
        
        # We implement custom tooltips on the push button to indicate
        # status. 
        self.gladeobjdict["pushbutton"].set_has_tooltip(True)
        self.gladeobjdict["pushbutton"].connect("query-tooltip",self.button_tooltip)

        # connect button-press-event so we can implement copy of the tooltip data to the clipboard
        self.gladeobjdict["pushbutton"].connect("button-press-event",self.button_mousepress)
        
        if self.viewautoexp: 
            self.addviewautoexpbutton()
            pass

        pass


    def dc_gui_init(self,guistate):

        self.set_fixed()  # set to fixed value if we are readonly if appropriate

        # call superclass (buttontextareastep) dc_gui_init
        super(runscriptstep,self).dc_gui_init(guistate)

        
        pass
    


    def is_fixed(self):
        # param readout is fixed when checklist is marked as
        # readonly or when checkbox is checked.
        if self.state==self.STATE_RUNNING and self.checklist.readonly and not(self.readonlydialogrunning):
            # warn user that script is running but checklist marked readonly!
            if hasattr(gtk,"MessageType") and hasattr(gtk.MessageType,"WARNING"):
                # gtk3
                Dialog=gtk.MessageDialog(type=gtk.MessageType.ERROR,buttons=gtk.ButtonsType.OK)
                pass
            else : 
                Dialog=gtk.MessageDialog(type=gtk.MESSAGE_ERROR,buttons=gtk.BUTTONS_OK)
                pass
            
            Dialog.set_markup("Error: runscriptstep: Checklist marked read-only while script still running!. Please wait for script to complete and then click 'OK'")
            self.readonlydialogrunning=True
            Dialog.run()
            Dialog.destroy()
            self.readonlydialogrunning=False
                        
            pass
        
        return (self.checklist.readonly or self.step.gladeobjdict["checkbutton"].get_property("active")) and self.state != self.STATE_RUNNING
    

    def value_from_xml(self):
        value=dc_value.stringvalue("")
        self.checklist.xmldoc.lock_ro()
        try: 
            xmltag=self.checklist.xmldoc.restorepath(self.xmlpath)
            
            scriptoutputparamnodes=self.checklist.xmldoc.xpathcontext(xmltag,"chx:parameter[@name='scriptlog']")
            if len(scriptoutputparamnodes) >= 1:
                scriptoutputparamnode=scriptoutputparamnodes[0]
                value=dc_value.stringvalue.fromxml(self.checklist.xmldoc,scriptoutputparamnode)
                gotdisplayfmt=dc_value.xmlextractdisplayfmt(self.checklist.xmldoc,scriptoutputparamnode)

                pass
            pass
        finally:
            self.checklist.xmldoc.unlock_ro()
            pass
        
        
        return (value,gotdisplayfmt)
    
    def set_fixed(self):
        fixed=self.is_fixed()
        (value,displayfmt)=self.value_from_xml()
        self.gladeobjdict["textarea"].set_fixed(fixed,value,displayfmt)
        pass
    
    def handle_check(self,checked):
        # automagically called by steptemplate when checkbox is checked or unchecked
        self.set_fixed()
        pass

    
    def set_readonly(self,readonly):
        # automagically called by step when checklist readonly state
        # changes.
        self.set_fixed()
        pass
        
        
    def addviewautoexpbutton(self):
        if self.viewautoexpbutton is None:
            self.viewautoexpbutton=gtk.Button("View result table")
            self.viewautoexpbutton.connect("clicked",self.viewresulttablecallback)
            self.gladeobjdict["ButtonBox"].pack_start(self.viewautoexpbutton,False,True,0)
            pass
        pass

    def viewresulttablecallback(self,*args):
        self.checklist.xmldoc.lock_rw()
        try : 
            viewtablewin=viewautoexp.viewautoexp(self.checklist.xmldoc,self.xmlpath)
            pass
        except:
            raise
        finally:
            self.checklist.xmldoc.unlock_rw()
            pass

        viewtablewin.show_all()
        pass

    def do_set_property(self,property,value):
        if property.name=="scriptlog":
            self.scriptlog=value
            self.set_property("readoutparam",value)
            pass
        elif property.name=="command":
            # command should have a "%(id)s" where the id should be substituted 
            # and a %(basename)s where the base of the output file name should
            # be substituted
            # note: current directoy will be the destination location and files
            # should be output there. 
            self.command=value
            pass
        elif property.name=="buttonlabel":
            self.buttonlabel=value
            if self.state==self.STATE_IDLE:
                self.gladeobjdict["pushbutton"].set_label(self.buttonlabel)
                pass
            pass
        elif property.name=="viewautoexp":
            self.viewautoexp=value
            if self.viewautoexp:
                self.addviewautoexpbutton()
                pass
            pass
        else :
            return buttontextareastep.do_set_property(self,property,value)
        pass
    
    def do_get_property(self,property,value):
        if property.name=="scriptlog":
            return self.scriptlog
        elif property.name=="command":
            return self.command
        elif property.name=="buttonlabel":
            return self.buttonlabel
        elif property.name=="viewautoexp":
            return self.viewautoexp
        else :
            return buttontextareastep.do_get_property(self,property,value)
        pass
        
    def determine_command(self):
        if self.checklist is None or self.checklist.chklistfile is None:
            #  This condition is diagnosed also when you click on the button (see nofilenamedialog)
            return ""
        
        return self.command % { "id": str(id(self)),"basename":os.path.splitext(self.checklist.chklistfile)[0]}

    def button_tooltip(self,item,x,y, keyboard_mode, tooltip):
        if self.state==self.STATE_IDLE or self.state==self.STATE_DONE:
            tooltip.set_text(self.environstr+self.determine_command()+"\n(Press right mouse button to copy to clipboard)")
            pass
        elif self.state==self.STATE_RUNNING:
            tooltip.set_text("pid=%s\n(Press right mouse button to copy to clipboard)" % (str(self.subprocess_pobj.pid)))
            pass
        return True

    def button_mousepress(self,obj,event):
        # sys.stderr.write("event.type=0x%x event.button=0x%x\n" % (event.type,event.button))

        if event.type==gdk.BUTTON_PRESS and event.button==3:
            clipstring=""
            if self.state==self.STATE_IDLE or self.state==self.STATE_DONE:
                clipstring="cd '%s' ; " % (unicode(self.paramdb["dest"].dcvalue)) + self.environstr + self.environstr + self.determine_command()
                pass
            elif self.state==self.STATE_RUNNING:
                clipstring=str(self.subprocess_pobj.pid)
                pass
            

            clipboard=gtk.Clipboard(gdk.display_get_default(),"PRIMARY")
            clipboard.set_text(clipstring,-1)
            clipboard.store()
            clipboard=gtk.Clipboard(gdk.display_get_default(),"CLIPBOARD")
            clipboard.set_text(clipstring,-1)
            clipboard.store()
            return True # eat event
        
        return False

    def buttoncallback(self,*args):
        if self.state==self.STATE_IDLE:

            # Check consistency 
            inconsistentlist=[]
            if not self.checklist.isconsistent(inconsistentlist):
                
                consistdialog=gtk.MessageDialog(type=gtk.MESSAGE_ERROR,buttons=gtk.BUTTONS_OK)
                consistdialog.set_markup("Error: Not all parameter entries in a consistent state.\nWill not run script.\nInconsistent params: %s" % (str(inconsistentlist)))
                consistdialog.run()
                consistdialog.destroy()

                return True

            if self.checklist is None or self.checklist.chklistfile is None:

                nofilenamedialog=gtk.MessageDialog(type=gtk.MESSAGE_ERROR,buttons=gtk.BUTTONS_OK)
                nofilenamedialog.set_markup("Error: Cannot run script until checklist filename has been determined (try completing previous checklist entries).")
                nofilenamedialog.run()
                nofilenamedialog.destroy()
                return True

            # fork off process; fork off reader thread that uses gobject.timeout_add() to pass data back every few seconds. Then triggers scriptcompletecallback when done. 
            # command should have a "%(id)s" where the id should be substituted 
            # and a %(basename)s where the base of the output file name should
            # be substituted
            # note: current directoy will be the destination location and files
            # should be output there. 
            # sys.stderr.write("Got buttoncallback... forking suprocess and starting thread\n");
            self.state=self.STATE_RUNNING

            # open pseudo-tty so that subprocess thinks it's interactive and doesn't buffer stdout
            (master,slave)=pty.openpty()
            
            # sys.stderr.write("command=%s\n" % (self.determine_command()))

            if unicode(self.paramdb["dest"].dcvalue)=="":
                self.state=self.STATE_DONE
                raise ValueError("runscriptstep: dest param is not permitted to be blank (open an experiment log first!)")
            
            newenviron=copy.deepcopy(os.environ)
            newenviron.update(self.environadd)

            try : 
                self.subprocess_pobj=subprocess.Popen(self.determine_command(),stdout=slave,stderr=subprocess.STDOUT,cwd=unicode(self.paramdb["dest"].dcvalue),shell=True,close_fds=True,env=newenviron)
                pass
            except : 
                
                exc_type,exc_value,tb = sys.exc_info()
                sys.stderr.write("child_traceback=%s\n" % (str(exc_value.child_traceback)))
                self.state=self.STATE_DONE
                raise
            os.close(slave)

            # threading.Thread(target=self.readsubprocess,args=(self.subprocess_pobj.stdout,)).start()
            threading.Thread(target=self.readsubprocess,args=(os.fdopen(master,'r'),)).start()
            # add timeout routine to pull data from queue
            gobject.timeout_add(250,self.readqueue)

            # set button to "Abort"
            self.gladeobjdict["pushbutton"].set_label("Abort")
            
            pass
        elif self.state==self.STATE_RUNNING:
            # perform abort
            self.subprocess_pobj.kill()  # scriptcompletecallback will adjust state
            pass

        elif self.state==self.STATE_DONE:
            # perform reset
            self.do_reset()


            pass
        
        return True

    def readqueue(self):
        
        try: 
            while True:
                line=filter_controlchars(self.queue.get_nowait())
                self.gladeobjdict["textarea"].pp_programmaticallyappend_noactivate(line)
                
                pass
            pass
        except Empty:
            pass
        
        if self.subprocess_pobj is None:
            return False
        else :
            return True
        pass
    
    
    def readsubprocess(self,pipe):
        # sys.stderr.write("readsubprocess thread starting...\n")
        try :
            for line in iter(pipe.readline,''):
                # sys.stderr.write("Got line: %s\n" % (line))
                self.queue.put(line)
                pass
            pass
        except IOError:
            # Child must be dead
            pass
        pipe.close()

        gobject.timeout_add(0,self.scriptcompletecallback,self.subprocess_pobj)
        pass

    def scriptcompletecallback(self,subprocess_pobj):

        self.readqueue()

        if self.subprocess_pobj is subprocess_pobj and subprocess_pobj is not None: # only if something else hasn't done cleanup

            # wait for subprocess to finish
            retcode=self.subprocess_pobj.wait()

            self.subprocess_pobj=None
            
            # Set the button label to "reset"
            self.gladeobjdict["pushbutton"].set_label("Reset")
        
            # Finalize the text input if there is no error. This will pass it off to the param handler.
            if retcode==0:
                # call scriptresultassignedcallback once result is assigned
                self.gladeobjdict["textarea"].pp_activate(self.scriptresultassignedcallback)
                pass
            else:
                self.state=self.STATE_DONE
                pass
            
            pass        
        
        return False

    def scriptresultassignedcallback(self,paragraphparam,result):

        if result is not None and not(self.is_fixed()):
            # assign result into xml

            self.checklist.xmldoc.lock_rw()
            try: 
                xmltag=self.checklist.xmldoc.restorepath(self.xmlpath)

                scriptoutputparamnodes=self.checklist.xmldoc.xpathcontext(xmltag,"chx:parameter[@name='scriptoutput']")
                if len(scriptoutputparamnodes) < 1:
                    # need to add a node
                    scriptoutputparamnode=self.checklist.xmldoc.addelement(xmltag,"chx:parameter")
                    self.checklist.xmldoc.setattr("name","scriptlog")
                    self.checklist.xmldoc.setattr("type","str")
                    pass
                else:
                    scriptoutputparamnode=scriptoutputparamnodes[0]
                    pass
                #dc_value.xmlstoredisplayfmt(self.checklist.xmldoc,scriptoutputparamnode,)
                
                self.checklist.xmldoc.settext(scriptoutputparamnode,result.value())
                
                pass
            finally:
                self.checklist.xmldoc.unlock_rw()
                pass
            

            pass
        self.state=self.STATE_DONE
        
        
        pass
    
    def do_reset(self):
        if self.state == self.STATE_RUNNING or self.subprocess_pobj is not None:
            self.subprocess_pobj.kill()
            self.subprocess_pobj.wait()
            self.subprocess_pobj=None
            pass
        
        self.readqueue()

        # clear out any dc:autoexp tags that have been added 
        self.checklist.xmldoc.lock_rw()
        try : 
            xmltag=self.checklist.xmldoc.restorepath(self.xmlpath)
            autoexps=self.checklist.xmldoc.xpathcontext(xmltag,'dc:autoexp')
            for autoexp in autoexps:
                autoexp.getparent().remove(autoexp)
                pass
            pass
        except: 
            raise
        finally: 
            self.checklist.xmldoc.unlock_rw()
            pass
            
        # Clear the script output
        self.paramdb[self.scriptlog].requestvalstr_sync("")
        self.gladeobjdict["textarea"].pp_abort()

        # Set the label on the button 
        self.gladeobjdict["pushbutton"].set_label(self.buttonlabel)

        self.state=self.STATE_IDLE
        
        pass

    def resetchecklist(self):
        buttontextareastep.resetchecklist(self)
        self.do_reset()
        pass


    pass


gobject.type_register(runscriptstep)  # required since we are defining new properties/signals
