import os
import sys
import socket
import time
import urlparse
import urllib
import copy

import xmldoc
import canonicalize_path
import dc_value

# ***!!! Should add "origfilename" and "done" attributes to dc:checklist tags...

__pychecker__="no-argsused no-import"

cdb_nsmap={
    "dc": "http://thermal.cnde.iastate.edu/datacollect",
    "chx": "http://thermal.cnde.iastate.edu/checklist",
    "dcv": "http://thermal.cnde.iastate.edu/dcvalue",
    "xlink":"http://www.w3.org/1999/xlink",
}

checklistcache={}  # cache -- by canonicalpath -- of xmldocs 
openchecklists=[] # list of open checklists (checklist class)

openplans=[] # list of open checklists (checklist class)


opennotifies=[]
filenamenotifies=[]
resetnotifies=[]
donenotifies=[]
closenotifies=[]

def requestopennotify(notify,*args,**kwargs):
    # Only adds if needed... based on equality of notify, args, and kwargs
    if (notify,args,kwargs) not in opennotifies:
        opennotifies.append((notify,args,kwargs))
        pass
    pass

def removeopennotify(notify,*args,**kwargs):
    # Only adds if needed... based on equality of notify, args, and kwargs
    if (notify,args,kwargs) in opennotifies:
        opennotifies.remove((notify,args,kwargs))
        pass
    pass

def requestfilenamenotify(notify,*args,**kwargs):
    # Only adds if needed... based on equality of notify, args, and kwargs
    if (notify,args,kwargs) not in filenamenotifies:
        filenamenotifies.append((notify,args,kwargs))
        pass
    pass

def removefilenamenotify(notify,*args,**kwargs):
    # Only adds if needed... based on equality of notify, args, and kwargs
    if (notify,args,kwargs) in filenamenotifies:
        filenamenotifies.remove((notify,args,kwargs))
        pass
    pass

def requestresetnotify(notify,*args,**kwargs):
    # Only adds if needed... based on equality of notify, args, and kwargs
    if (notify,args,kwargs) not in resetnotifies:
        resetnotifies.append((notify,args,kwargs))
        pass
    pass

def removeresetnotify(notify,*args,**kwargs):
    # Only adds if needed... based on equality of notify, args, and kwargs
    if (notify,args,kwargs) in resetnotifies:
        resetnotifies.remove((notify,args,kwargs))
        pass
    pass

def requestdonenotify(notify,*args,**kwargs):
    # Only adds if needed... based on equality of notify, args, and kwargs
    if (notify,args,kwargs) not in donenotifies:
        donenotifies.append((notify,args,kwargs))
        pass
    pass

def removedonenotify(notify,*args,**kwargs):
    # Only adds if needed... based on equality of notify, args, and kwargs
    if (notify,args,kwargs) in donenotifies:
        donenotifies.remove((notify,args,kwargs))
        pass
    pass



def requestclosenotify(notify,*args,**kwargs):
    # Only adds if needed... based on equality of notify, args, and kwargs
    if (notify,args,kwargs) not in closenotifies:
        closenotifies.append((notify,args,kwargs))
        pass
    pass

def removeclosenotify(notify,*args,**kwargs):
    # Only adds if needed... based on equality of notify, args, and kwargs
    if (notify,args,kwargs) in closenotifies:
        closenotifies.remove((notify,args,kwargs))
        pass
    pass


def checklistlookup(href):
    global checklistcache


    # Search for cached copy
    cached=None
    
    if href in checklistcache:
        cached=checklistcache[href]

        # Check that this cached xmldoc still points at the same canonpath
        if cached.get_filehref() != href:
            cached=None
            pass
        else:
            cached.lock_ro() # lock it for access
            pass
        pass
        
    if cached is None:
        if href.ismem():
            
            entry=checklistentry(None,None,href,False)
            entry.clinfo=""
            entry.cltype=""
            entry.starttimestamp=""
            entry.is_done=False
            entry.allchecked=False
            
            return entry
        #else :
           # # assume local file
            
        cached=xmldoc.xmldoc.loadhref(href,use_locking=True)
        # loadfile includes an implicit lock_ro()
        checklistcache[href]=cached
        pass
    try: 
        
        entry=checklistentry(None,cached,cached.get_filehref(),False)
        pass
    finally:
        cached.unlock_ro() # release lock on cached xmldoc
        pass
        
    return entry


#def create_checklisthashable(checklistxmldocu):
#    href=checklistxmldocu.get_filehref()
#    if href.isfile():
#        return "path(%s)" % (canonicalize_path.canonicalize_path(href.path))
#
#    return "url(%s)" % (href.absurl())

