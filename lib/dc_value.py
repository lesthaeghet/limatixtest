import sys
import os
import re
import copy
import math
import string 
import numpy as np
import datetime
import collections
import numbers
import urlparse
import urllib

from lxml import etree

treesync=None
try: 
    import dc_lxml_treesync as treesync
    pass
except ImportError:
    sys.stderr.write("dc_value: Warning: unable to import dc_lxml_treesync -- XML comparisons not supported\n")
    pass


import canonicalize_path

import dc_provenance as provenance
import xmldoc

import dg_units  # note: main program should call dg_units.units_config("insert_basic_units")

try: 
    import builtins  # python3
    pass
except ImportError: 
    import __builtin__ as builtins # python2
    pass

if not hasattr(builtins,"basestring"):
    basestring=str  # python3
    pass

__pychecker__="no-argsused no-override"


DCV="{http://thermal.cnde.iastate.edu/dcvalue}"

# *** IMPORTANT *** 
# Need to add distinction between strings and identifiers, and deal with escaping, etc. 
# Deal with unicode? 

def xmlstoredisplayfmt(xmldocu,element,formatstr):
    if formatstr is not None:
        xmldocu.setattr(element,"dcv:displayfmt",formatstr)
        pass
    else:
        if xmldocu.hasattr(element,"dcv:displayfmt"):
            xmldocu.remattr(element,"dcv:displayfmt")
            pass
        pass
    
    pass

def xmlextractdisplayfmt(xmldocu,element):
    displayfmt=None
    if xmldocu.hasattr(element,"dcv:displayfmt"):
        displayfmt=xmldocu.getattr(element,"dcv:displayfmt")
        pass
    return displayfmt


def xmlstorevalueclass(xmldocu,element,valueclass):
    if value is not None:
        xmldocu.setattr(element,"dcv:valueclass",valueclass.__name__[:-5])  # store class name without trailing "value"
        pass
    else:
        if xmldocu.hasattr(element,"dcv:valueclass"):
            xmldocu.remattr(element,"dcv:valueclass")
            pass
        pass
    
    pass

def xmlextractvalueclass(xmldocu,element):
    globalvars=globals()
    valueclass=None
    if xmldocu.hasattr(element,"dcv:valueclass"):
        valueclassname="%svalue" % (xmldocu.getattr(element,"dcv:valueclass"))
        if valueclassname in globalvars:
            # have a variable of correct name. Make sure it is a class
            # that derives from class value
            if globalvars[valueclassname].__class__ is type: # is a class (i.e. a type)
                if issubclass(globalvars[valueclassname],value): # is a subclass of dc_value.value
                    valueclass=globalvars[valueclassname]
                    pass
                pass
            pass
                    
        pass
    return valueclass


class MergeError(Exception):
    value=None
    def __init__(self,value):
        self.value=value
        pass
    def __str__(self):
        return "MergeError: "+repr(self.value)
    pass




# still need to implement XML output!

# value object and subclasses are all final!
# May not be modified after creation. 


# NOTE: The value classes here are shadowed by paramdb2.param
# So extra methods/any public members added here must also have pass-throughs added to paramdb2.param

class value(object): 
    final=False
    
    # No-op method templates
    def set_string(self,str):
        pass

    def isblank(self):
        return False
    
    def __str__(self) :
        pass

    def format(self,formatstr):
        return str(self)

    
    def __eq__(self,other) :
        pass

    def equiv(self,other):
        # equivalence operator -- like equality
        # but determines whether there is a distinction, 
        # not mathematical equality. 
        #
        # Main difference so far: 
        # NaN == Nan is False, 
        # but NaN.equiv(NaN) is True

        # default behavior: Same as __eq__, but
        # returns True if both are blank
        if self.isblank() and other.isblank():
            return True

        return self.__eq__(other)



    # Define ne as inverse of whatever __eq__ operator is defined
    def __ne__(self,other) :
        return not self.__eq__(other)
    
    def __setattr__(self,name,value):
        if not self.final:
            return object.__setattr__(self, name, value);
        raise AttributeError("Value object has been finalized")

    #@classmethod
    #def __equal_with_blank(cls,a,b):
    #    # private... used by merge
    #    if a.isblank() and b.isblank():
    #        return True
    #    elif a.isblank() and not b.isblank():
    #        return False
    #    elif not(a.isblank()) and b.isblank():
    #        return False
    #    else: 
    #        return a==b
    #    pass

    
    @classmethod
    def merge(cls,parent,descendentlist,contextdir=None):
        # merge: Used to merge multiple, possibly inconsistent, values
        # If parent is None, merge semantics are to overwrite blanks but 
        # otherwise error out
        # if parent is not None, merge semantics are to keep a single change
        # from that parent but to error out if there are multiple changes

        if parent is None: 
            value=None
            for descendent in descendentlist: 
                if not descendent.isblank():
                    if value is None: 
                        value=descendent
                        pass
                    elif value != descendent:  
                       # two values -- raise exception!
                        raise MergeError("Cannot merge values: %s and %s" % (str(value),str(descendent)))

                    pass
                pass
            # if we made it this far, either we have a unique value, or all are blank
            if value is None:  # all are blank
                return descendentlist[0]
            return value
        else : 
            # parent specified, merge in the change!
            
            newvalue=None
            for descendent in descendentlist:
                if not(parent.equiv(descendent)):
                    if newvalue != None: 
                        # two values -- raise exception!
                        raise MergeError("Cannot merge values: Orig=%s; descendents %s and %s" % (str(parent),str(newvalue),str(descendent)))
                        
                    newvalue=descendent
                pass
            if newvalue is None: # no changes at all
                newvalue=parent
                pass
            return newvalue
        pass

    pass


