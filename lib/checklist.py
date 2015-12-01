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
import string
import numbers
import copy
import traceback
import urllib

if not "gtk" in sys.modules:  # gtk3
    from gi.repository import Gtk as gtk
    from gi.repository import Gdk as gdk
    pass
else : 
    # gtk2
    import gtk
    import gtk.gdk as gdk
    pass

# import pygram

import xmldoc
import canonicalize_path
import checklistdb


import dg_timestamp

from dc_gtksupp import build_from_file
from dc_gtksupp import dc_initialize_widgets
from dc_gtksupp import guistate as create_guistate

from steptemplate import steptemplate
import paramdb2 as pdb
from dc_value import numericunitsvalue as numericunitsv
from dc_value import stringvalue as stringv
from dc_value import hrefvalue as hrefv
from dc_value import accumulatingintegersetvalue as accumulatingintegersetv
from dc_value import accumulatingdatesetvalue as accumulatingdatesetv
from dc_value import integersetvalue as integersetv
from dc_value import integervalue as integerv

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

from widgets.dc_wraplabel import dc_wraplabel



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
    pycode=None
    xmlpath=None  # xmldoc savedpath

    def __init__(self,title=None,cls=None,params=None,pycode=None,xmlpath=None):
        self.title=title
        self.cls=cls
        self.params=params
        
        self.pycode=pycode
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
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0" xmlns:exsl="http://exslt.org/common" extension-element-prefixes="exsl" xmlns:chx="http://thermal.cnde.iastate.edu/checklist">
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
<xsl:template match="chx:br">
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
        Dialog=gtk.MessageDialog(type=gtk.MessageType.ERROR,buttons=gtk.ButtonsType.OK)
        pass
    else : 
        Dialog=gtk.MessageDialog(type=gtk.MESSAGE_ERROR,buttons=gtk.BUTTONS_OK)
        pass
        
    # sys.stderr.write("Markup is Error: %s.\n%s: %s\n\nTraceback:\n%s" % (msg,str(exctype),xml.sax.saxutils.escape(unicode(excvalue)),xml.sax.saxutils.escape(tback)))
    Dialog.set_markup("Error: %s.\n%s: %s\n\nTraceback:\n%s" % (msg,xml.sax.saxutils.escape(exctype.__name__),xml.sax.saxutils.escape(str(excvalue)),xml.sax.saxutils.escape(tback)))
    Dialog.run()
    Dialog.destroy()
    
    
    pass



