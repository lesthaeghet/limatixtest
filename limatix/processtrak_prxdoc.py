import os
import sys
from lxml import etree

# This stuff is separate primarily because it is imported
# by provenance... this small collection is lightweight
# and doesn't try to import dc_value (which can't be imported
# within the header of provenance without a dependency loop)


def findstep(prxdoc,stepname):
    if stepname=="copyinput":
        return None  # None is a shorthand for the copyinput step
    for step in prxdoc.xpath("prx:step"):
        name=getstepname(prxdoc,step)
        if name==stepname:
            return step
        pass
    raise ValueError("step %s not found" % (stepname))



def getstepname(prxdoc,step):
    if step is None:
        return "copyinput"
    
    scripttag=prxdoc.xpathsinglecontext(step,"prx:script",default=None)
    if prxdoc.hasattr(step,"name"):
        return prxdoc.getattr(step,"name")
    elif scripttag is not None and prxdoc.hasattr(scripttag,"xlink:href"):
        scriptname=os.path.splitext(os.path.split(prxdoc.get_href_fullpath(contextnode=scripttag))[1])[0]
        # print ("scriptname=%s" % (str(scriptname)))
        
        if prxdoc.hasattr(scripttag,"function"):
            scriptname+="/"+prxdoc.getattr(scripttag,"function")
            pass
        return scriptname
    elif scripttag is not None and prxdoc.hasattr(scripttag,"name"):
        scriptname=os.path.splitext(os.path.split(prxdoc.getattr(scripttag,"name"))[1])[0]
        if prxdoc.hasattr(scripttag,"function"):
            scriptname+="/"+prxdoc.getattr(scripttag,"function")
            pass
        return scriptname
    else : 
        raise ValueError("step tag %s has no name specified" % (etree.tostring(step)))
    pass