class xmltreevalue(value):
    # This value class represents XML tree
    # NOTE: It is built on xmldoc, so it only handles the primary 
    # text node within an element. Weird mixed structures -- 
    # such as in xhtml -- are not supported. 
    # ... it does ignore whitespace text nodes, so it supports pretty-printing. 

    __xmldoc=None  # PRIVATE -- must use get_xmldoc() to get a copy!!!
    
    def __init__(self,xmldoc_element_or_string,defunits=None,nsmap=None,contextdir=None,force_abs_href=False):
        # contextdir is desired context of new document (also assumed context of source, if source has no context)
        if isinstance(xmldoc_element_or_string,self.__class__):
            self.__xmldoc=xmldoc_element_or_string.get_xmldoc(nsmap=nsmap,contextdir=contextdir,force_abs_href=force_abs_href)
            pass            
        elif isinstance(xmldoc_element_or_string,xmldoc.xmldoc):
            self.__xmldoc=xmldoc.xmldoc.inmemorycopy(xmldoc_element_or_string,nsmap=nsmap,contextdir=contextdir,force_abs_href=force_abs_href)
            pass
        elif isinstance(xmldoc_element_or_string,etree._ElementTree):
            self.__xmldoc=xmldoc.xmldoc.frometree(copy.deepcopy(xmldoc_element_or_string),nsmap=nsmap,contextdir=contextdir,force_abs_href=force_abs_href)
            pass
        elif isinstance(xmldoc_element_or_string,etree._Element):
            element=copy.deepcopy(xmldoc_element_or_string)
            self.__xmldoc=xmldoc.xmldoc.frometree(etree.ElementTree(element),nsmap=nsmap,contextdir=contextdir,force_abs_href=force_abs_href)
            
            pass
        elif xmldoc_element_or_string is None or xmldoc_element_or_string=="":
            self.__xmldoc=None  # Blank!
            pass
        else :
            # treat as string... note we skip whitespace 
            # so pretty-printing is ignored
            self.__xmldoc=xmldoc.xmldoc.fromstring(xmldoc_element_or_string,nsmap=nsmap,contextdir=contextdir,force_abs_href=force_abs_href)
            pass

        #if contextdir is None or contextdir=="":
        #    import pdb as pythondb
        #    pythondb.set_trace()

        self.final=True
        pass

    def isblank(self):
        # blank if __xmldoc is None or if there are no elements
        
        if self.__xmldoc is None:
            return True
        
        if len(self.__xmldoc.xpath("node()|@*"))==0:
            # No elements
            return True
        return False
    


    def get_xmldoc(self,nsmap=None,contextdir=None,force_abs_href=False):
        if self.__xmldoc is None: 
            return None
            
        # Returns a copy, so it's OK to write to it (but it won't have
        # any effect on the dc_value)
        return xmldoc.xmldoc.inmemorycopy(self.__xmldoc,nsmap=nsmap,contextdir=contextdir,force_abs_href=force_abs_href)

    def __unicode__(self):
        if self.__xmldoc is None:
            return u""
        return self.__xmldoc.tostring()
        
    def __str__(self):
        if self.__xmldoc is None:
            return ""
        if sys.version_info[0] >= 3: # Python 3... get unicode string
            return self.__xmldoc.tostring()
        else: 
            # Python 2... get bytes... and to minimize bugs
            # encode as ascii
            return self.__xmldoc.tobytes(encoding=None)
        pass

    def __eq__(self,other):
        othervalue=xmltreevalue(other)
        
        if self.__xmldoc is None and othervalue.__xmldoc is None:
            return True
        elif self.__xmldoc is None or othervalue.__xmldoc is None:
            return False
        #import pdb as pythondb
        if self.__xmldoc.getcontextdir() != other.__xmldoc.getcontextdir():
            # See if there are xlink:href attributes to screw things up
            attrsself=self.__xmldoc.xpath("//*[xlink:href]",namespaces={"xlink":"http://www.w3.org/1999/xlink"})
            attrsother=other.__xmldoc.xpath("//*[xlink:href]",namespaces={"xlink":"http://www.w3.org/1999/xlink"})
            
            if len(attrsself) != len(attrsother):
                return False
            
            if len(attrsself) > 0:
            
                #pythondb.set_trace()
                raise ValueError("xmltreevalue: Cannot currently compare trees with different context directories %s and %s" % (self.__xmldoc.getcontextdir(),other.__xmldoc.getcontextdir()))
            pass
            
        return treesync.treesmatch(self.__xmldoc.getroot(),othervalue.__xmldoc.getroot(),True)

    def xmlrepr(self,xmldocu,element,defunits=None,force_abs_href=False):
        # WARNING: Adds in all attributes of this xml structure to element, 
        # but only cleans out those in the dcvalue namespace, so it is 
        # possible to unintentionally merge. 
        # 
        # The best course of action is not to allow the tree root to have attributes. 
        # NOTE: Cannot update document's or element's nsmap in any effective way. 
        #       This will need to be handled some other way

        # assert(xml_attribute is None) # An xml tree cannot fit in an attribute
        
        oldattrs=element.attrib.keys()
        for oldattr in oldattrs:
            if oldattr.startswith(DCV):
                del element.attrib[oldattr]
                pass
            pass
        
        # Remove children
        element.text=""
        for child in element.getchildren():
            element.remove(child)
            pass
        
        if self.__xmldoc is not None:

            # do context conversion if necessary
            sourcecontext=self.__xmldoc.getcontextdir()
            targetcontext=xmldocu.getcontextdir()

            if sourcecontext is None or targetcontext is None:
                import pdb as pythondb
                pythondb.set_trace()
            
            if canonicalize_path.canonicalize_path(sourcecontext) != canonicalize_path.canonicalize_path(targetcontext):
                # create copy, in desired context
                treecopy=xmldoc.xmldoc.inmemorycopy(self.__xmldoc,contextdir=targetcontext,force_abs_href=force_abs_href)
                ourroot=treecopy.getroot()
                pass
            else: 
                ourroot=self.__xmldoc.getroot()
                pass

            # Copy our children
            ourroot=self.__xmldoc.getroot()
            element.attrib.update(ourroot.attrib) # copy attributes
            element.text=ourroot.text # copy text 
            for child in ourroot.getchildren(): # copy children
                element.append(copy.deepcopy(child))
                pass
            pass

        if xmldocu is not None:
            xmldocu.modified=True
            provenance.elementgenerated(xmldocu.doc,element)
            for child in element.iterdescendants():
                provenance.elementgenerated(xmldocu.doc,child)
                pass
            
            
            
            pass

        pass

    @classmethod
    def fromxml(cls,xmldocu,element,tagnameoverride=None,nsmap=None,defunits=None,contextdir=None,force_abs_href=False):
        # Create from a parsed xml representation. 
        # if tagnameoverride is specified, it will override the tag name of element
        # contextdir is the contextdir you want internally stored
        # in the object for relative links


        # assert(xml_attribute is None)  # storing content in an attribute does not make sense for an xml tre

        if xmldocu is not None:
            provenance.xmldocelementaccessed(xmldocu,element)
            pass

        if tagnameoverride is not None:
            newelement=etree.Element(tagnameoverride,attrib=element.attrib,nsmap=element.nsmap)

            # Copy children (attributes already initialized)
            newelement.text=element.text # copy text 
            for child in element.getchildren(): # copy children
                newelement.append(copy.deepcopy(child))
                pass
            
            element=newelement
            pass
        
        if contextdir is not None or force_abs_href:
            # need to adjust context. 
            # first create object in original context, then
            # convert its context
            obj=cls(element,nsmap=nsmap,contextdir=xmldocu.getcontextdir())

            # convert context
            obj.__xmldoc.setcontextdir(contextdir,force_abs_href=force_abs_href)
            return obj

        return cls(element,nsmap=nsmap,contextdir=xmldocu.getcontextdir())
    
    @classmethod
    def merge(cls,parent,descendentlist,contextdir=None,maxmergedepth=np.Inf,tag_index_paths_override=None):
        # merge: Used to merge multiple, possibly inconsistent, values
        # If parent is None, merge semantics are to overwrite blanks but 
        # otherwise error out
        # if parent is not None, merge semantics are to merge the XML trees, up to maxmergedepth
        
        if parent is None or parent.__xmldoc is None: 
            # blank overwriting semantics
            value=None
            for descendent in descendentlist: 
                if not descendent.isblank():
                    if contextdir is not None:
                        if canonicalize_path.canonicalize_path(descendent.__xmldoc.getcontextdir()) != canonicalize_path.canonicalize_path(contextdir):
                            # context mismatch. Redefine descendent with
                            # desired context
                            descendent=xmltreevalue(descendent,contextdir=contextdir)
                            pass
                        pass
                    if value is None: 
                        value=descendent
                        pass
                    elif value != descendent:  
                       # two values -- raise exception!
                        raise ValueError("Cannot merge values: %s and %s" % (str(value),str(descendent)))

                    pass
                pass
            # if we made it this far, either we have a unique value, or all are blank
            if value is None:  # all are blank
                # find any that actually has an object
                for descendent in descendentlist:
                    if descendent.__xmldoc is not None:
                        return descendent
                    pass
                return descendentlist[0]
            return value

        else: 
            #sys.stderr.write("xmltreev merge\n")
            #sys.stderr.write("parent=%s\n\n" % (str(parent)))
            #cnt=0
            #for descendent in descendentlist:
            #    sys.stderr.write("descendent[%d]=%s\n\n" % (cnt,str(descendent)))
            #    cnt+=1
            #    pass

            #import pdb as pythondb
            #if contextdir is None or isinstance(contextdir,etree._Element) or parent.__xmldoc.getcontextdir() is None:
            #    pythondb.set_trace()
            #try : 

            desiredcontext=canonicalize_path.canonicalize_path(contextdir)
            parentcontext=canonicalize_path.canonicalize_path(parent.__xmldoc.getcontextdir())
            if parentcontext != desiredcontext:
                # Create copy of parent in the proper context
                parent=xmltreevalue(parent,contextdir=contextdir)
                pass

            # Create copy of descendentlist, but in the proper context
            descendent_in_context_list=[ descendent if canonicalize_path.canonicalize_path(descendent.__xmldoc.getcontextdir())==desiredcontext else xmltreevalue(descendent,contextdir=contextdir) for descendent in descendentlist if descendent.__xmldoc is not None ]
                
            newelem=treesync.treesync_multi(parent.__xmldoc.getroot(),[descendent.__xmldoc.getroot() for descendent in descendent_in_context_list if descendent.__xmldoc is not None ],maxmergedepth,ignore_blank_text=True,tag_index_paths_override=tag_index_paths_override)
            #    pass
            #except: 
            #    pythondb.post_mortem()
            #    pass
            pass
        return cls(newelem,contextdir=contextdir)
    pass


class stringvalue(value):
    str=None

    def __init__(self,string,defunits=None) :
        if string is None:
            string=""
            pass

        self.str=str(string);
        self.final=True
        pass
    
    def isblank(self):
        # print "isblank() %d" % (len(self.str))
        if len(self.str) == 0:
            return True
        else : 
            return False
        pass
    
    def __str__(self) :
        return self.str;

    def xmlrepr(self,xmldocu,element,defunits=None):
        # NOTE: if xml_attribute is provided, xmldocu must be also.

        #print "xmlrepr!" + self.str
        # clear out any old attributes in the dcvalue namespace
        oldattrs=element.attrib.keys()
        for oldattr in oldattrs:
            if oldattr.startswith(DCV):
                del element.attrib[oldattr]
                pass
            pass

        text=self.str

        #if is_file_in_dest:
        #    # paramdb text is referring to a file in dest
        #    # need to find canonical location, then 
        #    # a relative path to that location
        #
        #    canonpath=canonicalize_path.canonicalize_relpath(dest,self.str)
        #    text=canonicalize_path.rel_or_abs_path(os.path.split(xmldocu.filename)[0],canonpath)
        #    pass

        #if xml_attribute is None: 
        # set text
        element.text=text
        #else: 
        #xmldocu.setattr(element,xml_attribute,text)
        #    pass
            
        if xmldocu is not None:
            xmldocu.modified=True
            provenance.elementgenerated(xmldocu.doc,element)
            pass

        pass

    def value(self):
        if self.str is None:
            return ""
        return self.str
    

    @classmethod
    def fromxml(cls,xmldocu,element,defunits=None,contextdir=None):
        # NOTE: to use xml_attribute you must provide xmldocu)
        if xmldocu is not None:
            provenance.xmldocelementaccessed(xmldocu,element)
            pass

        text=element.text
        # if xml_attribute is not None:
        #    text=xmldocu.getattr(element,xml_attribute,"")
        
        #if is_file_in_dest:
        #    # canonicalized file we are referring to 
        #    canonname=canonicalize_path.canonicalize_relpath(os.path.split(xmldocu.filename)[0],text)
        #    filepart=os.path.split(canonname)[1]
        #    # canonicalized dest
        #    canondest=canonicalize_path.canonicalize_path(dest)
        #    
        #    # put dest and filepart together... does it match canonname?
        #    if os.path.join(canondest,filepart)==canonname:
        #        # if so we strip off the path completely
        #        text=filepart
        #        pass
        #    # otherwise as-is
        #    pass

        return cls(text)
    
    
    
    def __eq__(self,other) :
        # print "StringValue Eq called!"
        if other is None and self.str is None:
            return True
        if other is None:
            return False
        
        # print "stringcomp(%s,%s)" % (self.str,str(other))
        return self.str==str(other);
    
    pass