def cachechecklist(checklistobj):
    # make sure a checklist is in our cache
    # overrides any current etnry

    global checklistcache

    checklistcache[checklistobj.xmldoc.get_filehref()]=checklistobj.xmldoc
    pass

class checklistentry(object):
    # a class checklistentry is how a checklist is represented
    # within the checklistdb
    filename=None # Just filename, no path
    #filename_abbrev=None  # used by checklistdbwin to represent abbreviated filename
    filehref=None # hrefvalue object representing URL
    orighref=None
    #origfilename_abbrev=None # used by checklistdbwin to represent abbreviated origfilename
    clinfo=None
    #clinfo_abbrev=None  # used by checklistdbwin to represent abbreviated clinfo
    cltype=None
    starttimestamp=None
    starttimestamp_abbrev=None  # used by checklistdbwin to represent abbreviated starttimestamp

    is_done=None  # is this checklist done
    #is_plan=None  # is this a plan as opposed to a regular checklist?
    is_open=None  # is this checklist in-memory
    allchecked=None # Have all items been checked?
    measnum=None  # measnum from checklist or None
    checklist=None # checklist object or None

    def __init__(self,checklist,xmldoc,filehref,is_open):
        # PRIVATE: Create and return a checklist entry for provided
        # xmldoc. 
        # Locks xmldoc for read

        self.checklist=checklist
        self.filehref=filehref

        if filehref is not None and not filehref.ismem():
            self.filename=filehref.get_bare_unquoted_filename()
            pass
            
        #self.canonicalpath=canonicalpath
        
        self.is_open=is_open

        if xmldoc is not None:
            xmldoc.lock_ro()
            try: 
                
                # does root element of checklist have "done" attribute and is it true?"
                if "done" in xmldoc.find('.').attrib and xmldoc.find('.').attrib["done"]=="true":
                    self.is_done=True
                    pass
                else :
                    self.is_done=False
                    pass
    
                # does root element of checklist have "allchecked" attribute and is it true?"
                if "allchecked" in xmldoc.find('.').attrib and xmldoc.find('.').attrib["allchecked"]=="true":
                    self.allchecked=True
                    pass
                else :
                    self.allchecked=False
                    pass

                self.measnum=None
                measnumels=xmldoc.xpath("dc:measnum")
                if len(measnumels) > 0:
                    measnumvalue=dc_value.integervalue.fromxml(xmldoc,measnumels[0])
                    self.measnum=measnumvalue.value()
                    pass
                
                self.clinfo=xmldoc.xpathsinglestr("string(chx:clinfo)")
                origelement=xmldoc.xpathsingle("chx:origunfilled")
                self.orighref=dc_value.hrefvalue.fromxml(xmldoc,origelement)
                self.cltype=xmldoc.xpathsinglestr("string(chx:clinfo/@type)")
                self.starttimestamp=xmldoc.xpathsinglestr("string(chx:log/@starttimestamp)")
                pass

            finally: 
                xmldoc.unlock_ro()
                pass
            pass
        
    
        pass

    pass
        


# xlinkhref2canonpath: no longer used
def xlinkhref2canonpath(contextdir,doc,element):
    # Get canonicalized path from a xlink:href attribute in a dc:checklist tag. 

    # NOTE: ***!!! Should be able to handle un-escaping URL's !!!

    URL=doc.getattr(element,"xlink:href",namespaces={"xlink": "http://www.w3.org/1999/xlink"})
    ## sys.stderr.write("xlinkhref2canonpath: URL=%s\n" % (URL))
    ParsedURL=urlparse.urlparse(URL)
    if ParsedURL.scheme == "mem": # in-memory
        return URL # just return the full unparsed, unescaped url for in-memory.... will be canonical
    if ParsedURL.scheme != "":
        raise ValueError("Full URLs not supported in checklist xlink: %s" % (URL))
    #ParsedURLpath=ParsedURL.path
    # stop using urlparse for now because we have ';' in some filenames that screws it up
    
    if URL.startswith("mem://"):
        return URL

    if URL.startswith("file://") or URL.startswith("http://"):
        raise ValueError("Full URLs not supported in checklist xlink: %s" % (URL))
    
    # unescape URL and convert path separators
    Path=urllib.url2pathname(URL)
        
    


    ## Convert Path to a filename
    #if os.path.sep != '/':
    #    Path=ParsedURLpath.replace("/",os.path.sep)
    #    pass
    #else: 
    #    Path=ParsedURLpath
    #    pass
        
    if not os.path.isabs(Path):
        ## Relative path... append to path of containing document
        #if doc.filename is None: 
        #    # relative filename, but we have no reference point... return None
        #    return None
        #Path=os.path.join(os.path.split(doc.filename)[0],Path)
        Path=os.path.join(contextdir,Path)
        
        pass
    CanonPath=canonicalize_path.canonicalize_path(Path)
    return CanonPath





