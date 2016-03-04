# This module defines a function called generate_wrapper
# that, given a (new-style) class to wrap and a dispatch function
# creates a new class that uses the dispatch function to wrap
# all method calls on the class. It is otherwise as invisible
# as possible. 
#
# Attribute access is unaffected
#
# Please note that operations like copying, pickling/unpickling, etc.
# will yield unwrapped copies unless the dispatch function
# somehow wraps the newly created object. 
import sys
import os
import types

junk=5
method_wrapper_type=junk.__str__.__class__

builtin_function_or_method_type = os.system.__class__ # os.system should consistently be a builtin

method_attr_types=[ types.MethodType, method_wrapper_type, builtin_function_or_method_type ]

if hasattr(types,"UnboundMethodType"):
    method_attr_types.append("UnboundMethodType") # Py2.x only
    pass

# set of names of Python magic methods
# magicnames omits __new__, __init__, __getattribute__,  
# otherwise this list is based on http://www.rafekettler.com/magicmethods.html    
magicnames=set(["__del__", "__cmp__", "__eq__","__ne__","__lt__","__gt__","__le__", "__ge__", "__pos__", "__neg__", "__abs__", "__invert__", "__round__", "__floor__", "__ceil__", "__trunc__", "__add__", "__sub__", "__mul__", "__floordiv__", "__div__", "__truediv__", "__mod__", "__divmod__", "__pow__", "__lshift__", "__rshift__", "__and__", "__or__", "__xor__", "__radd__", "__rsub__", "__rmul__", "__rfloordiv__", "__rdiv__", "__rtruediv__", "__rmod__", "__rdivmod__", "__rpow__", "__rlshift__", "__rrshift__", "__rand__", "__ror__", "__rxor__", "__iadd__", "__isub__", "__imul__", "__ifloordiv__", "__idiv__", "__itruediv__", "__imod__", "__ipow__", "__ilshift__", "__irshift__", "__iand__", "__ior__", "__ixor__", "__int__", "__long__", "__float__", "__complex__", "__oct__", "__hex__", "__index__", "__trunc__", "__coerce__", "__str__", "__repr__", "__unicode__", "__format__", "__hash__", "__nonzero__", "__dir__", "__sizeof__","__delattr__","__setattr__","__len__","__getitem__", "__setitem__","__delitem__","__iter__","__reversed__", "__contains__", "__missing__","__call__", "__getattr__","__enter__","__exit__","__get__","__set__","__delete__","__copy__","__deepcopy__","__getinitargs__","__getnewargs__","__getstate__","__setstate__","__reduce__","__reduce_ex__"])

if sys.version_info >= (2,7):
    magicnames.add("__subclasscheck__")  # cannot assign __subclasscheck__ prior to python 2.6
    magicnames.add("__instancecheck__") # cannot assign __instancecheck__ prior to python 2.6
    pass


def generate_wrapper_class(class_to_wrap,dispatch_function=None):
    """Generate a wrapper class for a class that uses the dispatch_function
    to perform all method calls. Specifically dispatch_function
    is called as  

       dispatch_function(wrapped_object,methodname,origmethod,*args,**kwargs)
    
    where: 
      methodname is the name of the method being called
      origmethod is the method being wrapped (callable)
      args, kwargs   parameters of the call

    NOTE: when __init__() is called, the wrapped_object does not 
    yet have its _wrappedobj attribute set. 
"""

    class wrappedclass(object):
        _wrappedobj=None
        _wrap_classdict=None # Initialized to a dictionary that is available for use -- single dictionary for all objects of this particular wrapped class
        _wrap_userdict=None # Initialized to a dictionary that is available for use -- one dictionary per instantiated object. 

        def __init__(self,*args,**kwargs):
            # print("__init__()")
            object.__setattr__(self,"_wrap_userdict",{})
            #object.__setattr__(self,"_wrappedobj",class_to_wrap(*args,**kwargs))

            object.__setattr__(self,"_wrappedobj",self._wrap("__init__",args,kwargs))
            
            pass

        def __getattribute__(self,name):
            #print("getattr(%s)"% (name))
            #origattr=super(wrappedclass,self).__getattribute__(name)
            if name == "_wrappedobj":
                return object.__getattribute__(self,"_wrappedobj")
            if name == "_wrap":
                return object.__getattribute__(self,"_wrap")
            if name == "_wrap_classdict":
                return object.__getattribute__(self,"_wrap_classdict")
            if name == "_wrap_userdict":
                return object.__getattribute__(self,"_wrap_userdict")
            
            wrappedobj=object.__getattribute__(self,"_wrappedobj")
            wrap=object.__getattribute__(self,"_wrap")
            origattr=wrappedobj.__getattribute__(name)
            if type(origattr) in method_attr_types:
                # if it is a method: Return wrapped copy
                return lambda *args, **kwargs: wrap(name,args,kwargs)
            return origattr

        #def _wrap(self,origattr,args,kwargs):
        def _wrap(self,_wrap_attrname,args,kwargs):
            if _wrap_attrname=="__init__":
                origattr=class_to_wrap
                pass
            else:
                origattr=self._wrappedobj.__getattribute__(_wrap_attrname)
                pass
            
            #print("Wrapper start")
            #print("attrname=%s" % (_wrap_attrname))
            #print("type(self)=%s" % (str(type(self))))
            #print("type(self._wrappedobj)=%s" % (str(type(self._wrappedobj))))
            #print("origattr=%s" % (str(origattr)))
            #print("args=%s" % (str(args)))
            #print("kwargs=%s" % (str(kwargs)))
            

            if dispatch_function is not None:
                return dispatch_function(self,_wrap_attrname,origattr,args,kwargs)
            else:
                result = origattr(*args,**kwargs)
                pass
            #print("Wrapper end")
            return result

        
        pass

    # override magic methods if present in original. Magic methods need
    # to be explicitly added because they cannot be overridden
    # with __getattribute__() 

    
    #setattr(wrappedclass,"__str__",lambda self, *args, **kwargs: self._wrap(object.__getattribute__(class_to_wrap,"__str__"),args,kwargs))
    
    for magicname in magicnames:
        if hasattr(class_to_wrap,magicname):
            #print("hasattr(class_to_wrap,\"%s\")" % (magicname))

            attrfunc=lambda magicname: lambda self, *args, **kwargs: self._wrap(magicname,args,kwargs)            
            setattr(wrappedclass,magicname,attrfunc(magicname))
            pass
        pass

    setattr(wrappedclass,"_wrap_classdict",{})
    #setattr(wrappedclass,"__str__",lambda self, *args, **kwargs: self._wrap(object.__getattribute__(class_to_wrap,"__str__"),args,kwargs))

    
    return wrappedclass





if __name__=="__main__":
    # Wrapper diagnostics
    
    wrappedint=generate_wrapper_class(int)
    foo=wrappedint(53)
    print(foo)
    

    class bar(object):
        bar=None
        pass

    wrappedbar=generate_wrapper_class(bar)
    fubar=wrappedbar()
    fubar.bar=32
    print(fubar)
    print(fubar.bar)
