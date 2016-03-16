
import sys
import os
import copy
import string
import traceback
import types
import re
import numpy as np
import collections


try: 
    import builtins  # python3
    pass
except ImportError: 
    import __builtin__ as builtins # python2
    pass
    
if not hasattr(builtins,"basestring"):
    basestring=str  # python3
    unicode=str # python3
    pass

if "gi" in sys.modules:  # gtk3
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import GObject as gobject
    pass
else : 
    # gtk2
    import gobject
    pass

from lxml import etree

import dataguzzler as dg
import dg_comm as dgc
from . import dg_io

from . import dc_value 

from .dc_value import stringvalue as stringv
from .dc_value import numericunitsvalue as numericunitsv

try:
    import databrowse.lib.db_lib as dbl
    pass
except ImportError:
    sys.stderr.write("paramdb2: databrowse not available... will not be able to access specimen database\n")
    dbl=None
    pass


__pychecker__="no-argsused"

# Usage examples
# stringv=dc_value.stringvalue
# numericunitsv=dc_value.numericunitsvalue
# 
# pdb=paramdb2.paramdb()
# pdb.addparamv(dgparams.dgsfile)
# pdb.addparam("meastype",stringv,options=["trialrun","sequence"])
# pdb.addparam("meastype",stringv,options=["trialrun","sequence"])
# paramdb.addparam("amplitude",numericunitsv,defunits="V",build=lambda param: paramdb2.dgcontroller(param,"AWG:AMPL"))
# *** IMPORTANT *** 
# Need to add distinction between strings and identifiers, and deal with escaping, etc. 
# Deal with unicode? 

# Not thread safe




class paramdb(dict):
    # paramdb, derived from dict, represents the entire parameter 
    # database. 
    # 
    # It internally creates a class param for each entry
    
    # BadValue=None;
    #dgio=None   # convenience storage for dgio reference
    iohandlers=None  # dictionary of i/o handlers

    
    # BUG!! Should implement iterator that ignores non-present entries
    # until then, users must check iterator keys with "if key in ..."
    
    def __init__(self,iohandlers) :
        # self.BadValue=[];
        self.iohandlers=iohandlers
        pass
    
    
    def __contains__(self,key) :
        if dict.__contains__(self,key) :
        #    value=dict.__getitem__(self,key)[0]
        #    if value is self.BadValue :
        #        return False
        #    else :
                return True
            
        else :
            return False
        pass

    def __setitem__(self,key,value):
        f = sys._current_frames().values()[0]
        name = f.f_back.f_globals['__file__']
        if name.endswith('pickle.py') or name.endswith('pickle.pyc'):
            super(paramdb,self).__setitem__(key, value)
        else:
            raise KeyError("Direct assignment of paramdb not permitted")
        pass    

    def __getitem__(self,key) :  
        value=super(paramdb,self).__getitem__(key)
        #if value is self.BadValue :
        #    raise KeyError(key)
        return value

    def addparamv(self,argskwargs):
        # Add a parameter but use a tuple of predefined (args,kwargs)
        # rather than providing the parameter inline
        (args,kwargs)=argskwargs
        return self.addparam(*args,**kwargs)

    def addparam(self,xmlname,*args,**kwargs):
        # Add a parameter with the specified xmlname (string/unicode)
        # Usage: pdb.addparam(xmlname,paramtype,options=None,build=None)
        # paramtype should be dc_value.stringvalue, dc_value.numericunitsvalue, dc_value.excitationparamsvalue, or similar
        # options is a list of suggested values for the field
        # build is a function that will be called with the param as a 
        # parameter. It will usually set-up whatever handles 
        # the assignment. For example, it might be:
        #   lambda param: dg_param.dg_paramcontroller(param,"AWG:AMPL")
        if xmlname in self:
            raise KeyError("Parameter %s already defined." % (xmlname))
        
        dict.__setitem__(self,xmlname,param(self,xmlname,*args,**kwargs))
        pass

    def addnotify(self,key,function,condition,*args):
        # print type(self)
        myparam=self[key]
        return myparam.addnotify(function,condition,*args)

    def remnotify(self,key,handle):
        myparam=self[key]
        myparam.remnotify(handle)
        pass
    pass


class etree_paramdb_ext(object): # etree extension class for paramdb that defines dc:paramdb() extension function for looking up parameters
    _paramdb=None  # paramdb instance
    extensions=None # extensions parameter for etree.xpath
    
    
    def __init__(self,paramdb):
        self._paramdb=paramdb
        functions=('param','paramdb','formatintegermindigits')
        self.extensions=etree.Extension(self,functions,ns='http://thermal.cnde.iastate.edu/datacollect')
        pass
    
    def param(self,context,name):

        if not(isinstance(name,basestring)):
            # We didn't get a string of some sort
            if isinstance(name,collections.Sequence): 
                # some sort of list
                if len(name) != 1:
                    raise ValueError("etree_paramdb_ext: XPath evaluation of dc:param() yielded %d values for parameter name" % (len(name)))
                name=name[0] # pass through to code below
                pass
            
            if not(isinstance(name,basestring)) and hasattr(name,"text"):
                name=name.text
                pass
            pass

        if not(isinstance(name,basestring)):
            raise ValueError("etree_paramdb_ext: Evaluation of XPath dc:param() function parameter does not yield a string")
        
        if not name in self._paramdb:
            raise ValueError("etree_paramdb_ext: unknown parameter \"%s\"." % (name))
        dcv=self._paramdb[name].dcvalue
        
        paramel=etree.Element(name)
        dcv.xmlrepr(None,paramel) # xml_attribute=self._paramdb[name].xml_attribute)

        return [paramel]  # return node-set

    def paramdb(self,context,name):
        # backward compatibility
        return self.param(context,name)

    def formatintegermindigits(self,context,number,mindigits):
        # Convenience extension that is used in explogwindow.py to format filenames for measurement photographs
        return "%.*d" % (int(mindigits),int(number))

    pass
    



class simplecontroller(object):
    # Simple class for controlling a parameter that accepts
    # all change requests, and handles changes instantly once mainloop is reentered
    controlparam=None
    id=None
    state=None  # see CONTROLLER_STATE defines in definition of param class
    numpending=None

    def __init__(self,controlparam):
        self.controlparam=controlparam
        self.id=id(self)
        self.state=param.CONTROLLER_STATE_QUIESCENT
        self.numpending=0

        pass


    def requestvalcallback(self,newvalue,requestid,*cbargs):
        self.numpending -= 1
        if (self.numpending==0):
            self.state=param.CONTROLLER_STATE_QUIESCENT
            pass

        
        if self.controlparam.defunits is not None:
            # force units
            self.controlparam.assignval(self.controlparam.paramtype(newvalue,units=self.controlparam.defunits),self.id)
            pass
        else :
            self.controlparam.assignval(self.controlparam.paramtype(newvalue),self.id)
            pass
        
        # self.controlparam.assignval(newvalue,self.id)            

        # print type(self.controlparam.paramtype)
        #    self.controlparam.assignval(self.controlparam.paramtype(newvalue),self.id)
        #    pass

        if len(cbargs) > 0:
            clientcallback=cbargs[0]
            clientcallback(self.controlparam,requestid,None,self.controlparam.dcvalue,*cbargs[1:])
            pass
        
        return False
 
    # requestval is a request that this parameter take on the requested value
    # (This is an asynchronous request. Will get callback when complete)
    # returns request identifier that can be used to cancel request 
    # callback(param,requestid,errorstr,newvalue,*cbargs)
    def requestval(self,param,newvalue,*cbargs):
        idstore=[]  # returned identifier is actually a list with the gobject source id as it's only element
        reqid=gobject.timeout_add(0,self.requestvalcallback,newvalue,idstore,*cbargs)
        idstore.append(reqid)
        self.state=param.CONTROLLER_STATE_REQUEST_PENDING
        self.numpending+=1
        return idstore
    

    def cancelrequest(self,param,requestid): 
        # returns True if successfully canceled
        canceled=gobject.source_remove(requestid[0])
        if canceled: 
            self.numpending -= 1
            if (self.numpending==0):
                self.state=param.CONTROLLER_STATE_QUIESCENT
                pass
            pass
        
        return canceled
    pass