def setelementsbyorder(setinp,*lists):
    # extract elements of setinp according to their order in the concatenation of lists

    setcpy=copy.copy(setinp)
    
    listcomb=[]
    for lst in lists:
        listcomb.extend(lst)
        pass
    
    result=[]
    for element in listcomb:
        if element in setcpy:
            setcpy.remove(element)
            result.append(element)
            pass
        pass
    
    # add in any additional elements (that weren't in the lists) in arbitrary order
    result.extend(list(setcpy))
    return result

    


def getchecklists(contexthref,paramdb,clparamname,clparamname2=None,allchecklists=False,allplans=False):
    # contexthref is the contexthref for paramdb[clparamname] and paramdb[clparamname2]
    # for example paramdb["checklists"], i.e. the directory that contains the file in which the 
    # contents of paramdb["checklists"] will be written. This is important because the dc:checklist tags
    # within have relative paths, and we need to know what they are relative to
    # contexthref and paramdb are only needed if clparamname or clparamname2 is provided. 

    # Get list of checklists -- those listed in paramdb[clparamname] which should be a dc:checklists
    # tag that contains multiple dc:checklist tags, each of which has an xlink:href attribute

    # returns list of class checklistentry
    
    # checklistset is a set either of mem:// urls or canonicalized paths
    checklistset=set([])

    all_cl_unnamed_inmem=[]
    all_cl_named_inmem=[]
    all_pl_unnamed_inmem=[]
    all_pl_named_inmem=[]


    if allchecklists:
        # unnamed checklists in-memory -- indexed by their id
        all_cl_unnamed_inmem=[ checklist.xmldoc.get_filehref() for checklist in openchecklists if checklist.xmldoc.filehref is None and not checklist.closed ]
        #sys.stderr.write("all_cl_unnamed_inmem=%s\n\n" % (str(all_cl_unnamed_inmem)))
        checklistset|=set(all_cl_unnamed_inmem)  
        # add in named checklists in-memory -- indexed by their canonicalized path
        all_cl_named_inmem=[ checklist.xmldoc.get_filehref() for checklist in openchecklists if checklist.xmldoc.filehref is not None and not checklist.closed ]
        #sys.stderr.write("all_cl_named_inmem=%s\n\n" % (str(all_cl_named_inmem)))
        checklistset|=set(all_cl_named_inmem)
        pass

    if allplans:
        # unnamed plans in-memory -- indexed by their id
        all_pl_unnamed_inmem=[ checklist.xmldoc_get_filehref() for checklist in openplans if checklist.xmldoc.filehref is None and not checklist.closed ]
        checklistset|=set(all_pl_unnamed_inmem)
        # add in named checklists in-memory -- indexed by their canonicalized path
        all_pl_named_inmem=[ checklist.xmldoc.get_filehref() for checklist in openplans if checklist.xmldoc.filehref is not None and not checklist.closed ]
        checklistset|=set(all_pl_named_inmem)
        pass

        
    checklists1=[]
    checklistsdoc=None
    if clparamname is not None:
        checklistsdoc=paramdb[clparamname].dcvalue.get_xmldoc(nsmap=cdb_nsmap,contexthref=contexthref)  # should be a <dc:checklists> tag containing <dc:checklist> tags. 

        # Go through xml parameter contents
        if checklistsdoc is not None:
            for checklist in checklistsdoc.xpath("dc:checklist"):
                # Should we just use dc_value.hrefvalue.fromxml(checklist)
                # here? Yes, but right now we confuse paths and URLS by storing
                # them the same way, so we would need a way to keep 
                # the distinction

                # Now we do
                checklisthref=dc_value.hrefvalue.fromxml(checklistsdoc,checklist)
                checklistset.add(checklisthref)
                checklists1.append(checklisthref)
                
                # if checklistsdoc.hasattr(checklist,"xlink:href"):
                #    # look for xlink:href attribute
                #    canonpath=xlinkhref2canonpath(contexthref,checklistsdoc,checklist)
                #    # sys.stderr.write("checklistset.add(%s)\n\n" % (canonpath))
                #    checklistset.add(canonpath)
                #    checklists1.append(canonpath)
                #    pass
                pass
            pass
        pass
        
    checklists2=[]
    checklistsdoc2=None
    if clparamname2 is not None: 
        checklistsdoc2=paramdb[clparamname2].dcvalue.get_xmldoc(nsmap=cdb_nsmap,contexthref=contexthref)  # should be a <dc:checklists> tag containing <dc:checklist> tags. 
        # Go through xml parameter contents
        if checklistsdoc2 is not None:
            for checklist in checklistsdoc2.xpath("dc:checklist"):
                # Now we do
                checklisthref=dc_value.hrefvalue.fromxml(checklistsdoc2,checklist)
                checklistset.add(checklisthref)
                checklists2.append(checklisthref)

                #if checklistsdoc2.hasattr(checklist,"xlink:href"):
                #    # look for xlink:href attribute
                #    canonpath=xlinkhref2canonpath(contexthref,checklistsdoc2,checklist)
                #    checklistset.add(canonpath)
                #    checklists2.append(canonpath)
                #    pass
                pass
            pass
        pass


            

    # PROBLEM: Want to tie checklist to how/why it was created and what document(s) it links to on creation
    #          but initially it has no filename, so no good way to make that link

    # SOLUTION: Represented mem:// or similar URL for in-memory checklists. include processid, hostname, starttime. 
    # Then when that checklist gets a name we can update the link

    entrylist=[]

    checklistobjbyhref=dict([ (checklistobj.xmldoc.get_filehref(),checklistobj) for checklistobj in openchecklists if not checklistobj.closed ])

    checklistobjbyhref.update(dict([ (checklistobj.xmldoc.get_filehref(),checklistobj) for checklistobj in openplans if not checklistobj.closed ]))
    
    #checklistobjbyhref.update(dict((generate_inmemory_id(checklistobj),checklistobj) for checklistobj in openchecklists if checklistobj.xmldoc.filename is None and not checklistobj.closed ))
    #checklistobjbycanonpath.update(dict((canonicalize_path.canonicalize_path(checklistobj.xmldoc.filename),checklistobj) for checklistobj in openchecklists if checklistobj.xmldoc.filename is not None and not checklistobj.closed ))

    #checklistobjbycanonpath.update(dict((generate_inmemory_id(checklistobj),checklistobj) for checklistobj in openplans if checklistobj.xmldoc.filename is None and not checklistobj.closed ))
    #checklistobjbycanonpath.update(dict((canonicalize_path.canonicalize_path(checklistobj.xmldoc.filename),checklistobj) for checklistobj in openplans if checklistobj.xmldoc.filename is not None and not checklistobj.closed ))


    for href in setelementsbyorder(checklistset,checklists1,checklists2,all_cl_unnamed_inmem,all_cl_named_inmem,all_pl_unnamed_inmem,all_pl_named_inmem): 
        checklistobj=None
        clentry=None   # clentry will be the checklistentry object

        # NOTE: Could speed up this search when number of checklists gets large by creating dictionaries !!!***
        
        if href in checklistobjbyhref:
            checklistobj=checklistobjbyhref[href]
            clentry=checklistentry(checklistobj,checklistobj.xmldoc,checklistobj.xmldoc.get_filehref(),True)
            pass
        else: 
            # look up a (possibly cached) copy of the XML file
            #sys.stderr.write("checklistlookup(%s)\n" % (canonpath))
            clentry=checklistlookup(href)
            pass
    
        entrylist.append(clentry)

        pass
    return entrylist

