# NOTE: always import this module EARLY in your list of imports, 
# as other modules need to be able to find it!

import os
import sys
import copy
import os.path
import socket
import datetime
import subprocess
import getpass
import threading
import traceback
import inspect
import hashlib
import csv
import string

import dg_timestamp
from . import canonicalize_path

from . import xmldoc
from .import dc_process_common

from lxml import etree
from pytz import reference

# NOTE: See provenance.xsd for overall documentation of provenance approach.

# !!! Should go through and switch xmldoc API usage to etree API usage 
# so we don't start collecting the provenance of the provenance !!!
# Also document distinction between xmldoc (xmldocu) and etree doc (doc)

###!!! Should mark doc.modified any time we use low-level tools to write a document

###***!!! Bug: This module doesn't explicitly define 
### filename paths as distinct from URLs, so 
### it will probably fail on Windows.
###  -- Need to use urllib.pathname2url()
###     and urllib.url2pathname() to convert
###     back and forth



try: 
    import builtins  # python3
    pass
except ImportError: 
    import __builtin__ as builtins # python2
    pass

if not hasattr(builtins,"basestring"):
    basestring=str  # python3
    pass

__pychecker__="no-import"


DCP="{http://thermal.cnde.iastate.edu/datacollect/provenance}"
dcp="http://thermal.cnde.iastate.edu/datacollect/provenance"

DC="{http://thermal.cnde.iastate.edu/datacollect}"
dc="http://thermal.cnde.iastate.edu/datacollect"


def determinehostname():
    hostname=socket.getfqdn()

    # work aroud bug issues in getfqdn()
    if hostname=='localhost' or hostname=='localhost6':
        hostname=None
        pass
    elif hostname.endswith('.localdomain') or hostname.endswith('.localdomain6'):
        hostname=None
        pass
    
    if hostname is None or not '.' in hostname:
        # try running 'hostname --fqdn'
        hostnameproc=subprocess.Popen(['hostname','--fqdn'],stdout=subprocess.PIPE)
        hostnamep=hostnameproc.communicate()[0].strip()
        if hostname is None:
            hostname=hostnamep
            pass

        if hostnamep=='localhost' or hostnamep=='localhost6':
            hostnamep=None
            pass
        elif hostnamep.endswith('.localdomain') or hostnamep.endswith('.localdomain6'):
            hostnamep=None
            pass
        
        if hostnamep is not None and not '.' in hostname and '.' in hostnamep:
            hostname=hostnamep
            pass
        pass
    # now have (hopefully robust) fqdn or worst-case bare hostname 
    return hostname

def write_timestamp(doc,process_el,tagname,timestamp=None):
    starttime_el=doc.addelement(process_el,tagname)
    if timestamp is None: 
        timestamp=dg_timestamp.now().isoformat()
        pass
    doc.settext(starttime_el,timestamp)

def write_process_log(doc,process_el,status,stdoutstderrlog):
    # "status" shoudl be "success" or "exception" 
    log_el=doc.addelement(process_el,"dcp:log")
    log_el.text=stdoutstderrlog
    log_el.attrib["status"]=status
    pass

def write_input_file(doc,process_el,inputfile):
    inpf_el=doc.addelement(process_el,"dcp:inputfile")
    inpf_el.text=inputfile
    pass

    

def write_process_info(doc,process_el):
    hostname_el=doc.addelement(process_el,"dcp:hostname")
    doc.settext(hostname_el,determinehostname())
    doc.setattr(hostname_el,"pid",str(os.getpid()))
    doc.setattr(hostname_el,"uid",str(os.getuid()))
    doc.setattr(hostname_el,"username",getpass.getuser())
    argv_el=doc.addelement(process_el,"dcp:argv")
    doc.settext(argv_el,unicode(sys.argv)) # Save command line parameters
    pass


def reference_etxpath(doc,parent,tagname,contextelement,reference_canonical_etxpath,warnlevel="error"):
    # Create a new element, named tagname, within parent, that references the canonical etxpath
    # specified as reference_canonical_etxpath (MUST have already been canonicalized)
    # The new element is given a relative etxpath (relative to contextelement), but also
    # contains the absolute etxpath in the "absetxpath" attribute.
    element=doc.addelement(parent,tagname)
    doc.setattr(element,"type","etxpath") 
    doc.setattr(element,"absetxpath",reference_canonical_etxpath) # store absolute path directly
    doc.settext(element,canonicalize_path.relative_etxpath_to(doc.get_canonical_etxpath(contextelement),reference_canonical_etxpath))
    doc.setattr(element,"warnlevel",warnlevel)
    return element


def reference_pymodule(doc,parent,tagname,contextelement,module,warnlevel="none"):
    # Create a new element, named tagname, within parent, that references the python
    # module object referenced as "module"
    # warnlevel defaults to "none" because we usually don't have the ability to diagnose, anyway

    element=doc.addelement(parent,tagname)
    doc.setattr(element,"type","pymodule")
    if hasattr(module,"__version__"):
        doc.setattr(element,"pymoduleversion",module.__version__)
        pass
    if hasattr(module,"__versiondiff__"):
        doc.setattr(element,"pymoduleversiondiff",module.__versiondiff__)
        pass
    
    doc.settext(element,module.__name__)
    doc.setattr(element,"warnlevel",warnlevel)
    return element

    

def reference_file(doc,parent,tagname,contextelement,reference,warnlevel="error"):
    # filecontext_xpath is "/"+outputroot.tag
    # warnlevel should be "none" "info", "warning", or "error" and represents when the 
    # reference to this file does not match the file itself, how loud the warning
    # should be
    
    element=doc.addelement(parent,tagname)

    doc.setattr(element,"type","fileetxpath") 
    # print "relpath=", canonicalize_path.relative_path_to(os.path.dirname(doc.filename),reference)
    doc.setattr(element,"filepath",canonicalize_path.relative_path_to(os.path.dirname(doc.filename),reference))
    absfilepath=canonicalize_path.canonicalize_path(reference)
    doc.setattr(element,"absfilepath",absfilepath)

    # print "doc.get_canonical_etxpath(contextelement)=%s" %(doc.get_canonical_etxpath(contextelement))
    # print "canonicalize_path.filepath_to_etxpath(reference)=%s" % (canonicalize_path.filepath_to_etxpath(reference))
    doc.settext(element,canonicalize_path.relative_etxpath_to(doc.get_canonical_etxpath(contextelement),canonicalize_path.filepath_to_etxpath(absfilepath)))
    doc.setattr(element,"absetxpath",canonicalize_path.canonicalize_etxpath(canonicalize_path.filepath_to_etxpath(absfilepath)))
    # mtime now comes from the in memory provenance database
    # mtime=datetime.datetime.fromtimestamp(os.path.mtime(reference),dg_timestamp.UTC()).isoformat()
    # doc.setattr(element,"timestamp",mtime)
    doc.setattr(element,"warnlevel",warnlevel)
    # print etree.tostring(element)
    return element

