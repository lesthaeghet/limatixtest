import sys
import re
import threading
import copy
import traceback
import atexit


# dg_io ... New generation io module for managing connections to dataguzzler
# 
# main class is dg_io.io()
# 
# It creates a main synchronous comm link (io.dgch)
# and a series of threads with their own comm links
# that can execute commands and queries
#
# It is tied into glib/gtk, using timeout_add() to 
# get called repetitively and to dispatch callbacks 
# into the glib/gtk event loop. So glib must be 
# in threaded mode (should call gobject.threads_init()
# at start of main()), but gdk/gtk can all be handled 
# in the main thread. 
#
# issuecommand() dispatches a command on one of the threads
# and triggers a callback in the glib event loop when done. 
# These commands can be aborted or canceled up to the point
# at which the callback has been queued into the glib event loop
#
# issuecommandsynchronous() uses the main sychronous comm 
# link and runs a command synchronously. It is not thread
# safe (only run from main glib/gtk event loop thread). 
#
# addquery()/remquery() provide the ability to run periodic 
# background queries with repetitive callbacks. The callbacks
# are likewise run through the main event loop. 
#
# Multiple queries of the same parameter are merged, so long as 
# the query strings are exactly the same. Thus module/command 
# names should generally be consistently in uppercase to as 
# to allow this merging to occur.
#
# add_chanmon() provides the ability to get callbacks 
# when dataguzzler channel revisions change. These are 
# currently handled through a callback in the main event loop.




# need to call g_thread_init() and gdk_threads_init() ????
# or glib.threads_init()

# sys.stderr.write("sys.path=%s\n" % (str(sys.path)))
if not "gi" in sys.modules:
    # GTK2/PyGTK
    # import gobject
    from gobject import timeout_add
    from gobject import threads_init
    pass
else :
    # new PyGObject way:
    from gi.repository import GLib
    from gi.repository.GLib import timeout_add
    from gi.repository.GLib import threads_init
    pass

try: 
    import dataguzzler as dg
    import dg_comm as dgc
    import dg_file as dgf

    dgc_client=dgc.client
    
    pass
except ImportError:
    # dataguzzler not available
    dg=None
    dgc=None
    dgf=None

    dgc_client=object
    pass


__pychecker__="no-import no-callinit no-local" # no-callinit because of spurious warning about (dg_comm.client) __init__() not being called

def addhandler(iohandlers):
    # This helper function adds the dg_io iohandler to
    # the main handlers list and starts communication
    if "dgio" not in iohandlers:
        iohandlers["dgio"]=io()
        iohandlers["dgio"].startcomm()
        pass
    
    
    pass


def savefilterpass(save_paramdict,ChanName):
    filter=save_paramdict["filter"]
    for regexp in filter:
        matchobj=re.match(regexp,ChanName)
        if matchobj is not None:
            if matchobj.group(0)==ChanName:
                # full match
                return False
            pass
        pass
    # Fallthrough: OK to show this chan
    return True

class iochan(dgc_client):
    # extension of dg_comm client class
    # that tracks whether it is in use
    
    # if pendingcom=None, then it is not in use. 
    # otherwise it is a pendingcommand or query object
    
    pendingcom=None
    readerthread=None
    ioobj=None  # link to io object structure
    cond=None

    connfailindicator=None  # connfailindicator is a List. If a connection fails, we add an entry to the list. If the list isempty and we have an i/o failure than we have to trigger a connection retry for everyone. 
    timetodie=None
    
    def readerthreadcode(self):
        raise ValueError("This routine should never be called (always overridden by subclass")
    

    def __init__(self,ioobj,*args,**kwargs):
        dgc.client.__init__(self,*args,**kwargs)
        self.ioobj=ioobj
        self.pendingcom=None
        self.timetodie=False
        self.connfailindicator=self.ioobj.connfailindicator

        self.readerthread=threading.Thread(None,self.readerthreadcode)
        self.readerthread.daemon=True
        # self.readerthread.start()  # start is issued by the derived class after it finishes initializing
        pass

    def killme(self):
        self.cond.acquire()
        self.cond.notifyAll()
        dgc.close(self)
        if self.readerthread.isAlive():
            self.timetodie=True
            pass

        if self.pendingcom is not None and (not hasattr(self.pendingcom,"cancelled") or not self.pendingcom.cancelled): 
            
            if isinstance(self.pendingcom,pendingcommand):
                
                self.pendingcom.dispatch_callback(1000,"","")
                self.pendingcom=None
                pass
            # for queries, self.pendingcom is actually a dictionary... but 
            # because queries are repetitive there's no point in error returns
            pass
        self.cond.release()
        pass
    
    pass



