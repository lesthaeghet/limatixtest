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



outputnsmap={
    "lip": "http://limatix.org/provenance",
}


prx_nsmap={
    "prx": "http://limatix.org/processtrak/processinginstructions",
    "dcv": "http://limatix.org/dcvalue",
    "xlink": "http://www.w3.org/1999/xlink",
};




def create_outputfile(prxdoc,inputfilehref,outputfilehref,outputdict):
            
    
    # print("inputfilehref=%s" % (inputfilehref.humanurl()))
    if inputfilehref.has_fragment():
        # input file url has a fragment... we're only supposed
        # to extract a portion of the file

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
        
        # Write out selected portion under new file name outputfilehref
        outdoc.set_href(outputfilehref,readonly=False)
        outdoc.close()
        
                
        
        pass
    else:
        # input file url has no fragment...
        # extract the whole thing!
        
        # Do we have an input filter? ... stored as xlink:href in <inputfilter> tag
        canonhash=None  # (we could hash the entire inputfile!)
        inputfilters=prxdoc.xpath("inputfilter")
        if len(inputfilters) > 1:
            raise ValueError("Maximum of one <inputfilter> element permitted in .prx file")
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
    return canonhash


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
    #  copyfileinfo=(canonhash, cf_starttime)
    
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
        
        # Give our lip:process element a unique hash   (hash is used for distinguishing adjacent process elements)
        provenance.set_hash(out.output,process_el,process_el)
    
        # Get a path to our lip:process element, now that we have defined its uuid
        out.processpath=out.output.savepath(process_el)


        
        if copyfileinfo is not None:
            (canonhash, cf_starttime)=copyfileinfo
            
            # Add a sub lip:process representing file copy action
            cfprocess_el=out.output.addelement(process_el,"lip:process")
            # have lip:used point to the input file we copied from 
            provenance.reference_file(out.output,cfprocess_el,"lip:used",outputroot,out.inputfilehref.value(),warnlevel="warning",fragcanonsha256=canonhash)
            provenance.write_action(out.output,cfprocess_el,"_copy_input_file")
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


def initialize_output_file(prxdoc,outputdict,inputfilehref,overall_starttime):


    out=outputdict[inputfilehref]
    
    # print("\n\nProcessing input URL %s to output URL %s." % (inputfilehref.humanurl(),outputfilehref.absurl())) 

    
    if not os.path.exists(out.outputfilehref.getpath()):
        # Need to create outputfile by copying or running inputfilter
        cf_starttime=timestamp.now().isoformat()

        canonhash=create_outputfile(prxdoc,inputfilehref,out.outputfilehref,outputdict)

        # Will mark provenance of each element of output file
        open_or_lock_output(prxdoc,out,overall_starttime,copyfileinfo=(canonhash, cf_starttime))   
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

def outputdict_run_steps(prxdoc,outputdict,steps,filters,overall_starttime,debugmode,stdouthandler,stderrhandler,ipythonmodelist):
    # delayed import to avoid circular reference
    from limatix import processtrak_procstep
    
    # Run the specified steps, on the specified files

    
    # Initialize any output files that don't exist
    for inputfilehref in outputdict:
        initialize_output_file(prxdoc,outputdict,inputfilehref,overall_starttime)
        pass


    # Run each step on each input file 
    for step in steps:
        print("\nProcessing step %s" % (processtrak_prxdoc.getstepname(prxdoc,step)))
        for inputfilehref in outputdict:
            # print("\nProcessing step %s on URL %s." % (processtrak_prxdoc.getstepname(prxdoc,step),output.get_filehref().absurl())) 

            processtrak_procstep.procstep(prxdoc,outputdict[inputfilehref],step,filters,overall_starttime,debugmode,stdouthandler,stderrhandler,ipythonmodelist)
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

