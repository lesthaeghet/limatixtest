from __future__ import print_function

import sys
import os
import os.path
import posixpath
import socket
import copy
import inspect
import numbers
import traceback
import collections
import ast
import hashlib
import binascii
import datetime

from lxml import etree

try:
    from cStringIO import StringIO
    pass
except ImportError:
    from io import StringIO
    pass


import shutil
import datetime
import subprocess

try:
    # py2.x
    from urllib import pathname2url
    from urllib import url2pathname
    from urllib import quote
    from urllib import unquote
    from urlparse import urlparse
    from urlparse import urlunparse
    from urlparse import urljoin    
    pass
except ImportError:
    # py3.x
    from urllib.request import pathname2url
    from urllib.request import url2pathname
    from urllib.parse import quote
    from urllib.parse import unquote
    from urllib.parse import urlparse
    from urllib.parse import urlunparse
    from urllib.parse import urljoin
    pass

# import lm_units

import timestamp
from . import canonicalize_path
from .canonicalize_path import etxpath2human

from . import dc_value as dcv
from . import provenance as provenance
from . import xmldoc
from . import processtrak_prxdoc
from . import timestamp as lm_timestamp



try:
    from pkg_resources import resource_string
    pass
except TypeError:
    # mask lack of pkg_resources when we are running under pychecker
    def resource_string(x,y):
        raise IOError("Could not import pkg_resources")
    pass


try: 
    __install_prefix__=resource_string(__name__, 'install_prefix.txt').decode('utf-8')
    pass
except IOError: 
    sys.stderr.write("processtrak: error reading install_prefix.txt. Assuming /usr/local.\n")
    __install_prefix__="/usr/local"
    pass

xsltpath=[os.path.join(__install_prefix__,"share","limatix","xslt")]



outputnsmap={
    "lip": "http://limatix.org/provenance",
}


prx_nsmap={
    "prx": "http://limatix.org/processtrak/processinginstructions",
    "dc": "http://limatix.org/datacollect",
    "dcv": "http://limatix.org/dcvalue",
    "xlink": "http://www.w3.org/1999/xlink",
};


xmlNameStartCharNums = (range(65,91) +    # From XML Spec
                        [95] +
                        range(97,123) +
                        range(0xC0,0xD7) +
                        range(0xD8,0xF7) +
                        range(0xF8,0x300) +
                        range(0x370,0x37E) +
                        range(0x37F,0x2000) +
                        range(0x200C,0x200E) +
                        range(0x2070,0x2190) +
                        range(0x2C00,0x2ff0) +
                        range(0x3001,0xD800) +
                        range(0xF900,0xFDD0) +
                        range(0xFDF0,0xFFFE) +
                        range(0x10000,0xF0000))
xmlNameCharNums = (xmlNameStartCharNums +
                   [ 45, 46 ] +
                   range(48,58) +
                   [ 0xB7 ] +
                   range(0x300,0x370) +
                   range(0x2040,2041))
                        
xmlNameStartCharSet = set( [ unichr(num) for num in xmlNameStartCharNums ] )
xmlNameCharSet = set( [ unichr(num) for num in xmlNameCharNums ] )


def convert_to_tagname(rawname):
    out=""

    if rawname is None or len(rawname)==0:
        return None
    
    if rawname[0] in xmlNameStartCharSet:
        out+=rawname[0]
        pass
    else:
        out+='_'
        pass
    
    for c in rawname[1:]:
        if c in xmlNameCharSet:
            out+=c
            pass
        else:
            out+='_'
            pass
        pass
    
    return out


def splitunits(titlestr):
    # attempt to split off trailing units in parentheses
    # allow nested parentheses
    titlestr=titlestr.strip()
    units=[]
    if (titlestr.endswith(')')):
        parencnt=1
        for pos in range(len(titlestr)-2,0,-1):
            if titlestr[pos]==')':
                parencnt+=1
                pass
            elif titlestr[pos]=='(':
                parencnt-=1
                if parencnt==0:
                    break
                pass            
            units.insert(0,titlestr[pos])
            pass

        if parencnt != 0:
            # failed
            return (titlestr,None)
        unitstr="".join(units)
        titlestr=titlestr[:pos].strip()
        return (titlestr,unitstr)
    return (titlestr,None)