def procresult(querytype,buf):
    
    if querytype==io.QT_UNQUOTEDSTRING:
        matchobj=re.match(r"""[a-zA-Z0-9_\.:]+\s(.*)\r\n$""",buf);
        res=matchobj.group(1)
        pass
    elif querytype==io.QT_LONGINT:
        matchobj=re.match(r"""[a-zA-Z0-9_\.:]+\s*([-+\d\.eE]+)""",buf);
        res=long(matchobj.group(1))
        pass
    elif querytype==io.QT_NUMERIC:
        matchobj=re.match(r"""[a-zA-Z0-9_\.:]+\s+([-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)""",buf)
        res=float(matchobj.group(4))
        pass
    elif querytype==io.QT_EXCPARAMS:
        # strip off leading GEN:
        matchobj=re.match(r"""[a-zA-Z0-9_\.:]+:(([a-zA-Z0-9\.]+) .*)""",buf)
        if matchobj is None: 
            # Failed match -- treat as GEN:NONE
            res="NONE"
            pass
        else :
            res=matchobj.group(1)
            pass
        pass
    else : # treat it in most generic way possible
        matchobj=re.match(r"""[a-zA-Z0-9_\.:]+(\s(.*))?\r\n$""",buf);
        if matchobj is None: 
            res=""
            pass
        else : 
            res=matchobj.group(2)
            if res is None:
                res=""
                pass
            pass
        pass
    return res



