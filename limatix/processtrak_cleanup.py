import sys
import copy
import collections
import posixpath

try:
    # python2 
    from urllib2 import HTTPError,URLError
    pass
except ImportError:
    # python3
    from urllib.error import HTTPError,URLError
    pass

try:
    # py2.x
    from urllib import pathname2url
    from urllib import url2pathname
    from urllib import quote
    from urllib import unquote
    pass
except ImportError:
    # py3.x
    from urllib.request import pathname2url
    from urllib.request import url2pathname
    from urllib.parse import quote
    from urllib.parse import unquote
    pass




from lxml import etree
from limatix import dc_value
from limatix import xmldoc
from limatix import canonicalize_path
from limatix import processtrak_common




nsmap={ 
    "dc": "http://limatix.org/datacollect",
    "dcv": "http://limatix.org/dcvalue",
    "lip": "http://limatix.org/provenance",
    "prx": "http://limatix.org/processtrak/processinginstructions",
    "xlink": "http://www.w3.org/1999/xlink"
}


class infiledicts(object):
    # Dictionaries are by href unless otherwise specified and are
    # of class inputfile, below
    all=None
    xlg=None
    xlp=None
    prx=None
    otherxml=None
    otherunk=None

    all_by_canonpath=None   # includes local files only

    
    def __init__(self,**kwargs):
        self.all=collections.OrderedDict()
        self.xlg=collections.OrderedDict()
        self.xlp=collections.OrderedDict()
        self.prx=collections.OrderedDict()
        self.otherxml=collections.OrderedDict()
        self.otherunk=collections.OrderedDict()
        self.all_by_canonpath=collections.OrderedDict()
        for kwarg in kwargs:
            assert(hasattr(self,kwarg))
            setattr(self,kwarg,kwargs[kwarg])
            pass
        pass

    @classmethod
    def fromhreflist(cls,inputfilehrefs):
        ifd=cls()
        
        for inputfilehref in inputfilehrefs:
            ifd.open_href(inputfilehref)
            pass
        return ifd

    def open_href(self,inputfilehref):

        inputfilehref=inputfilehref.fragless()
        
        if inputfilehref in self.all:
            return self.all[inputfilehref]
        
        ifo=inputfile.open_href(inputfilehref)
        if ifo.ftype==ifo.IFT_XLG:
            self.xlg[inputfilehref]=ifo
            pass
        elif ifo.ftype==ifo.IFT_XLP:
            self.xlp[inputfilehref]=ifo
            pass
        elif ifo.ftype==ifo.IFT_PRX:
            self.prx[inputfilehref]=ifo
            pass
        elif ifo.ftype==ifo.IFT_OTHERXML:
            self.otherxml[inputfilehref]=ifo
            pass
        elif ifo.ftype==ifo.IFT_OTHERUNK:
            self.otherunk[inputfilehref]=ifo
            pass
        else:
            assert()
            pass

        self.all[inputfilehref]=ifo

        if ifo.canonpath is not None:
            # If the test below fails, that means we have found
            # two files with different hrefs but which are actually the
            # same. This can happen if an href is specified in one place
            # as absolute and another as relative
            
            # This violates the assumptions of our processing
            # and we cannot continue
            if ifo.canonpath in self.all_by_canonpath:
                raise ValueError("Two hrefs: %s (contextlist=%s) and %s (%s) share the same canonical file path %s. This violates the assumptions of our processing and we cannot continue" % (
                    self.all_by_canonpath[ifo.canonpath].href.humanurl(),
                    str(self.all_by_canonpath[ifo.canonpath].href.href_context.contextlist),
                    ifo.href.humanurl(),
                    str(ifo.href.href_context.contextlist),
                    ifo.canonpath))
            
                    
                
            self.all_by_canonpath[ifo.canonpath]=ifo
            pass
        
        return ifo
        
    pass
    
class inputfile(object):
    href=None
    canonpath=None
    xmldocu=None   # opened with use_locking, readonly (for now)
    ftype=None

    IFT_XLG=0
    IFT_XLP=1
    IFT_PRX=2
    IFT_OTHERXML=3
    IFT_OTHERUNK=4
    
    def __init__(self,**kwargs):
        for kwarg in kwargs:
            assert(hasattr(self,kwarg))
            setattr(self,kwarg,kwargs[kwarg])
            pass
        pass

    @classmethod
    def open_href(cls,inputfilehref):
        #barefilename=inputfilehref.get_bare_unquoted_filename()
        #(basename,ext)=posixpath.splitext(barefilename)

        inputfilehref=inputfilehref.fragless()

        ftype=cls.IFT_OTHERUNK
        xmldocu=None
        try:
            xmldocu=xmldoc.xmldoc.loadhref(inputfilehref,nsmap=nsmap,readonly=True,use_locking=True,nodialogs=True)
            try: 
                ftype=cls.detect_ftype(xmldocu)
                pass
            
            finally:
                xmldocu.unlock_ro()
                pass
            pass
        except etree.XMLSyntaxError:
            # Failed to load as XML...
            # leave type as IFT_OTHERUNK
            pass

        canonpath=None
        if inputfilehref.isfile():
            canonpath=canonicalize_path.canonicalize_path(inputfilehref.getpath())
            pass
        
        ifobj=cls(href=inputfilehref,
                  canonpath=canonpath,
                  xmldocu=xmldocu,
                  ftype=ftype)
        return ifobj
    
                  
        
    @classmethod
    def detect_ftype(cls,xmldocu):
        xmldocu.lock_ro()
        try:
            ftype=cls.IFT_OTHERXML
            root=xmldocu.getroot()
            lipprocess=xmldocu.xpath("lip:process")                
            if len(lipprocess) > 0: 
                # does it have any lip:process tags under the main tag?
                # call it an .xlp
                ftype=cls.IFT_XLP
                pass
            elif xmldocu.tag_is(root,"dc:experiment"):
                # .xlg
                ftype=cls.IFT_XLG
                pass
            elif xmldocu.tag_is(root,"prx:processinginstructions"):
                ftype=cls.IFT_PRX
                pass
            elif xmldocu.tag_is(root,"prx:inputfiles") and len(xmldocu.xpath("lip:process")) > 0:
                # A .pro file, which we classify as a .xlp file
                ftype=cls.IFT_XLP
                pass            
            pass
        finally:
            xmldocu.unlock_ro()
            pass
        return ftype

    pass


