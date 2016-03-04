import sys
import os
import os.path
import subprocess
import socket
import urllib
import traceback

from . import checklistdb
from . import canonicalize_path
from . import xmldoc
from . import dc_value

class dummy(object):
    pass
thisdir=os.path.split(sys.modules[dummy.__module__].__file__)[0]


def load_config(href,paramdb,iohandlers,createparamserver):

    dir_href=href.leafless()
    
    fnamedir="-I%s" % (dir_href.getpath())
    confdir="-I%s" % (os.path.join(thisdir,"../conf/"))
    # sys.stderr.write("confdir=%s\n" % confdir)
    
    config_globals={"paramdb":paramdb,"iohandlers":iohandlers,"createparamserver":createparamserver,"DCCHREF":href,}

    # read config file, adding line to change quote characters to [[ ]] 
    configfh=open(href.getpath(),"rb")
    configstr="m4_changequote(`[[',`]]')\n".encode('utf-8')+configfh.read()
    configfh.close()
    
    # pass configfile through m4
    args=["m4","--prefix-builtins",fnamedir,confdir,]
    subproc=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    output=subproc.communicate(configstr)[0]

    try: 
        exec(output,config_globals)
        pass
    except: 
        tmpfname=os.tempnam(None,"dc2_preproc")
        tmpfh=file(tmpfname,"w")
        tmpfh.write(output)
        tmpfh.close()
        traceback.print_exc()
        sys.stderr.write("Exception executing processed config file %s; saving preprocessed output in %s\n" % (href.getpath(),tmpfname))

        raise
    return output.decode('utf-8')
    
def set_hostname(paramdb):

    # auto-set hostname
    if paramdb["hostname"].dcvalue.isblank():
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
    
        paramdb["hostname"].requestvalstr_sync(hostname)
    
        pass
    pass
        

def searchforchecklist(href):
    # search for in-memory checklist specified by href
    # return (chklistobj,href)
 
    checklists=checklistdb.getchecklists(None,None,None,None,allchecklists=True,allplans=True)

    #sys.stderr.write("dc2_misc/searchforchecklist: Available checklists: %s\n" % (str([checklist.canonicalpath for checklist in checklists])))

    matching=[checklist  for checklist in checklists if checklist.filehref==href]
    # sys.stderr.write("SearchForChecklist: matching=%s\n" % (str(matching)))
    if len(matching) > 1:
        raise ValueError("Multiple in-memory checklists match %s: %s" % (str(href),str(matching)))
    
    if len(matching)==0 or not matching[0].is_open or matching[0].checklist is None:
    #    if fname.startswith("mem://"):
    #        raise ValueError("Attempting to open nonexistent in-memory checklist %s (probably residue of incomplete checklist from previous run)." % (fname))                       
        return (None,href)
    else:
        return (matching[0].checklist,href)
    pass

def chx2chf(parentcontextdir,parent,infilecontextdir,infile,outfilecontextdir,outfile):
    # parameters are filenames
    # if parent is a relative path it is relative to parentcontextdir, etc. 

    if os.path.isabs(parent):
        parentabs=parent
        pass
    else: 
        parentabs=os.path.join(parentcontextdir,parent)
        pass


    if os.path.isabs(infile):
        infileabs=infile
        pass
    else: 
        infileabs=os.path.join(infilecontextdir,infile)
        pass

    if os.path.isabs(outfile):
        outfileabs=outfile
        pass
    else: 
        outfileabs=os.path.join(outfilecontextdir,outfile)
        pass

    inxml=xmldoc.xmldoc.loadfile(infileabs)

    inxml.setfilename(None)

    # set context to output file directory
    inxml.setcontextdir(canonicalize_path.canonicalize_path(os.path.split(outfileabs)[0]))

    root=inxml.getroot()
    parenttags=inxml.xpath("chx:parent")
    assert(len(parenttags) < 2) # multiple parents does not make sense
    
    if len(parenttags)==1:
        # remove attribute if present
        if inxml.hasattr(parenttags[0],"xlink:href"):
            inxml.remattr(parenttags[0],"xlink:href")
            pass
        parenttag=parenttags[0]
        pass
    else : 
        # no parent tag
        parenttag=inxml.addelement(root,"chx:parent")
        pass
                
    if os.path.isabs(parent):
    # absolute path
        inxml.setattr(parenttag,"xlink:href",urllib.pathname2url(parent))
        
        pass
    else :
    
        # relative path for our parent
        parentpath=canonicalize_path.relative_path_to(inxml.getcontextdir(),parentabs)
        inxml.setattr(parenttag,"xlink:href",urllib.pathname2url(parentpath))
        pass
    pass
    

    # write origfilename attribute
    if os.path.isabs(infile):
        origfilename=infile
        pass
    else: 
        origfilename=canonicalize_path.relative_path_to(inxml.getcontextdir(),infileabs)
        pass
        
    inxml.setattr(root,"origfilename",origfilename)

    # write output file
    inxml.setfilename(outfile)
    pass