def write_action(doc,process_el,action_name):
    action_el=doc.addelement(process_el,"dcp:action")
    doc.settext(action_el,action_name)
    pass

def write_target(doc,process_el,target_name):
    target_el=doc.addelement(process_el,"dcp:target")
    doc.settext(target_el,target_name)
    pass


class iterelementsbutskip(object):
    rootelement=None
    skipelement=None
    contextstack=None  # list of lists of children.  Last entry is latest
    contextstackpos=None # list of indexes into context stack... always pointing toward next element

    def __init__(self,rootelement,skipelement):
        # skipelement can either be an element object, tested for identity
        # or a string of some sort, which would match the Clark-notation tag.

        # will iterate through all descendents PLUS root element. 
        self.rootelement=rootelement
        self.skipelement=skipelement
        self.contextstack=[[self.rootelement]]
        self.contextstackpos=[0]
        pass

    def __iter__(self):
        return self

    def next(self):
        stackentry=len(self.contextstackpos)-1

        if stackentry < 0:
            # We must be done!
            raise StopIteration

        # Do we have a new entry in our current level
        if self.contextstackpos[stackentry] < len(self.contextstack[stackentry]):
            retval=self.contextstack[stackentry][self.contextstackpos[stackentry]]
            self.contextstackpos[stackentry]+=1 # increment index of next element to process
            if retval is self.skipelement:
                return self.next() # find another element instead

            if isinstance(self.skipelement,basestring):
                if retval.tag==self.skipelement:
                    return self.next() # find another element instead
                pass


            # Add sub level if children present
            if hasattr(retval,"getchildren"):
                retvalchildren=retval.getchildren()
                if len(retvalchildren) > 0:
                    self.contextstack.append(retvalchildren)
                    self.contextstackpos.append(0)
                    pass
                pass
            return retval
        else : 
            # no more elements at this level... go up one level
            self.contextstack.pop()
            self.contextstackpos.pop()
            return self.next()  # Find next element now that we are up one level
            
        pass


def add_generatedby_to_tree(xmldocu,treeroot,skipel,uuid):
    # skipel is None or perhaps the dcp:process element we have been creating
    # so that we don't list dependence on that

    for descendent in iterelementsbutskip(treeroot,skipel): #  iterate through descendents, but ignore the provenance tag structure we just created. 
        # print "descendent=%s" % (str(descendent))
        oldwgb=""
        if DCP+"wasgeneratedby" in descendent.attrib:
            oldwgb=descendent.attrib[DCP+"wasgeneratedby"]
            pass
        
        descendent.attrib[DCP+"wasgeneratedby"]=oldwgb + "uuid="+uuid+";"
        pass
    pass



def set_hash(xmldocu,doc_process_root,process_el):
    # MUST HAVE WRITTEN unique stuff such as file timestamps or start time or 
    # similar  before setting hash
    # Checks all other elements under doc_process_root for hash collisions
    
    #

    ourprocesshash=hashlib.sha1(etree.tostring(process_el)).hexdigest()
    
    # Check for hash collisions
    other_processes=xmldocu.xpathcontext(doc_process_root,"dcp:process")
    for other_process in other_processes:
        if xmldocu.hasattr(other_process,"uuid"):
            other_uuid=xmldocu.getattr(other_process,"uuid")
            if other_uuid==ourprocesshash:
                raise ValueError("Hash collision!") # should never happen unless you inadequately add unique stuff
            pass
        pass
    xmldocu.setattr(process_el,"uuid",ourprocesshash)
    return ourprocesshash



#class wrap_element_by_id(object):
#    """This class is a hashable wrapper around the id of another object
#       It is intended as immutable (although the other object may not be)"""
#    doc=None
#    obj=None
#    
#    def __hash__(self):
#        return id(self.obj)
#    
#    def __cmp__(self,other):
#        return id(self.obj) - id(other.obj)
#
#    def __init__(self,doc,obj):
#        self.doc=doc
#        self.obj=obj
#        pass
    
        


ProvenanceDB={}
# ProvenanceDB is the in-memory provenance database of a
# running process. It tracks elements that have been Used 
# and elements that are Generated.
#
# It is a dictionary, indexed by id(threading.current_thread)
# Each element of the dictionary is the list of 
# nested provenance tracking contexts for that thread. 
#
# We are always working on the last context (which will 
# be merged in with the previous context when complete)
# 
# A context is a 3-element tuple: 
# The first member is a set of document ETXpaths of XML elements, 
# that have been created or modified ("Generated"); the second 
# member is a set of tuples of (canonicalized ETXpaths of elements,element wasgeneratedby uuids or mtime)
# that have been accessed ("Used") by this process.
# The third member is a dictionary, by element object id, of a tuple: (the element, the corresponding element ETXpath) for all XML elements that have been created or modified
#
# These will become the contents of the dcp:process tag 
#


# To implement: Provenance tracking with xmldoc and dg_file
def starttrackprovenance():
    global ProvenanceDB # declaration not strictly needed because we never reassign it

    our_tid=id(threading.current_thread)
    if our_tid in ProvenanceDB:
        ourdb=ProvenanceDB[our_tid]
        pass
    else :
        ourdb=[]
        ProvenanceDB[our_tid]=ourdb
        pass
    
    ourcontext=(set([]),set([]),{})
    ourdb.append(ourcontext)
    

    pass

