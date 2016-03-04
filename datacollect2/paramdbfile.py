import os
import os.path
import sys
import urllib
from lxml import etree


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


from . import xmldoc
from . import dc_value
from . import canonicalize_path
from . import checklistdb

paramdbfile_nsmap={ "dc": "http://thermal.cnde.iastate.edu/datacollect", "xlink": "http://www.w3.org/1999/xlink", "dcv":"http://thermal.cnde.iastate.edu/dcvalue"}

# Replaced by canonicalize_path.rel_or_abs_path
#def determine_path(reffile,destfile):
#    canonpath=canonicalize_path.canonicalize_path(destfile)
#    relpath=canonicalize_path.relative_path_to(os.path.split(reffile)[0],canonpath)
#
#    relpathsplit=canonicalize_path.pathsplit(relpath)
#    if len(relpath) >= 2 and relpathsplit[0]==".." and relpathsplit[1]=='..':
#        # two ".."s at start... use absolute path
#        usepath=canonpath
#        pass
#    else: 
#        usepath=relpath
#        pass
#   return usepath
    


def save_params(configfhrefs,guis,paramdb,fname,xmldochref,SingleSpecimen,non_settable=False,dcc=True,gui=True,chx=True,plans=True,xlg=True,synced=False):
    # Save parameters in file fname. 
    # Parameters: 
    # configfhrefs:  list of .dcc files to include (dc_value.hrefvalue)
    # guis:          list of gladefiles to include
    # paramdb:       parameter database to dump
    # fname:         file to write
    # SingleSpecimen Truth value 
    # non_settable:  If True, include non-settable parameters with paramdb
    # dcc:           If True, include .dcc files, otherwise inhibit .dcc files
    # gui:           If True, include .glade files, otherwise inhibit
    # chx:           Extract list of in-memory checklists from checklistdb
    #                and include
    # plans:         Extract list of in-memory plans from checklistdb and
    #                include
    # xlg:           Extract experiment log info (experiment log name, and single specimen vs. multispecimen
    # synced:        Save parameters that are normally synced to the global
    #                experiment log

    #contextdir=os.path.split(fname)[0]

    paramdoc=xmldoc.xmldoc.newdoc("dc:params",nsmap=paramdbfile_nsmap)
    paramdoc.set_href(dc_value.hrefvalue(pathname2url(fname)),readonly=False)
    
    
    if dcc:
        configfiles=paramdoc.addelement(paramdoc.getroot(),"dc:configfiles")
        
        for configfhref in configfhrefs:
                
            configfile=paramdoc.addelement(configfiles,"dc:configfile")
            #sys.stderr.write("configfhref.path=%s; configfhref.contextdir=%s\n" % (configfhref.path,configfhref.contextdir))
            configfhref.xmlrepr(paramdoc,configfile)
            pass
        pass
        


    if gui:
        guitags=paramdoc.addelement(paramdoc.getroot(),"dc:guis")
            
        for guifname in guis:

            guihref=dc_value.hrefvalue.from_rel_or_abs_path(".",guifname)
            
            guitag=paramdoc.addelement(guitags,"dc:gui")
            guihref.xmlrepr(paramdoc,guitag)
            pass
        pass
            

    if chx:
        checklistentries=checklistdb.getchecklists(None,None,None,allchecklists=True)


        chxs=paramdoc.addelement(paramdoc.getroot(),"dc:chxs")
        
        for entry in checklistentries:
            
            if entry.checklist is None or entry.checklist.closed:
                continue
                
            # check if entry has a parent
            entry.checklist.xmldoc.lock_ro()
            try: 
                if len(entry.checklist.xmldoc.xpathsinglestr("string(chx:parent/@xlink:href)")) > 0:
                    # has a parent... don't include it (should come from parent!) 
                    continue
                pass
            finally: 
                entry.checklist.xmldoc.unlock_ro()                    
                pass

            chxhref=entry.checklist.xmldoc.get_filehref()
            
            chxtag=paramdoc.addelement(chxs,"dc:chx")
            chxhref.xmlrepr(paramdoc,chxtag)
            pass
        pass
        
        
    
    if plans:
        checklistentries=checklistdb.getchecklists(None,None,None,allplans=True)

        
        plans=paramdoc.addelement(paramdoc.getroot(),"dc:plans")
        
        for entry in checklistentries:
            
            if entry.checklist is None:
                continue
            if len(entry.checklist.xmldoc.xpathsinglestr("string(chx:parent/@xlink:href)")) > 0:
                # has a parent... don't include it (should come from parent!) 
                continue

            planhref=entry.checklist.xmldoc.get_filehref()
                    
                
            plantag=paramdoc.addelement(plans,"dc:plan")
            planhref.xmlrepr(paramdoc,plantag)
            pass
        pass

    if xlg:

        if xmldochref is not None:
            # include link to experiment log
            explog=paramdoc.addelement(paramdoc.getroot(),"dc:explog")
            xmldochref.xmlrepr(paramdoc,explog)
            pass
        
        # Indicate whether single- or multi-specimen
        if SingleSpecimen: 
            paramdoc.addelement(paramdoc.getroot(),"dc:singlespecimen")
            pass
        else: 
            paramdoc.addelement(paramdoc.getroot(),"dc:multiplespecimen")
            pass
        
    paramdbtag=paramdoc.addelement(paramdoc.getroot(),"dc:paramdb")
        
    for paramname in paramdb:
        if paramname in paramdb: 
            if paramname=="checklists" or paramname=="plans": 
                # Does not make sense to save current explogwindow list of checklists or plans with parameters
                continue

            # list of parameters here must be consistent with
            # instantiated synced parameters in datacollect2 script
            # and with adddoc() calls in explogwindow.py
            if not synced and (
                    (paramname=="specimen" and SingleSpecimen) or
                    paramname=="perfby" or
                    paramname=="date" or
                    paramname=="expnotes" or
                    paramname=="goal" or
                    paramname=="dest" or
                    paramname=="expphotos" or
                    paramname=="hostname" or
                    paramname=="measnum" or
                    paramname=="checklists" or
                    paramname=="plans"):
                # ignore sync'ed parameters with synced unset. 
                continue

            if non_settable or not paramdb[paramname].non_settable:
                paramtag=paramdoc.addelement(paramdbtag,"dc:"+paramname)
                paramdb[paramname].dcvalue.xmlrepr(paramdoc,paramtag,defunits=paramdb[paramname].defunits)  # xml_attribute=paramdb[paramname].xml_attribute)
                pass
            pass
        pass
        
    #sys.stderr.write("calling paramdoc.close() filename=%s\n" % (paramdoc.filename))
    paramdoc.close()

    pass