class optionscontroller_xmlfile_class(simplecontroller):
    # Controller to pull options for fields  from any file's 
    # XML representation using Databrowse.  When the provided
    # fields are updated, this is triggered to pull
    # options using Databrowse.  XPath expressions are passed
    # as parameters to control the value pulled from the file.

    def __init__(self, param, filestring, fileparams, xpath, xpathparams, attribute=None, namespaces=None, **kwargs):
        simplecontroller.__init__(self, param)
        paramdb = param.parent
        for subparam in list(set(fileparams + xpathparams)):
            # If We Got a Tuple with Units, Let's Pull The Parameter Name
            if type(subparam) is tuple:
                subparam = subparam[0]
            # Verify that Driving Parameter is A String or Numeric Units Value - Throw Exception if Not
            if type(paramdb[subparam].dcvalue) is not stringv and type(paramdb[subparam].dcvalue) is not numericunitsv:
                raise Exception('Parameter %s depends on %s which is type %s - This Type is Not Supported (Must be dc_value.stringvalue or dc_value.numericunitsvalue)' % (param.xmlname, subparam, repr(type(paramdb[subparam].dcvalue))))
            # Add Notify on The Contolling Field
            paramdb[subparam].addnotify(self.xmlfileupdated, param.parent[subparam].NOTIFY_NEWVALUE, param.xmlname, filestring, fileparams, xpath, xpathparams, attribute, namespaces, **kwargs)
            pass
        pass

    @classmethod
    def xmlfileupdated(cls, param, condition, controlparam, filestring, fileparams, xpath, xpathparams, attribute, namespaces, **kwargs):
        # Callback function to handle changes to a controller field

        options = []

        try:
            paramdb = param.parent
            
            # Prepare to Fetch Filename
            valuelist = []
            for subparam in fileparams:
                # Pull Units if they Exist
                units = None
                if type(subparam) is tuple:
                    units = subparam[1]
                    subparam = subparam[0]
                # Get Value
                if type(paramdb[subparam].dcvalue) is numericunitsv:
                    valuelist.append(paramdb[subparam].value(units))
                elif type(paramdb[subparam].dcvalue) is stringv:
                    valuelist.append(str(paramdb[subparam]))
                else:
                    raise Exception('Parameter %s depends on %s which is type %s - This type is Not Supported (Must be dc_value.stringvalue or dc_value.numericunitsvalue)' % (param.xmlname, subparam, repr(type(paramdb[subparam].dcvalue))))
                pass
            valuelist = tuple(valuelist)

            # Get Filename Value
            filename = filestring % valuelist

            # Open File
            # ***!!! Should we be wrapping this in an xmldoc????
            xml = dbl.GetXML(filename, output=dbl.OUTPUT_ETREE, **kwargs)

            # Prepare to Fetch Data
            valuelist = []
            for subparam in xpathparams:
                # Pull Units if they Exist
                units = None
                if type(subparam) is tuple:
                    units = subparam[1]
                    subparam = subparam[0]
                # Get Value
                if type(paramdb[subparam].dcvalue) is numericunitsv:
                    valuelist.append(paramdb[subparam].value(units))
                elif type(paramdb[subparam].dcvalue) is stringv:
                    valuelist.append(str(paramdb[subparam]))
                else:
                    raise Exception('Parameter %s depends on %s which is type %s - This type is Not Supported (Must be dc_value.stringvalue or dc_value.numericunitsvalue)' % (param.xmlname, subparam, repr(type(paramdb[subparam].dcvalue))))
                pass
            valuelist = tuple(valuelist)

            # Get Values - xpath should be like "specimen:geometry/specimen:dimension[@direction='length']/." 
            res = xml.xpath(xpath % valuelist, namespaces=namespaces)

            # Let's Look at The Results and Determine What Course of Action to Take
            if type(res) is list:  # We Got a List of Elements Back
                for item in res:
                    if attribute is not None:
                        options.append(item.get(attribute))
                    else:
                        options.append(item.text)
            else:  # We Got a Bool, Float, or String - Use it Directly - Errors Will Be Thrown Internally if There are Type Issues
                raise Exception('XPath Expression Returned Explicit Result - Expected a List')
            
        except:
            (exctype, excvalue) = sys.exc_info()[:2]
            sys.stderr.write("%s: %s fetching options: %s\n" % (controlparam, str(exctype), str(excvalue)))
        finally:
            paramdb[controlparam].options = options
            paramdb[controlparam].do_notify(paramdb[controlparam].NOTIFY_NEWOPTIONS)

    pass


# In some cases, we may wish to set options based off of an xpath query not dependent on any parameters
# This cannot be done at startup using the optionscontroller_xmlfile_class because the parameter has
# not yet been created and therefore cannot have its options set.  This provides an option to not only
# allow options to be set from the dcc file at startup, but also to trigger options to be set on parameters
# based on the autocontroller at startup, instead of having to wait for a callback on a controlling parameter.
# THIS WILL ONLY BE CALLED ONCE AT STARTUP!
def optionscontroller_startupoptions(paramdb, controlparam, filestring, fileparams, xpath, xpathparams, attribute, namespaces, **kwargs):
    # Callback function to handle changes to a controller field

    options = []

    try:        
        # Prepare to Fetch Filename
        valuelist = []
        for subparam in fileparams:
            # Pull Units if they Exist
            units = None
            if type(subparam) is tuple:
                units = subparam[1]
                subparam = subparam[0]
            # Get Value
            if type(paramdb[subparam].dcvalue) is numericunitsv:
                valuelist.append(paramdb[subparam].value(units))
            elif type(paramdb[subparam].dcvalue) is stringv:
                valuelist.append(str(paramdb[subparam]))
            else:
                raise Exception('Parameter %s depends on %s which is type %s - This type is Not Supported (Must be dc_value.stringvalue or dc_value.numericunitsvalue)' % (param.xmlname, subparam, repr(type(paramdb[subparam].dcvalue))))
            pass
        valuelist = tuple(valuelist)

        # Get Filename Value
        filename = filestring % valuelist

        # Open File
        # ***!!! Should we be wrapping this in an xmldoc????
        xml = dbl.GetXML(filename, output=dbl.OUTPUT_ETREE, **kwargs)

        # Prepare to Fetch Data
        valuelist = []
        for subparam in xpathparams:
            # Pull Units if they Exist
            units = None
            if type(subparam) is tuple:
                units = subparam[1]
                subparam = subparam[0]
            # Get Value
            if type(paramdb[subparam].dcvalue) is numericunitsv:
                valuelist.append(paramdb[subparam].value(units))
            elif type(paramdb[subparam].dcvalue) is stringv:
                valuelist.append(str(paramdb[subparam]))
            else:
                raise Exception('Parameter %s depends on %s which is type %s - This type is Not Supported (Must be dc_value.stringvalue or dc_value.numericunitsvalue)' % (param.xmlname, subparam, repr(type(paramdb[subparam].dcvalue))))
            pass
        valuelist = tuple(valuelist)

        # Get Values - xpath should be like "specimen:geometry/specimen:dimension[@direction='length']/." 
        res = xml.xpath(xpath % valuelist, namespaces=namespaces)

        # Let's Look at The Results and Determine What Course of Action to Take
        if type(res) is list:  # We Got a List of Elements Back
            for item in res:
                if attribute is not None:
                    options.append(item.get(attribute))
                else:
                    options.append(item.text)
        else:  # We Got a Bool, Float, or String - Use it Directly - Errors Will Be Thrown Internally if There are Type Issues
            raise Exception('XPath Expression Returned Explicit Result - Expected a List')
        
    except:
        (exctype, excvalue) = sys.exc_info()[:2]
        sys.stderr.write("%s: %s fetching options: %s\n" % (controlparam, str(exctype), str(excvalue)))
    finally:
        paramdb[controlparam].options = options
        paramdb[controlparam].do_notify(paramdb[controlparam].NOTIFY_NEWOPTIONS)

def optionscontroller_xmlfile(param, filestring, fileparams, xpath, xpathparams, attribute=None, namespaces=None, **kwargs):
    # Controller to Pull Options from any file using Databrowse and an XPath Expression
    # Will Take a List of Parameters from paramdb to Substitue into the Filename and
    #   the XPath Expression
    # Additional keyword arguments are passed directly to dbl.GetXML()
    # Will Trigger an Update Any Time Any Controlling Parameter is Updated
    # fileparams and xpath params are a list of strings of the xmlname of
    #   parameters that should be substituted into filestring or xpath,
    #   respectively, that will be expanded to their values on update
    # fileparams and xpath params must be numericunitsvalue or stringvalue
    #   types - numericunitsvalues are passed in default units as just
    #   the contained value
    # attribute can be used to specify an attribute on the elements
    #   selected to be used as the option value instead of the text of the
    #   element - None to use text of element
    # In lieu of a string, a numericunitsvalue can be passed in as a tuple
    #   of the format (xmlname, desiredunits)
    #   For Example:  ['specimen', ('pressure', 'psi'), 'perfby']
    # fileparams and xpathparams MUST ALWAYS be lists
    # Example Usage for Flaw Index in Specimen Database:
    #   optionscontroller_xmlfile(param, os.path.join('/databrowse/specimens', '%s.sdb'), ['specimen'], 'specimen:flawparameters', [], attribute='index', namespaces={'specimen':'http://thermal.cnde.iastate.edu/specimen'})
    if dbl is None: 
        # specimen database not available.... allow manual control
        return simplecontroller(param)
        pass
    else : 
        return optionscontroller_xmlfile_class(param, filestring, fileparams, xpath, xpathparams, attribute, namespaces, **kwargs)
    pass


