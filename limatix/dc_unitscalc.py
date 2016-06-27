#   unit-based calculator: dc_unitscalc.py

import sys

import traceback

# sys.path.append("/usr/local/dataguzzler/python")
import dg_units
from dc_value import numericunitsvalue as nuv

import math

import pygram

#sys.stderr.write("imported pygram\n");
#sys.stderr.flush()

try :
    import dc_dbus_paramclient as dcp
    pass
except :
    traceback.print_exc()
    pass
#sys.stderr.write("imported dbus_paramclient\n");
#sys.stderr.flush()

import threading
import readline

grammar=r"""

# -- CONFIGURATION SECTION ----------------------------
[
  disregard whitespace
  lexeme { inkeywd }
]


# -- FOUR FUNCTION CALCULATOR -------------------------
calculator $
 -> calculation, '\n'


calculation
 ->                                                       =nuv(0.0)
 -> unitconversion:x                                      =x
 -> name:n, '=', unitconversion:x                         =:
                  assignvar(n,x)
                  return x

inkeywd
 -> wschar, "->", wschar

unitconversion
 -> expression:x                                      =x
 -> expression:x, inkeywd, unitchars:u                   =x.inunits(u)
                  

expression
 -> term
 -> expression:x, '+', term:t                     = x+t;
 -> expression:x, '-', term:t                     = x-t;

term
 -> factor
 -> term:t, '*', factor:f                         = t*f;
 -> term:t, '/', factor:f                         = t/f;

factor
  -> power:p                                      
  -> power:p1,'^',power:p2                        =p1**p2

power
 -> name:n                                   = lookupvar(n);
 -> name:n,'(',unitconversion:arg,')'            = callfunc(n,arg)
 -> real                                     
 -> '(', unitconversion:x, ')'                        =x;

# -- LEXICAL UNITS ------------------------------------

realchars = "[-+]?(\\d+(\\.\\d*)?|\\.\\d+)([eE][-+]?\\d+)?" # this expression makes a real, from the python re documentation
unitchars = "[a-zA-Z%1][-a-zA-Z*/^+0-9.%]*"
wschar = "[ \t\r]"
comment = "/\\*.*?\\*/"

whitespace
 -> wschar
 -> comment

name  ="[a-zA-Z][a-zA-Z0-9_]*"

real
 -> realchars:c                               =nuv(float(c),"")
 -> realchars:c, unitchars:u                  =nuv(float(c),u)
 -> realchars:c, '[',unitchars:u,']'          =nuv(float(c),u)

"""

globalvars={
    "pi": nuv(math.pi,""),
    "e": nuv(math.e,""),
    }

localvars={} # dictionary of threads ids. Gives threadvarcontexts

def isnotsubcontext(subcontext,context):
    sc=subcontext.split("/")
    c=context.split("/")

    # print sc, c
    
    for idx in range(len(c)):
        if sc[idx] != c[idx]:
            return True
        pass
    return False

class threadvarcontext(object):
    contexts=None # list (stack) of (context name,context dictionary)

    def __init__(self):
        self.contexts=[]
        pass
    
    # context name is presumed to be a slash-separated string representing the full context stack (or None)
    def pushcontext(self,name=None):
        if name is not None:
            while len(self.contexts) > 0 and isnotsubcontext(name,self.contexts[-1][0]):
                sys.stderr.write("dc_unitscalc warning: %s is not a sub-context of %s (popping context)\n" % (name,self.contexts[-1][0]))
                self.contexts.pop()
                pass
            
            pass
        self.contexts.append((name,{}))
        pass
            
    def popcontext(self,name=None):
        (rmcontextname,rmcontextdict)=self.contexts[-1]
        if rmcontextname != name:
            sys.stderr.write("dc_unitscalc mismatched threadvarcontext popcontext(): %s vs. %s\n" % (rmcontextname,name))        
            pass
        self.contexts.pop()            
        
        pass
    