def add_to_traverse(infiles,pending,completed,newhref):

    newhref=newhref.fragless()

    if newhref.is_directory():
        return  # we don't traverse directories, only explicit references
    
    if newhref not in pending and newhref not in completed:
        try:
            infiles.open_href(newhref)  # adds to dicts if not already present
            pending.add(newhref)
            pass
        except (URLError,HTTPError,IOError):
            # file not present
            sys.stderr.write("WARNING: Unable to open URL %s: %s\n" % (newhref.humanurl(),str(sys.exc_info[1])))
            pass
        pass
    pass

    

def traverse_one(infiles,infileobj,pending,completed,dests,hrefs,recursive=False):
    # go through infile, searching for links


    assert(infileobj.href in pending)
    
    
    if infileobj.ftype==infileobj.IFT_OTHERUNK:
        pending.remove(infileobj.href)
        completed.add(infileobj.href)
        return # cannot contain links

    infileobj.xmldocu.lock_ro()

    try :
        # print("traverse_one: ftype=%d" % (infileobj.ftype))
        if infileobj.ftype==infileobj.IFT_XLG:
            # .XLG file has implicit link to its .XLP file
            barefilename=infileobj.href.get_bare_unquoted_filename()
            (barename,ext)=posixpath.splitext(barefilename)
            if ext==".xlg":
                xlpfile=barename+".xlp"
                xlphref=dc_value.hrefvalue(quote(xlpfile),contexthref=infileobj.href)
                if hrefs is not None:
                    hrefs.add(xlphref)
                    pass
                if recursive:
                    add_to_traverse(infiles,pending,completed,xlphref)
                    pass
                pass
            pass
        
        if infileobj.ftype==infileobj.IFT_XLG or infileobj.ftype==infileobj.IFT_XLP:
            # XLG and XLP files can have dest references
            # and we are tracking those
            # print("got xlg or xlp. infileobj.href=%s" % (infileobj.href.humanurl()))
            desttags=infileobj.xmldocu.xpath("dc:summary/dc:dest[@xlink:href]")
            for desttag in desttags:
                #print("got desttag!")
                desthref=dc_value.hrefvalue.fromxml(infileobj.xmldocu,desttag)
                dests.add(desthref)
                
                pass
            pass
        
        if infileobj.ftype==infileobj.IFT_PRX:
            # .PRX file has implicit links to its input and output files

            # ... We follow links to .xlp files whether or not the recursive flag is set
            
            prx_inputfiles_with_hrefs=processtrak_common.getinputfiles(infileobj.xmldocu)
            prx_outputdict=processtrak_common.build_outputdict(infileobj.xmldocu,prx_inputfiles_with_hrefs)

            for prx_inputfile_href in prx_outputdict:
                if hrefs is not None:
                    hrefs.add(prx_inputfile_href)
                    hrefs.add(prx_outputdict[prx_inputfile_href].outputfilehref)
                    pass
                
                if recursive:
                    add_to_traverse(infiles,pending,completed,prx_inputfile_href)
                    pass
                
                # follow link to output whether or not recursive is set 
                add_to_traverse(infiles,pending,completed,prx_outputdict[prx_inputfile_href].outputfilehref)
                pass
            pass

        # Now go through all explicit links if we need hrefs

        if hrefs is not None or recursive: 
            all_links=infileobj.xmldocu.xpath("//*[@xlink:href]")

            for link in all_links:
                href=dc_value.hrefvalue.fromxml(infileobj.xmldocu,link)
                if hrefs is not None:
                    hrefs.add(href)
                    pass
                if recursive:
                    add_to_traverse(infiles,pending,completed,href)
                    pass
                pass
            pass
        pass
    
    finally:
        infileobj.xmldocu.unlock_ro()
        pass
    
    pending.remove(infileobj.href)
    completed.add(infileobj.href)
 
    pass


def traverse(infiles,infilehrefs=None,recursive=False,need_href_set=False):
    # infiles is infiledict object, infilehrefs is list of hrefs

    
    pending=set([])
    completed=set([])
    dests=set([])

    if need_href_set:
        hrefs=set([])
        pass
    else :
        hrefs=None
        pass

    if infilehrefs is None:
        infilehrefs=list(infiles.all.keys())
        pass
    # print("traverse(%s)" % ([str(infilehref) for infilehref in infilehrefs]))

    
    for infilehref in infilehrefs:
        add_to_traverse(infiles,pending,completed,infilehref)
        pass
    
    # print("traversepending(%s)" % ([str(infilehref) for infilehref in pending]))
    while len(pending) > 0:
        for href in list(pending):
            traverse_one(infiles,infiles.all[href],pending,completed,dests,hrefs,recursive=recursive)
            pass
        pass

    return (completed,dests,hrefs)