class threadserializedcontroller(object):
    # Class for controlling a parameter for on object wrapped
    # using threadserializedwrapper
    id=None
    controlparam=None   # link to the class param
    serializedobject=None
    setter=None
    getter=None
    saver=None
    pollms=None
    state=None  # see CONTROLLER_STATE defines in definition of param class
    pendingrequest=None  # currently pending request tuple
    old_pending_requests=None # list of old pending request tuples that haven't come back yet
    
    def __init__(self,controlparam,serializedobject,getter=None,setter=None,saver=None,pollms=2000.0):
        self.id=id(self)
        self.controlparam=controlparam
        self.serializedobject=serializedobject
        self.getter=getter
        self.setter=setter
        self.saver=saver
        self.pollms=pollms
        self.state=param.CONTROLLER_STATE_QUIESCENT
        self.old_pending_requests=[]
    
        

        # Request repeated calls to doquery() every pollms milliseconds
        if self.pollms >= 0.0 and self.getter is not None:
            gobject.timeout_add(int(self.pollms),self.doquery)
            pass
        
        pass


    def doquery(self):
        if self.state!=param.CONTROLLER_STATE_QUIESCENT:
            # sys.stderr.write("paramdb: %s: id(self.pendingrequest)=%s\n" % (self.controlparam.xmlname,str(id(self.pendingrequest))))
            # Don't do query unless nothing else is happening
            assert(self.pendingrequest is not None)
            return True
 
        assert(self.pendingrequest is None)
   

        #if isinstance(self.getter,types.MethodType):
            # Bound method... do not provide serializedojbect
            # as first parameter

            # gobject_callback kwparam never really goes to the
            # getter but is stripped and handled by
            # threadserializedwrapper.wrap_dispatch()
        #    self.pending_request=self.getter(gobject_callback=(self.callback,None)) # No additional callback params for a query
        #    pass
        #else:
            #import pdb as pythondb
            #pythondb.set_trace()
        #    sys.stderr.write("type(self.getter)=%s\n" % (str(type(self.getter))))
        #    self.pending_request=self.getter(self.serializedobject,gobject_callback=(self.callback,None))  # No additional callback params for a query
        #    pass
        
        # (Checking for bound vs. unbound method (As above) turns out to 
        # be unnecessary and problematic... because due to the 
        # threadserializedwrapper it will always show up as a function,
        # even if it is actually a method
        
        self.state=param.CONTROLLER_STATE_REQUEST_PENDING
        self.pendingrequest=self.getter(gobject_callback=(self.callback,None)) # No additional callback params for a query
        # sys.stderr.write("doquery(): id(self.pendingrequest)=%s\n" % (str(id(self.pendingrequest))))

        return True  # Get called-back again in another pollms seconds

    
    def callback(self,request_tuple,result,additional_callback_params):
        old=False
        if self.pendingrequest is request_tuple:
            # sys.stderr.write("callback(): id(self.pendingrequest)=%s\n" % (str(id(self.pendingrequest))))
            self.pendingrequest=None
            self.state=param.CONTROLLER_STATE_QUIESCENT
            pass
        else:
            if not (request_tuple in self.old_pending_requests):
                # sys.stderr.write("paramdb2: id(pendingrequest)=%s\n" % (str(id(self.pendingrequest))))
                # sys.stderr.write("paramdb2: id(request_tuple)=%s\n" % (str(id(request_tuple))))
                # sys.stderr.write("paramdb2: old_pending_requests=%s\n" % (str(self.old_pending_requests)))
                pass
            assert(request_tuple in self.old_pending_requests)
            self.old_pending_requests.remove(request_tuple)
            old=True
            pass
        
            
        if not old and not isinstance(result,BaseException):

            # Request succeeded
            lastvalue=self.controlparam.dcvalue

            try:

                thisvalue=self.controlparam.paramtype(result,defunits=self.controlparam.defunits)
                pass
            except:
                (exctype, excvalue) = sys.exc_info()[:2] 
                            
                
                sys.stderr.write("%s assigning value %s to %s: %s\n" % (str(exctype.__name__),str(result),self.controlparam.xmlname,excvalue))
                traceback.print_exc()
                
                thisvalue=self.controlparam.paramtype("",defunits=self.controlparam.defunits)
                pass
            
            #if self.controlparam.paramtype is dc_value.hrefvalue:
            #    sys.stderr.write("paramdb2: assigning %s to %s\n" % (str(thisvalue.contextlist),self.controlparam.xmlname))
            #    pass

            if not lastvalue.equiv(thisvalue):
                self.controlparam.assignval(thisvalue,self.id)
                pass

            if additional_callback_params is not None and len(additional_callback_params) > 0:
                # our client asked for a callback
                clientcallback=additional_callback_params[0]
                cbrunargs=additional_callback_params[1:]
                
                clientcallback(self.controlparam,id(request_tuple),None,self.controlparam.dcvalue,*cbrunargs)

                pass


            
            
            pass
        else:
            # request failed
            reqid=None

            if request_tuple is not None:
                reqid=id(request_tuple)
                pass
            
            if additional_callback_params is not None and len(additional_callback_params) > 0:
                # our client asked for a callback
                clientcallback=additional_callback_params[0]
                cbrunargs=additional_callback_params[1:]
                clientcallback(self.controlparam,reqid,result,None,*cbrunargs)
                pass
            pass
        return False

    def _cancelpending(self):
        pendingrequest=self.pendingrequest
        if pendingrequest is not None and self.serializedobject._wrap_classdict["threadmanager"].attempt_cancel_call(self.pendingrequest) is not None:
            # success in canceling
            # sys.stderr.write("_cancelpending: request %s cleared\n" % (str(id(pendingrequest))))
            self.pendingrequest=None
            self.state=param.CONTROLLER_STATE_QUIESCENT

            # move to old_pending_requests
            self.old_pending_requests.append(pendingrequest)
 
            # extract callback info from pendingrequest (this is the tuple from threadserializedwrapper.py
            (cls,method,args,kwargs,callback_and_params,returnlist,donenotifyevent)=pendingrequest            
            # trigger callback with error return
            gobject.timeout_add(0,self.callback,pendingrequest,ValueError("Command overridden by new request"),callback_and_params[1])
            
            

            
            pass
        else:
            # Could not cancel... move to old_pending_requests
            self.old_pending_requests.append(pendingrequest)
            # sys.stderr.write("_cancelpending: request %s moved to old\n" % (str(id(pendingrequest))))
            self.pendingrequest=None
            self.state=param.CONTROLLER_STATE_QUIESCENT
            pass
        pass
    
    def requestval(self,param,newvalue,*cbargs):
        # print "requestval %s = %s" % (param.xmlname,str(newvalue))

        if self.state != param.CONTROLLER_STATE_QUIESCENT:
            # Cancel current pending request
            self._cancelpending()
            pass

        assert(self.pendingrequest is None)
        self.state=param.CONTROLLER_STATE_REQUEST_PENDING
        
        try:
            #if isinstance(self.setter,types.MethodType):
                # Bound method... do not provide serializedojbect
                # as first parameter
                
                # gobject_callback kwparam never really goes to the
                # getter but is stripped and handled by
                # threadserializedwrapper.wrap_dispatch()

            # create dummy request tuple to use if we don't manage to assign the real one
            #(cls,method,args,kwargs,callback_and_params,returnlist,donenotifyevent)
            self.pendingrequest=(None,None,None,None,(self.callback,cbargs),None,None)
            self.state=param.CONTROLLER_STATE_REQUEST_PENDING

            if self.setter is not None:
                self.pendingrequest=self.setter(newvalue,gobject_callback=(self.callback,cbargs))
                pass
            #elif self.setter is not None:
            #    self.pendingrequest=self.setter(self.serializedobject,newvalue,gobject_callback=(self.callback,cbargs))
            #    pass
            else:
                # no setter. This is a read-only parameter
                # OK to set to blank
                if newvalue.isblank():
                    # perform assignment if necessary

                    if not self.controlparam.dcvalue.equiv(newvalue):
                        self.controlparam.assignval(newvalue,self.id)
                        pass

                    # Request callback in gobject mainloop
                    gobject.timeout_add(0,self.callback,request_tuple,newvalue,cbargs)
                    pass
                else: 
                    raise ValueError("Parameter %s is not settable" % (self.controlparam.xmlname))
                pass
            pass
        except:
            (exctype,excvalue)=sys.exc_info()[:2]
            sys.stderr.write("paramdb2: Exception attempting to assign to %s... Making callback with exception \n" % (self.controlparam.xmlname))
            gobject.timeout_add(0,self.callback,self.pendingrequest,excvalue,cbargs)
            return None  # BUG: Should probably return valid request id in this case. Otherwise we use dgio idents, which are the id() of the pendingcommand structure
        reqid=id(self.pendingrequest)
        return reqid
    

    def cancelrequest(self,param,requestid): 
        # returns True if successfully canceled

        if id(self.pendingrequest)==requestid:
            # request to be cancelled is current... Cancel it!
            if self.serializedobject._wrap_classdict["threadmanager"].attempt_cancel_call(self.pendingrequest) is not None:
                # success in canceling
                # sys.stderr.write("cancelrequest: success on %s\n" % (str(id(self.pendingrequest))))
                self.pendingrequest=None
                self.state=param.CONTROLLER_STATE_QUIESCENT
    
                return True
            pass
        return False

    # Special method: perform_save()
    # works with dc_paramsavestep to issue a command
    # that performs a save and stores the URL in this 
    # parameter.
    #
    # Usually in this value you would set reset_with_meas_record=True
    # so it gets reset between measurement steps, and you would set
    # dangerous=True so it doesn't get restored, and you
    # would use it with a param that is an hrefvalue
    # and you would set pollms to -1.0 so it doesn't get polled
    #
    # perform_save() uses the saver routine
    def perform_save(self,param,savefilehref,*cbargs):

        if self.state != param.CONTROLLER_STATE_QUIESCENT:
            # Cancel current pending request
            self._cancelpending()
            pass

        assert(self.pendingrequest is None)
        self.state=param.CONTROLLER_STATE_REQUEST_PENDING
        
        # create dummy request tuple to use if we don't manage to assign the real one
            #(cls,method,args,kwargs,callback_and_params,returnlist,donenotifyevent)
        self.pendingrequest=(None,None,None,None,(self.callback,cbargs),None,None)
        self.state=param.CONTROLLER_STATE_REQUEST_PENDING
        try:
            #if isinstance(self.saver,types.MethodType):
            #    # Bound method... do not provide serializedojbect
            #    # as first parameter
            #    
            #    # gobject_callback kwparam never really goes to the
            #    # getter but is stripped and handled by
            #    # threadserializedwrapper.wrap_dispatch()
            self.pendingrequest=self.saver(savefilehref,gobject_callback=(self.callback,cbargs))
            #    pass
            #elif self.saver is not None:
            #    self.pendingrequest=self.saver(self.serializedobject,savefilehref,gobject_callback=(self.callback,cbargs))
            #    pass
            #else:
            #    raise ValueError("Attempt to perform save with no saver function set!")
            pass
        except:
            (exctype,excvalue)=sys.exc_info()[:2]
            sys.stderr.write("Exception issuing command... Should get callback with exception \n")
            gobject.timeout_add(0,self.callback,self.pendingrequest,excvalue,cbargs)
            return None  # BUG: Should probably return valid request id in this case. Otherwise we use dgio idents, which are the id() of the pendingcommand structure
        reqid=id(self.pendingrequest)
        return reqid
            
    
    pass