def find_xslt_in_path(contexthref,xsltname):
    #if os.path.exists(os.path.join(contexthref.getpath(),scriptname)):
    #    print("WARNING: direct paths to scripts should be specified with <script xlink:href=\"...\"/>. Use the name=\"...\" attribute only for scripts to be found in the script search path")
    #    pass
    
    #if posixpath.isabs(scriptname):
    #    return dcv.hrefvalue(quote(scriptname),contexthref=dcv.hrefvalue("./"))
    #
    #if posixpath.pathsep in scriptname:
    #    return dcv.hrefvalue(quote(scriptname),contexthref=contexthref)

    for trypath in xsltpath:
        if trypath==".":
            trypath=contexthref.getpath()
            pass
        
        if os.path.exists(os.path.join(trypath,url2pathname(xsltname))):
            return dcv.hrefvalue(quote(xsltname),contexthref=dcv.hrefvalue(pathname2url(trypath)+"/"))
        pass
    
    raise IOError("Could not find xslt transform %s in path %s" % (xsltname,unicode(xsltpath)))


def create_outputfile(prxdoc,inputfilehref,outputfilehref,outputdict):
    
    # print("inputfilehref=%s" % (inputfilehref.humanurl()))
    if inputfilehref.has_fragment():
        # input file url has a fragment... we're only supposed
        # to extract a portion of the file

        timestamp=datetime.datetime.fromtimestamp(os.path.getmtime(inputfilehref.getpath()),lm_timestamp.UTC()).isoformat()

        if inputfilehref.fragless()==prxdoc.get_filehref():
            inputfilecontent=prxdoc  # special case where input file is .prx file
            pass
        else: 
            inputfilecontent=xmldoc.xmldoc.loadfile(inputfilehref.getpath())
            pass
        
        inputfileportion=inputfilehref.evaluate_fragment(inputfilecontent)
        if len(inputfileportion)==0:
            raise ValueError("Input URL %s fragment reference failed to resolve" % (inputfilehref.humanurl()))
        elif len(inputfileportion) > 1:
            raise ValueError("Input URL %s fragment reference resolved to multiple elements" % (inputfilehref.humanurl()))

        
        #print("inputfilehref=%s" % (inputfilehref.humanurl()))
        #print("inputfileportion=%s" % (etree.tostring(inputfileportion[0])))
        #import pdb as pythondb
        #pythondb.set_trace()
        outdoc=xmldoc.xmldoc.copy_from_element(inputfilecontent,inputfileportion[0],nsmap=prx_nsmap)

        # Create canonicalization from unmodified outdoc so that we can hash it
        outdoc_canon=StringIO()
        outdoc.doc.write_c14n(outdoc_canon,exclusive=False,with_comments=True)
        canonhash=hashlib.sha256(outdoc_canon.getvalue()).hexdigest()


        if inputfileportion[0] is outputdict[inputfilehref].inputfileelement:
            # special case where this input file href with fragment
            # points to its very tag -- the <inputfiles> tag in the prxfile
            # auto-populate corresponding <outputfile> tags
            
            # i.e. modify outdoc to make sure there is an <outputfile> tag with an xlink:href
            # for each inputfile

            assert(inputfilecontent.gettag(inputfileportion[0])=="prx:inputfiles")
            
            outdoc_inputfiletags=[ outdoc.getroot() ]  # treat the root <inputfiles> tag as an inputfile
            outdoc_inputfiletags.extend(outdoc.xpath("prx:inputfile"))

            for outdoc_inputfiletag in outdoc_inputfiletags:
                if outdoc_inputfiletag is outdoc.getroot() and not outdoc.hasattr(outdoc_inputfiletag,"xlink:href"):
                    # root prx:inputfiles tag has no xlink:href
                    assert(outdoc.gettag(outdoc_inputfiletag)=="prx:inputfiles")
                    outdoc_inputfilehref = inputfilehref   # subsegment of input file 
                    pass
                
                elif outdoc.hasattr(outdoc_inputfiletag,"xlink:href") and outdoc_inputfiletag is not outdoc.getroot():                    
                    outdoc_inputfilehref = dcv.hrefvalue.fromxml(outdoc,outdoc_inputfiletag) # specified input file
                    pass
                else:
                    raise ValueError("Bad <prx:inputfiles> or <prx:inputfile> tag at %s" % (dcv.hrefvalue.fromelement(outdoc,outdoc_inputfiletag).humanurl()))

                #print("outdoc_inputfilehref:")
                #print(outdoc_inputfilehref)
                #print("outputdict keys:")
                #print(outputdict.keys())

                assert(outdoc_inputfilehref in outputdict)  # all of these input file references should be keys to the output dict because outputdict was made from the originals!

                # Find or create prx:outputfile tag
                outdoc_outputfiletag = outdoc.child(outdoc_inputfiletag,"prx:outputfile")
                if outdoc_outputfiletag is None:
                    outdoc_outputfiletag=outdoc.addelement(outdoc_inputfiletag,"prx:outputfile")
                    pass

                # Ensure prx:outputfile tag has a hyperlink
                if not outdoc.hasattr(outdoc_outputfiletag,"xlink:href"):
                    outputdict[outdoc_inputfilehref].outputfilehref.xmlrepr(outdoc,outdoc_outputfiletag)
                    pass

                pass
            
            pass
        
        # Did the user provide a prx:xslt href indicating 
        # a transformation to apply? 
        xslttag=prxdoc.xpathsinglecontext(outputdict[inputfilehref].inputfileelement,"prx:xslt",default=None)
        if xslttag is not None:
            if prxdoc.hasattr(xslttag,"xlink:href"):
                filename=dcv.hrefvalue.fromxml(prxdoc,xslttag).getpath()
                pass
            else:
                filename=find_xslt_in_path(prxdoc.getcontexthref(),prxdoc.getattr(xslttag,"name")).getpath()
                    
                pass
            stylesheet=etree.parse(filename)
            stylesheet_transform=etree.XSLT(stylesheet)

            # Replace outdoc with transformed copy
            outdoc=xmldoc.xmldoc.frometree(stylesheet_transform(outdoc.doc),nsmap=prx_nsmap,readonly=False,contexthref=outdoc.getcontexthref())
            pass

        # Write out selected portion under new file name outputfilehref
        assert(outputfilehref != inputfilehref)
        outdoc.set_href(outputfilehref,readonly=False)
        outdoc.close()
        
                
        
        pass
    elif inputfilehref.get_bare_unquoted_filename().lower().endswith(".xls") or inputfilehref.get_bare_unquoted_filename().lower().endswith(".xlsx"):
        try:
            import xlrd
            import xlrd.sheet
            
            inputfileelement=outputdict[inputfilehref].inputfileelement
            # Any dc: namespace elements within the inputfileelement
            # will get placed in a dc:summary tag
                 
            
            timestamp=datetime.datetime.fromtimestamp(os.path.getmtime(inputfilehref.getpath()),lm_timestamp.UTC()).isoformat()
            spreadsheet=xlrd.open_workbook(inputfilehref.getpath())
            sheetname=prxdoc.getattr(inputfileelement,"sheetname",spreadsheet.sheet_names()[0])

            sheet=spreadsheet.sheet_by_name(sheetname)
            titlerow=int(prxdoc.getattr(inputfileelement,"titlerow","1"))-1

            # titlerow=sheet.row(titlerownum)
            nrows=sheet.nrows
            ncols=sheet.ncols

            rawtitles = [ str(sheet.cell(titlerow,col).value).strip() for col in range(ncols) ]
            tagnames = [ convert_to_tagname(splitunits(rawtitle)[0]) if rawtitle is not None and len(rawtitle) > 0 else "blank" for rawtitle in rawtitles ]
            unitnames = [ convert_to_tagname(splitunits(rawtitle)[1]) if rawtitle is not None and len(rawtitle) > 0 else None for rawtitle in rawtitles ]

            
            
            nsmap=copy.deepcopy(prx_nsmap)
            nsmap["ls"] = "http://limatix.org/spreadsheet"

            outdoc=xmldoc.xmldoc.newdoc("ls:sheet",nsmap=nsmap,contexthref=outputfilehref)

            # Copy dc: namespace elements within inputfileelement
            # into a dc:summary tag
            inputfileel_children=prxdoc.children(inputfileelement)
            summarydoc=None
            for inputfileel_child in inputfileel_children:
                if prxdoc.gettag(inputfileel_child).startswith("dc:"):
                    if summarydoc is None:
                        summarydoc=xmldoc.xmldoc.newdoc("dc:summary",nsmap=nsmap,contexthref=prxdoc.getcontexthref())
                        pass
                    # place in document with same context as where it came from
                    summarydoc.getroot().append(copy.deepcopy(inputfileel_child))
                    pass
                pass
            if summarydoc is not None:
                # shift summary context and then copy it into outdoc
                summarydoc.setcontexthref(outdoc.getcontexthref())
                outdoc.getroot().append(copy.deepcopy(summarydoc.getroot()))
                pass
            
            
            # Copy spreadsheet table
            for row in range(titlerow+1,nrows):
                rowel=outdoc.addelement(outdoc.getroot(),"ls:row")
                rownumel=outdoc.addelement(rowel,"ls:rownum")
                outdoc.settext(rownumel,str(row))
                for col in range(ncols):
                    cell=sheet.cell(row,col)
                    cell_type=xlrd.sheet.ctype_text.get(cell.ctype,'unknown')
                    if cell_type=="empty":
                        continue
                    
                    cellel=outdoc.addelement(rowel,"ls:"+tagnames[col])
                    outdoc.setattr(cellel,"ls:celltype",cell_type)
                    hyperlink=sheet.hyperlink_map.get((row,col))
                    if cell_type=="text" and hyperlink is None:
                        outdoc.settext(cellel,cell.value)
                        pass
                    elif cell_type=="text" and hyperlink is not None:
                        # Do we need to do some kind of conversion on
                        # hyperlink.url_or_path()
                        outdoc.settext(cellel,cell.value)
                        hyperlink_href=dcv.hrefvalue(hyperlink.url_or_path,contexthref=inputfilehref)
                        hyperlink_href.xmlrepr(outdoc,cellel)
                        pass
                    elif cell_type=="number":
                        if unitnames[col] is not None:
                            outdoc.setattr(cellel,"dcv:units",unitnames[col])
                            pass
                        outdoc.settext(cellel,str(cell.value)) 
                        pass
                    elif cell_type=="xldate":
                        outdoc.settext(cellel,datetime.datetime(xlrd.xldate_as_tuple(cell.value,spreadsheet.datemode)).isoformat())
                        pass
                    elif cell_type=="bool":
                        outdoc.settext(cellel,str(bool(cell.value)))            
                        pass
                    elif cell_type=="error":
                        outdoc.settext(cellel,"ERROR %d" % (cell.value))
                        pass
                    else:
                        raise ValueError("Unknown cell type %s" %(cell_type))
                    
                    pass
                pass

            # Did the user provide a prx:xslt href indicating 
            # a transformation to apply? 
            xslttag=prxdoc.xpathsinglecontext(outputdict[inputfilehref].inputfileelement,"prx:xslt",default=None)
            if xslttag is not None:
                if prxdoc.hasattr(xslttag,"xlink:href"):
                    filename=dcv.hrefvalue.fromxml(prxdoc,xslttag).getpath()
                    pass
                else:
                    filename=find_xslt_in_path(prxdoc.getcontexthref(),prxdoc.getattr(xslttag,"name")).getpath()
                    
                    pass
                
                stylesheet=etree.parse(filename)
                stylesheet_transform=etree.XSLT(stylesheet)
                
                # Replace outdoc with transformed copy
                outdoc=xmldoc.xmldoc.frometree(stylesheet_transform(outdoc.doc),nsmap=prx_nsmap,readonly=False,contexthref=outdoc.getcontexthref())
                pass

            
            # Write out under new file name outputfilehref
            assert(outputfilehref != inputfilehref)
            outdoc.set_href(outputfilehref,readonly=False)
            outdoc.close()
            canonhash=None  # could hash entire input file...
            pass
        except ImportError:

            raise(ImportError("Need to install xlrd package in order to import .xls or .xlsx files"))
        
        pass
    else:
        # input file url has no fragment, not .xls or .xlsx: treat it as XML
        # extract the whole thing!
        
        # Do we have an input filter? ... stored as xlink:href in <inputfilter> tag
        canonhash=None  # (we could hash the entire inputfile!)
        inputfilters=prxdoc.xpath("inputfilter")
        if len(inputfilters) > 1:
            raise ValueError("Maximum of one <inputfilter> element permitted in .prx file")
        timestamp=datetime.datetime.fromtimestamp(os.path.getmtime(inputfilehref.getpath()),lm_timestamp.UTC()).isoformat()

        if len(inputfilters) > 0:
            # have an input filter
            inputfilter=inputfilters[0]
                
            # run input filter
            # Get path from xlink:href
            #inputfilterpath=prxdoc.get_href_fullpath(inputfilter)
            inputfilterhref=dcv.hrefvalue.fromxml(prxdoc,inputfilter)
            inputfilterpath=inputfilterhref.getpath()
            # build arguments
            inputfilterargs=[inputfilterpath]
            
            # pull attributes named param1, param2, etc. from inputfilter tag
            cnt=1
            while "param"+cnt in inputfilter.attrib:
                inputfilterargs.append(inputfilter.attrib["param"+cnt])
                cnt+=1
                pass
            
            # add input and output filenames as params to filter
            inputfilterargs.append(inputfilehref.getpath())
            inputfilterargs.append(outputfilehref.getpath())
            
            # Call input filter... will raise
            # exception if input filter fails. 
            subprocess.check_call(*inputfilterargs)
            
            pass
        else:
            # use shutil to copy input to output
            shutil.copyfile(inputfilehref.getpath(),outputfilehref.getpath())
            pass
        pass
    return (canonhash,timestamp)


