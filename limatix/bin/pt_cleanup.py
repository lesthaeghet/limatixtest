#! /usr/bin/env python
from __future__ import print_function

import sys

import os
import os.path
import socket
import copy
import inspect
import numbers
import traceback


try:
    from cStringIO import StringIO
    pass
except ImportError:
    from io import StringIO
    pass

import cProfile
import time

#if "--gtk3" in sys.argv or sys.version_info[0] >= 3:  # gtk3
#    from gi.repository import Gtk as gtk
#    pass
#else :  # gtk2
#    import gobject
#    import gtk
#    pass

import shutil
import datetime

try: 
    import builtins  # python3
    pass
except ImportError: 
    import __builtin__ as builtins # python2
    pass

if not hasattr(builtins,"raw_input"):
    # python3
    raw_input=input
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


from limatix import lm_units
lm_units.units_config("insert_basic_units")

#class dummy(object):
#    pass

## trace symbolic link to find installed directory
#thisfile=sys.modules[dummy.__module__].__file__
#if os.path.islink(thisfile):
#    installedfile=os.readlink(thisfile)
#    if not os.path.isabs(installedfile):
#        installedfile=os.path.join(os.path.dirname(thisfile),installedfile)
#        pass
#    pass
#else:
#    installedfile=thisfile
#    pass

#installeddir=os.path.dirname(installedfile)

#if os.path.exists(os.path.join(installeddir,"../lib/checklist.py")):
#    installeddir=os.path.join(installeddir,"../")
#    pass
#elif os.path.exists(os.path.join(installeddir,"../gui2/lib/checklist.py")):
#    installeddir=os.path.join(installeddir,"../gui2")
#    pass

#sys.path.append(installeddir)
#sys.path.append(os.path.join(installeddir,"lib/"))

from limatix import dc_value
from limatix import xmldoc
from limatix import processtrak_cleanup
from limatix import canonicalize_path
from limatix import provenance
from limatix import timestamp


def show_steps_in_xlp(xlpdocu):
    # Find all lip:process tags with an action child that also have-- either themselves or and ancestor -- a wascontrolledby with a lip:prxfile 
    actionprocesses=xlpdocu.xpath("lip:process/descendant-or-self::lip:process[lip:action and (ancestor-or-self::lip:process/lip:wascontrolledby)[1]/lip:prxfile/@xlink:href]")
                                  
    actionprocs_with_prxfile=[ (actionproc,xlpdocu.xpathsinglecontext(actionproc,"(ancestor-or-self::lip:process/lip:wascontrolledby)[1]/lip:prxfile")) for actionproc in actionprocesses ]
    
    stepname_with_prxfilehref=[ (xlpdocu.xpathsinglecontextstr(actionproc,"lip:action"), dc_value.hrefvalue.fromxml(xlpdocu,prxfile)) for (actionproc,prxfile) in actionprocs_with_prxfile ]
    
    stepname_with_prxfilehref_set = set(stepname_with_prxfilehref)


    # Count elements and get order 
    counterdict={}
    orderdict={}
    curposn=0

    for (stepname,prxfilehref) in stepname_with_prxfilehref:
        if (stepname,prxfilehref) in counterdict:
            counterdict[(stepname,prxfilehref)]+=1
            pass
        else:
            orderdict[(stepname,prxfilehref)]=curposn
            curposn+=1
            counterdict[(stepname,prxfilehref)]=1
            pass
        pass

    revorderdict=dict([ (orderdict[step_and_prxfile],step_and_prxfile) for step_and_prxfile in orderdict ])

    for posn in range(curposn):
        print("%s step %s (%d runs)" % (revorderdict[posn][1].humanurl(),revorderdict[posn][0],counterdict[revorderdict[posn]]))
        pass
    
    pass


def non_provenance_elements_generatedby_uuids(xlpdocu,uuidset):
    
    elementlist=[]
    treeroot=xlpdocu.getroot()
    elementcnt=0
    for descendent in provenance.iterelementsbutskip(treeroot,provenance.LIP+"process"):
        elementcnt+=1
        generatedby=xlpdocu.getattr(descendent,"lip:wasgeneratedby",default=None)
        if generatedby is not None:
            if generatedby.startswith("uuid="):
                if generatedby.endswith(";"):
                    generatedby=generatedby[:-1]
                    pass
                
                if generatedby[5:] in uuidset:
                    elementlist.append(descendent)
                    pass
                pass
            pass
        pass
    return (elementlist,elementcnt)