class dgcontroller(object):
    # Class for controlling a parameter that uses dataguzzler to manage
    # change requests
    controlparam=None  # link to the class param.... controlparam.iohandlers["dgio"] is the dgio instance.
    dgparam=None
    quote=None   # Should the value be quoted/unquoted before transmission? 
    escape=None  # Should unusual characters in the value be escaped before transmission (if not, they are invalid!)
    id=None
    state=None  # see CONTROLLER_STATE defines in definition of param class
                # (dg_io performs background repetitive query that qualifies as quiescent)
    numpending=None  # number of pending commands.
    querytype=None # dg_io querytype to use

    # set dgparam to None for perform_save() parameters
    def __init__(self,controlparam,dgparam,quote=False,escape=False,querytype=dg_io.io.QT_GENERIC):
        self.controlparam=controlparam
        self.dgparam=dgparam
        self.quote=quote
        self.escape=escape
        self.querytype=querytype
        self.id=id(self)
        self.state=param.CONTROLLER_STATE_QUIESCENT
        self.numpending=0
        if not self.controlparam.iohandlers["dgio"].commstarted:
            sys.stderr.write("dgcontroller: attempting to create dataguzzler parameter %s (%s) even though communication link not started!\n" % (self.controlparam.xmlname,self.dgparam))
            pass
        elif len(self.controlparam.iohandlers["dgio"].connfailindicator) > 0:
            sys.stderr.write("dgcontroller: attempting to create dataguzzler parameter %s (%s) even though dataguzzler communication link has failed!\n" % (self.controlparam.xmlname,self.dgparam))
            pass


        self.startquery()
        pass


    def do_quote_escape(self,paramstr):
        if self.quote and not self.escape:
            if ("\n" in paramstr or 
                "\r" in paramstr or 
                "\0" in paramstr or 
                ";" in paramstr or
                "\"" in paramstr):
                raise ValueError("Illegal character in unescaped parameter \"%s\"" % (dg.escapestr(paramstr)))
            
            return "\"%s\"" % (paramstr)

        elif self.quote and self.escape:
            return "\"%s\"" % (dg.escapestr(paramstr))
        
        elif not self.quote and not self.escape:
            if ("\n" in paramstr or 
                "\r" in paramstr or 
                "\0" in paramstr or 
                ";" in paramstr):
                raise ValueError("Illegal character in unescaped parameter \"%s\"" % (dg.escapestr(paramstr)))

            return paramstr

        elif not self.quote and self.escape:
            return dg.escapestr(paramstr)
        
        pass
    

    def do_unquote_unescape(self,paramstr):
        if self.quote and not self.escape:
            if paramstr[0] != "\"" or paramstr[-1] != "\"":
                raise ValueError("Quoted response %s is missing quotes")
            return paramstr[1:-1]
        
        
        if self.quote and self.escape:
            if paramstr[0] != "\"" or paramstr[-1] != "\"":
                raise ValueError("Quoted response %s is missing quotes")
            return dg.unescapestr(paramstr[1:-1])

        if not self.quote and not self.escape:
            return paramstr

        if not self.quote and self.escape:
            return dg.unescapestr(paramstr)
        pass


    def performsavecallback(self,reqid,fullquery,retcode,fullresponse,result,cbargs):
        # sys.stderr.write("performsavecallback. fullresponse=%s\n" % (fullresponse))
        self.numpending -= 1
        if (self.numpending==0):
            self.state=param.CONTROLLER_STATE_QUIESCENT
            self.startquery()
            pass

        clientcallback=None

        if len(cbargs) > 0:
            clientcallback=cbargs[0]
            cbrunargs=cbargs[1:]
            pass

        if retcode != 200:
            # error return

            assert(isinstance(result,BaseException))
            
            
        
            if clientcallback is not None:
                clientcallback(self.controlparam,reqid,fullresponse,None,*cbrunargs)
                pass
        
            return False
        
        assert(isinstance(result,dc_value.hrefvalue))

        try: 
            self.controlparam.assignval(result,self.id)

            pass
        except :
            (exctype, value) = sys.exc_info()[:2] 
            if clientcallback is not None:
                clientcallback(self.controlparam,reqid,"Exception assigning value: %s(%s)" % (str(exctype),str(value)),None,*cbrunargs)
                pass
            return False
        
        if clientcallback is not None:
            clientcallback(self.controlparam,reqid,None,self.controlparam.dcvalue,*cbargs[1:])
            pass
        
        return False

    
    def requestvalcallback(self,reqid,fullquery,retcode,fullresponse,result,cbargs):
        # sys.stderr.write("requestvalcallback. fullresponse=%s\n" % (fullresponse))
        self.numpending -= 1
        if (self.numpending==0):
            self.state=param.CONTROLLER_STATE_QUIESCENT
            self.startquery()
            pass

        clientcallback=None

        if len(cbargs) > 0:
            clientcallback=cbargs[0]
            cbrunargs=cbargs[1:]
            pass

        if retcode != 200:
            # error return
            if clientcallback is not None:
                clientcallback(self.controlparam,reqid,fullresponse,None,*cbrunargs)
                pass
        
            return False
        

        # print type(self.controlparam.paramtype)
        try :
            if self.controlparam.defunits is not None:
                newvalue=self.controlparam.paramtype(self.do_unquote_unescape(result),defunits=self.controlparam.defunits)
                pass
            else :
                newvalue=self.controlparam.paramtype(self.do_unquote_unescape(result))
                pass
            # print "assigning value: %s from %s" % (str(newvalue),self.do_unquote_unescape(result))
            self.controlparam.assignval(newvalue,self.id)

            pass
        except :
            (exctype, value) = sys.exc_info()[:2] 
            if clientcallback is not None:
                clientcallback(self.controlparam,reqid,"Exception assigning value: %s(%s)" % (str(exctype),str(value)),None,*cbrunargs)
                pass
            return False
        
        if clientcallback is not None:
            clientcallback(self.controlparam,reqid,None,self.controlparam.dcvalue,*cbargs[1:])
            pass
        
        return False


    
    def requestvalerrorcallback(self,e,*cbargs):
        # also used for save errors
        # sys.stderr.write("requestvalcallback. e=%s\n" % (str(e)))
        clientcallback=None
        
        if len(cbargs) > 0:
            clientcallback=cbargs[0]
            pass
        
        if clientcallback is not None:
            clientcallback(self.controlparam,None,e,None,*cbargs[1:])
            pass
        pass
    
    # requestval is a request that this parameter take on the requested value
    # (This is an asynchronous request. Will get callback when complete)
    # returns request identifier that can be used to cancel request 
    # callback(param,requestid,errorstr,newvalue,*cbargs)
    def requestval(self,param,newvalue,*cbargs):
        # print "requestval %s = %s" % (param.xmlname,str(newvalue))

        self.state=param.CONTROLLER_STATE_REQUEST_PENDING
        self.numpending+=1
        self.stopquery()


        if self.dgparam is None:
            # attempt to write a param with NULL dgparam
            # only case of this is dgsfile or setfile or similar
            # perform_save command
            # Only legitimate value to write is blank
            assert(newvalue.isblank())
            reqid=id(newvalue)
            fullcommand=""
            retcode=200
            fullresponse=""
            result=newvalue
            
            gobject.timeout_add(0,self.performsavecallback,reqid,fullcommand,retcode,fullresponse,result,cbargs)
            return reqid

        if not self.controlparam.iohandlers["dgio"].commstarted:
            sys.stderr.write("dgcontroller: attempting to write dataguzzler parameter %s (%s) even though communication link not started!\n" % (self.controlparam.xmlname,self.dgparam))
            pass
        elif len(self.controlparam.iohandlers["dgio"].connfailindicator) > 0:
            sys.stderr.write("dgcontroller: attempting to write dataguzzler parameter %s (%s) even though dataguzzler communication link has failed!\n" % (self.controlparam.xmlname,self.dgparam))
            pass



        try:
            if self.querytype==dg_io.io.QT_EXCPARAMS:
                reqid=self.controlparam.iohandlers["dgio"].issuecommand(None,"%s:%s" % (self.dgparam.split(":")[-2],self.do_quote_escape(str(newvalue))),self.requestvalcallback,cbargs,self.querytype)
                pass
            else :
                reqid=self.controlparam.iohandlers["dgio"].issuecommand(None,"%s %s" % (self.dgparam,self.do_quote_escape(str(newvalue))),self.requestvalcallback,cbargs,self.querytype)
                pass
            pass
        except ValueError as e:
            sys.stderr.write("Exception issuing command... Should get requestvalerrorcallback\n")
            gobject.timeout_add(0,self.requestvalerrorcallback,e,*cbargs)
            return None  # BUG: Should probably return valid request id in this case. Otherwise we use dgio idents, which are the id() of the pendingcommand structure1
            pass
        
            
        return reqid



    # perform_save is a request that this parameter be saved to disk
    # taking on the href of the save file as its value
    # (This is an asynchronous request. Will get callback when complete)
    # returns request identifier that can be used to cancel request 
    # callback(param,requestid,errorstr,newvalue,*cbargs)
    def perform_save(self,param,savehref,*cbargs):
        # print "requestval %s = %s" % (param.xmlname,str(newvalue))

        if not issubclass(self.controlparam.paramtype,dc_value.hrefvalue):
            raise ValueError("paramdb2.perform_save(%s):  Method only applies to parameters of hrefvalue type" (self.controlparam.xmlname))
        
        self.state=param.CONTROLLER_STATE_REQUEST_PENDING
        self.numpending+=1
        self.stopquery()

        if not self.controlparam.iohandlers["dgio"].commstarted:
            sys.stderr.write("dgcontroller: attempting to save dataguzzler parameter %s (%s) even though communication link not started!\n" % (self.controlparam.xmlname,self.dgparam))
            pass
        elif len(self.controlparam.iohandlers["dgio"].connfailindicator) > 0:
            sys.stderr.write("dgcontroller: attempting to save dataguzzler parameter %s (%s) even though dataguzzler communication link has failed!\n" % (self.controlparam.xmlname,self.dgparam))
            pass
        
        

        try:
            reqid=self.controlparam.iohandlers["dgio"].performsave(None,savehref,self.controlparam.save_extension,self.performsavecallback,cbargs)
            pass
        except ValueError as e:
            sys.stderr.write("Exception performing save... Should get requestvalerrorcallback\n")
            gobject.timeout_add(0,self.requestvalerrorcallback,e,*cbargs)
            return None  # BUG: Should probably return valid request id in this case. Otherwise we use dgio idents, which are the id() of the pendingcommand structure
            pass
        
            
        return reqid

    

    def cancelrequest(self,param,requestid): 
        # returns True if successfully canceled
        canceled=self.controlparam.iohandlers["dgio"].abortcommand(requestid)
        if canceled: 
            self.numpending -= 1
            if self.numpending == 0:
                self.state=param.CONTROLLER_STATE_QUIESCENT
                self.startquery()
                pass
            pass
        
        return canceled

    def startquery(self):
        assert(self.state==param.CONTROLLER_STATE_QUIESCENT)
        assert(self.numpending==0)

        if self.dgparam is None:  # this is a perform_save() parameter
            return

        paramsplit=self.dgparam.split()
        paramsplit[0]+="?"
        paramstring=" ".join(paramsplit)

        self.controlparam.iohandlers["dgio"].addquery(id(self),paramstring,self.querycallback,None,self.querytype)
        pass

    def stopquery(self):
        if self.dgparam is None:  # this is a perform_save() parameter
            return

        self.controlparam.iohandlers["dgio"].remquery(id(self))

        pass
    
    def querycallback(self,id,fullquery,retcode,fullresponse,result,queryparam):
        # print("Got query callback: %s" % (fullresponse))
        if (self.state != param.CONTROLLER_STATE_QUIESCENT):
            return # extraneous callback
        
        lastvalue=self.controlparam.dcvalue
        thisvalue=None
        
        try : 
            if self.controlparam.defunits is not None:
                thisvalue=self.controlparam.paramtype(self.do_unquote_unescape(result),defunits=self.controlparam.defunits)
                pass
            else : 
                thisvalue=self.controlparam.paramtype(self.do_unquote_unescape(result))
                pass
            pass
        except : 
            (exctype, excvalue) = sys.exc_info()[:2] 
            

            sys.stderr.write("%s assigning value %s from %s to %s: %s\n" % (str(exctype),self.do_unquote_unescape(result),self.dgparam,self.controlparam.xmlname,excvalue))
            traceback.print_exc()
            
            thisvalue=self.controlparam.paramtype("",defunits=self.controlparam.defunits)
            
            pass
        
	#print "In paramdb2 [%s]:  lastvalue = %s, thisvalue = %s" % (self.controlparam.xmlname, str(lastvalue), str(thisvalue))
        #print "lastvalue.equiv(thisvalue) is %s" % (str(lastvalue.equiv(thisvalue)))

        if not lastvalue.equiv(thisvalue):
            #print "Calling assignval"
            self.controlparam.assignval(thisvalue,self.id)            
            pass
        
        return False    

    pass

