# TODO: 
#  make <description>an alias for <parameter type="str" name="description">
#  make class="text" an assumed attribute for <checkitem>
#  Allow checkitem title to be placed as text within the tag. 
#  Read in <checklistname> and <checklisttitle> tags 

#import Ft.Xml.Domlette as Dom
import xml.sax.saxutils

from lxml import etree

import sys
import os
import os.path
import posixpath
import string
import numbers
import math
import copy
import traceback
import urllib
import pkg_resources

try:
    # py2.x
    from urllib import pathname2url
    from urllib import url2pathname
    from urllib import quote
    pass
except ImportError:
    # py3.x
    from urllib.request import pathname2url
    from urllib.request import url2pathname
    from urllib.parse import quote
    pass


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

if hasattr(gtk,"ResponseType") and hasattr(gtk.ResponseType,"OK"):
    # gtk3
    RESPONSE_OK=gtk.ResponseType.OK
    RESPONSE_CANCEL=gtk.ResponseType.CANCEL
    RESPONSE_NO=gtk.ResponseType.NO
    RESPONSE_YES=gtk.ResponseType.YES
else :
    RESPONSE_OK=gtk.RESPONSE_OK
    RESPONSE_CANCEL=gtk.RESPONSE_CANCEL
    RESPONSE_NO=gtk.RESPONSE_NO
    RESPONSE_YES=gtk.RESPONSE_YES
    pass


# import pygram


from . import xmldoc
from . import canonicalize_path
from . import checklistdb
from . import dc2_misc


import dg_timestamp

from .dc_gtksupp import build_from_file
from .dc_gtksupp import dc_initialize_widgets
from .dc_gtksupp import guistate as create_guistate

from .steptemplate import steptemplate
from . import paramdb2 as pdb
from .dc_value import numericunitsvalue as numericunitsv
from .dc_value import stringvalue as stringv
from .dc_value import hrefvalue as hrefv
from .dc_value import accumulatingintegersetvalue as accumulatingintegersetv
from .dc_value import accumulatingdatesetvalue as accumulatingdatesetv
from .dc_value import datesetvalue as datesetv
from .dc_value import integersetvalue as integersetv
from .dc_value import integervalue as integerv

try: 
    import builtins  # python3
    pass
except ImportError: 
    import __builtin__ as builtins # python2
    pass

if not hasattr(builtins,"basestring"):
    basestring=str  # python3
    pass


class dummy(object):
    pass
thisdir=os.path.split(sys.modules[dummy.__module__].__file__)[0]


# sys.path.append('steps/')

from .widgets.dc_wraplabel import dc_wraplabel



if hasattr(gtk,"StateType") and hasattr(gtk.StateType,"NORMAL"):
    # gtk3
    STATE_NORMAL=gtk.StateType.NORMAL
    pass
else:
    STATE_NORMAL=gtk.STATE_NORMAL
    pass

if hasattr(gtk,"ResponseType") and hasattr(gtk.ResponseType,"OK"):
    # gtk3
    RESPONSE_OK=gtk.ResponseType.OK
    RESPONSE_CANCEL=gtk.ResponseType.CANCEL
else :
    RESPONSE_OK=gtk.RESPONSE_OK
    RESPONSE_CANCEL=gtk.RESPONSE_CANCEL
    pass
    


__pychecker__="no-argsused"


class checkitem(object):
    title=None
    cls=None
    params=None
    xmlpath=None  # xmldoc savedpath

    def __init__(self,title=None,cls=None,params=None,xmlpath=None):
        self.title=title
        self.cls=cls
        self.params=params
        
        self.xmlpath=xmlpath
        pass
    pass



def escapestring(s):
    # convert a string to unicode and return a quoted escaped 
    # representation
    
    # use the unicode __repr__ to give us such 
    # a representation 
    # print "escapestring=%s" % (s)
    if hasattr(builtins,"unicode"):
        return repr(unicode(s)) # python2
        pass
    else:
        return repr(str(s)) # python3
        pass
    pass

xml2pangoxslt=r"""<?xml version="1.0"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0" xmlns:exsl="http://exslt.org/common" extension-element-prefixes="exsl" xmlns:chx="http://thermal.cnde.iastate.edu/checklist" xmlns:html="http://www.w3.org/1999/xhtml">
<xsl:output method="xml" encoding="utf-8"/>

<!-- normalize spaces in text nodes -->
<xsl:template match="text()" priority="0.25">
  <xsl:if test="position()!=1 and starts-with(string(.),' ')">
    <xsl:text> </xsl:text>
  </xsl:if>
  <xsl:value-of select="normalize-space(.)"/>
  <xsl:if test="position() != last() and substring(.,string-length(.))=' '"> <!-- substring(.,string-length(.))=' ' is xpath 1.0 equivalent for ends-with(string(.),' ') -->
    <xsl:text> </xsl:text>
  </xsl:if>
</xsl:template>

<!-- convert <parameter>, <description>, and <rationale> tags into <markup> tags for pango -->
<xsl:template match="chx:parameter|chx:description|chx:rationale">
  <markup>
    <xsl:apply-templates select="@*|node()"/>
  </markup>
</xsl:template>

<!-- convert <br/> tags into line breaks -->
<xsl:template match="chx:br|br|html:br">
  <xsl:text>&#x0a;</xsl:text>
</xsl:template>

<!-- copy everything else, converting into the null namespace -->
<xsl:template match="@*|node()">
  <xsl:copy>
    <xsl:apply-templates select="@*|node()"/>
  </xsl:copy>
</xsl:template>

<xsl:template match="*">
  <xsl:element name="{local-name()}">
    <xsl:apply-templates select="@*|node()"/>
  </xsl:element>
</xsl:template>


</xsl:stylesheet>
"""


xml2pango=etree.XSLT(etree.XML(xml2pangoxslt))


def ErrorDialog(msg,exctype,excvalue,tback):
    if hasattr(gtk,"MessageType") and hasattr(gtk.MessageType,"WARNING"):
        # gtk3
        Dialog=gtk.MessageDialog(type=gtk.MessageType.ERROR,buttons=gtk.ButtonsType.NONE)
        pass
    else : 
        Dialog=gtk.MessageDialog(type=gtk.MESSAGE_ERROR,buttons=gtk.BUTTONS_NONE)
        pass
    Dialog.add_buttons("Debug",1,"OK",0)
        
    # sys.stderr.write("Markup is Error: %s.\n%s: %s\n\nTraceback:\n%s" % (msg,str(exctype),xml.sax.saxutils.escape(unicode(excvalue)),xml.sax.saxutils.escape(tback)))
    Dialog.set_markup("Error: %s.\n%s: %s\n\nTraceback:\n%s" % (msg,xml.sax.saxutils.escape(exctype.__name__),xml.sax.saxutils.escape(str(excvalue)),xml.sax.saxutils.escape(tback)))
    result=Dialog.run()
    Dialog.destroy()
    
    if result==1:
        # run debugger
        import pdb as pythondb
        print("exception: %s: %s" % (exctype.__name__,str(excvalue)))
        sys.stderr.write(tback)

        pythondb.post_mortem()
        pass
    
    
    pass

def href_exists(href):
    # Check to see if a referenced href exists.
    # Once we support http, etc. this will have to be rewritten

    hrefpath=href.getpath()
    return os.path.exists(hrefpath)


syncedparam = lambda param: xmldoc.synced(param)


def get_step(name):
    matches=[]
    for entrypoint in pkg_resources.iter_entry_points("datacollect2.step"):
        if entrypoint.name==name:
            matches.append(entrypoint)
            pass
        pass
    if len(matches) == 0:
        raise ValueError("Step %s not provided by any installed Python module or package.\nStep must be configured using setuptools with entry_points={\"datacollect2.step\": \"%s = <importable Python module>\"" % (name,name))
    
    elif len(matches) > 1:
        sys.stderr.write("datacollect2 checklist: step %s is provided by multiple modules (%s). Using %s\n" % (name,str([entrypoint.module_name for entrypoint in matches]),matches[0].module_name))
        pass
    
    stepmodule=matches[0].load()
    stepclass=getattr(stepmodule,name)
    
    return stepclass