def _load_params_proc_configfiles(doc,child):
    configlist=[]

    configfiles=doc.xpathcontext(child,"*")
    for configfile in configfiles: 
        tag=doc.gettag(configfile)
        
        if tag=="dc:configfile":
            configlist.append(urllib.url2pathname(doc.getattr(configfile,"xlink:href")))
            pass
        else: 
            raise ValueError("Unknown tag in dc:configfiles: %s" % (tag))
        pass
    return configlist


def _load_params_proc_guis(doc,child):
    guilist=[]

    guis=doc.xpathcontext(child,"*")
    for gui in guis: 
        tag=doc.gettag(gui)
        
        if tag=="dc:gui":
            guilist.append(urllib.url2pathname(doc.getattr(gui,"xlink:href")))
            pass
        else: 
            raise ValueError("Unknown tag in dc:guis: %s" % (tag))
        pass
    return guilist

def _load_params_proc_chxs(doc,child):
    chxlist=[]

    chxs=doc.xpathcontext(child,"*")
    for chx in chxs: 
        tag=doc.gettag(chx)
        
        if tag=="dc:chx":
            chxlist.append(urllib.url2pathname(doc.getattr(chx,"xlink:href")))
            pass
        else: 
            raise ValueError("Unknown tag in dc:chxs: %s" % (tag))
        pass
    return chxlist
        

def _load_params_proc_plans(doc,child):
    planlist=[]

    plans=doc.xpathcontext(child,"*")
    for plan in plans: 
        tag=doc.gettag(plan)
        
        if tag=="dc:plan":
            planlist.append(urllib.url2pathname(doc.getattr(plan,"xlink:href")))
            pass
        else: 
            raise ValueError("Unknown tag in dc:plans: %s" % (tag))
        pass
    return planlist