class dgcontroller_nummathparam(dgcontroller):
    mathname=None
    commandformat=None # format string with "%s" where value should be inserted, e.g. "MATH:DEF foo=mul(bar,%s)" 
    interpretre=None   # interpret re is the regular expression to use to interpret the dataguzzler query and response. Match with this re, then extract element #interpretregroupnum, which should contain both number and units, if applicable. 
    interpretrecompiled=None
    interpretregroupnum=None

    def __init__(self,controlparam,mathname,commandformat,interpretre,interpretregroupnum):
        dgcontroller.__init__(self,controlparam,"MATH:DEF %s" % (mathname),quote=False,escape=False,querytype=dg_io.io.QT_GENERIC)
        self.mathname=mathname
        self.commandformat=commandformat
        self.interpretre=interpretre
        self.interpretrecompiled=re.compile(self.interpretre)
        self.interpretregroupnum=interpretregroupnum
        pass

    def requestvalcallback(self,reqid,fullquery,retcode,fullresponse,result,cbargs):
        # print "requestvalcallback. fullresponse=%s" % (fullresponse)
        self.numpending -= 1
        if (self.numpending==0):
            self.state=param.CONTROLLER_STATE_QUIESCENT
            self.startquery()
            pass

        newvalue=None

        clientcallback=None

        if len(cbargs) > 0:
            clientcallback=cbargs[0]
            cbrunargs=cbargs[1:]
            pass

        #if retcode != 200:
        #    # error return
        #    if clientcallback is not None:
        #        clientcallback(self.controlparam,reqid,fullresponse,None,*cbrunargs)
        #        pass
        # 
        # return False

        matchobj=self.interpretrecompiled.match(fullresponse)
        if retcode != 200 or matchobj is None:
            if not fullresponse.startswith("MATH:UNDEF ") and not fullresponse.startswith("MATH:ERROR_CHANNEL_NOT_FOUND"):
                sys.stderr.write("dgcontroller_nummathparam(%s): dg_response to value request \"%s\" does not match RE \"%s\"\n" % (self.mathname,fullresponse,self.interpretre))
                pass
            
            # Failed match means NaN parameter
            if self.controlparam.defunits is not None:
                newvalue=self.controlparam.paramtype("NaN",units=self.controlparam.defunits,defunits=self.controlparam.defunits)
                pass
            else :
                newvalue=self.controlparam.paramtype("NaN")
                pass
            pass
        else : 

            # print type(self.controlparam.paramtype)
            try :
                if self.controlparam.defunits is not None:
                    # sys.stderr.write("Match groups: %s\n" % (str(matchobj.groups())))
                    newvalue=self.controlparam.paramtype(matchobj.group(self.interpretregroupnum),defunits=self.controlparam.defunits)
                    pass
                else :
                    newvalue=self.controlparam.paramtype(self.interpretregroupnum)
                    pass
                # print "assigning value: %s from %s" % (str(newvalue),self.do_unquote_unescape(result))
                
                pass
            except :
                (exctype, value) = sys.exc_info()[:2] 
                if clientcallback is not None:
                    clientcallback(self.controlparam,reqid,"Exception extracting value: %s(%s)" % (str(exctype),str(value)),None,*cbrunargs)
                    pass
                return False
            pass
        try :

            self.controlparam.assignval(newvalue,self.id)
        except :
            (exctype, value) = sys.exc_info()[:2] 
            if clientcallback is not None:
                clientcallback(self.controlparam,reqid,"Exception assigning value: %s(%s)" % (str(exctype),str(value)),None,*cbrunargs)
                pass
            return False
            
        
        if clientcallback is not None:
            clientcallback(self.controlparam,reqid,None,self.controlparam.dcvalue,*cbargs[1:])
            pass
        
        return False
    
    
    # requestvalerrorcallback(): Just use superclass

    # requestval is a request that this parameter take on the requested value
    # (This is an asynchronous request. Will get callback when complete)
    # returns request identifier that can be used to cancel request 
    # callback(param,requestid,errorstr,newvalue,*cbargs)
    def requestval(self,param,newvalue,*cbargs):
        # print "requestval %s = %s" % (param.xmlname,str(newvalue))
    
        self.state=param.CONTROLLER_STATE_REQUEST_PENDING
        self.numpending+=1
        self.stopquery()
        
        
        
        try:
            if np.isnan(newvalue.value()):
                # sys.stderr.write("Issuing command: MATH:UNDEF %s\n" % (self.mathname))
                reqid=self.controlparam.iohandlers["dgio"].issuecommand(None,"MATH:UNDEF %s" % (self.mathname),self.requestvalcallback,cbargs,self.querytype)
                
            else :
                # sys.stderr.write("Issuing command: %s\n" % (self.commandformat % (str(newvalue))))
                reqid=self.controlparam.iohandlers["dgio"].issuecommand(None,self.commandformat % (str(newvalue)),self.requestvalcallback,cbargs,self.querytype)
                pass

            pass
        except ValueError as e:
            gobject.timeout_add(0,self.requestvalerrorcallback,e,*cbargs)
            return None  # BUG: Should probably return valid request id in this case. Otherwise we use dgio idents, which are the id() of the pendingcommand structure
        
        
        return reqid

    
    # cancelrequest() just use superclass

    # startquery() just use superclass
    # stopquery() just use superclass()

    def querycallback(self,id,fullquery,retcode,fullresponse,result,queryparam):
        # print("Got query callback: %s" % (fullresponse))
        if (self.state != param.CONTROLLER_STATE_QUIESCENT):
            return # extraneous callback
        
        lastvalue=self.controlparam.dcvalue
        thisvalue=None
        
        if fullresponse.startswith("MATH:ERROR_CHANNEL_NOT_FOUND"):
            # No channel defined... parameter unset
            if self.controlparam.defunits is not None:
                thisvalue=self.controlparam.paramtype("NaN",units=self.controlparam.defunits,defunits=self.controlparam.defunits)
                return False
            else :
                thisvalue=self.controlparam.paramtype("NaN")
                return False
            pass

        matchobj=self.interpretrecompiled.match(fullresponse)
        if matchobj is None:
            sys.stderr.write("dgcontroller_nummathparam(%s): dg_response to query \"%s\" does not match RE \"%s\"\n" % (self.mathname,fullresponse,self.interpretre))
            return False
        try : 
            if self.controlparam.defunits is not None:
                #sys.stderr.write("Match groups: %s\n" % (str(matchobj.groups())))
                thisvalue=self.controlparam.paramtype(matchobj.group(self.interpretregroupnum),defunits=self.controlparam.defunits)
                pass
            else : 
                thisvalue=self.controlparam.paramtype(self.interpretregroupnum)
                pass
            pass
        except : 
            (exctype, excvalue) = sys.exc_info()[:2] 
            
                
            sys.stderr.write("%s assigning value %s from %s to %s: %s\n" % (str(exctype),self.do_unquote_unescape(result),self.dgparam,self.controlparam.xmlname,excvalue))
            traceback.print_exc()
            
            thisvalue=self.controlparam.paramtype("NaN",defunits=self.controlparam.defunits)
            
            pass
        pass

	#print "In paramdb2 [%s]:  lastvalue = %s, thisvalue = %s" % (self.controlparam.xmlname, str(lastvalue), str(thisvalue))
        #print "lastvalue.equiv(thisvalue) is %s" % (str(lastvalue.equiv(thisvalue)))
            
        if not lastvalue.equiv(thisvalue):
            #print "Calling assignval"
            self.controlparam.assignval(thisvalue,self.id)            
            pass
        
        return False    
    
    
    pass


