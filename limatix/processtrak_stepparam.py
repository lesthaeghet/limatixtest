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


def evaluate_from_elements(xmldocu,elementlist,typename,paramname):
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
        if len(elementlist) > 1:
            raise ValueError("Got %d values for parameter %s" % (len(elementlist),paramname))
        elif len(elementlist) == 0:
            raise NameError("No element found")
        return basic_python_typedict[typename](xmldocu.gettext(elementlist[0]))
    elif typename in literal_python_typedict:
        if len(elementlist) > 1:
            raise ValueError("Got %d values for parameter %s" % (len(elementlist),paramname))
        elif len(elementlist) == 0:
            raise NameError("No element found")
        return literal_python_typedict(ast.literal_eval(xmldocu.gettext(elementlist[0])))
    elif typename=="nodeset":
        #import pdb as pythondb
        #pythondb.set_trace()
        return elementlist
        
    elif typename is None:
        if len(elementlist) > 1:
            raise ValueError("Got %d values for parameter %s" % (len(elementlist),paramname))
        elif len(elementlist) == 0:
            raise NameError("No element found")
        return elementlist[0]
    elif typename+"value" in dir(dcv) and issubclass(getattr(dcv,typename+"value"),dcv.value):
        if len(elementlist) > 1:
            raise ValueError("Got %d values for parameter %s" % (len(elementlist),paramname))
        elif len(elementlist) == 0:
            raise NameError("No element found")
        return getattr(dcv,typename+"value").fromxml(xmldocu,elementlist[0])
    elif typename=="doc":
        if len(elementlist) == 0:
            raise NameError("No element found")
        return xmldocu

    raise NameError("Unknown typename \"%s\" evaluating %s" % (typename,paramname))



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


    def test_condition(self,outdoc,element,inputfilehref):
        if not self.prxdoc.hasattr(self.element,"condition"):
            return True
        
        condition=self.prxdoc.getattr(self.element,"condition")
        
        
        namespaces=copy.deepcopy(self.element.nsmap)
        if None in namespaces:
            del namespaces[None]
            pass

        variables = {"outputfile":outdoc.get_filehref().get_bare_unquoted_filename(),
                     "outputfileurl":outdoc.get_filehref().absurl(),
                     "inputfile":inputfilehref.get_bare_unquoted_filename(),
                     "inputfileurl":inputfilehref.absurl(),
                     }

        result=outdoc.xpathcontext(element,condition,variables=variables,namespaces=namespaces,noprovenance=True)

        #sys.stderr.write("test_condition: condition=%s variables=%s result=%s\n" % (condition,str({"filename":outdoc.get_filehref().get_bare_unquoted_filename(),"fileurl":outdoc.get_filehref().absurl()}),str(result)))

        if result==True:
            return True
        elif result==False:
            return False
        elif isinstance(result,numbers.Number):
            return result != 0
        elif isinstance(result,list):
            # got a node-set
            return len(result) != 0
        else:
            raise ValueError("test_condition: condition \"%s\" returned invalid result (type %s)" % (condition,result.__class__.__name__))
        pass

    def evaluateas(self,typename):
        return evaluate_from_elements(self.prxdoc,[self.element],typename,self.name)    
    pass


def evaluate_params(paramdict,name,typename,outdoc,element,inputfilehref):
    params=paramdict[name]
    for param in params:
        if param.test_condition(outdoc,element,inputfilehref):
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
    children=outdoc.children(element,useargname,namespaces=namespaces)
    return evaluate_from_elements(outdoc,children,argtype,argname)
    #
    #raise NameError("No child element found")

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

        if "_" in argnamebase:
            # Argname may be prefix_base_type
            (argnameprefix,argnamebase_noprefix)=argnamebase.split("_",1)
            try: 
                ret=findparam_concrete(prxnsmap,outdoc,element,argnameprefix,argnamebase_noprefix,argnametype)
                return ret
            except NameError:
                pass
            pass

        # Argname  may be base_type
        try: 
            ret=findparam_concrete(prxnsmap,outdoc,element,None,argnamebase,argnametype)
            return ret
        except NameError:
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

