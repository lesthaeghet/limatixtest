import sys
import os
import os.path
import glob
import stat
import re
import string
import numbers
import inspect
import traceback
import dc_value as dcv
from datacollect2.dc_value import hrefvalue

try: 
    from collections.abc import Sequence  # moved to collections.abc in numpy 3.4(?)
    pass
except ImportError:
    from collections import Sequence
    pass

import dg_timestamp

from lxml import etree 

import xmldoc 
import dc_provenance

import numpy


__pychecker__="no-import"


class xmlfilterparams(object):
    nsmap=None
    WriteEnable=None
    Provenance=None
    use_databrowse=None
    debug=None

    def __init__(self,nsmap=None,WriteEnable=False,Provenance=True,use_databrowse=False,debug=False):
        self.nsmap=nsmap
        self.WriteEnable=WriteEnable
        self.Provenance=Provenance
        self.use_databrowse=use_databrowse
        self.debug=debug
        pass
    
    
    pass



def countresults(resultlist):
    if resultlist is None:
        return 0
    
    
    count=0
    for (doc,elements) in resultlist: 
        count += len(elements)
        pass
    
    return count


def filelistrecurse(name,use_databrowse):
    filelist=[];
    
    mode=os.lstat(name)[stat.ST_MODE];
    if stat.S_ISDIR(mode) and not use_databrowse:
        # recurse into directory

        # print name
        dirlist=os.listdir(name);
        for entry in dirlist :
            # print os.path.join(name,entry)
            if not entry.startswith("."): # ignore hidden
                filelist.extend(filelistrecurse(os.path.join(name,entry),use_databrowse));
                pass
            pass
        pass
    elif name.endswith("~") :
        # emacs backup... ignore
        pass
    elif name.endswith("#") :
        # emacs autosave ignore
        pass
    elif name.startswith("~") :
        # emacs backup... ignore
        pass
    elif name.endswith(".bak") :
        # backup... ignore
        pass
    elif name.endswith(".old") :
        # backup... ignore
        pass
    else :
        filelist.append(name);
        pass
    
    return filelist;


def openxmldoc(filename,nsmap=None,use_databrowse=False):
    filenamehref=hrefvalue(filename)
    doc = xmldoc.xmldoc(filenamehref,maintagname=None,nsmap=nsmap,readonly=True,use_databrowse=use_databrowse)
    return doc


def createfilelist(source,use_databrowse) :
    if isinstance(source,basestring):
        # wrap a bare filename in a list
        source=[source];
        pass

    dest=[];
    
    for name in source :
        if isinstance(name,basestring):
            dest.extend(glob.glob(name))
            pass
        else :
            dest.append(name);
            pass
        pass

    dest2=[]
    for name in dest :
        if isinstance(name,basestring): 
            dest2.extend(filelistrecurse(name,use_databrowse));
            pass
        else :
            dest2.append(name);
            pass

        pass
    
    
    return dest2


def dc_xmlfilterinplace(source,xpath,filterparams,filterfunc,*filterfuncargs,**filterfunckwargs) :
    # source may be a filename, or a list of filenames.
    # filenames not ending in .xml will be filtered out
    # if a directory is included that directory will be recursively searched for xml files. 

    # xpath selects which elements to apply the filter to
    # filterparams is an xmlfilterparams instance, or None to get the defaults

    # function is called with the filename, followed by the element followed by the specified functionargs
    # for each element found. Once a file is finished the XML as modified will be written to disk. 

    if filterparams is None:
        filterparams=xmlfilterparams()
        pass
    
    if not filterparams.WriteEnable: 
        print("dc_xmlfilterinplace: XML file writing is disabled (?)")
        pass

    sourcelist=createfilelist(source,filterparams.use_databrowse);
    # print sourcelist

    for filename in sourcelist :
        assert(isinstance(filename,basestring))
 
        
        
        dc_xmlfilter(filename,filename,xpath,filterparams,filterfunc,*filterfuncargs,**filterfunckwargs);
        
        
    pass