def output_ensure_namespaces(output,prxdoc,justcopied):
    
    output.lock_rw()
    try: 
        if justcopied:
            # sys.stderr.write("Merging dcp namespace!\n")
            output.merge_namespace("lip","http://limatix.org/provenance")
            output.suggest_namespace_rootnode("lip","http://limatix.org/provenance")
            #sys.stderr.write("nsmap=%s\n" % (output.doc.getroot().nsmap))
            pass
        
        # transfer namespace mapping from prxdoc to output to the extent possible
        # (and store in memory for our use)
        # print prxdoc
        # print  prxdoc.getroot()
        # print  prxdoc.getroot().nsmap
        prxdocmap=prxdoc.getroot().nsmap
        for nspre in prxdocmap.keys():
            if nspre is not None:
                output.merge_namespace(nspre,prxdocmap[nspre])
                output.suggest_namespace_rootnode(nspre,prxdocmap[nspre])
                pass
            pass
        pass
    finally:
        output.unlock_rw()
        pass
    pass

        

def open_or_lock_output(prxdoc,out,overall_starttime,copyfileinfo=None):
    # Use a list (opendoclist) to wrap our output object so
    # that it can be passed around and reassigned
    # Should always be length 1

    # copyfileinfo is None (normally)
    # or if we just copied the file
    #  copyfileinfo=(inputfilecanonhash, inputfiletimestamp, cf_starttime)
    
    # if we fail, we should raise an exception, leaving output unlocked
    # if success, we leave the output locked. 

    if out.output is not None:
        out.output.lock_rw()
        return
    
    out.output=xmldoc.xmldoc.loadhref(out.outputfilehref,readonly=False,num_backups=1,use_locking=True,nsmap=outputnsmap) # ,debug=True) # !!!*** Remove debug mode eventually for performance reasons

    try: 
        # Make sure output file and in memory NSMAP has the needed namespaces
        output_ensure_namespaces(out.output,prxdoc,copyfileinfo is not None)

        
        # Create our <lip:process> element
        outputroot=out.output.getroot()
        process_el=out.output.addelement(outputroot,"lip:process")
        wcb_el=out.output.addelement(process_el,"lip:wascontrolledby")
        prxfile_el=provenance.reference_file(out.output,wcb_el,"lip:prxfile",outputroot,prxdoc.get_filehref().value(),"info")
        out.output.setattr(prxfile_el,"lip:timestamp",datetime.datetime.fromtimestamp(os.path.getmtime(prxdoc.get_filehref().getpath()),timestamp.UTC()).isoformat())
    
        provenance.write_timestamp(out.output,process_el,"lip:starttimestamp",overall_starttime)
        provenance.write_process_info(out.output,process_el)
        provenance.write_input_file(out.output,process_el,out.inputfilehref)
        provenance.write_target(out.output,process_el,out.outputfilehref)
        
        # Give our lip:process element a unique hash   (hash is used for distinguishing adjacent process elements)
        provenance.set_hash(out.output,process_el,process_el)
    
        # Get a path to our lip:process element, now that we have defined its uuid
        out.processpath=out.output.savepath(process_el)


        
        if copyfileinfo is not None:
            (inputfilecanonhash, inputfiletimestamp,cf_starttime)=copyfileinfo
            
            # Add a sub lip:process representing file copy action
            cfprocess_el=out.output.addelement(process_el,"lip:process")
            # have lip:used point to the input file we copied from 
            provenance.reference_file(out.output,cfprocess_el,"lip:used",outputroot,out.inputfilehref.value(),warnlevel="warning",timestamp=inputfiletimestamp,fragcanonsha256=inputfilecanonhash)
            provenance.write_action(out.output,cfprocess_el,"copyinput")
            provenance.write_timestamp(out.output,cfprocess_el,"lip:starttimestamp",cf_starttime)
            provenance.write_timestamp(out.output,cfprocess_el,"lip:finishtimestamp")
            
            # hash this new lip:process tag
            copiedfile_uuid=provenance.set_hash(out.output,process_el,cfprocess_el)
            # Mark all elements in tree as being generated by this copy process
            provenance.add_generatedby_to_tree(out.output,outputroot,process_el,copiedfile_uuid)
            pass
        pass
    except:
        out.output.unlock_rw()
        raise
    
    
    pass