class hrefvalue(stringvalue):
    # an href is a hyperte reference with
    # a possible context. 

    # It is represented either as a URL
    # or as a relative or absolute path. If a relative path,
    # it is relative to the internally-stored contextdir. 
    
    # its string representation is an escaped URL
    #
    # if it is a relative local file reference, without leading
    # file://, it is stored along with a contextdir as a path


    # That way you don't need to specify dest or is_file_in_dest -- because it might not be in dest!


    # str=None    # str (defined in superclass) is used to store URL
                  # unless str is None, in which case path and context are used
    path = None   # File path (must be converted with pathname2url to use as a url)
    contextdir=None  # Contextdir for path if path is relative

    def __init__(self,URL,contextdir=None,path=None,defunits=None) :
        if URL is None and path is None:
            # URL blank
            URL=""
            pass

        if hasattr(URL,"path") and hasattr(URL,"contextdir"):
            # URL is actually an hrefvalue
            self.str=URL.str
            self.path=URL.path
            self.contextdir=URL.contextdir
            if self.str is None and not os.path.isabs(self.path):
                assert(self.contextdir is not None)
                pass
            pass
        elif URL is not None:
            # URL provided... if it is a local file, attempt
            # to interpret it. 
            self.contextdir=contextdir
            
            if URL=="":
                # blank
                self.str=""
                pass
            else: 
                parsedurl=urlparse.urlparse(str(URL))
                if parsedurl.scheme=="":
                    self.path=urllib.url2pathname(str(URL))
                    
                    if not os.path.isabs(self.path):
                        assert(self.contextdir is not None)
                        pass

                    pass
                elif parsedurl.scheme=="file" and parsedurl.netloc=="":
                    self.path=urllib.url2pathname(parsedurl.path)
                    if not os.path.isabs(self.path):
                        assert(self.contextdir is not None)
                        pass
                
                    pass
                else:
                    self.str=str(URL)
                    pass
                pass
            pass
        else:
            # Assume path provided 
            self.path=path
            self.contextdir=contextdir

            if not os.path.isabs(self.path):
                assert(self.contextdir is not None)
                pass

            pass

        self.final=True

        pass

    def isblank(self):
        if self.str is not None and len(self.str)==0:
            return True
        return False
        
    def ismem(self):
        return self.str is not None and self.str.startswith("mem://")

    def ishttp(self):
        return self.str is not None and self.str.startswith("http://")

    
    
    def __str__(self) :
        # returns escaped URL, relative if that is the way it is stored
        if self.str is not None:
            return self.str

        # Stored as path, not as URL
        # Convert to an escaped URL
        assert(self.path is not None)
        return urllib.pathname2url(self.path)
        

    def islocalfile(self):
        return self.path is not None
    
    def xmlrepr(self,xmldocu,element,defunits=None,force_abs_href=False):

        #import pdb as pythondb
        #if element.tag=="{http://thermal.cnde.iastate.edu/datacollect}dgsfile":
        #    pythondb.set_trace()

        #if xml_attribute is None:
        xml_attribute="xlink:href"
            
        #assert(xml_attribute=="xlink:href")
        #assert(not is_file_in_dest) # This derived class uses its internal context specification, not the is_file_in_dest parameter
        # NOTE: if xml_attribute is provided, xmldocu must be also.

        #print "xmlrepr!" + self.str
        # clear out any old attributes in the dcvalue namespace
        oldattrs=element.attrib.keys()
        for oldattr in oldattrs:
            if oldattr.startswith(DCV):
                del element.attrib[oldattr]
                pass
            pass

        text=self.str
        if text is None: 
            # stored as a path instead
            assert(self.path is not None)
            path=self.path
            if not(os.path.isabs(path)):
                # join with contextdir
                path=canonicalize_path.canonicalize_relpath(self.contextdir,path)
                pass

            # if relative, place relative to the contextdir of the xml file
            if not os.path.isabs(self.path) and not force_abs_href:
                docucontextdir=xmldocu.getcontextdir()
                path=canonicalize_path.relative_path_to(docucontextdir,path)
                pass
            
            # Perform url escaping
            text=urllib.pathname2url(path)
            pass
            
        xmldocu.setattr(element,xml_attribute,text)
        xmldocu.modified=True
        provenance.elementgenerated(xmldocu.doc,element)

        pass

    def getpath(self,contextdir=None):
        # returns path (relative to contextdir if appropriate, or current directory
        # by default) or None
        # if the URL is not an appropriate type
        # returns filesystem path, not URL
        if self.path is None:
            return None

        path=self.path
        if not os.path.isabs(path):
            path=os.path.join(self.contextdir,self.path)
            pass
        
            
        if not os.path.isabs(path):
            if contextdir is None:
                contextdir="."
                pass
            return canonicalize_path.relative_path_to(contextdir,os.path.join(self.contextdir,self.path))
        return path

    @classmethod
    def from_rel_path(cls,contextdir,path): # was frompath()
        # Path is desired file
        # Always stores relative path unless contextdir is None
        # contextdir is context relative to which path should be stored
        # will store absolute path otherwise

        if contextdir is not None:
            path=canonicalize_path.relative_path_to(contextdir,path)
            pass
        else: 
            path=canonicalize_path.canonicalize_path(path)
            pass
            
        # create and return the context
        return hrefvalue(None,contextdir=contextdir,path=path)

    @classmethod
    def from_rel_or_abs_path(cls,contextdir,path):
        # Path is desired file
        # Stores relative path or absolute path
        # according to whether path is relative or
        # absolute (unless contextdir is None, in which case
        # path is always absolute)
        # contextdir is context relative to which path should be stored
        # will store absolute path otherwise

        if contextdir is not None and not(os.path.isabs(path)):
            path=canonicalize_path.relative_path_to(contextdir,path)
            pass
        else: 
            path=canonicalize_path.canonicalize_path(path)
            pass
            
        # create and return the context
        return hrefvalue(None,contextdir=contextdir,path=path)


        

    @classmethod
    def fromxml(cls,xmldocu,element,defunits=None,contextdir=None,force_abs_href=False):
        # NOTE: to use xml_attribute you must provide xmldocu)
        # contextdir is the contextdir you want internally stored
        # in the object for relative links... defaults to context of xmldocu
        # if you don't specify it, aboslute links will be used!
        
        if xmldocu is not None:
            provenance.xmldocelementaccessed(xmldocu,element)

            xmlcontextdir=xmldocu.getcontextdir()
            pass
        else:
            xmlcontextdir=None
            pass

        #if xml_attribute is None:
        xml_attribute="xlink:href"

        # assert(xml_attribute=="xlink:href")

        #assert(not is_file_in_dest) # This derived class uses its internal context specification, not the is_file_in_dest parameter

        text=xmldocu.getattr(element,xml_attribute,"")

        val=hrefvalue(text,contextdir=xmlcontextdir)

        if val.contextdir is not None and contextdir is not None and val.path is not None:
            #sys.stderr.write("contextdir=%s; path=%s\n" % (val.contextdir,val.path))
            canonpath=canonicalize_path.canonicalize_path(os.path.join(val.contextdir,val.path))

            if force_abs_href:
                # use absolute path and create object
                return hrefvalue(None,contextdir=contextdir,path=canonpath)

            if contextdir != val.contextdir and val.path is not None and not os.path.isabs(val.path):
                # Now we know we have a relative path.
                # It is relative to the file it was stored in (val.contextdir)
                # but we need to make it relative to the requested location (contextdir)


                # create relative path and create object
                return hrefvalue(None,contextdir=contextdir,path=canonicalize_path.relative_path_to(contextdir,canonpath))
        

                pass

            #val.contextdir=contextdir  # We can't set the attribute because 'final' is already set
            object.__setattr__(val, "contextdir", contextdir);
            pass
        if val.path is not None and not os.path.isabs(val.path):
            assert(val.contextdir is not None)
        return val
    
    def __hash__(self):
        if self.str is not None:
            return self.str.__hash__()

        return canonicalize_path.canonicalize_path(self.path).__hash__()
    
    def __eq__(self,other) :
        if not hasattr(other,"path"):
            return str(self)==str(other)
        
        if self.path is None and other.path is None:
            return self.str==other.str

        if self.path is not None and other.path is None:
            return False
        
        if self.path is None and other.path is not None:
            return False

        # now both self and other have valid "path" attributes

        # consider blank case
        if (self.path=="" or other.path=="") and self.path != other.path:
            return False
        

        # return whether or not paths match
        return canonicalize_path.canonicalize_relpath(self.contextdir,self.path)==canonicalize_path.canonicalize_relpath(other.contextdir,other.path)

    
    pass


