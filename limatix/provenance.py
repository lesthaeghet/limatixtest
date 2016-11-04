# NOTE: always import this module EARLY in your list of imports, 
# as other modules need to be able to find it!

import os
import os.path
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
import collections

try:
    from cStringIO import StringIO
    pass
except ImportError:
    from io import StringIO
    pass


from . import timestamp as lm_timestamp
from . import canonicalize_path

from .canonicalize_path import href_context

# from . import xmldoc  # remove to eliminate circular reference
from .import processtrak_prxdoc

from lxml import etree
# from pytz import reference


try: 
    import builtins  # python3
    pass
except ImportError: 
    import __builtin__ as builtins # python2
    pass
    
if not hasattr(builtins,"basestring"):
    basestring=str  # python3
    unicode=str # python3
    pass


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


LIP="{http://limatix.org/provenance}"
lip="http://limatix.org/provenance"

DC="{http://limatix.org/datacollect}"
dc="http://limatix.org/datacollect"

global_nsmap={
    "dc": "http://limatix.org/datacollect",
    "lip": "http://limatix.org/provenance",
    "xlink":"http://www.w3.org/1999/xlink",
    }


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
        hostnamep=hostnameproc.communicate()[0].decode('utf-8').strip()
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
        timestamp=lm_timestamp.now().isoformat()
        pass
    doc.settext(starttime_el,timestamp)

def write_process_log(doc,process_el,status,stdoutstderrlog):
    # "status" shoudl be "success" or "exception" 
    log_el=doc.addelement(process_el,"lip:log")
    log_el.text=stdoutstderrlog
    log_el.attrib["status"]=status
    pass

def write_input_file(doc,process_el,inputfilehref):

    hrefc=inputfilehref.value()

    inpf_el=doc.addelement(process_el,"lip:inputfile")
    hrefc.xmlrepr(doc,inpf_el)  # Note no provenance written here because we use hrefc not dc_value

    
    
    pass

    

def write_process_info(doc,process_el):
    hostname_el=doc.addelement(process_el,"lip:hostname")
    doc.settext(hostname_el,determinehostname())
    doc.setattr(hostname_el,"pid",str(os.getpid()))
    if os.name=="posix":
        doc.setattr(hostname_el,"uid",str(os.getuid()))
        pass
    
    doc.setattr(hostname_el,"username",getpass.getuser())
    argv_el=doc.addelement(process_el,"lip:argv")
    doc.settext(argv_el,unicode(sys.argv)) # Save command line parameters
    pass


def reference_hrefcontext(doc,parent,tagname,contextelement,hrefc,warnlevel="error"):
    # Create a new element, named tagname, within parent, that references the file or element
    # specified as hrefc 
    element=doc.addelement(parent,tagname)
    hrefc.xmlrepr(doc,element)  # Note no provenance because we use hrefc not dc_value
    doc.setattr(element,"warnlevel",warnlevel)
    doc.setattr(element,"type","href")
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

    

def reference_file(doc,parent,tagname,contextelement,referencehrefc,warnlevel="error",timestamp=None,fragcanonsha256=None):
    # filecontext_xpath is "/"+outputroot.tag
    # warnlevel should be "none" "info", "warning", or "error" and represents when the 
    # reference to this file does not match the file itself, how loud the warning
    # should be

    #hrefc=referencehref.value()
    hrefc=referencehrefc

    
    element=doc.addelement(parent,tagname)

    
    #import pdb
    #pdb.set_trace()
    hrefc.xmlrepr(doc,element)  # Note no provenance because we use hrefc not dc_value

    # print("provenance.reference_file(%s,%s) -> xlink:href=%s" % (doc.getcontexthref().value().humanurl(),hrefc.humanurl(),element.attrib["{http://www.w3.org/1999/xlink}href"]))

    doc.setattr(element,"warnlevel",warnlevel)
    doc.setattr(element,"type","href")

    if timestamp is None:
        timestamp=datetime.datetime.fromtimestamp(os.path.getmtime(hrefc.getpath()),lm_timestamp.UTC()).isoformat()
        pass
    doc.setattr(element,"mtime",timestamp)
    
    if hrefc.has_fragment() and fragcanonsha256 is not None:
        doc.setattr(element,"fragcanonsha256",fragcanonsha256)
        pass
    
    
    doc.setattr(element,"warnlevel",warnlevel)
    # print etree.tostring(element)
    return element

def write_action(doc,process_el,action_name):
    action_el=doc.addelement(process_el,"lip:action")
    doc.settext(action_el,action_name)
    pass

def write_target(doc,process_el,target_hrefc):
    target_el=doc.addelement(process_el,"lip:target")
    target_hrefc.xmlrepr(doc,target_el)  # Note no provenance because we use hrefc not dc_value
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

    def __next__(self):  # python3
        return self.next()
    
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

            if "Element" not in retval.__class__.__name__:
                # not an element... perhaps a comment or processing instruction
                # ignore
                return self.next()

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
    # skipel is None or perhaps the lip:process element we have been creating
    # so that we don't list dependence on that

    for descendent in iterelementsbutskip(treeroot,skipel): #  iterate through descendents, but ignore the provenance tag structure we just created. 
        # print "descendent=%s" % (str(descendent))
        oldwgb=""
        if LIP+"wasgeneratedby" in descendent.attrib:
            oldwgb=descendent.attrib[LIP+"wasgeneratedby"]
            pass
        
        descendent.attrib[LIP+"wasgeneratedby"]=oldwgb + "uuid="+uuid+";"
        pass
    pass