def askremove(xlpdocu,removal_candidates):
    if len(removal_candidates)==0:
        return False # nothing more to do!
    retry=True
    while retry:
        retry=False
        got_input=raw_input("Enter \"REMOVE\" to remove them\n"
                            "\"p\" to show the list, or "
                            "anything else to not remove them:"
                            " --> ").strip()
        if got_input=="REMOVE":
            print("Removing elements...")
            for element in removal_candidates:
                xlpdocu.remelement(element,True)
                pass
            return True
        elif got_input=="p":
            retry=True
            for element in removal_candidates:
                print("%s:\n%s\n" % (dc_value.hrefvalue.fromelement(xlpdocu,element).humanurl(),xlpdocu.tostring_human(element)))
                
                pass
            pass
        pass
    return False

def cleanup_obsolete_tags(xlpdocu):
    xlphref=xlpdocu.get_filehref()
    
    obsolete_process_uuids=set([])

    # import pdb
    # pdb.set_trace()

    # Find all lip:process tags with uuids  and targets that also have-- either themselves or and ancestor -- an action and a wascontrolledby with a lip:prxfile 
    targetprocesses=xlpdocu.xpath("lip:process/descendant-or-self::lip:process[@uuid and lip:target and ancestor-or-self::lip:process/lip:action and (ancestor-or-self::lip:process/lip:wascontrolledby)[1]/lip:prxfile/@xlink:href]")

    ## list of (target lip:process, corresponding lip:wascontrolledby)
    #targetwithcontrolledby=[ (action,xlpdocu.xpathsinglecontext(action,"(ancestor-or-self::lip:process[lip:wascontrolledby])[1]/lip:wascontrolledby")) for action in actionprocesses ]

    # list of (target lip:process, corresponding prxfile tags 
    targetwithprxhref = [ (target,dc_value.hrefvalue.fromxml(xlpdocu,xlpdocu.xpathsinglecontext(target,"(ancestor-or-self::lip:process/lip:wascontrolledby)[1]/lip:prxfile")).fragless()) for target in targetprocesses ]

    prxdict = {}

    # open .prx files
    prxhrefs = set([ prxhref for (target,prxhref) in targetwithprxhref ])
    prxdict=dict([ (prxhref,xmldoc.xmldoc.loadhref(prxhref,nsmap=processtrak_cleanup.nsmap)) for prxhref in prxhrefs] )
    
    # go through .prx files

    # Match up target with step ... also filter out actions that were copyinput 
    target_with_step=[ (target,prxdict[prxhref].xpathsingle("prx:step[@name=%s]" % (canonicalize_path.string_to_etxpath_expression(xlpdocu.xpathsinglecontextstr(target,"(ancestor-or-self::lip:process/lip:action)[1]"))),default=None)) for (target,prxhref) in targetwithprxhref if xlpdocu.xpathsinglecontextstr(target,"ancestor-or-self::lip:process/lip:action") != "copyinput" ]
    
    # remember target here is a lip:process tag that contains a lip:target tag
    
    # Reduce and find targets where step is missing
    target_missing_step = [ target for (target,steptag) in target_with_step if steptag is None ]
    if len(target_missing_step) > 0:
        for target in target_missing_step:
            print("Step not found for %s... will eliminate generated tags" % (xlpdocu.xpathsinglecontextstr(target,"(ancestor-or-self::lip:process/lip:action)[1]")))
            pass
        
        obsolete_process_uuids.extend([ str(xlpdocu.getattr(target,"uuid")) for target in target_missing_step])  # xpathsinglecontextstr(target,"parent::lip:process/@uuid")) for action in action_missing_step])
        
        pass
    
    target_with_valid_step = [ (target,steptag) for (target,steptag) in target_with_step if steptag is not None ]

    # remember: target is really the lip:process element that has a lip:target element

    # So of all these processes, we need to figure out which ones are not
    # current so we can throw out their results
    
    # HOW DO WE DO THIS?

    # Have lip:process tags add a <lip:target> tag referring to their
    # input. That way if there are two process tags for the same step
    # referring to the same input, the earlier one is obsolete. 
    #
    # That way the prior process can be identified and any tags
    # generated by that process can be removed.
    

    
    #  So now let's sort these things out by what element they were operating on
    validtarget_step_and_targethref = [ (target,steptag,dc_value.hrefvalue.fromxml(xlpdocu,xlpdocu.xpathsinglecontext(target,"lip:target")) ) for (target,steptag) in target_with_valid_step  ]

    assert(all([targethref.fragless()==xlphref for (target,steptag,targethref) in validtarget_step_and_targethref]))

    #import pdb;
    #pdb.set_trace()
    #junk=targethref.evaluate_fragment(xlpdocu)


    #toprint = [ (targethref.humanurl(),targethref.evaluate_fragment(xlpdocu)) for (target,steptag,targethref) in validtarget_step_and_targethref  ]
    #print(toprint)

    # evaluate target href to element
    validtarget_step_and_targetfrag = [ (target,steptag,targethref.evaluate_fragment(xlpdocu)[0] ) for (target,steptag,targethref) in validtarget_step_and_targethref  ]

    # create dictionaries by id of step  and target elements
    #stepdict=dict([ (id(steptag),x) for (target,steptag,targetfrag) in validtarget_step_and_targetfrag ])
    #targetdict=dict([ (id(targetfrag),x) for (target,steptag,targetfrag) in validtarget_step_and_targetfrag ])
    
    # for each step and target, we need a list of (processes with targettag)
    # Action dictionary looks up targetprocess by (id(step),id(target))
    targetprocessdict={} # collections.OrderedDict()
    for (targetprocess,steptag,targetfrag) in validtarget_step_and_targetfrag:
        if not (id(steptag),id(targetfrag)) in targetprocessdict:
            targetprocessdict[(id(steptag),id(targetfrag))] = []
            pass
        
        targetprocessdict[(id(steptag),id(targetfrag))].append(targetprocess)
        pass

    
    # Now go through targetprocessdict, and all but the last
    # (most recent, latest in XML file) entry can be eliminated
    for (idstep,idtarget) in targetprocessdict:
        obsolete_process_uuids.update(set([ xlpdocu.getattr(processdictentry,"uuid") for processdictentry in targetprocessdict[(idstep,idtarget)][:-1] ]))
        pass

    # Finally we have a list of obsolete process uuids.
    # Now we have to identify which tags came from those processes.

    # Convert to a set of obsolete uuids
    obsolete_process_uuids_set=set(obsolete_process_uuids)
    
    # Iterate through entire document (except for provenance metadata) and identify 
    # all tags which were generated by obsolete processes
    (obsolete_elements,elementcnt)=non_provenance_elements_generatedby_uuids(xlpdocu,obsolete_process_uuids_set)
    
    # Now we've got a list of obsolete_elements
    print("Identified %d obsolete elements out of %d total non-provenance elements" % (len(obsolete_elements),elementcnt))


    askremove(xlpdocu,obsolete_elements)
    
    pass


