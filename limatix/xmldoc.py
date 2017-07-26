from lxml import etree
import os
import os.path
import copy
import sys
import traceback
import numbers
import signal
import socket
import time
import shutil
import collections
import xml.sax.saxutils
try: 
    # py2.x
    from urllib import pathname2url
    from urllib import url2pathname
    import urlparse
    pass
except ImportError:
    import urllib.parse as urlparse # python3 
    from urllib.request import pathname2url
    from urllib.request import url2pathname
    pass


import urllib


if os.name=='nt':
    # win32 fcntl.flock alternative: 
    # loosely based on http://code.activestate.com/recipes/65203/
    import win32con
    import win32file
    import pywintypes

    pwt__overlapped = pywintypes.OVERLAPPED()
    pass

else: 
    import fcntl    
    pass

    
    
try: 
    from . import provenance as provenance
    pass
except ImportError:
    sys.stderr.write("xmldoc: Warning provenance support not available\n")

    # Create dummy class "provenance" that makes provenance calls into no-ops
    class provenance(object):
        @classmethod
        def xmldocelementaccessed(cls,xmldocu,element):
            pass

        @classmethod
        def warnnoprovenance(cls,msg):
            pass
            
        @classmethod
        def elementgenerated(cls,doc,element):
            pass
        pass

    pass

import numpy as np

from . import lm_units as lmu


from . import dc_value


try: 
    from .canonicalize_path import canonicalize_path
    from .canonicalize_path import relative_path_to
    pass
except ImportError:
    from os.path import realpath as canonicalize_path
    relative_path_to=lambda start,path: os.path.relpath(path,start)
    pass

try: 
    from .canonicalize_path import canonicalize_etxpath
    from .canonicalize_path import getelementetxpath
    from .canonicalize_path import create_canonical_etxpath
    from .canonicalize_path import canonical_etxpath_split
    from .canonicalize_path import canonical_etxpath_join
    from .canonicalize_path import canonical_etxpath_absjoin
    from .canonicalize_path import etxpath_isabs
    from .canonicalize_path import etxpath2human
    pass
except ImportError:
    canonicalize_etxpath=None
    pass

try: 
    from cStringIO import StringIO
    pass
except ImportError:
    from io import StringIO
    pass

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


gtk=None
gobject=None


class fileinfo(object):
    mtime=None
    inode=None
    size=None
    
    def __init__(self,fd):
        statbuf=os.fstat(fd)
        self.mtime=statbuf.st_mtime
        self.inode=statbuf.st_ino
        self.size=statbuf.st_size
        pass

    def __str__(self):
        return "xmldoc.fileinfo(mtime=%d,inode=%d,size=%d)" % (self.mtime,self.inode,self.size)

    def __eq__(self,other):
        return self.mtime==other.mtime and self.inode==other.inode and self.size==other.size

    def __ne__(self,other):
        return not self.__eq__(other)

def loadgtk():
    global gtk
    if gtk is None:
        if "gi" in sys.modules:  # gtk3
            import gi
            gi.require_version('Gtk','3.0')
            from gi.repository import Gtk as gtk
            pass
        else : 
            # gtk2
            import gtk
            pass
        pass
    pass


def loadgobject():
    global gobject
    if gobject is None:
        if "gi" in sys.modules:  # gtk3
            from gi.repository import GObject as gobject
            pass
        else : 
            # gtk2
            import gobject
            pass
        pass
    pass

startuptime=None

def generate_inmemory_id(checklist):
    global startuptime

    hostname=socket.gethostname()
    if startuptime is None:
        startuptime=time.time() # log a hopefully unique value
        pass
    pid=os.getpid()
    
    return "mem://%s/%d/%d/%d" % (hostname,startuptime,pid,id(checklist))


def _xlinkcontextfixuptree(ETree,oldcontexthref,newcontexthref,force_abs_href=False):
    # Go through ETree, search for elements with xlink:href 
    # attributes, fix them up.
    # operates in-place on provided etree.ElementTree or etree.Element
    # force_abs_href causes all relative links to be shifted to absolute links
    # (appropriate if the new location is a fundamental move)
    # returns number of modifications made


    ETXobj=etree.ETXPath("//*[@{http://www.w3.org/1999/xlink}href]")
    xmlellist=ETXobj(ETree)

    modcnt=0

    for element in xmlellist: 
        URL=element.attrib["{http://www.w3.org/1999/xlink}href"]
        href=dc_value.hrefvalue(URL,contexthref=oldcontexthref)
        if force_abs_href or (newcontexthref is None) or newcontexthref.isblank():
            newurl=href.absurl()
            pass
        else:
            newurl=href.attempt_relative_url(newcontexthref)
            pass

        if newurl != URL:
            element.attrib["{http://www.w3.org/1999/xlink}href"]=newurl
            modcnt+=1
            pass
        pass
    return modcnt

    
try: 
    from databrowse.lib import db_lib as dbl
    pass
except ImportError:
    dbl=None
    pass

__pychecker__="no-argsused"

# !!! Very important: Only modify the xmldoc using its member functions (otherwise the modification tracking
# will not work)
# !!! Very important: Do not keep deep references inside the xmldoc. These may change due to a resync(). 
# Save element locations with savepath(). You can later reextract elements 
# after the resync() with restorepath(). This will work properly so 
# long as no elements have been added to the tree upward of where you 
# are looking. 

# Namespace management
# --------------------
# When you create an xmldoc, you specify a namespace mapping that 
# gets encoded into the root node. (If no mapping is provided, a default
# is used). When working with the xmldoc in memory and syncing to disk, 
# the in-memory mapping and the root node mapping are kept distinct. 
# When you add an in-memory mapping with merge_namespace or resync an
# on-disk copy that may be missing one of these namespaces, xmldoc 
# will add add any additional prefix mappings that might be in the 
# in-memory mapping to the root node to the root node mapping, so long
# as they do not conflict (either in prefix or namespace) with an existing
# mapping. 
# When you try to access elements, only the in-memory mapping is used. 
# The root node mapping is entirely irrelevant except that it is what is used
# when manually editing the file as written to disk 


# xmldoc limitations
# -----------------
#  * Not thread safe: See use of signal() to hold off SIGINT during 
#    _flush() update and use of lxml which itself is not thread safe
#  * Does not properly handle XML comments within simple tags (within
#    compound tags OK). The problem is we use lxml's ".text" object
#    attribute, which only gives us the first text node. 
#

# Future plans
# ------------
# 1. Fix deep references in checklist steps.    DONE
# 2. Add support for multiple layers of backup files. DONE
# 3. Eliminate xmlgrab2 PENDING
# 4. Implement file locking and explicit modification and critical regions.  DONE
# 5. Fix up provenance handling in recursive operations. Specifically copyelements()