class autocontrollerbase(object):
    # Simple base class for a controller that automatically 
    # determines values for a parameter

    # When subclassing, 
    #   * Remember to call this class's __init__
    #   * Register for notifications from your dependencies 
    #     (use param.addnotify() for parameter dependencies)
    #   * Use these notifications to trigger recalculation
    #   * Call self.controlparam.assignval(valueobj,self.id) to 
    #     assign the new value
    
    controlparam=None
    id=None
    state=None  # see CONTROLLER_STATE defines in definition of param class


    def __init__(self,controlparam):
        self.controlparam=controlparam
        self.id=id(self)
        self.state=param.CONTROLLER_STATE_QUIESCENT
        self.numpending=0
        self.controlparam.non_settable=True

        pass


 
    # requestval is a request that this parameter take on the requested value
    # (This is an asynchronous request. Will get callback when complete)
    # returns request identifier that can be used to cancel request 
    # callback(param,requestid,errorstr,newvalue,*cbargs)
    def requestval(self,param,newvalue,*cbargs):
        raise ValueError("automatic parameter %s does not support assignment" % (self.controlparam.xmlname))
    
    

    def cancelrequest(self,param,requestid): 
        raise ValueError("automatic parameter %s does not support assignment" % (self.controlparam.xmlname))
    
    pass


def updatedg_notifycallback(param, condition, module):
    # Callback to Run a Dataguzzler Command when a Parameter has
    # been updated.  Use with addnotify for a one-way update of a
    # Dataguzzler parameter.  Will only work if MODULE:DCLOCK TRUE 
    # can be called.
    outvalue = "NONE"
    if type(param.dcvalue) is numericunitsv:
        outvalue = param.format()
    elif type(param.dcvalue) is stringv:
        outvalue = str(param)
    else:
        raise Exception('Parameter %s is type %s - This type is Not Supported For Dataguzzler Assignment Callback (Must be dc_value.stringvalue or dc_value.numericunitsvalue)' % (param.xmlname, repr(type(param.dcvalue))))
    if outvalue.strip() == "":
        outvalue = "NONE"
    retfun = lambda id,fullcommand,retcode,full_response,result,param: False
    param.iohandlers["dgio"].issuecommand(None,"%s:DCLOCK FALSE;%s %s;%s:DCLOCK TRUE" % (module, module, outvalue, module), retfun, param,dg_io.io.QT_GENERIC)
    return False

def updatedg_exitcallback(param, module):
    # Callback to Run a Dataguzzler Command when everything is 
    # exiting.  Use with dgio.addexitcallback to unlock a
    # Dataguzzler parameter.  Will only work if MODULE:DCLOCK FALSE 
    # can be called.

    # We Must Issue Command Directly Because Garbage Collection Has Already Started And New Commands Will Not Get Dispatched
    dgc.command(param.iohandlers["dgio"].dgch, "%s:DCLOCK FALSE" % (module))
    return False

# Note: These routines (below) are for READ ONLY access to the specimen
# database, transducer database, etc. 
# For READ/WRITE synchronization of file content to a datacollect parameter, 
# see the xmldoc.synced class. 