class cmdiochan(iochan):
    # iochan with dispatch engine for handling commands
    def __init__(self,*args,**kwargs):
        iochan.__init__(self,*args,**kwargs)
        self.cond=self.ioobj.commcommandcondition
        self.readerthread.start()  # start is issued by the derived class after it finishes initializing
        pass

    def performsave(self,save_function,save_paramdict):
        
        if save_function is not None:
            save_function(self.pendingcom.savehref,save_extension,save_paramdict)
            pass

        if self.pendingcom.save_extension=="set":
            # settings file
            out=open(self.pendingcom.savehref.getpath(),"wb")
            retcode=dgc.command(self,"WFM:WFMS?")
            out.write(self.buf)
            retcode=dgc.command(self,"SET?")
            out.write(self.buf)
            out.close()
            
            pass
        else:
            # assume .dgs

            

            dgfh=dgf.creat(self.pendingcom.savehref.getpath())
            if dgfh is None:
                raise IOError("Could not open dgs file \"%s\" for write." % (self.pendingcom.savehref.getpath()))
            (globalrevision,ChanList)=dgc.downloadwfmlist(self,False,True,True);

            # only valid paramdict key is "filter"
            save_paramdict_keys=list(save_paramdict.keys())
            if any([save_paramdict_key != "filter" for save_paramdict_key in save_paramdict_keys]):
                raise ValueError("Only key supported in save_paramdict is 'filter': Found keys: %s" % (str(save_paramdict_keys)))
            

            # support regular expression filters in save_paramdict
            ChanFilteredList=[ Chan for Chan in ChanList if savefilterpass(save_paramdict,Chan[0]) ]
            
            dgf.startchunk(dgfh,"SNAPSHOT");
            # provide empty metadata chunk
            EmptyMetadata={};
            dgf.writemetadata(dgfh,EmptyMetadata);
            
            for Chan in ChanFilteredList :
                wfm=dgc.downloadwfmshm(self,Chan[0],Chan[1]);
                wfm.wfmname=Chan[0];
                dgf.writenamedwfm(dgfh,wfm);
                
                dgc.command(self,"WFM:UNLOCK %s %d" % (Chan[0],Chan[1]));
                pass
            dgf.endchunk(dgfh); # SNAPSHOT
            dgf.close(dgfh);
            
            pass
        pass

    def readerthreadcode(self):
        # This code should be constantly waiting on read from this connection,
        # whenever there is a pending command. 
        # Otherwise it should wait on a condition variable for the signal that
        # a command is pending. 
        HaveLock=False
        cond=self.cond
        
        try : 
            cond.acquire()
            HaveLock=True
            while 1: 
                if (self.timetodie):
                    cond.release()
                    return
                # sys.stderr.write("Reader thread %d waiting...\n" % id(self))
                cond.wait() # wait for signal

                # sys.stderr.write("Reader thread %d woken up...\n" % id(self))
                if len(self.ioobj.pending)==0:
                    # sys.stderr.write("Reader thread %d woken up...\n" % id(self))
                    # nothing to do
                    continue
                
                # grab work
                self.pendingcom=self.ioobj.pending.popitem()[1]
                # sys.stderr.write("Reader thread %d woken got work: %s\n" % (id(self),str(self.pendingcom)))
                
                cond.release()
                HaveLock=False
                
                if (self.timetodie):
                    return
                
                # sys.stderr.write("Reader thread %d issuing command %s\n" % (id(self),str(self.pendingcom.fullcommand)))
                # work on self.pendingcom                
                if self.pendingcom.savehref is not None:
                    try: 
                        self.performsave(self.pendingcom.save_function,self.pendingcom.save_paramdict)

                        # Serialize savehref as XML, store in res. 
                        # .... callback will convert back
                        # to hrefvalue
                        # hrefdoc=xmldoc.xmldoc.newdoc("performsave")
                        # self.pendingcom.savehref.xmlrepr(hrefdoc,hrefdoc.getroot())
                        # res=hrefdoc.tostring()

                        res=self.pendingcom.savehref
                        self.buf=b"" # full result is blank
                        pass
                    except:
                        (exctype, excvalue) = sys.exc_info()[:2] 
                        
                        
                        sys.stderr.write("dg_io: %s: %s performing save of URL \"%s\".\n" % (exctype.__name__,str(excvalue),self.pendingcom.savehref.absurl()))
                        traceback.print_exc()

                        self.retcode=600
                        res="%s: %s" % (exctype.__name__,str(excvalue))
                        pass
                    pass
                else:
                    dgc.command(self,self.pendingcom.fullcommand)
                
                    try : 
                        # sys.stderr.write("Reader thread %d attempting to process result %s\n" % (id(self),str(self.buf)))
                        res=procresult(self.pendingcom.querytype,self.buf)
                        pass
                    except : 
                        (exctype, excvalue) = sys.exc_info()[:2] 
                        
                        
                        sys.stderr.write("dg_io: %s: %s processing result \"%s\".\n" % (exctype.__name__,str(excvalue),self.buf))
                        traceback.print_exc()
                        
                        pass
                    pass
                    # sys.stderr.write("Reader thread %d processing complete\n" % (id(self)))
                
                if (self.timetodie):
                    return
                
                cond.acquire()
                HaveLock=True
                
                if (not self.pendingcom.cancelled):
                    try :
                        # sys.stderr.write("Reader thread %d dispatching callback\n" % (id(self)))
                        self.pendingcom.dispatch_callback(self.retcode,self.buf,res)
                        pass
                    except : 
                        (exctype, excvalue) = sys.exc_info()[:2] 
            

                        sys.stderr.write("%s in callback on \"%s\" (reduced to %s).\n" % (str(exctype),self.buf,res))
                        traceback.print_exc()
                    
                        pass

                    pass

                # sys.stderr.write("Reader thread %d complete and returning to wait\n" % (id(self)))
                
                self.pendingcom=None
                
                pass
            
            pass
        except :
            if HaveLock:
                cond.release()
                pass
            traceback.print_exc()
            if not len(self.connfailindicator):
                self.connfailindicator.append(True)
                
                timeout_add(3000,self.ioobj.reopenlinks)  # ask for callback in 3 secs
                pass
            
            raise
        
        pass
    pass
    