class xmldoc(object):
    """
    xmldoc is a class that represents readable (and optionally writable)
    xml documents. This class supports synchronization to disk (flushing
    of changes, reading in external changes) when requested.

    Because of the potential for rereading, and therefore 
    invalidation of all of the element objects, you should
    never store references to elements. Instead you 
    should use use xmldoc.getpath() to get the element 
    location which can be stored instead. Get a new
    reference when needed with xmldoc.xpathsingle() 
    (NOTE: getpath() results are not compatible with find())

    XPaths and find() vs. xpath()
    -----------------------------
    find() is a lighter-weight call that still has some matching
    capability but is quite a bit simpler. 
    
    The big difference is that find() does not handle leading 
    slashes in the path. So with find, you can't specify
    "/chx:checklist/chx:checkitem[3]", you must just specify
    "chx:checkitem[3]. 

    For both, the main tag is the context node for the search.
    So just leave off the leading slash and main tag name from 
    the search, and everything will work as expected. 

    """

    # Please consider all class variables to be private! 

    doc=None  # lxml etree document representation !!! private!!!
    olddoc=None # when unlocked, doc is none, olddoc is reference to old, unused document
    filehref=None  # Currently set href (formerly filename), or None
    _filename=None # private filename, for convenience... should always be equal to href.getpath()
    contexthref=None # If href is None, this dc_value.hrefvalue is the contextual
                    # location. 
                    
    nsmap=None  # prefix-to-namespace mapping
    namespaces=None  # copy of nsmap for xpath queries with None element removed
    modified=None  # Has the tree been modified since the last flush?
    resyncnotify=None  # List of recipients to notify after each resync
    # autoflush=None   # Automatically flush on modification? 
    # autoresync=None  # If set, resync() will be be called automatically when
                     # before elements that are synced with paramdb2 are 
                     # updated. 
                     # (In general, you should manually resync immediately 
                     # before changing the document, but be warned that 
                     # elements need to be re-found once you do this!)
    readonly=None    # True if writing is disabled. 
    use_databrowse=None  # True if we should use databrowse to read input. 
    extensions=None  # list of xpath extensions to provide by default
    num_backups=None # Number of backup files to keep when writing
    use_locking=None # Use file locking
    nodialogs=None   # disable GUI dialogs
    debug=None       # Enable paranoid debugging?
    debug_last_serialized=None # for debugging... copy of last serialized version
    lastfileinfo=None # Class fileinfo for most recently seen on-disk copy
    ro_lockcount=None # no. of times locked readonly
    rw_lockcount=None # no. of times locked readwrite
    lockfd=None      # file descriptor currently used for locking, or -1. If this is not -1 then this decriptor is locked. This should be close()'d when you unlock. This should always be set if ro_lockcount or rw_lockcount > 0 and filename is set, cleared otherwise
    lockfh=None      # file handle currently used for locking, for NT which requires that the file be left open and reused


    @classmethod
    def loadhref(cls,href,nsmap=None,readonly=True,use_databrowse=False,num_backups=1,use_locking=False,nodialogs=False,debug=False):
        """ xmldoc.loadhref(href,...): Load in an existing file. See 
        main constructor docs for other parameters.
        NOTE: Will merge in xmldoc default nsmap into root element 
        unless you explicitly supply nsmap={}"""

        return cls(href,maintagname=None,nsmap=nsmap,readonly=readonly,use_databrowse=use_databrowse,num_backups=num_backups,use_locking=use_locking,nodialogs=nodialogs,debug=debug)

    @classmethod
    def loadfile(cls,filename,nsmap=None,readonly=True,use_databrowse=False,num_backups=1,use_locking=False,nodialogs=False,debug=False):
        """ xmldoc.loadfile(filename,...): Load in an existing file. See 
        main constructor docs for other parameters.
        NOTE: Will merge in xmldoc default nsmap into root element 
        unless you explicitly supply nsmap={}"""
        href=dc_value.hrefvalue(pathname2url(filename),contexthref=dc_value.hrefvalue("./"))
        
        return cls(href,maintagname=None,nsmap=nsmap,readonly=readonly,use_databrowse=use_databrowse,num_backups=num_backups,use_locking=use_locking,nodialogs=nodialogs,debug=debug)

    @classmethod
    def newdoc(cls,maintagname,nsmap=None,num_backups=1,use_locking=False,contexthref=None,nodialogs=False,debug=False):
        """ xmldoc.newfile(maintagname,...): 
        Create a new in-memory document. See 
        main constructor docs for other parameters"""


        
        return cls(None,maintagname=maintagname,nsmap=nsmap,readonly=False,use_databrowse=False,num_backups=num_backups,use_locking=use_locking,contexthref=contexthref,nodialogs=nodialogs,debug=debug)

    @classmethod
    def fromstring(cls,xml_string,nsmap=None,num_backups=1,use_locking=False,contexthref=None,nodialogs=False,debug=False,force_abs_href=False):
        """ xmldoc.fromstring(...): 
        Create a new in-memory document from a string. See 
        main constructor docs for other parameters.
        NOTE: Will merge in xmldoc default nsmap into root element 
        unless you explicitly supply nsmap={}
        ... does not do fixups of xlink:hrefs... but does allow you to 
        contexthref (or if necessary contextdir) is the assumed context of the current file
        set contexthref so that set_href() or setcontext() will do fixups
        for you from the contexthref provided here to whatever you want
        if force_abs_href is set, it will absolutize all references for you
"""

        
        SIO=StringIO(xml_string)
        newdoc=cls(None,maintagname=None,nsmap=nsmap,readonly=False,use_databrowse=False,num_backups=num_backups,FileObj=SIO,use_locking=use_locking,contexthref=contexthref,nodialogs=nodialogs,debug=debug)
        SIO.close()
        
        if force_abs_href: 
            # absolutize all xlinks
            _xlinkcontextfixuptree(newdoc.doc,contexthref,contexthref,force_abs_href=force_abs_href)
            pass
        return newdoc
    
    @classmethod
    def inmemorycopy(cls,xmldoc,nsmap=None,readonly=False,contexthref=None,nodialogs=False,debug=False,force_abs_href=False):
        # Create a new in-memory XMLDOC with a copy of the content of an existing xmldoc
        # Does fixups of xlink:href attributes to contexthref or contextdir
        # if contextdir and contexthref are None, it is presumed that context does
        # not change. Otherwise contextdir is the presumed context
        # of the new document
        # if forceabs is set then contexthref need not be set --- 
        # xlink:hrefs will be converted to absolute
        newnsmap=copy.deepcopy(xmldoc.nsmap)
        if nsmap is not None:
            newnsmap.update(nsmap)
            pass


        if xmldoc.filehref is None:
            doccontexthref=xmldoc.contexthref
            pass
        else : 
            doccontexthref=xmldoc.filehref
            pass
        
        if contexthref is None:
            contexthref=doccontexthref
            pass

        ETreeObj=copy.deepcopy(xmldoc.doc)
        _xlinkcontextfixuptree(ETreeObj,doccontexthref,contexthref,force_abs_href=force_abs_href)

        newdoc=cls(None,maintagname=None,nsmap=newnsmap,readonly=readonly,ETreeObj=ETreeObj,use_locking=False,contexthref=contexthref,nodialogs=nodialogs,debug=debug)
        return newdoc

    @classmethod
    def copy_from_element(cls,xmldocu,etree_or_element,nsmap=None,readonly=False,contexthref=None,nodialogs=False,debug=False,force_abs_href=False):
        # Create a new xmldoc object by copying an element (and sub-elements)
        # or element tree object

        elementcopy=copy.deepcopy(etree_or_element)
        
        if hasattr(elementcopy,"getchildren"):
            # Element object has getchildren()
            # Wrap it in a new tree
            newetree=etree.ElementTree(elementcopy)
            if xmldocu is not None:
                for subel in etree_or_element.iter():
                    provenance.xmldocelementaccessed(xmldocu,subel)
                    pass
                pass
        else:     
            # ElementTree object does not have getchildren()
            newetree=elementcopy
            if xmldocu is not None:
                for subel in etree_or_element.getroot().iter():
                    provenance.xmldocelementaccessed(xmldocu,subel)
                    pass
                pass
            pass
        
        if xmldocu is not None:
            assert(contexthref is None)
            contexthref=xmldocu.getcontexthref()
            pass
        

        return xmldoc.frometree(newetree,nsmap=nsmap,readonly=readonly,contexthref=contexthref,nodialogs=nodialogs,debug=debug,force_abs_href=force_abs_href)
    
    
    @classmethod
    def frometree(cls,lxmletree,nsmap=None,readonly=False,contexthref=None,nodialogs=False,debug=False,force_abs_href=False):
        # Create an xmldoc object from an existing lxml ElementTree object
        # NOTE: Steals existing object and keeps using it internally!!!
        
        # ... does not do fixups of xlink:hrefs... but does allow you to 
        # set contextdir so that set_href() or setcontext() will do fixups
        # for you from the contextdir provided here to whatever you want
        # if you set contextdir and force_abs_href it will absolutize all
        # xlink:href references

        #if contexthref is None and contextdir is not None:
        #    if not contextdir.endswith("/"):
        #        contextdir+="/"
        #        pass
        #
        #    contexthref=dc_value.hrefvalue(pathname2url(contextdir))
        #    pass

        newdoc=cls(None,maintagname=None,nsmap=nsmap,readonly=readonly,ETreeObj=lxmletree,use_locking=False,contexthref=contexthref,nodialogs=nodialogs,debug=debug)

        if force_abs_href: 
            # absolutize all xlinks
            _xlinkcontextfixuptree(lxmletree,contexthref,contexthref,force_abs_href=force_abs_href)
            pass

        return newdoc


    def __init__(self,href,maintagname=None,nsmap=None,readonly=False,use_databrowse=False,num_backups=1,FileObj=None,ETreeObj=None,use_locking=False,contexthref=None,nodialogs=False,debug=False):  
        """ Main constructor fo xmldoc. WE STRONGLY RECOMMEND USING THE CLASS METHOD CONSTRUCTORS INSTEAD
        href:    File to map. May be None if we are creating a new 
                     document in write mode (maintagname != None). 
        maintagname: This is really a mode selector. If None, we will
                     read an existing file. If specified, we will 
                     create a new file (what if the file exists?)
        nsmap:       Namespace mapping. If None a default set for
                     datacollect is used. Example with a subset of 
                     the default: 
                       {
                         None: "http://limatix.org/datacollect",
                         "dc": "http://limatix.org/datacollect",
                         "chx": "http://limatix.org/checklist",
                       }
                     On creation of a blank document, these are put
                     into the XML main tag. Otherwise, this nsmap is used
                     to handle prefix mapping for all xmldoc accesses, 
                     but may differ from any mapping within the XML 
                     file.  
        readonly:    If True, force read-only mode (modifications can 
                     be made in memory, but not flushed to disk)

        use_databrowse: Use databrowse as read engine (can handle directory
                     trees in addition to individual files. Must be paired
                     with readonly flag. 
        num_backups: Number of backup files to keep when writing
        FileObj:     Input file-like object to replace file as input if 
                     maintagname is None.
                     Intended for use by class constructors. Does not 
                     close() this. 
        ETreeObj:    If given, TAKES OWNERSHIP OF THIS ETREE instead of 
                     reading a file
        use_locking: Use file locking. Must bracket all access with 
                     doc.lock_ro()/doc.unlock_ro() 
                     or doc.lock_rw()/doc.unlock_rw(). 
                     Open acts like a lock_rw(), unless the file is opened 
                     read-only, in which case it acts like a lock_ro()
                     Locking calls may be nested, but a lock_rw() cannot be 
                     nested within a lock_ro()
                     NOTE: When using file locking, operations between
                     lock_...() and unlock_...() should be in a try...
                     catch...finally block (or "with" statement") where 
                     the finally segment releases the lock. This way, if 
                     an exception occurs, the lock will be released.
        contexthref: If filename is None, this is the context for relative
                     xlink:href links. 
        nodialogs:   If False, bring up a dialog box or print to stderr
                     on errors. If True, raise an exception on errors
        debug:       Attempt to diagnose locking/use errors, etc.


        """

        # maintagname is the document tag, or None to put xmldoc in read mode. 
        # readonly prevents modifying the file. Note that it is reset with set_href()

        # attrlist is a list of (name,value) tuples for attributes
        if nsmap is None: 
            nsmap={ 
                    "dc": "http://limatix.org/datacollect",
                    "dcv": "http://limatix.org/dcvalue",
                    "chx": "http://limatix.org/checklist",
                    "lip": "http://limatix.org/provenance",
                    "dbvar": "http://limatix.org/databrowse/variable",
                    "dbdir": "http://limatix.org/databrowse/dir",
                    "sp":"http://limatix.org/spatial",
                    "xlink": "http://www.w3.org/1999/xlink",

                    }
            pass

        self.nsmap=copy.deepcopy(nsmap)
        self.namespaces=copy.deepcopy(nsmap)
        if None in self.namespaces: 
            del self.namespaces[None]
            pass
        
        self.readonly=readonly
        # self.autoflush=autoflush
        # self.autoresync=autoresync
        self.use_databrowse=use_databrowse
        if href is not None:
            assert(contexthref is None)
            #if canonicalize_path is not None:
            #    self.filename=canonicalize_path(filename)
            #    pass
            #else : 
            #    self.filename=os.path.realpath(self.filename)
            #    pass
            assert(not href.ismem()) # Can't arbitrarily access mem:// URL's
            assert(isinstance(href,dc_value.hrefvalue))
            self.filehref=href
            
            self._filename=self.filehref.getpath()
            pass
        else:
            # Context should not be forced to be leafless -- the leaf
            # (file name) is relevant to identifying self-links 
            
            # if contexthref is not None:
            #    self.contexthref=contexthref.leafless()
            #    pass
            self.contexthref=contexthref
            
            self.filehref=None
            self._filename=None
            pass
        self.resyncnotify=[]
        self.extensions=[]
        self.num_backups=num_backups
        self.use_locking=use_locking
        self.ro_lockcount=0
        self.rw_lockcount=0
        self.lockfd=-1

        self.nodialogs=nodialogs

        if self.use_databrowse:
            assert(self.readonly)  # databrowse is inherently read-only
            assert(maintagname is None) # databrowse is inherently read mode.
            pass
        
        if maintagname is None:
            # read in existing file
            self.modified=False;
            if ETreeObj is not None:
                self.doc=ETreeObj
                pass
            elif not self.use_locking:
                self._resync(initialload=True,FileObj=FileObj)
                pass
            elif self.use_locking and self.readonly: 
                self._resync(initialload=True,FileObj=FileObj,rolock=True)
                self.ro_lockcount=1
                pass
            elif self.use_locking and not self.readonly:
                self._resync(initialload=True,FileObj=FileObj,rwlock=True)
                self.rw_lockcount=1
                pass
            else : 
                assert(0)
                pass
            pass
        else : 
            # create new document

            # create element
            nspre_mtname=maintagname.split(":")
        
            assert(not self.readonly) # readonly new document does not make sense
            assert(len(nspre_mtname) <= 2)
            
            if len(nspre_mtname)==1:
                # no explicit prefix
                # create element
                maintag=etree.Element(nspre_mtname[0],nsmap=self.nsmap);
                pass
            else : 
                # explicit prefix
                maintag=etree.Element("{%s}%s" % (self.nsmap[nspre_mtname[0]],nspre_mtname[1]),nsmap=self.nsmap)
                pass
            
            self.doc=etree.ElementTree(maintag)
            self.modified=True;

            if self.use_locking:
                self._flush(rwlock=True)  # creates low-level lock on file if filename is set
                self.rw_lockcount=1
                pass
            pass
        

        
        pass

    def _merge_rootnode_namespaces(self,nsmap_to_merge):
        """Merge namespaces listed in nsmap into the root node, if possible
        (we don't overwrite existing mappings in the root node)
        NOTE: Invalidates references to document root!

"""

        # As of now you can't directly ask lxml to add a namespace itself. 
        # You have to rewrite the root element(!)
        # see: http://stackoverflow.com/questions/11346480/lxml-add-namespace-to-input-file
        rootel=self.doc.getroot()
        nsmap={}
        nsmap.update(rootel.nsmap)
        changed=False
        # Check if each prefix is already in the rootnode's namespace and not mapped  
        reverse_nsmap=dict((nsmap[k], k) for k in nsmap)
        for prefix in nsmap_to_merge:
            if not prefix in nsmap and not nsmap_to_merge[prefix] in reverse_nsmap: # don't any replace pre-existing mapping in file
                nsmap[prefix]=nsmap_to_merge[prefix]
                changed=True
                pass
            pass
        if changed: 
            # Replace root element 
            new_rootel=etree.Element(rootel.tag, attrib=rootel.attrib,nsmap=nsmap)
            new_doc=etree.ElementTree(new_rootel)
            # Move root element's children
            new_rootel[:]=rootel[:]
            new_rootel.text=rootel.text
            new_rootel.tail=rootel.tail
            
            # Move siblings (processing instructions, comments, xml declaration)
            cursibling=new_rootel
            while rootel.getprevious() is not None:
                preceding_sibling=rootel.getprevious()
                cursibling.addprevious(preceding_sibling)
                cursibling=preceding_sibling
                pass

            cursibling=new_rootel
            while rootel.getnext() is not None:
                succeeding_sibling=rootel.getnext()
                cursibling.addnext(succeeding_sibling)
                cursibling=succeeding_sibling
                pass
            pass
            
            self.doc=new_doc
            pass

        pass

    def _pull_in_rootnode_namespaces(self):
        # Note: _pull_in_rootnode_namespaces() no longer used because we shouldn't be using any namespace prefixes that we have not specified ourselves (lest a file with an unexpected mapping screw things up in weird ways
        """Pull namespaces listed in the root node into our
        namespaces/nsmap dictionary, without overwriting anything.
        """
        nsmap=self.doc.getroot().nsmap
        for nspre in nsmap:
            url=nsmap[nspre]
            if nspre is None: 
                continue  # ignore prefix-less mapping
            if not nspre in self.nsmap:
                self.nsmap[nspre]=url
                assert(not nspre in self.namespaces)
                self.namespaces[nspre]=url
                pass
            pass
        pass

    def suggest_namespace_rootnode(self,prefix,url):
        """Add a namespace prefix definition to the root 
        element (if that prefix is not already used)
        NOTE: Invalidates references to document root!
        (document must be locked for read/write access if applicable)"""
        
        self._merge_rootnode_namespaces({prefix: url})
        self.modified=True
        

    def merge_namespace(self,prefix,url):
        """Add (or replace) namespace prefix definition in internal 
        table. 
        prefix:    prefix to add/replace
        url:       New definition
        """
        
        self.nsmap[prefix]=url
        if prefix is not None:
            self.namespaces[prefix]=url
            pass
        
        pass
    
    # use addresyncnotify to get notifications after a resync -- so you can see if anything changed
    def addresyncnotify(self,notify,*args,**kwargs):
        """You can set yourself up to be notified after a resync. The
           notify function will be called with the provided additional 
           list and keyword arguments. Please note that for the moment
           no detection is done of whether the file has actually changed
             -- it is completely reread anyway"""
        self.resyncnotify.append((notify,args,kwargs))
        pass

    # Note: for remresyncnotify, the notify must be EXACTLY the same & the args passed must pass an equality test (==)
    def remresyncnotify(self,notify,precautionary,*args,**kwargs):
        """This function removes a resync notify that was added with 
           addresyncnotify(). Please note that the notify must be
           EXACTLY the same and the args passed must pass an equality 
           comparison with the args passed to addresyncnotify()

           !!!BUG Note that the current implementation does not correctly
           perform this equality test for kwargs, so if kwargs are 
           provided to addresyncnotify, the test will fail and you 
           will crash with an assertion failed.

           if precautionary is true, a failure of the resyncnotify to be present
           will not be diagnosed
"""
        removed=False
        
        for notifyentry in self.resyncnotify:
            (lnotify,largs,lkwargs)=notifyentry

            # !!!! Need to handle kwargs here!!! 
            # check if notify and args match exactly
            if lnotify == notify and all(map((lambda larg,arg: larg == arg),largs,args)) and lkwargs==kwargs:
                
                self.resyncnotify.remove(notifyentry)
                removed=True
                break
            pass
        if not precautionary:
            assert(removed) # if this fails, somebody tried to remove a nonexistant notification
            pass
        pass

    def get_filehref(self):
        # get the href... returns a mem:// URI for in-memory checklists
        if self.filehref is None:
            return dc_value.hrefvalue(generate_inmemory_id(self))
        return self.filehref
    
    def getcontexthref(self):
        #sys.stderr.write("xmldoc filehref: %s\n" % (str(self.filehref)))
        #sys.stderr.write("contexthref: %s\n" % (str(self.contexthref)))
        if self.filehref is not None:
            #sys.stderr.write("filehref contextlist: %s\n" % (str(self.filehref.contextlist)))
            #sys.stderr.write("filehref leafless contextlist: %s\n" % (str(self.filehref.leafless().contextlist)))
            # context is no longer leafless so that we
            # can support document self- and internal-references
            return self.filehref     # .leafless()
        else:
            #sys.stderr.write("contexthref contextlist: %s\n" % (str(self.contexthref.contextlist)))
            return self.contexthref
        pass

    def setcontexthref(self,contexthref,force_abs_href=False):
        # For an xmldoc with no filename set, adjust the contextdir
        # for xlink:hrefs to contextdir. 
        # If contextdir is already set will do fixups on 
        # all xlink:hrefs in the tree.
        # force_abs_href=True will force convert all relative xlink:hrefs
        # into absolute (and also allows contextdir=None)

        assert(self.filehref is None) # filename overrides context!

        #if contexthref is not None:
        #    contexthref=contexthref.leafless()  contexts are no longer always leafless
        #    pass
        
        # we should be locked!
        self.lock_rw()

        try: 
        
            oldcontexthref=self.contexthref
            if oldcontexthref is not None:
                modcnt=_xlinkcontextfixuptree(self.doc,oldcontexthref,contexthref,force_abs_href=force_abs_href)
                if modcnt > 0: 
                    self.modified=True
                    pass
                pass
            pass
        finally: 
            self.unlock_rw()
            pass


        assert(isinstance(contexthref,dc_value.hrefvalue))
        self.contexthref=contexthref
        pass

    def get_href(self,contextnode=None,xpath=None,namespaces=None,extensions=None,variables=None):
        # convert an xlink:href=... to a dc_value.hrefvalue object
        # if contextnode is None, context is assumed to be the root
        # if xpath is None, path is assumed to be the context node.
        # xpath should be path to a node which contains the xlink:href attribute
        # Remaining parameters are passed to xpathsingle()
        # for help in evaluating the xpath
        # returns dc_value.hrefvalue object.
        # Raises NameError if the xpath gives zero or multiple results
        # raises AttributeError if no suitable xlink:href is found in the tag
        # can be found

        if contextnode is None:
            contextnode=self.doc.getroot()
            pass

        if xpath is None:
            worknode=contextnode
            provenance.xmldocelementaccessed(self,worknode)
            pass
        else:
            # provenance handled by xpathsingle
            worknode=self.xpathsingle(xpath,namespaces=namespaces,contextnode=contextnode,extensions=extensions,variables=variables)
            pass

        if not "{http://www.w3.org/1999/xlink}href" in worknode.attrib:
            raise AttributeError("get_href(): xlink:href not found in node")

        href=worknode.attrib["{http://www.w3.org/1999/xlink}href"]
        
        hrefvalue=dc_value.hrefvalue(href,contexthref=self.getcontexthref())
        return hrefvalue
            
        

    def get_href_absurl(self,contextnode=None,xpath=None,namespaces=None,extensions=None,variables=None):
        # convert an xlink:href=... to an absolutized url 
        # if contextnode is None, context is assumed to be the root
        # if xpath is None, path is assumed to be the context node.
        # xpath should be path to a node which contains the xlink:href attribute
        # Remaining parameters are passed to xpathsingle()
        # for help in evaluating the xpath
        # returns URL.
        # Raises NameError if the xpath gives zero or multiple results
        # raises AttributeError if no suitable xlink:href is found in the tag
        # can be found
        # Raises IOError if the xlink:href does not refer to a local file


        hrefobj=self.get_href(contextnode=contextnode,xpath=xpath,namespaces=namespaces,extensions=extensions,variables=variables)
        

        if not hrefobj.islocalfile():
            raise IOError("get_href_absurl: URL \"%s\" does not refer to a local file" % (str(hrefobj)))

        return hrefobj.absurl()
    

    def get_href_filepath(self,contextnode=None,xpath=None,namespaces=None,extensions=None,variables=None):
        # convert an xlink:href=... to a complete filesystem path
        # if contextnode is None, context is assumed to be the root
        # if xpath is None, path is assumed to be the context node.
        # xpath should be path to a node which contains the xlink:href attribute
        # Remaining parameters are passed to xpathsingle()
        # for help in evaluating the xpath
        # returns filename.
        # Raises NameError if the xpath gives zero or multiple results
        # raises AttributeError if no suitable xlink:href is found in the tag
        # can be found
        # Raises IOError if the xlink:href does not refer to a local file


        hrefobj=self.get_href(contextnode=contextnode,xpath=xpath,namespaces=namespaces,extensions=extensions,variables=variables)
        

        if not hrefobj.islocalfile():
            raise IOError("get_href_filepath: URL \"%s\" does not refer to a local file" % (str(hrefobj)))
        
        path=hrefobj.getpath()
        
        return path
    


    def set_href(self,href,readonly=False,contexthref=None,force_abs_href=False):
        """This is used to set a file location if the document did
           not have one, or to set a new file location (i.e. href, i.e. filename). 
           It also 
           updates the readonly attribute (default False). 

           if file is currently locked, it triggers a write under the old href
        (i.e. filename)

        It triggers a write under the new href (i.e. filename)
           unless readonly is set. 

           Note: if the file is not locked, and changes have been made 
           to the on disk copy, and you change the filename, those 
           changes will NOT be copied into the new file. 
           If you want such behavior, lock the file (thereby reading in 
           the changes) prior to calling setfilename.

           If the file is new and we're supposed to be locked, 
           this creates the lock too. 

           NOTE: readonly applies to the new name, but NOT NECESSARILY 
           the old name
           If the name changes to something other than None, readonly must not be set
        
           If the name changes to None, you can specify a new contexthref
           and it will convert xlink:href's to the new contexthref. 
           If you don't specify the new contexthref, it will store the 
           old context in the xmldoc contexthref field. 
           
           In general, xlink:hrefs will be updated with the change. 
           if force_abs_href is True, then all such updates will be to 
           absolute paths

        """

        #sys.stderr.write("setfilename %s\n" % (filename))
 
        #import pdb as pythondb
        #pythondb.set_trace()

        oldhref=self.filehref

        if self.filehref is None:
            #oldcanonname=None
            oldcontexthref=self.contexthref
            #oldcanoncontextdir=canonicalize_path(self.contextdir)
            pass
        else:
            #oldcanonname=canonicalize_path(oldfilename)
            oldcontexthref=self.filehref   #.leafless()
            pass
            
        if href is None:
            #if contexthref is not None:
            #    contexthref=contexthref.leafless()
            #    pass
            if contexthref is None:
                newcontexthref=oldcontexthref
                pass
            else:
                newcontexthref=contexthref
                pass
            pass
        else:
            newcontexthref=href    #.leafless()
            assert(contexthref is None) # should not supply a contexthref if supplying a filename
            pass

        # our memory of initial state lockcounts
        ro_lockcount=0
        rw_lockcount=0

        #if filename is None:
        #    canonfilename=None
        #    pass
        #else : 
        #    canonfilename=canonicalize_path(filename)
        #    pass
        
        if ((oldhref is None) ^ (href is None)) or oldhref != href: # ^ operator is XOR
            
            # start by flushing (if necessary) and unlocking the old file
            if oldhref is not None:
                if self.rw_lockcount > 0:
                    assert(self.lockfd >= 0)
                    assert(not self.readonly)
                    self._flush()
                    self._unlock_rw()
                    rw_lockcount=self.rw_lockcount
                    self.rw_lockcount=0
                    pass
                elif self.ro_lockcount >0:
                    self._unlock_ro()
                    ro_lockcount=self.ro_lockcount
                    self.ro_lockcount=0
                    pass
                pass
            else : 
                ro_lockcount=self.ro_lockcount
                rw_lockcount=self.rw_lockcount
                self.ro_lockcount=0
                self.rw_lockcount=0
                pass
            

            assert(self.lockfd < 0)

            # update the filename
            self.filehref=href
            if self.filehref is not None:
                assert(isinstance(href,dc_value.hrefvalue))
                self._filename=self.filehref.getpath()
                pass
            else:
                self._filename=None
                pass
            
            # do xlink:href fixups for moving from old location to new location
            if self.doc is not None:
                _xlinkcontextfixuptree(self.doc,oldcontexthref,newcontexthref,force_abs_href=force_abs_href)
                pass
            else: 
                _xlinkcontextfixuptree(self.olddoc,oldcontexthref,newcontexthref,force_abs_href=force_abs_href)
                pass

            
            # if self.filehref is None:
            assert(isinstance(newcontexthref,dc_value.hrefvalue))
            self.contexthref=newcontexthref
            #    pass
            #else: 
            #    self.contexthref=None
            #    pass

            # flush out under the new name
            if self.filehref is not None:
                assert(not readonly)

                try : 
                    #if self.rw_lockcount > 0:
                    #    self._flush(rwlock=True)  # if new filename is not none, this gives us our low level lock.
                    #    pass
                    #elif self.ro_lockcount > 0:
                    #    self._flush(rolock=True)  # if new filename is not none, this gives us our low level lock.
                    #
                    #    pass                        
                    #else : 
                    #    self._flush(ok_to_be_unlocked=True)
                    #    pass

                    # now we resync as well as flush, to make sure
                    # resyncnotifies get called, etc. 
                    # so the flush drops the lock
                    # sys.stderr.write("flushing %s\n" % (self.filename))
                    self._flush(ok_to_be_unlocked=True)

                    if rw_lockcount > 0:
                        self._resync(rwlock=True)  # if new filename is not none, this gives us our low level lock.
                        self.rw_lockcount=rw_lockcount
                        rw_lockcount=0
                        pass
                    elif ro_lockcount > 0:
                        self._resync(rolock=True)  # if new filename is not none, this gives us our low level lock.
                        self.ro_lockcount=ro_lockcount
                        ro_lockcount=0
                        pass                        
                    else : 
                        #sys.stderr.write("setfilename: rw_lockcount=%d; self.rw_lockcount=%d\n" % (rw_lockcount,self.rw_lockcount))
                        self._resync()
                        #sys.stderr.write("setfilename: rw_lockcount=%d; self.rw_lockcount=%d\n" % (rw_lockcount,self.rw_lockcount))

                        pass
            
                    pass
                except: 
                    self.filehref=None # if flush failed, set filename to None
                    self._filename=None
                    raise
                    
                pass
            pass
            
        self.readonly=readonly

        pass

    def set_readonly(self,readonly):
        """Set readonly status... If locking is used, must be fully unlocked."""

        #if self.use_locking and (self.ro_lockcount > 0 or self.rw_lockcount > 0):
        #    raise ValueError("May not set readonly flag of xmldoc %s while locked (ro_lockcount=%d; rw_lockcount=%d" % (str(self.filename),self.ro_lockcount,self.rw_lockcount))
        if self.rw_lockcount > 0:
            assert(not self.readonly)
            # flush out any changes...
            if self.filehref is not None:
                assert(self.lockfd >= 0)
                self._flush()
                pass
            pass
        
        if self.use_databrowse and not readonly:
            raise ValueError("read/write mode on xmldoc %s incompatible with use_databrowse" % (str(self._filename)))
        
            
        
        self.readonly=readonly
        
        
        pass
    

    def xpathsingle(self,xpath,namespaces=None,contextnode=None,extensions=None,variables=None,default=NameError("No result found for xpath"),noprovenance=False):
        """xpathsingle() finds a single element based on an 
        arbitrary XPath expression. If 0 elements or more than one
        element is returned, it raises a NameError. The configured
        nsmap may be used, but note that that the default namespace
        is inoperative for xpath (implicit namespace means null namespace). 

        If your path is simple, and you don't care if there are 
        excess matches, use the find() method instead 

        xpath:         Path to search
        namespaces:    additional namespaces
        contextnode:   Context node or list for relative search
        extensions:    additional extensions
        
"""
        # self.doc.write(sys.stderr,pretty_print=True)


        taglist=self.xpath(xpath,namespaces=namespaces,contextnode=contextnode,extensions=extensions,variables=variables,noprovenance=noprovenance);
        if isinstance(taglist,basestring) or isinstance(taglist,numbers.Number):
            # single by definition!
            
            # Provenance support provided by base xpath method
            # lxml text nodes and attributes are "smart strings"
            # with a getparent() method to identify the enclosing element
            # if  hasattr(taglist,"getparent") and taglist.getparent() is not None:
            #     provenance.xmldocelementaccessed(self,taglist.getparent())
            #     pass
            # else :
            #     provenance.warnnoprovenance("Unable to identify provenance of XPath result %s for %s on file %s" % (unicode(taglist),xpath,self.filename))
            #     pass
                
            return taglist
        
        if len(taglist) > 1:
            raise NameError("XPath query %s returned %d elements" % (xpath,len(taglist)))
        if len(taglist) == 0:
            if isinstance(default,BaseException):
                raise default
            else: 
                return default
            pass
        
        # provenance.xmldocelementaccessed(self,taglist[0])
        
        return taglist[0]

    def xpathsinglecontext(self,contextnode,xpath,namespaces=None,extensions=None,variables=None,default=NameError("No result found for xpath"),noprovenance=False):
        """Alias for xpathsingle(xpath,namespaces,contextnode)"""

        return self.xpathsingle(xpath,namespaces=namespaces,contextnode=contextnode,extensions=extensions,variables=variables,default=default,noprovenance=noprovenance)

    def xpathsingleint(self,xpath,namespaces=None,contextnode=None,extensions=None,variables=None,default=NameError("No result found for xpath"),noprovenance=False):
        """Like xpathsingle(), but converts result to an integer. 
        Do NOT use the number() function of xpath, as that gives floats,
        not integers."""
        resultnode=self.xpathsingle(xpath,namespaces=namespaces,contextnode=contextnode,extensions=extensions,variables=variables,default=default,noprovenance=noprovenance)
        
        if isinstance(resultnode,basestring) or isinstance(resultnode,numbers.Number):
            return int(resultnode)
            pass
        else : 
            # should be an etree.Element
            return int(resultnode.text)
        pass

    def xpathsinglecontextint(self,contextnode,xpath,namespaces=None,extensions=None,variables=None,default=NameError("No result found for xpath"),noprovenance=False):
        """Alias for xpathsingleint(xpath,namespaces,contextnode)"""

        return self.xpathsingleint(xpath,namespaces=namespaces,contextnode=contextnode,extensions=extensions,variables=variables,default=default,noprovenance=noprovenance)


    #!!!*** Should build in unit support
    def xpathsinglefloat(self,xpath,units=None,namespaces=None,contextnode=None,extensions=None,variables=None,default=NameError("No result found for xpath"),noprovenance=False):
        """Like xpathsingle, but converts result to a float"""
        assert(units is None) # Unit support not implemented yet!

        resultnode=self.xpathsingle(xpath,namespaces=namespaces,contextnode=contextnode,extensions=extensions,variables=variables,default=default,noprovenance=noprovenance)
        
        if isinstance(resultnode,basestring) or isinstance(resultnode,numbers.Number):
            return float(resultnode)
            pass
        else : 
            # should be an etree.Element
            return float(resultnode.text)
        pass

    #!!!*** Should build in unit support
    def xpathsinglecontextfloat(self,contextnode,xpath,units=None,namespaces=None,extensions=None,variables=None,default=NameError("No result found for xpath"),noprovenance=False):
        """Alias for xpathsinglefloat(xpath,namespaces,contextnode)"""

        return self.xpathsinglefloat(xpath,units=units,namespaces=namespaces,contextnode=contextnode,extensions=extensions,variables=variables,default=default,noprovenance=noprovenance)
        


    def xpathsinglestr(self,xpath,namespaces=None,contextnode=None,extensions=None,variables=None,default=NameError("No result found for xpath"),noprovenance=False):
        """Like xpathsingle, but converts result to unicode"""
        resultnode=self.xpathsingle(xpath,namespaces=namespaces,contextnode=contextnode,extensions=extensions,variables=variables,default=default,noprovenance=noprovenance)

        if resultnode is default:
            return resultnode
        elif isinstance(resultnode,basestring):
            return unicode(resultnode)
        else : 
            # should be an etree.Element
            return unicode(resultnode.text)
        pass
        
    def xpathsinglecontextstr(self,contextnode,xpath,namespaces=None,extensions=None,variables=None,default=NameError("No result found for xpath"),noprovenance=False):
        """Alias for xpathsinglestr(xpath,namespaces,contextnode)"""

        return self.xpathsinglestr(xpath,namespaces=namespaces,contextnode=contextnode,extensions=extensions,variables=variables,default=default,noprovenance=noprovenance)

    def gettag(self,element,namespaces=None):
        """Get the name of the tag for a specific element, with proper
        namespace prefix. Raises IndexError if no prefix available"""

        self.element_in_doc(element)  # Verify that element is indeed in our document

        nsurl_elname=element.tag.split("}")
        if len(nsurl_elname)==1:
            # no prefix
            return element.tag
        else : 
            nsurl=nsurl_elname[0][1:]  # drop leading '{'
            if namespaces is not None:
                iv_namespaces=dict((v,k) for k, v in namespaces.items())
                if nsurl in iv_namespaces:
                    return "%s:%s" % (iv_namespaces[nsurl],nsurl_elname[1])
                pass
            iv_snamespaces=dict((v,k) for k, v in self.namespaces.items())
            if nsurl in iv_snamespaces:
                return "%s:%s" % (iv_snamespaces[nsurl],nsurl_elname[1])
            else: 
                raise IndexError("No namespace prefix for namespace %s of tag %s found" % (nsurl,element.tag))
            pass
        pass
    
    def getsingleelement(self,xpath):
        """getsingleelement() is an alias for xpathsingle() for 
        backward compatibility."""
        return self.xpathsingle(xpath)


    def postexcdialog(self,exctype,value,tback,initialload=False,cantretry=False):
        """ This routine is called when a resynchronization fails. If
            gtk2/gtk3 are loaded, it brings up a modal error/warning 
            dialog with the exception info. Otherwise it writes to stderr.

            exctype:      Type object for the exception. 
            value:        Value object for the exception
            initialload:  True if this is the first load of the file
                          (to disable in-memory recovery option)
            cantretry:    Disable retry option... used in combination 
                          with initialload when the new data has been 
                          loaded in by something external (e.g we have
                          been notified of someone's changes) and 
                          it is not meaningful to retry. 
        """
            

        # !!! Factor this out and also call it from adddoc()
        # if xmlresync() fails, as well as other places where 
        # xmlresync() is called

        if not "gtk" in sys.modules and not ("gi" in sys.modules and hasattr(sys.modules["gi"],"repository") and hasattr(sys.modules["gi"].repository,"Gtk")):
            # if nothing else has loaded gtk2 or gtk3
            # Just print exception
            sys.stderr.write("Exception resyncing file %s\n%s: %s\n" % (self._filename,str(exctype.__name__),str(value)))
            return "cancel"  # text mode is non-interactive
        else : 
            loadgtk() # do our gtk imports
            pass

        if hasattr(gtk,"MessageType") and hasattr(gtk.MessageType,"WARNING"):
            # gtk3
            warningdialog=gtk.MessageDialog(type=gtk.MessageType.ERROR,buttons=gtk.ButtonsType.NONE)
            pass
        else : 
            warningdialog=gtk.MessageDialog(type=gtk.MESSAGE_ERROR,buttons=gtk.BUTTONS_NONE)
            pass

        # print ("Exception resyncing file %s\n%s: %s" % (self.filename,str(exctype),str(value)))
        filename=self._filename
        if filename is None:
            filename="(Not available)"
            pass
        warningdialog.set_markup("<b>Exception resyncing file %s</b>\n%s: %s" % (xml.sax.saxutils.escape(filename),xml.sax.saxutils.escape(str(exctype.__name__)),xml.sax.saxutils.escape(str(value))))
        retrybutton=warningdialog.add_button("Retry",1)
        if cantretry:
            retrybutton.set_sensitive(False)
            pass
        warningdialog.add_button("Cancel operation",0)
        recoverbutton=warningdialog.add_button("Recover from in-memory copy",2)
        if initialload:  # disable in-memory recovery on initial load
            recoverbutton.set_sensitive(False)
            pass
        warningdialog.add_button("Debug",3)

        warningdialogval=warningdialog.run()
        warningdialog.destroy()
        if warningdialogval==1:
            return "retry"
        elif warningdialogval==2:
            return "recover"
        elif warningdialogval==3:
            import pdb as pythondb
            print("exception: %s: %s" % (exctype.__name__,str(value)))
            sys.stderr.write(tback)
            pythondb.post_mortem()
            pass
        else:
            return "cancel"
        pass
    

    def _resync(self,initialload=False,FileObj=None,rolock=False,rwlock=False):
        """_resync() reads in any changes from disk.
        
        INTERNAL USE ONLY

        This should generally be called prior to making a group 
        of changes to the document. Likewise you should call flush()
        after making the changes. 

        !!! VERY IMPORTANT !!! Any references you have to internal 
        elements may be LOST when you resync() -- You need to 
        find them again with  find()!!!!

        NOTE: Will merge contents of our nsmap into the root node of
        the resync'd documents. Pre-existing mappings in the file 
        take precidence over our in-memory mapping. 

        initialload:    if True, this is the initial load and it is 
                        not useful to recover from memory
        FileObj:        if not None, load from this file-like object
                        rather than reading file from disk. 

        rolock,rwlock:  Set if you want resync to acquire a low level 
                        read only or read write lock. Does not adjust
                        lock counts except temporarily during notify callback
        """

        if rolock or rwlock: 
            assert(self.lockfd==-1)
            pass

        assert(not self.modified); # shouldn't call resync() after making any local changes
        # print "Resync: id=%d self.filename=%s" % (id(self),self.filename)
        self.shouldbeunlocked() # make sure self.olddoc is set

        if self.debug_last_serialized is not None and etree.tostring(self.olddoc,encoding="utf-8") != self.debug_last_serialized:
            raise ValueError("Document content has changed without modified flag being set!")

        
            

        if self.filehref is not None or FileObj is not None:
            retry=True
            while retry:
                retry=False
                lockfd=-1
                fh=None
                try:
                    if self.use_databrowse:
                        if dbl is None: 
                            raise ImportError("databrowse.lib.db_lib not successfully imported. Can not use databrowse_mode.")

                        if rolock or rwlock:
                            raise ValueError("rolock and rwlock not supported with databrowse!")
                        self.doc=dbl.GetXML(self._filename, output=dbl.OUTPUT_ETREE)
                        self.lastfileinfo=None
                        pass
                    else :


                        # Use parser with remove_blank_text otherwise pretty_print
                        # won't work on output
                        parser=etree.XMLParser(remove_blank_text=True,huge_tree=True)
                        if FileObj is not None:
                            # stream object. Don't have to do anything to lock it
                            self.doc=etree.parse(FileObj,parser)
                            self.lastfileinfo=None
                            pass
                        else :
                            # Open an actual file...

                            # Always start by creating a rwlock
                            # on the file, because we may write 
                            # to it through the update notifications
                            # even if we just want to lock it read-only
                            
                            reuseold=False;

                            if os.name=="posix":
                                fh=open(self._filename,"rb")
                                self.lockfh=fh
                                pass
                            elif os.name=="nt" and self.lockfh is None:
                                fh=open(self._filename,"rb+") # always open read-write binary mode for NT
                            else:
                                fh=self.lockfh
                                pass
                            
                            #if rolock:
                            #    assert(os.name=="posix") 
                            #    lockfd=os.dup(fh.fileno())
                            #    self._lock_ro(lockfd) # pass ownership of lockfd
                            #    if self.lastfileinfo is not None and fileinfo(lockfd)==self.lastfileinfo: 
                            #        reuseold=True # avoid rereading file
                            #        pass
                            #    pass
                            # el

                            # always obtain rw lock whether or not 
                            # we are locking because resyncnotify
                            # routine might need to write

                            # On POSIX, lockfd owns an extra copy of the file descriptor and the one we use for
                            # reading/writing is only open when needed
                            # On NT, lockfd is the primary copy of the file descriptor, and we grab it from
                            # there as needed. Also store Python file handle in lockfh

                            # if rolock or rwlock:
                            #assert(os.name=="posix")
                            if os.name=="posix":
                                lockfd=os.dup(fh.fileno())
                                pass
                            else:
                                lockfd=fh.fileno()
                                pass
                            self._lock_rw(lockfd,fh) # pass ownership of lockfd/fh
                            if self.lastfileinfo is not None and fileinfo(lockfd)==self.lastfileinfo: 
                                reuseold=True # avoid rereading file
                                pass
                            #else: 
                            #    self.lastfileinfo=None
                            #    pass
                            if reuseold and self.olddoc is not None and not self.debug: # reusing old parsed copies is disabled in debug mode to avoid hiding referencing errors 
                                self.doc=self.olddoc
                                self.olddoc=None
                                pass
                            else : 
                                
                                self.doc=etree.parse(fh,parser)
                                if self.lockfd >= 0: # if locked, we can save this file info
                                    self.lastfileinfo=fileinfo(self.lockfd)
                                    pass
                                else :
                                    self.lastfileinfo=None
                                pass
                            if os.name=="posix":
                                fh.close()  # NOTE THAT THIS IS INCOMPATIBLE WITH fcntl() locking as this close will drop all locks on this file. Thus we use flock instead.
                                pass
                            
                            pass
                        pass
                    #if not self.readonly:
                        #self._merge_rootnode_namespaces(self.nsmap)
                    #    pass
                    # Note: _pull_in_rootnode_namespaces() removed because we shouldn't be using any namespace prefixes that we have not specified ourselves (lest a file with an unexpected mapping screw things up in weird ways
                    # self._pull_in_rootnode_namespaces()
                     
                    assert(self.doc is not None)
   
                    if self.debug:
                        self.debug_last_serialized=etree.tostring(self.doc,encoding="utf-8")
                        pass

                    # print "Resync: self.doc=%s" % (str(self.doc))
                    # temporarily increment lockcounts so it doesn't look like we are unlockes
                    
                    #if rwlock: 
                    #    self.rw_lockcount+=1
                    #    pass
                    #
                    #if rolock:

 
                    # always increment rw_lockcount whether or not 
                    # we are rolocking because resyncnotify
                    # routine might need to write
                    self.rw_lockcount+=1
            

                    #sys.stderr.write("doing resync notifies for %s; self.doc=%s\n" % (self.filename,str(self.doc)))
                    for (notify,args,kwargs) in self.resyncnotify:
                        assert(self.doc is not None)
                        #if args[0]=="dc:summary/dc:plans":
                        #    import pdb as pythondb
                        #    pythondb.set_trace()
                        notify(self,*args,**kwargs)
                        pass

                    # return lockcounts where they belong (caller will provide primary lockcount incrementing)
                    #if rwlock: 
                    #    self.rw_lockcount-=1
                    #    pass

                    #if rolock: 
                    self.rw_lockcount-=1

                    if self.modified:
                        # if notify routine made changes, they should 
                        # be flushed out
                        self._flush()
                        pass
                    
                    if rolock and self.lockfd >= 0:
                        # currently holding a rwlock
                        # but user asked for an rolock
                        # attempt to convert (non-atomic process)
                        self._lock_convert_rw_to_ro()
                        
                        # check if fileinfo has changed
                        if fileinfo(self.lockfd)!=self.lastfileinfo:
                            #sys.stderr.write("fileinfo=%s\nlastfileinfo=%s\n\n" % (fileinfo(self.lockfd),self.lastfileinfo))
                            # Need to go back and retry
                            self._unlock_ro()
                            lockfd=-1
                            retry=True
                            continue
                        pass
                    elif not rwlock and self.lockfd >= 0:
                        # relinquish lock, as we weren't asked for it
                        self._unlock_rw()
                        lockfd=-1
                        pass
                    pass
                except KeyboardInterrupt:
                    raise  # KeyboardInterrupt does not suggest the user wants to retry
    
                except:
                    # raise #!!!***
                    (exctype,value)=sys.exc_info()[:2]
                    tback=traceback.format_exc()
                    if self.nodialogs or (exctype.__name__=="IOError" and initialload):
                        # Don't bring up a dialog on initialload if 
                        # we had an IOerror. Just raise the exception back up
                        result="cancel"
                        pass
                    else:
                        result=self.postexcdialog(exctype,value,tback,initialload,cantretry=(FileObj is not None))
                        pass

                    if lockfd != -1: 
                        # We left something locked... see also _unlock_ro() and _unlock_rw()
                        assert(lockfd==self.lockfd)
                        #fcntl.flock(lockfd,fcntl.LOCK_UN)
                        self.__unlock()
                        if os.name=="posix":
                            os.close(lockfd)
                            pass
                        elif os.name=="nt":
                            fh.close()
                            pass
                        
                        self.lockfd=-1
                        self.lockfh=None
                        

                    if result=="retry": # retry
                        retry=True
                        continue
                    elif result=="recover": # recover in-memory
                        self.doc=self.olddoc
                        if self.debug:
                            self.debug_last_serialized=etree.tostring(self.doc,encoding="utf-8")
                            pass
                        return
                    else  : # result==cancel
                        # sys.exit(1)
                        raise
                    pass
                
                pass
            pass
        else: 
            # self.filename is None and no FileObj provided
            # attempt to restore from olddoc
            if self.olddoc is not None:
                self.doc=self.olddoc
                self.olddoc=None
                pass
            pass
        pass

    def remelement(self,element,nocheck=False):
        # Remove the provided element from the document
        if not nocheck:
            self.element_in_doc(element)
            pass
        
        element.getparent().remove(element)
        self.modified=True
        pass

    def remelements(self,elementlist):
        # Remove the provided elements from the document
        for element in elementlist:
            self.remelement(element)
            pass
        pass

    def addtreefromdoc(self,parent,sourcedoc,sourceel):
        """This routine copies sourceel (and sub-elements) from sourcedoc,
           and copies it into this document, adding it as a child of the 
           specified parent"""
        self.element_in_doc(parent)
        
        sourcecopy=copy.deepcopy(sourceel)

        parent.append(sourcecopy)
        
        for el in sourcecopy.iter():  # iter() gives descendant-or-self
            provenance.elementgenerated(self,el)
            pass

        if sourcedoc is not None:
            for el in sourceel.iter():
                provenance.xmldocelementaccessed(sourcedoc,el)
                pass
            pass

        pass
        
    
    def addelement(self,parent,elname): 
        """This routine creates and appends a new empty element to the document.
           parent:  a path (find()-style) or an element, or None to 
                    represent the main tag. 
           elname:  name of the element prefix, with namespace prefix if
                    appropriate 
           The newly created element is returned
        """

        self.element_in_doc(parent)

        if parent is None:
            parent=self.doc.getroot()
            pass

        if isinstance(parent,basestring):
            parentstr=parent
            parent=self.find(parent) # convert path to element
            if parent is None:
                raise ValueError("Parent element %s not found in file %s" % (parentstr,str(self.filehref)))
            pass

        assert (not elname.startswith("@")) # attributes can only be added with AddSimpleElement

        # regular element, not attribute
        # Indent according to the number parent traversals to get to the document
        
        nspre_elname=elname.split(":")
        
        assert(len(nspre_elname) <= 2)

        if len(nspre_elname)==1:
            # no explicit prefix
            # create element
            newnode=etree.Element(elname,nsmap=self.nsmap);
            pass
        else : 
            # explicit prefix
            newnode=etree.Element("{%s}%s" % (self.nsmap[nspre_elname[0]],nspre_elname[1]),nsmap=self.nsmap)
            pass
        parent.append(newnode);

        # Record provenance of this element
        provenance.elementgenerated(self,newnode)
        
        self.modified=True;

        # if self.autoflush:
        #     self.flush()
        #     pass

        return newnode

    def copyelements(self,parent,sourcedoc,sourceelements): 
        """This routine copies preexisting elements (sourceelements -- 
           a list of elements) from another document (sourcedoc)
           into this document.
           parent:  a path (find()-style) or an element, or None to 
                    represent the main tag. 
           sourcedoc: xmldoc from which to copy the elements
           sourceelements: list of elements to copy
        """

        self.element_in_doc(parent)

        if parent is None:
            parent=self.doc.getroot()
            pass

        if isinstance(parent,basestring):
            parent=self.find(parent) # convert path to element
            pass

	# Out List Of New Nodes
        newnodes = []

        # regular element, not attribute
        # Indent according to the number parent traversals to get to the document
        # !!!*** Should probably record provenance recursively!!!***
        
        for node in sourceelements: 
            newnode=copy.deepcopy(node)
            parent.append(newnode);
            # Record provenance of this element
            if sourcedoc is not None:
                provenance.xmldocelementaccessed(sourcedoc,node)
                pass
            provenance.elementgenerated(self,newnode)
            newnodes.append(newnode)
            pass
            
        self.modified=True;

        # if self.autoflush:
        #     self.flush()
        #     pass

        return newnodes



    def insertelement(self,parent,position,elname): 
        """This routine creates and inserts a new empty element to the document.
           parent:  a path (find()-style) or an element, or None to 
                    represent the main tag.
           position: Position within parent... 0 means first, -1 means last.
           elname:  name of the element prefix, with namespace prefix if
                    appropriate 
        """

        if parent is None:
            parent=self.doc.getroot()
            pass

        if isinstance(parent,basestring):
            parent=self.find(parent) # convert path to element
            pass

        self.element_in_doc(parent)
        

        assert (not elname.startswith("@")) # attributes can only be added with AddSimpleElement

        # regular element, not attribute
        # Indent according to the number parent traversals to get to the document
        
        nspre_elname=elname.split(":")
        
        assert(len(nspre_elname) <= 2)

        if len(nspre_elname)==1:
            # no explicit prefix
            # create element
            newnode=etree.Element(elname,nsmap=self.nsmap);
            pass
        else : 
            # explicit prefix
            newnode=etree.Element("{%s}%s" % (self.nsmap[nspre_elname[0]],nspre_elname[1]),nsmap=self.nsmap)
            pass
        parent.insert(position,newnode)

        # notify provenance engine. !!! Should also check to see if any 
        # provenance points at following elements, in case they need new 
        # name references!
        provenance.elementgenerated(self,newnode)
        
        self.modified=True;

        # if self.autoflush:
        #     self.flush()
        #     pass

        return newnode



    def settext(self,element,text):
        """Set the text content of an element. 
           element:  The element object
           text:     string or unicode object with the replacement text

        NOTE: Doesn't currently handle text after subelements or comments properly!
        """

        self.element_in_doc(element)

        element.text=text
        self.modified=True

        # Record provenance update for this element
        provenance.elementgenerated(self,element)

        # if self.autoflush:
        #     self.flush()
        #     pass

        pass


    def gettext(self,element):
        """Set the text content of an element. 
           element:  The element object

        NOTE: Doesn't currently handle text after subelements or comments properly!

        """

        self.element_in_doc(element)

        # Record provenance update for this element
        provenance.xmldocelementaccessed(self,element)

        if element.text is None:
            return ""
        

        return element.text

    def _xpath_merge_params(self,namespaces,extensions,variables):
        if namespaces is not None:
            # merge namespaces dictionaries
            namespaces=dict(list(self.namespaces.items())+list(namespaces.items()))
            pass
        else : 
            namespaces=self.namespaces
            pass
        
        useextensions=copy.copy(self.extensions)
        if extensions is not None:
            if isinstance(extensions,(list,tuple)):
                useextensions.extend(extensions)
                pass
            else:
                useextensions.append(extensions)
                pass
            pass
        
        if variables is None:
            variables={}
            pass

        return (namespaces,useextensions,variables)

    def _xpath_record_provenance(self,path,resultlist):
        if isinstance(resultlist,basestring) or isinstance(resultlist,numbers.Number) or isinstance(resultlist,bool):
            # single result
            if  hasattr(resultlist,"getparent") and resultlist.getparent() is not None:
                provenance.xmldocelementaccessed(self,resultlist.getparent())
                pass
            else :
                # probably a string( ) method... can't track this provenance
                # provenance.warnnoprovenance("Unable to identify provenance of XPath result %s for %s on file %s" % (str(resultlist),path,self._filename))
                pass
            pass
        else :
                
            
            # notify provenance of our dependence on each node in the resultlist
            for resultel in resultlist:
                if isinstance(resultel,basestring) or isinstance(resultel,numbers.Number): #  or isinstance(resultel,bool): (always satisfied by number criterion)
                    if hasattr(resultel,"getparent") and resultel.getparent() is not None:
                        provenance.xmldocelementaccessed(self,resultel.getparent())
                        pass
                    else :
                        # probably a string( ) method... can't track this provenance
                        
                        #provenance.warnnoprovenance("Unable to identify provenance of XPath result %s for %s on file %s" % (unicode(resultel),path,self._filename))
                        pass
                    pass
                else : 
                    # Should be an element of somesort
                    provenance.xmldocelementaccessed(self,resultel)
                    pass
                pass
            pass
        pass

    def xpath(self,path,namespaces=None,contextnode=None,extensions=None,variables=None,noprovenance=False):
        """Find the specified path given the option context (or main tag)
        Additional namespaces or extensions can be provided if desired.

        path:         path to search
        namespaces:   additional namespaces to merge with the main dictionary
        contextnode:  Starting point for path, or list of starting points.
        extensions:   Any additional xpath extensions desired
        """

        self.element_in_doc(contextnode)

        assert((not self.use_locking) or self.rw_lockcount!=0 or self.ro_lockcount!=0)  # should be locked if we are using locking

        (namespaces,useextensions,variables)=self._xpath_merge_params(namespaces,extensions,variables)
        

        # sys.stderr.write("namespaces=%s\n" % (unicode(namespaces)))
        

        if contextnode is None:
            resultlist=self.doc.xpath(path,namespaces=namespaces,extensions=useextensions,**variables)
            pass
        elif isinstance(contextnode,collections.Sequence):
            # context node is some sort of list
            xpathresults=[]
            for singlenode in contextnode:                
                xpathresults.append(singlenode.xpath(path,namespaces=namespaces,extensions=useextensions,**variables))
                pass
            resultlist=[]
            for xpathresult in xpathresults:
                if isinstance(xpathresult,collections.Sequence) and not isinstance(xpathresult,basestring):
                    # Some sort of list... add contents to result
                    resultlist.extend(xpathresult)
                    pass
                else : 
                    # not a list
                    resultlist.append(xpathresult)
                    pass
                pass
            pass
        else: 
            # Single element for context node
            resultlist=contextnode.xpath(path,namespaces=namespaces,extensions=useextensions,**variables)
            pass

        if not noprovenance:
            self._xpath_record_provenance(path,resultlist)
            pass
        return resultlist
        

    def etxpath(self,path,contextnode=None,extensions=None,variables=None,noprovenance=False):
        """Find the specified path given the option context (or main tag)
        Additional namespaces or extensions can be provided if desired.

        path:         etxpath to search
        contextnode:  Starting point for path, or list of starting points.
        extensions:   Any additional xpath extensions desired
        """

        self.element_in_doc(contextnode)

        assert((not self.use_locking) or self.rw_lockcount!=0 or self.ro_lockcount!=0)  # should be locked if we are using locking

        (namespaces,useextensions,variables)=self._xpath_merge_params(None,extensions,variables)
        

        ETXobj=etree.ETXPath(path,extensions=useextensions)

        if contextnode is None:
            resultlist=ETXobj(self.doc,**variables)
            pass
        elif isinstance(contextnode,collections.Sequence):
            # context node is some sort of list
            xpathresults=[]
            for singlenode in contextnode:                
                xpathresults.append(ETXobj(singlenode,**variables))
                pass
            resultlist=[]
            for xpathresult in xpathresults:
                if isinstance(xpathresult,collections.Sequence) and not isinstance(xpathresult,basestring):
                    # Some sort of list... add contents to result
                    resultlist.extend(xpathresult)
                    pass
                else : 
                    # not a list
                    resultlist.append(xpathresult)
                    pass
                pass
            pass
        else: 
            # Single element for context node
            resultlist=ETXobj(contextnode,**variables)
            pass
        
        if not noprovenance:
            self._xpath_record_provenance(path,resultlist)
            pass
        return resultlist
    


    
    def xpathcontext(self,contextnode,path,namespaces=None,extensions=None,variables=None,noprovenance=False):
        """Alias for xpath(path,namespaces,contextnode)"""
        return self.xpath(path,namespaces=namespaces,contextnode=contextnode,extensions=extensions,variables=variables,noprovenance=noprovenance)
        
    def xpathnumpy(self,path,namespaces=None,contextnodes=None,extensions=None,variables=None,iscomplex=False,oneper=True,desiredunits=None):
        """Like xpath, but convert node-set to floating point, return as 
        numpy array along with units.

        All entries are presumed to have the same units. An exception
        will be thrown if a unit mismatch is found. 

        contextnodes can be either a single context node, or a list, 
        in which case if oneper==True, there must be exactly one result
        per context node.

        Do NOT use xpath to convert node to number

        returns (resultunits, numpyarray) where resultunits is a 
        lm_units instance. Don't forget to properly initialize lm_units!

        iscomplex:    If true, output array should be complex instead of 
                      real. 
        oneper:       If True, there must be exactly one result per 
                      context node (if contextnodes is a list)

"""


        if iscomplex:
            converter=complex
            dtype=np.complex128
            pass
        else:
            converter=float
            dtype=np.float64
        pass

        nodeset=self.xpathtonodestrlist(path,namespaces=namespaces,contextnodes=contextnodes,extensions=extensions,variables=variables,oneper=oneper)
        # nodeset=[]
        
        resultarray=np.zeros(len(nodeset),dtype=dtype)

        if desiredunits is not None:
            if isinstance(desiredunits,basestring):
                desiredunits=lmu.parseunits(desiredunits)
                pass
            resultunits=desiredunits
            pass
        else:
            resultunits=None
            pass
        
        if len(nodeset) > 0:

            for cnt in range(len(nodeset)):
                
                if not(isinstance(nodeset[cnt],basestring)):
                    # A node, not a string
                    if "{http://limatix.org/dcvalue}units" in nodeset[cnt].attrib:
                        thisresultunits=lmu.parseunits(nodeset[cnt].attrib["{http://limatix.org/dcvalue}units"])
                        pass
                    elif "units" in nodeset[cnt].attrib:
                        thisresultunits=lmu.parseunits(nodeset[cnt].attrib["units"])
                        pass
                    else:
                        thisresultunits=lmu.parseunits("") # presumed unitless
                        pass
                    thisresulttext=nodeset[cnt].text
                    pass
                else :
                    # a string, not a node
                    thisresultunits=lmu.parseunits("") # presumed unitless .... (or should we parse the text?)
                    thisresulttext=nodeset[cnt]
                    pass


                converted=converter(thisresulttext)

                isnotfinite=((iscomplex and not np.isfinite(converted.real) and not np.isfinite(converted.imag)) or
                             (not iscomplex and not np.isfinite(converted)))

                coeff=1.0

                if not(isnotfinite):
                    # only transfer units and worry about unit match for
                    # finite numbers

                    if resultunits is None and thisresultunits is not None:
                        # Record units, if we have them!
                        resultunits=thisresultunits
                        pass

                    if thisresultunits is not None and resultunits is not None:
                        # Make sure units match... extract conversion coefficient
                        coeff=lmu.compareunits(resultunits,thisresultunits)
                        pass
                
                    if thisresultunits is None:
                        raise ValueError("xpathnumpy: Missing units for cnt=%d; thisresulttext=%s" % (cnt,thisresulttext))
                    if coeff==0.0:
                        raise ValueError("Unit mismatch in array generation: %s vs. %s." % (lmu.printunits(resultunits,True),lmu.printunits(thisresultunits,True)))
                    pass
                


                
                resultarray[cnt]=converted/coeff
                                
                pass
            pass
        return (resultarray,resultunits)


    def xpathcontextnumpy(self,contextnodes,path,namespaces=None,extensions=None,variables=None,iscomplex=False,oneper=True,desiredunits=None):
        """Like xpathnumpy but must provide context nodes"""
        return self.xpathnumpy(path,namespaces=namespaces,contextnodes=contextnodes,extensions=extensions,variables=variables,iscomplex=iscomplex,oneper=oneper,desiredunits=desiredunits)

    def xpathtonodestrlist(self,path,namespaces=None,contextnodes=None,extensions=None,variables=None,oneper=True):
        """Intended for internal use only. Convert an xpath and provided 
        set of context nodes to a list of nodes or strings"""

        nodeset=[]
        if isinstance(contextnodes,list):
            for contextnode in contextnodes:
                newnodes=self.xpath(path,namespaces=namespaces,contextnode=contextnode,extensions=extensions,variables=variables)
                #sys.stderr.write("nodeset=%s; newnodes=%s\n" % (str(""),str(newnodes)))
                if isinstance(newnodes,basestring):
                    # xpath already converted it to a string... append it directly... automatically satisfies oneper condition
                    nodeset.append(newnodes)
                    # provenance now handled by base xpath method
                    # if  hasattr(newnodes,"getparent"):
                    #     provenance.xmldocelementaccessed(self,newnodes.getparent())
                    #     pass
                    # else : 
                    #     provenance.warnnoprovenance("Unable to identify provenance of XPath result for %s on file %s" % (path,self._filename))
                    # 
                    #     pass
                        
                    
                    pass
                else :
                    if oneper and len(newnodes) != 1:
                        raise ValueError("%d nodes resulting from xpath query %s: Try unsetting oneper option if one-to-one mapping not needed" % (len(newnodes),path))
                    for node in newnodes: 
                        # register provenance
                        if isinstance(node,basestring) or isinstance(node,float):
                            if hasattr(node,"getparent"):
                                provenance.xmldocelementaccessed(self,node.getparent())
                                pass
                            else : 
                                provenance.warnnoprovenance("Unable to identify provenance of XPath result for %s on file %s" % (path,self._filename))
                            
                                pass
                            pass
                        else :
                            provenance.xmldocelementaccessed(self,node)
                            pass
                        pass
                    nodeset.extend(newnodes)
                    pass
                pass
            pass
        else :
            nodeset=self.xpath(path,namespaces=namespaces,contextnode=contextnodes,extensions=extensions)
            if isinstance(nodeset,basestring):
                # xpath already converted it to a string... convert to list... 
                nodeset=[nodeset]
                pass
            pass

        return nodeset

    def xpathnumpystr(self,path,namespaces=None,contextnodes=None,extensions=None,variables=None,oneper=True):
        """Like xpath, but convert node-set to unicode, return as 
        numpy array.

        contextnodes can be either a single context node, or a list, 
        in which case if oneper==True, there must be exactly one result
        per context node

        oneper:       If True, there must be exactly one result per 
                      context node (if contextnodes is a list)

"""


        nodeset=self.xpathtonodestrlist(path,namespaces=namespaces,contextnodes=contextnodes,extensions=extensions,variables=variables,oneper=oneper)

            
        resultarray=np.zeros(len(nodeset),dtype='O')
        
        cnt=0
        for node in nodeset:
            if isinstance(node,basestring):
                resultarray[cnt]=unicode(node)
                pass
            else :
                resultarray[cnt]=unicode(node.text)
                pass
            cnt+=1
            pass
        return resultarray
    

    def xpathcontextnumpystr(self,contextnodes,path,namespaces=None,extensions=None,variables=None,oneper=True):
        """Like xpathnumpy but must provide context nodes before path"""
        return self.xpathnumpystr(path,namespaces=namespaces,contextnodes=contextnodes,extensions=extensions,variables=variables,oneper=oneper)




    def xpathnumpyint(self,path,namespaces=None,contextnodes=None,extensions=None,variables=None,oneper=True):
        """Like xpath, but convert node-set to integers, return as 
        numpy array.

        Nodes must NOT be comverted to numbers using xpath but must be 
        given as nodes or (if necessary) as strings . 

        contextnodes can be either a single context node, or a list, 
        in which case if oneper==True, there must be exactly one result
        per context node

        oneper:       If True, there must be exactly one result per 
                      context node (if contextnodes is a list)

"""

        nodeset=self.xpathtonodestrlist(path,namespaces=namespaces,contextnodes=contextnodes,extensions=extensions,variables=variables,oneper=oneper)

            
        resultarray=np.zeros(len(nodeset),dtype=np.int64)
        
        cnt=0
        for node in nodeset:
            if isinstance(node,basestring):
                resultarray[cnt]=np.int64(node)
                pass
            else :
                resultarray[cnt]=np.int64(node.text)
                pass
            cnt+=1
            pass
        return resultarray


    def xpathcontextnumpyint(self,contextnodes,path,namespaces=None,extensions=None,variables=None,oneper=True):
        """Like xpathnumpyint, but with mandatory context before path"""
        return self.xpathnumpyint(path,namespaces=namespaces,contextnodes=contextnodes,extensions=extensions,variables=variables,oneper=oneper)


    def getroot(self):
        """Get the root node of the document"""
        root=self.doc.getroot()
        provenance.xmldocelementaccessed(self,root)

        return self.doc.getroot()

    def get_canonical_etxpath(self,element):
        """Find a canonical absolute (Clark notation) xpath representation based 
        off the filesystem root for the specified element within
        doc. The document must have a filename for this to work. 
        """
        assert(canonicalize_etxpath is not None) # if this fails, you need to install the canonicalize_path package!

        self.element_in_doc(element)

        return create_canonical_etxpath(self._filename,self.doc,element)
        
        
    
    def savepath(self,element):
        """Get a saveable path the specified element. Treat the 
           data structure as opaque as it may evolve: 
 
           NOTE: The returned xpath is currently NOT compatible 
           with find() and WILL be incorrect if nodes have been 
           added or removed upwards and prior in the tree. 

           If the canonicalize_path package is available, it
           will be used to provide a more consistent scheme for
           identifying deep content, which can often be correct
           even if nodes are added or removed prior in the tree. 
           
           The canonicalize_path package can be customized with
           /etc/canonicalize_path/tag_index_paths_local.conf or
           /usr/local/etc/canonicalize_path/tag_index_paths_local.conf
           depending on the installation prefix of canonicalize_path. 
"""
        
        # Note: VERY Recent versions (2014 and later?) of lxml have a new 
        # method getelementpath() that is slower, but constructs a more 
        # meaningful path suitable for find(). 
        self.element_in_doc(element)

        if canonicalize_etxpath is None:
            return self.doc.getpath(element)
        else :
            return getelementetxpath(self.doc,element)
        pass
    def restorepath(self,savedpath):
        """Restore a saved path (as returned from savepath) to an element. 
           Treat the data structure as opaque as it may evolve. 
        """
        if canonicalize_etxpath is None:
            return self.doc.xpath(savedpath)[0]
        else :
            ETXobj=etree.ETXPath(savedpath)

            foundelement=ETXobj(self.doc)
            if len(foundelement) != 1:
                raise ValueError("Non-unique result restoring saved path %s" % (savedpath))

            # Mark provenance reference
            provenance.xmldocelementaccessed(self,foundelement[0])
            return foundelement[0]
            
        pass
    def find(self,path,namespaces=None,contextnode=None):
        """ Find the element matching path in the tree, 
        optionally with respect to the specified context node or the document root. 
        
        find is always relative to the main tag node (default) or 
        supplied context node. Absolute finds not supported.

        path: An ElementPath (simplified XPath)
        namespaces: additional namespaces needed for interpreting path
        contextnode: optional context node"""

        self.element_in_doc(contextnode)

        if namespaces is not None:
            # merge namespaces dictionaries
            namespaces=dict(list(self.namespaces.items())+list(namespaces.items()))
            pass
        else : 
            namespaces=self.namespaces
            pass

        if contextnode is None:
            foundnode=self.doc.find(path,namespaces=namespaces)
        else :
            
            foundnode=contextnode.find(path,namespaces=namespaces)
            pass

        if isinstance(foundnode,basestring) or isinstance(foundnode,float):
            if  hasattr(foundnode,"getparent"):
                provenance.xmldocelementaccessed(self,foundnode.getparent())
                pass
            else :
                provenance.warnnoprovenance("Unable to identify provenance of XPath result for %s on file %s" % (path,self._filename))
                pass
            pass
        else : 
            provenance.xmldocelementaccessed(self,foundnode)

            pass


        return foundnode
    
    def findcontext(self,contextnode,path,namespaces=None):
        """alias for find(path,namespaces,contextnode"""
        return self.find(path,namespaces=namespaces,contextnode=contextnode)
        


    def elementdone(self,parent,element): 
        """no-op now that indentation is done with pretty_print
        """
        self.modified=True
        
        # Notify provenance engine that this element has been messed with
        
        provenance.elementgenerated(self,element)
        pass
    
    def addsimpleelement(self,parent,elname,valueunits): 
        """ Add a simple sub-element containing value and optional units

        parent:      may be a path or an element
        elname:      Name of element to create, optionally with namespace 
                     prefix. In addition if elname begins with '@', 
                     an attribute is added instead of an element
        valueunits:  (value,units) tuple. If units is provided, it will 
                     be an attribute with name dcv:units.

        """

        self.element_in_doc(parent)

        if parent is None:
            parent=self.doc.getroot()
            pass
        

        if isinstance(parent,basestring):
            parent=self.find(parent) # convert path to element
            pass

        if elname.startswith("@") : # an attribute, not an element
            assert(len(valueunits)==1 or (len(valueunits)==2 and valueunits[1] is None) or (len(valueunits)==2 and valueunits[1]=="")); # attributes cannot themselves have attributes. Thus attributes may not have units
            self.setattr(parent,elname[1:],unicode(valueunits[0]))
            provenance.elementgenerated(self,parent)
            newnode=None;
            pass
        else : 
            # regular element, not attribute
            
            # create element
            nspre_elname=elname.split(":")
        
            assert(len(nspre_elname) <= 2)
            
            if len(nspre_elname)==1:
                # no explicit prefix
                # create element
                newnode=etree.Element(elname,nsmap=self.nsmap);
                pass
            else : 
                # explicit prefix
                newnode=etree.Element("{%s}%s" % (self.nsmap[nspre_elname[0]],nspre_elname[1]),nsmap=self.nsmap)
                pass

            # add "units" attribute if present
            if len(valueunits) > 1 and valueunits[1] is not None:
                newnode.attrib["{http://limatix.org/dcvalue}units"]=valueunits[1]
                pass
            newnode.text=unicode(valueunits[0])
            parent.append(newnode);
            provenance.elementgenerated(self,newnode)
            
            pass
        self.modified=True;

        # if self.autoflush:
        #     self.flush()
        #     pass
        return newnode

    def child(self,context,tag,namespaces=None,noprovenanceupdate=False):
        """Find context child specified by tag. Return child or None
        (return value can be used as truth value)
        """
        
        self.element_in_doc(context)

        if namespaces is not None:
            usenamespaces=copy.copy(self.namespaces) # make our own copy
            usenamespaces.update(namespaces)  # manual parameter overrides
            pass
        else:
            usenamespaces=self.namespaces
            pass

        if ":" in tag: # colon in tag name means this is in a namespace
            # apply namespace from nsmap
            colonoffset=tag.find(':')
            namespaceuri=usenamespaces[tag[:colonoffset]]
            clarktag="{%s}%s" % (namespaceuri,tag[(colonoffset+1):])
            pass
        else : 
            clarktag=tag
            pass
        for child in context.iterchildren():
            if child.tag==clarktag:
                if not noprovenanceupdate:
                    provenance.xmldocelementaccessed(self,child)
                    pass
                return child
            pass
        return None


    def children(self,context,tag=None,namespaces=None,noprovenanceupdate=False,allow_comments=False):
        """Find context children specified by tag or all children. Return list
        """
        
        self.element_in_doc(context)

        if namespaces is not None:
            usenamespaces=copy.copy(self.namespaces) # make our own copy
            usenamespaces.update(namespaces)  # manual parameter overrides
            pass
        else:
            usenamespaces=self.namespaces
            pass

        if tag is not None:
            if ":" in tag: # colon in tag name means this is in a namespace
                # apply namespace from nsmap
                colonoffset=tag.find(':')
                namespaceuri=usenamespaces[tag[:colonoffset]]
                clarktag="{%s}%s" % (namespaceuri,tag[(colonoffset+1):])
                pass
            else : 
                clarktag=tag
                pass
            
            children=[]
            for child in context.iterchildren():
                if child.tag==clarktag:
                    if not noprovenanceupdate:
                        provenance.xmldocelementaccessed(self,child)
                        pass
                    children.append(child)
                    pass                
                pass
            pass
        else:
            # tag is none
            children=[]
            for child in context.iterchildren():
                if child.tag is etree.Comment and not allow_comments:
                    continue
                if not noprovenanceupdate:
                    provenance.xmldocelementaccessed(self,child)
                    pass
                children.append(child)
                pass
            pass
        
        return children
        
    def is_comment(self,element):
        """Determine whether an element is actually an XML comment"""
        return element.tag is etree.Comment
    
    def setattr(self,tag,attrname,value,namespaces=None) :
        """Set an attribute of an element to the specified value.
        Use namespace prefixes as usual. 

        tag:      The element itself, or path to it from the main tag, or 
                  None to reference attributes of the main tag
        attrname: Name of attribute to set
        value:    Value of the attribute
        """


        if isinstance(tag,basestring):
            tag=self.find(tag,namespaces=namespaces);
            pass
        if tag is None:
            tag=self.doc.getroot()
            pass

        self.element_in_doc(tag)

        if namespaces is not None:
            # merge namespaces dictionaries
            namespaces=dict(list(self.namespaces.items())+list(namespaces.items()))
            pass
        else : 
            namespaces=self.namespaces
            pass


        if ":" in attrname:  # colon in attrname means this is in a namespace
            # Apply namespace from nsmap
            colonoffset=attrname.find(':')
            namespaceuri=namespaces[attrname[:colonoffset]]
            tag.attrib["{%s}%s" % (namespaceuri,attrname[(colonoffset+1):])]=value
            pass
        else : 
            tag.attrib[attrname]=value
            pass
        
        self.modified=True;
        

        # if self.autoflush:
        #     self.flush()
        #     pass

        pass

    def remattr(self,tag,attrname,namespaces=None) :
        """Remove an attribute of an element.
        Use namespace prefixes as usual. 

        tag:      The element itself, or path to it from the main tag
        attrname: Name of attribute to remove
        """


        if isinstance(tag,basestring):
            tag=self.find(tag,namespaces=namespaces);
            pass
        self.element_in_doc(tag)

        if namespaces is not None:
            # merge namespaces dictionaries
            namespaces=dict(list(self.namespaces.items())+list(namespaces.items()))
            pass
        else : 
            namespaces=self.namespaces
            pass


        if ":" in attrname:  # colon in attrname means this is in a namespace
            # Apply namespace from nsmap
            colonoffset=attrname.find(':')
            namespaceuri=namespaces[attrname[:colonoffset]]
            ETattrname="{%s}%s" % (namespaceuri,attrname[(colonoffset+1):])
            if ETattrname in tag.attrib: 
                del tag.attrib[ETattrname]
                pass
            else: 
                raise ValueError("Attempt to remove nonexistent attribute %s from element" % (attrname))
                
            pass
        else : 
            if attrname in tag.attrib: 
                del tag.attrib[attrname]
                pass
            else: 
                raise ValueError("Attempt to remove nonexistent attribute %s from element" % (attrname))
            pass
        
        self.modified=True;
        

        # if self.autoflush:
        #     self.flush()
        #     pass

        pass



    def removeelement(self,element):
        # Remove the specified element.
        
        self.element_in_doc(element)

        provenance.element_to_be_removed(self,element)
        element.getparent().remove(element)
        pass

    def getattr(self,tag,attrname,default=IndexError("Attribute not found"),namespaces=None) :
        """Set the attribute of the specified element or path
        Use namespace prefixes as usual. 

        tag:      The element itself, or path to it from the main tag,
                  or None to get attributes of the main tag
        attrname: Name of attribute to get
        default: Default value of the attribute to return. If
                  this is not provided, IndexError
                  will be raised. 
        namespaces: Additional namespaces for attribute evaluation
        """

        if isinstance(tag,basestring):
            tag=self.find(tag);
            pass
        if tag is None:
            tag=self.doc.getroot()
            pass

        self.element_in_doc(tag)
        if ":" in attrname:  # colon in attrname means this is in a namespace
            # Apply namespace from nsmap
            colonoffset=attrname.find(':')
            namespaceuri=self.nsmap[attrname[:colonoffset]]
            
            fullattrname="{%s}%s" % (namespaceuri,attrname[(colonoffset+1):])
            pass
        else : 
            fullattrname=attrname
            pass
            
        if fullattrname in tag.attrib:
            return tag.attrib[fullattrname]
        elif isinstance(default,BaseException):
            raise default
        else:
            return default
        
        pass


    def hasattr(self,tag,attrname) :
        """Check if the attribute of the specified element or path
        exists. Use namespace prefixes as usual. 

        tag:      The element itself, or path to it from the main tag,
                  or None to reference the main tag
        attrname: Name of attribute to check the existance of 
        """

        if isinstance(tag,basestring):
            tag=self.find(tag);
            pass
        if tag is None:
            tag=self.doc.getroot()
            pass
        self.element_in_doc(tag)
        if ":" in attrname:  # colon in attrname means this is in a namespace
            # Apply namespace from nsmap
            colonoffset=attrname.find(':')
            namespaceuri=self.nsmap[attrname[:colonoffset]]
            return ("{%s}%s" % (namespaceuri,attrname[(colonoffset+1):])) in tag.attrib
        else : 
            return attrname in tag.attrib
            
        pass
        
    def _flush(self,rolock=False,rwlock=False,ok_to_be_unlocked=False) :
        """Flush file to disk, whether or not 
        any explicit changes have been made. 
        Creates backups according to num_backups

        If rwlock is set it creates a low level read/write lock, leaves 
        this lock set, and assigns self.lockfd. Does not adjust or pay attention 
        to lock counts
        """
        # print "Flush: self._filename=%s" % (self._filename)
        
        if self.debug:
            if self.debug_last_serialized is not None and not self.modified:
                debugdoc=self.doc
                if debugdoc is None:
                    debugdoc=self.olddoc
                    pass
                    
                if debugdoc is not None and etree.tostring(self.doc,encoding="utf-8") != self.debug_last_serialized:
                    raise ValueError("Document content has changed without modified flag being set")
                pass
            pass


        if self.filehref is not None:

            if self.readonly:
                raise IOError('xmldoc: attempt to flush in readonly mode')

            if self.use_locking and self.lockfd < 0 and self.filehref is not None and not(rolock) and not(rwlock) and not(ok_to_be_unlocked):
                sys.stderr.write("flush() when not locked!\n")
                traceback.print_stack()
                pass


            lockfd=-1
            lockfh=None
            if os.name=="posix" and rolock or rwlock :
                # This stuff is to support rename-based backups, which we don't do on non-POSIX platforms (NT)
                assert(self.lockfd < 0)
            
                #assert(os.name=="posix")
                try : 
                    lockfd=os.open(self._filename,os.O_RDONLY)
                    if rwlock: 
                        self._lock_rw(lockfd) # pass ownership of lockfd
                        pass
                    else : 
                        self._lock_ro(lockfd) # pass ownership of lockfd
                        pass
                    pass
                except OSError: 
                    # can not lock if file does not exist
                    pass
                pass
            

            # Check if we have something to write!
            if self.doc is None and ( not(ok_to_be_unlocked) or self.olddoc is None): 
                raise ValueError("No document available to write!")

                              
            # flush changes to disk
            
            (filenamepath,filenamefile)=os.path.split(self._filename)
            
            # save backup first
            if os.name=="posix":
                for baknum in range(self.num_backups,0,-1):
                    
                    bakname=os.path.join(filenamepath,"."+filenamefile+(".bak%d" % (baknum)))
                    nextbakname=os.path.join(filenamepath,"."+filenamefile+(".bak%d" % (baknum+1)))
                    
                    if baknum==self.num_backups and os.path.exists(bakname):
                        try : 
                            os.remove(bakname)
                            pass
                        except :
                            (exctype,value)=sys.exc_info()[:2]
                            sys.stderr.write("%s: %s removing old backup %s\n" % (unicode(exctype.__name__),unicode(value),bakname))
                            pass
                        pass
                    elif os.path.exists(bakname):
                        try: 
                            os.rename(bakname,nextbakname)
                            pass
                        except :
                            (exctype,value)=sys.exc_info()[:2]
                            sys.stderr.write("%s: %s renaming old backup %s to %s\n" % (unicode(exctype.__name__),unicode(value),bakname,nextbakname))
                            pass
                        pass
                    
                    pass
                

                bakname=os.path.join(filenamepath,"."+filenamefile+(".bak1"))
                if self.num_backups > 0 and os.path.exists(self._filename):
                    try :
                        shutil.copyfile(self._filename,bakname);
                        pass
                    except :
                        (exctype,value)=sys.exc_info()[:2]
                        sys.stderr.write("%s: %s renaming %s to %s to save as backup\n" % (unicode(exctype.__name__),unicode(value),self._filename,bakname))
                        pass
                    pass
                pass
            # put temporary SIGINT handler in place that 
            # ignores during critical writing code

            gotsigints=[0]  # Storage for counter of how many SIGINTS we got
            
            def sigintholdoff(signalnum,stackframe): # signal handler
                gotsigints[0]+=1
                pass
            
            oldsiginthandler=None
            try: 
                oldsiginthandler=signal.signal(signal.SIGINT,sigintholdoff)
                pass
            except ValueError: 
                sys.stderr.write("xmldoc _flush() cannot hold off SIGINT for critical output section (not running in main thread?)\n")
                pass

            if os.name=="nt" and self.lockfd >= 0:
                # reuse file handle
                OutFH=self.lockfh
                OutFH.seek(0)
                OutFH.truncate()
                pass
            else:
                OutFH=open(self._filename,"wb");
                pass
            
            if (rolock or rwlock) and lockfd < 0:
                # try again to lock
                if os.name=="posix":
                    lockfd=os.dup(OutFH.fileno())
                    pass
                else:
                    lockfd=OutFH.fileno()
                    pass
                
                if rwlock: 
                    self._lock_rw(lockfd,OutFH) # pass ownership of dup'd file descriptor
                    pass
                else:
                    # Shoudn't this be dependent on rolock parameter??
                    self._lock_ro(lockfd,OutFH) # pass ownership of dup'd file descriptor
                    pass
                pass
            if self.doc is None and ok_to_be_unlocked: 
                # if we are unlocked and we don't have a current document, use olddoc
                self.olddoc.write(OutFH,encoding='utf-8',pretty_print=True,xml_declaration=True)
                pass
            else : 
                self.doc.write(OutFH,encoding='utf-8',pretty_print=True,xml_declaration=True)
                pass
            if os.name=="posix": # Close non-lock copy
                OutFH.close();
                pass
            
            if self.lockfd >= 0:
                # if locked, save mtime, etc. 
                self.lastfileinfo=fileinfo(self.lockfd)
                pass
            else:
                self.lastfileinfo=None
                pass
            
            # put old SIGINT handler back in place
            if oldsiginthandler is not None:
                try:
                    signal.signal(signal.SIGINT,oldsiginthandler)
                    pass
                except ValueError:
                    pass
                
            if gotsigints[0] > 0: 
                raise KeyboardInterrupt("Deferred during xmldoc write")
            
            if self.debug:
                self.debug_last_serialized=etree.tostring(self.doc,encoding="utf-8")
                pass
            pass

        self.modified=False
        pass

    def __lock_ro(self):
        # super-low-level file locking
        if os.name=='nt':
            hfile=win32file._get_osfhandle(self.lockfd)
            flags=0
            win32file.LockFileEx(hfile, flags, 0, -0x10000, pwt__overlapped)
            pass
        else:
            fcntl.flock(self.lockfd,fcntl.LOCK_SH)
            pass
        pass

    def _lock_ro(self,fd,fh):
        # low-level non recursive file locking
        # NOTE: This takes ownership of fd and will close it on unlock
        assert(self.lockfd==-1)
        self.lockfd=fd
        self.lockfh=fh
        # !!!*** bug: Should handle receipt of signal
        # during flock() call...
        # fcntl.flock(self.lockfd,fcntl.LOCK_SH)
        self.__lock_ro()
        pass
        
    def _lock_convert_rw_to_ro(self):
        # !!!*** WARNING ***!!!! non-atomic !!!***
        assert(self.lockfd > 0)
        #fcntl.flock(self.lockfd,fcntl.LOCK_UN)
        self.__unlock()
        # Somebody else could modifiy the file right now!!!
        # (according to man page we don't actually need to unlock it first
        #  .... should probably fix this)

        # !!!*** bug: Should handle receipt of signal
        # during flock() call...
        #fcntl.flock(self.lockfd,fcntl.LOCK_SH)
        self.__lock_ro()
        pass
        

    def __unlock(self):
        # super-low-level file locking
        if os.name=='nt':
            hfile=win32file._get_osfhandle(self.lockfd)
            win32file.UnlockFileEx(hfile,  0, -0x10000, pwt__overlapped)
            pass
        else:
            fcntl.flock(self.lockfd,fcntl.LOCK_UN)
            pass
        pass
    
    def _unlock_ro(self):
        # low-level non recursive file locking
        assert(self.lockfd > 0)
        self.__unlock()
        #fcntl.flock(self.lockfd,fcntl.LOCK_UN)  # See also exception handler in resync() for another unlock call
        if os.name=="posix":
            os.close(self.lockfd)
            pass
        elif os.name=="nt":
            self.lockfh.close()
            pass
        self.lockfh=None
        self.lockfd=-1
        pass


    def __lock_rw(self):
        # super-low-level file locking
        if os.name=='nt':
            hfile=win32file._get_osfhandle(self.lockfd)
            flags=win32con.LOCKFILE_EXCLUSIVE_LOCK
            win32file.LockFileEx(hfile, flags, 0, -0x10000, pwt__overlapped)
            pass
        else:
            fcntl.flock(self.lockfd,fcntl.LOCK_EX)
            pass
        pass
    
    def _lock_rw(self,fd,fh):
        # low-level non recursive file locking
        # NOTE: This takes ownership of fd and will close it on unlock
        assert(self.lockfd==-1)
        self.lockfd=fd
        self.lockfh=fh
        # !!!*** bug: Should handle receipt of signal
        # during flock() call
        #fcntl.flock(self.lockfd,fcntl.LOCK_EX)
        self.__lock_rw()
        pass

    # no distinction between __unlock_ro() and __unlock_rw()
    # so we just define __unlock()
    #def __unlock_rw(self):
    #    # super-low-level file locking
    #    if os.name=='nt':
    #        hfile=win32file._get_osfhandle(self.lockfd)
    #        win32file.UnlockFileEx(hfile,  0, -0x10000, pwt__overlapped)
    #        pass
    #    else:
    #        fcntl.flock(self.lockfd,fcntl.LOCK_UN)  # See also exception handler in resync() for another unlock call
    #        pass
    #    pass

    def _unlock_rw(self):
        # low-level non recursive file locking
        assert(self.lockfd > 0)
        #fcntl.flock(self.lockfd,fcntl.LOCK_UN)  # See also exception handler in resync() for another unlock call
        self.__unlock()
        if os.name=="posix":
            os.close(self.lockfd)
            pass
        elif os.name=="nt":
            self.lockfh.close()
            pass
        self.lockfh=None
        self.lockfd=-1
        pass


    def lock_ro(self):
        """Lock the file for read only access. File locking is counted, 
        so lock calls may be nested"""
        if not self.use_locking:
            return

        assert(self.rw_lockcount > 0 or not self.modified)

        if self.ro_lockcount > 0 or self.rw_lockcount > 0:
            self.ro_lockcount+=1
            pass
        else : 
            self._resync(rolock=True)
            self.ro_lockcount+=1
            pass

        pass
    
    def unlock_ro(self):
        """Unlock the file from read-only-access"""
        if not self.use_locking:
            return

        assert(self.ro_lockcount > 0)
        assert(self.rw_lockcount > 0 or not self.modified)
        
        self.ro_lockcount-=1
        if self.ro_lockcount==0 and self.rw_lockcount==0:
            if self.filehref is not None:
                self._unlock_ro()
                self._free_doc()
                pass
                
            pass
        pass

    def is_locked(self):
        """Return whether the document is locked for access"""
        assert(self.use_locking)

        if self.rw_lockcount > 0:
            return True
        if self.ro_lockcount > 0: 
            return True
        return False



    def lock_rw(self):
        """Lock the file for read-write access. File locking is counted, 
        so lock calls may be nested"""
        
        if not self.use_locking:
            return

        if self.readonly:
            raise ValueError("Cannot add read/write lock on read only file")
        
        if self.rw_lockcount > 0:
            self.rw_lockcount+=1
            pass
        else : 
            assert(self.ro_lockcount==0) # cannot add rw lock if already have ro lock 
            assert(not self.modified)
            self._resync(rwlock=True)
            self.rw_lockcount+=1
            pass

        pass

    def unlock_rw(self):
        """Unlock the file from read-write access"""
        if not self.use_locking:
            return

        assert(self.rw_lockcount > 0)

        
        self.rw_lockcount-=1
        if self.rw_lockcount==0:
            assert(self.ro_lockcount==0)
            if self.modified:
                try: 
                    self._flush(ok_to_be_unlocked=True)
                    pass
                except:
                    raise
                finally:
                    self.modified=False # clear modified, even if there was an error writing it out (presumably diagnosed by our caller) so we don't get a second exception on the next lock attempt
                    pass
                pass
            if self.filehref is not None:
                self._unlock_rw()
                self._free_doc()
                pass
            
            pass
        pass
    
    def _free_doc(self):
        # if we're fully unlocked, we don't need the self.doc object anymore, 
        # except for recovery if the file on disk gets corrupted. 

        assert(self.use_locking)
    
        assert(self.doc is not None)

        self.olddoc=self.doc
        self.doc=None

        pass



    def shouldbeunlocked(self):
        """Assert that the document should be unlocked"""
        if not self.use_locking:
            return

        diagnosed=False
        if self.ro_lockcount > 0:
            sys.stderr.write("Shouldbeunlocked() failed with ro_lockcount=%d! Traceback follows.\nUnless this was the result of a prior exception, this needs to be debugged!\n" % (self.ro_lockcount))
            traceback.print_stack()
            diagnosed=True
            pass

        self.ro_lockcount=0

        if self.rw_lockcount > 0:
            sys.stderr.write("Shouldbeunlocked() failed with rw_lockcount=%d! Traceback follows.\nUnless this was the result of a prior exception, this needs to be debugged!\n" % (self.rw_lockcount))
            traceback.print_stack()
            diagnosed=True
            pass
        
        self.rw_lockcount=0

        if diagnosed and self.modified:
            self._flush(ok_to_be_unlocked=True)
            
            pass

        if self.lockfd >= 0:
            if not diagnosed: 
                sys.stderr.write("Shouldbeunlocked() failed with lockfd set! Traceback follows.\nUnless this was the result of a prior exception, this needs to be debugged!\n" )
                traceback.print_stack()
                pass

            # fcntl.flock(self.lockfd,fcntl.LOCK_UN)  # See also exception handler in resync() for another unlock call
            self.__unlock()

            if os.name=="posix":
                os.close(self.lockfd)
                pass
            self.lockfd=-1
            
            pass

        if self.doc is not None:
            self._free_doc()  # don't need a current document when we're unlocked
            pass
        pass

    def should_be_rwlocked_once(self):
        """Assert that the document should be read-write locked exactly once"""

        if not self.use_locking:
            return
        
        if self.ro_lockcount > 0:
            sys.stderr.write("xmldoc.should_be_rwlocked_once: Got nonzero ro_lockcount of %d\n" % (self.ro_lockcount))
            traceback.print_stack()

            if self.rw_lockcount==0 and self.lockfd >= 0:
                # May have genuine readonly lock... this must be unlocked!
                self.ro_lockcount=1
                self.unlock_ro()
                assert(self.ro_lockcount==0)
                pass
            else : 
                self.ro_lockcount=0
                pass
            pass
        # ro_lockcount is now 0
        if self.rw_lockcount==0:
            sys.stderr.write("xmldoc.should_be_rwlocked_once: Got zero rw_lockcount\n")
            traceback.print_stack()
            if self.lockfd >= 0:
                # mysterious lock... unlock it
                #fcntl.flock(self.lockfd,fcntl.LOCK_UN)  # See also exception handler in resync() for another unlock call
                self.__unlock()
                if os.name=="posix":
                    os.close(self.lockfd)
                    pass
                self.lockfd=-1
                pass
            # rw_lockcount is zero... need to relock file
            self.lock_rw()
            pass
        if self.rw_lockcount > 1:
            sys.stderr.write("xmldoc.should_be_rwlocked_once: Got rw_lockcount > 1: %d\n" % (self.rw_lockcount))
            traceback.print_stack()
            # set lockcount to correct value of 1
            self.rw_lockcount=1
            pass
        
        # now ro_lockcount == 0, rw_lockcount == 1.
        # check value of lockfd
        if self.filehref is not None:
            if self.lockfd < 0:
                sys.stderr.write("xmldoc.should_be_rwlocked_once: Got invalid lockfd with valid filename\n")
                traceback.print_stack()
                assert(os.name=="posix") # can't recover on Windows
                lockfd=os.open(self._filename,os.O_RDONLY)
                self._lock_rw(lockfd) # pass ownership of lockfd
                pass
            pass
        else: # self.filename is None
            if self.lockfd >= 0:
                sys.stderr.write("xmldoc.should_be_rwlocked_once: Got valid lockfd with invalid filename\n")
                traceback.print_stack()
                self._unlock_rw() # clear underlying lock
                pass
            pass
        pass
    def disable_locking(self):
        # take xmldoc out of locking mode 
        # for the time being this is irreversable. 
        # Document should be locked exactly once

        if not self.use_locking:
            return

        assert((self.rw_lockcount==1 and self.ro_lockcount==0) or
               (self.rw_lockcount==0 and self.ro_lockcount==1))

        self.rw_lockcount=0
        self.ro_lockcount=0

        if self.lockfd >= 0:
            self._unlock_rw() # clear underlying lock
            pass
        
        self.use_locking=False
        pass


    def element_in_doc(self,element):
        # element may be a single element or smart string  or a list of elements/smart strings,
        # This is an assertion that the specified element is in our document


        # if self.debug and element is not None:
        if element is not None:
            # sys.stderr.write("element=%s\n" % (str(element)))
            if isinstance(element,basestring):
                return
                
            if not(isinstance(element,collections.Sequence)):
                element=[element] # wrap in a list so we can iterate
                pass
            
            # element should now be a list

            assert(self.doc is not None)
            root=self.doc.getroot()
            
            for singleelement in element:
                if isinstance(singleelement,basestring):
                    continue

                while singleelement is not root: 
                    singleelement=singleelement.getparent()
                    assert(singleelement is not None) # if this fails, element was not in the document!
                    pass
                pass
            pass
        pass

    def tag_is(self,element,tagname,namespaces=None):
        """ Return true if element tag matches tagname"""
        self.element_in_doc(element)
        if element is None:
            element=self.getroot()
            pass

        if namespaces is not None:
            usenamespaces=copy.copy(self.namespaces) # make our own copy
            usenamespaces.update(namespaces)  # manual parameter overrides
            pass
        else:
            usenamespaces=self.namespaces
            pass


        if ":" in tagname: # colon in tag name means this is in a namespace
            # apply namespace from nsmap
            colonoffset=tagname.find(':')
            namespaceuri=usenamespaces[tagname[:colonoffset]]
            clarktag="{%s}%s" % (namespaceuri,tagname[(colonoffset+1):])
            pass
        else : 
            clarktag=tagname
            pass
    
        return clarktag==element.tag

    def tostring(self,element=None,pretty_print=False):
        # Convert to unicode string... see also tobytes()

        self.element_in_doc(element)

        # Serialize entire document or tree within one element to a string
        if element is None:
            return etree.tostring(self.doc,encoding='utf-8',pretty_print=pretty_print).decode("utf-8")
        else : 
            # !!! Should we mark the provenance of the entire tree under this? 
            provenance.xmldocelementaccessed(self,element)
            return etree.tostring(element,encoding='utf-8',pretty_print=pretty_print).decode("utf-8")

        pass


    def tostring_human(self,element,noprovenance=False):
        # Create a human readable string representation,
        # of element without all of the pesky xmlns namepace
        # declarations

        if not noprovenance:
            provenance.xmldocelementaccessed(self,element)
            pass
        
        elementcopy=copy.deepcopy(element)
        
        # Define a junk parent tag to wrap the copy
        # and take the xmlns declarations of the overall document
        newparent=etree.Element("j",nsmap=self.getroot().nsmap)
        newparent.append(elementcopy)

        fullresponse=etree.tostring(newparent,encoding='utf-8',pretty_print=True,xml_declaration=False).decode("utf-8")

        # strip out <j></j> tags
        response=fullresponse.split('>',1)[1].rsplit('<',1)[0].strip()
        return response

    
    def tobytes(self,element=None,encoding='utf-8',pretty_print=False):
        # Convert to utf-8 bytes
        # can specify encoding=None to generate ascii (and use entities
        # for higher characters)

        self.element_in_doc(element)

        # Serialize entire document or tree within one element to a string
        if element is None:
            return etree.tostring(self.doc,encoding=encoding,pretty_print=pretty_print)
        else : 
            # !!! Should we mark the provenance of the entire tree under this? 
            provenance.xmldocelementaccessed(self,element)
            return etree.tostring(element,encoding=encoding,pretty_print=pretty_print)

        pass

    def getparent(self,element):
        """Get the parent of a particular element"""
        parent=element.getparent()
        provenance.xmldocelementaccessed(self,element)
        return parent
    
    
    def close(self):
        """Close and empty this document. Flush to disk first if modified"""
        if self.modified:
            self._flush()
            pass

        self.doc=None
        self.filehref=None
        self._filename=None
        self.nsmap=None
        self.namespaces=None
        self.modified=False
        self.resyncnotify=None
        # self.autoflush=False
        
        pass

    pass