class complexunitsvalue(value) :
    val=None  #!!! private
    unit=None #!!! private
    defunit=None #!!! private

    # neither val nor unit are permitted to be None. 
    # val may be NaN
    # unit may be unitless.
    
    def __reduce__(self):
        # dg_units is complicated to pickle, so instead, let's just 
        # pass this value as its actual value string and recreate it
        # as a new value object on the other side
        arg1 = self.__class__
        arg2 = (self.format(),)
        return (arg1, arg2)

    def __init__(self,val,units=None,defunits=None) :
                
        if isinstance(val,basestring):
            if units is None:
                matchobj=re.match(R""" *([\(]? *([-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?) *[+-] *([-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?[ij]?) *?[\)]?) *[[]?([^\][]*)[]]?""",val)
                if matchobj is not None :
                    self.val=complex(matchobj.group(1))
                    self.unit=dg_units.parseunits(matchobj.group(10))
                    pass
                pass
            else :
                self.val=complex(val)                
                if isinstance(units,basestring):
                    self.unit=dg_units.parseunits(units);
                    pass
                else :
                    self.unit=dg_units.copyunits(units);
                    pass
                pass
            pass
        elif hasattr(val,"value"):
            # val is already a dc_value object
            if units is None:
                self.val=val.value()
                self.unit=val.units()
                pass
            else : 
                if isinstance(units,basestring):
                    unitstruct=dg_units.parseunits(units)
                    pass
                else: 
                    unitstruct=units
                    pass
                
                self.val=val.value(unitstruct)
                self.unit=dg_units.copyunits(unitstruct)
                pass
            
            pass
        elif isinstance(val, complex):
            self.val=val;
            if units is not None:
                if isinstance(units,basestring):
                    self.unit=dg_units.parseunits(units);
                    pass
                else :
                    self.unit=dg_units.copyunits(units);
                    pass
                pass
            pass
        elif val is None:
            pass
        else:
            raise AttributeError("Invalid value input for complexunitsvalue:  %s is %s" % (repr(val), repr(type(val))))

        if self.val is None:
            self.val=complex(np.nan, np.nan)
            pass

        if defunits is not None:
            self.defunit=dg_units.parseunits(defunits);
            pass
        
        if self.unit is None and self.defunit is not None:
            self.unit=dg_units.copyunits(self.defunit);            
            pass
        

        if self.unit is None:
            self.unit=dg_units.createunits()
            pass
        
        if self.unit is not None and self.defunit is not None :
            # print self.unit
            unitfactor=dg_units.compareunits(self.unit,self.defunit);
            if unitfactor==0.0 :
                # incompatible units
                raise AttributeError("Incompatible units: %s %s and %s" % (self.val,str(self.unit),str(defunits)))
            
            pass

        
        self.final=True
        pass


    def isblank(self): # we represent blank as NaN
        return np.isnan(self.val)

    def numvalue(self,units=None):
        return self.value(units)

    def value(self,units=None):
        if units is None:
            return self.val;
        
        if isinstance(units,basestring):
            unitstruct=dg_units.parseunits(units)
            pass
        else :
            unitstruct=units
            pass
        
        # print type(self.unit)
        # print type(units)
        # print type(units) is str
        # print type(self.unit)
        unitfactor=dg_units.compareunits(self.unit,unitstruct)
        # print unitfactor
        if unitfactor==0.0:
            raise ValueError("Incompatible units: %s and %s" % (str(self.unit),str(unitstruct)))
        
        return self.val*unitfactor

    def units(self):
        return dg_units.copyunits(self.unit)

    def valuedefunits(self):
        return self.value(self.defunit)

    def format(self,formatstr=None,unit=None):

        if unit is not None and not isinstance(unit,dg_units.dgu_units):
            unit=dg_units.parseunits(unit)
            pass
        if unit is  None:
            unit=self.defunit
            pass
        if unit is None:
            unit=self.unit
            pass

        if formatstr is None:
            return "%s %s" % (repr(self.value(unit)),str(unit))
        
        
        # print "formatstr=%s" % (formatstr)
        # if you get a 
        # TypeError: not all arguments converted during string formatting
        # on this next line, then you probably forgot the % in the %f or %g
        # in your initialization of displayfmt in the .dcc file
        return (formatstr+" %s") % (self.value(unit),str(unit))

    def comsolstr(self):
        if self.val is None: 
            return ""
        elif len(str(self.unit))==0 :
            return repr(self.val)
        else :
            return "%s[%s]" % (repr(self.val),str(self.unit))
        pass
    
    def __str__(self) :
        if self.val is None: 
            return ""
        elif len(str(self.unit))==0 :
            return repr(self.val)
        else :
            return "%s %s" % (repr(self.val),str(self.unit))
        pass
    
    @classmethod
    def fromxml(cls,xmldocu,element,defunits=None,contextdir=None):
        # NOTE: if xml_attribute is provided, xmldocu must be also.

        # Check if we have a units attribute
        if xmldocu is not None:
            provenance.xmldocelementaccessed(xmldocu,element)
            pass
        
        #if xml_attribute is None:
        elementtext=element.text
        #    pass
        #else: 
        #    elementtext=xmldocu.getattr(element,xml_attribute,"")
        #    pass


        if DCV+"units" in element.attrib:
            return cls(elementtext,element.attrib[DCV+"units"],defunits=defunits)
        elif "units" in element.attrib:
            return cls(elementtext,element.attrib["units"],defunits=defunits)
        else :
            return cls(elementtext,defunits=defunits)
        pass


    def xmlrepr(self,xmldocu,element,defunits=None):
        # NOTE: if xml_attribute is provided, xmldocu must be also.

        # clear out any old attributes
        oldattrs=element.attrib.keys()
        for oldattr in oldattrs:
            if oldattr.startswith(DCV):
                del element.attrib[oldattr]
                pass
            pass

        defunit=self.defunit

        if defunits is not None:
            # default unit set: force this unit
            defunit=dg_units.parseunits(defunits)
            # print "defunits: %s defunit: %s self.val: %s self.unit: %s" % (str(defunits),str(defunit),str(self.val),str(self.unit))
            pass
        
        
        if defunit is not None:
            if not np.isnan(self.val):
                unitfactor=0.0
                
                unitfactor=dg_units.compareunits(self.unit,defunit);
                
                if unitfactor != 0.0:
                    if self.val is not None:
                        elementtext=repr(self.val*unitfactor)
                        element.attrib[DCV+"units"]=str(defunit)
                        pass
                    else :
                        elementtext=""
                        element.attrib[DCV+"units"]=str(defunit)
                        pass
                    pass
                else :
                    sys.stderr.write("Warning: unit mismatch in %s tag: %s vs %s\n" % (element.tag,str(self),str(defunits)))
                    pass
                pass
            else :
                elementtext="NaN"
                element.attrib[DCV+"units"]=str(defunits)
                
                pass
            
            pass
        else : 
            if self.val is not None: 
                elementtext=repr(self.val)
                pass
            else :
                elementtext="NaN"
                pass
            
            element.attrib[DCV+"units"]=str(self.unit)
            
            pass

        #if xml_attribute is None: 
        # set text
        element.text=elementtext
        #    pass
        #else: 
        #    xmldocu.setattr(element,xml_attribute,elementtext)
        #    pass
        
        if xmldocu is not None:
            xmldocu.modified=True
            provenance.elementgenerated(xmldocu.doc,element)
            pass

        
        pass
    

    def simplifyunits(self):
        unitcopy=dg_units.copyunits(self.unit)
        dg_units.simplifyunits(unitcopy)
        coefficient=dg_units.extractcoefficient(unitcopy);

        return complexunitsvalue(self.val*coefficient,unitcopy)

    def inunits(self,unit): # unit conversion, new complexunitsvalue object
        
        if unit is None:
            unit=""
            pass
        
        if not isinstance(unit,dg_units.dgu_units):
            unit=dg_units.parseunits(unit)
            pass
        

        return complexunitsvalue(self.value(unit),unit)
    
    
    def __eq__(self,other) :
        # print "NumericUnitsValue Eq called!"
        # print self.val==other.value(),self.unit==other.units()
        # print str(self.unit),str(other.units())

        otherval=other.value()

        otherunit=other.units()
        
        # print "self.val=%s, otherval=%s" % (str(self.val),str(otherval))
        # print "self.unit=%s, otherunit=%s" % (str(self.unit),str(otherunit))
        unitfactor=dg_units.compareunits(self.unit,otherunit)
        unitfactor2=dg_units.compareunits(otherunit,self.unit)
        if unitfactor==0.0 or unitfactor2==0.0:
            # unit mismatch
            return False
        else :
            
            # avoid roundoff issues by checking strict equality both ways
            if self.val*unitfactor==otherval or self.val==otherval*unitfactor2:
                return True
            else :
                return False
            
            pass
        
        pass

    def equiv(self,other):
        # Like __eq__ but determines equivalence, 
        # not equality. e.g. NaN equivalent to NaN
        otherval=other.value()
        otherunit=other.units()
        
        unitfactor=dg_units.compareunits(self.unit,otherunit)
        unitfactor2=dg_units.compareunits(otherunit,self.unit)
    
        if unitfactor==0.0 or unitfactor2==0.0:
            # unit mismatch
            return False
        
        if np.isnan(self.val) and np.isnan(otherval):
            return True # NaN equivalent to NaN

        # fall through to equality
        return self.__eq__(other)
    
        
    def __pow__(self,other,modulo=None):
        if modulo is not None:
            raise ValueError("pow modulo not supported")

        if isinstance(other,complexunitsvalue):
            other=other.value("") # need unitless representation of exponent
            pass
        
        return complexunitsvalue(self.val**other,dg_units.powerunits(self.unit,other))

        pass
    
    def __add__(self,other):
        if isinstance(other,numbers.Number):
            unitfactor=dg_units.compareunits(self.unit, dg_units.createunits())            
            value=other
            pass        
        else :
            unitfactor=dg_units.compareunits(self.unit, other.units())
            value=other.value()
            pass
        if unitfactor == 0.0:
            raise ValueError("Attempting to add values with incompatible units %s and %s" % (str(self.unit),str(other.units())))
        
        return complexunitsvalue(self.val + value/unitfactor,self.unit);

    def __sub__(self,other):
        if isinstance(other,numbers.Number):
            unitfactor=dg_units.compareunits(self.unit, dg_units.createunits())
            value=other
            pass        
        else :
            unitfactor=dg_units.compareunits(self.unit, other.units())
            value=other.value()
            pass
        
        if unitfactor == 0.0:
            raise ValueError("Attempting to add values with incompatible units %s and %s" % (str(self.unit),str(other.units())))
        
        return complexunitsvalue(self.val - value/unitfactor,self.unit);
    
    def __mul__(self,other):
        if not isinstance(other,float):
            newunits=dg_units.multiplyunits(self.unit, other.units())
            tomul=other.value();
            pass
        else :
            newunits=self.unit
            tomul=other;
            pass
        
        return complexunitsvalue(self.val*tomul,newunits);
    
    def __div__(self,other):
        if not isinstance(other,float):
            newunits=dg_units.divideunits(self.unit, other.units())
            
            todiv=other.value()
            pass
        else :
            newunits=self.unit
            todiv=other
            pass

        
        return complexunitsvalue(self.val/todiv,newunits);
    pass
    