def remove_step_output(xlpdocu,stepname):
    # Find all lip:process tags with an action child that also have-- either themselves or and ancestor -- a wascontrolledby with a lip:prxfile

    actionprocesses=xlpdocu.xpath("lip:process/descendant-or-self::lip:process[lip:action[normalize-space(.)=%s] and (ancestor-or-self::lip:process/lip:wascontrolledby)[1]/lip:prxfile/@xlink:href]" % (canonicalize_path.string_to_etxpath_expression(stepname)))

    actionprocs_with_prxfile=[ (actionproc,xlpdocu.xpathsinglecontext(actionproc,"(ancestor-or-self::lip:process/lip:wascontrolledby)[1]/lip:prxfile")) for actionproc in actionprocesses ]

    actionprocs_and_descendents_with_uuids = []
    for actionproc in actionprocesses:
        actionprocs_and_descendents_with_uuids.extend(xlpdocu.xpathcontext(actionproc,"descendant-or-self::lip:process[@uuid]"))
        pass

    actionprocs_and_descendents_uuids=[ xlpdocu.getattr(actionproc,"uuid") for actionproc in actionprocs_and_descendents_with_uuids ]
                                               
    uuidset = set(actionprocs_and_descendents_uuids)
    
    (toremove,elementcnt)=non_provenance_elements_generatedby_uuids(xlpdocu,uuidset)
    
    print("Steps runs found (to be removed; don't forget to cleanup provenance)")
    print("--------------------------------------------------------------------")
    print("%-22s %-22s %s" % ("Start time","End time","PRX file"))
    print("-------------------------------------------------------------------")
    localtz=timestamp.getlocaltz()
    for (actionproc,prxfile) in actionprocs_with_prxfile:
        starttimestring=xlpdocu.xpathsinglecontextstr(actionproc,"(ancestor-or-self::lip:process/lip:starttimestamp)[1]",default="None")
        if starttimestring != "None":
            starttimestring=timestamp.readtimestamp(starttimestring).astimezone(localtz).strftime("%Y-%m-%d %H:%M:%S")
            pass
        finishtimestring=xlpdocu.xpathsinglecontextstr(actionproc,"(ancestor-or-self::lip:process/lip:finishtimestamp)[1]",default="None")
        if finishtimestring != "None":
            finishtimestring=timestamp.readtimestamp(finishtimestring).astimezone(localtz).strftime("%Y-%m-%d %H:%M:%S")
            pass
        
        prxfileurl=dc_value.hrefvalue.fromxml(xlpdocu,prxfile).humanurl()
        print("%-22s %-22s %s" % (starttimestring,finishtimestring,prxfileurl))
        pass
    
    removed=askremove(xlpdocu,toremove)
    
    if removed: 
        print("DON'T FORGET TO CLEANUP PROVENANCE  (-p option)")
        pass

    pass