def warnnoprovenance(message):
    global ProvenanceDB
    
    our_tid=id(threading.current_thread)
    if our_tid in ProvenanceDB:
        ourdb=ProvenanceDB[our_tid]
        if len(ourdb) > 0:
            sys.stderr.write("Provenance warning: %s\n.Stack trace follows:\n" % (message))
            traceback.print_stack(inspect.currentframe().f_back.f_back,file=sys.stderr)
            pass
        pass

    pass

def remove_current_reference(reference_set,element_and_canonpath_dict,doc,element):
    # element_and_canonpath dict is a dictionary by id(element) of (element,canonpath) tuples
    # search through reference_set to see if element is referenced.
    # if so, remove that reference

    if id(element) in element_and_canonpath_dict:
        (gotelement,gotcanonpath)=element_and_canonpath_dict[id(element)]
        if gotelement is element:
            # if this is really referring to the same element
            # remove existing canonpath in reference_set (in case
            # we will be adding a replacement that may be different, e.g.
            # if an index field has changed)
            if gotcanonpath in reference_set:
                reference_set.remove(gotcanonpath)
                pass

            # since it is gone, remove the reference from element_and_canonpath_dict as well
            del element_and_canonpath_dict[id(element)]
            pass
        pass
    
    #for elementpath in list(reference_set):
    #    ETXobj=etree.ETXPath(elementpath)
    #    foundelement=ETXobj(doc)
    #    if len(foundelement) != 1:
    #        raise ValueError("Non-unique result identifying provenance reference %s" % (elementpath))
    #    if foundelement is element:
    #        reference_set.remove(elementpath)
    #        pass
    #    pass
    pass

def elementgenerated(doc,element):
    # Call this for each XML element created/modified, so that we can
    # mark its dependencies later
    #
    # Best to call this (or call again) after element has had attributes,
    # content, etc. assigned so that we can get the best possible index for it. 

    # !!! Should also check if there is any existing provenance 
    # pointing at this element -- if so we need to invalidate
    # those dependent elements

    # ... Not strictly necessary because references to tags that 
    # are replaced will reference the old WasGeneratedBy, indicating
    # that the link is broken.
    global ProvenanceDB
    
    if doc is None: 
        return

    our_tid=id(threading.current_thread)
    if our_tid in ProvenanceDB:
        ourdb=ProvenanceDB[our_tid]
        if len(ourdb) > 0:
            remove_current_reference(ourdb[-1][0],ourdb[-1][2],doc,element) # Remove current reference because that naming may be obsolete.
            canonpath=canonicalize_path.getelementetxpath(doc,element)
            ourdb[-1][0].add(canonpath)
            ourdb[-1][2][id(element)]=(element,canonpath)
            pass
        pass

    pass

def xmldocelementaccessed(xmldocu,element):
    if xmldocu is None:
        return
    
    elementaccessed(xmldocu._filename,xmldocu.doc,element)
    pass

def elementaccessed(filepath,doc,element):
    # Call this for each XML element accessed (read) to log the provenance
    global ProvenanceDB
    
    our_tid=id(threading.current_thread)
    if our_tid in ProvenanceDB:
        ourdb=ProvenanceDB[our_tid]
        if len(ourdb) > 0:
            canonical_etxpath=canonicalize_path.create_canonical_etxpath(filepath,doc,element)
            uuids=""
            uuidsname=DCP+"wasgeneratedby"
            if uuidsname in element.attrib:
                uuids=element.attrib[uuidsname]
                pass
                
            ourdb[-1][1].add((canonical_etxpath,uuids))
            pass
        pass
    pass
    
def fileaccessed(filepath): 
    # Call this for each non-XML file accessed (read) to log the provenance
    global ProvenanceDB
    
    our_tid=id(threading.current_thread)
    if our_tid in ProvenanceDB:
        ourdb=ProvenanceDB[our_tid]
        if len(ourdb) > 0:
            mtime=datetime.datetime.fromtimestamp(os.path.getmtime(filepath),dg_timestamp.UTC()).isoformat()
            ourdb[-1][1].add((canonicalize_path.create_canonical_etxpath(filepath,None,None),"mtime=%s" % (mtime)))
            pass
        pass
    pass
    

def finishtrackprovenance():
    global ProvenanceDB # declaration not strictly needed because we never reassign it

    ourdb=ProvenanceDB[id(threading.current_thread)]

    latestcontext=ourdb.pop()
    # latestcontext[0] is set of wrapped elements
    # latestcontext[1] is set of canonical xpath provenances
    # latestcontext[2] is dictionary by element ids of (element object,canonpath)
    
    if len(ourdb) > 0:
        # Have parent context
        # Merge in context we are popping with parent
        prevcontext=ourdb[-1]
        prevcontext[0].update(latestcontext[0]) # update set
        prevcontext[1].update(latestcontext[1]) # update set
        prevcontext[2].update(latestcontext[2]) # update dictionary

        pass
        
    # should return set of canonicalized ETxpaths representing wrapped modified elements, set of (canonicalized etxpaths,uuids_or_mtime_string) representing provenance
    return (latestcontext[0] ,latestcontext[1])  # currently omits dictionary of element ids

def writeprocessprovenance(doc,rootprocesspath,parentprocesspath,referenced_elements):
    # Create dcp:process element that contains dcp:used tags listing all referenced elements 

    ourcanonicalname=canonicalize_path.canonicalize_path(doc.filename)

    rootprocess_el=doc.restorepath(rootprocesspath)
    parentprocess_el=doc.restorepath(parentprocesspath)
    process_el=doc.addelement(parentprocess_el,"dcp:process")

    refdoccache={}  # Dictionary of referenced documents... so we don't 
                    # have to reparse for each element

    refdoccache[ourcanonicalname]=doc  # put ourselves in the document cache

    for (element_etxpath,uuids_or_mtime) in referenced_elements:
        (filepath,etxpath)=canonicalize_path.canonical_etxpath_break_out_file(element_etxpath)
        if etxpath != "": # Element reference
            used_el=reference_etxpath(doc,process_el,"dcp:used",rootprocess_el.getparent(),element_etxpath,warnlevel="error")
            # supply wasgeneratedby uuid(s) of referenced elements in the usedwasgeneratedby attribute
            if len(uuids_or_mtime) > 0:
                assert(not(uuids_or_mtime.startswith("mtime=")))
                doc.setattr(used_el,"usedwasgeneratedby",uuids_or_mtime)
                pass
                
            pass
        else :
            # etxpath=="".. Just dependent on the file
            assert(uuids_or_mtime=="" or uuids_or_mtime.startswith("mtime="))
            used_el=reference_file(doc,process_el,"dcp:used",rootprocess_el.getparent(),filepath,warnlevel="error")
            if len(uuids_or_mtime) > 0:
                doc.setattr(used_el,"dcp:timestamp",uuids_or_mtime[6:])
                
                pass
            pass

        pass
    return process_el