def set_hash(xmldocu,doc_process_root,process_el):
    # MUST HAVE WRITTEN unique stuff such as file timestamps or start time or 
    # similar  before setting hash
    # Checks all other elements under doc_process_root for hash collisions
    
    #

    ourprocesshash=hashlib.sha1(etree.tostring(process_el)).hexdigest()
    
    # Check for hash collisions
    other_processes=xmldocu.xpathcontext(doc_process_root,"lip:process")
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
# The first member is a set of hrefc's of XML elements, 
# that have been created or modified ("Generated"); the second 
# member is a set of tuples of (hrefc's of elements,element wasgeneratedby uuids or mtime)
# that have been accessed ("Used") by this process.
# The third member is a dictionary, by element object id, of a tuple: (the element, the corresponding element hrefc) for all XML elements that have been created or modified
#
# These will become the contents of the lip:process tag 
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

def remove_current_reference(generated_reference_set,used_reference_set,element_and_hrefc_dict,xmldocu,element):
    # element_and_canonpath dict is a dictionary by id(element) of (element,hrefc) tuples
    # search through reference_set to see if element is referenced.
    # if so, remove that reference

    
    if id(element) in element_and_hrefc_dict:
        (gotelement,gothrefc)=element_and_hrefc_dict[id(element)]
        assert(gotelement is element)
        if gotelement is element:
            # if this is really referring to the same element
            # remove existing canonpath in reference_set (in case
            # we will be adding a replacement that may be different, e.g.
            # if an index field has changed)
            if gothrefc in generated_reference_set:
                # print("removing %s from generated_reference_set" % (gothrefc.humanurl()))

                generated_reference_set.remove(gothrefc)
                pass

            uuids=""
            uuidsname=LIP+"wasgeneratedby"
            if uuidsname in element.attrib:
                uuids=element.attrib[uuidsname]
                pass
            
            # print("gothrefc=%s; uuids=%s; %s" % (gothrefc.humanurl(),uuids,etree.tostring(element)))
            if (gothrefc,uuids) in used_reference_set:
                # print("removing %s from used_reference_set" % (gothrefc.humanurl()))
                
                used_reference_set.remove((gothrefc,uuids,))
                pass
            
            
            # since it is gone, remove the reference from element_and_hrefc_dict as well
            # print("removing %s from element_and_hrefc_dict" % (gothrefc.humanurl()))
            
            del element_and_hrefc_dict[id(element)]
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

def element_to_be_removed(xmldocu,element):
    # Eliminate any current reference to a removed element

    if xmldocu is None: 
        return
    
    our_tid=id(threading.current_thread)
    if our_tid in ProvenanceDB:
        ourdb=ProvenanceDB[our_tid]
        if len(ourdb) > 0:
            # print("elementremoved(): remove_current_reference(%s)" % (href_context.fromelement(xmldocu,element).humanurl()))
            remove_current_reference(ourdb[-1][0],ourdb[-1][1],ourdb[-1][2],xmldocu,element) # Remove current reference because that naming may be obsolete.
            # print("elementremoved(): done")
            
            pass
        pass
    pass

def print_current_used():
    ourdb=[]
    our_tid=id(threading.current_thread)
    if our_tid in ProvenanceDB:
        ourdb=ProvenanceDB[our_tid]
        # if len(ourdb) > 0:
        #     current_used=ourdb[-1][2]
        #     pass
        pass

    print("currently referenced elements")
    print("-----------------------------")
    for pos in range(len(ourdb)-1,-1,-1):
        print("Level %d:" % (pos))
        for objid in ourdb[pos][2]:
            (element,elementhrefc)=ourdb[pos][2][objid]

            if "{http://limatix.org/provenance}wasgeneratedby" in element.attrib:
                print("%s generated by %s" % (elementhrefc.humanurl(),element.attrib["{http://limatix.org/provenance}wasgeneratedby"]))
                pass
            else:
                print(elementhrefc.humanurl())
                pass
            pass
        pass
    print("currently used set")
    print("------------------")
    for pos in range(len(ourdb)-1,-1,-1):
        print("Level %d:" % (pos))
        usedset=ourdb[pos][1]
        for objid in usedset:
            (hrefc,uuids)=objid
            print("%s: uuids=%s" % (hrefc,uuids))
            pass
        pass
    
    pass

def elementgenerated(xmldocu,element):
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
    
    if xmldocu is None or xmldocu.filehref is None: 
        return

    if isinstance(element,etree._Comment) or isinstance(element,etree._ProcessingInstruction):
        return # Don't track provenance of comments or processing instructions
    

    our_tid=id(threading.current_thread)
    if our_tid in ProvenanceDB:
        ourdb=ProvenanceDB[our_tid]
        if len(ourdb) > 0:
            remove_current_reference(ourdb[-1][0],ourdb[-1][1],ourdb[-1][2],xmldocu,element) # Remove current reference because that naming may be obsolete.

            hrefc=href_context.fromelement(xmldocu,element)

            # print("provenance.elementgenerated(%s)" % hrefc.humanurl())
            
            ourdb[-1][0].add(hrefc)
            ourdb[-1][2][id(element)]=(element,hrefc)
            pass
        pass

    pass

def xmldocelementaccessed(xmldocu,element):
    global ProvenanceDB
    if xmldocu is None or xmldocu.filehref is None:
        return

    if isinstance(element,etree._Comment) or isinstance(element,etree._ProcessingInstruction):
        return # Don't track provenance of comments or processing instructions
 
   
    our_tid=id(threading.current_thread)
    if our_tid in ProvenanceDB:
        ourdb=ProvenanceDB[our_tid]
        if len(ourdb) > 0:

            hrefc=href_context.fromlxmldocelement(xmldocu.filehref.value(),xmldocu.doc,element)

            uuids=""
            uuidsname=LIP+"wasgeneratedby"
            if uuidsname in element.attrib:
                uuids=element.attrib[uuidsname]
                pass
                
            ourdb[-1][1].add((hrefc,uuids))
            ourdb[-1][2][id(element)]=(element,hrefc)
            pass
        pass

    
    pass

