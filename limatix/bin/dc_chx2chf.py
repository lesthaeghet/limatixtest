#! /usr/bin/env python

import sys
import os
import urllib
import os.path

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

#class dummy(object):
#    pass

# trace symbolic link to find installed directory
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
from limatix import dc2_misc

def main(args=None):

    if args is None:
        args=sys.argv
        pass
    
    positionals=[]

    argc=1
    while argc < len(args):
        arg=args[argc]
        
        if arg=="-h" or arg=="--help":	
            print("""Usage: %s parent.chf input.chx output.chf""" % (args[0]))
            sys.exit(0)
            pass	
        elif arg.startswith("-"):
            raise ValueError("Unknown flag: %s" % (arg))
        else: 	
            positionals.append(arg)
            pass
        argc+=1
        pass
    
    parent=positionals[0]
    infile=positionals[1]
    outfile=positionals[2]
    
    dc2_misc.chx2chf(dc_value.hrefvalue(pathname2url(parent),contexthref=dc_value.hrefvalue("./")),
                     dc_value.hrefvalue(pathname2url(infile),contexthref=dc_value.hrefvalue("./")),
                     dc_value.hrefvalue(pathname2url(outfile),contexthref=dc_value.hrefvalue("./")))
                     
    pass