def print_checklists(contexthref,paramdb,clparamname,clparamname2=None,allchecklists=False,allplans=False):
    entrylist=getchecklists(contexthref,paramdb,clparamname,clparamname2=clparamname2,allchecklists=allchecklists,allplans=allplans)

    sys.stderr.write("\nChecklists\n")
    sys.stderr.write("---------------------------------------------------\n")
    for entry in entrylist: 
        if entry.is_done: 
            sys.stderr.write("%s: Done\n" % (entry.filehref.absurl()))
            pass
        else: 
            sys.stderr.write("%s: Incomplete\n" % (entry.filehref.absurl()))
            pass
        pass
        
    sys.stderr.write("---------------------------------------------------\n\n")
    pass
        


def checklist_handle_done(checklist,href):
    if checklist.closed:
        return

    # on done the checklist switches into read-only mode and
    # is essentially closed
    

    if href is None:
        raise ValueError("Cannot mark unnamed checklist as done")

    #canonname=canonicalize_path.canonicalize_path(filename)

    # Leave the old one in the paramdbs....
        
    pass


def checklistdonenotify(checklist,href):
    if checklist.closed:
        return
    checklist_handle_done(checklist,href)

    # perform requested notifications
    for (notify,args,kwargs) in donenotifies:
        notify(checklist,*args,**kwargs)
        pass

    pass