def elementaccessed(filehrefc,doc,element):
    # Call this for each XML element accessed (read) to log the provenance
    global ProvenanceDB
    
    our_tid=id(threading.current_thread)
    if our_tid in ProvenanceDB:
        ourdb=ProvenanceDB[our_tid]
        if len(ourdb) > 0:

            hrefc=href_context.fromlxmldocelement(filehrefc,doc,element)

            uuids=""
            uuidsname=LIP+"wasgeneratedby"
            if uuidsname in element.attrib:
                uuids=element.attrib[uuidsname]
                pass
                
            ourdb[-1][1].add((hrefc,uuids))
            ourdb[-1][2][id(element)]=(element,hrefc)
            pass
        pass
    pass
    
def fileaccessed(filehrefc): 
    # Call this for each non-XML file accessed (read) to log the provenance
    global ProvenanceDB
    
    our_tid=id(threading.current_thread)
    if our_tid in ProvenanceDB:
        ourdb=ProvenanceDB[our_tid]
        if len(ourdb) > 0:
            mtime=datetime.datetime.fromtimestamp(os.path.getmtime(filehrefc.getpath()),lm_timestamp.UTC()).isoformat()

            
            ourdb[-1][1].add((filehrefc,"mtime=%s" % (mtime)))
            # ourdb[-1][2][id(element)]=(element,hrefc)
            pass
        pass
    pass


def finishtrackprovenance():
    global ProvenanceDB # declaration not strictly needed because we never reassign it

    ourdb=ProvenanceDB[id(threading.current_thread)]

    latestcontext=ourdb.pop()
    # latestcontext[0] is set of wrapped elements
    # latestcontext[1] is set of hrefc provenances
    # latestcontext[2] is dictionary by element ids of (element object,hrefc)
    
    if len(ourdb) > 0:
        # Have parent context
        # Merge in context we are popping with parent
        prevcontext=ourdb[-1]
        prevcontext[0].update(latestcontext[0]) # update set
        prevcontext[1].update(latestcontext[1]) # update set
        prevcontext[2].update(latestcontext[2]) # update dictionary

        pass
        
    # should return set of hrefcs representing wrapped modified elements, set of (hrefcs,uuids_or_mtime_string) representing provenance
    return (latestcontext[0] ,latestcontext[1])  # currently omits dictionary of element ids

def writeprocessprovenance(doc,rootprocesspath,parentprocesspath,referenced_elements):
    # Create lip:process element that contains lip:used tags listing all referenced elements 

    
    # ourhrefc=doc.filehref.fragless()

    rootprocess_el=doc.restorepath(rootprocesspath)
    parentprocess_el=doc.restorepath(parentprocesspath)
    process_el=doc.addelement(parentprocess_el,"lip:process")

    # refdoccache={}  # Dictionary of referenced documents... so we don't 
    #                 # have to reparse for each element

    #  refdoccache[ourhrefc]=doc  # put ourselves in the document cache

    for (element_hrefc,uuids_or_mtime) in referenced_elements:

        used_el=reference_hrefcontext(doc,process_el,"lip:used",rootprocess_el.getparent(),element_hrefc,warnlevel="error")

        if len(uuids_or_mtime) > 0:
            if uuids_or_mtime.startswith("mtime="):
                # mtime
                doc.setattr(used_el,"lip:timestamp",uuids_or_mtime[6:])
                pass
            else:
                # uuid list
                assert(uuids_or_mtime.startswith("uuid="))
                doc.setattr(used_el,"usedwasgeneratedby",uuids_or_mtime)
                pass
            pass
        
        pass
    return process_el



def mark_modified_elements(xmldocu,modified_elements,process_uuid):
    # !!! fixme... shouldn't use xmldocu.getattr or xmldocu.setattr because we
    # don't want to track the provenance of the provenance
    # print("mark_modified_elements: %s" % (str([ str(modified_element) for modified_element in  modified_elements])))
    for modified_element_hrefc in modified_elements:

        # Doesn't currently support going across file boundaries
        assert(modified_element_hrefc.fragless()==xmldocu.filehref.value())

        
        foundelement=modified_element_hrefc.evaluate_fragment(xmldocu,None,noprovenance=True)

        
        #sys.stderr.write("foundelement=%s\n" % (str(foundelement)))
        
        if len(foundelement) != 1:
            msg="Non-unique result identifying provenance reference %s: Got %d elements." % (modified_element_hrefc.humanurl(),len(foundelement))
            msg+=" ".join("foundelement[%d]=%s" % (idx,href_context.fromelement(xmldocu,foundelement[idx]).humanurl()) for idx in range(len(foundelement)))
            raise ValueError(msg) # etree.tostring(xmldocu.doc)))

        # oldwgb=xmldocu.getattr(foundelement[0],"lip:wasgeneratedby","")
        # xmldocu.setattr(foundelement[0],"lip:wasgeneratedby",oldwgb+"uuid="+process_uuid+";")

        # read out "lip:wasgeneratedby" attribute of foundelement[0]
        if LIP+"wasgeneratedby" in foundelement[0].attrib:
            oldwgb=foundelement[0].attrib[LIP+"wasgeneratedby"]
            pass
        else:
            oldwgb=""
            pass

        
        # rewrite "lip:wasgeneratedby" tag with this process uuid attached
        foundelement[0].attrib[LIP+"wasgeneratedby"]=oldwgb+"uuid="+process_uuid+";"
        
        pass
    pass