def mark_modified_elements(xmldocu,modified_elements,process_uuid):
    # !!! fixme... shouldn't use xmldocu.getattr or xmldocu.setattr because we
    # don't want to track the provenance of the provenance
    for modified_element_etxpath in modified_elements:
        ETXobj=etree.ETXPath(modified_element_etxpath)
        foundelement=ETXobj(xmldocu.doc)
        #sys.stderr.write("foundelement=%s\n" % (str(foundelement)))
        if len(foundelement) != 1:
            raise ValueError("Non-unique result identifying provenance reference %s" % (modified_element_etxpath)) # etree.tostring(xmldocu.doc)))

        # oldwgb=xmldocu.getattr(foundelement[0],"dcp:wasgeneratedby","")
        # xmldocu.setattr(foundelement[0],"dcp:wasgeneratedby",oldwgb+"uuid="+process_uuid+";")

        # read out "dcp:wasgeneratedby" attribute of foundelement[0]
        if DCP+"wasgeneratedby" in foundelement[0].attrib:
            oldwgb=foundelement[0].attrib[DCP+"wasgeneratedby"]
            pass
        else:
            oldwgb=""
            pass

        
        # rewrite "dcp:wasgeneratedby" tag with this process uuid attached
        foundelement[0].attrib[DCP+"wasgeneratedby"]=oldwgb+"uuid="+process_uuid+";"
        
        pass
    pass

def find_process_el(xmldocu,processdict,element,uuidcontent):
    # Find the process element referred to by uuidcontent of element
    # return canonical etxpath

    # processdict from checkprovenance, below

    if uuidcontent in processdict:
        return processdict[uuidcontent][0]  # return etxpath from processdict

    workelement=element   # start first with children of our node in search for <dcp:process> element with matching uuid
    process=None

    while process is None:
        processlist=workelement.xpath("dcp:process",namespaces={"dcp":dcp})
        for processtag in processlist:
            # if "uuid" in processtag.attrib: 
            #     print "%s vs %s" % (processtag.attrib["uuid"],uuidcontent)
            #     pass
            if "uuid" in processtag.attrib and processtag.attrib["uuid"]==uuidcontent:
                process=processtag # Match!
                break
            processsublist=processtag.xpath(".//dcp:process[@uuid=\"%s\"]" % (uuidcontent),namespaces={"dcp": dcp})
            # print "sublist constraint: .//dcp:process[@uuid=\"%s\"]" % (uuidcontent)
            # print "len(processsublist)=%d" % (len(processsublist))
            if len(processsublist) > 1: 
                raise IndexError("Multiple dcp:process tags matching uuid %s." % (uuidcontent))
            if len(processsublist) == 1:
                process=processsublist[0] # Match!
                break
            pass
        workelement=workelement.getparent()
        if workelement is None and process is None: 
            # reached top of tree
            return None
        pass
    # print "Success!"

    return canonicalize_path.create_canonical_etxpath(xmldocu._filename,xmldocu.doc,process)

def checkallprovenance(xmldocu):
    # xmldocu must be locked in memory 
    docdict={}
    processdict={}
    processdictbypath={}
    processdictbyusedelement={}
    elementdict={}

    globalmessagelists={"error": [],
                        "warning":  [],
                        "info": [],
                        "none": []}
    
    treeroot=xmldocu.doc.getroot()
    for descendent in iterelementsbutskip(treeroot,DCP+"process"):

        refuuids_or_mtime=None
        if DCP+"wasgeneratedby" in descendent.attrib: 
            refuuids_or_mtime=str(descendent.attrib[DCP+"wasgeneratedby"])
            pass
        else : 
            globalmessagelists["warning"].append("Element %s in file %s does not have dcp:wasgenerateby provenance" % (canonicalize_path.etxpath2human(canonicalize_path.getelementetxpath(xmldocu.doc,descendent),nsmap=xmldocu.nsmap),xmldocu._filename))
            pass
        element_etxpath=canonicalize_path.create_canonical_etxpath(xmldocu._filename,xmldocu.doc,descendent)
        checkprovenance(element_etxpath,refuuids_or_mtime,nsmap=xmldocu.nsmap,docdict=docdict,processdict=processdict,processdictbypath=processdictbypath,processdictbyusedelement=processdictbyusedelement,elementdict=elementdict,globalmessagelists=globalmessagelists)
        pass

    # merge all messages into totalmessagelists...
    # element messages:
    totalmessagelists=copy.deepcopy(globalmessagelists)
    for elementinfo in elementdict:
        (processuuidlist,messagelists)=elementdict[elementinfo]
        for messagekey in messagelists:
            totalmessagelists[messagekey].extend(messagelists[messagekey])
            pass
        pass

    # process messages: 
    for processuuid in processdict: 
        (processpath,elementinfolist,messagelists,parent_process_uuid_or_None)=processdict[processuuid]
        for messagekey in messagelists:
            totalmessagelists[messagekey].extend(messagelists[messagekey])
            pass
        
        pass

    return  (docdict,processdict,processdictbypath,processdictbyusedelement,elementdict,globalmessagelists,totalmessagelists)