def checklistclosenotify(checklist):
    # MUST ARRANGE THAT THIS BE CALLED when a checklist is closed. 
    global openchecklists
    global openplans
    
    if checklist.closed:
        return


    while checklist in openchecklists:
        openchecklists.remove(checklist)
        pass

    while checklist in openplans:
        openplans.remove(checklist)
        pass

    # perform requested notifications
    for (notify,args,kwargs) in closenotifies:
        notify(checklist,*args,**kwargs)
        pass

    pass

    
def checklist_in_param(href,checklistsdoc):
    # href can be found from checklist.get_filehref()

    gotclentry=False
    for checklisttag in checklistsdoc.xpath("dc:checklist"):
        testhref=dc_value.hrefvalue.fromxml(checklistsdoc,checklisttag)
        if testhref==href:
            gotclentry=True
            break
        pass

    return gotclentry

class paramdbentry(object):
    paramdb=None
    clparamname=None
    contexthref=None
    is_plan=None

    def __init__(self,paramdb,clparamname,contexthref,is_plan):
        self.paramdb=paramdb
        self.clparamname=clparamname
        self.contextdir=contexthref
        self.is_plan=is_plan
    pass

paramdbentries={} # indexed by "%s;%s" % (id(paramdb),clparamname)

def paramdbindex(paramdb,clparamname):
    return "%s;%s" % (id(paramdb),clparamname)

def register_paramdb(paramdb,clparamname,contexthref,is_plan):
    # register a param within a paramdb with checklistdb 
    #   contextdir is the directory which the <dc:checklist xlink:href= 
    #              attributes within the paramdb should be relative to. 
    #              (usually directory containing the experiment log or
    #              the parent checklist that owns this paramdb)

    #   clparamname is the parameter within the paramdb
    #   is_plan is whether that parameter within the paramdb
    #              represents a plan (as opposed to a checklist)
    global paramdbentries

    index=paramdbindex(paramdb,clparamname)
    
    if index in paramdbentries:
        del paramdbentries[index]
        pass
        
    entry=paramdbentry(paramdb,clparamname,contexthref,is_plan)
    paramdbentries[index]=entry
    pass

def unregister_paramdb(paramdb,clparamname,contexthref,is_plan):
    global paramdbentries

    index=paramdbindex(paramdb,clparamname)
    
    if index in paramdbentries:
        del paramdbentries[index]
        pass
    pass
    

def addchecklisttoparamdb(checklist,paramdb,clparamname):
    # paramdb must have been previously registered!
    # NOTE: May call requestval_sync()

    # if checklist is newly-opened, should
    # call newchecklistnotify AFTER addchecklisttoparamdb

    href=checklist.xmldoc.get_filehref()
    
    
    index=paramdbindex(paramdb,clparamname)

    if index not in paramdbentries: 
        raise ValueError("Attempting to add checklist %s to unregistered paramdb" % (str(href)))

    paramdbentry=paramdbentries[index]


    checklistsdoc=paramdb[clparamname].dcvalue.get_xmldoc(nsmap=cdb_nsmap,contexthref=paramdbentry.contexthref)  # should be a <dc:checklists> tag containing <dc:checklist> tags. 

    gotclentry=checklist_in_param(href,checklistsdoc)

    if not(gotclentry):
        # no existing entry for this checklist...  add one!
        # 
        
        newelement=checklistsdoc.addelement(checklistsdoc.getroot(),"dc:checklist")
        href.xmlrepr(checklistsdoc,newelement)
        
        
        #if canonname.startswith("mem://"):
        #    checklistsdoc.setattr(newelement,"xlink:href",canonname)
        #    pass
        #else: 
        #    checklistsdoc.setattr(newelement,"xlink:href",urllib.pathname2url(canonicalize_path.relative_path_to(paramdbentry.contextdir,canonname)))
        #    pass

        # update paramdb entry
        paramdb[clparamname].requestval_sync(dc_value.xmltreevalue(checklistsdoc,contexthref=paramdbentry.contexthref))
        
        
        pass
    pass
    
    
def newchecklistnotify(checklist,is_plan=False):
    # if you also need to add the checklist to a paramdb,
    # you should do this FIRST
    
    global openchecklists
    global openplans

    # make sure this checklist is in our cache
    cachechecklist(checklist)


    # filename=checklist.xmldoc.filename

    is_new=False

    if is_plan:
        if checklist not in openplans: 
            openplans.append(checklist)
            is_new=True
            pass
        pass
    else:
        if checklist not in openchecklists: 
            openchecklists.append(checklist)
            is_new=True
            pass
        pass


    # make sure we are notified if the filename is set or reset. 
    # ***!!! Should really have a way to destroy the notify
    # ***!!! if the paramdb goes away (e.g. if parent checklist closes)
    # *** Also need better organization of the sub-notifies that we
    # *** provide to others, so we don't duplicate those just because 
    # *** we got duplicate notifies ourselves for the different paramdbs

    checklist.addfilenamenotifyifneeded(filenamenotify) # ,contextdir,paramdb,clparamname)
    checklist.addresetnotifyifneeded(resetnotify)  # ,None,None,None,contextdir,paramdb,clparamname)
    checklist.adddonenotifyifneeded(checklistdonenotify)
    checklist.addclosenotifyifneeded(checklistclosenotify)

    # perform open notifies only if the checklist is actually new
    if is_new:
        for (notify,args,kwargs) in opennotifies:
            notify(checklist,*args,**kwargs)
            pass
        pass
    pass