class numericunitsvalue(value) :
    val=None  #!!! private
    unit=None #!!! private
    defunit=None #!!! private

    # neither val nor unit are permitted to be None. 
    # val may be NaN
    # unit may be unitless.
    
    def __reduce__(self):
        # dg_units is complicated to pickle, so instead, let's just 
        # pass this value as its actual value string and recreate it
        # as a new value object on the other side
        arg1 = self.__class__
        arg2 = (self.format(),)
        return (arg1, arg2)

    def __init__(self,val,units=None,defunits=None) :
        # self.name=name;

        
        if isinstance(val,basestring):
            if units is None:
                matchobj=re.match(R""" *(([-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)|([-+]?[iI][nN][fF])|([nN][aA][nN])) *[[]?([^\][]*)[]]?""",val);
                if matchobj is not None :
                    self.val=float(matchobj.group(1))
                    self.unit=dg_units.parseunits(matchobj.group(8))
                    pass
                pass
            else :
                self.val=float(val)                
                if isinstance(units,basestring):
                    self.unit=dg_units.parseunits(units);
                    pass
                else :
                    self.unit=dg_units.copyunits(units);
                    pass
                pass
            pass
        elif hasattr(val,"value"):
            # val is already a dc_value object
            if units is None:
                self.val=val.value()
                self.unit=val.units()
                pass
            else : 
                if isinstance(units,basestring):
                    unitstruct=dg_units.parseunits(units)
                    pass
                else: 
                    unitstruct=units
                    pass
                
                self.val=val.value(unitstruct)
                self.unit=dg_units.copyunits(unitstruct)
                pass
            
            pass
        else :
            self.val=val;
            if units is not None:
                if isinstance(units,basestring):
                    self.unit=dg_units.parseunits(units);
                    pass
                else :
                    self.unit=dg_units.copyunits(units);
                    pass
                pass
            pass

        if self.val is None:
            self.val=float('NaN')
            pass

        if defunits is not None:
            self.defunit=dg_units.parseunits(defunits);
            pass
        
        if self.unit is None and self.defunit is not None:
            self.unit=dg_units.copyunits(self.defunit);            
            pass
        

        if self.unit is None:
            self.unit=dg_units.createunits()
            pass
        
        if self.unit is not None and self.defunit is not None :
            # print self.unit
            unitfactor=dg_units.compareunits(self.unit,self.defunit);
            if unitfactor==0.0 :
                # incompatible units
                raise AttributeError("Incompatible units: %.8g %s and %s" % (self.val,str(self.unit),str(defunits)))
            
            pass

        
        self.final=True
        pass


    def isblank(self): # we represent blank as NaN
        return math.isnan(self.val)

    def numvalue(self,units=None):
        return self.value(units)
    

    def value(self,units=None):
        if units is None:
            return self.val;
        
        if isinstance(units,basestring):
            unitstruct=dg_units.parseunits(units)
            pass
        else :
            unitstruct=units
            pass
        
        # print type(self.unit)
        # print type(units)
        # print type(units) is str
        # print type(self.unit)
        unitfactor=dg_units.compareunits(self.unit,unitstruct)
        # print unitfactor
        if unitfactor==0.0:
            raise ValueError("Incompatible units: %s and %s" % (str(self.unit),str(unitstruct)))
        
        return self.val*unitfactor

    def units(self):
        return dg_units.copyunits(self.unit)

    def valuedefunits(self):
        return self.value(self.defunit)

    def format(self,formatstr=None,unit=None):

        if unit is not None and not isinstance(unit,dg_units.dgu_units):
            unit=dg_units.parseunits(unit)
            pass
        if unit is  None:
            unit=self.defunit
            pass
        if unit is None:
            unit=self.unit
            pass

        if formatstr is None:
            return "%s %s" % (repr(self.value(unit)),str(unit))
        
        
        # print "formatstr=%s" % (formatstr)
        # if you get a 
        # TypeError: not all arguments converted during string formatting
        # on this next line, then you probably forgot the % in the %f or %g
        # in your initialization of displayfmt in the .dcc file
        return (formatstr+" %s") % (self.value(unit),str(unit))

    def comsolstr(self):
        if self.val is None: 
            return ""
        elif len(str(self.unit))==0 :
            return repr(self.val)
        else :
            return "%s[%s]" % (repr(self.val),str(self.unit))
        pass
    
    def __str__(self) :
        if self.val is None: 
            return ""
        elif len(str(self.unit))==0 :
            return repr(self.val)
        else :
            return "%s %s" % (repr(self.val),str(self.unit))
        pass
    
    @classmethod
    def fromxml(cls,xmldocu,element,defunits=None,contextdir=None):
        # NOTE: if xml_attribute is provided, xmldocu must be also.

        if xmldocu is not None:
            provenance.xmldocelementaccessed(xmldocu,element)
            pass

        #if xml_attribute is None:
        elementtext=element.text
        #    pass
        #else: 
        #    elementtext=xmldocu.getattr(element,xml_attribute,"")
        #    pass

        # Check if we have a units attribute
        if DCV+"units" in element.attrib:
            return cls(elementtext,element.attrib[DCV+"units"],defunits=defunits)
        elif "units" in element.attrib:
            return cls(elementtext,element.attrib["units"],defunits=defunits)
        else :
            return cls(elementtext,defunits=defunits)
        pass


    def xmlrepr(self,xmldocu,element,defunits=None):
        # NOTE: if xml_attribute is provided, xmldocu must be also.

        # clear out any old attributes
        oldattrs=element.attrib.keys()
        for oldattr in oldattrs:
            if oldattr.startswith(DCV):
                del element.attrib[oldattr]
                pass
            pass

        defunit=self.defunit

        if defunits is not None:
            # default unit set: force this unit
            defunit=dg_units.parseunits(defunits)
            # print "defunits: %s defunit: %s self.val: %s self.unit: %s" % (str(defunits),str(defunit),str(self.val),str(self.unit))
            pass
        
        
        if defunit is not None:
            if not math.isnan(self.val):
                unitfactor=0.0
                
                unitfactor=dg_units.compareunits(self.unit,defunit);
                
                if unitfactor != 0.0:
                    if self.val is not None:
                        elementtext=repr(self.val*unitfactor)
                        element.attrib[DCV+"units"]=str(defunit)
                        pass
                    else :
                        elementtext=""
                        element.attrib[DCV+"units"]=str(defunit)
                        pass
                    pass
                else :
                    raise ValueError("Warning: unit mismatch in %s tag: %s vs %s\n" % (element.tag,str(self),str(defunits)))
                pass
            else :
                elementtext="NaN"
                element.attrib[DCV+"units"]=str(defunits)
                
                pass
            
            pass
        else : 
            if self.val is not None: 
                elementtext=repr(self.val)
                pass
            else :
                elementtext="NaN"
                pass
            
            element.attrib[DCV+"units"]=str(self.unit)
            
            pass

        #if xml_attribute is None: 
        # set text
        element.text=elementtext
        #    pass
        #else: 
        #    xmldocu.setattr(element,xml_attribute,elementtext)
        #    pass
        
        if xmldocu is not None:
            xmldocu.modified=True
            provenance.elementgenerated(xmldocu.doc,element)
            pass
        
        pass
    

    def simplifyunits(self):
        unitcopy=dg_units.copyunits(self.unit)
        dg_units.simplifyunits(unitcopy)
        coefficient=dg_units.extractcoefficient(unitcopy);

        return numericunitsvalue(self.val*coefficient,unitcopy)

    def inunits(self,unit): # unit conversion, new numericunitsvalue object
        
        if unit is None:
            unit=""
            pass
        
        if not isinstance(unit,dg_units.dgu_units):
            unit=dg_units.parseunits(unit)
            pass
        

        return numericunitsvalue(self.value(unit),unit)
    
    
    def __eq__(self,other) :
        # print "NumericUnitsValue Eq called!"
        # print self.val==other.value(),self.unit==other.units()
        # print str(self.unit),str(other.units())

        otherval=other.value()

        otherunit=other.units()
        
        # print "self.val=%s, otherval=%s" % (str(self.val),str(otherval))
        # print "self.unit=%s, otherunit=%s" % (str(self.unit),str(otherunit))
        unitfactor=dg_units.compareunits(self.unit,otherunit)
        unitfactor2=dg_units.compareunits(otherunit,self.unit)
        if unitfactor==0.0 or unitfactor2==0.0:
            # unit mismatch
            return False
        else :
            

            # avoid roundoff issues by checking strict equality both ways
            if self.val*unitfactor==otherval or self.val==otherval*unitfactor2:
                return True
            else :
                return False
            
            pass
        
        pass

    def equiv(self,other):
        # Like __eq__ but determines equivalence, 
        # not equality. e.g. NaN equivalent to NaN
        otherval=other.value()
        otherunit=other.units()
        
        unitfactor=dg_units.compareunits(self.unit,otherunit)
        unitfactor2=dg_units.compareunits(otherunit,self.unit)
    
        if unitfactor==0.0 or unitfactor2==0.0:
            # unit mismatch
            return False
        
        if np.isnan(self.val) and np.isnan(otherval):
            return True # NaN equivalent to NaN

        # fall through to equality
        return self.__eq__(other)


    def __pow__(self,other,modulo=None):
        if modulo is not None:
            raise ValueError("pow modulo not supported")

        if isinstance(other,numericunitsvalue):
            other=other.value("") # need unitless representation of exponent
            pass
        
        return numericunitsvalue(self.val**other,dg_units.powerunits(self.unit,other))

        pass
    
    def __add__(self,other):
        if isinstance(other,numbers.Number):
            unitfactor=dg_units.compareunits(self.unit, dg_units.createunits())            
            value=other
            pass        
        else :
            unitfactor=dg_units.compareunits(self.unit, other.units())
            value=other.value()
            pass
        if unitfactor == 0.0:
            raise ValueError("Attempting to add values with incompatible units %s and %s" % (str(self.unit),str(other.units())))
        
        return numericunitsvalue(self.val + value/unitfactor,self.unit);

    def __sub__(self,other):
        if isinstance(other,numbers.Number):
            unitfactor=dg_units.compareunits(self.unit, dg_units.createunits())
            value=other
            pass        
        else :
            unitfactor=dg_units.compareunits(self.unit, other.units())
            value=other.value()
            pass
        
        if unitfactor == 0.0:
            raise ValueError("Attempting to add values with incompatible units %s and %s" % (str(self.unit),str(other.units())))
        
        return numericunitsvalue(self.val - value/unitfactor,self.unit);
    
    def __mul__(self,other):
        if not isinstance(other,float):
            newunits=dg_units.multiplyunits(self.unit, other.units())
            tomul=other.value();
            pass
        else :
            newunits=self.unit
            tomul=other;
            pass
        
        return numericunitsvalue(self.val*tomul,newunits);
    
    def __div__(self,other):
        if not isinstance(other,float):
            newunits=dg_units.divideunits(self.unit, other.units())
            
            todiv=other.value()
            pass
        else :
            newunits=self.unit
            todiv=other
            pass

        
        return numericunitsvalue(self.val/todiv,newunits);
    pass