class queryiochan(iochan):
    # iochan with dispatch engine for handling background queries
    def __init__(self,*args,**kwargs):
        iochan.__init__(self,*args,**kwargs)
        self.cond=self.ioobj.commquerycondition
        self.readerthread.start()  # start is issued by the derived class after it finishes initializing
        pass
    
    def readerthreadcode(self):

        HaveLock=False
        
        cond=self.cond

        try : 
            cond.acquire()
            HaveLock=True
            
            while 1: 
                if self.timetodie:
                    cond.release()
                    return
                cond.wait() # wait for signal
                while len(self.ioobj.todoquerydict)!=0:
                    
                    # grab work... note: self.pendingcom is now a dictionary of queries
                    (fullquery,self.pendingcom)=self.ioobj.todoquerydict.popitem()
                    
                    
                    cond.release()
                    HaveLock=False
                    
                    if self.timetodie:
                        return
                    # work on self.pendingcom ... this is a dictionary of queries, indexed by unique id, all of which share the same query: fullquery

                    # print "Running query: %s" % (fullquery)
                    
                    dgc.write(self,"%s\n" % (fullquery))
                    dgc.read(self)
                    
                    if self.timetodie:
                        return

                    # go through all of the queries and process the result and 
                    # issue callbacks independently
                    
                    res=None
                    for uniqueid in self.pendingcom:
                        
                        try : 
                            res=procresult(self.pendingcom[uniqueid].querytype,self.buf)
                        
                            pass
                        except : 
                            (exctype,excvalue)=sys.exc_info()[:2]
                            sys.stderr.write("Exception parsing dataguzzler result: %s %s\n" % (str(exctype.__name__),str(excvalue)))
                            traceback.print_exc()
                            
                            pass

                        self.pendingcom[uniqueid].dispatch_callback(self.retcode,self.buf,res)
                    
                        
                        pass
                    
                    self.pendingcom=None # clear out dictionary...
                    cond.acquire()
                    HaveLock=True
                    
                    pass
                
                pass
            pass
        except:
            if HaveLock:
                cond.release()
                pass

            if not len(self.connfailindicator):
                self.connfailindicator.append(True)
                
                timeout_add(3000,self.ioobj.reopenlinks)  # ask for callback in 3 secs
                pass

            raise
        pass
    pass


class pendingcommand(object):
    # the pendingcommand object
    id=None # Unique ID of requester... usually id(requesting ojbect)
    fullcommand=None # full string transmitted
    func=None # function to call when command complete. Params are(id,fullcommand,retcode,full_response,result,param). Should return false
    param=None 
    querytype=None
    savehref=None    # savehref and save_extension are used ony for performsave()
    save_extension=None
    save_function=None
    save_paramdict=None
    
    cancelled=None           
                      

    def __init__(self,ident,fullcommand,func,param,querytype,savehref=None,save_extension=None,save_function=None,save_paramdict=None):
        if ident is None:
            ident=id(self)
            pass
        self.id=ident
        self.fullcommand=fullcommand
        self.func=func
        self.param=param
        self.cancelled=False     
        self.querytype=querytype
        self.savehref=savehref
        self.save_extension=save_extension
        self.save_function=save_function
        self.save_paramdict=save_paramdict
        pass

    def dispatch_callback(self,retcode,buf,res):
        timeout_add(0,self.func,self.id,self.fullcommand,retcode,buf,res,self.param)
        pass
    
    pass