def dc_xmlfilter(filename,dest,xpath,filterparams,filterfunc,*filterfuncargs,**filterfunckwargs) :
    # filename is the source filename, .
    # dest is the destination filename or None
    # filterparams is an xmlfilterparams instance, or None to get the defaults

    # WritEnable enables writing to dest
    # Provenance, if None or False, disables provenance generation/updating
    # Provenance, if True, enables provenance generation with default and automatic values
    # Provenance, if a provenance structure, provides overriding values

    # xpath selects which elements to apply the filter to

    # filterfunc is called with the xmlgrab reference to the document, followed by the xmlgrab reference to the element, followed by the xmldoc object, followed by the etree element followed by the specified functionargs
    # for each element found. Once a file is finished the XML as modified will be written to disk. 
    # filterfunc should return the text contents that should go into
    # the "dc:processessinglog" tag.
    # print filename

    if filterparams is None:
        filterparams=xmlfilterparams()
        pass

    oldprovenance=None
    processguid=None

    inputfileinfo=os.stat(filename)


    doc=openxmldoc(filename,filterparams.nsmap,filterparams.use_databrowse)
    

    # extract provenance at start, if desired
    # if provenance use is specified (i.e. not None and not False)...
    if filterparams.Provenance is not None and not(isinstance(filterparams.Provenance,bool) and not filterparams.Provenance):
        oldprovenance=dc_xmlgrab([(doc,[doc.getroot()])],"dcp:provenance")
        if countresults(oldprovenance) > 0:
            assert(countresults(oldprovenance)==1)  # only one root dcp:provenance tag allowed!
            oldprovenance=oldprovenance[0][1][0]  # get first and only provenance element off of list
            pass
        else : 
            oldprovenance=None
            pass
        
        if isinstance(filterparams.Provenance,bool):
            # no provenance provided... create one
            filterparams.Provenance=dc_provenance.provenance()
            pass
        
        if filterparams.Provenance.wasderivedfrom is None:
            filterparams.Provenance.wasderivedfrom=dc_provenance.prov_wasderivedfrom.fromfileinfo(filename,None,inputfileinfo,oldprovenance)
            pass
        
        if filterparams.Provenance.wasgeneratedby is None:
            if "__main__" in sys.modules and hasattr(sys.modules["__main__"],"__file__"):
                sourcefile=inspect.getsourcefile(sys.modules["__main__"])
                sourcefileinfo=os.stat(sourcefile)
                filterparams.Provenance.wasgeneratedby=dc_provenance.prov_wasgeneratedby.fromfileinfo(sourcefile,None,sourcefileinfo)
                pass
            pass
        
        # Provenance.wastriggeredby cannot be filled out automatically -- must be provided! 
        
        # Provenance.wascontrolledby -- must be pre-filled if we want to have perfby
        if filterparams.Provenance.wascontrolledby is None:
            filterparams.Provenance.wascontrolledby=dc_provenance.prov_wascontrolledby.fromnow()
            pass
        
        pass

    if filterparams.Provenance is not None and filterparams.Provenance.wascontrolledby is not None:
        processguid=filterparams.Provenance.wascontrolledby.processguid
        pass

    # extract list of desired elements
    ellist = doc.xpath(xpath);
    
    # must be a node-set
    if not isinstance(ellist,Sequence) or isinstance(ellist,basestring):
        raise ValueError("dc_xmlfilter: xpath must map to a node-set")
    
    if (filterparams.WriteEnable) :
        # strip .xml of of file name
        # targetbase=re.match(r"""(.*)\.xml""",dest).group(1);
        targetbase=os.path.splitext(dest)[0]
  
        # rename old xml file
        if os.path.exists(dest):
            try :
                os.rename(dest,targetbase+".bak");
                pass
            except :
                print ("Error renaming %s to %s" % (dest,targetbase+".bak"))
                raise
            pass
        pass
    
    if filterparams.WriteEnable:
        doc.setfilename(dest)
        pass
    
    # filter each desired element
    for el in ellist :
        try : 
            (logstatus,logtext)=filterfunc([(doc,[doc.getroot()])],[(doc,[el])],doc,el,*filterfuncargs,**filterfunckwargs);
            pass
        except : 
            logstatus="exception"
            (exctype,excvalue)=sys.exc_info()[:2]
            logtext="Exception %s %s\n\nTraceback:\n%s\n" % (
                str(exctype.__name__),str(excvalue),traceback.format_exc())

            if filterparams.debug and sys.stdin.isatty() and sys.stderr.isatty():
                # automatically start the debugger from an exception in debug mode (if stdin and stderr are ttys) 
                sys.stderr.write(logtext)
                
                import pdb  # Note: Should we consider downloading/installing ipdb (ipython support for pdb)???
                # run debugger in post-mortem mode. 
                pdb.post_mortem()

                pass
            pass

        # add log entry
        processinglogtag=doc.addelement(el,"dc:processinglog")
        processinglogtag.attrib["timestamp"]=dg_timestamp.now().isoformat()
        processinglogtag.attrib["status"]=unicode(logstatus)
        processinglogtag.text=unicode(logtext)
        processinglogtag.attrib["script"]=os.path.split(sys.argv[0])[1]
        if processguid is not None:
            processinglogtag.attrib["processguid"]=processguid 
            pass
        
        if filterparams.WriteEnable:            
            doc.flush()
            pass
        
        pass

    # add provenance
    
 
    # if provenance use is specified (i.e. not None and not False)
    if filterparams.Provenance is not None and not(isinstance(filterparams.Provenance,bool) and not filterparams.Provenance):
        # Add endtime if not provided
        if filterparams.Provenance.wascontrolledby.endtime is None:
            filterparams.Provenance.wascontrolledby.tonow()
            pass
        
        if oldprovenance is not None:
            oldprovenance.getparent().remove(oldprovenance)  # remove old element from document
            pass
        
        doc.getroot().append(filterparams.Provenance.toxml()) # add new element to document
        pass
    
    if filterparams.WriteEnable:
        doc.flush()
        pass
    
    return doc




