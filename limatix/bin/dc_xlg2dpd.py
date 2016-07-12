#! /usr/bin/env python

import sys
import os
import os.path
import string
import datetime
import socket
import json

import subprocess
from lxml import etree

from limatix import lm_units
lm_units.units_config("insert_basic_units")



#class dummy(object):
#    pass
#
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
#
#installeddir=os.path.dirname(installedfile)
#
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
from limatix import canonicalize_path
from limatix import paramdbfile


x2d_nsmap={ "dc": "http://limatix.org/datacollect", "xlink": "http://www.w3.org/1999/xlink", "dcv":"http://limatix.org/dcvalue", "chx": "http://limatix.org/checklist"}

positionals=[]
argc=1

xlg2dpd_xsl=r"""<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:dc="http://limatix.org/datacollect" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:dcv="http://limatix.org/dcvalue" xmlns:chx="http://limatix.org/checklist">
  <xsl:output method="xml"/>

  <xsl:template match="dc:experiment">
    <xsl:apply-templates select="dc:configstr|dc:summary|((dc:measurement)[last()])"/>
  </xsl:template>

  <xsl:template match="dc:summary">
    <dc:paramdb>
      <xsl:apply-templates mode="paramdb"/>
    </dc:paramdb>
  </xsl:template>

  <xsl:template match="dc:measurement">
    <dc:paramdb>
      <xsl:apply-templates mode="paramdb"/>     
    </dc:paramdb>
  </xsl:template>

  <!-- ignore dc:configstr -->
  <xsl:template match="dc:configstr"/>

  <xsl:template match="/">
    <dc:params>
      <xsl:apply-templates/> <!-- select="dc:configstr|dc:summary|((dc:measurement)[last()])"/> -->
    </dc:params>
  </xsl:template>

  <!-- Copying paramdb elements -->
  <xsl:template match="dc:checklists" mode="paramdb"/> <!-- ignore dc:checklists tag -->
  <xsl:template match="dc:plans" mode="paramdb"/> <!-- ignore dc:plans tag -->
  <xsl:template match="dc:recordmeastimestamp" mode="paramdb"/> <!-- ignore dc:recordmeastimestamp tag -->
  <xsl:template match="chx:clinfo" mode="paramdb"/> <!-- ignore chx:clinfo tags -->
  <xsl:template match="chx:cltitle" mode="paramdb"/> <!-- ignore chx:cltitle tags -->

  <xsl:template match="@*|node()" mode="paramdb">
    <xsl:copy>
      <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
  </xsl:template>

  <xsl:template match="*" mode="paramdb">
    <!-- <xsl:copy-of select="."/> --> <!-- This causes excess xmlns:xxx entries -->
    <xsl:element name="{name()}" namespace="{namespace-uri()}">
      <xsl:apply-templates select="@*|node()" mode="paramdb"/>
    </xsl:element>
  </xsl:template>


</xsl:stylesheet>
"""


def main():
    while argc < len(sys.argv):
        arg=sys.argv[argc]
        
        if arg=="-h" or arg=="--help":	
            print("""Usage: %s input.xlg [output.dpd]""" % (sys.argv[0]))
            sys.exit(0)
            pass
        elif arg.startswith("-"):
            raise ValueError("Unknown flag: %s" % (arg))
        else: 
            positionals.append(arg)
            pass
        argc+=1
        pass
    
    if len(positionals) > 2:
        raise ValueError("Too many positional parameters (see -h for command line help")
    
    if len(positionals) < 1:
        raise ValueError("Not enough positional parameters (see -h for command line help")
    
    if len(positionals)==1:
        xlgfile=positionals[0]
        dpdfile=os.path.splitext(xlgfile)[0]+".dpd"
        
        pass
    else:
        assert(len(positionals)==2)
        xlgfile=positionals[0]
        dpdfile=positionals[1]
        pass
    
    
    if dpdfile==xlgfile:
        raise ValueError("xlg file %s must not match dpd file %s" % (xlgfile,dpdfile))
    

    # Use XSLT to transform paramdb entries
    xlgdoc=xmldoc.xmldoc.loadfile(xlgfile,x2d_nsmap,readonly=True)
    
    xlg2dpd_transform=etree.XSLT(etree.XML(xlg2dpd_xsl))
    initialdpdfile=xlg2dpd_transform(xlgdoc.doc)
    
    dpddoc=xmldoc.xmldoc.frometree(initialdpdfile,nsmap=x2d_nsmap)
    
    # fixups: go through configfiles
    
    confighrefs=[]
    
    # find final dc:config block 
    config=xlgdoc.xpathsingle("dc:config[last()]")
    # go through all configfile tags, which are xlink:hrefs to the .dcc
    for configfile in xlgdoc.xpathcontext(config,"dc:configfile"):
        confighref=dc_value.hrefvalue.fromxml(xlgdoc,configfile)
        confighrefs.extend(confighref)
        pass
    
    ## canonicalize list of configfiles
    #canonicalize_path.canonicalize_filelist(os.path.split(xlgfile)[0],configfnames)
    
    ## configfpaths are the paths from the perspective of the dpdfile
    #configfpaths=[ canonicalize_path.rel_or_abs_path(os.path.split(dpdfile)[0],configf) for configf in configfnames ]
    
    # insert dc:configfiles tag and generate dc:configfile tags within 
    configfilesel=dpddoc.insertelement(None,0,"dc:configfiles")
    for confighref in confighrefs: 
        configfileel=dpddoc.addelement(configfilesel,"dc:configfile")
        confighref.xmlrepr(dpddoc,configfileel)
        pass
    
    # insert dc:explog tag
    explogel=dpddoc.insertelement(None,1,"dc:explog")
    xlghref=dc_value.hrefvalue.from_rel_path(".",xlgfile)
    xlghref.xmlrepr(dpddoc,explogel)
    
    # go through checklists
    checklist_hrefs=[] # list of hrefs
    #origfilenameset=set([]) # set of canonicalize origfilenames

    #reldest=xlgdoc.xpath("string(dc:summary/dc:reldest)")
    ##sys.stderr.write("reldest=%s\n" % (reldest))
    checklists=xlgdoc.xpath("dc:summary/dc:checklists/dc:checklist")
    for checklist in checklists:
        href=dc_value.hrefvalue.fromxml(xlgdoc,checklist)
        
        if href.ismem():
            # ignore and do nothing
            continue

        # ignore if checklist has a parent (we will get it from its parent)
        checklistfname=href.getpath(".")
        chxdoc=xmldoc.xmldoc.loadfile(checklistfname,x2d_nsmap,readonly=True)
        has_parent = len(chxdoc.getattr(None,"parent","")) > 0 
        is_done = chxdoc.getattr(chxdoc.getroot(),"done",default="false")=="true"
        if has_parent or is_done:
            continue
        
        checklist_hrefs.append(href)
        pass
    
    
    # Now add everything in origfilenameset to a dc:chxs tag
    # and generate dc:chx tags within
    chxsel=dpddoc.insertelement(None,0,"dc:chxs")
    for checklist_href in checklist_hrefs: 
        chxel=dpddoc.addelement(chxsel,"dc:chx")
        checklist_href.xmlrepr(dpddoc,chxel)
        pass
    
    # Write out the resulting dpdfile
    dpddoc.setfilename(dpdfile)
    dpddoc.close()
    pass