def stepwidget_update_xml(stepwidget,paramname,newvalue):
    """ Update, add, or remove an XML paramdb2 parameter value 
        within the checklist entry for the checklist step
        used by stepwidget. The parameter database used is
        stepwidget.paramdb and a restorable path is presumed to 
        be in stepwidget.xmlpath. 

        paramname gives the name of the paramdb2 entry to 
        create/update/remove the tag for and newvalue is the
        value to represent. 
        
        If newvalue is blank, then it will remove the tag. """

    gottag=False
    
    if stepwidget.checklist.xmldoc is None:
        try: 
            assert(0)
            pass
        except: 
            # import pdb as pythondb
            # pythondb.post_mortem()
            raise
        pass
    # print "Param Name:  %s" % (paramname)          
        
    # chxstate="checked" in stepwidget.xmltag.attrib and stepwidget.xmltag.attrib["checked"]=="true"
    # if chxstate: 
    #     # once checked, inhibit updates
    #     
    #     pass
    # else : 
    #     # otherwise copy current state into xmltag
    stepwidget.checklist.xmldoc.lock_rw()
    try:
        xmltag=stepwidget.checklist.xmldoc.restorepath(stepwidget.xmlpath)
        if not newvalue.isblank():
            for child in stepwidget.checklist.xmldoc.children(xmltag):
                childtag=stepwidget.checklist.xmldoc.gettag(child)
                if childtag=="dc:"+paramname or childtag==paramname:
                    newvalue.xmlrepr(stepwidget.checklist.xmldoc,child) # ,xml_attribute=xml_attribute)
                    # !!! If we are having trouble with writing absolute hrefs to the checklist file, try uncommenting these
                    #if paramname=="troublesome_parameter":
                    #    sys.stderr.write("dc2_misc: %s %s %s\n" % (str(newvalue.contextlist),str(stepwidget.checklist.xmldoc.filehref.contextlist),stepwidget.checklist.xmldoc.tostring(child)))
                    dc_value.xmlstoredisplayfmt(stepwidget.checklist.xmldoc,child,stepwidget.paramdb[paramname].displayfmt)
                    dc_value.xmlstorevalueclass(stepwidget.checklist.xmldoc,child,stepwidget.paramdb[paramname].paramtype)
                    gottag=True
                    break
                pass
            if not gottag: 
                # need to create tag
                newchild=stepwidget.checklist.xmldoc.addelement(xmltag,"dc:"+paramname)
                newvalue.xmlrepr(stepwidget.checklist.xmldoc,newchild) #xml_attribute=xml_attribute)
                dc_value.xmlstoredisplayfmt(stepwidget.checklist.xmldoc,newchild,stepwidget.paramdb[paramname].displayfmt)
                dc_value.xmlstorevalueclass(stepwidget.checklist.xmldoc,newchild,stepwidget.paramdb[paramname].paramtype)
                # !!! If we are having trouble with writing absolute hrefs to the checklist file, try uncommenting these
                # if paramname=="troublesome":
                #     sys.stderr.write("dc2_misc: %s %s %s\n" % (str(newvalue.contextlist),str(stepwidget.checklist.xmldoc.getcontexthref().contextlist),stepwidget.checklist.xmldoc.tostring(newchild)))
                #     pass
                pass
            pass
        else:
            # newvalue is blank
            # ... remove dc:<paramname> tags from checklist entry
            for child in stepwidget.checklist.xmldoc.children(xmltag):
                childtag=stepwidget.checklist.xmldoc.gettag(child)
                if childtag=="dc:"+paramname or childtag==paramname:
                    stepwidget.checklist.xmldoc.remelement(child)
                    pass
                pass
            
            pass
        pass
    except: 
        raise
    finally:
        stepwidget.checklist.xmldoc.unlock_rw()
        pass
    
    return newvalue

def stepwidget_value_from_xml(stepwidget,paramname):
            
    gotvalue=None
    gotdisplayfmt=None
    # xml_attribute=stepwidget.paramdb[stepwidget.myprops["paramname"]].xml_attribute

    stepwidget.checklist.xmldoc.lock_ro()
    try: 
        xmltag=stepwidget.checklist.xmldoc.restorepath(stepwidget.xmlpath)
        for child in stepwidget.checklist.xmldoc.children(xmltag):
            childtag=stepwidget.checklist.xmldoc.gettag(child)
            if childtag=="dc:"+paramname or childtag==paramname:
                if stepwidget.paramdb is not None:
                    # Use type specified in paramdb if possible
                    paramtype=stepwidget.paramdb[paramname].paramtype
                    pass
                else:
                    # pull type from XML
                    paramtype=dc_value.xmlextractvalueclass(stepwidget.checklist.xmldoc,child)
                    # sys.stderr.write("element %s: paramtype=%s\n" % (etree.tostring(child),str(paramtype)))
                    pass
                if paramtype is not None:
                    gotvalue=paramtype.fromxml(stepwidget.checklist.xmldoc,child)  # xml_attribute=xml_attribute)
                    gotdisplayfmt=dc_value.xmlextractdisplayfmt(stepwidget.checklist.xmldoc,child)
                    pass
                else :
                    gotvalue=dc_value.stringvalue("") # blank
                    gotdisplayfmt=None
                    pass
                break
            pass
        pass
    except: 
        raise
    finally:
        stepwidget.checklist.xmldoc.unlock_ro()
        pass
    return (gotvalue,gotdisplayfmt)
    
