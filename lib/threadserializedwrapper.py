import sys
import os
import threading

import collections
import traceback


if "gi" in sys.modules:  # gtk3
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import GObject as gobject
    pass
else : 
    # gtk2
    import gobject
    pass


import genericmethodwrapper

# This module generates Python wrapper classes that
# serialize all accesses to regular named methods.
# does not serialize attribute access

# Calls can either be made inline, in which case the
# calling thread must wait, or can be initiated with a
# callback for the gobject main loop, in which case the
# callback will be called when done.

# Use case 1: Simple hardware driver
# import device_class
# device_serialized=(wrapserialized(device_class))(param1,param2,param3)
# paramdb.addparam("dvcparam", stringv,
#                  build=lambda param:
#                  threadserializedcontroller(param,
#                                             device_serialized, 
#                                             device_serialized.get_dvcparam,
#                                             device_serialized.set_dvcparam,
#                                             pollms=1000.0)
# paramdb.addparam("dvcparam", stringv,
#                  build=lambda param:
#                  threadserializedcontroller(param,
#                                             device_serialized,
#                                             lambda dev,**kwargs: dev.get_param("dvcparam",**kwargs),
#                                             lambda dev,value,**kwargs: dev.set_param("dvcparam",value,**kwargs),
#                                             pollms=1000.0)


# Use case 2: Multiple hardware drivers all using gpib
# gpib_serialized=(wrapserialized(gpib_class))(param1,param2)
# device1=wrapserialized(device1_class,share_thread=gpib_serialized)(gpib_serialized,param3,param4)
# device2=wrapserialized(device2_class,share_thread=gpib_serialized)(gpib_serialized,param5,param6)




class threadmanager(object):
    thread=None
    callqueue=None  # deque of (cls,method,args,kwargs,callback_and_params,returnlist,donenotifyevent)
    WakeupEvent=None
    
    def __init__(self):
        gobject.threads_init()
        self.callqueue=collections.deque()
        self.thread=threading.Thread(None,self.threadcode)
        self.WakeupEvent=threading.Event()
        pass

    def threadcode(self):
        while True:
            try:
                if len(self.callqueue)==0:
                    self.WakeupEvent.wait()
                    pass

                if len(self.callqueue) > 0:
                    params=self.callqueue.popleft()
                    self.WakeupEvent.clear()
                    (cls,method,args,kwargs,callback_and_params,returnlist,donenotifyevent)=params
                    result=None
                    try: 
                        result=method(*args,**kwargs)
                        pass
                    except:
                        (exctype,excvalue)=sys.exc_info()[:2]
                        sys.stderr.write("Exception in serialized thread: %s: %s\nTraceback:\n" % (str(exctype.__name__),str(excvalue)))
                        traceback.print_exc()
                        result=excvalue
                        pass
                    
                    if callback_and_params is not None:
                        gobject.timeout_add(0,callback_and_params[0],params,result,callback_and_params[1])
                        pass
                    else:
                        returnlist.append((result,params))
                        donenotifyevent.set()
                        pass
                    pass
                
                pass
            except:
                (exctype,excvalue)=sys.exc_info()[:2]
                sys.stderr.write("Exception in serialized thread: %s: %s\nTraceback:\n" % (str(exctype.__name__),str(excvalue)))
                traceback.print_exc()
                pass
            pass
        pass

    def attempt_cancel_call(self,paramtuple):
        # NOTE: Generally will be called from different thread
        removed=None
        
        if paramtuple in self.callqueue:    
            try:
                self.callqueue.remove(paramtuple)
                removed=paramtuple
                pass
            except:
                # might fail due to race condition
                pass
            
            pass
        return removed

    pass

def wrap_dispatch(wrapped_object,methodname,methodtocall,args,kwargs):
    """ Can pass "gobject_callback" in kwargs. This should be a tuple
        of a function/method  to  called in the gobject main event loop 
        when the function completes and an extra parameter to pass to the function . 
    The callback should always return False. 
    If you pass gobject_callback, then instead of returning the result, 
    the wrapped call returns the manager callqueue tuple... (or None
    if no manager involvement was required) """
    
                            
    gobject_callback=None
    if "gobject_callback" in kwargs:
        gobject_callback=kwargs["gobject_callback"]
        del kwargs["gobject_callback"]
        pass

    
    manager=wrapped_object._wrap_classdict["threadmanager"]

    if threading.current_thread is manager.thread:
        # We are already running in the correct context...
        # execute and return
        # immediately!
        assert(gobject_callback is None) # does not make sense to have a call with a callback from the thread manager thread
        return methodtocall(*args,**kwargs)
    

    if methodname.startswith("__") and methodname.endswith("__") and methodname != "__init__":
        # magic methods other than __init__ are not dispatched to
        # the serialized thread, but are executed immediately here.
        retval=methodtocall(*args,**kwargs)

        if gobject_callback is not None:
            return retval
        else:
            gobject.timeout_add(0,gobject_callback[0],None,retval,gobject_callback[1])
            return None
        
        pass

    
    
    if gobject_callback is not None:
        # Dispatch with callback
        callqueue_params=(wrapped_object,methodtocall,args,kwargs,gobject_callback,None,None)
        manager.callqueue.append(callqueue_params)
        manager.WakeupEvent.set()
        return callqueue_params
    else:
        # Dispatch and wait
        returnlist=[]
        donenotifyevent=threading.Event()
        manager.callqueue.append((wrapped_object,methodtocall,args,kwargs,None,returnlist,donenotifyevent))
        manager.WakeupEvent.set()

        donenotifyevent.wait()
        (returnobj,queueparams)=returnlist[0]

        if isinstance(returnobj,BaseException):
            raise returnobj
        
        return returnobj
    
    pass

def wrapserialized(cls,share_thread=None):
    """This function creates a thread manager (or reuses
    the thread manager from the wrapper specified with share_thread)
    and defines a wrapper class around cls that uses this thread 
    manager to serialize access to cls. Please note that simple
    attribute assignment is not serialized, nor are any of the 
    Python "magic" methods (those beginning and ending with __), 
    except for the constructor __init__"""
    
    if share_thread is None:
        manager=threadmanager()
        pass
    else:
        manager=share_thread._wrap_classdict["threadmanager"]
        pass
    
    wrapped=genericmethodwrapper.generate_wrapper_class(cls,dispatch_function=wrap_dispatch)
    wrapped._wrap_classdict["threadmanager"]=manager
    
    return wrapped