def find_process_el(xmldocu,processdict,element,uuidcontent):
    # Find the process element referred to by uuidcontent of element
    # return hrefc

    # processdict from checkprovenance, below

    if uuidcontent in processdict:
        return processdict[uuidcontent][0]  # return hrefc from processdict

    workelement=element   # start first with children of our node in search for <lip:process> element with matching uuid
    process=None

    while process is None:
        processlist=workelement.xpath("lip:process",namespaces={"lip":lip})
        for processtag in processlist:
            # if "uuid" in processtag.attrib: 
            #     print "%s vs %s" % (processtag.attrib["uuid"],uuidcontent)
            #     pass
            if "uuid" in processtag.attrib and processtag.attrib["uuid"]==uuidcontent:
                process=processtag # Match!
                break
            processsublist=processtag.xpath(".//lip:process[@uuid=\"%s\"]" % (uuidcontent),namespaces={"lip": lip})
            # print "sublist constraint: .//lip:process[@uuid=\"%s\"]" % (uuidcontent)
            # print "len(processsublist)=%d" % (len(processsublist))
            if len(processsublist) > 1: 
                raise IndexError("Multiple lip:process tags matching uuid %s." % (uuidcontent))
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

    return href_context.fromelement(xmldocu,process)


def findprocesstags(xmldocu,context,my_uuid,processtagbyuuid,childuuidbyuuid,processtagsnouuid):
    processtags=xmldocu.xpathcontext(context,"lip:process",namespaces=global_nsmap)
    if my_uuid is not None:
        childuuidbyuuid[my_uuid]=[]
        pass

    for processtag in processtags: 
        uuid=xmldocu.getattr(processtag,"uuid",None)
        if uuid is None:
            # add process tag to list of process tags without a uuid
            # a process tag without a uuid is inherently broken
            # and usually results from an exception during processing
            processtagsnouuid.append(processtag)
            pass
        else: 
            processtagbyuuid[uuid]=processtag
            
            if my_uuid is not None:
                childuuidbyuuid[my_uuid].append(uuid)
                pass
        
            findprocesstags(xmldocu,processtag,uuid,processtagbyuuid,childuuidbyuuid,processtagsnouuid)
            pass
        pass
    pass


def process_is_obsolete(processdict,processtagbyuuid,obsoleteprocesstagbyuuid,childuuidbyuuid,uuid):
    # private
    if uuid not in processdict:
        # looks obsolete!
        obsolete=True

        # Are all children obsolete? 
        for sub_uuid in childuuidbyuuid[uuid]:
            obsolete=obsolete and process_is_obsolete(processdict,processtagbyuuid,obsoleteprocesstagbyuuid,childuuidbyuuid,sub_uuid)
            pass

        if obsolete:
            # remove from processtagbyuuid dictionary, add to obsoleteprocesstagbyuuid
            processtag=processtagbyuuid[uuid]
            del processtagbyuuid[uuid]
            obsoleteprocesstagbyuuid[uuid]=processtag
            
            return True
        pass
    return False

def cleanobsoleteprovenance(xmldocu):
    # xmldocu must be locked in memory READ-WRITE
    # lip prefix be configured in nsmap
    

    # Check all provenance
    (docdict,processdict,processdictbyhrefc,processdictbyusedelement,elementdict,globalmessagelists,totalmessagelists)=checkallprovenance(xmldocu)

    # Obsolete provenance are any lip:process tags that don't show up in
    # processdict and that don't have children or descendents that show up in
    # processdict

    processtagbyuuid=collections.OrderedDict()  # ordered so we go through it in parent-child order and find the tree roots correctly below
    childuuidbyuuid={}  # dictionary of child process tag uuid by parent process tag uuid
    processtagsnouuid=[] # list of process tags not even having a uuid
    # Find lip:process tags and fill in uuid dictionaries
    findprocesstags(xmldocu,xmldocu.getroot(),None,processtagbyuuid,childuuidbyuuid,processtagsnouuid)
    
    obsoleteprocesstagbyuuid={}  # Will move from processtagbyuuid into here as we determine tags are obsolete
    obsolete_root_uuids=[]

    for uuid in list(processtagbyuuid.keys()):
        if uuid in processtagbyuuid:
            # Move process and sub-processes into obsoleteprocesstagbyuuid if they are obsolete
            if process_is_obsolete(processdict,processtagbyuuid,obsoleteprocesstagbyuuid,childuuidbyuuid,uuid):
                # This is a root of an obsolete tree, because if we were at a branch or leaf of an obsolete tree, it would have been removed before we got here
                obsolete_root_uuids.append(uuid)
                pass
            pass
        
        pass
    
    msg="Removed %d process tags containing %d total lip:provenance elements (%d remaining)" % (len(obsolete_root_uuids)+len(processtagsnouuid),len(obsoleteprocesstagbyuuid),len(processtagbyuuid))
    for processtag in processtagsnouuid:
        xmldocu.remelement(processtag)
        pass
    
    for uuid in obsolete_root_uuids:
        processtag=obsoleteprocesstagbyuuid[uuid]
        xmldocu.remelement(processtag)
        pass

    return msg


def checkallprovenance(xmldocu):
    # xmldocu must be in memory... i.e. either locked
    # or read in with locking (now) disabled
    docdict={}

    docdict[xmldocu.get_filehref()]=xmldocu
    processdict={}
    processdictbyhrefc={}
    processdictbyusedelement={}
    elementdict={}

    globalmessagelists={"error": [],
                        "warning":  [],
                        "info": [],
                        "none": []}
    
    treeroot=xmldocu.doc.getroot()
    for descendent in iterelementsbutskip(treeroot,LIP+"process"):

        refuuids_or_mtime=None
        if LIP+"wasgeneratedby" in descendent.attrib: 
            refuuids_or_mtime=str(descendent.attrib[LIP+"wasgeneratedby"])
            pass
        else : 
            globalmessagelists["warning"].append("Element %s does not have lip:wasgenerateby provenance" % (href_context.fromelement(xmldocu,descendent).humanurl()))
            pass
        element_hrefc=href_context.fromelement(xmldocu,descendent)
        checkprovenance("",element_hrefc,refuuids_or_mtime,nsmap=xmldocu.nsmap,docdict=docdict,processdict=processdict,processdictbyhrefc=processdictbyhrefc,processdictbyusedelement=processdictbyusedelement,elementdict=elementdict,globalmessagelists=globalmessagelists)
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

    return  (docdict,processdict,processdictbyhrefc,processdictbyusedelement,elementdict,globalmessagelists,totalmessagelists)

