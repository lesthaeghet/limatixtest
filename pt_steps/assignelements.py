# setelements.py 
# set (i.e. add or replace) specified sub-elements 
# in the experiment log element we are operating on
#
# Please note: 
#  This is only suitable if the desire is to have exactly one 
#  element in the result with the tag you are defining
#
# You can easily add different elements to different tags by using
# the condition attribute of the param tag. 
#
# Usage: In the .prx file
# select the parent elements to operate on with <elementmatch>
# and the input file with <inputfilematch> (if necessary)
# <prx:script name="setelements.py>
#   <prx:param name="elements" condition="dc:measnum=5">
#     <dc:mysetting>Value5</dc:mysetting>
#   </prx:param>
#   <prx:param name="elements" condition="dc:measnum=6">
#     <dc:mysetting>Value6</dc:mysetting>
#   </prx:param>

def run(_xmldoc,_element,elements_doc,elements):
    
    for child in elements_doc.children(elements):
        # remove old elements with same tag
        
        oldels=_xmldoc.xpathcontext(_element,elements_doc.gettag(child),namespaces=elements_doc.namespaces)
        for oldel in oldels: 
            _xmldoc.remelement(oldel)
            pass
        
        # Copy element with subtree
        _xmldoc.addtreefromdoc(_element,elements_doc,child)
        pass
    
    pass
