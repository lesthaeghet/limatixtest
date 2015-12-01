import sys
import os
import os.path
import subprocess
import socket
import urllib
import traceback

import checklistdb
import canonicalize_path
import xmldoc

class dummy(object):
    pass
thisdir=os.path.split(sys.modules[dummy.__module__].__file__)[0]


def load_config(fname,paramdb,dgio,createparamserver):

    fnamepath=os.path.split(fname)[0]
    if fnamepath=="":
        fnamepath="."
        pass
    
    fnamedir="-I%s" % (fnamepath)
    confdir="-I%s" % (os.path.join(thisdir,"../conf/"))
    # sys.stderr.write("confdir=%s\n" % confdir)
    
    # read config file, adding line to change quote characters to [[ ]] 
    configfh=open(fname,"rb")
    configstr="m4_changequote(`[[',`]]')\n".encode('utf-8')+configfh.read()
    configfh.close()
    
    # pass configfile through m4
    args=["m4","--prefix-builtins",fnamedir,confdir,]
    subproc=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    output=subproc.communicate(configstr)[0]

    try: 
        exec(output,globals(),{"paramdb":paramdb,"dgio":dgio,"createparamserver":createparamserver})
        pass
    except: 
        tmpfname=os.tempnam(None,"dc2_preproc")
        tmpfh=file(tmpfname,"w")
        tmpfh.write(output)
        tmpfh.close()
        traceback.print_exc()
        sys.stderr.write("Exception executing processed config file %s; saving preprocessed output in %s\n" % (fname,tmpfname))

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
        

def searchforchecklist(fname):
    # search for in-memory checklist specified by fname
    # return (chklistobj,canonfname)
 
    checklists=checklistdb.getchecklists(None,None,None,None,allchecklists=True,allplans=True)
    if fname.startswith("mem://"):
        canonfname=fname
        pass
    else:
        canonfname=canonicalize_path.canonicalize_path(fname)
        pass
    matching=[checklist  for checklist in checklists if checklist.canonicalpath==canonfname]
    # sys.stderr.write("SearchForChecklist: matching=%s\n" % (str(matching)))
    if len(matching) > 1:
        raise ValueError("Multiple in-memory checklists match %s: %s" % (fname,str(matching)))
    if len(matching)==0 or not matching[0].is_open or matching[0].checklist is None:
        if fname.startswith("mem://"):
            raise ValueError("Attempting to open nonexistent in-memory checklist %s (probably residue of incomplete checklist from previous run)." % (fname))
                
            
        return (None,canonfname)
    else:
        return (matching[0].checklist,canonfname)
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