def dc_xmlgrab(source,xpath,nsmap=None,use_databrowse=False) :
    # Grab data from source, according to xpath.
    # Source may be a single filename, list of filenames, or list of (xmldoc,elementlist) tuples.
    # Automatically applies globbing on files and recursion into directories.     # Results are returned as a [list of (xmldoc,[element list]) tuples]
    
    sourcelist=createfilelist(source,use_databrowse);
    # print sourcelist

    resultlist=[]
    for element in sourcelist:
        if isinstance(element,basestring):
            # a filename!
            doc=openxmldoc(element,nsmap,use_databrowse)
            
            xpathres=doc.xpath(xpath)
            if isinstance(xpathres,Sequence) and not isinstance(xpathres,basestring):
                # got list result
                if len(xpathres) > 0:
                    resultlist.append((doc,xpathres))
                    pass
                pass
            elif xpathres is not None : 
                resultlist.append((doc,[xpathres]))
                pass
        else :
            (doc,elems)=element
            sublist=[]
            for elem in elems:
                xpathres=doc.xpath(xpath,contextnode=elem)
                if isinstance(xpathres,Sequence) and not isinstance(xpathres,basestring):
                    # got list result    
                    sublist.extend(xpathres)
                    pass
                elif xpathres is not None: 
                    sublist.append(xpathres)
                    pass
                
                pass
            if len(sublist) > 0:
                resultlist.append((doc,sublist))
                pass
            pass
        
        pass
    
    return resultlist;

def dc_xmlgrabsingle(source,xpath,nsmap=None,use_databrowse=False):
    # returns either: 
    #   * None if no result found
    #   * a single result, suitable for passing to dc_xmlgrab
    #   * Otherwise raises ValueError

    results=dc_xmlgrab(source,xpath,nsmap=nsmap,use_databrowse=use_databrowse)
    numresults=countresults(results)
    if numresults > 1:
        raise ValueError("xmlgrabsingle got %d results" % (numresults))
    elif numresults==0:
        return None
    return results