#def checklistnotify(checklist,contextdir,paramdb,clparamname,is_plan=False):
    # MUST ARRANGE THAT THIS BE CALLED when a checklist is opened. 
    # This routine both makes sure that the checklist is in the global list of in-memory plans/checklists,
    # and registers it with a paramdb2 parameter that tracks its presence through an XML structure. 
    # explogwindow.open_checklist() calls this to register it with the master experiment log. 
    # 
    # if a checklist is to be registered elsewhere, this routine must be called with that contextdir,
    # paramdb, and clparamname as well!


    # use is_plan=True to put this checklist into the plan list instead of the list of checklists
    # WARNING: May call requestval_sync

    # sys.stderr.write("checklistnotify() start\n")

#    global openchecklists
#    global openplans


    # contextdir is the directory in which the paramdb elements are written (usually directory containing the experiment log)
#    filename=checklist.xmldoc.filename

 #   is_new=False
#
#    if is_plan:
#        if checklist not in openplans: 
#            openplans.append(checklist)
#            is_new=True
#            pass
#        pass
#    else:
#        if checklist not in openchecklists: 
#            openchecklists.append(checklist)
#            is_new=True
#            pass
#        pass
#        
#    if filename is None:
#        canonname=generate_inmemory_id(checklist)
#        pass
#    else :
#        canonname=canonicalize_path.canonicalize_path(filename)
#        pass
#
#    checklistsdoc=paramdb[clparamname].dcvalue.get_xmldoc(nsmap={"dc": "http://thermal.cnde.iastate.edu/datacollect","xlink":"http://www.w3.org/1999/xlink"})  # should be a <dc:checklists> tag containing <dc:checklist> tags. 
#
#    gotclentry=checklist_in_param(checklist,contextdir,checklistsdoc)
#
#    if not(gotclentry):
#        # no existing entry for this checklist...  add one!
#        # 
#        newelement=checklistsdoc.addelement(checklistsdoc.getroot(),"dc:checklist")
#        checklistsdoc.setattr(newelement,"xlink:href",canonicalize_path.relative_path_to(contextdir,canonname))
#
#        # update paramdb entry
#        paramdb[clparamname].requestval_sync(checklistsdoc)
#        
#        
#        pass

    # make sure we are notified if the filename is set or reset. 
    # ***!!! Should really have a way to destroy the notify
    # ***!!! if the paramdb goes away (e.g. if parent checklist closes)
    # *** Also need better organization of the sub-notifies that we
    # *** provide to others, so we don't duplicate those just because 
    # *** we got duplicate notifies ourselves for the different paramdbs
#
#    checklist.addfilenamenotifyifneeded(filenamenotify,contextdir,paramdb,clparamname)
#    checklist.addresetnotifyifneeded(resetnotify,None,None,None,contextdir,paramdb,clparamname)
#    checklist.adddonenotifyifneeded(checklistdonenotify)
#    checklist.addclosenotifyifneeded(checklistclosenotify)
        
#    # perform open notifies only if the checklist is actually new
#    if is_new:
#        for (notify,args,kwargs) in opennotifies:
#            notify(checklist,*args,**kwargs)
#            pass
#        pass
#
#    pass

#!!! fix to separate out reset and assign filename behaviors
# !!! filenamenotify should get old name too. 

#def filenamenotify_internal(checklist,origfilename,fname,contextdir,paramdb,clparamname):
#    # MUST ARRANGE THAT THIS BE CALLED when checklist gets its filename set (DONE)
#    # Note that it should also be called when the filename gets reset due to rerunning the checklist
#    # WARNING: May call requestval_sync which runs sub-mainloop

#    #if checklist.xmldoc.filename is None: 
#    #    raise ValueError("Null fname")
#    #sys.stderr.write("fname=%s\n" % (checklist.xmldoc.filename))
#    #import traceback
#    #traceback.print_stack()
##
#
#    if clparamname not in paramdb: 
#        # invalid paramdb -- probably a closed one
#        return
#
#
#    filename=checklist.xmldoc.filename  # need to use this to get full path. otherwise it may just be file part