def initialize_output_file(prxdoc,outputdict,inputfilehref,overall_starttime,force=False):


    out=outputdict[inputfilehref]
    
    # print("\n\nProcessing input URL %s to output URL %s." % (inputfilehref.humanurl(),outputfilehref.absurl())) 

    
    if force or not os.path.exists(out.outputfilehref.getpath()):
        # Need to create outputfile by copying or running inputfilter
        cf_starttime=timestamp.now().isoformat()

        (inputfilecanonhash,inputfiletimestamp)=create_outputfile(prxdoc,inputfilehref,out.outputfilehref,outputdict)

        # Will mark provenance of each element of output file
        open_or_lock_output(prxdoc,out,overall_starttime,copyfileinfo=(inputfilecanonhash, inputfiletimestamp, cf_starttime))   
        out.output.unlock_rw()  # free output lock
        pass
    
    if out.output is not None:
        out.output.shouldbeunlocked()
        pass
    
    pass
    

def finalize_output_file(prxdoc,outputdict,inputfilehref):
    
    # Write final timestamp
    out=outputdict[inputfilehref]
    if out.output is None:
        return # This output file was never actually used
    
    out.output.lock_rw()
    try: 
        process_el=out.output.restorepath(out.processpath)
        provenance.write_timestamp(out.output,process_el,"lip:finishtimestamp")
        pass
    finally:
        out.output.unlock_rw()  # free output lock
        pass
    pass