class query(object):
    fullquery=None # parameter to query, including '?'
    func=None # function to call. Params are (id,fullquery,retcode,fullresponse,result,param). Should return False
    id=None # unique id, or None
    param=None # opaque pointer to pass to callback
    querytype=None 

    # constants for querytype are defined in class io

    def __init__(self,ident,fullquery,func,param,querytype):
        if ident is None:
            ident=id(self)
            pass
        
        self.id=ident
        self.fullquery=fullquery
        self.func=func
        self.param=param
        self.querytype=querytype
        pass

    def dispatch_callback(self,retcode,buf,res):
        timeout_add(0,self.func,self.id,self.fullquery,retcode,buf,res,self.param)
        pass
    
    pass


class genericcallback(object):
    id=None     # Unique ID
    func=None   # Function to Call... arguments are (id, dgio, *cbargs)
    cbargs=None   # Argument to Pass to Fun

    def __init__(self,ident,func,*cbargs):
        if ident is None:
            ident = id(self)
            pass

        self.id=ident
        self.func=func
        self.cbargs=cbargs
        pass

    def dispatch_callback(self):
        timeout_add(0, self.func, *self.cbargs[0])

    def dispatch_callback_blocking(self):
        self.func(*self.cbargs[0])

    pass


class io(object):
    commstarted=None
    numcommand=None
    numquery=None
    queryperiodms=None
    uri=None
    authcode=None
    connfailindicator=None  # connfailindicator is a List. If a connection fails, we add an entry to the list. If the list isempty and we have an i/o failure then whoever sees the failure should trigger a connection retry for everyone. 
    suppress_connfail=None # this is set to true to suppress repeated messages about failing to open connections. 

    dgch=None  # synchronous channel (regular dgc.client)
    dgch_sync=None  # synchronous channel for dg_command_synchronous (regular dgc.client)
    

    # list of iochans that can be used for commands
    commcommandlist=None
    commcommandcondition=None # condition variable for notification

    # list of iochans that can be used for queries
    commquerylist=None
    commquerycondition=None # condition variable for notification  (notification happens at periodic wakeup)


    # Pending is a dictionary of pendingcommand objects.
    pending=None   # indexed by id

    # reconncallbacklist is a dictionary of functions to call on reopenlinks being called
    reconncallbacklist=None     # indexed by id

    # exitcallbacklist is a dictionary of cleanup callback functions to call on exit
    exitcallbacklist=None       # indexed by id


    # polllist is a list of functions to call in each poll cycle
    # this supports dumb polling. 
    # it is basically obsolete and its use should be avoided
    # Each entry in polllist is a function that takes dgch as a parameter.
    polllist=None  # (not implemented yet)


    querydict=None # query dict is a dictionary by query string of dictionaries by id of queries to do each time (class query, indexed by a unique id so they can be removed as needed)
    
    querystringdict=None # querystringdict is a dictionary of query strings indexed by ID to find the right querydict entry if all you have is the ID


    todoquerydict=None # each time a poll is initiated, copy querydict here. Then we slog through it


    # for chanmon:
    chanmondict=None
    chanrevs=None
    latestglobalrev=None;
    pollinprogress=None

    # constants
    CANCEL_ABORTED=0 # not executed, no response
    CANCEL_INHIBITED=1 # executed, response ignored
    CANCEL_TOOLATE=2 # executed, response triggered, too late to effect

    # constants for querytype
    QT_GENERIC=0 # generic re
    QT_NUMERIC=1 # floating point
    QT_LONGINT=2 # longint
    QT_UNQUOTEDSTRING=3 # unquoted string parameter
    QT_EXCPARAMS=4 # excitation parameters

    def createcomms(self,num,subclass,uri,authcode):
        retval=[]
        for cnt in range(num):
            retval.append(subclass(self,uri,authcode))
            pass
        return retval

    
    def reopenlinks(self):
        if not self.suppress_connfail: 
            sys.stderr.write("dg_io: Reopening all links.\n") #  len(querydict)=%d " % (len(self.querydict))
            pass
            
        # replace connfailindicator with a new list
        self.connfailindicator=[]

        # first, close all existing links 
        if self.dgch is not None:
            try: 
                dgc.close(self.dgch)
                pass
            except: 
                pass
            self.dgch=None
            pass

        if self.dgch_sync is not None:
            try: 
                dgc.close(self.dgch_sync)
                pass
            except: 
                pass
            self.dgch_sync=None
            pass

        
        if self.commcommandlist is not None:
            while len(self.commcommandlist) > 0:
                comm=self.commcommandlist.pop() 
                comm.killme()
                pass
            
            pass
        
        if self.commquerylist is not None:
            while len(self.commquerylist) > 0:
                comm=self.commquerylist.pop()
                comm.killme()
                pass
            pass
        
        # fail all pending communications

        while len(self.todoquerydict) > 0:
            self.todoquerydict.popitem()
            # queries are repetitive and need no acknowledgement
            pass
        
        while len(self.pending) > 0:
            cmd=self.pending.popitem()[1]
            # issue null failure response (#1000)
            cmd.dispatch_callback(1000,"","")
            
            pass
        
        # try to reestablish communications
        try: 
            # open synchronous link
            self.dgch=dgc.client(self.uri,self.authcode)

            # open synchronous link
            self.dgch_sync=dgc.client(self.uri,self.authcode)
            
            # open asynchronous links
            self.commcommandlist=self.createcomms(self.numcommand,cmdiochan,self.uri,self.authcode)
            self.commquerylist=self.createcomms(self.numquery,queryiochan,self.uri,self.authcode)

            # reset globalrev
            self.latestglobalrev=0

            # reset channel versions, call all chanmons
            # sys.stderr.write("dg_io: calling all chanmons for connection reset\n")
            for channame in self.chanrevs:
                self.chanrevs[channame]=0
                # sys.stderr.write("chanrevs[%s]=%d\n" % (channame,self.chanrevs[channame]))
                
                if channame in self.chanmondict:
                    for (chanmon,chanargs) in self.chanmondict[channame]:
                        try:
                            chanmon(self.dgch,*chanargs) # remember that we have to be reentrant in case chanmon creates a nested glib main loop...
                            pass
                        except :
                            sys.stderr.write("dg_io: Exception calling chanmon function: \n")
                            traceback.print_exc()
                            pass
                        pass
                    pass
                pass

            # Call reconncallback Functions
            for callback in self.reconncallbacklist:
                try:
                    self.reconncallbacklist[callback].dispatch_callback()
                except:
                    sys.stderr.write("dg_io: Exception calling reconnection callback function: \n")
                    traceback.print_exc()
                    pass
                pass

            if self.suppress_connfail: 
                self.suppress_connfail=False
                sys.stderr.write("dg_io: Communications reestablished\n")
                pass
                
            pass
        except: 
            if not self.suppress_connfail:
                traceback.print_exc()
                pass
            self.suppress_connfail=True
            

            timeout_add(3000,self.reopenlinks)  # ask for callback in 3 secs
            pass
        
        
        pass
    
    
    def __init__(self,numcommand=5,numquery=1,queryperiodms=1000.0,uri="tcp://127.0.0.1:1649",authcode="xyzzy"):

        threads_init()

        self.pollinprogress=False
        self.commstarted=False

        self.numcommand=numcommand
        self.numquery=numquery
        self.queryperiodms=queryperiodms

        self.uri=uri
        self.authcode=authcode
        self.suppress_connfail=False
        


        self.commcommandcondition=threading.Condition()
        self.commquerycondition=threading.Condition()

        # initialize with temporary empty lists
        # self.commquerylist=[]
        # self.commcommandlist=[]

        self.pending={}
        self.polllist=[]
        self.querydict={}
        self.querystringdict={}
        self.todoquerydict={}
        self.reconncallbacklist={}
        self.exitcallbacklist={}

        self.chanmondict={}
        self.chanrevs={}
        self.latestglobalrev=0

        atexit.register(self.exit_handler)
        
        # NOTE: Need to call startcomm() method to initiate communications
        pass


    def exit_handler(self):
        for callback in self.exitcallbacklist:
            try:
                self.exitcallbacklist[callback].dispatch_callback_blocking()
            except:
                sys.stderr.write("dg_io: Exception calling exit callback function: \n")
                traceback.print_exc()
                pass
            pass        
    
    def startcomm(self):
        if not self.commstarted:
            self.reopenlinks() # open communications links
            timeout_add(int(self.queryperiodms),self.do_poll)
            self.commstarted=True
            pass
        
        pass


    def do_poll(self):
        # print "do_poll"
        # periodically called by glib main loop as a result of timeout_add() in init()

        self.pollinprogress=True

        try : 
            # trigger query process.
            self.commquerycondition.acquire()
            if len(self.todoquerydict)==0:
                self.todoquerydict={}
                for key in self.querydict:
                    self.todoquerydict[key]=copy.copy(self.querydict[key])
                    pass
                pass
            
            self.commquerycondition.notifyAll() # wake up query threads
            self.commquerycondition.release()
            
            # channel monitoring functionality:
            
            if self.dgch is not None :
                dgc.command(self.dgch,"WFM:GLOBALREADYREV?");
                globalrev=int(re.match("""[a-zA-Z0-9_\.:]+\s+(\d+)\s*""",self.dgch.buf).group(1));
                
                if (globalrev > self.latestglobalrev) :
                    (self.latestglobalrev,chanlist)=dgc.downloadwfmlist(self.dgch,True,False,True);
                    for entry in chanlist :
                        channame=entry[0];
                        chanrev=entry[1];
                        # if channame in self.chanrevs: 
                        #     sys.stderr.write("dg_io: channame=%s chanrev=%d\n" % (channame,self.chanrevs[channame]))
                        #     pass
                            
                        if (not channame in self.chanrevs or chanrev > self.chanrevs[channame]) :
                            # sys.stderr.write("dg_io: chanrev changed to %d for %s\n" % (chanrev,channame))

                            self.chanrevs[channame]=chanrev;
                            if channame in self.chanmondict :
                                for (chanmon,chanargs) in self.chanmondict[channame] :
                                    try : 
                                        chanmon(self.dgch,*chanargs)   # remember that we have to be reentrant in case chanmon creates a nested glib main loop...
                                        pass
                                    except :
                                        sys.stderr.write("dg_io: Exception calling chanmon function: \n")
                                        traceback.print_exc()
                                        
                                        # for el in sys.exc_info() :
                                        #    print el
                                        #    
                                        #    pass
                                        pass
                                    pass
                                pass
                            pass
                        pass
                    pass
                pass
            pass
        except IOError: 
            traceback.print_exc()
            
            # trigger close and reopen of all links
            if not len(self.connfailindicator):
                self.connfailindicator.append(True)
                
                timeout_add(3000,self.reopenlinks)  # ask for callback in 3 secs
                self.pollinprogress=False
                pass
            
            pass
        except: 
            self.pollinprogress=False
            raise
        self.pollinprogress=False
        return True # get called back again
    

    def add_chanmon(self,chan,func,*args) :
        try :
            chanmonlist=self.chanmondict[chan];
            pass
        except KeyError :
            chanmonlist=[];
            self.chanmondict[chan]=chanmonlist;
            pass
        
        chanmonlist.append((func,args));
        pass
    
        

    def addquery(self,ident,fullquery,func,param,querytype): # add a background repetitive query. func should be a function that returns False
        newquery=query(ident,fullquery,func,param,querytype)

        if ident is None: 
            ident=id(newquery)
            pass
        
        if not fullquery in self.querydict:
            self.querydict[fullquery]={}
            pass
        
        self.querydict[fullquery][ident]=newquery
        self.querystringdict[ident]=fullquery
        
        return ident
    
    def remquery(self,ident):
        if ident in self.querystringdict:
            querystring=self.querystringdict[ident]
            
            del self.querydict[querystring][ident]
            del self.querystringdict[ident]
            pass
        pass
    
    def addreconncallback(self, ident, func, *cbargs):
        newcallback = genericcallback(ident, func, cbargs)

        if ident is None:
            ident=id(newcallback)
            pass

        self.reconncallbacklist[ident] = newcallback

        return ident

    def remreconncallback(self, ident):
        if ident in self.reconncallbacklist:
            del self.reconncallbacklist[ident]
            pass
        pass

    def addexitcallback(self, ident, func, *cbargs):
        newcallback = genericcallback(ident, func, cbargs)

        if ident is None:
            ident=id(newcallback)
            pass

        self.exitcallbacklist[ident] = newcallback

        return ident

    def remexitcallback(self, ident):
        if ident in self.exitcallbacklist:
            del self.exitcallbacklist[ident]
            pass
        pass

    # performsave like issuecommand but does a save dgs or save settings operation
    def performsave(self,ident,savehref,save_extension,save_function,save_paramdict,func,param):
        if not self.commstarted:
            raise IOError("Attempting to save dataguzzler data as URL %s over link that has not been started" % (savehref))

        self.commcommandcondition.acquire() # acquire lock
        newcommand=pendingcommand(ident,None,func,param,None,savehref=savehref,save_extension=save_extension,save_function=save_function,save_paramdict=save_paramdict)

        if ident is None:
            ident=id(newcommand)
            pass

        self.pending[ident]=newcommand

        self.commcommandcondition.notify() # wake up a dispatcher, if necessary

        self.commcommandcondition.release()

        return ident

    def issuecommand(self,ident,fullcommand,func,param,querytype): # issue a one-time command. func should be a callback function that returns False
        if not self.commstarted:
            raise IOError("Attempting to issue dataguzzler command %s over link that has not been started" % (fullcommand))
        
        # sys.stderr.write("issuecommand() started\n")
        self.commcommandcondition.acquire() # acquire lock
        # sys.stderr.write("Got lock\n")
        newcommand=pendingcommand(ident,fullcommand,func,param,querytype)
        if ident is None:
            ident=id(newcommand)
            pass
        # sys.stderr.write("Created newcommand; ident=%s\n" % (str(ident)))
        
        self.pending[ident]=newcommand
        
        # sys.stderr.write("Calling notify() \n")
        self.commcommandcondition.notify() # wake up a dispatcher, if necessary
        # sys.stderr.write("Calling release() \n")
        self.commcommandcondition.release()
        # sys.stderr.write("issuecommand() done \n")
        return ident
    
    def issuecommandsynchronous(self,fullcommand,querytype):
        # returns (retcode,return string,parsed result)
        # May ONLY be called when it is not possible that (a) something else may be calling
        # issuecommandsynchronous
        # AND (b) it is not possible that gtk is calling the timeout function do_poll() above. 
        
        dgc.command(self.dgch_sync,fullcommand)

        res=procresult(querytype,self.dgch_sync.buf)
        
        return (self.dgch_sync.retcode,self.dgch_sync.buf,res)

    def abortcommand(self,ident):
        # abort means prevent it from happening if possible
        # if it's still pending, abort it and return TRUE
        # if it's already been sent let it go, return FALSE,  and let the callback happen
        self.commcommandcondition.acquire() # acquire lock
        if ident in self.pending:
            del self.pending[ident]
            self.commcommandcondition.release() # release lock
            return True
        self.commcommandcondition.release() # release lock
        return False
        

    def cancelcommand(self,ident):
        # abort means prevent it from happening if possible and ignore the result if it was already sent out
        # if it's still pending, abort it and return CANCEL_ARBORTED
        # if it's already been sent let it go, return CANCEL_INHIBITED,  and stop the callback
        # if it's too late (response already queued) return CANCEL_TOOLATE

        self.commcommandcondition.acquire() # acquire lock
        if ident in self.pending:
            del self.pending[ident]
            self.commcommandcondition.release() # release lock
            return self.CANCEL_ABORTED
        
        for chan in self.commcommandlist:
            if chan.pendingcom.id==ident:
                chan.pendingcom.cancelled=True
                self.commcommandcondition.release() # release lock
                return self.CANCEL_INHIBITED
            pass
        
        
        self.commcommandcondition.release() # release lock
        return self.CANCEL_TOOLATE
        
        

    pass