def pushcontext(name=None):
    tid=id(threading.current_thread())
    if not tid in localvars:
        localvars[tid]=threadvarcontext()
        pass
    
    localvars[tid].pushcontext(name)
    
    pass
    
def popcontext(name=None):
    tid=id(threading.current_thread())
    
    if not tid in localvars:
        localvars[tid]=threadvarcontext()
        pass
    
    
    localvars[tid].popcontext(name)
    pass


def callfunc(name,arg):
    if name=="sqrt":
        return pow(arg,0.5)
    

    if not hasattr(math,name):
        raise ValueError("Unknown function %s" % (name))
    
    func=getattr(math,name)

    argsimple=arg.simplifyunits()
    asunits=argsimple.units()
    if dg_units.compareunits(dg_units.parseunits(""),asunits) != 1.0:
        raise ValueError("Parameter to function %s is not unitless (has units of %s or %s)" % (name,str(arg.units()),str(asunits)))

    retval=nuv(func(argsimple.value()),"")
    
    return retval
    
def lookupvar(name):
    if name in globalvars:
        return globalvars[name]
    
    tid=id(threading.current_thread())

    if tid in localvars:
        
        if name in localvars[tid].contexts[-1][1]:
            return localvars[tid].contexts[-1][1][name]
        
        pass

    # try for a datacollect parameter

    return dcp.dc_param(name)


def assignglobal(name,val):
    if not isinstance(val,nuv):
        val=evalstr(val)
        pass
    
    globalvars[name]=val
    pass


def assignvar(name,val):
    if name in globalvars:
        raise KeyError("local variable %s shadows global" % (name))
    
    if not isinstance(val,nuv):
        val=evalstr(val)
        pass
    
    tid=id(threading.current_thread())

    if tid in localvars:
        
        localvars[tid].contexts[-1][1][name]=val
        return None
    
    
    raise KeyError(name)

def assignvarcontext(context,name,val):
    tid=id(threading.current_thread())

    if localvars[tid].contexts[-1][0] != context:
        raise ValueError("assignvarcontext: context mismatch %s vs. %s" % (context,localvars[tid].contexts[-1][0]))
    
    assignvar(name,val)
    pass

def lookupvarcontext(context,name):
    tid=id(threading.current_thread())
    
    if localvars[tid].contexts[-1][0] != context:
        raise ValueError("lookupvarcontext: context mismatch %s vs. %s" % (context,localvars[tid].contexts[-1][0]))
    
    return lookupvar(name)

def evalstr(inp):
    res=pygram.parse(grammar,inp+"\n",globals(),globals());
    return res

def evalinunits(inp,units): # returns double
    res=pygram.parse(grammar,inp+"\n",globals(),globals());
    return res.inunits(units).value()

def evalcontext(context,inp):
    tid=id(threading.current_thread())
    
    if localvars[tid].contexts[-1][0] != context:
        raise ValueError("evalcontext: context mismatch %s vs. %s" % (context,localvars[tid].contexts[-1][0]))
    
    return evalstr(inp)

def evalinunitscontext(context,inp,units): # returns double
    tid=id(threading.current_thread())
    
    if localvars[tid].contexts[-1][0] != context:
        raise ValueError("evalcontext: context mismatch %s vs. %s" % (context,localvars[tid].contexts[-1][0]))    
    
    return evalinunits(inp,units)

if __name__=="__main__":
    dg_units.units_config("insert_basic_units")

    pushcontext()
    value={}; # empty dictionary
    while (1):
        inp=raw_input("dc_unitscalc--> ");
        try :
            res=pygram.parse(grammar,inp+"\n",globals(),globals());
            print(res.format("%g"))
            pass
        except pygram.pyg_syntaxerror:
            print("Syntax error")
            pass
        except pygram.pyg_reductionexception as exc:
            if exc.value[0] is KeyError :
                print("Unknown variable %s" % (exc.value[1]))
                pass
            elif exc.value[0] is ValueError:
                print("ValueError: %s" % (exc.value[1]))
            else :
                raise
            pass
        
        pass
    popcontext()
    
    pass