def cleanup_dest(input_files,desthref_set,href_set):
    canonpath_set=set([ canonicalize_path.canonicalize_path(href.getpath()) for href in href_set if href.isfile() ])

    if len(desthref_set) == 0:
        print("cleanup_dest(): Did not find any .xlg or .xlp files containing dc:summary/dc:dest tags")
        pass
    #print("cleanup_dest(): desthref_set = %s" % ([str(desthref) for desthref in desthref_set]))
    
    for desthref in desthref_set:
        
        excess_files=[]
        
        destpath=desthref.getpath()
        assert(destpath.endswith('/') or destpath.endswith(os.path.sep))

        for filename in os.listdir(destpath):
            if os.path.isdir(os.path.join(destpath,filename)):
                continue # We don't currently recurse into subdirectories of dest
            filehref = dc_value.hrefvalue(quote(filename),contexthref=desthref)
            if filehref not in href_set:
                # This is an excess file
                # Check canonpath
                assert(canonicalize_path.canonicalize_path(filehref.getpath()) not in canonpath_set)
                assert(os.path.exists(filehref.getpath()))
                excess_files.append(filehref.getpath())
                pass
            pass
        print("Excess files in %s:" % (destpath))
        print("---------------------------------------------------------")
        for excess_file in excess_files:
            print(excess_file)
            pass
        
        if len(excess_files) > 0: 
            shoulddelete=raw_input("Answer \"YES\" to delete these files --> ")
            if shoulddelete.strip() == "YES":
                print("Deleting files...")
                for excess_file in excess_files:
                    os.remove(excess_file)
                    pass
                
                pass
            else:
                print("NOT deleting files")
                time.sleep(2)
                pass
            pass
        pass
    pass

def usage():
    print ("""Usage: %s [flags] file.xlp_or_prx [file2.xlp]...
      
Flags:
    -h,--help:      This help
    --steps         Show steps
    -b              Cleanup obsolete elements from processed log 
    -s prx_step     Remove content from step named prx_step
    -p              Cleanup provenance
    -d              Cleanup dest
    -r              Recursively search for xlp, xlg, prx, and other XML files
    -v:             Verbose output (list contents of errors)
    """ % (sys.argv[0]))
    pass
        