def apply_paramdb_updates(paramdb_updates,paramdb):
    # assign parameters (except those marked in paramdb as dangerous) into
    # paramdb; return paramlog
    # returns list of log entries
    log=[]

    if paramdb is None:
        return log # ignore

    params=paramdb_updates.xpath("*")
    for param in params: 
        tag=paramdb_updates.gettag(param)
        
        (prefix,dctag)=tag.split(":")
        if prefix != "dc":
            raise ValueError("Paramdb tag %s is not in the datacollect namespace" % (tag))
        
        if not(dctag in paramdb):
            raise ValueError("Paramdb tag %s is not in the parameter database" % (tag))

        if paramdb[dctag].dangerous:
            log.append((dctag,"dangerous",None,None))
        else: 
            dest=None

            if "dest" in paramdb: 
                dest=paramdb["dest"].dcvalue.value()
                pass
            # only restore non-dangerous parameters
            # temporarily set filename for paramdb_updates
            dcvalue=paramdb[dctag].paramtype.fromxml(paramdb_updates,param,defunits=paramdb[dctag].defunits)   # xml_attribute=paramdb[dctag].xml_attribute)

            if dcvalue is None: 
                raise ValueError("Got None from fromxml() for %s from %s" % (dctag,etree.tostring(param)))

            actval=paramdb[dctag].requestval_sync(dcvalue)

            #if actval is None: 
            #    raise ValueError("Got None from requstval_sync() for %s from %s" % (dctag,str(dcvalue)))

            # sys.stderr.write("actval=%s\n" % (str(actval)))
            if actval is None:
                log.append((dctag,"error",dcvalue,None))               
            elif actval==dcvalue:
                log.append((dctag,"match",dcvalue,None))
                pass
            else: 
                log.append((dctag,"mismatch",dcvalue,actval))
                pass
            pass
        pass
    return log


def load_params(dpdfile):
    # Return (dpdconfigfiles,dpdguis,dpdchxfiles,dpdplans,dpdexplog,paramupdates,singlespecimen),
    # Call apply_paramdb_updates() later with paramupdates 
    # to actually apply the paramdb updates. 

    configfiles=[]
    guis=[]
    chxs=[]
    plans=[]
    explog=None
    singlespecimen=None

    doc=xmldoc.xmldoc.loadfile(dpdfile,paramdbfile_nsmap)

    
    # Give our in-memory document a name (should never be written) because it needs to have a name and
    # be in the same directoyr as dpdfile so it has that context for reading data from the xml
    #(dpddir,dpdname)=os.path.split(dpdfile)
    #tmpfilename=os.path.join(dpddir,".%s_pdbtmp" % (dpdname))
    paramupdates=xmldoc.xmldoc.newdoc("dc:paramdb",contextdir=os.path.split(dpdfile)[0],nsmap=paramdbfile_nsmap)
    
    for child in doc.xpath("*"):
        tag=doc.gettag(child)
        
        if tag=="dc:configfiles":
            filelist=_load_params_proc_configfiles(doc,child)
            configfiles.extend(filelist)
            pass
        elif tag=="dc:guis":
            filelist=_load_params_proc_guis(doc,child)
            guis.extend(filelist)
            pass
        elif tag=="dc:chxs":
            filelist=_load_params_proc_chxs(doc,child)
            chxs.extend(filelist)
            pass
        elif tag=="dc:plans":
            filelist=_load_params_proc_plans(doc,child)
            plans.extend(filelist)
            pass
        elif tag=="dc:explog":
            explog=urllib.url2pathname(doc.getattr(child,"xlink:href"))
            pass
        elif tag=="dc:paramdb":
            # copy elements into a new document that we will return
            paramupdates.copyelements(None,doc,child.xpath("*"))

            pass
        elif tag=="dc:singlespecimen":
            singlespecimen=True
            pass
        elif tag=="dc:multispecimen":
            singlespecimen=False
            pass
        else: 
            raise ValueError("Unknown tag: %s" % (tag))
        pass

    contextdir=os.path.split(dpdfile)[0]
    
    canonicalize_path.canonicalize_filelist(contextdir,configfiles)
    canonicalize_path.canonicalize_filelist(contextdir,guis)
    canonicalize_path.canonicalize_filelist(contextdir,chxs)
    canonicalize_path.canonicalize_filelist(contextdir,plans)

    if explog is not None: 
        # canonicalize relative to contextdir
        if os.path.isabs(explog):
            explog=canonicalize_path.canonicalize_path(explog)
            pass
        else: 
            explog=canonicalize_path.canonicalize_path(os.path.join(contextdir,explog))
            pass


    return (configfiles,guis,chxs,plans,explog,paramupdates,singlespecimen)