class autocontroller_xmlfile_class(autocontrollerbase):
    # Controller that links fields to any file's XML
    # representation using Databrowse.  When the provided
    # fields are updated, this is triggered to pull
    # values using Databrowse.  XPath expressions are passed
    # as parameters to control the value pulled from the file.
    # 
    # TODO: Get Rid of Excess Type Checking - Not Very Pythonic
    # Some of it may be required, but there should be ways to 
    # get rid of most of it
    # 
    # TODO: Remove old autocontroller_specimendb and 
    # autocontroller_xducerdb when we think they have mostly
    # disappeared from dcc files outside of the repo

    def __init__(self, param, filestring, fileparams, xpath, xpathparams, namespaces=None, **kwargs):
        autocontrollerbase.__init__(self, param)
        paramdb = param.parent
        for subparam in list(set(fileparams + xpathparams)):
            # If We Got a Tuple with Units, Let's Pull The Parameter Name
            if type(subparam) is tuple:
                subparam = subparam[0]
            # Verify that Driving Parameter is A String or Numeric Units Value - Throw Exception if Not
            if type(paramdb[subparam].dcvalue) is not stringv and type(paramdb[subparam].dcvalue) is not numericunitsv:
                raise Exception('Parameter %s depends on %s which is type %s - This Type is Not Supported (Must be dc_value.stringvalue or dc_value.numericunitsvalue)' % (param.xmlname, subparam, repr(type(paramdb[subparam].dcvalue))))
            # Add Notify on The Contolling Field
            paramdb[subparam].addnotify(self.xmlfileupdated, param.parent[subparam].NOTIFY_NEWVALUE, param.xmlname, filestring, fileparams, xpath, xpathparams, namespaces, **kwargs)
            pass
        pass

    @classmethod
    def xmlfileupdated(cls, param, condition, controlparam, filestring, fileparams, xpath, xpathparams, namespaces, **kwargs):
        # Callback function to handle changes to a controller field
        try:
            paramdb = param.parent
            
            # Prepare to Fetch Filename
            valuelist = []
            for subparam in fileparams:
                # Pull Units if they Exist
                units = None
                if type(subparam) is tuple:
                    units = subparam[1]
                    subparam = subparam[0]
                # Get Value
                if type(paramdb[subparam].dcvalue) is numericunitsv:
                    valuelist.append(paramdb[subparam].value(units))
                elif type(paramdb[subparam].dcvalue) is stringv:
                    valuelist.append(str(paramdb[subparam]))
                else:
                    raise Exception('Parameter %s depends on %s which is type %s - This type is Not Supported (Must be dc_value.stringvalue or dc_value.numericunitsvalue)' % (param.xmlname, subparam, repr(type(paramdb[subparam].dcvalue))))
                pass
            valuelist = tuple(valuelist)

            # Get Filename Value
            filename = filestring % valuelist

            # Open File
            xml = dbl.GetXML(filename, output=dbl.OUTPUT_ETREE, **kwargs)

            # Prepare to Fetch Data
            valuelist = []
            for subparam in xpathparams:
                # Pull Units if they Exist
                units = None
                if type(subparam) is tuple:
                    units = subparam[1]
                    subparam = subparam[0]
                # Get Value
                if type(paramdb[subparam].dcvalue) is numericunitsv:
                    valuelist.append(paramdb[subparam].value(units))
                elif type(paramdb[subparam].dcvalue) is stringv:
                    valuelist.append(str(paramdb[subparam]))
                else:
                    raise Exception('Parameter %s depends on %s which is type %s - This type is Not Supported (Must be dc_value.stringvalue or dc_value.numericunitsvalue)' % (param.xmlname, subparam, repr(type(paramdb[subparam].dcvalue))))
                pass
            valuelist = tuple(valuelist)

            # Get Values - xpath should be like "specimen:geometry/specimen:dimension[@direction='length']/." 
            res = xml.xpath(xpath % valuelist, namespaces=namespaces)

            # Let's Look at The Results and Determine What Course of Action to Take
            if type(res) is list:  # We Got a List of Elements Back
                if len(res) != 1:  # We Got Too Many or Too Few Elements Back
                    raise Exception('XPath Expression Returned %d Results - Expected Exactly 1' % len(res))
                else:
                    valueobj = paramdb[controlparam].paramtype.fromxml(None,res[0])  # xml_attribute=paramdb[controlparam].xml_attribute)
            else:  # We Got a Bool, Float, or String - Use it Directly - Errors Will Be Thrown Internally if There are Type Issues
                valueobj = paramdb[controlparam].paramtype(res)
            
        except:
            (exctype, excvalue) = sys.exc_info()[:2]
            sys.stderr.write("%s: %s creating value object: %s\n" % (controlparam, str(exctype), str(excvalue)))
            if paramdb[controlparam].defunits is not None:
                valueobj = paramdb[controlparam].paramtype("NaN", units=paramdb[controlparam].defunits)
            else:
                valueobj = paramdb[controlparam].paramtype("NaN")
        finally:
            paramdb[controlparam].assignval(valueobj, paramdb[controlparam].controller.id)

    pass

def autocontroller_xmlfile(param, filestring, fileparams, xpath, xpathparams, namespaces=None, **kwargs):
    # Controller to Pull Data from any file using Databrowse and an XPath Expression
    # Will Take a List of Parameters from paramdb to Substitue into the Filename and
    #   the XPath Expression
    # Additional keyword arguments are passed directly to dbl.GetXML()
    # Will Trigger an Update Any Time Any Controlling Parameter is Updated
    # fileparams and xpath params are a list of strings of the xmlname of
    #   parameters that should be substituted into filestring or xpath,
    #   respectively, that will be expanded to their values on update
    # fileparams and xpath params must be numericunitsvalue or stringvalue
    #   types - numericunitsvalues are passed in default units as just
    #   the contained value
    # In lieu of a string, a numericunitsvalue can be passed in as a tuple
    #   of the format (xmlname, desiredunits)
    #   For Example:  ['specimen', ('pressure', 'psi'), 'perfby']
    # fileparams and xpathparams MUST ALWAYS be lists
    # Example Usage for Specimen Database:
    #   autocontroller_xmlfile(param, os.path.join('/databrowse/specimens', '%s.sdb'), ['specimen'], 'specimen:geometry/specimen:dimension[@direction="length"]', [], namespaces={'specimen':'http://thermal.cnde.iastate.edu/specimen'})
    if dbl is None: 
        # specimen database not available.... allow manual control
        return simplecontroller(param)
        pass
    else : 
        return autocontroller_xmlfile_class(param, filestring, fileparams, xpath, xpathparams, namespaces, **kwargs)
    pass

# DEPRECATED!!!  Do Not Use This Controller - Provided Only for Temporary Backwards Compatility - Will Be Removed
def autocontroller_specimendb(param, specimenparam, dblocation, valuexpath):
    sys.stderr.write("DeprecationWarning:  `autocontroller_specimendb` is deprecated - Please update dcc file with autocontroller_xmlfile\n")
    if dbl is None: 
        # specimen database not available.... allow manual control
        return simplecontroller(param)
        pass
    else : 
        return autocontroller_xmlfile_class(param, os.path.join(dblocation, '%s.sdb'), [specimenparam], valuexpath, [], namespaces={'specimen':'http://thermal.cnde.iastate.edu/specimen'})
    pass

# DEPRECATED!!!  Do Not Use This Controller - Provided Only for Temporary Backwards Compatility - Will Be Removed
def autocontroller_xducerdb(param, xducerparam, dblocation, valuexpath):
    sys.stderr.write("DeprecationWarning:  `autocontroller_xducerdb` is deprecated - Please update dcc file with autocontroller_xmlfile\n")
    if dbl is None: 
        # specimen database not available.... allow manual control
        return simplecontroller(param)
        pass
    else :
        return autocontroller_xmlfile_class(param, os.path.join(dblocation, '%s.tdb'), [xducerparam], valuexpath, [], namespaces={'transducer':'http://thermal.cnde.iastate.edu/transducer'})
    pass

class autocontroller_averagedwfm(autocontrollerbase):
    wfmname=None

    def __init__(self,controlparam,wfmname):
        autocontrollerbase.__init__(self,controlparam)
        self.wfmname=wfmname
        self.controlparam.iohandlers["dgio"].add_chanmon(wfmname,self.chanmon)
        
        pass

    def chanmon(self,dgio):
        (rev,wfm)=dgc.getlatestwfm(self.controlparam.iohandlers["dgio"].dgch_sync,self.wfmname,readyflag=True);
        
        if wfm is not None and wfm.data is not None:
            newunits=""
            
            newvalue=float(wfm.data.mean())
            if "AmplUnits" in wfm.MetaData and wfm.MetaData["AmplUnits"].isstr():
                newunits=wfm.MetaData["AmplUnits"].Value;
                pass
            # print "%s: units=%s; defunits=%s\n" % (self.controlparam.xmlname,newunits,self.controlparam.defunits)
            try : 
                valueobj=self.controlparam.paramtype(newvalue,units=newunits,defunits=self.controlparam.defunits)
                pass
            except:
                (exctype, excvalue) = sys.exc_info()[:2] 
                sys.stderr.write("%s: %s creating value object: %s\n" % (self.controlparam.xmlname,str(exctype),str(excvalue)))
                valueobj=self.controlparam.paramtype("NaN",units=self.controlparam.defunits)
                pass
            pass
        else :
            valueobj=self.controlparam.paramtype("NaN",units=self.controlparam.defunits)
            pass
        
        self.controlparam.assignval(valueobj,self.id)        
        pass

    pass