class checklist(object):

    closed=None # Set to True once this checklist is closed and should be considered invalid
    gladeobjdict=None
    gladebuilder=None
    parsedchecklist=None
    iohandlers=None
    steps=None
    xmldoc=None
    orighref=None
    desthref=None  # if not None, href to put filled checklist in (otherwise use dest)
    paramdb=None
    paramdb_ext=None # dc:param() extension function
    chklistfile=None # in datacollect mode, once the filename has been determined and we are auto-saving, chklistfile is the name of the file we are saving as

    datacollectmode=None
    
    datacollect_explog=None  # in datacollect mode we always autosave after 
                           # the first box is checked, unless a later box
                           # is referenced (by title) in dest/@autofilename

    datacollect_explogwin=None  

    private_paramdb=None # private paramdb is used for entries that should
                         # not be shared... checklist name, dest,
                         # perhaps notes.
                         # In datacollect mode, private_paramdb["measnum"]  is the set of measnums assigned by datacollect to this instance of this checklist for checklists that have done_is_save_measurement or part_of_a_measurement. We will need pull in a new value when the first box is checked

    done_is_save_measurement=None # flag, in datacollect mode, to transform the "Save"/"Done" button into a button that saves the measurement to the xml file. Also triggers storing checklist file name in "measchecklist" param. Also makes the notes field at the bottom shared between the checklist and the experiment log
    has_save_measurement_step=None # Flag, in datacollect mode, that indicates that the checklist has a save measurement step. It triggers storing checklist file name in "measchecklist" param. Also makes the notes field at the bottom shared between the checklist and the experiment log
    part_of_a_measurement=None # Flag, in datacollect mode that indicates that a checklist is part of a measurement and therefore when saved should be saved using the measnum
    readonly=None   # Checklist is read only out (after done is pressed, before reset)
    pre_reset_href=None # last real href from before a reset
    
    shared_notes=None # flag to indicate whether the notes field is shared or not. Automatically set with done_is_save_measurement
    specimen_disabled=None  # if True, then we don't show a specimen widget and we don't sync the specimen field

    # adddoc/remdoc params. Whether these members are None is used as a flag for whether remdoc() needs to be called.
    notes_sync=None
    #dest_sync=None
    date_sync=None
    perfby_sync=None
    specimen_sync=None
    measnum_sync=None

    savebuttonnormalcolor=None # GdkColor
    savebuttonreadycolor=None  # GdkColor

    filenamenotify=None # list of (function to call when the checklist gets a name...,*args,**kwargs)  used for example by runcheckliststep. Called as filenamenotify[idx][0](checklist,orighref,dest,fname,*filenamenotify[idx][1],**filenamenotify[idx][2])
    donenotify=None
    resetnotify=None
    closenotify=None

    
    def __init__(self,orighref,paramdb,datacollect_explog=None,datacollect_explogwin=None,desthref=None):


        self.closed=False
        self.paramdb=paramdb
        self.desthref=desthref
        self.private_paramdb=pdb.paramdb(None) # could pass dgio as parameter to allow private parameters to interact with dataguzzler
        #self.private_paramdb.addparam("notes",stringv,build=lambda param: xmldoc.synced(param))
        # use syncedparambuilder (above) because of incompatibility of lambda with exec statement below in python 2.6
        self.private_paramdb.addparam("notes",stringv,build=syncedparam)

        self.private_paramdb.addparam("defaultfilename",stringv)  # defaultfilename maps to the filename entry field at the bottom of the checklist window

        self.paramdb_ext=pdb.etree_paramdb_ext(paramdb)
        self.steps=[]
        self.datacollect_explog=datacollect_explog
        if self.datacollect_explog is None:
            self.datacollectmode=False
            pass
        else :
            self.datacollectmode=True
            pass

        self.datacollect_explogwin=datacollect_explogwin
        
        self.done_is_save_measurement=False
        self.has_save_measurement_step=False
        self.part_of_a_measurement=False
        self.shared_notes=False
        self.filenamenotify=[]
        self.donenotify=[]
        self.resetnotify=[]
        self.closenotify=[]
        

        
        (self.gladeobjdict,self.gladebuilder)=build_from_file(os.path.join(thisdir,"checklist.glade"))


        if "gi" in sys.modules: # gtk3
            #print self.gladeobjdict["SaveButton"].get_style().lookup_color("theme_bg_color")
            (junk,self.savebuttonnormalcolor)=self.gladeobjdict["SaveButton"].get_style().lookup_color("theme_bg_color") # use theme_bg_color or background-color? 
            (Junk,self.savebuttonreadycolor)=gdk.Color.parse('green')
            #print "savebuttonnormalcolor=",self.savebuttonnormalcolor
            #print "savebuttonreadycolor=",self.savebuttonreadycolor
            pass
        else : 
            # gtk2
            self.savebuttonnormalcolor=self.gladeobjdict["SaveButton"].get_style().bg[STATE_NORMAL]
            self.savebuttonreadycolor=self.gladeobjdict["SaveButton"].get_colormap().alloc_color("green")
            pass


        self.orighref=orighref
        
        origbasename=orighref.get_bare_unquoted_filename()
        
        # if orighref is not a .chf and not a .plf, then open
        # as a new checklist with no name, in read/write mode
        if os.path.splitext(origbasename)[1]!=".chf" and os.path.splitext(origbasename)[1]!=".plf":
            
        
            # hide the file -- prevent locking, etc. by reading it from a file object
            fh=open(orighref.getpath(),"rb")
            self.xmldoc=xmldoc.xmldoc(None,None,None,FileObj=fh,use_locking=True,contexthref=orighref,debug=True) # !!!*** can improve performance once debugged by setting debug=False
            fh.close()

            self.readonly=False
            initializefromunfilled=True
            ## absolutize all relative xlink:href links
            ##self.xmldoc.setcontextdir(os.path.split(origfilename)[0]) # ,force_abs_href=True)
            self.xmldoc.merge_namespace("chx","http://thermal.cnde.iastate.edu/checklist")
            self.xmldoc.merge_namespace("dc","http://thermal.cnde.iastate.edu/datacollect")
            self.xmldoc.suggest_namespace_rootnode(None,"http://thermal.cnde.iastate.edu/checklist")
            self.xmldoc.suggest_namespace_rootnode("chx","http://thermal.cnde.iastate.edu/checklist")
            self.xmldoc.suggest_namespace_rootnode("dc","http://thermal.cnde.iastate.edu/datacollect")
   
            #self.xmldoc.setattr(".", "origfilename", origfilename)
            unfilled_elements=self.xmldoc.xpath("chx:origunfilled")
            if len(unfilled_elements) > 0:
                unfilled_element=unfilled_elements[0]
                pass
            else: 
                unfilled_element=self.xmldoc.addelement(self.xmldoc.getroot(),"chx:origunfilled")
                pass

            # store original href 
            orighref.xmlrepr(self.xmldoc,unfilled_element)
            # log start timestamp
            
            self.logstarttimestamp()

            self.xmldoc.setattr(".","filled","true")

            # put in-memory checklist in likely destination context
            self.xmldoc.setcontexthref(self.requesteddest())

            pass
        else :

            # open existing filled checklist/plan (.chf or .plf) in read only mode 
            self.readonly=True
            initializefromunfilled=False

            #import pdb as pythondb
            try:
                self.xmldoc=xmldoc.xmldoc(orighref,None,None,use_locking=True) # !!!*** can improve performance once debugged by setting debug=False
                pass
            except IOError:
                (exctype, excvalue) = sys.exc_info()[:2] 
                tback=traceback.format_exc()
                #pythondb.set_trace()
                ErrorDialog("Error Loading Checklist",exctype,excvalue,tback)
                pass
            self.xmldoc.merge_namespace("chx","http://thermal.cnde.iastate.edu/checklist")
            self.xmldoc.merge_namespace("dc","http://thermal.cnde.iastate.edu/datacollect")

            unfilled_elements=self.xmldoc.xpath("chx:origunfilled")
            if len(unfilled_elements) > 0:
                unfilled_element=unfilled_elements[0]
                self.orighref = hrefv.fromxml(self.xmldoc,unfilled_element)                
                pass
            else: 
                sys.stderr.write("Warning:  Original Filename Not Set in Filled Checklist\n")
                pass
            

            self.chklistfile=orighref.get_bare_unquoted_filename()

            pass
        
        try :  # try...catch...finally block for handling lock we just acquired with xmldoc()

            ## do we have a <chx:parent> tag?
            #parentlist=self.xmldoc.xpath("chx:parent")
            #if len(parentlist) == 0:
            #    # add a parent tag so we don't 
            #    # end up messing with tag positioning later
            #    self.xmldoc.addelement(self.xmldoc.getroot(),"chx:parent")
            #    pass

            if self.chklistfile is not None:
                # window title is filename if we are actively updating the file
                #self.gladeobjdict["CheckListWindow"].set_title(self.chklistfile)
                self.set_window_title()
                
                #self.xmldoc.autoflush=True
                #print "Auto flush mode!!!"

                # check if our checklistfile is already in "dest"
                # if so, give it just a relative path. 
                pass
            pass
        finally:
            try : 
                self.xmldoc.unlock_rw()  # unlock and flush output to disk
                pass
            except IOError: 
                (exctype, excvalue) = sys.exc_info()[:2] 
                tback=traceback.format_exc()
                ErrorDialog("Exception flushing checklist to disk; output may not be saved",exctype,excvalue,tback)

                pass
            pass
            
        if self.xmldoc.filehref is not None:
            #chklistfile_abspath=os.path.abspath(self.chklistfile)
            #(chklistfile_absdir,chklistfile_absfile)=os.path.split(chklistfile_abspath)
            # WARNING: filenamenotify may call requestval_sync which runs sub-mainloop
            for (filenamenotify,fnargs,fnkwargs) in self.filenamenotify:
                filenamenotify(self,self.orighref,self.xmldoc.filehref,None,*fnargs,**fnkwargs)
                pass
            pass
        
        # datacollect mode:  dest does not exist. can not 
        # explicitly save
        if self.datacollectmode:
            #self.gladeobjdict["ChecklistEntry"].set_editable(False)
            #self.gladeobjdict["DestEntry"].set_editable(False)
            #self.gladeobjdict["DestBox"].hide()
            #self.gladeobjdict["DestBox"].set_no_show_all(True)
            #self.gladeobjdict["ParamBox"].remove(self.gladeobjdict["DestBox"])
            #del self.gladeobjdict["DestEntry"]
            #del self.gladeobjdict["DestLabel"]
            #del self.gladeobjdict["DestBox"]

            self.gladeobjdict["SaveButton"].connect("clicked",self.handle_done)
            if self.xmldoc.filehref is not None:
                self.private_paramdb["defaultfilename"].requestvalstr_sync(self.xmldoc.filehref.getpath())
                pass
            

            pass
        else:
            # not datacollectmode
            if self.xmldoc.filehref is not None: 
                # If checklist already has a filename, then 
                # Save button replaced with Done button
                self.gladeobjdict["SaveButton"].set_property("label","Done")                
                
                self.private_paramdb["defaultfilename"].requestvalstr_sync(self.xmldoc.filehref.getpath())
                
                
                pass
            else: 
                # self.xmldoc.filename is None
                try:
                    # Put this in a "try...except" because requestedfilename() does not seem to have much in terms of error handling
                    reqfilename=self.requestedfilename()
                    self.private_paramdb["defaultfilename"].requestvalstr_sync(reqfilename)
                    pass
                except:
                    (exctype, excvalue) = sys.exc_info()[:2] 
                    sys.stderr.write("checklist.py: warning: exception requesting default filename: %s, %s\n" % (exctype,excvalue))
                    pass
                pass
            if len(self.private_paramdb["defaultfilename"].dcvalue.value())==0:
                # still blank...
                # Create default filename from original name, ".chx" -> ".chf"
                if origbasename.endswith(".chx"):
                    self.private_paramdb["defaultfilename"].requestvalstr_sync(posixpath.splitext(origbasename)[0]+".chf")
                    pass
                elif origbasename.endswith(".plx"):
                    self.private_paramdb["defaultfilename"].requestvalstr_sync(posixpath.splitext(origbasename)[0]+".plf")
                    pass
                pass

            self.gladeobjdict["SaveButton"].set_sensitive(True)
            self.gladeobjdict["SaveButton"].connect("clicked",self.handle_save)
            #self.gladeobjdict["CheckListWindow"].connect("delete_event",self.handle_quit)

            pass
        
        
        self.xmldoc.lock_ro()  
        try:
        
        
            #checklisttag=self.xmldoc.find(".")


            if self.datacollectmode:

                # in datacollect mode, the save button is instead the "Done" button
                # if done button is supposed to save the measurement
                # then the checklist done_is_save_measurement attribute of the 
                # checklist tag 
                # should be true
                
                # also the the save button shouldn't be sensitive until we have 
                # figured out a file name
            
                if self.xmldoc.getattr(self.xmldoc.getroot(),"dc:done_is_save_measurement","false")=="true": 
                    #sys.stderr.write("Done is save measurement\n")
                    self.done_is_save_measurement=True
                    self.gladeobjdict["SaveButton"].set_property("label","Finish and save measurement")                
                    pass
                else :
                    #sys.stderr.write("Done is not save measurement\n")
                    self.gladeobjdict["SaveButton"].set_property("label","Done")
                    pass


                if self.xmldoc.getattr(".","dc:part_of_a_measurement","false")=="true": 
                    self.part_of_a_measurement=True
                    pass


                pass
            else :
                # Not datacollectmode
                pass


            # Make sure common tags exist: clinfo, specimen, perfby, date, dest, and notes
            # Important to do this here, lest tag numbering change underneath
            # the various steps and screw with resyncinc. 

            dest=None
            destl=self.xmldoc.xpath("chx:dest")
            assert(len(destl) <= 1)
            if len(destl) > 0:
                dest=destl[0]
                pass
            
            if self.datacollect_explog is not None and (dest is None or (not self.xmldoc.hasattr(dest,"autofilename") and not self.xmldoc.hasattr(dest,"autodcfilename"))):
                raise ValueError("In datacollect mode, chx:checklist/chx:dest must have an autofilename or autodcfilename attribute to determine autosave filename")
            
            checkitems=self.xmldoc.xpath("chx:checkitem")
            self.parsedchecklist=[]
            for curitem in checkitems:
                cls=self.xmldoc.getattr(curitem,"class","text")

                for char in cls: 
                    if char=="." or char=="/" or (not(char.isalnum()) and char != "_"):
                        raise ValueError("invalid character in step class %s" % (cls))
                    pass

                # Try to import class so as to obtain parameter types
                stepclass=get_step(cls+"step")
                stepgprops=gobject.list_properties(stepclass) 
                # convert gprops into types: dictionary of gobject.TYPE_whatever
                stepgprop_gtypes=dict([(prop.name,prop.value_type) for prop in stepgprops])
                stepxmlprops={}
                if hasattr(stepclass,"_%s__dcvalue_xml_properties" % (cls+"step")):
                    stepxmlprops=getattr(stepclass,"_%s__dcvalue_xml_properties" % (cls+"step"))
                    pass
                stephrefprops=frozenset([])
                if hasattr(stepclass,"_%s__dcvalue_href_properties" % (cls+"step")):
                    
                    stephrefprops=getattr(stepclass,"_%s__dcvalue_href_properties" % (cls+"step"))
                    pass
            
                step_nonparameter_elements=frozenset([])
                if hasattr(stepclass,"_%s__nonparameter_elements" % (cls+"step")):
                    
                    step_nonparameter_elements=getattr(stepclass,"_%s__nonparameter_elements" % (cls+"step"))
                    pass
                
                    
                params={}
                for child in self.xmldoc.children(curitem):
                    if self.xmldoc.is_comment(child):
                        continue
                    tag=self.xmldoc.gettag(child)
                    (prefix,dctag)=tag.split(":")
                    if prefix != "chx":
                        continue  # silently ignore non-chx tags

                    if dctag=="parameter": # old-style format
                        paramname=self.xmldoc.xpathcontext(child,"string(@name)")
                        if paramname=="": 
                            raise ValueError("Parameter does not have a name attribute in checklist item %s" % (etree.tostring(curitem,encoding="UTF-8")))
                        pass
                    else:
                        paramname=dctag
                        pass
                    
                    if paramname in step_nonparameter_elements:
                        continue # silently ignore nonparameter elements

                    #if paramname=="image":
                    #    import pdb as pythondb
                    #    pythondb.set_trace()
                    #    pass
                    description=""
                    if paramname=="description":
                        # try : 
                        description=self.xmldoc.gettext(child)
                        params[paramname]=etree.tostring(xml2pango(child),encoding='utf-8').decode("utf-8")
                        pass
                    else:
                        if paramname not in stepgprop_gtypes:
                            raise ValueError("Parameter %s not supported by %sstep" % (paramname,cls))
                        if stepgprop_gtypes[paramname].is_a(str):
                            if paramname in stepxmlprops:
                                params[paramname]=etree.tostring(child,encoding='utf-8').decode('utf-8')
                                pass
                            elif paramname in stephrefprops:
                                if self.xmldoc.hasattr(child,"xlink:href"):
                                    params[paramname]=self.xmldoc.getattr(child,"xlink:href")
                                    pass
                                else:
                                    params[paramname]=""
                                    pass
                                
                                #paramval=hrefv.fromxml(self.xmldoc,child)

                                #import pdb as pythondb
                                #pythondb.set_trace()
                                #if paramval is None:
                                #    params[paramname]=""
                                #    pass
                                #else:
                                #    params[paramname]=paramval.attempt_relative_url(self.xmldoc.getcontexthref())
                                #    pass
                                
                                pass
                            else:
                                # Regular old string parameter
                                params[paramname]=self.xmldoc.xpathcontext(child,"string(.)")
                                pass
                            
                            pass
                        elif stepgprop_gtypes[paramname].is_a(bool):
                            paramstr=self.xmldoc.xpathcontext(child,"string(.)").strip()
                            paramval=False
                            if len(paramstr)==0 or paramstr.lower()=="true":
                                paramval=True
                                pass
                            params[paramname]=paramval
                            pass
                        elif stepgprop_gtypes[paramname].is_a(int):
                            params[paramname]=int(self.xmldoc.xpathcontext(child,"string(.)").strip())
                            pass
                        elif stepgprop_gtypes[paramname].is_a(float):
                            
                            params[paramname]=float(self.xmldoc.xpathcontext(child,"string(.)").strip())
                            pass
                        else:
                            raise ValueError("Unknown type from %sstep for %s: %s" % (cls,paramname,str(stepgprop_gtypes[paramname])))
                        
                        pass
                    pass
                title=self.xmldoc.getattr(curitem,"title",defaultvalue="")

                if len(title)==0:
                    title=curitem.text
                    pass

                if title is None or len(title)==0:
                    title=description
                    pass
            
                if title is None: 
                    raise ValueError("No title or content specified in checklist item: %s" % (etree.tostring(curitem,encoding="UTF-8")))
            
                title=title.strip() # strip leading and trailing whitespace
            
                cls=self.xmldoc.getattr(curitem,"class","text")
            
                if cls=="savemeasurement":
                    self.has_save_measurement_step=True
                    pass
            
                # pycode=xml.sax.saxutils.unescape(curitem.xpath("string(pycode)"))
                #pycode=self.xmldoc.xpathcontext(curitem,"string(chx:pycode)")
                
                # self.parsedchecklist.append(checkitem(title=xml.sax.saxutils.unescape(curitem.xpath("string(@title)")),cls=curitem.xpath("string(@class)"),params=params,pycode=pycode))

                if not "description" in params:
                    if self.xmldoc.xpathcontext(curitem,"count(chx:description)") > 0:
                        params["description"]=etree.tostring(xml2pango(self.xmldoc.xpathsinglecontext(curitem,"chx:description")),encoding='utf-8').decode('utf-8')
                        pass
                    pass
            
            
                self.parsedchecklist.append(checkitem(title=title,cls=cls,params=params,xmlpath=self.xmldoc.savepath(curitem)))
                pass
            

            

            #if self.done_is_save_measurement or self.has_save_measurement_step:
            #    # extract and increment nextmeasnum        
            #    self.measnum=self.paramdb["nextmeasnum"].value()
            #    if self.measnum is None: 
            #        self.measnum=0
            #        pass
            #        
            #    self.paramdb["nextmeasnum"].requestval_sync(self.measnum+1)
            #    pass

            #if "dest" in self.paramdb:
            #    destval=self.paramdb["dest"].dcvalue
            #    pass
            #else: 
            #    destval=hrefv(".",contextdir=".")
            #    pass
            

            # if <specimen> has the special value disabled, hide the "specimen" box and set specimen_disabled
            if self.xmldoc.xpathsinglestr("chx:specimen",default="")=="disabled":
                self.gladeobjdict["SpecBox"].hide()
                self.gladeobjdict["SpecBox"].set_no_show_all(True)
                self.gladeobjdict["ParamBox"].remove(self.gladeobjdict["SpecBox"])
                del self.gladeobjdict["SpecEntry"]
                del self.gladeobjdict["SpecLabel"]
                del self.gladeobjdict["SpecBox"]
                self.specimen_disabled=True
                # sys.stderr.write("specimen is disabled!\n")
                pass            

            #if not datacollect mode, hide the "dest" entry
            #if not self.datacollectmode:
            #    del self.gladeobjdict["DestEntry"]
            #    del self.gladeobjdict["DestLabel"]
            #    del self.gladeobjdict["DestBox"]
            #    pass

        except: 
            raise
        finally:
            try : 
                self.xmldoc.unlock_ro()  # unlock 
                pass
            except IOError: 
                (exctype, excvalue) = sys.exc_info()[:2] 
                tback=traceback.format_exc()
                ErrorDialog("Exception flushing checklist to disk; output may not be saved",exctype,excvalue,tback)

                pass
            pass


        if not(self.done_is_save_measurement) and not(self.has_save_measurement_step) and not(self.part_of_a_measurement): 
            # Remove MeasnumBox and MeasnumEntry if we are not a datacollect checklist that uses them
            self.gladeobjdict["ParamBox"].remove(self.gladeobjdict["MeasnumBox"])
            del self.gladeobjdict["MeasnumEntry"]
            del self.gladeobjdict["MeasnumBox"]
            pass
                
        if self.done_is_save_measurement or self.has_save_measurement_step:
            self.shared_notes=True
            self.gladeobjdict["NotesText"].paramdb=self.paramdb
            pass
        else:
            self.shared_notes=False
            # Tell widget to use private paramdb
            self.gladeobjdict["NotesText"].paramdb=self.private_paramdb
            pass
        
        # tell filename widget to use private paramdb
        self.gladeobjdict["filenameentry"].paramdb=self.private_paramdb
        
        
        
        # set window title to checklist name
        # if self.xmldoc.filehref is None:  # not using filename for window title
        #   self.gladeobjdict["CheckListWindow"].set_title(origbasename)
        #    pass
        self.set_window_title()

        self.build_checklistbox(initializefromunfilled)  # adds the step to self.steps
        # self.checkdone()
        
        # Set savebutton background to normal condition 
        if "gi" in sys.modules: # gtk3
            ## !!!*** fixme: Probably should only create newprops once, and then add/remove it and/or enable/disable it
            #newprops=gtk.StyleProperties.new()
            #newprops.set_property("background-color",STATE_NORMAL,self.savebuttonnormalcolor)
            #self.gladeobjdict["SaveButton"].get_style_context().add_provider(newprops,gtk.STYLE_PROVIDER_PRIORITY_USER)
            self.gladeobjdict["SaveButton"].override_background_color(STATE_NORMAL,gdk.RGBA.from_color(self.savebuttonnormalcolor))

            pass
        else : # gtk2
            newsavestyle=self.gladeobjdict["SaveButton"].get_style().copy()
            newsavestyle.bg[STATE_NORMAL]=self.savebuttonnormalcolor
            self.gladeobjdict["SaveButton"].set_style(newsavestyle)
            pass
        
        
        self.gladebuilder.connect_signals(self)

        # FIXME: We should size the scroller in gtk3 too
        # ... but it seems complicated
        # 1. Need to subclass scroller
        # 2. Replace signal with get_preffered_width() and get_preferred_height virtual functions (see https://developer.gnome.org/gtk3/3.0/ch25s02.html)
        # 3. Virtual functions must be named do_get_preferred. (see http://stackoverflow.com/questions/9496322/overriding-virtual-methods-in-pygobject)
        if not( "gi" in sys.modules): 
            # gtk2 only
            self.gladeobjdict["Scroller"].connect("size-request",self.scroller_reqsize)
            pass
        else :
            # self.gladeobjdict["Scroller"].set_property("hscrollbar-policy",gtk.PolicyType.ALWAYS)
            pass
        
        
        self.xmldoc.shouldbeunlocked()


        # sys.stderr.write("Checklist: setting readonly to %s\n" % (str(self.readonly)))
        self.set_readonly(self.readonly)  # set widgets to fix and do adddoc()'s as needed
        self.gladeobjdict["ReadWriteButton"].connect("clicked",self.handle_readwrite)
        
        pass

    def set_window_title(self):

        titlehref=self.orighref  # fallback condition -- original filename
        
        if self.xmldoc.filehref is not None: 
            titlehref=self.xmldoc.filehref  # current file name
            pass
        
        # use filename part only
        filepart=titlehref.get_bare_unquoted_filename()
        
        titlestr=filepart
        
        if self.is_done():
            titlestr += " (done)"
            pass

        self.gladeobjdict["CheckListWindow"].set_title(titlestr)
        pass
        
        

    def is_done(self):
        self.xmldoc.lock_ro()
        try:
            is_done = self.xmldoc.getattr(self.xmldoc.getroot(),"done",defaultvalue="false")=="true"
            pass
        finally: 
            self.xmldoc.unlock_ro()
            pass
        return is_done

    def get_children(self):
        # Return list of all hrefs pointed to by dc:checklist tags within chx:subchecklists tags
        self.xmldoc.lock_ro()
        try:
            checklisttags=self.xmldoc.xpath("//chx:subchecklists/dc:checklist")
            children = [ hrefv.fromxml(self.xmldoc,checklisttag) for checklisttag in checklisttags ]
            
            pass
        finally: 
            self.xmldoc.unlock_ro()
            pass

        return children
    
    def get_parent(self):
        # returns hrefvalue object or None
        self.xmldoc.lock_ro()

        try:
            root=self.xmldoc.getroot()
            parentl=self.xmldoc.xpathcontext(root,"chx:parent")
            if len(parentl)==0:
                return None
                
            if self.xmldoc.hasattr(parentl[0],"xlink:href"):
                return hrefv.fromxml(self.xmldoc,parentl[0])
            else: 
                return None
                
        finally:
            self.xmldoc.unlock_ro()
            pass
        pass

    def set_parent(self,parenthref):
        # set <chx:parent> tag of main node, referring to
        # parent checklist
        # NOTE: Can only set a parent when we have a filename ourselves.
        # NOTE: since parent is a relative reference, need to redoit 
        # if we get moved somehow

        assert(not self.readonly)

        #sys.stderr.write("parentfile=%s" % (parentfile))
        #import pdb as pythondb
        
        #pythondb.set_trace()
        #traceback.print_stack()
                         
        self.xmldoc.lock_rw()

        try: 
            root=self.xmldoc.getroot()
            parenttags=self.xmldoc.xpath("chx:parent")
            assert(len(parenttags) < 2) # multiple parents does not make sense
            
            if len(parenttags)==1:
                # remove attribute if present
                if self.xmldoc.hasattr(parenttags[0],"xlink:href"):
                    self.xmldoc.remattr(parenttags[0],"xlink:href")
                    pass
                parenttag=parenttags[0]
                pass
            else : 
                # no parent tag
                # insert at beginning of file for human readability
                parenttag=self.xmldoc.insertelement(root,0,"chx:parent")
                pass


            parenthref.xmlrepr(self.xmldoc,parenttag)
            # sys.stderr.write("checklist.set_parent(): parenthref=%s; xlink:href=%s\n" % (parenthref.absurl(),self.xmldoc.getattr(parenttag,"xlink:href")))
            self.xmldoc.setattr(parenttag,"xlink:arcrole","http://thermal.cnde.iastate.edu/linktoparent")

            pass
        finally: 
            self.xmldoc.unlock_rw()
            pass
        #import pdb as pythondb
        #pythondb.set_trace()

        pass

    def addfilenamenotify(self,notify,*args,**kwargs):
        self.filenamenotify.append((notify,args,kwargs))
        pass

    def removefilenamenotify(self,notify,*args,**kwargs):
        if (notify,args,kwargs) in self.filenamenotify:
            self.filenamenotify.remove((notify,args,kwargs))
            pass
        pass

    def addfilenamenotifyifneeded(self,notify,*args,**kwargs):
        for (snotify,sargs,skwargs) in self.filenamenotify:
            if snotify==notify and args==sargs and kwargs==skwargs:
                return
            pass
            
        # if we made it through, we need to add
        self.filenamenotify.append((notify,args,kwargs))
        pass


    def addresetnotify(self,notify,*args,**kwargs):
        self.resetnotify.append((notify,args,kwargs))
        pass

    def addresetnotifyifneeded(self,notify,*args,**kwargs):
        for (snotify,sargs,skwargs) in self.resetnotify:
            if snotify==notify and args==sargs and kwargs==skwargs:
                return
            pass
            
        # if we made it through, we need to add
        self.resetnotify.append((notify,args,kwargs))
        pass

    def removeresetnotify(self,notify,*args,**kwargs):
        if (notify,args,kwargs) in self.resetnotify:
            self.resetnotify.remove((notify,args,kwargs))
            pass
        pass

    def addclosenotify(self,notify,*args,**kwargs):
        self.closenotify.append((notify,args,kwargs))
        pass

    def removeclosenotify(self,notify,*args,**kwargs):
        if (notify,args,kwargs) in self.closenotify:
            self.closenotify.remove((notify,args,kwargs))
            pass
        pass

    def addclosenotifyifneeded(self,notify,*args,**kwargs):
        for (snotify,sargs,skwargs) in self.closenotify:
            if snotify==notify and args==sargs and kwargs==skwargs:
                return
            pass
            
        # if we made it through, we need to add
        self.closenotify.append((notify,args,kwargs))
        pass

    def adddonenotify(self,notify,*args,**kwargs):
        self.donenotify.append((notify,args,kwargs))
        pass

    def removedonenotify(self,notify,*args,**kwargs):
        if (notify,args,kwargs) in self.donenotify:
            self.donenotify.remove((notify,args,kwargs))
            pass
        pass

    def adddonenotifyifneeded(self,notify,*args,**kwargs):
        for (snotify,sargs,skwargs) in self.donenotify:
            if snotify==notify and args==sargs and kwargs==skwargs:
                return
            pass
            
        # if we made it through, we need to add
        self.donenotify.append((notify,args,kwargs))
        pass
        
        

    def isconsistent(self,inconsistentlist):
        # Note: This goes through __OUR_OWN__ checklist
        # and in datacollect mode, through explogwin, (in turn through all the GUIs) 
        # but it does not go through __OTHER__ checklists
        consistent=True
        for key in self.gladeobjdict:
            if hasattr(self.gladeobjdict[key],"isconsistent"):
                consistent=consistent and self.gladeobjdict[key].isconsistent(inconsistentlist)
                pass
            pass

        for step in self.steps:
            if hasattr(step,"isconsistent"):
                consistent=consistent and step.isconsistent(inconsistentlist)
                pass
            pass
        

        if self.datacollect_explogwin is not None:
            consistent=consistent and self.datacollect_explogwin.isconsistent(inconsistentlist)
            pass
        
        return consistent


    def dc_gui_init(self,guistate):
        self.iohandlers=guistate.iohandlers

        

        # We create our own copy of guistate so we can 
        # have an expanded search directory list that would contain
        # the directory containing the checklist file

        #origfiledir=os.path.split(self.origfilename)[0]
        
        #searchdirs=[origfiledir]
        #searchdirs.extend(guistate.searchdirs)
        
        newguistate=create_guistate(guistate.iohandlers,guistate.paramdb)

                                    
        dc_initialize_widgets(self.gladeobjdict,newguistate)
        
        
        for step in self.steps: 
            try: 
                step.dc_gui_init(newguistate)
                pass
            except:
                (exctype,excvalue)=sys.exc_info()[:2]
                
                raise RuntimeError("Error initializing checklist step \"%s\" in checklist %s->%s:\n%s\n%s" % (step.stepdescr,self.orighref.absurl(),self.xmldoc.get_filehref().absurl(),traceback.format_exc(),str(excvalue)))
            step.show_all()
            pass
        self.gladeobjdict["MinorBox"].show_all()  # Make sure Rationale box shows up too, among others


        self.gladeobjdict["LowerVBox"].show_all()
        
        
        ## if we have all the information needed to set the filename, go ahead and do it!
        #if self.ok_set_filename():
        #    self.setchecklistfilename()
        #    pass
        

        # read only mode shows/hides certain components, so resetting here
        # is a good thing. 
        self.set_readonly(self.readonly)

        
        pass

    def getlog(self):
        # must only be called when xmldoc is locked, as ist returns an element
        assert(self.xmldoc.ro_lockcount > 0 or self.xmldoc.rw_lockcount > 0)

        logitems=self.xmldoc.xpath("chx:log")
        if len(logitems)==0:
            checklisttag=self.xmldoc.find(".")
            log=self.xmldoc.addelement(checklisttag,"chx:log")
            return log
        elif len(logitems) > 1:
            raise ValueError("Checklist contains multiple log entries!")
        else :
            return logitems[0]
        
        pass
    
    def logstarttimestamp(self):
        if self.readonly:
            return
        
        self.xmldoc.lock_rw()
        try:

            # generate new starttimestamp
            log=self.getlog()
            self.xmldoc.setattr(log, "starttimestamp", dg_timestamp.roundtosecond(dg_timestamp.now()).isoformat())
            
            pass
        finally:
            self.xmldoc.unlock_rw()
            pass
            

    def addlogentry(self,message,item=None,action=None,value=None,timestamp=None):
        message=str(message)
        if self.readonly:
            return
        
        self.xmldoc.lock_rw()
        
        try: 
            log=self.getlog()
            logentry=self.xmldoc.addelement(log,"chx:logentry")
            self.xmldoc.settext(logentry,message)
        
            if item is not None:
                self.xmldoc.setattr(logentry,"item",str(item))
                pass
                
            if action is not None:
                self.xmldoc.setattr(logentry,"action",str(action))
                pass

            if value is not None:
                self.xmldoc.setattr(logentry,"value",str(value))
                pass
        
            if timestamp is not None:
                self.xmldoc.setattr(logentry,"timestamp",str(timestamp))
                pass
            else :    
                # Generate timestamp with current time
                self.xmldoc.setattr(logentry,"timestamp",dg_timestamp.now().isoformat())
                pass
            pass
        except:
            raise
        finally:
            self.xmldoc.unlock_rw()
            pass

        pass
        

    def getwindow(self):
        return self.gladeobjdict["CheckListWindow"]
    

    def present(self):  # Open window, bring to front, etc. 
        self.gladeobjdict["CheckListWindow"].present()
        pass

    def build_checklistbox(self,initializefromunfilled): 
        cnt=1

        readonly=self.readonly
        if readonly:
            self.xmldoc.lock_ro()
            pass
        else:
            self.xmldoc.lock_rw()
            pass
        try :
            # show rationale if present
            rationale=self.xmldoc.find("chx:rationale")
            if rationale is not None:
                RationaleLabel=dc_wraplabel()
                RationaleLabel.set_markup("<b>Rationale</b>")
                self.gladeobjdict["MinorBox"].pack_start(RationaleLabel,True,True,0)
                
                RationaleText=dc_wraplabel()
                
                RationaleText.set_markup(etree.tostring(xml2pango(rationale),encoding='utf-8').decode('utf-8'))
                self.gladeobjdict["MinorBox"].pack_start(RationaleText,True,True,0)

                # Add HSeparator after rationale
                RationaleSeparator=gtk.HSeparator()
                self.gladeobjdict["MinorBox"].pack_start(RationaleSeparator,False,True,0)
                
                pass
        
            for item in self.parsedchecklist:
                #codelist=[]
                # sys.stderr.write("item.params=%s\n" % (str(item.params)))
                #for key in item.params:
                #    codelist.append(" stepobj.set_property(\"%s\"," % (key)) 
                #    if isinstance(item.params[key],basestring):
                #        #codelist.append("\'%s\'" % (item.params[key]))
                #        codelist.append(escapestring(item.params[key]))
                #        pass
                #    elif isinstance(item.params[key],numbers.Number):
                #        codelist.append("%d" % (item.params[key]))
                #        pass
                #    elif isinstance(item.params[key],numbers.Number):
                #        codelist.append("%16.16g" % (float(item.params[key])))
                #        pass
                #    elif isinstance(item.params[key],hrefv):
                #        # codelist.append
                #    else:
                #        raise ValueError("unknown parameter value %s of type %s" % (str(item.params[key]),str(type(item.params[key]))))
               #     codelist.append(")\n")
               #     pass
               # if len(item.pycode) > 0:
               #     codelist.append(" if True:\n")
                #    codelist.append(item.pycode)
                #    pass
                ##print "Len: item.pycode=%d" % len(item.pycode)
                ##print ":".join("{0:x}".format(ord(c)) for c in item.pycode)

                ## append terminating "pass" statement to code list
                #codelist.append("\n pass\n")
            
                try: 
                    step=steptemplate(cnt,item.title,item.cls+"step",params=item.params,chklist=self,xmlpath=item.xmlpath,paramdb=self.paramdb)
                    pass
                except:
                    (exctype,excvalue)=sys.exc_info()[:2]
                    
                    raise RuntimeError("Error initializing checklist step \"%s\" in checklist %s->%s:\n%s\n%s" % (item.title,self.orighref.absurl(),self.xmldoc.get_filehref().absurl(),traceback.format_exc(),str(excvalue)))
                

                self.gladeobjdict["MinorBox"].pack_start(step,True,True,0)

                if initializefromunfilled:
                    assert(not self.readonly)
                    step.resetchecklist()
                    pass
                
                self.steps.append(step)

                step.gladeobjdict["checkbutton"].connect("toggled",self.handle_check,cnt-1)

                if item.xmlpath is not None:
                    xmltag=self.xmldoc.restorepath(item.xmlpath)
                    if self.xmldoc.hasattr(xmltag,"checked") and self.xmldoc.getattr(xmltag,"checked")=="true":
                        step.gladeobjdict["checkbutton"].set_property("active",True)
                        pass
                    pass

                    
                    
                self.setheadingcolor(cnt-1)
                
                
                cnt+=1
                
                pass
            pass
        except:
            raise
        finally:
            if readonly:
                self.xmldoc.unlock_ro()
                pass
            else:
                self.xmldoc.unlock_rw()
                pass
            
            pass

        pass
    def handle_reset(self,event):

        self.xmldoc.shouldbeunlocked()

        
        if self.datacollect_explogwin is not None:
            # perform explogwin pre-notification so it can open any parent
            self.datacollect_explogwin.open_checklist_parent(self)
            pass


        # # flush file
        # self.xmldoc.flush()
        

        if self.xmldoc.filehref is not None:
            self.pre_reset_href=self.xmldoc.filehref
            pass

        # Eliminate current name so it can be re-set
        self.set_readonly(True) # force disconnection from file
        self.xmldoc.set_href(None,readonly=False)

        # preset readonly flag so nothing objects to writing. 
        self.readonly=False
        
        # set filename field at bottom of window
        self.private_paramdb["defaultfilename"].requestvalstr_sync("") 

        self.xmldoc.autoflush=False
        self.chklistfile=None

        self.xmldoc.lock_rw()
        try : 
            # clear done attribute of <checklist> tag
            if self.xmldoc.hasattr(self.xmldoc.getroot(),"done"):
                self.xmldoc.remattr(self.xmldoc.getroot(),"done")
        finally:
            self.xmldoc.unlock_rw()
            pass
        
        # make any notifications
        # WARNING: resetnotify may call requestval_sync which runs sub-mainloop
        # cnt=0
        for (resetnotify,rnargs,rnkwargs) in self.resetnotify:
            #sys.stderr.write("cnt=%d\n" % (cnt))
            resetnotify(self,self.pre_reset_href,*rnargs,**rnkwargs)
            #cnt+=1
            pass

        

        # if "measnum" in self.private_paramdb:# reset checklist measnum entry to the empy set
        #    self.private_paramdb["measnum"].requestval_sync(integersetv(set([])))
        #    #sys.stderr.write("chklist measnum=%s; paramdb measnum=%s\n" % (str(self.private_paramdb["measnum"].dcvalue),str(self.paramdb["measnum"].dcvalue)))
        #    pass
        

        ## Get new measnum
        #if "measnum" in self.private_paramdb:
        #    self.private_paramdb.measnum=self.paramdb["nextmeasnum"].value()
        #    self.paramdb["nextmeasnum"].requestval_sync(self.measnum+1)
        #    pass
            
        

        # try : 
        #     assert(0)
        # except:
        #     import pdb as pythondb
        #     pythondb.post_mortem()
        #     pass

        self.xmldoc.lock_rw()

        try : 
            assert(self.xmldoc.doc is not None)
        
            for cnt in range(len(self.steps)):
                self.steps[cnt].gladeobjdict["checkbutton"].set_property("active",False)
                xmltag=self.xmldoc.restorepath(self.steps[cnt].xmlpath)
                self.xmldoc.setattr(xmltag,"checked","false")
                
                self.steps[cnt].resetchecklist()
                pass

            # clear measnum
            measnumels=self.xmldoc.xpath("dc:measnum")
            for measnumel in measnumels:
                self.xmldoc.remelement(measnumel)
                pass

            # clear specimen
            specimenels=self.xmldoc.xpath("dc:specimen")
            for specimenel in specimenels:
                self.xmldoc.remelement(specimenel)
                pass

            # clear perfby
            perfbyels=self.xmldoc.xpath("dc:perfby")
            for perfbyel in perfbyels:
                self.xmldoc.remelement(perfbyel)
                pass

            # clear date
            dateels=self.xmldoc.xpath("dc:date")
            for dateel in dateels:
                self.xmldoc.remelement(dateel)
                pass

            

            # reset 'done' attribute
            if self.xmldoc.hasattr(self.xmldoc.getroot(),'done'):
                self.xmldoc.remattr(self.xmldoc.getroot(),'done')
                pass
                
            # reset 'allchecked' attribute
            if self.xmldoc.hasattr(self.xmldoc.getroot(),'allchecked'):
                self.xmldoc.remattr(self.xmldoc.getroot(),'allchecked')
                pass
            
            # reset 'filled' attribute
            if self.xmldoc.hasattr(self.xmldoc.getroot(),'filled'):
                self.xmldoc.remattr(self.xmldoc.getroot(),'filled')
                pass
        
            
        
            # remove any dc:autoexp elements that might have been added
            for autoexp in self.xmldoc.xpath("chx:checkitem/dc:autoexp"):
                autoexp.getparent().remove(autoexp)
                pass
        


            
            # reset window title to checklist name
            #self.gladeobjdict["CheckListWindow"].set_title(os.path.split(self.orighref.get_bare_unquoted_filename())[1])
            self.set_window_title()

            # clear notes
            notesels=self.xmldoc.xpath("chx:notes")
            for notesel in notesels:
                #sys.stderr.write("Removing notesel: %s\n" % (etree.tostring(notesel)))
                self.xmldoc.remelement(notesel)
                pass


            #if self.shared_notes:
            #    self.paramdb["notes"].requestvalstr_sync("")
            #    pass
            #else :
            #    self.private_paramdb["notes"].requestvalstr_sync("")
            #    pass
            
            # reset checklist log
            log=self.getlog()
            
            logentries=list(log) # get list of children of checklist log
            for logentry in logentries: 
                log.remove(logentry)
                pass
            
            self.addlogentry("Reset checklist",action="reset")
            self.logstarttimestamp()

            

            self.set_readonly(False)
            

            pass
        except: 
            raise

        finally:
            
            self.xmldoc.unlock_rw()
                       
            pass


        
        for cnt in range(len(self.steps)):
            self.steps[cnt].resetchecklist()
            pass
        
        
        pass

    def verify_save(self):


        inconsistentlist=[]

        consistent=self.isconsistent(inconsistentlist)

        if not consistent:
            if hasattr(gtk,"MessageType") and hasattr(gtk.MessageType,"WARNING"):
                consistdialog=gtk.MessageDialog(type=gtk.MessageType.ERROR,buttons=gtk.ButtonsType.OK)
                # gtk3
                pass
            else : 
                consistdialog=gtk.MessageDialog(type=gtk.MESSAGE_ERROR,buttons=gtk.BUTTONS_OK)
                pass
            consistdialog.set_markup("Error: Not all parameter entries in a consistent state.\nWill not save measurement.\nInconsistent params: %s" % (str(inconsistentlist)))
            consistdialog.run()
            consistdialog.destroy()
            return False
        
        done=self.checkdone()
        if not done:
            if hasattr(gtk,"MessageType") and hasattr(gtk.MessageType,"WARNING"):
                # gtk3
                donedialog=gtk.MessageDialog(type=gtk.MessageType.WARNING,buttons=gtk.ButtonsType.OK_CANCEL)
                pass
            else : 
                donedialog=gtk.MessageDialog(type=gtk.MESSAGE_WARNING,buttons=gtk.BUTTONS_OK_CANCEL)
                pass
            donedialog.set_markup("Warning: Not all items are checked. Continue  save? ")
            result=donedialog.run()
            donedialog.destroy()
            
            if result==RESPONSE_OK:
                return True
            return False
        

        return True  # OK to do save

    def save_measurement(self):
        clinfo=None
        cltitle=None

        if self.readonly:
            return
            

        if self.xmldoc.filehref is None: 
            raise ValueError("Checklist save_measurement() called on checklist that does not have a filename set.... Need to check at least one box prior to saving measurement")

        self.paramdb["measchecklist"].requestval_sync(self.xmldoc.get_filehref())

        self.xmldoc.lock_rw()
        try:
            clinfo_ns=self.xmldoc.xpath("chx:clinfo")
            if len(clinfo_ns) > 0 and len(clinfo_ns[0].text) > 0:
                clinfo=clinfo_ns[0].text
                pass
        
            cltitle_ns=self.xmldoc.xpath("chx:cltitle")
            if len(cltitle_ns) > 0 and len(cltitle_ns[0].text) > 0:
                cltitle=cltitle_ns[0].text
                pass
        
            # store name of this checklist file in paramdb
            # self.paramdb["measchecklist"].requestvalstr_sync(self.chklistfile)         
            #if os.path.isabs(self.origfilename):
            #    measchecklist_context=None # use absolute path
            #else: 
            # measchecklist_context=self.xmldoc.getcontextdir()

            #if self.xmldoc.filename is None:
            #    self.paramdb["measchecklist"].requestval_sync(checklistdb.generate_inmemory_id(self))
            #    pass
            #else : 

            
            autoexps=[]
            for autoexp in self.xmldoc.xpath("chx:checkitem/dc:autoexp"):
            
                aecopy=copy.deepcopy(autoexp)
                # sys.stderr.write("\n\ngot aecopy: %s\n" % (etree.tostring(aecopy)))
                aecopydoc=xmldoc.copy_from_element(self.xmldoc,autoexp)
                
                title=self.xmldoc.xpathcontext(autoexp,"string(../@title)")
                if len(title)==0:
                    title=self.xmldoc.xpathcontext(autoexp,"string(..)")
                    pass
                title=title.strip() # strip whitespace
            
                # have to use low-level lxml code here because aecopy is not tied to any xmldoc yet.
                aecopydoc.setattr(aecopydoc.getroot(),"title",title)
                
                autoexps.append(aecopydoc)                
            
                pass
        
            # main paramdb measnum should be one of the measnums in the set 
            # that is our private_paramdb measnum
            #assert(self.paramdb["measnum"].dcvalue.value() in self.private_paramdb["measnum"].dcvalue.value())
            # add in any <dc:autoexp>s with their <dc:automeas>s from the checklist 
            # sys.stderr.write("\n\ngot meastag: %s\n" % (etree.tostring(meastag)))
            pass
        except:
            raise
        finally:
            self.xmldoc.unlock_rw()
            pass

        #sys.stderr.write("checklist save_measurement(): calling recordmeasurement()\n")
        self.datacollect_explog.recordmeasurement(self.paramdb["measnum"].dcvalue.value(),clinfo=clinfo,cltitle=cltitle,extratagdoclist=autoexps)
        
        
        pass

    # dont_switch_xmldoc_mode=False is used as a flag from setfilename
    # to indicate we're not really making the file readonly,
    # just using readonly mode as a way to unsync from the file before we change
    # the name
    def set_readonly(self,readonly,dont_switch_xmldoc_mode=False):
        if (readonly): 
            self.readonly=True

            # update xmldoc readonly flag -- used to indicate we're just disconnecting syncrhonization, not really setting readony
            if not dont_switch_xmldoc_mode:
                self.xmldoc.set_readonly(True)

                # Set all child checklists
                # that are open to read-only too. 
                for childhref in self.get_children():
                    (childclobj,childhref2)=dc2_misc.searchforchecklist(childhref)
                    if childclobj is not None:
                        childclobj.set_readonly(True)
                        pass
                    
                    pass
                
                pass
            # extract values for notes, date, perfby,  specimen, and measnum fields
            self.xmldoc.lock_ro()
            try:
                notesvalue=stringv("")
                notestags=self.xmldoc.xpath("chx:notes")
                if len(notestags) > 0:
                    notesvalue=stringv.fromxml(self.xmldoc,notestags[0])
                    pass

                datevalue=datesetv("")
                datetags=self.xmldoc.xpath("chx:date")
                if len(datetags) > 0:
                    datevalue=datesetv.fromxml(self.xmldoc,datetags[0])
                    pass

                perfbyvalue=stringv("")
                perfbytags=self.xmldoc.xpath("chx:perfby")
                if len(perfbytags) > 0:
                    perfbyvalue=stringv.fromxml(self.xmldoc,perfbytags[0])
                    pass

                specimenvalue=stringv("")
                specimentags=self.xmldoc.xpath("chx:specimen")
                if len(specimentags) > 0:
                    specimenvalue=stringv.fromxml(self.xmldoc,specimentags[0])
                    pass
                
                measnumvalue=integerv("")
                measnumtags=self.xmldoc.xpath("dc:measnum")
                if len(measnumtags) > 0:
                    measnumvalue=integerv.fromxml(self.xmldoc,measnumtags[0])
                    pass
                pass

            
            finally:
                self.xmldoc.unlock_ro()
                pass
            

            # gray out done button
            self.gladeobjdict["SaveButton"].set_sensitive(False)



            # Show "read only" warning and button
            #sys.stderr.write("showing readonlyhbox\n")
            self.gladeobjdict["ReadonlyHBox"].show_all()

            # gray out all of the steps
            for boxnum in range(len(self.steps)):
                self.steps[boxnum].set_readonly(readonly)
                pass
            
            # gray out notes entry but keep same text
            self.gladeobjdict["NotesText"].set_fixed(True,notesvalue)
            # unsync notes
            if self.shared_notes:
                if self.notes_sync is not None:
                    self.paramdb["notes"].controller.remdoc(*self.notes_sync)
                    pass
                pass
            else: 
                if self.notes_sync is not None:
                    self.private_paramdb["notes"].controller.remdoc(*self.notes_sync)
                    pass
                pass
            self.notes_sync=None

            ## unsync dest
            #self.gladeobjdict["DestEntry"].set_fixed(True)
            #if self.dest_sync is not None:
            #    self.paramdb["dest"].controller.remdoc(*self.dest_sync)
            #    pass
            #self.dest_sync=None

            # unsync date 
            self.gladeobjdict["DateEntry"].set_fixed(True,datevalue)
            if self.date_sync is not None:
                self.paramdb["date"].controller.remdoc(*self.date_sync)
                pass
            self.date_sync=None

            # unsync perfby
            self.gladeobjdict["PerfbyEntry"].set_fixed(True,perfbyvalue)
            if self.perfby_sync is not None:
                self.paramdb["perfby"].controller.remdoc(*self.perfby_sync)
                pass
            self.perfby_sync=None
            
            # unsync specimen
            if not self.specimen_disabled:
                self.gladeobjdict["SpecEntry"].set_fixed(True,specimenvalue)
                if self.specimen_sync is not None:
                    self.paramdb["specimen"].controller.remdoc(*self.specimen_sync)
                    pass
                self.specimen_sync=None
                pass

            # unsync measnum
            # gray-out Measnum eentry
            if "MeasnumEntry" in self.gladeobjdict:
                self.gladeobjdict["MeasnumEntry"].set_fixed(True,measnumvalue)
                if self.measnum_sync is not None:
                    self.paramdb["measnum"].controller.remdoc(*self.measnum_sync)
                    pass
                pass
            self.measnum_sync=None

            
            pass
        else:
            # not readonly

            self.readonly=False
            if not dont_switch_xmldoc_mode:
                self.xmldoc.set_readonly(False)
                pass
            
            try: 


                # set up synchronization
                
                # measnum is in general a set of integers. We only create it now 
                # that we know if we have done_is_save_measurement, has_save_measurement_step or part_of_a_measurement
                if self.done_is_save_measurement or self.has_save_measurement_step or self.part_of_a_measurement: 
                    # sync measnum... create element if necessary, then adddoc

                    if self.measnum_sync is None:
                        self.measnum_sync = self.paramdb["measnum"].controller.adddoc(self.xmldoc,"dc:measnum",logfunc=self.addlogentry,autocreate_parentxpath=".",autocreate_tagname="dc:measnum",autocreate_insertpos=0)
                        pass
                    # un-gray-out Measnum eentry
                    self.gladeobjdict["MeasnumEntry"].set_fixed(False)
                    
                    
                    pass
                


                # sync specimen
                if not self.specimen_disabled:
                    if self.specimen_sync is None:
                        self.specimen_sync=self.paramdb["specimen"].controller.adddoc(self.xmldoc,"chx:specimen",logfunc=self.addlogentry,autocreate_parentxpath=".",autocreate_tagname="chx:specimen",autocreate_insertpos=0)
                        pass
                    self.gladeobjdict["SpecEntry"].set_fixed(False)
                    pass
            

                # sync perfby
                if self.perfby_sync is None:
                    self.perfby_sync=self.paramdb["perfby"].controller.adddoc(self.xmldoc,"chx:perfby",logfunc=self.addlogentry,autocreate_parentxpath=".",autocreate_tagname="chx:perfby",autocreate_insertpos=0)
                    pass
                self.gladeobjdict["PerfbyEntry"].set_fixed(False)
                
                # sync date:
                if self.date_sync is None:
                    self.date_sync=self.paramdb["date"].controller.adddoc(self.xmldoc,"chx:date",logfunc=self.addlogentry,autocreate_parentxpath=".",autocreate_tagname="chx:date",autocreate_insertpos=0)
                    pass
                self.gladeobjdict["DateEntry"].set_fixed(False)

                ## sync dest
                #if self.dest_sync is None:
                #    self.dest_sync=self.paramdb["dest"].controller.adddoc(self.xmldoc,"chx:dest",logfunc=self.addlogentry,autocreate_parentxpath=".",autocreate_tagname="chx:dest",autocreate_insertpos=0)
                #    pass
                #self.gladeobjdict["DestEntry"].set_fixed(False)
                
                # sync notes
                if self.shared_notes:
                    if self.notes_sync is None:
                        self.notes_sync=self.paramdb["notes"].controller.adddoc(self.xmldoc,"chx:notes",logfunc=self.addlogentry,autocreate_parentxpath=".",autocreate_tagname="chx:notes",autocreate_insertpos=0)
                        pass
                    pass
                else:  # not self.shared_notes
                    if self.notes_sync is None:
                        self.notes_sync=self.private_paramdb["notes"].controller.adddoc(self.xmldoc,"chx:notes",logfunc=self.addlogentry,autocreate_parentxpath=".",autocreate_tagname="chx:notes",autocreate_insertpos=0)
                        pass
                    pass
                self.gladeobjdict["NotesText"].set_fixed(False)


                # un-gray out all of the checkboxes and steps
                for boxnum in range(len(self.steps)):
                    self.steps[boxnum].set_readonly(readonly)
                    
                    pass


                # Hide "read only" warning and button
                #sys.stderr.write("hiding ReadonlyHBox\n")
                self.gladeobjdict["ReadonlyHBox"].hide()
                
                # un-gray out notes entry
                self.gladeobjdict["NotesText"].set_fixed(False)

                
                if (self.datacollectmode and self.xmldoc.filehref is None) or (self.datacollectmode and self.is_done()):
                    # gray out done button if we are in datacollect mode
                    # (in datacollect mode cannot be sensitive until the filename
                    # is picked) or the checklist is already marked as done
                    self.gladeobjdict["SaveButton"].set_sensitive(False)
                    
                    pass
                else:
                    self.gladeobjdict["SaveButton"].set_sensitive(True)
                    pass

                # for checklist to be read-write, parent must also
                # be read-write
                parentclobj=None
                parent=self.get_parent() # returns hrefv

                if parent is not None:
                    (parentclobj,parenthref)=dc2_misc.searchforchecklist(parent)
                    pass
                
                if parentclobj is not None:
                    parentclobj.set_readonly(False)
                    pass
                elif parent is not None:
                    sys.stderr.write("checklist.set_readonly(%s,False): Cannot find parent %s to set it in read/write mode. This is not a problem if the parent checklist is managed by dc_checklist instead of datacollect2.\n"  % (self.xmldoc.get_filehref(),parent.absurl()))
                    pass
                
                
                pass
            except:
                # exception when adding documents... switch back to readonly
                sys.stderr.write("checklist (%s): Exception switching to read/write mode. Returning to read-only mode\n" % (str(self.xmldoc.get_filehref())))
                self.set_readonly(True)
                raise
            pass
        pass

    def handle_readwrite(self,event):
        # user clicked the ReadWriteButton to convert a checklist to read/write mode
        self.set_readonly(False)
        pass
    
    
    def handle_done(self,event):
        # This is the save button, in datacollect mode. It makes all
        # the checkitems insensitive and clears the filename

        #contextdir=os.path.join(os.path.split(self.xmldoc.filename)[0],"..")
        if self.readonly:
            return
        
        #checklistdb.print_checklists(contextdir,self.paramdb,"checklists")

        #sys.stderr.write("handle_done()\n")
            
        self.xmldoc.shouldbeunlocked()

        if not self.verify_save():
            return
        
        # Check if it's OK to be 'done'... in datacollect mode
        # measnum should not have been used before
        if self.datacollectmode and (self.done_is_save_measurement):
            (measnum_in_xlg,beyond_latest_measnum)=self.check_measnum_status()
            if measnum_in_xlg or not(beyond_latest_measnum):
                # Ask user if OK to proceed
                if hasattr(gtk,"MessageType") and hasattr(gtk.MessageType,"QUESTION"):
                    # gtk3
                    Dialog=gtk.MessageDialog(type=gtk.MessageType.QUESTION,buttons=gtk.ButtonsType.YES_NO)
                    pass
                else : 
                    Dialog=gtk.MessageDialog(type=gtk.MESSAGE_QUESTION,buttons=gtk.BUTTONS_YES_NO)
                    pass
                if measnum_in_xlg:
                    statusmsg="already used in the experiment log."
                    pass
                else: 
                    statusmsg="less than the most recent Measnum."
                    pass

                Dialog.set_markup(("Warning: Measurement number (Measnum=%d) is " % (self.paramdb["measnum"].dcvalue.value()))+ statusmsg + "\nOK to use this Measnum and write to the experiment log anyway?")
                result=Dialog.run()
                Dialog.destroy() 
                if result!=RESPONSE_YES:
                    return
                pass
            pass
        
        #import pdb as pythondb
        #pythondb.set_trace()

        # gray out done button so user doesn't accidentally re-click
        self.gladeobjdict["SaveButton"].set_sensitive(False)

        try : 

            # sys.stderr.write("handle_done() try block. done_is_save_measurement=%s\n" % (str(self.done_is_save_measurement)))

            #sys.stderr.write("checklist done: setting done attribute\n")
            self.xmldoc.lock_rw()
            try : 
                # set done attribute of <checklist> tag
                self.xmldoc.setattr(self.xmldoc.getroot(),'done','true')
            finally:
                self.xmldoc.unlock_rw()
                pass

            #import pdb as pythondb
            #pythondb.set_trace()
                
            self.set_window_title()  # update window title now that we are done
                
            if self.done_is_save_measurement:
                #sys.stderr.write("handle_done() saving measurement\n")
                self.save_measurement()
                pass
            # All lockcounts should be zero now!
            self.xmldoc.shouldbeunlocked()

            #checklistdb.print_checklists(contextdir,self.paramdb,"checklists")


            # self.xmldoc.flush() # Make sure everything written
            #sys.stderr.write("checklist done: doing notifies\n")
            
            for (donenotify,dnargs,dnkwargs) in self.donenotify: 
                donenotify(self,self.xmldoc.filehref,*dnargs,**dnkwargs)
                pass

            self.set_readonly(True)
            
            # self.grayed_out=True
            # self.pre_reset_filename=self.xmldoc.href

            #sys.stderr.write("Notifications done\n")
            #checklistdb.print_checklists(contextdir,self.paramdb,"checklists")


            # self.xmldoc.setfilename(None) #  Inhibit future writes
                


            # if this is a done_is_save_measurement checklist, need to increment
            # measnum
            if self.done_is_save_measurement: 
                self.paramdb["measnum"].requestval_sync(integerv(self.paramdb["measnum"].dcvalue.value()+1))
                pass

            
            
            if self.done_is_save_measurement or self.has_save_measurement_step:
                # clear out notes -- ready for next measurement
                self.paramdb["notes"].requestvalstr_sync("") 
                pass
                
            #sys.stderr.write("grayed out\n")
            #checklistdb.print_checklists(contextdir,self.paramdb,"checklists")


            #sys.stderr.write("cleared out\n")
            #checklistdb.print_checklists(contextdir,self.paramdb,"checklists")

            if self.done_is_save_measurement or self.has_save_measurement_step:
                # clear name of checklist file in paramdb
                ###!!!*** possible bug: Should measchecklist param be private? 
                ### No it shouldn't.... There is one and only one checklist
                ### for which the save measurement button is clicked. 
                self.paramdb["measchecklist"].requestvalstr_sync("")         
                pass

            
            
            pass
        except : 
            (exctype, excvalue) = sys.exc_info()[:2] 
            tback=traceback.format_exc()
            ErrorDialog("Exception handling done condition; output may not be saved",exctype,excvalue,tback)
            pass
        
        pass

    def handle_save(self,event):
        if self.readonly:
            return

        if not self.datacollectmode and self.xmldoc.filehref is not None:
            # if filename has been set, delegate to done button
            return self.handle_done(event)

        if not self.verify_save():
            return

        # print "Save as..."
        if hasattr(gtk,"FileChooserAction") and hasattr(gtk.FileChooserAction,"OPEN"):
            # gtk3
            Chooser=gtk.FileChooserDialog(title="Save as...",action=gtk.FileChooserAction.SAVE,buttons=(gtk.STOCK_CANCEL,gtk.ResponseType.CANCEL,gtk.STOCK_SAVE,gtk.ResponseType.OK))
        else : 
            Chooser=gtk.FileChooserDialog(title="Save as...",action=gtk.FILE_CHOOSER_ACTION_SAVE,buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_SAVE,gtk.RESPONSE_OK))
            pass

        Chooser.set_modal(True)
        #sys.stderr.write("checklist set_current_name(%s)\n" % (str(self.private_paramdb["defaultfilename"].dcvalue)))
        Chooser.set_current_name(os.path.split(str(self.private_paramdb["defaultfilename"].dcvalue))[1])
        Chooser.set_current_folder(os.path.join(os.path.split(str(self.private_paramdb["defaultfilename"].dcvalue))[0],'.'))
        Chooser.set_do_overwrite_confirmation(True)

        origbasename=self.orighref.get_bare_unquoted_filename()
        if origbasename.endswith(".plx") or origbasename.endswith(".plf"):
            plffilter=gtk.FileFilter()
            plffilter.set_name("Filled-out plan files")
            plffilter.add_pattern("*.plf")
            Chooser.add_filter(plffilter)
            
            pass
        else : 
            chffilter=gtk.FileFilter()
            chffilter.set_name("Filled-out checklist files")
            chffilter.add_pattern("*.chf")
            Chooser.add_filter(chffilter)
            pass

        response=Chooser.run()
        name=Chooser.get_filename()
        Chooser.hide()
        Chooser.destroy()

        if self.datacollectmode:
            # name should be relative to datacollect context href
            contextdir=self.datacollect_explog.getcontexthref().getpath()
            relpath=canonicalize_path.relative_path_to(contextdir,name)
            namehref=hrefv(pathname2url(relpath),self.datacollect_explog.getcontexthref())
            pass
        else:
            # absolute paths OK
            namehref=hrefv(pathname2url(name))
            pass
        
        if response==RESPONSE_OK:

            # print "Saving..."
            

            
            oldhref=self.xmldoc.get_filehref()

            old_readonly=self.readonly
            self.set_readonly(True,dont_switch_xmldoc_mode=True) # force disconnection from file
            self.xmldoc.set_href(namehref)  #,force_abs_href=True)
            self.set_readonly(old_readonly) # reconnect to file, if applicable
            
            # WARNING: filenamenotify may call requestval_sync which runs sub-mainloop

            # self.xmldoc.lock_rw()
            # try: 
                #destl=self.xmldoc.xpath("chx:dest")
                #assert(len(destl) == 1)
                #dest=destl[0]
                
                # xlink fixups now automatic
                #if len(self.xmldoc.xpath("chx:parent")) > 0:
                #    # if we have a parent update it relative to the new filename
                #    self.set_parent(self.xmldoc.getcontexthref(),self.xmldoc.getattr(None,"parent"))
                #
                #    pass
            #     pass
            # finally:
            #    self.xmldoc.unlock_rw()
            #    pass


            for (filenamenotify,fnargs,fnkwargs) in self.filenamenotify:
                
                filenamenotify(self,self.orighref,namehref,oldhref,*fnargs,**fnkwargs)
                pass
            
            # Now that we have a filename, "Save" button should be a "Done" button
            self.gladeobjdict["SaveButton"].set_property("label","Done")

            # set window title
            #self.gladeobjdict["CheckListWindow"].set_title(os.path.split(name)[-1])
            self.set_window_title()
            
            # fh=file(name,"w")
            # fh.write(etree.tostring(self.xmldoc,pretty_print=True))
            # fh.close()
            pass
        else: 
            # print "Canceling"
            pass
        pass
    

    def destroy(self):


        self.xmldoc.shouldbeunlocked()

        # IMPORTANT: remdoc() calls here must be matched with adddoc() calls in constructor !!!

        for (closenotify,cnargs,cnkwargs) in self.closenotify: 
            closenotify(self,*cnargs,**cnkwargs)
            pass

            

        # if self.specimen_perfby_date_in_private_paramdb:
        #     if not self.specimen_disabled: 
        #         self.private_paramdb["specimen"].controller.remdoc(self.xmldoc,"chx:specimen",logfunc=self.addlogentry)
        #         pass
        #     self.private_paramdb["perfby"].controller.remdoc(self.xmldoc,"chx:perfby",logfunc=self.addlogentry)
        #     self.private_paramdb["date"].controller.remdoc(self.xmldoc,"chx:date",logfunc=self.addlogentry)

        #pass
        #else: 
        #
        #    if not self.specimen_disabled: 
        #        self.paramdb["specimen"].controller.remdoc(self.xmldoc,"chx:specimen",logfunc=self.addlogentry)
        #        pass
        #    self.paramdb["perfby"].controller.remdoc(self.xmldoc,"chx:perfby",logfunc=self.addlogentry)
        #    self.paramdb["date"].controller.remdoc(self.xmldoc,"chx:date",logfunc=self.addlogentry)
        #    pass
        #
        #self.private_paramdb["dest"].controller.remdoc(self.xmldoc,"chx:dest",logfunc=self.addlogentry)

        #notes=self.xmldoc.xpath("chx:notes")[0]
        #if "shared" in notes.attrib and notes.attrib["shared"]=="true":
        #if self.shared_notes: 
        #    self.paramdb["notes"].controller.remdoc(self.xmldoc,"chx:notes",logfunc=self.addlogentry)
        #    pass
        #else: 
            # unlink private notes entry from physical document
        #    self.private_paramdb["notes"].controller.remdoc(self.xmldoc,"chx:notes",logfunc=self.addlogentry)
        #    pass

        # unlink measnum from private paramdb
        #if "measnum" in self.private_paramdb: 
        #    self.private_paramdb["measnum"].controller.remdoc(self.xmldoc,"dc:measnum")
        #    pass

        self.set_readonly(True)

        self.closed=True


        self.getwindow().hide()
        self.getwindow().destroy()
        del self.gladeobjdict
        del self.gladebuilder
        del self.parsedchecklist
        self.iohandlers=None

        for step in self.steps: 
            if hasattr(step,"destroystep"):
                step.destroystep()
                pass
            pass


        self.steps=None
        del self.xmldoc
        self.paramdb=None
        del self.paramdb_ext
        self.datacollect_explog=None
        del self.private_paramdb

        pass

    # handle_quit() now taken over by standalone_checklist.handle_checklist_close()
    # and explogwindow.closehandler()
    #def handle_quit(self,param1,param2):
    #    gtk.main_quit()
    #    pass

    def setheadingcolor(self,boxnum):
        obj=self.steps[boxnum]
        if obj.gladeobjdict["checkbutton"].get_property("active"):
        
            # set title bar to green
            obj.gladeobjdict["numbertitle"].modify_fg(STATE_NORMAL,gdk.color_parse("#00a000"))
            pass
        else : 
            # set title bar to red
            obj.gladeobjdict["numbertitle"].modify_fg(STATE_NORMAL,gdk.color_parse("#a00000"))
            pass
        pass


    def checkdone(self):
        done=True
        for step in self.steps: 
            if not step.gladeobjdict["checkbutton"].get_property("active"):
                done=False
                break
            pass
        
        return done
    
    def check_measnum_status(self):
        # Must lock explog, so don't call with checklist locked!!! 
        
        measnum=self.paramdb["measnum"].dcvalue
        
        
        # evaluate experiment log status: 
                
        self.datacollect_explog.lock_ro()
        try: 

            # Measnum_in_xlg says whether we find this measnum in the experiment log already
            measnum_in_xlg=len(self.datacollect_explog.xpath("dc:measurement[number(dc:measnum)=%d]" % (measnum.value()))) > 0
                    
                    
            # find maximum measnum with xpath (per http://stackoverflow.com/questions/1128745/how-can-i-use-xpath-to-find-the-minimum-value-of-an-attribute-in-a-set-of-elemen )
 
               
            latest_measnum=self.datacollect_explog.xpathsingle("number(dc:measurement/dc:measnum[not(. < ../../dc:measurement/dc:measnum)][1])",default=None)
            if latest_measnum is not None and not math.isnan(latest_measnum):                
                beyond_latest_measnum = measnum.value() > latest_measnum
                pass
            else:
                beyond_latest_measnum=True
                pass
            
            pass
        finally:
            self.datacollect_explog.unlock_ro()
            pass
        return (measnum_in_xlg,beyond_latest_measnum)
    

   
    
    def ok_set_filename(self):
        # Return whether enough checkboxes have been checked that
        # it's OK to set the filename (and we still need to)

        self.xmldoc.shouldbeunlocked()
        
        #sys.stderr.write("ok_set_filename()\n")
        OK=False
        measnum_in_xlg=None

        if self.xmldoc.filehref is not None:
            return False

        # if we are in datacollectmode and done_is_save_measurement, has_save_measurement_step, or part_of_a_measurement, then we use the measnum in the filename so we need a valid measnum before we can set the filename
        if self.datacollectmode and (self.done_is_save_measurement or self.has_save_measurement_step or self.part_of_a_measurement):
            if self.paramdb["measnum"].dcvalue.isblank():
                #sys.stderr.write("ok_set_filename nned measnum\n")

                return False
            pass
        


        self.xmldoc.lock_ro()
        try: 
            destl=self.xmldoc.xpath("chx:dest")

            if len(destl)==0:
                OK=True
                pass
            else: 
                assert(len(destl) == 1)
                dest=destl[0]
                
                use_autodcfilename=False
                use_autofilename=False
                
                if not self.xmldoc.filehref:
                    if self.datacollectmode and self.xmldoc.hasattr(dest,"autodcfilename"):
                        use_autodcfilename=True
                        pass
                    elif self.xmldoc.hasattr(dest,"autofilename"):
                        use_autofilename=True
                        pass
                    pass
                
                if not self.xmldoc.filehref and (use_autofilename or use_autodcfilename):
                    #sys.stderr.write("ok_set_filename looking for needed unchecked items\n")
                    
                    # if self.datacollect_explog is not None and not self.autosaved and "autofilename" in dest.attrib:
                    # once none of the titles in unchecked checkitems are contained
                    # in the autofilename string, it is OK to set the name and autosave
                    checkitems=self.xmldoc.xpath("chx:checkitem")
            
                    boxcnt=0
                    while boxcnt < len(checkitems):
                        if self.xmldoc.getattr(checkitems[boxcnt],"checked","false")=="true":
                            boxcnt+=1
                            continue
                
                        title=self.xmldoc.getattr(checkitems[boxcnt],"title",checkitems[boxcnt].text).strip()
                
                        if ((use_autofilename and (title in self.xmldoc.getattr(dest,"autofilename")))
                            or (use_autodcfilename and title in self.xmldoc.getattr(dest,"autodcfilename"))):
                            #sys.stderr.write("ok_set_filename found needed unchecked items\n")
                    
                            break # prevent autosave at this time
                
                        boxcnt+=1
                        pass

                    if boxcnt==len(checkitems):
                        # if we went all the way to the end of the previous loop
                        # then it's OK to set the filename and autosave if 
                        # in datacollect mode
                        #  self.xmldoc.unlock_rw()   (now unlocked by finally block)

                        OK=True
                        
                        pass
                    pass
                pass
            pass
        except:
            raise
        finally:
            self.xmldoc.unlock_ro()
            pass
        
        
        if OK: 

            # Make final check whether this makes sense -- is there
            # a measnum conflict???
            if self.datacollectmode and (self.done_is_save_measurement or self.has_save_measurement_step or self.part_of_a_measurement):
                (measnum_in_xlg,beyond_latest_measnum)=self.check_measnum_status()

                if measnum_in_xlg or not(beyond_latest_measnum):
                    # Ask user if OK to proceed
                    if hasattr(gtk,"MessageType") and hasattr(gtk.MessageType,"QUESTION"):
                        # gtk3
                        Dialog=gtk.MessageDialog(type=gtk.MessageType.QUESTION,buttons=gtk.ButtonsType.YES_NO)
                        pass
                    else : 
                        Dialog=gtk.MessageDialog(type=gtk.MESSAGE_QUESTION,buttons=gtk.BUTTONS_YES_NO)
                        pass
                    if measnum_in_xlg:
                        statusmsg="already used in the experiment log."
                        pass
                    else: 
                        statusmsg="less than the most recent Measnum."
                        pass

                    Dialog.set_markup(("Warning: Measurement number (Measnum=%d) is " % (self.paramdb["measnum"].dcvalue.value()))+ statusmsg + "\nOK to use this Measnum and assign a filename to this checklist anyway?")
                    result=Dialog.run()
                    Dialog.destroy() 
                    if result==RESPONSE_YES:
                        OK=True
                    else:
                        OK=False
                    pass
                pass
            pass
        return OK


    def requesteddest(self):

        #import pdb as pythondb
        #pythondb.set_trace()
        
        self.xmldoc.lock_ro()
        try :

            # Obtain dest tag
            desttag=self.xmldoc.xpathsingle("chx:dest",default=None)

            
            # obtain dest from desthref constructor parameter by preference
            desthref=None
            if self.desthref is not None:
                desthref=self.desthref
                pass
            else:
                # In datacollect mode use paramdb
                if self.datacollectmode:
                    desthref=self.paramdb["dest"].dcvalue
                    pass
                else:
                    # Grab dest from the xlink:href in the desttag, if present
                    if desttag is not None:
                        desthref=hrefv.fromxml(self.xmldoc,desttag)
                        pass
                    pass
                pass

            # if all of the above fails, strip file part off of context
            # of our current file.
            
            if desthref is None or desthref.isblank():
                desthref=self.xmldoc.getcontexthref().leafless()
                pass
            pass
        finally:
            self.xmldoc.unlock_ro()
            pass

        
        return desthref
    
    def requestedfilename(self):

        self.xmldoc.lock_ro()
        try :


            # Obtain dest tag
            desttag=self.xmldoc.xpathsingle("chx:dest",default=None)

            
            # Now determine the desired filename, if possible
            contextnode=self.xmldoc.find(".")

            # Use "autofilename" attribute, but override with
            # "autodcfilename" attribute if it is present and we
            # are in datacollectmode
            autofilename_attrib="autofilename"
            if self.datacollectmode and self.xmldoc.hasattr(desttag,"autodcfilename"):
                autofilename_attrib="autodcfilename"
                pass


            # use autofilename attribute if present
            if self.xmldoc.hasattr(desttag,autofilename_attrib):
                
                # filename can use POSIX path separators if desired
                filename=self.xmldoc.xpath(self.xmldoc.getattr(desttag,autofilename_attrib),contextnode=contextnode,extensions=self.paramdb_ext.extensions) # extension allows use of dc:paramdb(string) to extract xml representation of paramdb entry
                pass
            else:
                # build requestedfilename from orighref
                origbasename=self.orighref.get_bare_unquoted_filename()
                (origbase,origext)=posixpath.splitext(origbasename)
                assert(origext != ".chf" and origext != "plf")
                if origext==".plx":
                    filename=origbase+".plf"
                    pass
                else:
                    filename=origbase+".chf"
                    pass
                pass
            pass
        finally:
            self.xmldoc.unlock_ro()
            pass

        
        return filename

    def setchecklistfilename(self):
        # should have already passed ok_set_filename test before calling this!!!

        #import pdb as pythondb
        #pythondb.set_trace()

        if self.readonly:
            return 

        self.xmldoc.shouldbeunlocked()
        
        desthref=self.requesteddest()
        filename=self.requestedfilename()
        
        if self.datacollectmode and (self.done_is_save_measurement or self.has_save_measurement_step or self.part_of_a_measurement): 
            # automatically set the filename

            # assert("measnum" in self.private_paramdb)
            # Make sure current experiment log measnum is in the checklist measnum set

            # assert(self.paramdb["measnum"].dcvalue.value() in self.private_paramdb["measnum"].dcvalue.value())
            
            (filebasename,fileext)=os.path.splitext(filename)
            # cnt=1
            
            if self.done_is_save_measurement or self.has_save_measurement_step: 
                chklistfile="%s-%.4d%s" % (filebasename,self.paramdb["measnum"].dcvalue.value(),fileext)
                chklisthref=hrefv(quote(chklistfile),contexthref=desthref)
                #chklistpath=os.path.join(destdir,chklistfile)
                    
                cnt=1
                while (href_exists(chklisthref)) :

                    chklistfile="%s-%.4d-%d%s" % (filebasename,self.paramdb["measnum"].dcvalue.value(),cnt,fileext)
                    chklisthref=hrefv(quote(chklistfile),contexthref=desthref)
                    #chklistpath=os.path.join(destdir,chklistfile)
                    
                    cnt+=1

                    #if hasattr(gtk,"MessageType") and hasattr(gtk.MessageType,"WARNING"):
                    #    # gtk3
                    #    existsdialog=gtk.MessageDialog(type=gtk.MessageType.ERROR,buttons=gtk.ButtonsType.NONE)
                    #    pass
                    #else : 
                    #    existsdialog=gtk.MessageDialog(type=gtk.MESSAGE_ERROR,buttons=gtk.BUTTONS_NONE)
                    #    pass
                            
                    #existsdialog.set_markup("Error: File %s exists.\nWill not overwrite, but you can manually delete and click Retry" % (chklistpath))
                    #existsdialog.add_button("Retry",1)
                    #existsdialog.add_button("Cancel operation",0)
                
                    #existsdialogval=existsdialog.run()
                
                    #existsdialog.destroy()
                    
                    #if existsdialogval==0:
                    #    # cancel
                    #    return   # calls unlock via finally block
                    pass
                
                pass
            else : 
                # this checklist must be part_of_a_measurement
                assert(self.part_of_a_measurement)
                chklistfile="%s-%.4d%s" % (filebasename,self.paramdb["measnum"].dcvalue.value(),fileext)
                chklisthref=hrefv(quote(chklistfile),contexthref=desthref)
                cnt=0
                    
                while href_exists(chklisthref):
                    cnt+=1
                    
                    chklistfile="%s-%.4d-%.4d%s" % (filebasename,self.paramdb["measnum"].dcvalue.value(),cnt,fileext)
                    chklisthref=hrefv(quote(chklistfile),contexthref=desthref)
                    pass
                
                
                
                
                pass
            
            #sys.stderr.write("before rw_lc=%d\n" % (self.xmldoc.rw_lockcount))
            oldreadonly=self.readonly
            self.set_readonly(True,dont_switch_xmldoc_mode=True) # Set readonly to disconnect from file
            #sys.stderr.write("intermed rw_lc=%d\n" % (self.xmldoc.rw_lockcount))
            oldhref=self.xmldoc.get_filehref()
            self.xmldoc.set_href(chklisthref)
            #sys.stderr.write("after rw_lc=%d\n" % (self.xmldoc.rw_lockcount))
            self.set_readonly(oldreadonly) # reconnect to file if applicable
            #sys.stderr.write("wayafter rw_lc=%d\n" % (self.xmldoc.rw_lockcount))
            
            self.gladeobjdict["SaveButton"].set_sensitive(True)


            # xlink:href updates now automatic!
            # if self.xmldoc.hasattr(None,"parent"):
            #    # if we have a parent attribute, update it relative to the new filename
            # if oldfilename is None:
            #        reffilename=self.pre_reset_filename
            #        pass
            #    else: 
            #        reffilename=oldfilename
            #        pass
            #    
            #    if reffilename is not None:
            #        self.set_parent(self.xmldoc.getcontextdir(),canonicalize_path.canonicalize_relpath(os.path.split(reffilename)[0],self.xmldoc.getattr(None,"parent")))
            #        pass
            #    else: 
            #        self.set_parent(self.xmldoc.getcontextdir(),self.xmldoc.getattr(None,"parent"))
            #pass
            #    pass
            
            #self.xmldoc.autoflush=True
            
            # WARNING: filenamenotify may call requestval_sync which runs sub-mainloop
            for (filenamenotify,fnargs,fnkwargs) in  self.filenamenotify: 
                filenamenotify(self,self.orighref,chklisthref,oldhref,*fnargs,**fnkwargs)
                pass
            
            # enable save button
            self.gladeobjdict["SaveButton"].set_sensitive(True)
                
            self.chklistfile=chklistfile  # store for convenience
                
            # set filename field at bottom of window
            self.private_paramdb["defaultfilename"].requestvalstr_sync(chklisthref.get_bare_unquoted_filename()) 
            
            self.set_window_title()

            pass
        else :
            # not datacollectmode or datacollectmode but not part_of_a_measurement, done_is_save_measurement, etc. 
                
            # add a numeric suffix if this file already exists.
            (filebasename,fileext)=posixpath.splitext(filename)
            cnt=0
            
            oldhref=self.xmldoc.get_filehref()
            
            chklistfile=filename
            chklisthref=hrefv(quote(chklistfile),contexthref=desthref)
            
            #import pdb as pythondb
            #pythondb.set_trace()

            while href_exists(chklisthref):
                cnt+=1
                
                chklistfile="%s-%.4d%s" % (filebasename,cnt,fileext)
                chklisthref=hrefv(quote(chklistfile),contexthref=desthref)
                pass
            
            #sys.stderr.write("newfilename=%s\n" % (newfilename))
                
            try : 
                
                oldreadonly=self.readonly
                self.set_readonly(True,dont_switch_xmldoc_mode=True) # Set readonly to disconnect from file
                oldhref=self.xmldoc.get_filehref()
                self.xmldoc.set_href(chklisthref)
                self.set_readonly(oldreadonly) # reconnect to file if applicable
                pass
            except: 
                (exctype, excvalue) = sys.exc_info()[:2] 
                tback=traceback.format_exc()
                ErrorDialog("Exception assigning filename %s to checklist; output may not be saved" % (str(chklisthref)),exctype,excvalue,tback)
                chklisthref=None
                # self.xmldoc.setfilename(None)
                
                pass
            
            self.gladeobjdict["SaveButton"].set_sensitive(True)
            
            # if self.xmldoc.hasattr(None,"parent"):
            #    # if we have a parent attribute, update it relative to the new filename
            # xlink:href updates now automatic
            #self.set_parent(self.xmldoc.getcontextdir(),self.xmldoc.getattr(None,"parent"))
            #    pass

            #self.xmldoc.autoflush=True
            
            # WARNING: filenamenotify may call requestval_sync which runs sub-mainloop
            for (filenamenotify,fnargs,fnkwargs) in self.filenamenotify: 
                filenamenotify(self,self.orighref,chklisthref,oldhref,*fnargs,**fnkwargs)
                pass
            self.chklistfile=chklistfile  # store for convenience
            
            # set filename field at bottom of window
            self.private_paramdb["defaultfilename"].requestvalstr_sync(chklistfile) 

            if chklisthref is not None:
                # unless the filename assignment failed
                self.gladeobjdict["SaveButton"].set_property("label","Done")
                pass
            pass

        
        pass
    


    def handle_check(self,obj,boxnum):
        
        if self.readonly:
            return

        measname_mismatch_ok=False

        if self.datacollectmode:
            # verify measnum match, merge in if necessary
            
            # extract measnum        
            if self.paramdb["measnum"].dcvalue.isblank():
                # Set to 0 if blank
                self.paramdb["measnum"].requestval_sync(integerv(0))
                pass
            curmeasnum=self.paramdb["measnum"].dcvalue.value()
            
            # see if we need to give this checklist a measnum
            if self.steps[boxnum].gladeobjdict["checkbutton"].get_property("active"):
                if "measnum" in self.private_paramdb and self.private_paramdb["measnum"].dcvalue.isblank():
                    # Needs checklist measnum set 
              
                    # sys.stderr.write("Requesting measnum=%d\n" % (curmeasnum))
                    self.private_paramdb["measnum"].requestval_sync(integersetv(curmeasnum))
                    pass
                elif "measnum" in self.private_paramdb : 
                    # if current measnum is not in the checklist set
                    if curmeasnum not in self.private_paramdb["measnum"].dcvalue:
                        # If there are no more measurement steps (or done_is_save_measurement) in this checklist, 
                        # let it be and do nothing. 
                        #
                        # If there are more measurement steps, then we need to add 
                        # to the checklist measnum set
                        # (THIS IS THE ONLY PLACE WHERE A CHECKLIST CAN GET MORE
                        # THAN ONE MEASNUM)
                        
                        # check if we have had a previous savemeasurement step
                        prior_savemeasurement_step=False
                        for stepnum in range(boxnum+1):
                            if self.parsedchecklist[stepnum].cls=="savemeasurement":
                                prior_savemeasurement_step=True
                                pass
                            pass
                        
                        # first check that no boxes beyond this point have been checked yet. 
                        found_checked=False
                        for stepnum in range(boxnum+1,len(self.steps)):
                            if self.steps[stepnum].gladeobjdict["checkbutton"].get_active():
                                found_checked=True
                                pass
                            pass
                        
                        if not found_checked and prior_savemeasurement_step and self.done_is_save_measurement: 
                            self.private_paramdb["measnum"].requestval_sync(self.private_paramdb["measnum"].dcvalue.union(integersetv(curmeasnum)))
                            pass

                        
                        
                        # go through remaining steps to see if there are any 
                        # savemeasurementsteps 

                        
                        if not found_checked and prior_savemeasurement_step:
                            for stepnum in range(boxnum+1,len(self.steps)):
                                if self.parsedchecklist[stepnum].cls=="savemeasurement":
                                    # there is a remaining savemeasurement step,
                                    # and no following boxes are checked
                                    # and there is a prior save measurement step
                                    # so we add the new measurement number
                                    # to the set 
                                    self.private_paramdb["measnum"].requestval_sync(self.private_paramdb["measnum"].dcvalue.union(integersetv(curmeasnum)))

                                    pass
                                pass
                            pass
                    
                        if prior_savemeasurement_step:
                            # if we have a prior measurement step
                            # then we either unioned in the current measnum
                            # or its OK for the measname to mismatch for
                            # the last few checks at the bottom of the list
                            measname_mismatch_ok=True
                            pass
                        pass
                    pass
                pass
            else: 
                # checkbox removed.... mismatch is OK
                measname_mismatch_ok=True
                pass
            pass

        self.steps[boxnum].handle_check(self.steps[boxnum].gladeobjdict["checkbutton"].get_property("active"))
        
        self.xmldoc.lock_rw()
        
        try : 
            # print "boxnum=%d, active=%s" % (boxnum,self.steps[boxnum].gladeobjdict["checkbutton"].get_property("active"))
            if obj.get_property("active"):
                #if (boxnum+1 < len(self.steps)): 
                #    self.steps[boxnum+1].gladeobjdict["steptemplate"].set_expanded(True)
                #    pass
            
                #if (boxnum-2 >= 0): 
                #    self.steps[boxnum-2].gladeobjdict["steptemplate"].set_expanded(False)
                #
                #    pass
                pass
        
            xmltag=self.xmldoc.restorepath(self.steps[boxnum].xmlpath)
            
            if self.steps[boxnum].gladeobjdict["checkbutton"].get_property("active"):
                self.xmldoc.setattr(xmltag,"checked","true")
                checked=True
                self.addlogentry("Item %d Marked Complete" % (boxnum+1),item=str(boxnum+1),action="checked")
                pass
            else :
                self.xmldoc.setattr(xmltag,"checked","false")
                checked=False
                self.addlogentry("Item %d Marked Incomplete" % (boxnum+1),item=str(boxnum+1),action="unchecked")
                pass
        
                
            self.setheadingcolor(boxnum)


            # check if allchecked
            checkitems=self.xmldoc.xpath("chx:checkitem")
        
            boxcnt=0
            while boxcnt < len(checkitems):
                if self.xmldoc.getattr(checkitems[boxcnt],"checked","false") != "true":
                    break
            
                    
                boxcnt+=1            
                pass
        
            if boxcnt==len(checkitems): 
                # all are checked
                self.xmldoc.setattr(self.xmldoc.getroot(),"allchecked","true")
                pass
            else: 
                self.xmldoc.setattr(self.xmldoc.getroot(),"allchecked","false")
                pass
        

                
            pass
        except: 
            raise

        finally:            
            self.xmldoc.unlock_rw()
            pass

        if checked and self.ok_set_filename():
            self.setchecklistfilename()
            pass


        # self.xmldoc.shouldbeunlocked()  # must be unlocked for our changes to be flushed to disk
        

        if self.checkdone():
            # set a color on the SaveButton to indicate done...

            if "gi" in sys.modules: # gtk3  ... currently INOPERABLE
                # !!!*** fixme: Probably should only create newprops once, and then add/remove it and/or enable/disable it
                #newprops=gtk.StyleProperties.new()
                #newprops.set_property("background-color",STATE_NORMAL,self.savebuttonreadycolor)
                #self.gladeobjdict["SaveButton"].get_style_context().add_provider(newprops,gtk.STYLE_PROVIDER_PRIORITY_USER)
                self.gladeobjdict["SaveButton"].override_background_color(STATE_NORMAL,gdk.RGBA.from_color(self.savebuttonreadycolor))
                pass
            else : # gtk2

                newsavestyle=self.gladeobjdict["SaveButton"].get_style().copy()
                newsavestyle.bg[STATE_NORMAL]=self.savebuttonreadycolor
                self.gladeobjdict["SaveButton"].set_style(newsavestyle)
                pass
            pass
        else:

            if "gi" in sys.modules: # gtk3  ... currently INOPERABLE
            # set color to indicate not done
                self.gladeobjdict["SaveButton"].override_background_color(STATE_NORMAL,gdk.RGBA.from_color(self.savebuttonnormalcolor))
                pass
            else: # gtk2
                newsavestyle=self.gladeobjdict["SaveButton"].get_style().copy()
                newsavestyle.bg[STATE_NORMAL]=self.savebuttonnormalcolor
                self.gladeobjdict["SaveButton"].set_style(newsavestyle)
                pass
            pass
        
        pass

    def scroller_reqsize(self,obj,requisition):
        # This is called to set the size of the Scrolled Window. 
        # We override it so as to automatically select the minimum size
        # that fits the content without scrolling
        
        # Get size request from Scrolled Window
        # gtk.ScrolledWindow.do_size_request(self.gladeobjdict["Scroller"],requisition)

        # vprequisition=requisition.copy()
    
        # Get size request from Viewport
        # gtk.Viewport.do_size_request(self.gladeobjdict["ScrollerViewport"],vprequisition)
        
        # print requisition.height, vprequisition.height
        
        # For some reason gtk.Entry asks for a crazy size sometimes (?)
        # Here we bound the request to 200px wide
        #if vprequisition.height > requisition.height:
        #    requisition.height=vprequisition.height
        #    pass
        pass
        
    pass