def find_process_value_or_ancestor(process_el,tagpath,default=AttributeError("Could not find tag")):
    # tag should use dcp: prefix
    # print "tag:",tag
    gottags=process_el.xpath(tagpath,namespaces={"dcp":dcp})
    
    if len(gottags)==0: 
        parent=process_el.getparent()

        if parent.tag==DCP+"process":
            return find_process_value_or_ancestor(parent,tagpath,default=default)
        
        if isinstance(default,BaseException):
            raise default
        else: 
            return default
        pass
    
    if len(gottags) > 1:
        raise ValueError("Multiple tags: %s" % (unicode(gottags)))

    return gottags[0].text


def addquotesifnecessary(arg):
    # Does not do robust quoting and escaping, but this should
    # cover likely circumstances
    okchars=set(string.digits+string.letters+"-_/.:")

    if set(arg).issubset(okchars):
        return arg
    else: 
        return "\'"+arg+"\'"
    pass

def removequotesifable(arg):
    # Does not do robust quoting and escaping, but this should
    # cover likely circumstances

    startindex=arg.find('\'')
    endindex=arg.rfind('\'')
    
    usearg=arg[(startindex+1):endindex]
    
    okchars=set(string.digits+string.letters+"-_/.:")

    if set(usearg).issubset(okchars):
        return usearg
    else: 
        return arg[startindex:(endindex+1)]
    pass


def getnonprocessparent(foundelement):
    # Find the first non-dcp:process parent of the specified element
    # and return the node itself and the path from foundelement to 
    # that node. 
    #
    # This is useful because dcp:process relative ETXPaths are relative
    # to the first non-process parent of the dcp:process tag. 
    # So you take the location of the dcp:process tag, 
    # append the path returned by this function, 
    # and append the relative etxpath, 
    # and finally canonicalize the result
    
    context_node=foundelement.getparent()
    append_path=".."
    while context_node.tag==DCP+"process":
        context_node=context_node.getparent()
        append_path+="/.."
        pass
    return (context_node,append_path)

def suggest(docdict,processdict,processdictbypath,processdictbyusedelement,elementdict,globalmessagelists,totalmessagelists):

    suggestion_processes=set([])
    suggestions=set([])
    suggestions_by_prxfile={}
    prxfiles=set([])

    # print("type(processdict)=%s" % (str(type(processdict))))

    for elementinfo in elementdict:
        (etxpath,uuid_or_mtime)=elementinfo
        (processuuidlist,messagelists)=elementdict[elementinfo]
        for message in messagelists["error"]: 
            if message.startswith("WasGeneratedBy process uuids do not match for"):
                if elementinfo in processdictbyusedelement:
                    rerunprocess_uuids=processdictbyusedelement[elementinfo]
                    for rerunprocess_uuid in rerunprocess_uuids: 
                        if rerunprocess_uuid not in processdict: 
                            sys.stderr.write("Warning: process uuid %s not in processdict (?)\n" % (rerunprocess_uuid))
                            continue
                        (processpath,usedelements,messagelists,parent_uuid_or_None)=processdict[rerunprocess_uuid]
                        if processpath in suggestion_processes: 
                            continue # already handled this process
                        suggestion_processes.add(processpath) # mark this one as handled

                        (processfilepath,processetxpath)=canonicalize_path.canonical_etxpath_break_out_file(processpath)
                        if processfilepath  not in docdict:
                            sys.stderr.write("Warning: File %s not in docdict (?)\n" % (processfilepath))
                            continue

                        xmldocu=docdict[processfilepath]
                        
                        ETXobj=etree.ETXPath(processetxpath)
                        # print "xmldocu=",str(xmldocu)
                        foundelement=ETXobj(xmldocu.doc) 
                        if len(foundelement)==0:
                            sys.stderr.write("Warning: Could not find process path %s in file %s\n" % (processetxpath,processfilepath))
                            continue
                        assert(len(foundelement)==1)  # This would be triggered by a hash collision. Should be separately diagnosed in processing. 
                        # foundelement[0] is the dcp:process tag
                    
                        
                        inputfile=find_process_value_or_ancestor(foundelement[0],"dcp:inputfile",default="")
                        action=find_process_value_or_ancestor(foundelement[0],"dcp:action",default="")
                        prxfile=find_process_value_or_ancestor(foundelement[0],"dcp:wascontrolledby/dcp:prxfile",default="")

                        # prxfile is path relative to the first non-dcp:process ancestor
                        
                        (context_node,append_path)=getnonprocessparent(foundelement[0])
                        foundelement_etxpath=canonicalize_path.create_canonical_etxpath(xmldocu._filename,xmldocu.doc,foundelement[0])
                        # print "foundelement_etxpath=",foundelement_etxpath
                        # print "append_path=",append_path
                        # print "prxfile=",prxfile
                        prxfile_path=canonicalize_path.canonicalize_etxpath(canonicalize_path.canonical_etxpath_join(foundelement_etxpath,append_path,prxfile))
                        # print "prxfile_path=",prxfile_path

                        (prxfile_filepath,prxfile_etxpath)=canonicalize_path.canonical_etxpath_break_out_file(prxfile_path)
                        # print "Filepath,ETXpath=",prxfile_filepath,prxfile_etxpath
                        assert(prxfile_etxpath=="") # should be blank as the PRX file is, indeed, its own file



                        #argv=find_process_value_or_ancestor(foundelement[0],"dcp:argv",default="")
                        #args=" ".join([removequotesifable(arg) for arg in csv.reader([argv[1:-1]]).__iter__().next()])
                    
                        prxfiles.add(prxfile_filepath)
                        if not prxfile_filepath in suggestions_by_prxfile:
                            suggestions_by_prxfile[prxfile_filepath]=set([])
                            pass
                        suggestions_by_prxfile[prxfile_filepath].add((inputfile,action))
                        pass
                    pass
                pass

            pass
                    
        pass
    
    # go through each prxfile and suggest steps in order
    # We don't worry about sorting prxfiles, because
    # we don't expect to have multiple prxfiles
    for prxfile_filepath in prxfiles: 
        prxfile_dir=os.path.split(prxfile_filepath)[0]
        prxfile_doc=xmldoc.xmldoc.loadfile(prxfile_filepath,nsmap={"prx":"http://thermal.cnde.iastate.edu/datacollect/processinginstructions","xlink":"http://www.w3.org/1999/xlink"})
        prxfile_steps=prxfile_doc.xpath("prx:step")
        prxfile_inputfiles=prxfile_doc.xpath("prx:inputfile")
        for step in prxfile_steps:
            stepaction=dc_process_common.getstepname(prxfile_doc,step)
            refdinputfiles=[inputfile for (inputfile,action) in suggestions_by_prxfile[prxfile_filepath] if action==stepaction]
            for refdinputfile in refdinputfiles:
                suggestions_by_prxfile[prxfile_filepath].remove((refdinputfile,stepaction))
                # refdinputfile is a complete path
                # dc_process takes <inputfile> tag of prxfile
                # Search for match between refdinputfile and the inputfiles specified in prx document
                foundinputfile=False
                for prxinputfile_el in prxfile_inputfiles:
                    prxinputfile_fullpath=prxfile_doc.get_href_fullpath(prxinputfile_el)
                    # prxinputfile=prxfile_doc.gettext(prxinputfile_el)
                    # if os.path.isabs(prxinputfile):
                    #     prxinputfile_fullpath=prxinputfile
                    #     pass
                    # else: 
                    #     prxinputfile_fullpath=os.path.join(prxfile_dir,prxinputfile)
                    #     pass
                    prxinputfile_canonpath=canonicalize_path.canonicalize_path(prxinputfile_fullpath)
                    refdinputfile_canonpath=canonicalize_path.canonicalize_path(refdinputfile)
                    # print "prxinputfile=",prxinputfile_canonpath
                    # print "refdinputfile=",refdinputfile_canonpath

                    if prxinputfile_canonpath==refdinputfile_canonpath:
                        foundinputfile=True
                        suggestions.add(("Rerun step %s on file %s." % (stepaction,inputfile),"dc_process -s %s -f %s %s" % (addquotesifnecessary(stepaction),addquotesifnecessary(prxinputfile_fullpath),addquotesifnecessary(prxfile_filepath))))
                        break
                        
                    pass
                if not foundinputfile: 
                    sys.stderr.write("Could not find reference to input file %s in %s" % (refdinputfile,prxfile_filepath))
                    pass
                pass
            pass
        for (inputfile,stepaction) in suggestions_by_prxfile[prxfile_filepath]:
            sys.stderr.write("Unknown (inputfile,stepname) for %s: (%s,%s)\n" % (prxfile_filepath,inputfile,stepaction))
            pass
        pass
    return suggestions