#    # sys.stderr.write("filenamenotify: filename=%s\n" % (filename))

#    oldname=generate_inmemory_id(checklist) # the mem:// url

            
#    if filename is not None: 
#        canonname=canonicalize_path.canonicalize_path(filename)
#        pass

#    checklistsdoc=paramdb[clparamname].dcvalue.get_xmldoc(nsmap={"dc": "http://thermal.cnde.iastate.edu/datacollect","xlink":"http://www.w3.org/1999/xlink"})  # should be a <dc:checklists> tag containing <dc:checklist> tags. 

#    if oldname is not None and checklistsdoc is not None:
#        # find and remove preexisting elements within the checklist param that reference this file


#        for checklisttag in checklistsdoc.xpath("dc:checklist"):
#            if checklistsdoc.hasattr(checklisttag,"xlink:href"):
#                # look for xlink:href attribute
#                canonpath=xlinkhref2canonpath(contextdir,checklistsdoc,checklisttag)
#                if canonpath==oldname: # Found the mem:// url for this checklist? 
#                    # update the mem:// url
#
#                    if filename is not None: 
#                        checklistsdoc.setattr(checklisttag,"xlink:href",canonicalize_path.relative_path_to(contextdir,canonname))
#                        # update paramdb entry
#                        paramdb[clparamname].requestval_sync(checklistsdoc)
#
#                        # we've updated the name... were done
#                        return
#                    else : 
#                        # checklist has no name... we want the mem://url
#                        checklistsdoc.setattr(checklisttag,"xlink:href",generate_inmemory_id(checklist))
#                        # update paramdb entry
#                        paramdb[clparamname].requestval_sync(checklistsdoc)
#                        break # should only be one entry... no need to go on
#                    pass 
#                pass
#            pass
#            
#        
#        pass
    
#    # if we got here, it hasn't set the name.
#    if filename is None:
#        inmemoryname=generate_inmemory_id(checklist) # the mem:// url
#        
#        foundref=checklistsdoc.xpath("dc:checklist[@xlink:href='%s']" % (inmemoryname))
#        if len(foundref) < 1:
#            # add reference
#            newelement=checklistsdoc.addelement(checklistsdoc.getroot(),"dc:checklist")
#            checklistsdoc.setattr(newelement,"xlink:href",inmemoryname)
#            
#            # update paramdb entry
#            paramdb[clparamname].requestval_sync(checklistsdoc)
#
#            pass
#        pass
#    else : 
#        # filename provided... search it out
#        canonfname=canonicalize_path.canonicalize_path(filename)
#
#        gotit=False
#        for checklisttag in checklistsdoc.xpath("dc:checklist"):
#            if checklistsdoc.hasattr(checklisttag,"xlink:href"):
#                # look for xlink:href attribute
#                canonpath=xlinkhref2canonpath(contextdir,checklistsdoc,checklisttag)
#                if canonpath==canonfname: # Found the url for this checklist? 
#                    gotit=True
#                    break
#                pass
#            pass
#        
#        if not gotit: 
#            # Need to create a new entry 
#            
#            newelement=checklistsdoc.addelement(checklistsdoc.getroot(),"dc:checklist")
#            checklistsdoc.setattr(newelement,"xlink:href",canonicalize_path.relative_path_to(contextdir,filename))
#            
#            # update paramdb entry
#            paramdb[clparamname].requestval_sync(checklistsdoc)
#            pass
#        pass
#
#    pass