class integervalue(value) :
    val=None  #!!! private

    # val may be None
    
    def __reduce__(self):
        # dg_units is complicated to pickle, so instead, let's just 
        # pass this value as its actual value string and recreate it
        # as a new value object on the other side
        arg1 = self.__class__
        arg2 = (str(self.val),)
        return (arg1, arg2)
        
    def __init__(self,val,defunits=None) :
        # self.name=name;

        
        if isinstance(val,basestring):
            if val=="None" or val=="":
                self.val=None
                pass
            else : 
                self.val=int(val)                
                pass
            pass
        elif hasattr(val,"value"):
            # val is already a dc_value object
            self.val=val.value()
            pass
        elif val is None:
            self.val=None
            pass
        else :
            self.val=int(val);
            pass

        
        self.final=True
        pass


    def isblank(self): 
        return self.val is None

    def numvalue(self):
        return self.value();

    def value(self):
        return self.val;


    def format(self,formatstr=None):
        # NOTE: Will not operate correctly if val is None and formatstr is specified
        
        if formatstr is None:
            if self.val is None:
                return ""
            return str(self.val)
        

        # print "formatstr=%s" % (formatstr)
        # if you get a 
        # TypeError: not all arguments converted during string formatting
        # on this next line, then you probably forgot the % in the %f or %g
        # in your initialization of displayfmt in the .dcc file
        return (formatstr) % (self.val)

    def comsolstr(self):
        return str(self.val)
    
    def __str__(self) :
        if self.val is None:
            return ""

        return str(self.val)
    
    @classmethod
    def fromxml(cls,xmldocu,element,defunits=None,contextdir=None):
        # NOTE: if xml_attribute is provided, xmldocu must be also.
        if xmldocu is not None:
            provenance.xmldocelementaccessed(xmldocu,element)
            pass

        #if xml_attribute is None:
        elementtext=element.text
        #pass
        #else: 
        #    elementtext=xmldocu.getattr(element,xml_attribute,"")
        #    pass

        return cls(elementtext)


    def xmlrepr(self,xmldocu,element,defunits=None):
        # clear out any old attributes
        oldattrs=element.attrib.keys()
        for oldattr in oldattrs:
            if oldattr.startswith(DCV):
                del element.attrib[oldattr]
                pass
            pass


        #if xml_attribute is None: 
        # set text
        element.text=str(self.val)
        #    pass
        #else: 
        #    xmldocu.setattr(element,xml_attribute,str(self.val))
        #    pass
            
            
        
        if xmldocu is not None:
            xmldocu.modified=True
            provenance.elementgenerated(xmldocu.doc,element)
            pass
            
        pass
    
    
    def __eq__(self,other) :
        if self.val is None:
            return False

        assert(not hasattr(other,"units")) # don't support comparison between integervalue and numericunitsvalue at this point
        # if we want to support that later we could build off the code in numericunitsvalue

        otherval=other.value()
        return self.val==otherval


    
    def __add__(self,other):
        assert(self.val is not None)
        assert(not hasattr(other,"units")) # don't support arithmetic between integervalue and numericunitsvalue at this point
        if isinstance(other,int):
           
            return integervalue(self.val + other);
        else :
            raise ValueError("Attempting to add something other than int (%s) to dcv.integervalue " % (other.__class__.__name__))
            
        pass

    def __sub__(self,other):
        assert(self.val is not None)
        assert(not hasattr(other,"units")) # don't support arithmetic between integervalue and numericunitsvalue at this point
        if isinstance(other,int):
           
            return integervalue(self.val - other);
        else :
            raise ValueError("Attempting to subtract something other than int (%s) to dcv.integervalue " % (other.__class__.__name__))
            
        pass
    
    def __mul__(self,other):
        assert(self.val is not None)
        assert(not hasattr(other,"units")) # don't support arithmetic between integervalue and numericunitsvalue at this point
        if isinstance(other,int):
           
            return integervalue(self.val * other);
        else :
            raise ValueError("Attempting to multiply something other than int (%s) to dcv.integervalue " % (other.__class__.__name__))
            
        pass
        
    
    def __div__(self,other):
        assert(self.val is not None)
        assert(not hasattr(other,"units")) # don't support arithmetic between integervalue and numericunitsvalue at this point
        if isinstance(other,int):
           
            return integervalue(self.val // other);
        else :
            raise ValueError("Attempting to divide something other than int (%s) to dcv.integervalue " % (other.__class__.__name__))
            
        pass
    pass




class heatingvalue(numericunitsvalue) :
    pixbuf=None;
    def __init__(self,val,units=None,pixbuf=None) :
        self.pixbuf=pixbuf;
        numericunitsvalue.__init__(self,val,units); # this call finalizes the structure, so it must be last!
        pass
    
    pass

    

class excitationparamsvalue(value) : 
    type=None;
    wfm=None  # not yet fully implemented
    f0=None;
    f1=None;
    t0=None;
    t1=None;
    t2=None;
    t3=None;


    def __init__(self,string,defunits=None):
        if isinstance(string,dict):  # if we were provided with a dictionary of type, f1, f2, etc.
            paramdict=string

            #print "paramdict:", paramdict

            for key in paramdict:
                setattr(self,key,paramdict[key])
                pass
            self.final=True
            return
        elif isinstance(string,excitationparamsvalue):  # if we were provided with this class already, just copy it
            self.type=string.type
            self.f0=string.f0
            self.f1=string.f1
            self.t0=string.t0
            self.t1=string.t1
            self.t2=string.t2
            self.t3=string.t3
            
            return

        # otherwise string really should be a string. 

        # should provide string with initial GEN: removed
        sweepmatch=re.match(r"""SWEEP Arb ([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?) Hz ([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?) Hz ([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?) s ([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?) s ([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?) s ([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?) s""",string)
        if (sweepmatch is not None) :
            self.type="SWEEP"
            self.f0=float(sweepmatch.group(1));
            self.f1=float(sweepmatch.group(2));
            self.t0=float(sweepmatch.group(3));
            self.t1=float(sweepmatch.group(4));
            self.t2=float(sweepmatch.group(5));
            self.t3=float(sweepmatch.group(6));
            if self.f0==self.f1 :
                self.type="BURST";
                pass
            pass
        else :
            burstmatch=re.match(r"""BURST Arb ([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?) Hz ([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?) s ([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?) s ([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?) s ([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?) s""",string)
            if (burstmatch is not None) :
                self.type="BURST"
                self.f0=float(burstmatch.group(1));
                self.f1=self.f0;
                self.t0=float(burstmatch.group(2));
                self.t1=float(burstmatch.group(3));
                self.t2=float(burstmatch.group(4));
                self.t3=float(burstmatch.group(5));
                pass
            else : 
                self.type=None
                pass
            pass
        self.final=True

        pass
    
    
    def __str__(self) :
        # BUG: Should use repr's here instead of %g
        if self.type=="SWEEP" or self.type=="sweep":            
            return "SWEEP Arb %.2f Hz %.2f Hz %.8g s %.8g s %.8g s %.8g s" % (self.f0,self.f1,self.t0,self.t1,self.t2,self.t3)
        elif self.type=="BURST" or self.type=="burst":
            return "BURST Arb %.2f Hz %.8g s %.8g s %.8g s %.8g s" % (self.f0,self.t0,self.t1,self.t2,self.t3)
        elif self.type is not None :
            raise TypeError("Excitation type (%s) other than SWEEP or BURST" % (self.type));
        
        else:
            return ""
        pass

    
    def __eq__(self,other) :
        return type(self) is type(other) and self.type==other.type and self.f0==other.f0 and self.f1==other.f1 and self.t0==other.t0 and self.t1==other.t1 and self.t2==other.t2 and self.t3==other.t3



    @classmethod
    def fromxml(cls,xmldocu,element,defunits=None,contextdir=None):
        # NOTE: if xml_attribute must be none because of the structure used.

        #assert(xml_attribute is None)

        vals={}
        if xmldocu is not None:
            provenance.xmldocelementaccessed(xmldocu,element)
            pass

        vals["type"]=element.attrib[DCV+"exctype"]
        

        for subel in element:
            if (subel.tag != DCV+"f0" and 
                subel.tag != DCV+"f1" and
                subel.tag != DCV+"t0" and
                subel.tag != DCV+"t1" and
                subel.tag != DCV+"t2" and
                subel.tag != DCV+"t3"):
                raise ValueError("excitationparamsvalue found invalid tag: %s" % (subel.tag))
            tag=subel.tag.split(DCV)[1]
            if tag[0]=='f':
                defunits="Hz"
                pass
            else : 
                defunits="s"
                pass
            
            vals[tag]=numericunitsvalue(subel.text,units=subel.attrib[DCV+"units"],defunits=defunits).valuedefunits()
            pass
        
        return cls(vals)
    
    def xmlrepr(self,xmldocu,tag,defunits=None): # usually "excitation" tag
        
        # as this tag has subelements it cannot be stored in an xml attribute
        #assert(xml_attribute is None)

        # clear out any attributes in the dcvalue namespace
        oldattrs=tag.attrib.keys()
        for oldattr in oldattrs:
            if oldattr.startswith(DCV):
                del tag.attrib[oldattr]
                pass
            pass

        while len(tag) > 0: 
            # remove any old subelements
            tag.remove(tag[0])
            pass
        
        if self.type is not None:

            tag.attrib[DCV+"exctype"]=self.type.lower()
            
            f0el=etree.Element(DCV+"f0")
            f0el.text=str(self.f0)
            f0el.attrib[DCV+"units"]="Hz"
            tag.append(f0el)
            
            if self.type == "SWEEP":
                f1el=etree.Element(DCV+"f1")
                f1el.text=str(self.f1)
                f1el.attrib[DCV+"units"]="Hz"
                tag.append(f1el)
                pass
            
            t0el=etree.Element(DCV+"t0")
            t0el.text=str(self.t0)
            t0el.attrib[DCV+"units"]="s"
            tag.append(t0el)
            
            t1el=etree.Element(DCV+"t1")
            t1el.text=str(self.t1)
            t1el.attrib[DCV+"units"]="s"
            tag.append(t1el)
            
            t2el=etree.Element(DCV+"t2")
            t2el.text=str(self.t2)
            t2el.attrib[DCV+"units"]="s"
            tag.append(t2el)
            
            t3el=etree.Element(DCV+"t3")
            t3el.text=str(self.t3)
            t3el.attrib[DCV+"units"]="s"
            tag.append(t3el)
            pass
        else : # type is None 
            tag.attrib[DCV+"exctype"]="INVALID"
            pass
        if xmldocu is not None:
            xmldocu.modified=True
            provenance.elementgenerated(xmldocu.doc,tag)
            pass

        return
    



    pass

class photosvalue(value):
    photoset=None # actually a frozenset
    # ...  of hrefvalues

    def __init__(self,value,defunits=None):
        if isinstance(value,tuple) or isinstance(value,list) or isinstance(value,set):
            self.photoset=frozenset(copy.deepcopy(value))
            pass
        elif isinstance(value,photosvalue):
            self.photoset=copy.deepcopy(value.photoset)
            pass
        else :
            self.photoset=frozenset([])
            
            if value is not None and len(value) != 0:
                raise ValueError("photosvalue from string not yet implemented")
            pass
        pass

    def __str__(self):
        return ";".join([ os.path.split(photohref.getpath("."))[-1] for photohref in self.photoset ])

    def copyandappend(self,newphotohref):
        tmp=set(self.photoset)
        tmp.add(newphotohref)
        return photosvalue(tmp)

    def isblank(self):
        return len(self.photoset)==0
    
    
    @classmethod
    def fromxml(cls,xmldocu,element,defunits=None,contextdir=None):
        # NOTE: Does not currently handle context directories in a meaningful way (ignores them; assumes everything ends up in dest)
        #assert(xml_attribute=="xlink:href")
        if xmldocu is not None:
            provenance.xmldocelementaccessed(xmldocu,element)
            pass
        tmp=set([])
        for subel in element:
            if subel.tag != DCV+"photo":
                raise ValueError("Photosvalue found non-dcv:photo tag: %s" % (subel.tag))
            tmp.add(hrefvalue.fromxml(xmldocu,subel))
            
            pass
        
        return cls(tmp)
    
    def xmlrepr(self,xmldocu,tag,defunits=None):
        # as this tag has subelements it cannot be stored in an xml attribute
        #assert(xml_attribute=="xlink:href")

        # clear out any attributes in the dcvalue namespace
        oldattrs=tag.attrib.keys()
        for oldattr in oldattrs:
            if oldattr.startswith(DCV):
                del tag.attrib[oldattr]
                pass
            pass

        while len(tag) > 0: 
            # remove any old subelements
            tag.remove(tag[0])
            pass
        
        for photohref in self.photoset:
            newel=etree.Element(DCV+"photo")
            photohref.xmlrepr(xmldocu,newel)
            tag.append(newel)
            pass
        if xmldocu is not None:
            xmldocu.modified=True
            provenance.elementgenerated(xmldocu.doc,tag)
            pass
            
        return

    @classmethod
    def merge(cls,parent,descendentlist,contextdir=None,maxmergedepth=np.Inf,tag_index_paths_override=None):
        added=set([])
        removed=set([])
        if parent is not None:
            parentset=frozenset(parent.photoset)
            pass
        else:
            parentset=frozenset([])
            pass
        
        # ... for all descendents...
        for descendent in descendentlist:
            # find all photos that were added in this descendent
            # and all those that were removed in this descendent
            #sys.stderr.write("parentset=%s; descendent=%s\n" % (str(parentset),str(descendent)))
            added.update(descendent.photoset.difference(parentset))
            removed.update(parentset.difference(descendent.photoset))
            pass

        # if a photo was both added and removed, that is an error
        if len(added.intersection(removed)) > 0:
            raise MergeError("Error in merge: Photos %s were added in one descendent and removed in another descendent" % (str(added.intersection(removed)))) 

        return cls(parentset.difference(removed).union(added))

    def __eq__(self,other):
        return self.photoset==other.photoset
    
    pass

class datesetvalue(value):
    # represents a set of dates, separated by semicolons
    dateset=None
    
    def __init__(self,param,defunits=None):
        self.dateset=set([])
        if isinstance(param,collections.Set):
            self.dateset=set(param)
            pass
        elif isinstance(param,basestring):
            self.dateset=self.parsedates(param)
            pass
        elif isinstance(param,datetime.date):
            self.dateset=set([param])
            pass
        elif isinstance(param,datetime.datetime):
            self.dateset=set([param.date()])
            pass
        elif param is None:
            self.dateset=set([])
            pass
        elif isinstance(param,datesetvalue):
            self.dateset=set(param.dateset)
            pass
        else : 
            raise ValueError("Unknown parameter type: %s for value %s\n" % (param.__class__.__name__,str(param)))
        self.final=True
        pass

    def parsedates(self,datesstr):
        # interpret both semicolon-delimited and comma-delimited
        if ";" in datesstr: 
            dates=datesstr.split(";")
            pass
        elif "," in datesstr:
            dates=datesstr.split(",")
            pass
        else: 
            dates=[datesstr]
            pass
        
        datesstrip=[date.strip() for date in dates]

        datesparsed=set([self.parsedate(date) for date in datesstrip if len(date) > 0])
        # sys.stderr.write("dates=%s datesparsed=%s\n" % (str(dates),str(datesparsed)))
        return datesparsed


    def parsedate(self,datestr):
        # sys.stderr.write("datestr=%s\n" % (datestr))
        return datetime.datetime.strptime(datestr,"%Y-%m-%d").date()
                        

    def union(self,other):
        # sys.stderr.write("Union(%s,%s)\n" % (str(self.dateset),str(other.dateset)))
        newset=self.dateset.union(other.dateset)
        return datesetvalue(newset)

    def __str__(self):
        sorteddates=[str(dateentry) for dateentry in self.dateset]
        sorteddates.sort()
        # sys.stderr.write("dateset=%s\n" % (str(self.dateset)))
        # sys.stderr.write("sorteddates=%s\n" % (sorteddates))
        return ",".join(sorteddates)
        
    @classmethod
    def fromxml(cls,xmldocu,element,defunits=None,contextdir=None):
        # NOTE: if xml_attribute is provided, xmldocu must be also.

        #if xml_attribute is None:
        elementtext=element.text
        #    pass
        #else: 
        #    elementtext=xmldocu.getattr(element,xml_attribute,"")
        #    pass

        if xmldocu is not None:
            provenance.xmldocelementaccessed(xmldocu,element)
            pass
        return cls(elementtext)
    
    def xmlrepr(self,xmldocu,element,defunits=None):
        #if xml_attribute is None: 
        # set text
        element.text=str(self)
        #pass
        #else: 
        #    xmldocu.setattr(element,xml_attribute,str(self))
        #    pass

        if xmldocu is not None:
            xmldocu.modified=True
            provenance.elementgenerated(xmldocu.doc,element)
            pass

        pass

    def isblank(self):
        return len(self.dateset) == 0


    def __eq__(self,other) :
        return self.dateset==other.dateset
        
    def __contains__(self,other):
        return self.dateset >= other.dateset
    pass

class accumulatingdatesetvalue(datesetvalue):
    # derived class of datesetvalue
    # which overrides merge so that merged dates
    # accumulate (union) together
    
    def __init__(self,*args,**kwargs):
        #sys.stderr.write("adsv: %s %s\n" % (str(args),str(kwargs)))
        super(accumulatingdatesetvalue,self).__init__(*args,**kwargs)
        pass
    
    @classmethod
    def merge(cls,parent,descendentlist,contextdir=None):
        # merge them together
        accum=set([])
        if parent is not None:
            accum=accum.union(parent.dateset)
            pass

        for descendent in descendentlist:
            accum=accum.union(descendent.dateset)
            pass
        return cls(accum)




class integersetvalue(value) :
    setval=None  #!!! private

    # val may be None
    
        
    def __init__(self,val,defunits=None) :
        # self.name=name;

        
        if isinstance(val,basestring):
            if val=="None" or val=="":
                self.setval=None
                pass
            else : 
                if ";" in val:
                    self.setval = set([int(valuecomponent) for valuecomponent in val.split(";")])
                    pass
                elif "," in val: 
                    self.setval = set([int(valuecomponent) for valuecomponent in val.split(",")])                    
                    pass
                else : 
                    self.setval=set([int(val)])
                    pass
                pass
                
            pass
        elif isinstance(val,collections.Set):
            self.setval=set(val)
            pass
        elif isinstance(val,list):
            self.setval=set(val)
            pass
        elif hasattr(val,"value"):
            # val is already a dc_value object
            self.setval=set(copy.copy(val.value()))
            pass
        elif val is None:
            self.setval=None
            pass
        else :
            self.setval=set([int(val)]);
            pass

        
        self.final=True
        pass


    def isblank(self): 
        return self.setval is None or len(self.setval)==0

    def value(self):
        if self.setval is None:
            return set([])
        return copy.copy(self.setval);
        


    def __str__(self) :
        if self.setval is None: 
            return ""

        # print out in sorted order
        setlist=list(self.setval)
        setlist.sort()
        
        return ",".join([str(intv) for intv in setlist])  # convert each element to a string, then join them with semicolons

        
    
    @classmethod
    def fromxml(cls,xmldocu,element,defunits=None,contextdir=None):
        # NOTE: if xml_attribute is provided, xmldocu must be also.
        if xmldocu is not None:
            provenance.xmldocelementaccessed(xmldocu,element)
            pass

        #if xml_attribute is None:
        elementtext=element.text
        #    pass
        #else: 
        #    elementtext=xmldocu.getattr(element,xml_attribute,"")
        #    pass

        return cls(elementtext)


    def xmlrepr(self,xmldocu,element,defunits=None):
        # clear out any old attributes
        oldattrs=element.attrib.keys()
        for oldattr in oldattrs:
            if oldattr.startswith(DCV):
                del element.attrib[oldattr]
                pass
            pass

            
        #if xml_attribute is None: 
        # set text
        element.text=str(self)
        #pass
        #else: 
        #    xmldocu.setattr(element,xml_attribute,str(self))
        #    pass
            
        
        if xmldocu is not None:
            xmldocu.modified=True
            provenance.elementgenerated(xmldocu.doc,element)
            pass
            
        pass
    
    
    def __eq__(self,other) :
        if self.setval is None:
            return False

        assert(not hasattr(other,"units")) # don't support comparison between integervalue and numericunitsvalue at this point
        # if we want to support that later we could build off the code in numericunitsvalue

        otherval=other.value()
        return self.setval==otherval


    def union(self,other):
        # sys.stderr.write("Union(%s,%s)\n" % (str(self.dateset),str(other.dateset)))
        newset=self.setval.union(other.setval)
        return integersetvalue(newset)

    def __contains__(self,other):
        if hasattr(other,"setval"): # integersetvalue
            return self.setval >= other.setval
        elif isinstance(other,numbers.Number): # raw number
            return other in self.setval
        elif hasattr(other,"value"): # integervalue
            return other.value() in self.value 
        else:
            raise ValueError("Cannot determine whether %s is a subset" % (str(other)))
        pass
    pass




class accumulatingintegersetvalue(integersetvalue):
    # !!! NOT CURRENTLY USED !!!
    # derived class of datesetvalue
    # which overrides merge so that merged dates
    # accumulate (union) together
    
    def __init__(self,*args,**kwargs):
        #sys.stderr.write("adsv: %s %s\n" % (str(args),str(kwargs)))
        super(accumulatingintegersetvalue,self).__init__(*args,**kwargs)
        pass
    
    @classmethod
    def merge(cls,parent,descendentlist,contextdir=None):
        # merge them together
        accum=set([])
        if parent is not None and parent.setval is not None:
            accum=accum.union(parent.setval)
            pass

        for descendent in descendentlist:
            if descendent.setval is not None:
                accum=accum.union(descendent.setval)
                pass
            pass
        return cls(accum)

    pass
# This class is for matrices that may be read/written from XML files
# it is not intended for particularly large matrices. 
class arrayvalue(value):
    array=None  # Numpy array
    
    def __init__(self,array,defunits=None):
        self.array=copy.copy(array)
        pass
    
    def __str__(self):
        return str(self.array)

    def xmlrepr(self,xmldocu,element,defunits=None):
        oldattrs=element.attrib.keys()
        for oldattr in oldattrs:
            if oldattr.startswith(DCV):
                del element.attrib[oldattr]
                pass
            pass
        oldchildren=element.getchildren()
        for child in oldchildren:
            element.remove(child)
            pass
        
        element.attrib[DCV+"arraystorageorder"]='C'
        
        nrows_element=etree.Element(DCV+"arrayshape")
        nrows_element.text=" ".join([str(axislen) for axislen in self.array.shape])
        element.append(nrows_element)
        data_element=etree.Element(DCV+"arraydata")
        data_element.text=" ".join(["%15.15g" % (arrayval) for arrayval in self.array.ravel(order="C")])
        element.append(data_element)

        xmldocu.modified=True
        provenance.elementgenerated(xmldocu.doc,element)
        
        pass
    
    @classmethod
    def fromxml(cls,xmldocu,element,defunits=None):
        if xmldocu is not None:
            provenance.xmldocelementaccessed(xmldocu,element)
            pass
        
        arraystorageorder=element.attrib[DCV+"arraystorageorder"]
        shapeel=element.find(DCV+"arrayshape")
        shape=[int(axislen) for axislen in shapeel.text.split()]
        
        data_element=element.find(DCV+"arraydata")
        data=[float(dataval) for dataval in data_element.text.split()]

        array=np.array(data,dtype='d').reshape(*shape)
        return cls(array)
    pass

    def isblank(self):
        if np.prod(self.array.shape)==0:
            return True
        return False
    
    def value(self):
        return copy.copy(self.array)

    def __eq__(self,other):
        if isinstance(other,arrayvalue):
            return self.array==other.array
        else:
            return self.array==other
        pass

    pass


    
    
