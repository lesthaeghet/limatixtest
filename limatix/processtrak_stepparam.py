import sys
import os
import os.path
import numbers
import copy
import ast

from . import dc_value as dcv
from .canonicalize_path import etxpath2human

try: 
    import builtins  # python3
    pass
except ImportError: 
    import __builtin__ as builtins # python2
    pass
    
if hasattr(builtins,"long"):
    int_or_long=long
    pass
else:
    int_or_long=int  # python3
    pass


def evaluate_from_element(xmldocu,element,typename):
    # typename can be str,float,int,bool : basic Python types
    # list, tuple, dict, set : Python type interpreted by ast.literal_eval() -- may return None if that is given!
    # href, string, xmltree, numericunits, etc: dc_value types
    
    # if typename is None, then we evaluate as an element
    # if typename is "doc" then we evaluate as the document
    # containg the element, i.e. xmldocu, -- which for <param> elements in prx file is prxdoc
    # (i.e.. the document that contains the element)
        
    basic_python_typedict={
        "str": str,
        "float": float,
        "int": int_or_long,
        "bool": bool,
    }
    literal_python_typedict={
        "list": list,
        "tuple": tuple,
        "dict": dict,
        "set": set,
    }
    val=None
    if typename in basic_python_typedict:
        return basic_python_typedict[typename](xmldocu.gettext(element))
        pass
    elif typename in literal_python_typedict:
        return literal_python_typedict(ast.literal_eval(xmldocu.gettext(element)))
    elif typename is None:
        return element
    elif typename+"value" in dir(dcv) and issubclass(getattr(dcv,typename+"value"),dcv.value):
        return getattr(dcv,typename+"value").fromxml(xmldocu,element)
    elif typename=="doc":
        return xmldocu

    raise ValueError("Unknown typename \"%s\" evaluating %s" % (typename,dcv.hrefvalue.fromelement(xmldocu,element).humanurl()))



class stepparam(object):
    name=None
    prxdoc=None
    element=None  # element in prxdoc
    

    def __init__(self,**kwargs): # supply name and value
        self.textflag=False
        self.values=[]

        for argname in kwargs:
            if argname=="value":
                self.values.append(kwargs[argname])
                pass
            else :
                setattr(self,argname,kwargs[argname])
                pass
            pass
        pass


    def test_condition(self,outdoc,element):
        if not self.prxdoc.hasattr(self.element,"condition"):
            return True
        
        condition=self.prxdoc.getattr(self.element,"condition")
        
        
        result=outdoc.xpathsinglecontext(element,condition,variables={"filename":outdoc.get_filehref().get_bare_unquoted_filename(),"fileurl":outdoc.get_filehref().absurl()},nsmap=self.element.nsmap,noprovenance=True)

        # sys.stderr.write("test_condition: condition=%s variables=%s result=%s\n" % (self.condition,str({"filepath":outdoc.filename,"filename":os.path.split(outdoc.filename)[1]}),str(result)))

        if result==True:
            return True
        elif result==False:
            return False
        elif isinstance(result,numbers.Number):
            return result != 0
        else: 
            raise ValueError("test_condition: condition \"%s\" returned invalid result (type %s)" % (condition,result.__class__.__name__))
        pass

    def evaluateas(self,typename):
        return evaluate_from_element(self.prxdoc,self.element,typename)    
    pass


def evaluate_params(paramdict,name,typename,outdoc,element):
    params=paramdict[name]
    for param in params:
        if param.test_condition(outdoc,element):
            return param.evaluateas(typename)
        pass
    raise ValueError("No value found for parameter %s for element %s" % (name,etxpath2human(outdoc.get_canonical_etxpath(element),outdoc.nsmap)))

def findparam_concrete(prxnsmap,outdoc,element,arg_nspre,argname,argtype):
    namespaces={}
    namespaces.update(element.nsmap)
    namespaces.update(prxnsmap)
    if None in namespaces:
        del namespaces[None]
        pass

    if arg_nspre is not None:
        useargname="%s:%s" % (arg_nspre,argname)
        if arg_nspre not in namespaces:
            raise NameError("Unknown namespace prefix %s" % (arg_nspre))
        pass
    else:
        useargname=argname
        pass
    child=outdoc.child(element,useargname,namespaces=namespaces)
    if child is not None:
        return evaluate_from_element(outdoc,child,argtype)

    raise NameError("No child element found")

def findparam(prxnsmap,outdoc,element,argname):
    #     Create a parameter structure for parameter argname from outdoc
    #   element data
    #  ... xpath nsmap should come from outdoc, but updated by prxdoc



    # Argname may be the complete element name
    try: 
        ret=findparam_concrete(prxnsmap,outdoc,element,None,argname,None)
        return ret
        pass
    except NameError:
        pass
    
    if "_" in argname:
        # Argname  may be base_type
        (argnamebase,argnametype)=argname.rsplit("_",1)
        try: 
            ret=findparam_concrete(prxnsmap,outdoc,element,None,argnamebase,argnametype)
            return ret
        except NameError:
            pass

        if "_" in argnamebase:
            # Argname may be prefix_base_type
            (argnameprefix,argnamebase_noprefix)=argnamebase.split("_",1)
            try: 
                ret=findparam_concrete(prxnsmap,outdoc,element,argnameprefix,argnamebase_noprefix,argnametype)
                return ret
            except NameError:
                pass
            pass
        
        # argname maybe prefix_base
        (argnameprefix,argnamebase_noprefix)=argname.split("_",1)
        try: 
            ret=findparam_concrete(prxnsmap,outdoc,element,argnameprefix,argnamebase_noprefix,None)
            return ret
        except NameError:
            pass
        pass
    raise NameError("Element %s: No child element matching \"%s\" found!" % (dcv.hrefvalue.fromelement(outdoc,element).humanurl(),argname))