# synced is not yet as documented as it should be. It is used to 
# keep paramdb2 entries synchronized with specific elements of XML files. 

# Please note that this is for READ/WRITE/EXTERNALLY UPDATED access to 
# XML files. If all you need is read-only access, see xmlcontroller in paramdb2.py
    
class synced(object):
    # This class represents a paramdb2 entry that is sync'd with an element within one or more xmldoc's
    # it functions as a controller for paramdb2
    doclist=None  # A list; elements are (xmldoc,xmlpath,ETxmlpath,logfunc)  
                  # where xmldoc is the class xmldoc, once fully set up
                  # xmlpath is The path of the element within xmldoc


    mergekwargs=None
    
    # controller members
    controlparam=None
    id=None
    state=None  # see CONTROLLER_STATE defines in definition of param class
    numpending=None
    in_synchronize=None  # are we in a synchronize right now


    def __init__(self,controlparam,**kwargs):
        self.controlparam=controlparam
        self.id=id(self)
        self.state=controlparam.CONTROLLER_STATE_QUIESCENT
        self.numpending=0
        self.doclist=[]
        self.mergekwargs=kwargs
        self.in_synchronize=False

        loadgobject() # gobject needed for requestval
        

        pass

    def find_a_context_href(self,paramset=None):
        # find a suitable context href for xml synchronization
        # paramset is a (xmldocu,xmlpath,ETxmlpath,logfunc) tuple

        doclist=copy.copy(self.doclist)
        if paramset is not None:
            doclist.append(paramset)
            pass
        # First look for anything with a filename set
        for (xmldocu,xmlpath,ETxmlpath,logfunc) in doclist:
            if xmldocu is not None and xmldocu.filehref is not None:
                #sys.stderr.write("find_a_context_href(): %s\n" % (xmldocu.getcontexthref().absurl()))
                return xmldocu.getcontexthref()
            pass

        # Now look for anything 
        for (xmldocu,xmlpath,ETxmlpath,logfunc) in doclist:
            if xmldocu is not None and xmldocu.contexthref is not None:
                #sys.stderr.write("find_a_context_href(): %s\n" % (xmldocu.getcontexthref().absurl()))
                return xmldocu.getcontexthref()
            pass
        
        # import pdb as pythondb
        # pythondb.set_trace()

        # worst-case fallthrough
        sys.stderr.write("xmldoc.find_a_context_href(): Falling through to \"./\"\n")
        return dc_value.hrefvalue("./") # current directory!
        
    
    # adddoc: Add a document that will have a synchronized element. 
    # xmlpath is the xpath to the element (which should already exist)
    # logfunc is a function or method that will be called to 
    # log changes. It takes the log message as a mandatory parameter, 
    # then "item", "action", and "value" as optional parameters
    # if xmlpath is None then ETxmlpath can be an ETXPath to locate the
    # element instead.
    # autocreate_parentxpath if not None indicates that we should autocreate a blank element, and gives the xpath of the parent element
    # autocreate_tagname gives the tag to create if necessary, and autocreate_insertpos gives where to insert the new element
    #  (autocreate_insertpos=-1 means add to then end, otherwise gives position in the element)
    def adddoc(self,xmldocobj,xmlpath,ETxmlpath=None,logfunc=None,autocreate_parentxpath=None,autocreate_tagname=None,autocreate_insertpos=-1):

        try : 
            retry=True
            while retry:
                retry=False

                #if xmlpath=="dc:summary/dc:expnotes":
                #    import pdb as pythondb
                #    pythondb.set_trace()
                    
                xmldocobj.lock_rw()
                try :
                    if autocreate_parentxpath is not None:
                        if ETxmlpath is not None:
                            ETXobj=etree.ETXPath(ETxmlpath)
                            xmlellist=ETXobj(xmldocobj.doc)
                            pass
                        else: 
                            xmlellist=xmldocobj.xpath(xmlpath)
                            pass
                        if len(xmlellist)==0:
                            # need to autocreate
                            autocreate_parentlist=xmldocobj.xpath(autocreate_parentxpath)
                            if len(autocreate_parentlist) < 1:
                                raise ValueError("Could not find parent path %s to autocreate element" % (autocreate_parentxpath))
                            xmldocobj.insertelement(autocreate_parentlist[0],autocreate_insertpos,autocreate_tagname)
                            pass
                        pass
                        
                    # sys.stderr.write("%s %s: %s\n" % (xmldocobj._filename,self.controlparam.xmlname,str(self.controlparam.dcvalue)))
                    self.xmlresync(xmldocobj,xmlpath,ETxmlpath,logfunc=logfunc,initialload=True)
                    pass
                except:
                    (exctype,value)=sys.exc_info()[:2]
                    tback=traceback.format_exc()
                    result=xmldocobj.postexcdialog(exctype,value,tback,initialload=True,cantretry=False)
                    if result=="retry":
                        retry=True
                        continue
                    else : 
                        raise
                    pass
                
                finally: 
                    xmldocobj.unlock_rw()
                    pass
                pass
            
            self.doclist.append((xmldocobj,xmlpath,ETxmlpath,logfunc))
            xmldocobj.addresyncnotify(self.xmlresync,xmlpath,ETxmlpath,logfunc=logfunc)
            pass

        except:
            # some kind of exception. Do precautionary remdoc and then raise
            self.remdoc(xmldocobj,xmlpath,ETxmlpath,logfunc,precautionary=True)
            raise
        return (xmldocobj,xmlpath,ETxmlpath,logfunc)

    def remdoc(self,xmldocobj,xmlpath,ETxmlpath=None,logfunc=None,precautionary=False):
        entry=None
        for doc in self.doclist:
            if doc[0] is xmldocobj and doc[1]==xmlpath and doc[2]==ETxmlpath and doc[3]==logfunc:
                entry=doc
                break
            pass
        if entry is None and not precautionary:
            raise ValueError("synced: Attempt to remove unknown document and path %s and %s" % (str(xmldocobj),str(xmlpath)))
        
        if entry is not None: 
            self.doclist.remove(entry)
            xmldocobj.remresyncnotify(self.xmlresync,precautionary,entry[1],entry[2],logfunc=logfunc)
            pass
        
        
        pass

    #def valueobjfromxml(self,xmldocobj,xmlel):
    #    # this is a separate method so it can be overridden by derived 
    #    # class for implementing expanding date class
    #    return self.controlparam.paramtype.fromxml(xmldocobj,xmlel,self.controlparam.defunits)

    #def createvalueobj(self,newvalue):
    #    # this is a separate method so it can be overridden by derived 
    #    # class for implementing expanding date class
    #    return self.controlparam.paramtype(newvalue,defunits=self.controlparam.defunits)

    #def isconsistent(self,newval,oldval):
    #    # this is a separate method so it can be overridden by derived 
    #    # class for implementing expanding date class
    #    return newval == self.controlparam.dcvalue

    def manualmergedialog(self,humanpath,paramtype,parent,parentsource,descendentlist,descendentsourcelist,contexthref,kwargs):
        # Something else must have made sure gtk is loaded!
        
        dialog=gtk.Dialog(title="Manual merge: %s" % (humanpath),buttons=("Cancel and raise error",0,
                                                        "Apply",1))
        box=dialog.get_content_area()

        ScrolledWindow=gtk.ScrolledWindow()
        if "gi" in sys.modules:  # gtk3
            ScrolledWindow.set_policy(gtk.PolicyType.NEVER,gtk.PolicyType.ALWAYS)
            pass
        else:
            ScrolledWindow.set_policy(gtk.POLICY_NEVER,gtk.POLICY_ALWAYS)
            pass
        
        box.pack_start(ScrolledWindow,True,True,0)
        #Viewport=gtk.Viewport()
        #ScrolledWindow.add(Viewport)
        VBox=gtk.VBox()
        #Viewport.add(VBox)
        ScrolledWindow.add_with_viewport(VBox)
        #box.add(VBox)
        
        #import pdb as pythondb
        #pythondb.set_trace()

        if parent is not None:
            ParentFrame=gtk.Frame()
            ParentFrame.set_label("Parent: from %s" % (str(parentsource)))
            ParentTextView=gtk.TextView()
            ParentTextBuffer=gtk.TextBuffer()
            parentdoc=xmldoc.fromstring("<parent/>",contexthref=contexthref)
            parent.xmlrepr(parentdoc,parentdoc.getroot())
            ParentTextBuffer.set_text(parentdoc.tostring(pretty_print=True))
            ParentTextView.set_buffer(ParentTextBuffer)
            if "gi" in sys.modules:  # gtk3
                ParentTextView.set_wrap_mode(gtk.WrapMode.WORD_CHAR)
                pass
            else:
                ParentTextView.set_wrap_mode(gtk.WRAP_WORD_CHAR)
                pass
            ParentTextView.set_property('editable',False)
            ParentFrame.add(ParentTextView)
            VBox.add(ParentFrame)
            pass
        
        for deccnt in range(len(descendentlist)):
            descendent=descendentlist[deccnt]
            desc_src=descendentsourcelist[deccnt]
            
            DescendentFrame=gtk.Frame()
            DescendentFrame.set_label("Descendent %d: from %s" % (deccnt+1,str(desc_src)))
            DescendentTextView=gtk.TextView()
            DescendentTextBuffer=gtk.TextBuffer()
            descendentdoc=xmldoc.fromstring("<descendent/>",contexthref=contexthref)
            descendent.xmlrepr(descendentdoc,descendentdoc.getroot())
            DescendentTextBuffer.set_text(descendentdoc.tostring(pretty_print=True))
            DescendentTextView.set_buffer(DescendentTextBuffer)
            if "gi" in sys.modules:  # gtk3
                DescendentTextView.set_wrap_mode(gtk.WrapMode.WORD_CHAR)
                pass
            else:
                DescendentTextView.set_wrap_mode(gtk.WRAP_WORD_CHAR)
                pass
            DescendentTextView.set_property('editable',False)
            DescendentFrame.add(DescendentTextView)
            VBox.add(DescendentFrame)
            pass
        MergedFrame=gtk.Frame()
        MergedFrame.set_label("Merged")
        
        MergedTextView=gtk.TextView()
        MergedTextBuffer=gtk.TextBuffer()
        MergedTextBuffer.set_text("")
        MergedTextView.set_buffer(MergedTextBuffer)
        if "gi" in sys.modules:  # gtk3
            MergedTextView.set_wrap_mode(gtk.WrapMode.WORD_CHAR)
            pass
        else:
            MergedTextView.set_wrap_mode(gtk.WRAP_WORD_CHAR)
            pass
        MergedFrame.add(MergedTextView)
        VBox.add(MergedFrame)

        box.show_all()
        ScrolledWindow.show_all()
        #Viewport.show_all()
        VBox.show_all()
        dialog.show_all()

        dialogval=dialog.run()

        if dialogval==1:
            mergeddoc=xmldoc.fromstring(MergedTextBuffer.get_text(MergedTextBuffer.get_start_iter(),MergedTextBuffer.get_end_iter(),False),contexthref=contexthref)
            # ***!!!! Bug: If we have to merge an XMLTreevalue,
            # the resulting tree's root is a <parent> or <descendent>
            # tag, not what it should be, and therefore
            # mergedvalue ends up wrong!
            #
            # Workaround: User manually puts in correct tag from window title
            # Suggested fix: Use correct tag in parent and descendents
            mergedvalue=paramtype.fromxml(mergeddoc,mergeddoc.getroot())
            
            dialog.destroy()
            return mergedvalue
        dialog.destroy()
        return None


    def domerge(self,humanpath,parent,parentsource,descendentlist,descendentsourcelist,contexthref=None,manualmerge=True,**kwargs):
        # this is a separate method so it can be overridden by derived 
        # class for implementing expanding date class
        #print self.controlparam.paramtype
        #print parent
        #import pdb
        #try : 
        #    sys.stderr.write("%s\n" % (type(parent)))
        #    if parent is not None and "xmltreevalue" in str(type(parent)):
        #        sys.stderr.write("parent=%s\n\n\ndescendentlist[0]=%s\n\n\ndescendentlist[1]=%s\n\n\n" % (etree.tostring(parent._xmltreevalue__xmldoc.doc,pretty_print=True),etree.tostring(descendentlist[0]._xmltreevalue__xmldoc.doc,pretty_print=True),etree.tostring(descendentlist[1]._xmltreevalue__xmldoc.doc,pretty_print=True)))
        #        pass
        #import pdb as pythondb
        #try:

        # if self.controlparam.paramtype is dc_value.hrefvalue:
        #     sys.stderr.write("domerge: contexthref=%s\n" % (contexthref.absurl()))
        #     pass

        try : 
            result=self.controlparam.paramtype.merge(parent,descendentlist,contexthref=contexthref,**kwargs)
            pass
        except:
            (exctype,value)=sys.exc_info()[:2]
            if manualmerge:   ###***!!!
                if not "gtk" in sys.modules and not ("gi" in sys.modules and hasattr(sys.modules["gi"],"repository") and hasattr(sys.modules["gi"].repository,"Gtk")):
                    # if nothing else has loaded gtk2 or gtk3
                    # Just raise it
                    raise
                else:
                    loadgtk()
                    result=self.manualmergedialog(humanpath,self.controlparam.paramtype,parent,parentsource,descendentlist,descendentsourcelist,contexthref,kwargs)

                    if result is None:
                        raise
                    
                    pass
                pass
            else:
                raise
            
            pass
        #except:
        #    pythondb.set_trace()
        #    if parent is not None and "xmltreevalue" in str(type(parent)) and "fubar" in etree.tostring(result._xmltreevalue__xmldoc.doc):
        #        sys.stderr.write("\nFOUNDIT\n")
        return result
        #except: 
        #    pdb.post_mortem()
        #    pass
        #pass


    def _get_dcvalue_from_file(self,xmldocobj,xmlpath,ETxmlpath):
        # xmldocobj must be locked during this process
        
        #sys.stderr.write("get_dcvalue_from_file: filename=%s xmlpath=%s ETxmlpath=%s\n" % (xmldocobj.filename,xmlpath,ETxmlpath))

        if xmlpath is not None:
            xmlellist=xmldocobj.doc.xpath(xmlpath,namespaces=xmldocobj.namespaces,extensions=xmldocobj.extensions)

            if len(xmlellist) > 1:
                raise NameError("XPath query %s returned %d elements" % (xmlpath,len(xmlellist)))
        
            if len(xmlellist)==0:
                # No element -- append one to the parent
            
                (parent,separator,elname)=xmlpath.rpartition("/")
                xmlel=xmldocobj.addelement(parent,elname)
                pass
            else :
                xmlel=xmlellist[0]
                pass
                
            pass
        else: 
            # ETxpath provided, not regular xpath
            ETXobj=etree.ETXPath(ETxmlpath)
            xmlellist=ETXobj(xmldocobj.doc)


            # sys.stderr.write("parent=%s\n" % (parent))

            if len(xmlellist) > 1:
                raise NameError("ETXPath query %s returned %d elements" % (ETxmlpath,len(xmlellist)))
        
            if len(xmlellist)==0:
                # No element -- append one to the parent
            
                splitpath=canonical_etxpath_split(ETxmlpath)

                # parent comes from splitting of the last portion of the ETXpath
                if etxpath_isabs(ETxmlpath):
                    parent=canonical_etxpath_absjoin(*splitpath[:-1])
                    pass
                else:
                    parent=canonical_etxpath_join(*splitpath[:-1])
                    pass


                ParentETXobj=etree.ETXPath(parent)
                ParentElements=ParentETXobj(xmldocobj.doc)
                if len(ParentElements) != 1:
                    raise NameError("ETXPath parent query %s returned %d elements" % (parent,len(ParentElements)))
                    

                elname=splitpath[-1]
                
                if '[' in elname:  # if there was a constraint in the last portion of the etxpath...
                    elname=elname[:elname.index('[')] # cut it off.
                    pass
                

                ChildElement=etree.Element(elname,nsmap=ParentElements[0].nsmap)
                ParentElements[0].append(ChildElement)
                xmlel=ChildElement
                xmldocobj.modified=True
                
                pass
            else :
                xmlel=xmlellist[0]
                pass
                
            
            pass

        

        # newvalue=xmlel.text  # raw new value
        # newval=None  # new value as calculated from dc_value class

        #newval=self.controlparam.paramtype.fromxml(xmldocobj,xmlel,self.controlparam.defunits,xml_attribute=self.controlparam.xml_attribute,contextdir=".")
        newval=self.controlparam.paramtype.fromxml(xmldocobj,xmlel,self.controlparam.defunits)
        #newval=self.valueobjfromxml(xmldocobj,xmlel)
        
        return newval

    # xmlresync loads in new data that has already been read in from the xml file
    def xmlresync(self,xmldocobj,xmlpath,ETxmlpath,logfunc=None,initialload=False):
        # NOTE: xmldocobj MUST be locked (or must be in the process of being locked)!!!

        #if xmlpath=="dc:summary/dc:dest":
        #    import pdb as pythondb
        #    pythondb.set_trace()
        #    pass

        #sys.stderr.write("xmlresync: %s doc=%s xp=%s etxp=%s in_synchronize=%s\n" % (xmldocobj.filename,str(xmldocobj.doc),xmlpath,ETxmlpath,str(self.in_synchronize)))
        # make sure xmldocobj is in our list
        # print "this document: ", xmldocobj,xmlpath,logfunc
        # print self.doclist
        if not initialload: 
            assert(any([doc[0] is xmldocobj and doc[1]==xmlpath and doc[2]==ETxmlpath and doc[3]==logfunc for doc in self.doclist]))
            pass

        if self.in_synchronize: 
            # synchronize() handles things in this case
            return

        # it is actually _get_dcvalue_from_file that guarantees that
        # referenced nodes actually exist in the file...
        # if xmlpath=="dc:summary/dc:dest":
        #    import pdb as pythondb
        #    pythondb.set_trace()
        #    pass
        newval=self._get_dcvalue_from_file(xmldocobj,xmlpath,ETxmlpath)
 
        
        # print xmldocobj.extensions
        # print xmlpath

        # if "units" in xmlel.attrib:
        #     units=xmlel.attrib["{http://limatix.org/dcvalue}units"]
        #     
        #     if self.controlparam.defunits is not None:
        #         newval=self.controlparam.paramtype(newvalue,units=units,defunits=self.controlparam.defunits)          
        #         pass
        #     else : 
        #         # print type(self.controlparam.paramtype)
        #         newval=self.controlparam.paramtype(newvalue,units=units)
        #         pass
        #     pass
        # 
        # else :
        #     if self.controlparam.defunits is not None:
        #         newval=self.controlparam.paramtype(newvalue,defunits=self.controlparam.defunits)
        #         pass
        #     else : 
        #         # print type(self.controlparam.paramtype)
        #         newval=self.controlparam.paramtype(newvalue)
        #         pass
        #     pass
        


        if newval != self.controlparam.dcvalue:
            if initialload:
                self.synchronizeinitialload(initialloadvalue=newval,initialloadparams=(xmldocobj,xmlpath,ETxmlpath,logfunc))
                pass
            else: 
                self.synchronize()
                pass
            pass
        pass
    
    def synchronizeinitialload(self,initialloadvalue,initialloadparams):
        # if we are performing the initial synchronization of an existing file use the no-parent merge semantics (any non-blank)
        #sys.stderr.write("no-parent merge for %s: %s and %s\n" % (self.controlparam.xmlname,str(newval),str(self.controlparam.dcvalue)))
            

        (xmldocobj,xmlpath,ETxmlpath,logfunc)=initialloadparams
        
        #import pdb as pythondb
        #if self.controlparam.xmlname=="specimen" and len(str(newval))==0 and len(str(self.controlparam.dcvalue))==0:
        #    pythondb.set_trace()
                #    pass

        # for synced accumulating date support: 
        #initialloadvalue=self.createvalueobj(initialloadvalue)
        contexthref=self.find_a_context_href(initialloadparams)

        humanpath=xmlpath
        if xmlpath is None:
            humanpath=etxpath2human(ETxmlpath,xmldocobj.nsmap)
            pass
        
        try: 
            # sys.stderr.write("initialloadvalue=%s %s; self.controlparam.dcvalue=%s %s\n" % (initialloadvalue.__class__.__name__,str(initialloadvalue),self.controlparam.dcvalue.__class__.__name__,str(self.controlparam.dcvalue)))

            # domerge enforces the correct value class by using that class to do the merge 
            mergedval=self.domerge(humanpath,None,"None",[ initialloadvalue, self.controlparam.dcvalue ],[xmldocobj._filename,"in memory"],contexthref=contexthref,manualmerge=True,**self.mergekwargs)
            #sys.stderr.write("mergedval=%s\n\n" % (str(mergedval)))
            pass
        except ValueError as e: 
            raise ValueError("Error performing initial merge of information for parameter %s from URL %s: %s" % (self.controlparam.xmlname, str(xmldocobj.filehref),str(e)))
            pass

        if mergedval != initialloadvalue: 
            # need to update file we just loaded
            self.update_file(xmldocobj,xmlpath,ETxmlpath,mergedval,logfunc,"Text Field %s Updated on file initial load" % (self.controlparam.xmlname))
            pass

        if mergedval != self.controlparam.dcvalue:
            # need to update everything else

            # Pass initialloadparams so we can get a good contexthref for synchronization if one doesn't already exist
            self.synchronize(mergedval,initialloadparams)
            pass


        pass
            

    def synchronize(self,requestedvalue=None,requestedvalueparams=None):
        # prevent nested synchronization attempts
        # as we lock files
        #
        # requestedvalueparams is a (xmldocobj,xmlpath,ETxmlpath,logfunc)
        # tuple that can be used as an extra context source for 
        # find_a_context_href()

        self.in_synchronize=True
        xmldocobj=None

        locklist=[]
        try : 
            
            # attempt a real merge, with our in-memory value as the old value
            
            # lock all files
            # ***BUG*** Opportunity for deadlock with another process
            # working on the same files because our doclists aren't
            # necessarily in the sam e order!!!
            for (xmldocobj,xmlpath,ETxmlpath,logfunc) in self.doclist:
                xmldocobj.lock_rw()
                locklist.append(xmldocobj)
                pass
                
            oldvalue=self.controlparam.dcvalue
            
            mergevalues=[]
            mergesources=[]
            if requestedvalue is not None:
                mergevalues.append(requestedvalue)
                mergesources.append("requested change")
                pass

            humanpath=None
            # read in values of all copies
            for (xmldocobj,xmlpath,ETxmlpath,logfunc) in self.doclist:

                if humanpath is None:
                    humanpath=xmlpath
                    if xmlpath is None:
                        humanpath=etxpath2human(ETxmlpath,xmldocobj.nsmap)
                        pass
                    pass
                
                mergevalues.append(self._get_dcvalue_from_file(xmldocobj,xmlpath,ETxmlpath))
                mergesources.append(xmldocobj.get_filehref().absurl())
                pass
            #sys.stderr.write("mergevalues=%s\n" % (str(mergevalues)))
            # sys.stderr.write("parent merge for %s: %s and %s\n" % (self.controlparam.xmlname,str(newval),str(self.controlparam.dcvalue)))
            
            # Perform merge
            #sys.stderr.write("oldvalue=%s %s\n" % (oldvalue.__class__.__name__,str(oldvalue)))
            #for mv in mergevalues:
            #    sys.stderr.write("mv=%s %s\n" % (mv.__class__.__name__,str(mv)))

            # If we are requesting a non-blank value that can provide a context URL, always use that for the merge context 
            if requestedvalue is not None and hasattr(requestedvalue,"getcontexthref") and not(requestedvalue.getcontexthref().isblank()):
                contexthref=requestedvalue.getcontexthref()
                pass
            else: 
                contexthref=self.find_a_context_href(requestedvalueparams)
                pass
                
            # domerge enforces the correct value class by using that class to do the merge 
            mergedval=self.domerge(humanpath,oldvalue,"in memory",mergevalues,mergesources,contexthref=contexthref,**self.mergekwargs)
            # sys.stderr.write("mergedval=%s\n\n" % (str(mergedval)))

            # createvalueobj can be overridden by derived class (used for current implemenetation of expanding date -- probably should be redone with some kind of merge override instead)
            #mergedval=self.createvalueobj(mergedval)
        

            if requestedvalue is None:
                logfuncmsg="Text Field %s Updated Due to File Resync" % (self.controlparam.xmlname)
                pass
            else :
                logfuncmsg="Text Field %s Updated" % (self.controlparam.xmlname)
                pass
            
            # Write to files if necessary
            for (xmldocobj,xmlpath,ETxmlpath,logfunc) in self.doclist:
                self.update_file(xmldocobj,xmlpath,ETxmlpath,mergedval,logfunc=logfunc,logfuncmsg=logfuncmsg) 
                pass
                    
            # Update param if necessary
            if mergedval != oldvalue: 
                # if self.controlparam.paramtype is dc_value.xmltreevalue:
                #     sys.stderr.write("Assigning merged value to %s (contexthref=%s; specified contexthref=%s): %s\n" % (self.controlparam.xmlname,mergedval._xmltreevalue__xmldoc.getcontexthref().absurl(),contexthref.absurl(),str(mergedval)))
                #     pass
                self.controlparam.assignval(mergedval,self.id)       
                pass
                    
                

            #import pdb as pythondb
            #if self.controlparam.xmlname=="specimen" and len(str(newval))==0:
            #    pythondb.set_trace()
            #    pass
            pass
        except ValueError as e: 
            URL="None"
            if xmldocobj is not None:
                URL=xmldocobj.filehref.absurl()
                pass
            raise ValueError("Error merging information for parameter %s from file %s: %s" % (self.controlparam.xmlname, str(URL),str(e)))
        finally: 
            # unlock all files
            for xmldocobj in locklist:
                xmldocobj.unlock_rw()
                pass
                
            self.in_synchronize=False
            pass
        
        # update this file, if necessary
        #self.update_file(xmldocobj,xmlpath,ETxmlpath,mergedval,logfunc)
        #sys.stderr.write("update_file: %s %s -> %s\n" % (xmldocobj.filename,self.controlparam.xmlname,str(mergedval)))

        #if mergedval != self.controlparam.dcvalue: 
            # controller value has changed... may need to update 
            # everything else 

        #    self.controlparam.assignval(mergedval,self.id)

        #   # update everything else
        #   for (listxmldocobj,listxmlpath,listETxmlpath,listlogfunc) in self.doclist:
        #       if listxmldocobj is not xmldocobj: 

                    # if xmldocobj.autoresync:
                    #     xmldocobj._resync()
                    #     pass
                
        #           listxmldocobj.lock_rw()

        #           # print "Updating file..."
        #           try: 
        #               self.update_file(listxmldocobj,listxmlpath,listETxmlpath,mergedval,logfunc=listlogfunc)
        #               pass
        #           finally:
        #               listxmldocobj.unlock_rw()
        #               pass
        #           pass
        #
        #
        #       pass
                

        pass
        
    
    def update_file(self,xmldocobj,xmlpath,ETxmlpath,valueobj,logfunc,logfuncmsg):
        # xmldocobj MUST be locked when making this call
        # sys.stderr.write("Updating file: %s %s %s\n" % (xmlpath,ETxmlpath,str(valueobj)))
        # sys.stderr.write("lock count: %d %d\n" % (xmldocobj.ro_lockcount,xmldocobj.rw_lockcount))

        if xmlpath is None:
            ETXobj=etree.ETXPath(ETxmlpath)
            foundelement=ETXobj(xmldocobj.doc)
            if len(foundelement) != 1:
                raise ValueError("Non-unique result in update_file for %s (len=%d)" % (ETxmlpath,len(foundelement)))
            xmltag=foundelement[0]
            pass
        else:
            xmltag=xmldocobj.xpathsingle(xmlpath)
            pass
            
        # contexthref=self.find_a_context_href()
        
        #filevalue=self.controlparam.paramtype.fromxml(xmldocobj,xmltag,defunits=self.controlparam.defunits,xml_attribute=self.controlparam.xml_attribute,contextdir=contextdir)
        filevalue=self.controlparam.paramtype.fromxml(xmldocobj,xmltag,defunits=self.controlparam.defunits)

        
        if filevalue != valueobj: # update needed
            # sys.stderr.write("Upddate needed: %s != %s\n" % (str(filevalue),str(valueobj)))

            if logfunc is not None:
                logfunc(logfuncmsg,item=self.controlparam.xmlname,action="updatetext",value=str(valueobj))
                pass
            
            
            if self.controlparam.defunits is not None:            
                # write representation into XML element
                valueobj.xmlrepr(xmldocobj,xmltag,defunits=self.controlparam.defunits) # ,xml_attribute=self.controlparam.xml_attribute)
                pass
            else : 
                # print type(self.controlparam.paramtype)
                # print "id=%x autoflush=%s" % (id(xmldocobj),str(xmldocobj.autoflush))
                valueobj.xmlrepr(xmldocobj,xmltag) # xml_attribute=self.controlparam.xml_attribute)
                pass

            provenance.elementgenerated(xmldocobj,xmltag)
            xmldocobj.modified=True
            pass
        pass
        
        # if xmldocobj.autoflush:
        #     xmldocobj.flush()
        #     pass
        
        pass
    

    def requestvalcallback(self,newvalue,requestid,*cbargs):
        self.numpending -= 1
        if (self.numpending==0):
            self.state=self.controlparam.CONTROLLER_STATE_QUIESCENT
            pass

        # print "doclist=%s" % (str(self.doclist))
        
        try:
            self.synchronize(requestedvalue=newvalue)
            pass
        except:
            # Give error client callback, then raise exception
            if len(cbargs) > 0:
                (exctype,excvalue)=sys.exc_info()[:2]
                clientcallback=cbargs[0]
                clientcallback(self.controlparam,requestid,str(excvalue),None,*cbargs[1:])
                pass

            raise
        #oldvalue=self.controlparam.dcvalue


        ## valueobj=self.controlparam.paramtype(newvalue,defunits=self.controlparam.defunits)
        # valueobj=self.createvalueobj(newvalue)
        
        #mergevalues=[ valueobj ]  # list of values to merge

        ## lock each file smultaneously. Normally we would try to avoid this to eliminate the risk of 
        ## deadlock, but since we are in the mainloop, nobody should have anything locked (hopefully!)

        #for (xmldocobj,xmlpath,ETxmlpath,logfunc) in self.doclist:

        ## xmldocobj.shouldbeunlocked()

        #    xmldocobj.lock_rw() # the lock_rw triggers an xmlresync that can call assignval with a new value
        #    # update mergevalues with this entry
        #    mergevalues.append(self.controlparam.dcvalue)
        #    pass
        #
        #try: 

        ## attempt to merge
        #mergedval=self.domerge(oldvalue,mergevalues,**self.mergekwargs)

        ## attempt to update file
        #    for (xmldocobj,xmlpath,ETxmlpath,logfunc) in self.doclist:
        #        self.update_file(xmldocobj,xmlpath,ETxmlpath,mergedval,logfunc=logfunc)
        #        pass
        #
        #    pass
        #finally:
        #    for (xmldocobj,xmlpath,ETxmlpath,logfunc) in self.doclist:
        #        xmldocobj.unlock_rw() 
        #        pass
        #    pass
        

        ## sys.stderr.write("assign %s=%s\n" % (self.controlparam.xmlname,str(valueobj)))
        #self.controlparam.assignval(valueobj,self.id)       

        #for (xmldocobj,xmlpath,ETxmlpath,logfunc) in self.doclist:
        #    if logfunc is not None:
        #        logfunc("Text Field %s Updated" % (self.controlparam.xmlname),item=self.controlparam.xmlname,action="updatetext",value=str(self.controlparam.dcvalue)) #
        #         pass
        #     pass
        if len(cbargs) > 0:
            clientcallback=cbargs[0]
            clientcallback(self.controlparam,requestid,None,self.controlparam.dcvalue,*cbargs[1:])
            pass
        
        return False
 
    # requestval is a request that this parameter take on the requested value
    # (This is an asynchronous request. Will get callback when complete)
    # returns request identifier that can be used to cancel request 
    # callback(param,requestid,errorstr,newvalue,*cbargs)
    def requestval(self,param,newvalue,*cbargs):
        idstore=[]  # returned identifier is actually a list with the gobject source id as it's only element
        reqid=gobject.timeout_add(0,self.requestvalcallback,newvalue,idstore,*cbargs)
        idstore.append(reqid)
        self.state=self.controlparam.CONTROLLER_STATE_REQUEST_PENDING
        self.numpending+=1
        return idstore

    def cancelrequest(self,param,requestid): 
        # returns True if successfully canceled
        canceled=gobject.source_remove(requestid[0])
        if canceled: 
            self.numpending -= 1
            if (self.numpending==0):
                self.state=self.controlparam.CONTROLLER_STATE_QUIESCENT
                pass
            pass
        
        return canceled
    pass

    