def find_process_value_or_ancestor(process_el,tagpath,default=AttributeError("Could not find tag")):
    # tag should use lip: prefix
    # print "tag:",tag
    gottags=process_el.xpath(tagpath,namespaces={"lip":lip})
    
    if len(gottags)==0: 
        parent=process_el.getparent()

        if parent.tag==LIP+"process":
            return find_process_value_or_ancestor(parent,tagpath,default=default)
        
        if isinstance(default,BaseException):
            raise default
        else: 
            return default
        pass
    
    if len(gottags) > 1:
        raise ValueError("Multiple tags: %s" % (unicode(gottags)))

    return gottags[0]



def find_process_value_or_ancestor_text(process_el,tagpath,default=AttributeError("Could not find tag")):

    ret=find_process_value_or_ancestor(process_el,tagpath,default=None)
    if ret is None:
        if isinstance(default,BaseException):
            raise default
        else:
            return default
        pass

    return ret.text

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
    # Find the first non-lip:process parent of the specified element
    # and return the node itself and the path from foundelement to 
    # that node. 
    #
    # This used to be  useful because lip:process relative ETXPaths are relative
    # to the first non-process parent of the lip:process tag. 
    # So you take the location of the lip:process tag, 
    # append the path returned by this function, 
    # and append the relative etxpath, 
    # and finally canonicalize the result
    
    context_node=foundelement.getparent()
    append_path=".."
    while context_node.tag==LIP+"process":
        context_node=context_node.getparent()
        append_path+="/.."
        pass
    return (context_node,append_path)

def suggest(docdict,processdict,processdictbyhrefc,processdictbyusedelement,elementdict,globalmessagelists,totalmessagelists):

    from . import xmldoc # don't want this in top-of-file because it creates a circular reference

    suggestion_processes=set([])
    suggestions=set([])
    suggestions_by_prxfile={}
    prxfiles=set([])

    # print("type(processdict)=%s" % (str(type(processdict))))

    for elementinfo in elementdict:
        (hrefc,uuid_or_mtime)=elementinfo
        (processuuidlist,messagelists)=elementdict[elementinfo]
        for message in messagelists["error"]: 
            if message.startswith("Object provenance does not match for"):
                if elementinfo in processdictbyusedelement:
                    rerunprocess_uuids=processdictbyusedelement[elementinfo]
                    for rerunprocess_uuid in rerunprocess_uuids: 
                        if rerunprocess_uuid not in processdict: 
                            sys.stderr.write("Warning: process uuid %s not in processdict (?)\n" % (rerunprocess_uuid))
                            continue
                        (processhrefc,usedelements,messagelists,parent_uuid_or_None)=processdict[rerunprocess_uuid]
                        if processhrefc in suggestion_processes: 
                            continue # already handled this process
                        suggestion_processes.add(processhrefc) # mark this one as handled

                        processfilehrefc=processhrefc.fragless()
                        if processfilehrefc  not in docdict:
                            sys.stderr.write("Warning: URL %s not in docdict (?)\n" % (processfilehrefc.absurl()))
                            continue

                        xmldocu=docdict[processfilehrefc]
                        foundelement=processhrefc.evaluate_fragment(xmldocu,None,noprovenance=True)
                        if len(foundelement)==0:
                            sys.stderr.write("Warning: Could not find process path %s in URL %s\n" % (processhrefc.gethumanfragment(),processfilehrefc.absurl()))
                            continue
                        assert(len(foundelement)==1)  # This would be triggered by a hash collision. Should be separately diagnosed in processing. 
                        # foundelement[0] is the lip:process tag
                    
                        
                        inputfilehrefc=href_context.fromxml(xmldocu,find_process_value_or_ancestor(foundelement[0],"lip:inputfile"))
                        action=find_process_value_or_ancestor_text(foundelement[0],"lip:action",default="")
                        prxhrefc=href_context.fromxml(xmldocu,find_process_value_or_ancestor(foundelement[0],"lip:wascontrolledby/lip:prxfile"))


                    
                        prxfiles.add(prxhrefc)
                        if not prxhrefc in suggestions_by_prxfile:
                            suggestions_by_prxfile[prxhrefc]=set([])
                            pass
                        suggestions_by_prxfile[prxhrefc].add((inputfilehrefc,action))
                        pass
                    pass
                pass

            pass
                    
        pass
    
    # go through each prxfile and suggest steps in order
    # We don't worry about sorting prxfiles, because
    # we don't expect to have multiple prxfiles
    for prxfile_hrefc in prxfiles: 

        from . import xmldoc # don't want this in top-of-file because it creates a circular reference
        from . import dc_value # don't want this in top-of-file because it creates a circular reference

        print("prxfile_hrefc=%s" % (prxfile_hrefc.humanurl()))

        prxfile_doc=xmldoc.xmldoc.loadhref(dc_value.hrefvalue(prxfile_hrefc),nsmap={"prx":"http://limatix.org/processtrak/processinginstructions","xlink":"http://www.w3.org/1999/xlink"})
        prxfile_steps=prxfile_doc.xpath("prx:step")
        prxfile_inputfiles=prxfile_doc.xpath("prx:inputfile")
        for step in prxfile_steps:
            stepaction=processtrak_prxdoc.getstepname(prxfile_doc,step)
            refdinputhrefcs=[inputfilehrefc for (inputfilehrefc,action) in suggestions_by_prxfile[prxfile_hrefc] if action==stepaction]
            for refdinputhrefc in refdinputhrefcs:
                suggestions_by_prxfile[prxfile_hrefc].remove((refdinputhrefc,stepaction))
                # processtrak takes <inputfile> tag of prxfile
                # Search for match between refdinputfile and the inputfiles specified in prx document
                foundinputfile=False
                for prxinputfile_el in prxfile_inputfiles:
                    prxinputfile_hrefc=href_context.fromxml(prxfile_doc,prxinputfile_el)
                    # prxinputfile=prxfile_doc.gettext(prxinputfile_el)
                    # if os.path.isabs(prxinputfile):
                    #     prxinputfile_fullpath=prxinputfile
                    #     pass
                    # else: 
                    #     prxinputfile_fullpath=os.path.join(prxfile_dir,prxinputfile)
                    #     pass
                    # prxinputfile_canonpath=canonicalize_path.canonicalize_path(prxinputfile_fullpath)
                    # refdinputfile_canonpath=canonicalize_path.canonicalize_path(refdinputfile)
                    # print "prxinputfile=",prxinputfile_canonpath
                    # print "refdinputfile=",refdinputfile_canonpath

                    if prxinputfile_hrefc==refdinputhrefc:
                        foundinputfile=True
                        suggestions.add(("Rerun step %s on file %s." % (stepaction,prxinputfile_hrefc.humanurl()),"processtrak -s %s -f %s %s" % (addquotesifnecessary(stepaction),addquotesifnecessary(prxinputfile_hrefc.getpath()),addquotesifnecessary(prxfile_hrefc.getpath()))))
                        break
                        
                    pass
                if not foundinputfile: 
                    sys.stderr.write("Could not find reference to input file %s in %s" % (refdinputhrefc.humanurl(),prxfile_hrefc.humanurl()))
                    pass
                pass
            pass
        for (inputfilehrefc,stepaction) in suggestions_by_prxfile[prxfile_hrefc]:
            sys.stderr.write("Unknown (inputfile,stepname) for %s: (%s,%s)\n" % (prxfile_hrefc.humanurl(),inputfilehrefc.humanurl(),stepaction))
            pass
        pass
    return suggestions