class checklist(object):

    closed=None # Set to True once this checklist is closed and should be considered invalid
    gladeobjdict=None
    gladebuilder=None
    parsedchecklist=None
    io=None
    steps=None
    xmldoc=None
    origfilename=None
    paramdb=None
    paramdb_ext=None # dc:paramdb() extension function
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
    grayed_out=None   # Checklist is grayed out (after done is pressed, before reset)
    pre_reset_filename=None # last real filename from before a reset
    
    shared_notes=None # flag to indicate whether the notes field is shared or not. Automatically set with done_is_save_measurement
    specimen_disabled=None  # if True, then we don't show a specimen widget and we don't sync the specimen field
    specimen_perfby_date_in_private_paramdb=None



    savebuttonnormalcolor=None # GdkColor
    savebuttonreadycolor=None  # GdkColor

    filenamenotify=None # list of (function to call when the checklist gets a name...,*args,**kwargs)  used for example by runcheckliststep. Called as filenamenotify[idx][0](checklist,origfilename,dest,fname,*filenamenotify[idx][1],**filenamenotify[idx][2])
    donenotify=None
    resetnotify=None
    closenotify=None

    
    def __init__(self,origfilename,paramdb,datacollect_explog=None,datacollect_explogwin=None,destoverride=None):


        self.closed=False
        self.paramdb=paramdb
        self.private_paramdb=pdb.paramdb(None) # could pass dgio as parameter to allow private parameters to interact with dataguzzler
        self.private_paramdb.addparam("clinfo",stringv,build=lambda param: xmldoc.synced(param))
        self.private_paramdb.addparam("dest",stringv,build=lambda param: xmldoc.synced(param))
        self.private_paramdb.addparam("notes",stringv,build=lambda param: xmldoc.synced(param))

        self.private_paramdb.addparam("defaultfilename",stringv)  # defaultfilename maps to the filename entry field at the bottom of the checklist window
        self.specimen_perfby_date_in_private_paramdb=False

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
        self.grayed_out=False
        self.shared_notes=False
        self.filenamenotify=[]
        self.donenotify=[]
        self.resetnotify=[]
        self.closenotify=[]
        

        
        (self.gladeobjdict,self.gladebuilder)=build_from_file(os.path.join(thisdir,"checklist.glade"))


        if not "gtk" in sys.modules: # gtk3
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


        self.origfilename=origfilename
        

        if os.path.splitext(origfilename)[1]!=".chf" and os.path.splitext(origfilename)[1]!=".plf":
        
            # hide the file -- prevent locking, etc. by reading it from a file object
            fh=open(origfilename,"rb")
            self.xmldoc=xmldoc.xmldoc(None,None,None,FileObj=fh,use_locking=True,contextdir=os.path.split(origfilename)[0],debug=True) # !!!*** can improve performance once debugged by setting debug=False
            fh.close()
            
            # absolutize all relative xlink:href links
            self.xmldoc.setcontextdir(os.path.split(origfilename)[0],force_abs_href=True)
            self.xmldoc.merge_namespace(None,"http://thermal.cnde.iastate.edu/checklist")     
            self.xmldoc.setattr(".", "origfilename", origfilename)
            # log start timestamp
            
            self.logstarttimestamp()
            
            #self.xmldoc.setfilename(None)  # prevent auto-flushing, etc. unless this is a "filled" file
            pass
        else : 
            #import pdb as pythondb
            try:
                self.xmldoc=xmldoc.xmldoc(origfilename,None,None,use_locking=True) # !!!*** can improve performance once debugged by setting debug=False
            except IOError:
                (exctype, excvalue) = sys.exc_info()[:2] 
                tback=traceback.format_exc()
                #pythondb.set_trace()
                ErrorDialog("Error Loading Checklist",exctype,excvalue,tback)
            self.xmldoc.merge_namespace(None,"http://thermal.cnde.iastate.edu/checklist")
            try:
                self.origfilename = self.xmldoc.getattr(".", "origfilename")
            except IndexError:
                sys.stderr.write("Warning:  Original Filename Not Set in Filled Checklist\n")     
    

            self.chklistfile=os.path.basename(origfilename)

            pass
        
        try :  # try...catch...finally block for handling lock we just acquired with xmldoc()

            # do we have a <chx:parent> tag?
            parentlist=self.xmldoc.xpath("chx:parent")
            if len(parentlist) == 0:
                # add a parent tag so we don't 
                # end up messing with tag positioning later
                self.xmldoc.addelement(self.xmldoc.getroot(),"chx:parent")
                pass

            if self.chklistfile is not None:
                # window title is filename if we are actively updating the file
                self.gladeobjdict["CheckListWindow"].set_title(os.path.split(origfilename)[-1])
                
                #self.xmldoc.autoflush=True
                #print "Auto flush mode!!!"
            
                
                # Evalute "dest" even though the primary code for this is below
                curdest=destoverride
                if curdest is None and "dest" in self.paramdb:
                    curdest=unicode(self.paramdb["dest"].dcvalue)
                    pass
                if curdest is None:
                    curdest="."
                    pass

                if curdest.endswith(os.path.sep):
                    curdest=curdest[:-1]
                    pass
                
                curdest_abspath=canonicalize_path.canonicalize_path(curdest)

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
            
        if self.chklistfile is not None:
            chklistfile_abspath=os.path.abspath(self.chklistfile)
            (chklistfile_absdir,chklistfile_absfile)=os.path.split(chklistfile_abspath)
            # WARNING: filenamenotify may call requestval_sync which runs sub-mainloop
            # ***!!! Possible bug because shouldn't do this with stuff locked
            for (filenamenotify,fnargs,fnkwargs) in self.filenamenotify:
                if chklistfile_absdir==curdest_abspath:
                    filenamenotify(self,self.origfilename,curdest,chklistfile_absfile,None,*fnargs,**fnkwargs)
                    pass
                else :
                    # must supply absolute path
                    filenamenotify(self,self.origfilename,curdest,chklistfile_abspath,None,*fnargs,**fnkwargs)
                    pass
                pass
            pass
        
        self.xmldoc.lock_rw()  
        try:
        
        
            checklisttag=self.xmldoc.find(".")


            # datacollect mode: clinfo and dest are not editable; can not 
            # explicitly save
            if self.datacollectmode:
                #self.gladeobjdict["ChecklistEntry"].set_editable(False)
                self.gladeobjdict["DestEntry"].set_editable(False)

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


                self.gladeobjdict["SaveButton"].connect("clicked",self.handle_done)
                if self.xmldoc.filename is None:
                    self.gladeobjdict["SaveButton"].set_sensitive(False)
                    pass
                else : 
                    self.private_paramdb["defaultfilename"].requestvalstr_sync(self.xmldoc.filename)
                    self.gladeobjdict["SaveButton"].set_sensitive(True)
                
                    pass
            
                pass
            else :
                # Not datacollectmode
                if self.xmldoc.filename is not None: 
                    self.gladeobjdict["SaveButton"].set_property("label","Save")                
                    self.private_paramdb["defaultfilename"].requestvalstr_sync(self.xmldoc.filename)
                    pass


                self.gladeobjdict["SaveButton"].set_sensitive(True)
                self.gladeobjdict["SaveButton"].connect("clicked",self.handle_save)
                #self.gladeobjdict["CheckListWindow"].connect("delete_event",self.handle_quit)
                pass


            # Make sure common tags exist: clinfo, specimen, perfby, date, dest, and notes
            # Important to do this here, lest tag numbering change underneath
            # the various steps and screw with resyncinc. 
        
            destl=self.xmldoc.xpath("chx:dest")
            assert(len(destl) <= 1)
            if len(destl)==0:
                dest=self.xmldoc.insertelement(".",0,"chx:dest")
                pass
            else : 
                dest=destl[0]
                pass
        
            if self.datacollect_explog is not None and not self.xmldoc.hasattr(dest,"autofilename") and not self.xmldoc.hasattr(dest,"autodcfilename"):
                raise ValueError("In datacollect mode, checklist/dest must have an autofilename or autodcfilename attribute to determine autosave filename")
        
            datel=self.xmldoc.xpath("chx:date")
            assert(len(datel) <= 1)
            if len(datel)==0:
                date=self.xmldoc.insertelement(".",0,"chx:date")
                pass
            else : 
                date=datel[0]
                pass
                
            perfbyl=self.xmldoc.xpath("chx:perfby")
            assert(len(perfbyl) <= 1)
            if len(perfbyl)==0:
                perfby=self.xmldoc.insertelement(".",0,"chx:perfby")
                pass
            else : 
                perfby=perfbyl[0]
                pass
        
            specimenl=self.xmldoc.xpath("chx:specimen")
            assert(len(specimenl) <= 1)
            if len(specimenl)==0:
                specimen=self.xmldoc.insertelement(".",0,"chx:specimen")
                pass
            else : 
                specimen=specimenl[0]
                pass
        
        
            clinfol=self.xmldoc.xpath("chx:clinfo")
            assert(len(clinfol) <= 1)
            if len(clinfol)==0:
                clinfo=self.xmldoc.insertelement(".",0,"chx:clinfo")
                pass
            else:
                clinfo=clinfol[0]
                pass
                
            notesl=self.xmldoc.xpath("chx:notes")
            assert(len(notesl) <= 1)
            if len(notesl)==0:
                notes=self.xmldoc.insertelement(".",0,"chx:notes")
                pass
            else:
                notes=notesl[0]
                pass

            self.xmldoc.setattr(".","filled","true")
            # self.xmldoc.flush()  # force flush in case we added elements above. 
                             # (only applies if we are on a .chf file, because
                             # otherwise filename set to None, above)

            checkitems=self.xmldoc.xpath("chx:checkitem")
            self.parsedchecklist=[]
            for curitem in checkitems:
                params={}
                for parameter in self.xmldoc.xpathcontext(curitem,"chx:parameter"):
                    typestr=self.xmldoc.xpathcontext(parameter,"string(@type)")
                    if typestr=="href":
                        paramtype=hrefv # dc_value.hrefvalue
                        pass
                    else: 
                        paramtype=__builtins__[typestr]
                        pass
                    paramname=self.xmldoc.xpathcontext(parameter,"string(@name)")
                    if paramname=="": 
                        raise ValueError("Parameter does not have a name attribute in checklist item %s" % (etree.tostring(curitem,encoding="UTF-8")))
                
                                     
                    if paramname=="description":
                        # try : 
                        params[paramname]=etree.tostring(xml2pango(parameter),encoding='utf-8').decode("utf-8")
                        #    pass
                        # except:
                        #    print "XSLT Error log:\n"+ string.join([ "%s l%d c%d %s\n" % (entry.filename,entry.line,entry.column,str(entry)) for entry in xml2pango.error_log])+"\n"
                        #    raise
                        #    pass
                        
                        # print unicode(xml2pango(parameter))
                        pass
                    else :
                        if paramtype is bool:
                            paramstr=self.xmldoc.xpathcontext(parameter,"string(.)").strip()
                            paramval=False
                            if paramstr.lower()=="true":
                                paramval=True
                                pass
                            params[paramname]=paramval
                            pass
                        elif paramtype is hrefv: # dc_value.hrefvalue
                            params[paramname].fromxml(self.xmldoc,parameter,contextdir=self.xmldoc.getcontextdir())
                        else : 

                            params[paramname]=paramtype(self.xmldoc.xpathcontext(parameter,"string(.)").strip())
                            pass
                        pass
                    pass
                title=self.xmldoc.getattr(curitem,"title",defaultvalue="")

                if len(title)==0:
                    title=curitem.text
                    pass
            
                if title is None: 
                    raise ValueError("No title or content specified in checklist item: %s" % (etree.tostring(curitem,encoding="UTF-8")))
            
                title=title.strip() # strip leading and trailing whitespace
            
                cls=self.xmldoc.getattr(curitem,"class","text")
            
                if cls=="savemeasurement":
                    self.has_save_measurement_step=True
                    pass
            
                # pycode=xml.sax.saxutils.unescape(curitem.xpath("string(pycode)"))
                pycode=self.xmldoc.xpathcontext(curitem,"string(chx:pycode)")
                
                # self.parsedchecklist.append(checkitem(title=xml.sax.saxutils.unescape(curitem.xpath("string(@title)")),cls=curitem.xpath("string(@class)"),params=params,pycode=pycode))

                if not "description" in params:
                    if self.xmldoc.xpathcontext(curitem,"count(chx:description)") > 0:
                        params["description"]=etree.tostring(xml2pango(self.xmldoc.xpathsinglecontext(curitem,"chx:description")),encoding='utf-8').decode('utf-8')
                        pass
                    pass
            
            
                self.parsedchecklist.append(checkitem(title=title,cls=cls,params=params,pycode=pycode,xmlpath=self.xmldoc.savepath(curitem)))
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

            if "dest" in self.paramdb:
                destval=self.paramdb["dest"].dcvalue.value()
                pass
            else: 
                destval="."
                pass


            # if <specimen> has the special value disabled, hide the "specimen" box and set specimen_disabled
            if self.xmldoc.xpathsinglestr("chx:specimen")=="disabled":
                self.gladeobjdict["SpecBox"].hide()
                self.gladeobjdict["SpecBox"].set_no_show_all(True)
                self.specimen_disabled=True
                pass

            
            
            # measnum is in general a set of integers. We only create it now 
            # that we know if we have done_is_save_measurement, has_save_measurement_step or part_of_a_measurement
            if self.done_is_save_measurement or self.has_save_measurement_step or self.part_of_a_measurement: 
                self.private_paramdb.addparam("measnum",integersetv,build=lambda param: xmldoc.synced(param))

                measnuml=self.xmldoc.xpath("dc:measnum")
                assert(len(measnuml) <= 1)
                if len(measnuml)==0:
                    measnumel=self.xmldoc.insertelement(".",0,"dc:measnum")
                    pass
                else : 
                    measnumel=measnuml[0]
                    pass

                
                self.private_paramdb["measnum"].controller.adddoc(self.xmldoc,destval,"dc:measnum")

                self.gladeobjdict["MeasnumEntry"].paramdb=self.private_paramdb
                # print "specimen: "+str(self.paramdb["specimen"])
                

                pass
            else: 
                # Remove MeasnumBox and MeasnumEntry if we are not a datacollect checklist that uses them
                self.gladeobjdict["ParamBox"].remove(self.gladeobjdict["MeasnumBox"])
                del self.gladeobjdict["MeasnumEntry"]
                del self.gladeobjdict["MeasnumBox"]
        
            # connect paramdb (including GUI objects for name, specimen, perfby, date, dest & notes) with XML file

            # IMPORTANT: adddoc() calls here must be matched with remdoc() calls in self.destroy() !!!
        
            self.private_paramdb["clinfo"].controller.adddoc(self.xmldoc,destval,"chx:clinfo")
            ## Tell widget to use private paramdb
            #self.gladeobjdict["ChecklistEntry"].paramdb=self.private_paramdb
            # print "specimen: "+str(self.paramdb["specimen"])

            
            is_done = self.xmldoc.getattr(self.xmldoc.getroot(),"done",defaultvalue="false")=="true"
            if is_done:
                # if checklist is done, specimen, perfby, and date are 
                # in private paramdb and widgets are grayed out 
                self.specimen_perfby_date_in_private_paramdb=True
                if not self.specimen_disabled:
                    self.private_paramdb.addparam("specimen",stringv,build=lambda param: xmldoc.synced(param))
                    self.private_paramdb["specimen"].controller.adddoc(self.xmldoc,destval,"chx:specimen",logfunc=self.addlogentry)
                    pass
                
                # Tell widget to use private paramdb
                self.gladeobjdict["SpecEntry"].paramdb=self.private_paramdb
                self.gladeobjdict["SpecEntry"].set_sensitive(False)

                self.private_paramdb.addparam("perfby",stringv,build=lambda param: xmldoc.synced(param))
                self.private_paramdb["perfby"].controller.adddoc(self.xmldoc,destval,"chx:perfby",logfunc=self.addlogentry)
                # Tell widget to use private paramdb
                self.gladeobjdict["PerfbyEntry"].paramdb=self.private_paramdb
                self.gladeobjdict["PerfbyEntry"].set_sensitive(False)

                self.private_paramdb.addparam("date",accumulatingdatesetv,build=lambda param: xmldoc.synced(param))
                self.private_paramdb["date"].controller.adddoc(self.xmldoc,destval,"chx:date",logfunc=self.addlogentry)
                # Tell widget to use private paramdb
                self.gladeobjdict["DateEntry"].paramdb=self.private_paramdb
                self.gladeobjdict["DateEntry"].set_sensitive(False)
                pass

            else: 
                # ... in master paramdb. Use try...except block 
                # so in case of failure we don't end up with dangling
                # synchronization references. 

                
                
                try: 
                    if not self.specimen_disabled: 
                        self.paramdb["specimen"].controller.adddoc(self.xmldoc,destval,"chx:specimen",logfunc=self.addlogentry)
                        pass
                    self.paramdb["perfby"].controller.adddoc(self.xmldoc,destval,"chx:perfby",logfunc=self.addlogentry)
                    self.paramdb["date"].controller.adddoc(self.xmldoc,destval,"chx:date",logfunc=self.addlogentry)
                    pass
                except: 
                    if not self.specimen_disabled:
                        self.paramdb["specimen"].controller.remdoc(self.xmldoc,"chx:specimen",logfunc=self.addlogentry,precautionary=True)
                        pass

                    self.paramdb["perfby"].controller.remdoc(self.xmldoc,"chx:perfby",logfunc=self.addlogentry,precautionary=True)
                    self.paramdb["date"].controller.remdoc(self.xmldoc,"chx:date",logfunc=self.addlogentry,precautionary=True)
                    raise
                pass



            # print "specimen: "+str(self.paramdb["specimen"])

            self.private_paramdb["dest"].controller.adddoc(self.xmldoc,destval,"chx:dest",logfunc=self.addlogentry)
            # Tell widget to use private paramdb
            self.gladeobjdict["DestEntry"].paramdb=self.private_paramdb


            if not is_done and destoverride is not None: 
                self.private_paramdb["dest"].requestvalstr_sync(destoverride)
                pass
                
                
            if self.done_is_save_measurement or self.has_save_measurement_step:
                self.paramdb["notes"].controller.adddoc(self.xmldoc,destval,"chx:notes",logfunc=self.addlogentry)
                self.shared_notes=True
                pass
            else: 
                # link private notes entry do physical document
                self.private_paramdb["notes"].controller.adddoc(self.xmldoc,destval,"chx:notes",logfunc=self.addlogentry)
                # Tell widget to use private paramdb
                self.gladeobjdict["NotesText"].paramdb=self.private_paramdb
                pass
                
            # tell filename widget to use private paramdb
            self.gladeobjdict["filenameentry"].paramdb=self.private_paramdb



            # set window title to checklist name
            if self.xmldoc.filename is None:  # not using filename for window title
                self.gladeobjdict["CheckListWindow"].set_title(str(self.private_paramdb["clinfo"].dcvalue))
                pass
        
            # if clinfo.text is not None and len(clinfo.text.strip()) > 0:
            #     paramdb["clinfo"].requestvalstr(clinfo.text)
            #     pass
            # paramdb.addnotify("clinfo",lambda param,cond: clinfo.__setattr__("text",str(param.dcvalue)),pdb.param.NOTIFY_NEWVALUE)
            #
            # if specimen.text is not None and len(specimen.text.strip()) > 0:
            #     paramdb["specimen"].requestvalstr(specimen.text)
            #     pass
            # paramdb.addnotify("specimen",lambda param,cond: specimen.__setattr__("text",str(param.dcvalue)),pdb.param.NOTIFY_NEWVALUE)
        

            # if perfby.text is not None and len(perfby.text.strip()) > 0:
            #     paramdb["perfby"].requestvalstr(perfby.text)
            #     pass
            # paramdb.addnotify("perfby",lambda param,cond: perfby.__setattr__("text",str(param.dcvalue)),pdb.param.NOTIFY_NEWVALUE)
        
            # if date.text is not None and len(date.text.strip()) > 0:
            #     paramdb["date"].requestvalstr(date.text)
            #     pass
            # paramdb.addnotify("date",lambda param,cond: date.__setattr__("text",str(param.dcvalue)),pdb.param.NOTIFY_NEWVALUE)
        
            # if dest.text is not None and len(dest.text.strip()) > 0:
            #     paramdb["dest"].requestvalstr(dest.text)
            #     pass
            # paramdb.addnotify("dest",lambda param,cond: dest.__setattr__("text",str(param.dcvalue)),pdb.param.NOTIFY_NEWVALUE)

            # if notes.text is not None and len(notes.text.strip()) > 0:
            #     paramdb["notes"].requestvalstr(notes.text)
            #    # See comment on notes lack-of-custom-widget hack, below
            #     self.gladeobjdict["NotesText"].get_buffer().set_property("text",notes.text)
            #    
            #     pass
            # paramdb.addnotify("notes",lambda param,cond: notes.__setattr__("text",str(param.dcvalue)),pdb.param.NOTIFY_NEWVALUE)
            
            self.build_checklistbox()
            # self.checkdone()
        
            # Set savebutton background to normal condition 
            if not "gtk" in sys.modules: # gtk3
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
            
            # expand first two steps
            # self.steps[0].gladeobjdict["steptemplate"].set_expanded(True)
            # self.steps[1].gladeobjdict["steptemplate"].set_expanded(True)
            
            # expand all steps
            # for step in self.steps:
            #     step.gladeobjdict["steptemplate"].set_expanded(True)
            #    pass

            self.gladebuilder.connect_signals(self)

            # FIXME: We should size the scroller in gtk3 too
            # ... but it seems complicated
            # 1. Need to subclass scroller
            # 2. Replace signal with get_preffered_width() and get_preferred_height virtual functions (see https://developer.gnome.org/gtk3/3.0/ch25s02.html)
            # 3. Virtual functions must be named do_get_preferred. (see http://stackoverflow.com/questions/9496322/overriding-virtual-methods-in-pygobject)
            if "gtk" in sys.modules: 
                # gtk2 only
                self.gladeobjdict["Scroller"].connect("size-request",self.scroller_reqsize)
                pass
            else :
                # self.gladeobjdict["Scroller"].set_property("hscrollbar-policy",gtk.PolicyType.ALWAYS)
                pass
            
            pass
        except: 
            raise
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

        self.xmldoc.shouldbeunlocked()


        pass

    def get_parent(self):
        # returns hrefvalue object or None
        self.xmldoc.lock_ro()

        try:
            root=self.xmldoc.getroot()
            parentl=self.xmldoc.xpathcontext(root,"chx:parent")
            if len(parentl)==0:
                return None
                
            if self.xmldoc.hasattr(parentl[0],"xlink:href"):
                return hrefv.fromxml(self.xmldoc,parentl[0],contextdir=self.xmldoc.getcontextdir())
            else: 
                return None
                
        finally:
            self.xmldoc.unlock_ro()
            pass
        pass

    def set_parent(self,pfcontextdir,parentfile):
        # set <chx:parent> tag of main node, referring to
        # parent checklist
        # NOTE: Can only set a parent when we have a filename ourselves.
        # NOTE: since parent is a relative reference, need to redoit 
        # if we get moved somehow


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
                parenttag=self.xmldoc.addelement(root,"chx:parent")
                pass
                
            if os.path.isabs(parentfile):
                # absolute path
                self.xmldoc.setattr(parenttag,"xlink:href",urllib.pathname2url(parentfile))                
                pass
            else :
                
                # relative path for our parent
                parentpath=canonicalize_path.relative_path_to(self.xmldoc.getcontextdir(),canonicalize_path.canonicalize_relpath(pfcontextdir,parentfile))
                self.xmldoc.setattr(parenttag,"xlink:href",urllib.pathname2url(parentpath))

                pass
            self.xmldoc.setattr(parenttag,"xlink:arcrole","http://thermal.cnde.iastate.edu/linktoparent")

            pass
        finally: 
            self.xmldoc.unlock_rw()
            pass
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
        self.io=guistate.io

        

        # We create our own copy of guistate so we can 
        # have an expanded search directory list that would contain
        # the directory containing the checklist file

        origfiledir=os.path.split(self.origfilename)[0]

        searchdirs=[origfiledir]
        searchdirs.extend(guistate.searchdirs)
        
        newguistate=create_guistate(guistate.io,guistate.paramdb,searchdirs)

                                    
        dc_initialize_widgets(self.gladeobjdict,newguistate)

        for step in self.steps: 
            step.dc_gui_init(newguistate)
            pass


        ## if we have all the information needed to set the filename, go ahead and do it!
        #if self.ok_set_filename():
        #    self.setchecklistfilename()
        #    pass
        

        

        
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

    def build_checklistbox(self): 
        cnt=1

        

        self.xmldoc.lock_rw()
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
            
                step=steptemplate(cnt,item.title,item.cls+"step",params=item.params,checklist=self,xmlpath=item.xmlpath,paramdb=self.paramdb)
            
                self.gladeobjdict["MinorBox"].pack_start(step,True,True,0)
                
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
            self.xmldoc.unlock_rw()
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
        

        if self.xmldoc.filename is not None:
            self.pre_reset_filename=self.xmldoc.filename
            pass

        # Eliminate current name so it can be re-set
        self.xmldoc.setfilename(None)

        # set filename field at bottom of window
        self.private_paramdb["defaultfilename"].requestvalstr_sync("") 

        self.xmldoc.autoflush=False
        self.chklistfile=None


        # make any notifications
        # WARNING: resetnotify may call requestval_sync which runs sub-mainloop
        # cnt=0
        for (resetnotify,rnargs,rnkwargs) in self.resetnotify:
            #sys.stderr.write("cnt=%d\n" % (cnt))
            resetnotify(self,self.pre_reset_filename,*rnargs,**rnkwargs)
            #cnt+=1
            pass



        if "measnum" in self.private_paramdb:# reset checklist measnum entry to the empy set
            self.private_paramdb["measnum"].requestval_sync(integersetv(set([])))
            #sys.stderr.write("chklist measnum=%s; paramdb measnum=%s\n" % (str(self.private_paramdb["measnum"].dcvalue),str(self.paramdb["measnum"].dcvalue)))
            pass
        

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
        


            # un-gray out all of the checkboxes (in case user already hit 'done'
            for boxnum in range(len(self.steps)):
                checkbutton=self.steps[boxnum].gladeobjdict["checkbutton"]
                checkbutton.set_sensitive(True)
                pass
        
            # un-gray out notes entry
            self.gladeobjdict["NotesText"].start()

            self.grayed_out=False
            
            # reset window title to checklist name
            self.gladeobjdict["CheckListWindow"].set_title(str(self.private_paramdb["clinfo"].dcvalue))

            # clear notes
            if self.shared_notes:
                self.paramdb["notes"].requestvalstr_sync("")
                pass
            else :
                self.private_paramdb["notes"].requestvalstr_sync("")
                pass
            
            # reset checklist log
            log=self.getlog()
            
            logentries=list(log) # get list of children of checklist log
            for logentry in logentries: 
                log.remove(logentry)
                pass
            
            self.addlogentry("Reset checklist",action="reset")
            self.logstarttimestamp()

            
            if self.done_is_save_measurement or self.has_save_measurement_step:
                # clear name of checklist file in paramdb
                ###!!!*** possible bug: Should measchecklist param be private? 
                self.paramdb["measchecklist"].requestvalstr_sync("")         
                pass
            
            if not self.datacollectmode:
                # un-gray out done button unless we are in datacollect mode
                # (in datacollect mode cannot be sensitive until the filename
                # is picked) 
                self.gladeobjdict["SaveButton"].set_sensitive(True)
                
                pass
            pass
        except: 
            raise

        finally:
            
            self.xmldoc.unlock_rw()
                       
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

        if not self.checknotcurrent():
            return
            

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
            if os.path.isabs(self.origfilename):
                measchecklist_context=None # use absolute path
            else: 
                measchecklist_context=self.xmldoc.getcontextdir()
                pass
            self.paramdb["measchecklist"].requestval_sync(hrefv.frompath(measchecklist_context,self.origfilename))
            
            autoexps=[]
            for autoexp in self.xmldoc.xpath("chx:checkitem/dc:autoexp"):
            
                aecopy=copy.deepcopy(autoexp)
                # sys.stderr.write("\n\ngot aecopy: %s\n" % (etree.tostring(aecopy)))
                title=self.xmldoc.xpathcontext(autoexp,"string(../@title)")
                if len(title)==0:
                    title=self.xmldoc.xpathcontext(autoexp,"string(..)")
                    pass
                title=title.strip() # strip whitespace
            
                # have to use low-level lxml code here because aecopy is not tied to any xmldoc yet.
                aecopy.attrib["title"]=title
            
                autoexps.append(aecopy)                
            
                pass
        
            # main paramdb measnum should be one of the measnums in the set 
            # that is our private_paramdb measnum
            #assert(self.paramdb["measnum"].dcvalue.value() in self.private_paramdb["measnum"].dcvalue.value())
            self.datacollect_explog.recordmeasurement(self.paramdb["measnum"].dcvalue.value(),self.paramdb["dest"].dcvalue.value(),clinfo=clinfo,cltitle=cltitle,extrataglist=autoexps)
            # add in any <dc:autoexp>s with their <dc:automeas>s from the checklist 
            # sys.stderr.write("\n\ngot meastag: %s\n" % (etree.tostring(meastag)))
            pass
        except:
            raise
        finally:
            self.xmldoc.unlock_rw()
            pass

        pass
    
    def handle_done(self,event):
        # This is the save button, in datacollect mode. It makes all
        # the checkitems insensitive and clears the filename

        #contextdir=os.path.join(os.path.split(self.xmldoc.filename)[0],"..")

        if not self.checknotcurrent():
            return

        #checklistdb.print_checklists(contextdir,self.paramdb,"checklists")

        #sys.stderr.write("handle_done()\n")

        self.xmldoc.shouldbeunlocked()

        if not self.verify_save():
            return
        
        try : 

            # sys.stderr.write("handle_done() try block. done_is_save_measurement=%s\n" % (str(self.done_is_save_measurement)))

            self.xmldoc.lock_rw()
            try : 
                # set done attribute of <checklist> tag
                self.xmldoc.setattr(self.xmldoc.getroot(),'done','true')
            finally:
                self.xmldoc.unlock_rw()
                pass

            #import pdb as pythondb
            #pythondb.set_trace()
                
                
            if self.done_is_save_measurement:
                # sys.stderr.write("handle_done() saving measurement\n")
                self.save_measurement()
                pass
            # All lockcounts should be zero now!
            self.xmldoc.shouldbeunlocked()

            #checklistdb.print_checklists(contextdir,self.paramdb,"checklists")


            # self.xmldoc.flush() # Make sure everything written


            for (donenotify,dnargs,dnkwargs) in self.donenotify: 
                donenotify(self,self.xmldoc.filename,*dnargs,**dnkwargs)
                pass

            self.grayed_out=True
            self.pre_reset_filename=self.xmldoc.filename

            #sys.stderr.write("Notifications done\n")
            #checklistdb.print_checklists(contextdir,self.paramdb,"checklists")


            self.xmldoc.setfilename(None) #  Inhibit future writes
                


            # if this is a done_is_save_measurement checklist, need to increment
            # measnum
            if self.done_is_save_measurement: 
                self.paramdb["measnum"].requestval_sync(integerv(self.paramdb["measnum"].dcvalue.value()+1))
                pass

            
            # gray out all of the checkboxes
            for boxnum in range(len(self.steps)):
                checkbutton=self.steps[boxnum].gladeobjdict["checkbutton"]
                checkbutton.set_sensitive(False)
                pass
            
            # gray out notes entry
            self.gladeobjdict["NotesText"].stop()
            
            if self.done_is_save_measurement or self.has_save_measurement_step:
                # clear out notes -- ready for next measurement
                self.paramdb["notes"].requestvalstr_sync("") 
                pass
                
            #sys.stderr.write("grayed out\n")
            #checklistdb.print_checklists(contextdir,self.paramdb,"checklists")

            self.xmldoc.lock_rw()
            try : 
                # clear done attribute of <checklist> tag
                if self.xmldoc.hasattr(self.xmldoc.getroot(),"done"):
                    self.xmldoc.remattr(self.xmldoc.getroot(),"done")
            finally:
                self.xmldoc.unlock_rw()
                pass

            #sys.stderr.write("cleared out\n")
            #checklistdb.print_checklists(contextdir,self.paramdb,"checklists")
            
            
            # gray out done button
            self.gladeobjdict["SaveButton"].set_sensitive(False)
            pass
        except : 
            (exctype, excvalue) = sys.exc_info()[:2] 
            tback=traceback.format_exc()
            ErrorDialog("Exception handling done condition; output may not be saved",exctype,excvalue,tback)
            pass
        
        pass

    def handle_save(self,event):

        if not self.datacollectmode and self.xmldoc.filename is not None:
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
        Chooser.set_current_name(str(self.private_paramdb["defaultfilename"].dcvalue))
        Chooser.set_do_overwrite_confirmation(True)

        if self.origfilename.endswith(".plx") or self.origfilename.endswith(".plf"):
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
        
        if response==RESPONSE_OK:

            # print "Saving..."
            
            self.xmldoc.shouldbeunlocked()

            oldfilename=self.xmldoc.filename
            self.xmldoc.setfilename(name,force_abs_href=True)
            # WARNING: filenamenotify may call requestval_sync which runs sub-mainloop

            self.xmldoc.lock_rw()
            try: 
                destl=self.xmldoc.xpath("chx:dest")
                assert(len(destl) == 1)
                dest=destl[0]
                

                if self.xmldoc.hasattr(None,"parent"):
                    # if we have a parent attribute, update it relative to the new filename
                    self.set_parent(self.xmldoc.getcontextdir(),self.xmldoc.getattr(None,"parent"))
                    pass
                pass
            finally:
                self.xmldoc.unlock_rw()
                pass


            for (filenamenotify,fnargs,fnkwargs) in self.filenamenotify:
                
                filenamenotify(self,self.origfilename,dest,name,oldfilename,*fnargs,**fnkwargs)
                pass
            
            

            # set window title
            self.gladeobjdict["CheckListWindow"].set_title(os.path.split(name)[-1])
            
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

        if "dest" in self.paramdb:
            destval=self.paramdb["dest"].dcvalue.value()
            pass
        else: 
            destval="."
            pass
            

        self.private_paramdb["clinfo"].controller.remdoc(self.xmldoc,destval,"chx:clinfo")

        if self.specimen_perfby_date_in_private_paramdb:
            if not self.specimen_disabled: 
                self.private_paramdb["specimen"].controller.remdoc(self.xmldoc,destval,"chx:specimen",logfunc=self.addlogentry)
                pass
            self.private_paramdb["perfby"].controller.remdoc(self.xmldoc,destval,"chx:perfby",logfunc=self.addlogentry)
            self.private_paramdb["date"].controller.remdoc(self.xmldoc,destval,"chx:date",logfunc=self.addlogentry)

            pass
        else: 

            if not self.specimen_disabled: 
                self.paramdb["specimen"].controller.remdoc(self.xmldoc,destval,"chx:specimen",logfunc=self.addlogentry)
                pass
            self.paramdb["perfby"].controller.remdoc(self.xmldoc,destval,"chx:perfby",logfunc=self.addlogentry)
            self.paramdb["date"].controller.remdoc(self.xmldoc,destval,"chx:date",logfunc=self.addlogentry)
            pass

        self.private_paramdb["dest"].controller.remdoc(self.xmldoc,destval,"chx:dest",logfunc=self.addlogentry)

        #notes=self.xmldoc.xpath("chx:notes")[0]
        #if "shared" in notes.attrib and notes.attrib["shared"]=="true":
        if self.shared_notes: 
            self.paramdb["notes"].controller.remdoc(self.xmldoc,destval,"chx:notes",logfunc=self.addlogentry)
            pass
        else: 
            # unlink private notes entry from physical document
            self.private_paramdb["notes"].controller.remdoc(self.xmldoc,destval,"chx:notes",logfunc=self.addlogentry)
            pass

        # unlink measnum from private paramdb
        if "measnum" in self.private_paramdb: 
            self.private_paramdb["measnum"].controller.remdoc(self.xmldoc,destval,"dc:measnum")
            pass
            

        self.closed=True


        self.getwindow().hide()
        self.getwindow().destroy()
        del self.gladeobjdict
        del self.gladebuilder
        del self.parsedchecklist
        self.io=None

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
    
    
    
    def ok_set_filename(self):
        # Return whether enough checkboxes have been checked that
        # it's OK to set the filename (and we still need to)

        
        #sys.stderr.write("ok_set_filename()\n")

        if self.xmldoc.filename is not None:
            return False

        # if we are in datacollectmode and done_is_save_measurement, has_save_measurement_step, or part_of_a_measurement, then we use the measnum in the filename so we need a valid measnum before we can set the filename
        if self.datacollectmode and (self.done_is_save_measurement or self.has_save_measurement_step or self.part_of_a_measurement):
            if self.paramdb["measnum"].dcvalue.isblank():
                #sys.stderr.write("ok_set_filename nned measnum\n")

                return False
            pass
        


        self.xmldoc.lock_rw()
        try: 
            destl=self.xmldoc.xpath("chx:dest")
            assert(len(destl) == 1)
            dest=destl[0]
            
            use_autodcfilename=False
            use_autofilename=False
            
            if not self.xmldoc.filename:
                if self.datacollectmode and self.xmldoc.hasattr(dest,"autodcfilename"):
                    use_autodcfilename=True
                    pass
                elif self.xmldoc.hasattr(dest,"autofilename"):
                    use_autofilename=True
                    pass
                pass

            if not self.xmldoc.filename and (use_autofilename or use_autodcfilename):
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
                    return True
                pass
            pass
        except:
            raise
        finally:
            self.xmldoc.unlock_rw()
            pass
        return False


    def requestedfilename(self):

        self.xmldoc.lock_ro()
        try : 
            dest=self.xmldoc.xpathsingle("chx:dest")


            contextnode=self.xmldoc.find(".")
        
            autofilename_attrib="autofilename"
            if self.datacollectmode and "autodcfilename" in dest.attrib:
                autofilename_attrib="autodcfilename"
                pass

            filename=self.xmldoc.xpath(self.xmldoc.getattr(dest,autofilename_attrib),contextnode=contextnode,extensions=self.paramdb_ext.extensions) # extension allows use of dc:paramdb(string) to extract xml representation of paramdb entry
            pass
        except: 
            raise
        finally:
            self.xmldoc.unlock_ro()
            pass

        
        return filename

    def setchecklistfilename(self):
        # should have already passed ok_set_filename test before calling this!!!

        if not self.checknotcurrent():
            return
        

        self.xmldoc.lock_rw()
        
        try : 
            destl=self.xmldoc.xpath("chx:dest")
            assert(len(destl) == 1)
            dest=destl[0]
            
            desttext=""
            if dest.text is not None:
                desttext=dest.text.strip()
                pass
            
        
            filename=self.requestedfilename()
        
        
            # sys.stderr.write("filename=%s\n" % (filename))
            
            # if self.datacollectmode: 
            if self.datacollectmode and (self.done_is_save_measurement or self.has_save_measurement_step or self.part_of_a_measurement): 
                # automatically set the filename

                assert("measnum" in self.private_paramdb)
                # Make sure current experiment log measnum is in the checklist measnum set

                # assert(self.paramdb["measnum"].dcvalue.value() in self.private_paramdb["measnum"].dcvalue.value())
            
                (filebasename,fileext)=os.path.splitext(filename)
                # cnt=1
            
                if self.done_is_save_measurement or self.has_save_measurement_step: 
                    chklistfile="%s-%.4d%s" % (filebasename,self.paramdb["measnum"].dcvalue.value(),fileext)
                    chklistpath=os.path.join(desttext,chklistfile)
                    
                    cnt=1
                    while (os.path.exists(chklistpath)) :

                        chklistfile="%s-%.4d-%d%s" % (filebasename,self.paramdb["measnum"].dcvalue.value(),cnt,fileext)
                        chklistpath=os.path.join(desttext,chklistfile)
                        
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
                    cnt=0
                    
                    while os.path.exists(os.path.join(desttext,chklistfile)):
                        cnt+=1
                    
                        chklistfile="%s-%.4d-%.4d%s" % (filebasename,self.paramdb["measnum"].dcvalue.value(),cnt,fileext)
                        pass


                    chklistpath=os.path.join(desttext,chklistfile)
                    
                    
                    pass
                oldfilename=self.xmldoc.filename
                self.xmldoc.setfilename(os.path.join(desttext,chklistfile))
                self.gladeobjdict["SaveButton"].set_sensitive(True)


                if self.xmldoc.hasattr(None,"parent"):
                    # if we have a parent attribute, update it relative to the new filename
                    if oldfilename is None:
                        reffilename=self.pre_reset_filename
                        pass
                    else: 
                        reffilename=oldfilename
                        pass
                    
                    if reffilename is not None:
                        self.set_parent(self.xmldoc.getcontextdir(),canonicalize_path.canonicalize_relpath(os.path.split(reffilename)[0],self.xmldoc.getattr(None,"parent")))
                        pass
                    else: 
                        self.set_parent(self.xmldoc,getcontextdir(),self.xmldoc.getattr(None,"parent"))
                        pass
                    pass

                #self.xmldoc.autoflush=True
                
                # WARNING: filenamenotify may call requestval_sync which runs sub-mainloop
                # ***!!! Possible bug because shouldn't do this with stuff locked
                for (filenamenotify,fnargs,fnkwargs) in  self.filenamenotify: 
                    filenamenotify(self,self.origfilename,dest,chklistfile,oldfilename,*fnargs,**fnkwargs)
                    pass
            
                # enable save button
                self.gladeobjdict["SaveButton"].set_sensitive(True)
                
                if self.done_is_save_measurement or self.has_save_measurement_step:
                    # store name of this checklist file in paramdb
                    self.paramdb["measchecklist"].requestval_sync(hrefv.frompath(self.xmldoc.getcontextdir(),chklistfile))
                    pass
                self.chklistfile=chklistfile  # store for convenience
                
                # set window title 
            
                # set filename field at bottom of window
                self.private_paramdb["defaultfilename"].requestvalstr_sync(os.path.split(chklistfile)[-1]) 
            
                self.gladeobjdict["CheckListWindow"].set_title(os.path.split(chklistfile)[-1])
            
                pass
            else :
                # not datacollectmode or datacollectmode but not part_of_a_measurement, done_is_save_measurement, etc. 
                
                # add a numeric suffix if this file already exists.
                (filebasename,fileext)=os.path.splitext(filename)
                cnt=0

                oldfilename=self.xmldoc.filename
            
                chklistfile=filename
            
                while os.path.exists(os.path.join(desttext,chklistfile)):
                    cnt+=1
                    
                    chklistfile="%s-%.4d%s" % (filebasename,cnt,fileext)
                    pass

                newfilename=os.path.join(desttext,chklistfile)

                #sys.stderr.write("newfilename=%s\n" % (newfilename))
                
                try : 
                    
                    self.xmldoc.setfilename(newfilename)
                    pass
                except: 
                    (exctype, excvalue) = sys.exc_info()[:2] 
                    tback=traceback.format_exc()
                    ErrorDialog("Exception assigning filename %s to checklist; output may not be saved" % (newfilename),exctype,excvalue,tback)
                    newfilename=None
                    # self.xmldoc.setfilename(None)
                    
                    pass

                self.gladeobjdict["SaveButton"].set_sensitive(True)

                if self.xmldoc.hasattr(None,"parent"):
                    # if we have a parent attribute, update it relative to the new filename
                    self.set_parent(self.xmldoc.getcontextdir(),self.xmldoc.getattr(None,"parent"))
                    pass

                #self.xmldoc.autoflush=True
            
                # WARNING: filenamenotify may call requestval_sync which runs sub-mainloop
                # ***!!! Possible bug because shouldn't do this with stuff locked
                for (filenamenotify,fnargs,fnkwargs) in self.filenamenotify: 
                    #import pdb as pythondb
                    #try: 
                    filenamenotify(self,self.origfilename,dest,chklistfile,oldfilename,*fnargs,**fnkwargs)
                    #except:
                    #    pythondb.post_mortem()
                    pass
                self.chklistfile=chklistfile  # store for convenience

                # self.xmldoc.setfilename(os.path.join(desttext,chklistfile))

                # set filename field at bottom of window
                self.private_paramdb["defaultfilename"].requestvalstr_sync(chklistfile) 

                if newfilename is not None:
                    # unless the filename assignment failed
                    # self.gladeobjdict["SaveButton"].set_property("label","Auto-save mode")
                    self.gladeobjdict["SaveButton"].set_property("label","Done")
                    pass
                pass
            pass
        except:
            raise

        finally:
            self.xmldoc.unlock_rw()
            pass

        # self.xmldoc.flush() # only actually flushes if an output name has been set

        
        pass
    

    def checknotcurrent(self):
        if "measnum" in self.private_paramdb:
            curmeasnum=self.paramdb["measnum"].dcvalue.value()
            if curmeasnum is not None and curmeasnum not in self.private_paramdb["measnum"].dcvalue.value():
                # raise ValueError("Not Current: curmeasnum=%s; checklistmeasnum=%s" % (curmeasnum,self.private_paramdb["measnum"].dcvalue.value()))
                if hasattr(gtk,"MessageType") and hasattr(gtk.MessageType,"WARNING"):
                    # gtk3
                    notcurrentdialog=gtk.MessageDialog(type=gtk.MessageType.WARNING,buttons=gtk.ButtonsType.NONE)
                    pass
                else : 
                    notcurrentdialog=gtk.MessageDialog(type=gtk.MESSAGE_WARNING,buttons=gtk.BUTTONS_NONE)
                    pass
                    
                notcurrentdialog.set_markup("This measurement checklist is not current.\nChecklist measnum=%s; current measnum=%d." % (str(self.private_paramdb["measnum"].dcvalue),curmeasnum))
                notcurrentdialog.add_button("Continue",1)
                notcurrentdialog.add_button("Cancel operation",0)
                
                notcurrentdialogval=notcurrentdialog.run()
                
                notcurrentdialog.destroy()

                return notcurrentdialogval==1  # Whether we should continue

                
            pass
        return True
    


    def handle_check(self,obj,boxnum):
        
        if self.grayed_out:
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
        # make sure that checklist is now current
        if not measname_mismatch_ok:
            if not self.checknotcurrent():
                return
            pass



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
        

                
            if checked and self.ok_set_filename():
                self.setchecklistfilename()
                pass
            pass
        except: 
            raise

        finally:            
            self.xmldoc.unlock_rw()
            pass

        # self.xmldoc.shouldbeunlocked()  # must be unlocked for our changes to be flushed to disk
        

        if self.checkdone():
            # set a color on the SaveButton to indicate done...

            if not "gtk" in sys.modules: # gtk3  ... currently INOPERABLE
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