def getinputfiles(prxdoc):
    # Returns list of (inputfileelement,inputfilehref) tuples
    
    inputfiles=prxdoc.xpath("prx:inputfiles/prx:inputfile")
    inputfiles_with_hrefs = [ (inputfile,dcv.hrefvalue.fromxml(prxdoc,inputfile)) for inputfile in inputfiles ]

    #for inf in inputfilehrefs:
    #    print(inf.value().contextlist)
    #    pass
    
    prxoutputfile=prxdoc.xpath("prx:inputfiles/prx:outputfile")
    if len(prxoutputfile) > 1:
        raise ValueError("Only one outputfile corresponding to the .prx file (i.e. not inside a <prx:inputfile> tag) is permitted")
    elif len(prxoutputfile)==1:
        # got an output file for the .prx file
        # This means we have to define the inputfiles segment as
        # an inputfile... via a hypertext reference with fragment
        inputfiles_element=prxdoc.xpathsingle("prx:inputfiles")
        inputfiles.insert(0,inputfiles_element)
        inputfiles_with_hrefs.insert(0,(inputfiles_element,dcv.hrefvalue.fromelement(prxdoc,inputfiles_element)))
        pass

    return inputfiles_with_hrefs


def build_outputdict(prxdoc,useinputfiles_with_hrefs):
    outputdict=collections.OrderedDict()
    
    
    for (inputfileelement,inputfilehref) in useinputfiles_with_hrefs:
        
        # Figure out output file name
        outputfiletag=prxdoc.child(inputfileelement,"prx:outputfile")
        if outputfiletag is not None and prxdoc.hasattr(outputfiletag,"xlink:href"):
            outputfilehref=dcv.hrefvalue.fromxml(prxdoc,outputfiletag)         
            pass
        else:
            infilename=inputfilehref.get_bare_unquoted_filename()
            (inbasename,inext)=posixpath.splitext(infilename)
            
            if inext==".prx":
                outext=".pro"
                pass
            else:
                outext=".xlp"
                pass
            
            outputfilehref=dcv.hrefvalue(quote(inbasename+outext),inputfilehref.leafless())
            pass
        
        # Make sure output and input aren't the same!
        if outputfilehref==inputfilehref:
            raise ValueError("Output file URL %s is idential to input file url %s" % (outputfilehref.absurl(),inputfilehref.absurl()))
        if outputfilehref.isfile():
            if os.path.normcase(outputfilehref.getpath())==os.path.normcase(inputfilehref.getpath()):
                raise ValueError("Output file %s is the same as input file %s" % (outputfilehref.getpath(),inputfilehref.getpath()))
            pass

        outputdict[inputfilehref]=outputdoc(inputfilehref=inputfilehref,inputfileelement=inputfileelement,outputfilehref=outputfilehref)
        pass
    return outputdict

