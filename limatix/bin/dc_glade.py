#! /usr/bin/env python

import sys
import os
import os.path

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

#gladedir=os.path.join(installeddir,"../glade-3")

#if os.path.exists(gladedir):
#    pass
#elif os.path.exists(os.path.join(installeddir,"../glade-3")):
#    gladedir=os.path.join(installeddir,"../glade-3")
#    pass
from limatix import widgets

widgetsdir=os.path.split(widgets.__file__)[0]


#if "GLADE_CATALOG_PATH" in os.environ:
#    os.environ["GLADE_CATALOG_PATH"]=os.environ["GLADE_CATALOG_PATH"]+":"+os.path.join(gladedir,"glade_catalogs")
#    pass
#else:
os.environ["GLADE_CATALOG_PATH"]=os.path.join(widgetsdir,"glade_catalogs")
#pass

#if "GLADE_MODULE_PATH" in os.environ:
#   os.environ["GLADE_MODULE_PATH"]=os.environ["GLADE_MODULE_PATH"]+":"+os.path.join(gladedir,"glade_modules")
#    pass
#else:
#os.environ["GLADE_MODULE_PATH"]=os.path.join(gladedir,"glade_modules")
#    pass

#print (os.environ["GLADE_MODULE_PATH"])

def main():
    print (os.environ["GLADE_CATALOG_PATH"])

    params=["glade-367"]
    params.extend(sys.argv[1:])
    # print params
    os.execvp(params[0],tuple(params))
    pass