def main(args=None):
    if args is None:
        args=sys.argv
        pass
    
    argc=1
    input_file_names=[]
    show_steps=False
    verbose=False
    cleanup_provenance=False
    cleanup_dest_files=False
    cleanup_obsolete=False
    recursive=False
    remove_steps=[]

    while argc < len(args):
        arg=args[argc]
        if arg=="-h" or arg=="--help":
            usage()
            sys.exit(0)
            pass
        elif arg=="--steps":
            show_steps=True
            pass
        elif arg=="-b":
            # cleanup obsolete content
            cleanup_obsolete=True
            pass
        elif arg=="-s":
            argc+=1
            remove_steps.append(args[argc])
        elif arg=="-p":
            # cleanup provenance
            cleanup_provenance=True
            pass
        elif arg=="-d":
            # cleanup dest
            cleanup_dest_files=True
            pass
        elif arg=="-r":
            # recursive
            recursive=True
            pass
        elif arg=="-v":
            verbose=True   # ***!!! Does not currently do anything
            pass
        else: 
            input_file_names.append(arg)
            pass
        argc+=1
        pass

    if len(input_file_names) < 1: 
        usage()
        sys.exit(0)
        pass

    input_file_hrefs=[ dc_value.hrefvalue(pathname2url(input_file_name),contexthref=dc_value.hrefvalue("./")) for input_file_name in input_file_names ]

    input_files=processtrak_cleanup.infiledicts.fromhreflist(input_file_hrefs)



    #import pdb
    #pdb.set_trace()
    (completed_set,desthref_set,href_set)=processtrak_cleanup.traverse(input_files,recursive=recursive,need_href_set=not(cleanup_obsolete or len(remove_steps)>0) and cleanup_dest_files)


    if show_steps:
        for xlpfilehref in input_files.xlp:
            print("Showing steps in %s..." % (xlpfilehref.humanurl()))
            xlpdocu=input_files.xlp[xlpfilehref].xmldocu
            xlpdocu.lock_ro()
            try:
                show_steps_in_xlp(xlpdocu)
                pass
            finally:
                xlpdocu.unlock_ro()
                pass

            pass
        

    
    if cleanup_obsolete:
        
        
        for xlpfilehref in input_files.xlp:
            print("Cleaning up obsolete tags in %s..." % (xlpfilehref.humanurl()))
            xlpdocu=input_files.xlp[xlpfilehref].xmldocu
            xlpdocu.set_readonly(False)
            xlpdocu.lock_rw()
            try:
                cleanup_obsolete_tags(xlpdocu)
                
                pass
            finally:
                xlpdocu.unlock_rw()
                xlpdocu.set_readonly(True)
                pass

            pass

        pass

    for remove_step in remove_steps:
        for xlpfilehref in input_files.xlp:
            print("Removing output from step %s in %s..." % (remove_step,xlpfilehref.humanurl()))
            xlpdocu=input_files.xlp[xlpfilehref].xmldocu
            xlpdocu.set_readonly(False)
            xlpdocu.lock_rw()
            try:
                remove_step_output(xlpdocu,remove_step)
                
                pass
            finally:
                xlpdocu.unlock_rw()
                xlpdocu.set_readonly(True)
                pass

            pass

        pass
    
    if cleanup_obsolete or len(remove_steps)>0:
        # Re-call traverse(), this time getting the href_set if neede , but we don't need to recurse because we would have done that last time
        (completed_set,desthref_set,href_set)=processtrak_cleanup.traverse(input_files,recursive=False,need_href_set=cleanup_dest_files)

        pass
    
        

    
    if cleanup_dest_files:
        cleanup_dest(input_files,desthref_set,href_set)
        pass

    if cleanup_provenance:
        # import pdb
        # pdb.set_trace()

        for xlpfilehref in input_files.xlp:
            print("Cleaning up provenance in %s..." % (xlpfilehref.humanurl()))
            xlpdocu=input_files.xlp[xlpfilehref].xmldocu
            xlpdocu.set_readonly(False)
            xlpdocu.lock_rw()
            try:
                msg=provenance.cleanobsoleteprovenance(xlpdocu)
                pass
            finally:
                xlpdocu.unlock_rw()
                xlpdocu.set_readonly(True)
                pass
            print("Cleanup provenance: %s" % (msg))
            pass
        pass
    pass