#class synced_accumulating_dates(synced):
#    # This class is a paramdb2 controller for sync'd date elements 
#    # that accumulate instead of replace as you change them. 
#    # It is compatible with dc_value.datesetvalue. 
#    
#    def __init__(self,controlparam):
#        synced.__init__(self,controlparam)
#
#        pass
#        
#
#    def valueobjfromxml(self,xmldocobj,xmlel):
#        # this is a separate method so it can be overridden by derived 
#        # class for implementing expanding date class
#        #!!!*** BUG!! This should really be moved into a domerge() function !!!***
#
#        newval=self.controlparam.paramtype.fromxml(xmldocobj,xmlel,self.controlparam.defunits)
#        oldval=self.controlparam.dcvalue
#        
#        # Form union of desired new value with previous value
#        return newval.union(oldval)
#
#    def createvalueobj(self,newvalue):
#        # this is a separate method so it can be overridden by derived 
#        # class for implementing expanding date class
#        #sys.stderr.write("newvalue=%s\n" % (str(newvalue)))
#        newval=self.controlparam.paramtype(newvalue,defunits=self.controlparam.defunits)
#        #sys.stderr.write("newval=%s (class=%s)\n" % (str(newval),newval.__class__.__name__))
#        oldval=self.controlparam.dcvalue
#        # sys.stderr.write("oldval=%s\n" % (str(oldval)))
#
#        # Form union of desired new value with previous value
#        #sys.stderr.write("New value: %s\n" % (str(newval.union(oldval))))
#        return newval.union(oldval)
#
#    def isconsistent(self,newval,oldval):  # !!! not used anymore (?)
#        return oldval in newval
#    pass