def outputdict_run_steps(prxdoc,outputdict,useinputfiles_with_hrefs,steps,filters,overall_starttime,debugmode,stdouthandler,stderrhandler,ipythonmodelist):
    # delayed import to avoid circular reference
    from limatix import processtrak_procstep
    
    # Run the specified steps, on the specified files

    
    # # Initialize any output files that don't exist
    # for inputfilehref in outputdict:
    #     initialize_output_file(prxdoc,outputdict,inputfilehref,overall_starttime)
    #     pass


    # Run each step on each input file 
    for step in steps:

    
        
        for (inputfile,inputfilehref) in useinputfiles_with_hrefs:

            if step is None: 
                # Initialize output file 
                print("\nProcessing step %s on %s->%s" % (processtrak_prxdoc.getstepname(prxdoc,step),inputfilehref.humanurl(),outputdict[inputfilehref].outputfilehref.humanurl()))

                initialize_output_file(prxdoc,outputdict,inputfilehref,overall_starttime,force=True)
                pass
            else: 
                # print("\nProcessing step %s on URL %s." % (processtrak_prxdoc.getstepname(prxdoc,step),output.get_filehref().absurl())) 

                processtrak_procstep.procstep(prxdoc,outputdict[inputfilehref],step,filters,overall_starttime,debugmode,stdouthandler,stderrhandler,ipythonmodelist)
                pass
            pass
        pass

    for inputfilehref in outputdict:
        finalize_output_file(prxdoc,outputdict,inputfilehref)
        pass



class outputdoc(object):
    output=None # xmldoc object
    outputfilehref=None
    inputfilehref=None
    inputfileelement=None  # element in in-memory copy of .prx file

    processpath=None # path to the lip:process tag for our overall process

    def __init__(self,**kwargs):
        for key in kwargs:
            assert(hasattr(self,key))            
            setattr(self,key,kwargs[key])
            pass
        pass
    
    pass