def dc_xml2numpy(source,xpath,nsmap=None,oneper=True,use_databrowse=False) :
    # Grab data from source, according to xpath, returning a double-precision numpy array
    # if oneper is true, then exactly one result in the output array is expected per 
    # element of source. ValueError will be raised if there is more than one result
    # and a NaN will be inserted if there is lest than one result. (Note that if source
    # contains filenames/directories/globbing, the per-element applies post-directory recursion
    # and post-globbing.
    # if oneper is false, then any number of return entries can come from each source entry. 

    if oneper:
        sourcelist=createfilelist(source,use_databrowse);
        resultlist=[];
        for sourceentry in sourcelist:
            if isinstance(sourceentry,basestring):
                # a filename!

                doc=openxmldoc(sourceentry,nsmap,use_databrowse)
                elements=[None]
                pass
            else :
                (doc,elements)=sourceentry
                pass
            sublist=[]
            
            for element in elements :
                ((doc2,addelements),)=dc_xmlgrab([(doc,(element,))],xpath);
                assert(doc2 is doc)
                if len(addelements) > 1:
                    raise ValueError("dc_xml2numpy: %d results from %s on %s (try oneper=False?)" % (len(addelements),xpath,unicode(sourceentry)))
                if len(addelements)==0:
                    # create dummy element with NaN
                    newnode=etree.Element("__xmlgrab_dummy_NaN_element");
                    newnode.text="NaN"
                    
                    addelements.append(newnode)
                    pass
                sublist.extend(addelements)
                pass
            if len(sublist) > 0:
                resultlist.append((doc,sublist))
                pass
            
            pass
        pass
    else :
        resultlist=dc_xmlgrab(source,xpath);
        pass
    
    resultarray=numpy.zeros(countresults(resultlist),dtype='d');
    
    cnt=0
    for (doc,elements) in resultlist:
        for element in elements: 
            #print "doc=",doc
            #print "element=", element
            if isinstance(element,basestring) or isinstance(element,numbers.Number): # string, numeric, or boolean
                resultarray[cnt]=float(element)
                pass
            else : 
                # should be bare element
                resultarray[cnt]=float(element.text)
                pass
            cnt += 1
            pass
        
        pass
    
    return resultarray




def dc_xml2numpyint(source,xpath,nsmap=None,oneper=True,use_databrowse=False) :

    if oneper:
        sourcelist=createfilelist(source,use_databrowse);
        resultlist=[];
        for sourceentry in sourcelist:
            if isinstance(sourceentry,basestring):
                # a filename!
                doc=openxmldoc(sourceentry,nsmap,use_databrowse)
                elements=[None]
                pass
            else :
                (doc,elements)=sourceentry
                pass
            
            sublist=[]
            for element in elements:
                ((doc2,addelements),)=dc_xmlgrab([(doc,(element,))],xpath);
                assert(doc2 is doc)
                if len(addelements) > 1:
                    raise ValueError("dc_xml2numpyint: %d results from %s on %s  (try oneper=False?)" % (len(addelements),xpath,unicode(sourceentry)))
                if len(addelements)==0:
                    raise ValueError("dc_xml2numpyint: Path %s not found in element #%d (%s)",xpath,len(resultlist),str(addelements));
                sublist.extend(addelements)
                pass
            if len(sublist) > 0:
                resultlist.append((doc,sublist));
                pass
            pass
        pass
    else :
        resultlist=dc_xmlgrab(source,xpath);
        pass
        
    resultarray=numpy.zeros(countresults(resultlist),dtype='i');
    
    cnt=0
    for (doc,elements) in resultlist:
        for element in elements: 
            if isinstance(element,basestring) or isinstance(element,numbers.Number): # string, numeric, or boolean
                resultarray[cnt]=int(element)
                pass
            else : 
                # should be bare element
                resultarray[cnt]=int(element.text)
                pass
            cnt += 1
            pass
        
        pass
    
    return resultarray