class autocontroller_wfmmetadata(autocontrollerbase):
    wfmname=None
    metadatumname=None

    def __init__(self,controlparam,wfmname,metadatumname):
        autocontrollerbase.__init__(self,controlparam)
        self.wfmname=wfmname
        self.metadatumname=metadatumname
        self.controlparam.iohandlers["dgio"].add_chanmon(wfmname,self.chanmon)
        
        pass

    def chanmon(self,dgio):
        (rev,wfm)=dgc.getlatestmetadata(self.controlparam.iohandlers["dgio"].dgch_sync,self.wfmname,readyflag=True);
        valueinp=""
        if wfm is not None and wfm.MetaData is not None:
            if self.metadatumname in wfm.MetaData:                 
                valueinp=wfm.MetaData[self.metadatumname].Value
                pass
            pass
        
        try :
            valueobj=self.controlparam.paramtype(valueinp,defunits=self.controlparam.defunits)
                
            pass
        except:
            (exctype, excvalue) = sys.exc_info()[:2] 
            sys.stderr.write("%s: %s creating value object: %s\n" % (self.controlparam.xmlname,str(exctype),str(excvalue)))
            valueobj=self.controlparam.paramtype("",defunits=self.controlparam.defunits)
            pass
        self.controlparam.assignval(valueobj,self.id)        
        pass
 
    pass



# Not thread safe
class param(object):
    # class for representing parameter within paramdb
    parent=None
    #dgio=None
    iohandlers=None
    xmlname=None
    paramtype=None
    defunits=None
    options=None
    dcvalue=None # dc_value object
    controller=None
    status=None
    valstate=None  # state of dcvalue... VALSTATE_ consts below...; see also controller.state for controller state 
    notifylist=None # list of (function,condition,arglist) tuples. condition should be one of the NOTIFY_ values below (function is called as function(param,condition,*arglist)
    displayfmt=None # printf-style format for printing a number, e.g. "%f" or "%g"
    hide_from_meas=None  # Should we hide this entry when measurements are written to the experiment log? 
    reset_with_meas_record=None  # Should we clear this entry when measurements are written to the experiment log? 
    dangerous=None  # Set this flag on parameter creation to indicate that this parameter has potentially dangerous (usually mechanical) side effects and should be ignored on restore. 
    non_settable=None # specified on creation or by controller to indicate that this parameter is not generally settable by the user. Used to select which parameters in the database are saved. 
    # xml_attribute=None # if not None, dc_value.value.xmlrepr()  and dc_value.value.fromxml() should store their data this attribute, specified by name (namespace prefixes OK) rather than in the content of the tag
    save_extension=None # filename extension to use when saving
    
    # NOTE: since this class shadows a dc_value object, it should NOT have members
    # with the same name as those in a dc_value or it's derived classes 
    # i.e. final, str, val, unit, defunit, pixbuf, type, f0, f1, t0, t1, t2, t3
    # or methods with the same name, i.e. 
    # simplifyunits, valuedefunits, units, value

    VALSTATE_UNASSIGNED=0
    VALSTATE_UPDATING=3  # Updating those who are monitoring this parameter
    VALSTATE_QUIESCENT=4 # Nothing doing
    
    CONTROLLER_STATE_QUIESCENT=0  # no outstanding requests
    CONTROLLER_STATE_REQUEST_PENDING=1  # controller has at least one request pending

    # notify conditions
    NOTIFY_CONTROLLER_REQUEST=0 # Function called when notified should not try to mess with the value
    NOTIFY_NEWVALUE=1  # every successful controller request should result in a newvalue, whether or not the value actually changed
    NOTIFY_NEWOPTIONS=2 # Called when options are updated by the controller so that they can be reloaded in the GUI

    def __init__(self,parent,xmlname,paramtype,options=None,defunits=None,build=None,displayfmt=None,hide_from_meas=False,reset_with_meas_record=False,dangerous=False,non_settable=False,save_extension=".dat"): # xml_attribute=None):
        # DO NOT CALL THIS DIRECTLY.... Should be called indirectly from pdb.addparam() 
        # create a parameter with the specified xmlname (string/unicode)
        # paramtype should be dc_value.stringvalue, dc_value.numericunitsvalue, dc_value.excitationparamsvalue, or similar
        # options is a list of suggested values for the field
        # build is a function that will be called with the param as a 
        # parameter. It will usually set-up whatever handles 
        # the assignment. For example, it might be:
        #   lambda param: dg_param.dg_paramcontroller(param,"AWG:AMPL")
        # 
        self.parent=parent
        self.iohandlers=parent.iohandlers
        self.xmlname=xmlname
        self.paramtype=paramtype
        if options is not None:
            self.options=list(copy.deepcopy(options))
            pass
        
        self.defunits=defunits
        self.valstate=param.VALSTATE_UNASSIGNED
        self.notifylist=[]
        self.displayfmt=displayfmt
        self.hide_from_meas=hide_from_meas
        self.reset_with_meas_record=reset_with_meas_record
        self.dangerous=dangerous
        self.non_settable=non_settable  # specified on creation or by controller to indicate that this parameter is not generally settable by the user. Used to select which parameters in the database are saved.
        self.save_extension=save_extension
        #self.xml_attribute=xml_attribute

        #import pdb as pythondb
        #pythondb.set_trace()
        
        object.__setattr__(self,'dcvalue',self.paramtype(""))


        if build is not None:
            self.controller=build(self)
            pass
        
        if self.controller is None:
            # if no controller created by build(), instantiate a simplecontroller
            self.controller=simplecontroller(self)
            pass

        
        pass

    def perform_save(self,savefilehref,*cbargs):
        
        # pass request onto controller
        return self.controller.perform_save(self,savefilehref,*cbargs)
    
    # requestval is a request that this parameter take on the requested value
    # (This is an asynchronous request. Will get callback when complete)
    def requestval(self,valueobj,*cbargs):
        # cbargs is callback function/method, followed by list of arguments
        # the function will be called with the new value as the first parameter, followed by the list of arguments
        # print "requestval on parameter %s = %s" % (self.xmlname,str(valueobj))

        assert(isinstance(valueobj,dc_value.value))

        self.do_notify(param.NOTIFY_CONTROLLER_REQUEST)
        
        # pass request onto controller
        return self.controller.requestval(self,valueobj,*cbargs)
        
    def cancelrequest(self,requestid):
        # pass cancel on to controller

        return self.controller.cancelrequest(self,requestid)


    # requestval is a request that this parameter take on the requested value,
    # provided in string or unicode form
    # (This is an asynchronous request. Will get callback when complete)
    def requestvalstr(self,valuestr,*cbargs):
        valueobj=self.paramtype(valuestr,defunits=self.defunits)
        
        return self.requestval(valueobj,*cbargs)


    # requestval_sync is a request that this parameter take on the requested value
    # (Request is synchronous. Will return when complete)
    # NOTE: This creates and starts a glib event loop for dispatching
    # so other event handers may be called in the middle
    def requestval_sync(self,valueobj):
        def callback(controlparam,requestid,errorstr,newvalue,mainloop,retcontain):
            # sys.stderr.write("%s got requestval_sync callback\n" % (controlparam.xmlname))
            # sys.stderr.write("newvalue=%s\n" % (str(newvalue)))
            retcontain.append(newvalue)
            mainloop.quit()
            pass

        assert(isinstance(valueobj,dc_value.value))
        
        # sys.stderr.write("%s requesting value %s\n" % (self.xmlname,str(valueobj)))
        
        self.do_notify(param.NOTIFY_CONTROLLER_REQUEST)
        retcontainer=[]  # set first and only element to return value
        NestedLoop=gobject.MainLoop()

        # pass request onto controller
        self.controller.requestval(self,valueobj,callback,NestedLoop,retcontainer)
        
        # Start main loop 
        NestedLoop.run()

        # The main loop returning signifies that we have receved our callback, and the value should
        # be retcontainer[0]
        
        if len(retcontainer) < 1:
            raise ValueError("requestval_sync: No return value from assignment request to %s" % (str(valueobj)))
        
        return retcontainer[0]


    # requestvalstr_sync is a request that this parameter take on the requested value
    # provided in string or unicode form.
    # (Request is synchronous. Will return when complete)
    # NOTE: This creates and starts a glib event loop for dispatching
    # so other event handers may be called in the middle
    def requestvalstr_sync(self,valuestr):
        valueobj=self.paramtype(valuestr,defunits=self.defunits)
        return self.requestval_sync(valueobj)
    
    def do_notify(self,condition): # condition should be one of the NOTIFY_... conditions
        self.valstate=param.VALSTATE_UPDATING
        for (function,notifycondition,arglist) in self.notifylist:
            if notifycondition==condition:
                function(self,condition,*arglist)
                pass
            pass
        self.valstate=param.VALSTATE_QUIESCENT

        pass
    

    def addnotify(self,function,condition,*args):
        handle=(function,condition,args)
        self.notifylist.append(handle)
        return handle

    def remnotify(self,handle):
        self.notifylist.remove(handle)
        pass


    
    
    # assignval is performed by controller, often in response to requestval
    def assignval(self,valueobj,idnum):
        if idnum != id(self.controller):
            raise ValueError("Bad assignment (may only be done by controller; otherwise use requestval()")
        object.__setattr__(self,'dcvalue',valueobj)

        self.do_notify(param.NOTIFY_NEWVALUE)
        pass

    def __setattr__(self,item,value):
        # prevent "value" from being changed w/out permission
        if item=="dcvalue":
            raise KeyError("param.dcvalue may not be changed directly; use param.assignval() or param.requestval()")
        return object.__setattr__(self,item,value)
    

    
        
    
    pass