def checkprovenance(element_etxpath,refuuids_or_mtime,nsmap={},referrer_etxpath="",warnlevel="error",docdict=None,processdict=None,processdictbypath=None,processdictbyusedelement=None,elementdict=None,globalmessagelists=None):
    # Find the provenance of element_etxpath -- which should be a canonical etxpath
    # refuuids_or_mtime is None or the expected "uuid=" or "mtime=" provenance of this particular element

    # docdict, processdict, processdictbypath, processdictbyusedelement, elementdict, and global messagelists should be empty. They will be filled
    # 
    # docdict: cached dictionary by file name of xmldoc documents
    # processdict: cached dictionary by uuid of (full paths to dcp:process elements, [list of (element etxpath,uuid_or_mtime)],messagelists,parent_process_uuid_or_None)   ... parent process is implicit WasControlledBy
    # processdictbypath: dictionary by etxpath of uuids for processdict
    # processdictbyusedelement: dictionary by (element etxpath,uuid_or_mtime) of [list of uuids for processes that used that element ]
    # elementdict dictionary by (etxpath,uuid_or_mtime) tuples that we have processed of ([list of process uuids],messagelists)

    # messagelists & globalmessagelists: dictionary by error type of lists of error messages

    # Currently ignore pymodule references. 

    if refuuids_or_mtime is not None: 
        refuuids_or_mtime=str(refuuids_or_mtime) # in case it is some sort of alternate string
        pass

    if docdict is None: 
        docdict={}
        pass
    
    if processdict is None:
        processdict={}
        pass

    if processdictbypath is None:
        processdictbypath={}
        pass

    if processdictbyusedelement is None:
        processdictbyusedelement={}
        pass

    if elementdict is None:
        elementdict={}
        pass

    if globalmessagelists is None:
        globalmessagelists={"error": [],
                            "warning":  [],
                            "info": [],
                            "none": []}
        pass

    messagelisttemplate={"error": [],
                         "warning":  [],
                         "info": [],
                         "none": []}

    
    # fh=file("/tmp/provlog","a")
    # fh.write(element_etxpath+"\t"+str(refuuids_or_mtime)+"\n")
    # fh.close()

    if (element_etxpath,refuuids_or_mtime) in elementdict:
        return # already processed this element
    # NOTE: Can probably optimize here. When refuuid_or_mtime is passed as None -- implying current element -- is there a way to automatically identify if we have previously processed it?... less of an issue now that checkallprovenance passes refuuid_or_mtime 
    


    if element_etxpath in processdictbypath:
        return # already processed this dcp:process element
        
    # print "element_etxpath=",element_etxpath
    (filepath,etxpath)=canonicalize_path.canonical_etxpath_break_out_file(element_etxpath)

    if etxpath != "":
        # not just a file...
        # load file and extract provenance uuids if possible


        if refuuids_or_mtime is not None and refuuids_or_mtime.startswith("mtime="):
            errmsg="Attempting to specify mtime provenance %s for an element %s in provenance of %s" % (refuuids_or_mtime,canonicalize_path.etxpath2human(etxpath,nsmap),canonicalize_path.etxpath2human(element_etxpath,nsmap))
            if referrer_etxpath in processdictbypath: 
                processdict[processdictbypath[referrer_etxpath]][2]["error"].append(errmsg)
                pass
            else: 
                globalmessagelists["error"].append(errmsg)
                pass
            pass

        if filepath in docdict:
            xmldocu=docdict[filepath]
            pass
        else :
            xmldocu=None
            try : 
                xmldocu=xmldoc.xmldoc.loadfile(filepath)
                pass
            except IOError:
                errmsg="File %s missing for %s referred by %s." % (filepath,canonicalize_path.etxpath2human(element_etxpath,nsmap),canonicalize_path.etxpath2human(referrer_etxpath,nsmap))
                sys.stderr.write(errmsg+"\n")
                if referrer_etxpath in processdictbypath: 
                    processdict[processdictbypath[referrer_etxpath]][2]["error"].append(errmsg)
                    pass
                else : 
                    globalmessagelists["error"].append(errmsg)
                    pass
                pass
            docdict[filepath]=xmldocu
            pass
        if xmldocu is None:
            return # nothing to do... error would have been diagnosed above

        ETXobj=etree.ETXPath(etxpath)
        # print "xmldocu=",str(xmldocu)
        foundelement=ETXobj(xmldocu.doc)
        if len(foundelement)==0:
            elementdict[(element_etxpath,refuuids_or_mtime)]=([],copy.deepcopy(messagelisttemplate)) # mark that we have done this
            # Add error message to messagelists
            elementdict[(element_etxpath,refuuids_or_mtime)][1]["error"].append("Object %s missing when accessing %s in %s referred by %s." % (canonicalize_path.etxpath2human(element_etxpath,nsmap),canonicalize_path.etxpath2human(etxpath,nsmap),filepath,canonicalize_path.etxpath2human(referrer_etxpath,nsmap)))
        elif len(foundelement) > 1:
            elementdict[(element_etxpath,refuuids_or_mtime)]=([],copy.deepcopy(messagelisttemplate)) # mark that we have done this
            # add error to messagelists
            elementdict[(element_etxpath,refuuids_or_mtime)][1]["error"].append("Object %s not unique when accessing %s in %s referred by %s." % (canonicalize_path.etxpath2human(element_etxpath,nsmap),canonicalize_path.etxpath2human(etxpath,nsmap),filepath,canonicalize_path.etxpath2human(referrer_etxpath,nsmap)))
            pass
        elif foundelement[0].tag==DCP+"process":
            # dcp:process tag ! 
            

            if not "uuid" in foundelement[0].attrib:
                globalmessagelists["error"].append("process %s has no uuid attribute" % (canonicalize_path.etxpath2human(element_etxpath,nsmap)))
                processdictbypath[element_etxpath]=None # mark that we have done this
                pass
            else :
                uuid=foundelement[0].attrib["uuid"]
                
                parent_uuid=None
                parenttag=foundelement[0].getparent()
                if parenttag.tag==DCP+"process":
                    if "uuid" in parenttag.attrib: 
                        parent_uuid=parenttag.attrib["uuid"]
                        pass
                    else : 
                        globalmessagelists["error"].append("parent process of process %s has no uuid attribute" % (canonicalize_path.etxpath2human(element_etxpath,nsmap)))
                        pass
                    pass

                # Put this in processdict
                processdict[uuid]=(element_etxpath,[],copy.deepcopy(messagelisttemplate),parent_uuid)
                processdictbypath[element_etxpath]=uuid # mark that we have done this
                
                for usedtag in foundelement[0].xpath("dcp:used",namespaces={"dcp": dcp}):
                    if not "type" in usedtag.attrib:
                        # add error message to message list
                        processdict[uuid][2]["error"].append("dcp:used tag %s does not have a type attribute" % (canonicalize_path.etxpath2human(canonicalize_path.create_canonical_etxpath(xmldocu._filename,xmldocu.doc,usedtag),nsmap)))
                        continue

                    # Extract common attributes
                    subwarnlevel="error"
                    if "warnlevel" in usedtag.attrib:
                        subwarnlevel=usedtag.attrib["warnlevel"]
                        pass

                    if usedtag.attrib["type"]=="pymodule":
                        # Reference to a python module
                        # Do nothing for now as we don't currently pay attention to python modules
                        pass
                    elif usedtag.attrib["type"]=="etxpath" or usedtag.attrib["type"]=="fileetxpath":
                        # Reference to a clark-notation xpath

                        # Context of the etxpath is the parent of the nested dcp:process nodes.
                        (context_node,append_path)=getnonprocessparent(foundelement[0])
                            
                        # print "For newetxpath, element_etxpath=",element_etxpath
                        # print "append_path=",append_path
                        # print "usedtag.text=",usedtag.text
                        # print "joined=",canonicalize_path.canonical_etxpath_join(element_etxpath,append_path,usedtag.text)
                        newetxpath=canonicalize_path.canonicalize_etxpath(canonicalize_path.canonical_etxpath_join(element_etxpath,append_path,usedtag.text))
                        if "absetxpath" in usedtag.attrib and newetxpath != usedtag.attrib["absetxpath"]:
                            # add error message to message list
                            processdict[uuid][2]["warning"].append("Relative ETXPath %s on %s resolves to %s which does not match absolute path %s. Using relative path.\n" % (usedtag.text,canonicalize_path.etxpath2human(canonicalize_path.create_canonical_etxpath(xmldocu._filename,xmldocu.doc,usedtag),nsmap),newetxpath,usedtag.attrib["absetxpath"]))
                            pass
                        
                        uuids_or_mtime=None
                        if "usedwasgeneratedby" in usedtag.attrib:
                            uuids_or_mtime=str(usedtag.attrib["usedwasgeneratedby"])
                            pass

 
                        # Mark this process as referring to this element
                        processdict[uuid][1].append((newetxpath,uuids_or_mtime))
                        if not (newetxpath,uuids_or_mtime) in processdictbyusedelement:
                            processdictbyusedelement[(newetxpath,uuids_or_mtime)]=[]
                            pass
                        processdictbyusedelement[(newetxpath,uuids_or_mtime)].append(uuid)
                        

                        # Make recursive call to evaluate this tag that was "used" by the process!
                        # print "recursive call for used element"
                            
                        checkprovenance(newetxpath,uuids_or_mtime,nsmap=nsmap,referrer_etxpath=element_etxpath,warnlevel=subwarnlevel,docdict=docdict,processdict=processdict,processdictbypath=processdictbypath,processdictbyusedelement=processdictbyusedelement,elementdict=elementdict,globalmessagelists=globalmessagelists)
                        pass
                    else:
                        # add error message to message list
                        processdict[uuid][2]["error"].append("dcp:used tag %s does has unknown type attribute %s" % (canonicalize_path.etxpath2human(canonicalize_path.create_canonical_etxpath(xmldocu._filename,xmldocu.doc,usedtag),nsmap),usedtag.attrib["type"]))
                        pass
                        
                    pass

                
                pass

        else:

            # no specific tag. Look for recorded provenance
            uuidstring=str(xmldocu.getattr(foundelement[0],"dcp:wasgeneratedby","",namespaces={"dcp": dcp}))
            if refuuids_or_mtime is not None and refuuids_or_mtime != uuidstring:
                # refuuids_or_mtime is what we were lead to believe (by the calling dcp:process) generated this element
                # uuidstring is what actually generated this element

                # it is the calling dcp:process, really, that has a problem
                # !!! Should diagnose this better by looking up the two process elements !!!
                # create elementdict entry right away so we can put the error message into it
                elementdict[(element_etxpath,refuuids_or_mtime)]=([],copy.deepcopy(messagelisttemplate)) # mark that we have done this, but mark the referred element as that is the real provenance

                # sys.stderr.write("Compare \"%s\"\n        \"%s\"\n" % 

                elementdict[(element_etxpath,refuuids_or_mtime)][1][warnlevel].append("WasGeneratedBy process uuids do not match for %s: %s specified in %s vs. %s actual. Referenced version has probably been overwritten" % (canonicalize_path.etxpath2human(element_etxpath,nsmap),refuuids_or_mtime,canonicalize_path.etxpath2human(referrer_etxpath,nsmap),uuidstring))

                uuidstring=refuuids_or_mtime # mark the referred element as that is the real provenance

                pass
            else  :
                elementdict[(element_etxpath,uuidstring)]=([],copy.deepcopy(messagelisttemplate)) # mark that we have done this
                pass
                

            if uuidstring != "":
                # This element wasgeneratedby ...
                # recursively investigate its provenance
                uuids=uuidstring.split(";")
                for uuid in uuids:
                    if uuid=="":
                        continue # skip blanks, such as trailing final ';'
                    if not uuid.startswith("uuid="):
                        # store error message in elementdict messagelist
                        elementdict[(element_etxpath,uuidstring)][1]["error"].append("uuid string \"%s\" specified in %s or %s is not valid" % (uuid,canonicalize_path.etxpath2human(element_etxpath,nsmap),canonicalize_path.etxpath2human(referrer_etxpath,nsmap)))
                        continue
                    

                    try: 
                        process_el_etxpath=find_process_el(xmldocu,processdict,foundelement[0],uuid[5:]) # !!! need to write find_process_el
                        pass
                    except IndexError as e:
                        # store error message in elementdict messagelist
                        elementdict[(element_etxpath,uuidstring)][1]["error"].append(str(e))
                        pass
                    if process_el_etxpath is None:
                        # store error message in elementdict messagelist
                        elementdict[(element_etxpath,uuidstring)][1]["error"].append("Could not find dcp:process element for uuid %s when looking up %s (possibly specified in %s)" % (uuid,canonicalize_path.etxpath2human(element_etxpath,nsmap),canonicalize_path.etxpath2human(referrer_etxpath,nsmap)))
                        continue

                    elementdict[(element_etxpath,uuidstring)][0].append(uuid[5:]) # add this link to list for this element

                    # recursive call to handle dcp:process element
                    # print "recursive call for process element"
                    checkprovenance(process_el_etxpath,None,nsmap=nsmap,referrer_etxpath=element_etxpath,warnlevel=warnlevel,docdict=docdict,processdict=processdict,processdictbypath=processdictbypath,processdictbyusedelement=processdictbyusedelement,elementdict=elementdict,globalmessagelists=globalmessagelists)
                    
                        
                    pass
                
                pass
            pass
        pass
    else : 
        # etxpath==""
        # just a file

        elementdict[(element_etxpath,refuuids_or_mtime)]=([],copy.deepcopy(messagelisttemplate)) # mark that we have done this file

        if refuuids_or_mtime is not None and not (refuuids_or_mtime.startswith("mtime=")):
            # Add error message to elementdict messagelist
            elementdict[(element_etxpath,refuuids_or_mtime)][1]["error"].append("Attempting to specify uuid provenance %s for a file %s in proveance of %s" % (refuuids_or_mtime,filepath,canonicalize_path.etxpath2human(element_etxpath,nsmap)))
            pass


        if not os.path.exists(filepath):
            # Add error message to elementdict messagelist
            elementdict[(element_etxpath,refuuids_or_mtime)][1]["error"].append("Object %s missing when accessing  %s referred by %s." % (canonicalize_path.etxpath2human(element_etxpath,nsmap),filepath,canonicalize_path.etxpath2human(referrer_etxpath,nsmap)))
            pass
        else : 
            if refuuids_or_mtime is not None:
                mtime=datetime.datetime.fromtimestamp(os.path.mtime(filepath),dg_timestamp.UTC()).isoformat()
                if mtime != refuuids_or_mtime[6:]:
                    # Add error message to elementdict messagelist
                    elementdict[(element_etxpath,refuuids_or_mtime)][1][warnlevel].append("File modification times do not match for %s: %s specified in %s vs. %s actual" % (filepath,refuuids_or_mtime,canonicalize_path.etxpath2human(referrer_etxpath,nsmap),mtime))
                    pass
                pass
            pass
        pass
    pass
    
    
# code snippet for extracting provenance uuid from an canonicalized ETXpath:
junk="""
        refuuid=""
        (filepath,etxpath)=canonicalize_path.canonical_etxpath_break_out_file(element_etxpath)
        if etxpath != "":
            # load file and extract provenance uuids if possible
            if filepath in refdoccache:
                refdoc=refdoccache[filepath]
                pass
            else : 
                refdoc=xmldoc.xmldoc.loadfile(filepath)
                refdoccache[filepath]=refdoc
                pass
            refETXobj=etree.ETXPath(etxpath)
            foundrefelement=refETXobj(refdoc)
            if len(foundrefelement)==0:
                refuuid="object_missing"
                pass
            elif len(foundrefelement) > 1:
                refuuid="object_not_unique"
                pass
            else:
                refuuid=refdoc.getattr(foundrefelement[0],"dcp:wasgeneratedby","",namespaces={"dcp": dcp})
                pass
            pass
"""   