def dc_xml2numpystr(source,xpath,nsmap=None,oneper=True,use_databrowse=False) :
    if oneper:
        sourcelist=createfilelist(source,use_databrowse);
        resultlist=[];

        for sourceentry in sourcelist:
            if isinstance(sourceentry,basestring):
                # a filename!
                doc=openxmldoc(sourceentry,nsmap,use_databrowse)
                elements=[None]
                pass
            else :
                (doc,elements)=sourceentry
                pass

            sublist=[]
            for element in elements:
                ((doc2,addelements),)=dc_xmlgrab([(doc,(element,))],xpath);
                assert(doc2 is doc)
                if len(addelements) > 1:
                    raise ValueError("dc_xml2numpystr: %d results from %s on %s (try oneper=False?)" % (len(addelements),xpath,unicode(sourceentry)))
                if len(addelements)==0:
                    # create dummy element with empty string
                    newnode=etree.Element("__xmlgrab_dummy_blank_element");
                    newnode.text="";
                    addelements.append(newnode);
                    pass
                sublist.extend(addelements)
                pass
            if len(sublist) > 0:
                resultlist.append((doc,sublist));
                pass
            pass
        
        pass
    else :
        resultlist=dc_xmlgrab(source,xpath);
        pass

    resultarray=numpy.zeros(countresults(resultlist),dtype='O');
    
    cnt=0
    for (doc,elements) in resultlist:
        for element in elements: 
            if isinstance(element,basestring) or isinstance(element,numbers.Number) : # string, numeric, or boolean
                resultarray[cnt]=unicode(element) # convert to string
                pass
            else: 
                # should be bare element
                # print "element=",element
                resultarray[cnt]=element.text
                pass
            cnt += 1
            pass
        
        pass
    return resultarray

def dc_xml2float(source,xpath) :
    resultlist=dc_xmlgrab(source,xpath);
    if len(resultlist)==1 and len(resultlist[0][1])==1:
        result=resultlist[0][1][0]
        if isinstance(result,basestring) or isinstance(result,numbers.Number): # string, numeric, or boolean
            return float(resultlist[0][1][0])
        else :
            return float(resultlist[0][1][0].text)
        pass
    else :
        raise ValueError("dc_xml2float: %d results from %s" % (countresults(resultlist),str(resultlist)));
    pass

def dc_xml2int(source,xpath) :
    resultlist=dc_xmlgrab(source,xpath);
    if len(resultlist)==1 and len(resultlist[0][1])==1:
        result=resultlist[0][1][0]
        if isinstance(result,basestring) or isinstance(result,numbers.Number): # string, numeric, or boolean
            return int(resultlist[0][1][0])
        else :
            return int(resultlist[0][1][0].text)
        pass
    else :
        raise ValueError("dc_xml2int: %d results from %s" % (countresults(resultlist),str(resultlist)));
    pass


def dc_xml2strlist(source,xpath) :
    resultlist=dc_xmlgrab(source,xpath);
    resultstrlist=[];
    for (doc,elements) in resultlist :
        for element in elements:
            if isinstance(element,basestring) or isinstance(element,numbers.Number): # string, numeric, or boolean
                resultstrlist.append(unicode(element))
                pass
            else : # regular element
                resultstrlist.append(element.text)
                pass
            pass
        pass
    return resultstrlist

def dc_xml2str(source,xpath) :
    resultlist=dc_xmlgrab(source,xpath);
    # print "Resultlist=%s" % (str(resultlist))
    if len(resultlist)==1 and len(resultlist[0][1])==1:
        result=resultlist[0][1][0]
        if isinstance(result,basestring) or isinstance(result,numbers.Number): # string, numeric, or boolean
            return unicode(resultlist[0][1][0])
        else :
            return unicode(resultlist[0][1][0].text)
        pass
    elif len(resultlist)==0:
        return u"";
    else :
        raise ValueError("dc_xml2str: %d results from %s" % (countresults(resultlist),str(resultlist)));
    pass



def dc_xml2ellist(source,xpath) :
    resultlist=dc_xmlgrab(source,xpath);
    resultellist=[];
    for (doc,elements) in resultlist :
        for element in elements:
            resultellist.append(element)
            pass
        pass
    return resultellist

def dc_xml2el(source,xpath) :
    
    resultellist=dc_xml2ellist(source,xpath) 
    if len(resultellist)==1:
        return resultellist[0]
    else : 
        raise ValueError("dc_xml2el: %d results from %s" % (len(resultellist),str(xpath)))

    pass

def dc_xml2nuv(source,xpath,units=None) :    
    resultel=dc_xml2el(source,xpath) 


    if units is None:
        return dcv.numericunitsvalue.fromxml(resultel)
    else :
        return dcv.numericunitsvalue.fromxml(resultel).inunits(units)
    

    pass