def checkprovenance(history_stack,element_hrefc,refuuids_or_mtime,nsmap={},referrer_hrefc="",warnlevel="error",docdict=None,processdict=None,processdictbyhrefc=None,processdictbyusedelement=None,elementdict=None,globalmessagelists=None):
    # Find the provenance of element_hrefc
    # start with a history_stack of ""
    # refuuids_or_mtime is None or the expected "uuid=" or "mtime=" provenance of this particular element

    # docdict, processdict, processdictbyhrefc, processdictbyusedelement, elementdict, and global messagelists should be empty. They will be filled
    # 
    # docdict: cached dictionary by fragless hrefc of xmldoc documents
    # processdict: cached dictionary by uuid of (hrefcs to lip:process elements, [list of (element hrefc,uuid_or_mtime)],messagelists,parent_process_uuid_or_None)   ... parent process is implicit WasControlledBy
    # processdictbyhrefc: dictionary by hrefc of uuids for processdict
    # processdictbyusedelement: dictionary by (element hrefc,uuid_or_mtime) of [list of uuids for processes that used that element ]
    # elementdict dictionary by (hrefc,uuid_or_mtime) tuples that we have processed of ([list of process uuids],messagelists)

    # messagelists & globalmessagelists: dictionary by error type of lists of error messages

    # Currently ignore pymodule references.

    # note: functionality of referrer_hrefc mostly replaced by history_stack

    new_history_stack=history_stack+"/"+element_hrefc.humanurl()

    if refuuids_or_mtime is not None: 
        refuuids_or_mtime=str(refuuids_or_mtime) # in case it is some sort of alternate string
        pass

    if docdict is None: 
        docdict={}
        pass
    
    if processdict is None:
        processdict={}
        pass

    if processdictbyhrefc is None:
        processdictbyhrefc={}
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
    # fh.write(element_hrefc+"\t"+str(refuuids_or_mtime)+"\n")
    # fh.close()

    if (element_hrefc,refuuids_or_mtime) in elementdict:
        return # already processed this element
    # NOTE: Can probably optimize here. When refuuid_or_mtime is passed as None -- implying current element -- is there a way to automatically identify if we have previously processed it?... less of an issue now that checkallprovenance passes refuuid_or_mtime 
    


    if element_hrefc in processdictbyhrefc:
        return # already processed this lip:process element
        
    # sys.stderr.write("element_hrefc="+str(element_hrefc)+"\n")
    filehrefc=element_hrefc.fragless()

    # sys.stderr.write("filehrefc="+str(filehrefc)+"\n")

    #(filepath,etxpath)=canonicalize_path.canonical_etxpath_break_out_file(element_etxpath)

    if element_hrefc.has_fragment():
        # not just a file...
        # load file and extract provenance uuids if possible


        if refuuids_or_mtime is not None and refuuids_or_mtime.startswith("mtime="):
            # mtime specified on something with a fragment
            errmsg="Attempting to specify mtime provenance %s for an element %s inside a file. Referrer=%s" % (refuuids_or_mtime,element_hrefc.humanurl(),referrer_hrefc.humanurl())
            
            if referrer_hrefc in processdictbyhrefc: 
                processdict[processdictbyhrefc[referrer_hrefc]][2]["error"].append(errmsg)
                pass
            else: 
                globalmessagelists["error"].append(errmsg)
                pass
            pass

        if filehrefc in docdict:
            xmldocu=docdict[filehrefc]
            pass
        else :
            xmldocu=None
            try :
                from . import xmldoc # don't want this in top-of-file because it creates a circular reference
                from . import dc_value # don't want this in top-of-file because it creates a circular reference

                xmldocu=xmldoc.xmldoc.loadhref(dc_value.hrefvalue(filehrefc.fragless()))
                pass
            except IOError:
                errmsg="URL %s missing for %s referred by %s." % (filehrefc.humanurl(),element_hrefc.humanurl(),referrer_hrefc.humanurl())
                sys.stderr.write(errmsg+"\n")
                if referrer_hrefc in processdictbyhrefc: 
                    processdict[processdictbyhrefc[referrer_hrefc]][2]["error"].append(errmsg)
                    pass
                else : 
                    globalmessagelists["error"].append(errmsg)
                    pass
                pass
            docdict[filehrefc]=xmldocu
            pass
        if xmldocu is None:
            return # nothing to do... error would have been diagnosed above

        foundelement=element_hrefc.evaluate_fragment(xmldocu,None,noprovenance=True)
        if len(foundelement)==0:
            elementdict[(element_hrefc,refuuids_or_mtime)]=([],copy.deepcopy(messagelisttemplate)) # mark that we have done this
            # Add error message to messagelists
            elementdict[(element_hrefc,refuuids_or_mtime)][1]["error"].append("Object %s missing referred by via %s" % (element_hrefc.humanurl(),history_stack))  #,referrer_hrefc.humanurl()))
            pass
        elif len(foundelement) > 1:
            elementdict[(element_hrefc,refuuids_or_mtime)]=([],copy.deepcopy(messagelisttemplate)) # mark that we have done this
            # add error to messagelists
            elementdict[(element_hrefc,refuuids_or_mtime)][1]["error"].append("Object %s not unique referred via %s." % (element_hrefc.humanurl(),history_stack))
            pass
        elif foundelement[0].tag==LIP+"process":
            # lip:process tag ! 
            

            if not "uuid" in foundelement[0].attrib:
                globalmessagelists["error"].append("process %s has no uuid attribute" % (element_hrefc.humanurl()))
                processdictbyhrefc[element_hrefc]=None # mark that we have done this
                pass
            else :
                uuid=foundelement[0].attrib["uuid"]
                
                parent_uuid=None
                parenttag=foundelement[0].getparent()
                if parenttag.tag==LIP+"process":
                    if "uuid" in parenttag.attrib: 
                        parent_uuid=parenttag.attrib["uuid"]
                        pass
                    else : 
                        globalmessagelists["error"].append("parent process of process %s has no uuid attribute" % (element_hrefc.humanurl()))
                        pass
                    pass


                        
                # Put this in processdict
                processdict[uuid]=(element_hrefc,[],copy.deepcopy(messagelisttemplate),parent_uuid)
                processdictbyhrefc[element_hrefc]=uuid # mark that we have done this
                
                for usedtag in foundelement[0].xpath("lip:used",namespaces={"lip": lip}):
                    if not "type" in usedtag.attrib:
                        # add error message to message list
                        processdict[uuid][2]["error"].append("lip:used tag %s does not have a type attribute" % (href_context.fromelement(xmldocu,usedtag).humanurl()))
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
                    elif usedtag.attrib["type"]=="href" or usedtag.attrib["type"]=="fileetxpath":
                        # Reference to a href

                        # Context of the href is the parent of the nested lip:process nodes, but these are all absolute within the document now anyway
                        #(context_node,append_path)=getnonprocessparent(foundelement[0])
                            
                        # print "For newetxpath, element_etxpath=",element_etxpath
                        # print "append_path=",append_path
                        # print "usedtag.text=",usedtag.text
                        # print "joined=",canonicalize_path.canonical_etxpath_join(element_etxpath,append_path,usedtag.text)
                        # newetxpath=canonicalize_path.canonicalize_etxpath(canonicalize_path.canonical_etxpath_join(element_etxpath,append_path,usedtag.text))
                        # if "absetxpath" in usedtag.attrib and newetxpath != usedtag.attrib["absetxpath"]:
                        #     # add error message to message list
                        #     processdict[uuid][2]["warning"].append("Relative ETXPath %s on %s resolves to %s which does not match absolute path %s. Using relative path.\n" % (usedtag.text,canonicalize_path.etxpath2human(canonicalize_path.create_canonical_etxpath(xmldocu._filename,xmldocu.doc,usedtag),nsmap),newetxpath,usedtag.attrib["absetxpath"]))
                        #    pass

                        newhrefc=href_context.fromxml(xmldocu,usedtag)
                        #sys.stderr.write("newhref=%s fragment=%s\n" % (str(newhrefc.contextlist),str(newhrefc.fragment)))
                        
                        #if str(newhrefc.contextlist)=="('',)":
                        #    import pdb
                        #    pdb.set_trace()
                        #    newhrefc=href_context.fromxml(xmldocu,usedtag)
                        #    pass
                        
                        
                        
                        uuids_or_mtime=None
                        if "usedwasgeneratedby" in usedtag.attrib:
                            uuids_or_mtime=str(usedtag.attrib["usedwasgeneratedby"])
                            pass
                        elif "fragcanonsha256" in usedtag.attrib:
                            uuids_or_mtime="fragcanonsha256="+usedtag.attrib["fragcanonsha256"]
                            pass
                        elif "mtime" in usedtag.attrib:
                            uuids_or_mtime="mtime="+usedtag.attrib["mtime"]
                            pass
                        
                        # Mark this process as referring to this element
                        processdict[uuid][1].append((newhrefc,uuids_or_mtime))
                        if not (newhrefc,uuids_or_mtime) in processdictbyusedelement:
                            processdictbyusedelement[(newhrefc,uuids_or_mtime)]=[]
                            pass
                        processdictbyusedelement[(newhrefc,uuids_or_mtime)].append(uuid)
                        

                        
                        # Make recursive call to evaluate this tag that was "used" by the process!
                        # print "recursive call for used element"
                            
                        checkprovenance(new_history_stack,newhrefc,uuids_or_mtime,nsmap=nsmap,referrer_hrefc=element_hrefc,warnlevel=subwarnlevel,docdict=docdict,processdict=processdict,processdictbyhrefc=processdictbyhrefc,processdictbyusedelement=processdictbyusedelement,elementdict=elementdict,globalmessagelists=globalmessagelists)
                        pass
                    else:
                        # add error message to message list
                        processdict[uuid][2]["error"].append("lip:used tag %s does has unknown type attribute %s" % (href_context.fromelement(xmldocu,usedtag),usedtag.attrib["type"]))
                        pass
                        
                    pass

                
                pass

        else:

            # no specific tag. Look for recorded provenance
            
            uuidstring=str(xmldocu.getattr(foundelement[0],"lip:wasgeneratedby","",namespaces={"lip": lip}))
            if refuuids_or_mtime is not None:
                if refuuids_or_mtime.startswith("uuid="):
                    matchstring=uuidstring
                    pass
                elif refuuids_or_mtime.startswith("mtime="):
                    matchstring="mtime="+datetime.datetime.fromtimestamp(os.path.getmtime(xmldocu.get_filehref().getpath()),lm_timestamp.UTC()).isoformat()
                    pass
                elif refuuids_or_mtime.startswith("fragcanonsha256="):
                    # Create canonicalization:
                    canondoc=xmldoc.xmldoc.copy_from_element(xmldocu,foundelement[0],nsmap=foundelement[0].nsmap)
                    canonbuf=StringIO()
                    canondoc.doc.write_c14n(canonbuf,exclusive=False,with_comments=True)
                    matchstring="fragcanonsha256=" + hashlib.sha256(canonbuf.getvalue()).hexdigest()
                else:
                    matchstring="ERROR_INVALID_UUID_CLASS"
                    pass
                pass
            if refuuids_or_mtime is not None and refuuids_or_mtime != matchstring:
                # refuuids_or_mtime is what we were lead to believe (by the calling lip:process) generated this element
                # matchstring is what actually generated this element

                # it is the calling lip:process, really, that has a problem
                # !!! Should diagnose this better by looking up the two process elements !!!
                # create elementdict entry right away so we can put the error message into it
                elementdict[(element_hrefc,refuuids_or_mtime)]=([],copy.deepcopy(messagelisttemplate)) # mark that we have done this, but mark the referred element as that is the real provenance

                # sys.stderr.write("Compare \"%s\"\n        \"%s\"\n" % 

                elementdict[(element_hrefc,refuuids_or_mtime)][1][warnlevel].append("Object provenance does not match for %s: %s specified in %s vs. %s actual. Referenced version has probably been overwritten. Access history: %s" % (element_hrefc.humanurl(),refuuids_or_mtime,referrer_hrefc.humanurl(),matchstring,history_stack))

                if refuuids_or_mtime.startswith("uuid="):
                    uuidstring=refuuids_or_mtime # mark the referred element as that is the real provenance
                    pass
                pass
            else  :
                elementdict[(element_hrefc,uuidstring)]=([],copy.deepcopy(messagelisttemplate)) # mark that we have done this
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
                        elementdict[(element_hrefc,uuidstring)][1]["error"].append("uuid string \"%s\" specified in %s or %s is not valid" % (uuid,element_hrefc.humanurl(),referrer_hrefc.humanurl()))
                        continue
                    

                    try: 
                        process_el_hrefc=find_process_el(xmldocu,processdict,foundelement[0],uuid[5:]) # !!! need to write find_process_el
                        pass
                    except IndexError as e:
                        # store error message in elementdict messagelist
                        elementdict[(element_hrefc,uuidstring)][1]["error"].append(str(e))
                        pass
                    if process_el_hrefc is None:
                        # store error message in elementdict messagelist
                        elementdict[(element_hrefc,uuidstring)][1]["error"].append("Could not find lip:process element for uuid %s when looking up %s (possibly specified in %s)" % (uuid,element_hrefc.humanurl(),referrer_hrefc.humanurl()))
                        continue

                    elementdict[(element_hrefc,uuidstring)][0].append(uuid[5:]) # add this link to list for this element

                    new_history_stack_process=new_history_stack+"/"+process_el_hrefc.humanurl()

                    # recursive call to handle lip:process element
                    # print "recursive call for process element"
                    checkprovenance(new_history_stack_process,process_el_hrefc,None,nsmap=nsmap,referrer_hrefc=element_hrefc,warnlevel=warnlevel,docdict=docdict,processdict=processdict,processdictbyhrefc=processdictbyhrefc,processdictbyusedelement=processdictbyusedelement,elementdict=elementdict,globalmessagelists=globalmessagelists)
                    
                        
                    pass
                
                pass
            pass
        pass
    else : 
        # etxpath==""
        # just a file

        elementdict[(element_hrefc,refuuids_or_mtime)]=([],copy.deepcopy(messagelisttemplate)) # mark that we have done this file

        if refuuids_or_mtime is not None and not (refuuids_or_mtime.startswith("mtime=")):
            # Add error message to elementdict messagelist
            elementdict[(element_hrefc,refuuids_or_mtime)][1]["error"].append("Attempting to specify uuid provenance %s for a file %s in provenance of %s" % (refuuids_or_mtime,filehrefc.humanurl(),element_hrefc.humanurl()))
            pass


        if not os.path.exists(filehrefc.getpath()):
            # Add error message to elementdict messagelist
            elementdict[(element_hrefc,refuuids_or_mtime)][1]["error"].append("Object %s missing when accessing  %s referred by %s." % (element_hrefc.humanurl(),filehrefc.getpath(),referrer_hrefc.humanurl()))
            pass
        else : 
            if refuuids_or_mtime is not None:
                mtime=datetime.datetime.fromtimestamp(os.path.getmtime(filehrefc.getpath()),lm_timestamp.UTC()).isoformat()
                if mtime != refuuids_or_mtime[6:].split(";")[0]:
                    # Add error message to elementdict messagelist
                    elementdict[(element_hrefc,refuuids_or_mtime)][1][warnlevel].append("File modification times do not match for %s, referenced in %s: %s referenced vs. %s actual" % (filehrefc.humanurl(),referrer_hrefc.humanurl(),refuuids_or_mtime,mtime))
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
                refuuid=refdoc.getattr(foundrefelement[0],"lip:wasgeneratedby","",namespaces={"lip": lip})
                pass
            pass
"""   