def filenamenotify(checklist,orighref,newhref,oldhref): #paramdb,clparamname):
    # Warning: May call requestval_sync!

    #sys.stderr.write("checklistdb.filenamenotify: origfilename=%s, fname=%s, oldfilename=%s, closed=%s\n" % (origfilename,fname,oldfilename,str(checklist.closed)))

    #import pdb as pythondb
    #pythondb.set_trace()
    
    if checklist.closed:
        return

    

    #filename=checklist.xmldoc.filename  # need to use this to get full path. otherwise it may just be file part
    #href=checklist.xmldoc.get_filehref()

    #if oldhref is not None:
    #    oldcanonname=canonicalize_path.canonicalize_path(oldfilename)
    #    pass
    #else:
    #    oldcanonname=generate_inmemory_id(checklist) # the mem:// url
    #    pass

    #if filename is not None:
    #    canonname=canonicalize_path.canonicalize_path(filename)
    #    pass
    #else: 
    #    canonname=generate_inmemory_id(checklist)
    #    pass

    
    #if canonname==oldcanonname:
    if (newhref is None) and (oldhref is None):
        return
    if (newhref is not None) and (oldhref is not None) and newhref==oldhref:
        return 
        
    # canonical name has changed from oldhref to newhref
    

    # go through all paramdb's and find instances of oldcanonname
    # and change them to canonname
    for index in paramdbentries: 
        entry=paramdbentries[index]
        
        checklistsdoc=entry.paramdb[entry.clparamname].dcvalue.get_xmldoc(nsmap=cdb_nsmap,contexthref=entry.contexthref)  # should be a <dc:checklists> tag containing <dc:checklist> tags. 
        if checklistsdoc is not None:
            for checklisttag in checklistsdoc.xpath("dc:checklist"):

                checklisthref=dc_value.hrefvalue.fromxml(checklistsdoc,checklisttag)
                
                if oldhref is not None and checklisthref==oldhref:
                    # found a previous name for this checklist
                    #sys.stderr.write("checklistdb.filenamenotify: matched %s...\n" % (oldcanonname))
                    # update the url

                    newhref.xmlrepr(checklistsdoc,checklisttag)
                    # update paramdb entry
                    entry.paramdb[entry.clparamname].requestval_sync(dc_value.xmltreevalue(checklistsdoc,contexthref=entry.contexthref))
                    #sys.stderr.write("checklistdb: updatedentry=%s\n" % (str(entry.paramdb[entry.clparamname])))
                    pass
                pass
                
            pass
        
        pass
    pass



    # filenamenotify_internal(checklist,origfilename,fname,contextdir,paramdb,clparamname)
    
    # perform requested notifications
    for (notify,args,kwargs) in filenamenotifies:
        notify(checklist,orighref,newhref,oldhref,*args,**kwargs)
        pass
    pass


def checklist_handle_reset(checklist,oldhref):
    # uses oldhref, which should be the last "real" filename
    # to make sure we are added to the right paramdbs

    if checklist.closed:
        return

    #sys.stderr.write("checklistdb:checklist_handle_reset(%s)\n" % (oldfilename))
    # make sure this checklist is in our cache
    cachechecklist(checklist)


    # on reset the checklist forks into two: 
    #  The pre-existing, pre-reset checklist stays, but 
    # is no longer in memory. 
    #
    # In addition a new, unfilled, in-memory checklist is 
    # created


    href=checklist.xmldoc.get_filehref() # the file path or mem:// url

    # sys.stderr.write("handle_reset: oldcanonname=%s canonname=%s\n" % (oldcanonname,canonname))
    
    #if oldhref.ismem(): 
        # checklist that has not been saved gets lost on reset -- we do nothing for this case
    #    pass
    if oldhref is not None and not oldhref.ismem(): 
    
        # had a name and now it doesn't
        # Leave the old one in the paramdbs....
        # Add the new in-memory name to each of the paramdbs 
        # in which we find the old name


        # always make sure the new canonname is in the 

        # Since there can be multiple paramdbs want to make sure
        # we add new entry to same place as old entry
        entryupdated=False
        for index in paramdbentries: 
            entry=paramdbentries[index]
        
            checklistsdoc=entry.paramdb[entry.clparamname].dcvalue.get_xmldoc(cdb_nsmap,contextdir=entry.contextdir)  # should be a <dc:checklists> tag containing <dc:checklist> tags. 
            
            if checklistsdoc is not None:
                for checklisttag in checklistsdoc.xpath("dc:checklist"):

                    
                    checklisthref=dc_value.hrefvalue.fromxml(checklistsdoc,checklisttag)
                
                    if checklisthref==oldhref:
                        # found a previous name for this checklist
                        
                        # Create a new entry
                        newelement=checklistsdoc.addelement(checklistsdoc.getroot(),"dc:checklist")
                        href.xmlrepr(checklistsdoc,newelement)
                        
                        # update paramdb entry
                        entry.paramdb[entry.clparamname].requestval_sync(dc_value.xmltreevalue(checklistsdoc,contexthref=entry.contexthref))
                        entryupdated=True
                        
                        pass
                    pass
                pass
            pass
        assert(entryupdated)
        pass
        

    #import pdb as pythondb
    #try: 
    #filenamenotify_internal(checklist,origfilename,dest,fname,contextdir,paramdb,clparamname)
    #    pass
    #except:
    #    pythondb.post_mortem()
    #    pass
        
    # perform requested notifications
def resetnotify(checklist,oldfilename):
    if checklist.closed:
        return

    checklist_handle_reset(checklist,oldfilename)

    for (notify,args,kwargs) in resetnotifies:
        notify(checklist,*args,**kwargs)
        pass
    pass
