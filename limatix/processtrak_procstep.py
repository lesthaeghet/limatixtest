from __future__ import print_function

import sys
import os
import os.path
import posixpath
import socket
import copy
import inspect
import numbers
import traceback
import collections
import ast
import hashlib
import fnmatch
import binascii

from lxml import etree

try:
    from cStringIO import StringIO
    pass
except ImportError:
    from io import StringIO
    pass


import shutil
import datetime
import subprocess

try:
    # py2.x
    from urllib import pathname2url
    from urllib import url2pathname
    from urllib import quote
    from urllib import unquote
    from urlparse import urlparse
    from urlparse import urlunparse
    from urlparse import urljoin    
    pass
except ImportError:
    # py3.x
    from urllib.request import pathname2url
    from urllib.request import url2pathname
    from urllib.parse import quote
    from urllib.parse import unquote
    from urllib.parse import urlparse
    from urllib.parse import urlunparse
    from urllib.parse import urljoin
    pass

# import dg_units

from . import timestamp
from . import canonicalize_path
from .canonicalize_path import etxpath2human

from . import dc_value as dcv
from . import provenance as provenance
from . import xmldoc
from . import processtrak_prxdoc
from . import processtrak_stepparam
from . import processtrak_common


try:
    from pkg_resources import resource_string
    pass
except TypeError:
    # mask lack of pkg_resources when we are running under pychecker
    def resource_string(x,y):
        raise IOError("Could not import pkg_resources")
    pass


try: 
    __install_prefix__=resource_string(__name__, 'install_prefix.txt').decode('utf-8')
    pass
except IOError: 
    sys.stderr.write("processtrak: error reading install_prefix.txt. Assuming /usr/local.\n")
    __install_prefix__="/usr/local"
    pass


steppath=[os.path.join(__install_prefix__,"share","limatix","pt_steps")]


def find_script_in_path(contexthref,scriptname):
    #if os.path.exists(os.path.join(contexthref.getpath(),scriptname)):
    #    print("WARNING: direct paths to scripts should be specified with <script xlink:href=\"...\"/>. Use the name=\"...\" attribute only for scripts to be found in the script search path")
    #    pass
    
    #if posixpath.isabs(scriptname):
    #    return dcv.hrefvalue(quote(scriptname),contexthref=dcv.hrefvalue("./"))
    #
    #if posixpath.pathsep in scriptname:
    #    return dcv.hrefvalue(quote(scriptname),contexthref=contexthref)

    for trypath in steppath:
        if trypath==".":
            trypath=contexthref.getpath()
            pass
        
        if os.path.exists(os.path.join(trypath,url2pathname(scriptname))):
            return dcv.hrefvalue(quote(scriptname),contexthref=dcv.hrefvalue(pathname2url(trypath)+"/"))
        pass
    
    raise IOError("Could not find script %s in path %s" % (scriptname,unicode(steppath)))


def procstepmatlab(*args,**kwargs):
    # *** output should be rwlock'd exactly ONCE when this is called
    # *** Output will be rwlock'd exactly ONCE on return
    #     (but may have been unlocked in the interim)
    raise NotImplementedError("procstepmatlab")

def procsteppython_do_run(stepglobals,runfunc,argkw,ipythonmodelist,action,scripthref,pycode_text,pycode_lineno):

    if not ipythonmodelist[0]:
        resultdict=runfunc(**argkw)
        return resultdict
    else:
        # ipython mode
        # in-process kernel, a-la https://raw.githubusercontent.com/ipython/ipython/master/examples/Embedding/inprocess_qtconsole.py

        ## Set PyQt4 API version to 2 and import it -- required for ipython compatibility
        #import sip
        #sip.setapi('QVariant', 2)
        #sip.setapi('QString', 2)
        #sip.setapi('QDateTime', 2)
        #sip.setapi('QDate', 2)
        #sip.setapi('QTextStream', 2)
        #sip.setapi('QTime', 2)
        #sip.setapi('QUrl', 2)
        #from PyQt4 import QtGui   # force IPython to use PyQt4 by importing it first

        # RHEL6 compatibility  -- if running under Python 2.6, just import IPython, get PyQt4
        if sys.version_info < (2,7):
            from IPython.qt.console.rich_ipython_widget import RichIPythonWidget
            from IPython.qt.inprocess import QtInProcessKernelManager
            pass
        else: 

            # Under more recent OS's: Make matplotlib use PySide
            # http://stackoverflow.com/questions/6723527/getting-pyside-to-work-with-matplotlib
            import matplotlib
            matplotlib.use('Qt4Agg')
            matplotlib.rcParams['backend.qt4']='PySide'
            pass

        from IPython.lib import guisupport
        app = guisupport.get_app_qt4() 

        from IPython.qt.inprocess import QtInProcessKernelManager
        kernel_manager = QtInProcessKernelManager()
        kernel_manager.start_kernel()
        kernel = kernel_manager.kernel
        kernel.gui = 'qt4'
        
        # Should we attempt to run the function here?
        
        gui, backend, clobbered = kernel.shell.enable_pylab("qt4",import_all=False) # (args.gui, import_all=import_all)

        kernel.shell.push(stepglobals) # provide globals as variables
        kernel.shell.push(argkw) # provide arguments as variables
        
        kernel.shell.push({"kernel":kernel},interactive=False) # provide kernel for debugging purposes

        kernel_client = kernel_manager.client()
        kernel_client.start_channels()
        abort_requested_list=[False] # encapsulated in a list to make it mutable

        def stop():
            control.hide()
            kernel_client.stop_channels()
            kernel_manager.shutdown_kernel()
            app.exit()
            pass

        def abort():
            # simple exit doesn't work. See http://stackoverflow.com/questions/1527689/exit-from-ipython
            # too bad this doesn't work right now!!!
            class Quitter(object):
                def __repr__(self):
                    sys.exit()
                pass
            kernel.shell.push({"quitter":Quitter()})
            kernel.shell.ex("quitter")

            stop()
            abort_requested_list.pop()
            abort_requested_list.append(True)
            pass
        
        if pycode_text is None:            
            kernel.shell.write("\n\nExecute %s/%s\n" % (scripthref.getpath(),runfunc.__name__))
            pass
        else: 
            kernel.shell.write("\n\nExecute %s/%s/%s\n" % (scripthref.getpath(),action,runfunc.__name__))
            pass

        kernel.shell.write("Assign return value to \"ret\" and press Ctrl-D\n")
        kernel.shell.write("Set cont=True to disable interactive mode\n")
        # kernel.shell.write("call abort() to exit\n")

        from IPython.qt.console.rich_ipython_widget import RichIPythonWidget
        control = RichIPythonWidget()
        control.kernel_manager = kernel_manager
        control.kernel_client = kernel_client
        control.exit_requested.connect(stop)
        control.show()


        #sys.stderr.write("lines=%s\n" % (str(lines)))
        #sys.stderr.write("lines[0]=%s\n" % (str(lines[0])))
        try:
            if pycode_text is None:
                (lines,startinglineno)=inspect.getsourcelines(runfunc)
                
                assert(lines[0].startswith("def")) # first line of function is the defining line
                del lines[0] # remove def line
                lines.insert(0,"if 1:\n") # allow function to be indented
                runfunc_syntaxtree=ast.parse("".join(lines), filename=scripthref.getpath(), mode='exec') # BUG: Should set dont_inherit parameter and properly determine which __future__ import flags should be passed

                # fixup line numbers
                for syntreenode in ast.walk(runfunc_syntaxtree):
                    if hasattr(syntreenode,"lineno"):
                        syntreenode.lineno+=startinglineno-1
                        pass
                    pass

                # runfunc_syntaxtree should consist of the if statement we just added
                # use _fields attribute to look up fields of an AST element
                # (e.g. test, body, orelse for IF)
                # then those fields can be accessed directly
                assert(len(runfunc_syntaxtree.body)==1)
                code_container=runfunc_syntaxtree.body[0]
                assert(isinstance(code_container,ast.If)) # code_container is the if statement we just wrote
                
                kernel.shell.push({"runfunc_syntaxtree": runfunc_syntaxtree},interactive=False) # provide processed syntax tree for debugging purposes

                pass
            else : 
                fullsyntaxtree=ast.parse(pycode_text) # BUG: Should set dont_inherit parameter and properly determine which __future__ import flags should be passed
                # fixup line numbers
                for syntreenode in ast.walk(fullsyntaxtree):
                    if hasattr(syntreenode,"lineno"):
                        syntreenode.lineno+=pycode_lineno-1
                        pass
                    pass
                code_container=None
                for codeelement in fullsyntaxtree.body:
                    if isinstance(codeelement,ast.FunctionDef):
                        if codeelement.name==runfunc.__name__:
                            code_container=codeelement
                            pass
                        pass
                    
                    pass
                if code_container is None: 
                    raise ValueError("Couldn't find code for %s for ipython execution" % (runfunc.__name__)) 

                kernel.shell.push({"fullsyntaxtree": fullsyntaxtree},interactive=False) # provide full syntax tree for debugging purposes
                
                pass
            
            
            kernel.shell.push({"abort": abort}) # provide abort function
            kernel.shell.push({"cont": False}) # continue defaults to False



            
            returnstatement=code_container.body[-1]
            if isinstance(returnstatement,ast.Return):
                # last statement is a return statement!
                # Create assign statement that assigns 
                # the result to ret
                retassign=ast.Assign(targets=[ast.Name(id="ret",ctx=ast.Store(),lineno=returnstatement.lineno,col_offset=returnstatement.col_offset)],value=returnstatement.value,lineno=returnstatement.lineno,col_offset=returnstatement.col_offset)
                del code_container.body[-1] # remove returnstatement
                code_container.body.append(retassign) # add assignment
                pass
            

            runfunc_lines=code_container.body

            kernel.shell.push({"runfunc_lines": runfunc_lines,"scripthref": scripthref},interactive=False) # provide processed syntax tree for debugging purposes
            
            # kernel.shell.run_code(compile("kernel.shell.run_ast_nodes(runfunc_lines,scriptpath,interactivity='all')","None","exec"))
            from IPython.external.qt import QtCore
            QTimer=QtCore.QTimer

            def showret():
                control.execute("ret")
                pass
                
            
            def runcode():
                control.execute("kernel.shell.run_ast_nodes(runfunc_lines,scripthref.getpath(),interactivity='none')")
                # QTimer.singleShot(25,showret) # get callback 25ms into main loop
                # showret disabled because it prevents you from running the 
                # debugger in post-mortem mode to troubleshoot an exception:
                # import pdb; pdb.pm() 
                pass
            
            QTimer.singleShot(25,runcode) # get callback 25ms into main loop
            # control.execute("kernel.shell.run_ast_nodes(runfunc_lines,scripthref.getpath(),interactivity='none')")

            pass
        except:
            (exctype, excvalue) = sys.exc_info()[:2] 
            sys.stderr.write("%s while attempting to prepare URL %s code for interactive execution: %s\n" % (exctype.__name__,scripthref.absurl(),str(excvalue)))
            traceback.print_exc()
            raise




        guisupport.start_event_loop_qt4(app) 
        if abort_requested_list[0]:
            pass
        
        if kernel.shell.ev("cont"):
            # cont==True -> disable interactive mode
            ipythonmodelist.pop()
            ipythonmodelist.append(False)
            pass
        

        try : 
            return kernel.shell.ev("ret") # Assign result dictionary to "ret" variablex
        except NameError: # if ret not assigned, return {}
            return {}
        pass
    pass

def resultelementfromdict(output,resultdict):
    # resultdict can either be a dict
    # or a list/tuple of (key,element) pairs. 
    # tuple use case is so that what would otherwise be a key
    # can itself contain a dictionary of attributes

    resultelementdoc=xmldoc.xmldoc.newdoc("resultelement",nsmap=output.nsmap,contexthref=output.getcontexthref())
    
    applyresultdict(resultelementdoc,None,None,resultelementdoc.getroot(),resultdict)
    return resultelementdoc

def applyresultdict(output,prxdoc,steptag,element,resultdict):
    # resultdict can either be a dict
    # or a list/tuple of (key,element) pairs. 
    # tuple use case is so that what would otherwise be a key
    # can itself contain a dictionary of attributes

    
    if isinstance(resultdict,collections.Mapping):
        # dictionary or dictionary-like: 
        # Convert to list of (key,element) pairs
        resultlist=[ (key,resultdict[key]) for key in resultdict.keys() ]
        pass
    else:
        # list or tuple
        resultlist=resultdict
        pass

    # Go through results...
    for (resultname,resultitem) in resultlist: 


        #  resultitem=resultdict[resultname]
        attrdict={}
        if isinstance(resultname,tuple):
            # if result is a tuple, then treat first element 
            # of tuple as actual name, second element as attribute dictionary, 
            assert(len(resultname)==2)
            attrdict.update(resultname[1])
            name=resultname[0]
            pass
        else: 
            name=resultname
            pass

        if not ":" in name and None in output.nsmap:
            sys.stderr.write("processtrak_procstep.applyresultdict() WARNING: Results from processtrak\nsteps should always specify the XML namespace of result tags\nwhen a default namespace is set. Otherwise they get placed in\nthe default namespace, but not replaced on the next run.\n")
            pass


        if isinstance(resultitem,tuple):
            # if result is a tuple, then treat first element 
            # of tuple as an attribute dictionary, second
            # element as value object
            assert(len(resultitem)==2)
            attrdict.update(resultitem[0])
            resultvalue=resultitem[1]
            pass
        else: 
            resultvalue=resultitem
            pass
        
        # Remove preexisting elements if present
        oldelements=output.children(element,name,noprovenanceupdate=True)
        for oldelement in oldelements:
            # do the requested attributes match?
            attrmatch=True

            for attrname in attrdict:
                if not(output.hasattr(oldelement,attrname)) or output.getattr(oldelement,attrname)!=attrdict[attrname]:
                    attrmatch=False
                    break
                pass
            
            if attrmatch: 
                # no attribute mismatch... remove element
                output.removeelement(oldelement)
                pass
            pass
        
        # Create new element according to type
        # sys.stderr.write("resultdict=%s\n" % (str(resultdict))) 
        if isinstance(resultvalue,numbers.Number):
            newel=output.addsimpleelement(element,name,(resultvalue,))
            pass
        elif isinstance(resultvalue,dcv.value):
            newel=output.addelement(element,name)
            resultvalue.xmlrepr(output,newel)
            pass
        elif isinstance(resultvalue,basestring):
            newel=output.addelement(element,name)
            output.settext(newel,resultvalue)
            pass
        elif isinstance(resultvalue,xmldoc.xmldoc):            
            newel=output.addelement(element,name)
            # copy tree from resultvalue
            resultroot=copy.deepcopy(resultvalue.doc.getroot())
            newel[:]=resultroot[:]
            for attrname in resultroot.attrib:
                newel.attrib[attrname]=resultroot.attrib[attrname]
                pass
            newel.text=resultroot.text
            newel.tail=resultroot.tail

            # mark provenance of sub-elements
            for subel in newel.iterdescendants():
                provenance.elementgenerated(output,subel)
                pass
            pass
        else :
            if prxdoc is not None and steptag is not None:
                raise ValueError("step %s gave unknown result type %s for %s" % (prxdoc.tostring(steptag),unicode(resultvalue.__class__),name))
            else: 
                raise ValueError("step gave unknown result type %s for %s" % (unicode(resultvalue.__class__),name))
            pass
        # add attributes to newel
        for attrname in attrdict:
            output.setattr(newel,attrname,attrdict[attrname])
            pass

        pass
    pass

def procsteppython_runelement(output,prxdoc,prxnsmap,steptag,rootprocesspath,stepprocesspath,elementpath,stepglobals,argnames,argsdefaults,params,inputfilehref,ipythonmodelist,execfunc,action,scripthref,pycode_text,pycode_lineno):
    # *** output should be rwlock'd exactly ONCE when this is called
    # *** Output will be rwlock'd exactly ONCE on return
    #     (but may have been unlocked in the interim)



    element=output.restorepath(elementpath)

    print("Element %s\r" % (dcv.hrefvalue.fromelement(output,element).humanurl()),end="\r")
    #print("Element %s\r" % (canonicalize_path.getelementhumanxpath(output,element,nsmap=prxnsmap)),end="\r")
    sys.stdout.flush()

    rootprocess_el=output.restorepath(rootprocesspath)
    
    provenance.starttrackprovenance()
    try : # try-catch-finally block for starttrackprovenance()
        
        argkw={}
        
        #sys.stderr.write("argnames=%s\n" % (str(argnames)))
        #sys.stderr.write("params.keys()=%s\n" % (str(params.keys())))
        
        for argname in argnames:
            # argname often has a underscore-separated type suffix
            if "_" in argname:
                (argnamebase,argnametype)=argname.rsplit("_",1)
                pass
            else:
                argnamebase=None
                pass
            
            if argname in params:
                # calling evaluate tracks provenance!
                # returns XML element for auto-params or xpaths
                # returns dc_value for fixed numeric params
                # returns string for fixed string params
                argkw[argname]=processtrak_stepparam.evaluate_params(params,argname,None,output,element)
                pass
            elif argnamebase in params:
                argkw[argname]=processtrak_stepparam.evaluate_params(params,argnamebase,argnametype,output,element)
                
            elif argname=="_xmldoc":  # _xmldoc parameter gets output XML document
                argkw[argname]=output         # supply output XML document
                pass
            elif argname=="_prxdoc":  # _xmldoc parameter gets output XML document
                argkw[argname]=prxdoc         # supply output XML document
                pass
            elif argname=="_step":  # _xmldoc parameter gets output XML document
                argkw[argname]=steptag         # supply output XML document
                pass
            elif argname=="_inputfilename":  # _inputfilename parameter gets unquoted name (but not path) of input file
                argkw[argname]=inputfilehref.get_bare_unquoted_filename()
                pass
            elif argname=="_element" or argname=="_tag": # _element (formerly _tag) parameter gets current tag we are operating on
                argkw[argname]=element
                pass
            elif argname=="_dest_href":
                # Get hrefvalue pointing at destination directory, where
                # files should be written
                destlist=output.xpath("dc:summary/dc:dest",namespaces=processtrak_common.prx_nsmap)
                argkw[argname]=None
                if len(destlist)==1:
                    argkw[argname]=dcv.hrefvalue.fromxml(output,destlist[0])
                    pass
                pass
            else :
                # Try to extract it from a document tag
                try : 
                    argkw[argname]=processtrak_stepparam.findparam(prxnsmap,output,element,argname)
                    pass
                except NameError:
                    # if there is a default, use that
                    if argname in argsdefaults:
                        argkw[argname]=argsdefaults[argname]
                        pass
                    else:
                        raise  # Let user know we can't find this!
                    pass
                pass
            pass
        
        # unlock XML file if "rununlocked" so parallel processes can mess with it

        #os.chdir(destdir) # CD into destination directory
        try :  # try... catch.. finally.. block for changed directory
            if execfunc.__name__.endswith("unlocked"): 
                assert(not "_tag" in argnames) # can't supply tag if lock is released
                output.unlock_rw() # release output lock 
                try: 
                    resultdict=procsteppython_do_run(stepglobals,execfunc,argkw,ipythonmodelist,action,scripthref,pycode_text,pycode_lineno)
                    pass
                finally: 
                    output.lock_rw() # secure output lock ... otherwise
                    # an exception would be handled several levels above
                    # which assumes we are locked. 
                    pass

                del rootprocess_el
                element=output.restorepath(elementpath)
                
                pass
            else: 
                resultdict=procsteppython_do_run(stepglobals,execfunc,argkw,ipythonmodelist,action,scripthref,pycode_text,pycode_lineno)
                # print("processtrak: print_current_used() after do_run of %s" % (str(execfunc)))
                # provenance.print_current_used()
                
            
                output.should_be_rwlocked_once() # Verify that after running, the output is still locked exactly once
                element=output.restorepath(elementpath) # run function may have unlocked output temporarily so we need to restore the element from its path
                pass
            pass
        except: 
            raise
        finally: 
            #os.fchdir(cwd_fd) # CD back to regular directory
            pass
        
        if resultdict is None: 
            resultdict={}  # no results provided
            pass
        

        applyresultdict(output,prxdoc,steptag,element,resultdict)
    
        pass
    except:
        raise
    finally:
        # print("processtrak: print_current_used()")
        # provenance.print_current_used()

        (modified_elements,referenced_elements)=provenance.finishtrackprovenance()
        pass

    # exit with output still in locked state. 
    return (modified_elements,referenced_elements)
    


def procsteppython_execfunc(scripthref,pycode_text,pycode_lineno,prxdoc,prxnsmap,output,steptag,scripttag,rootprocesspath,stepprocesspath,stepglobals,elementmatch,elementmatch_nsmap,params,filters,inputfilehref,debugmode,stdouthandler,stderrhandler,ipythonmodelist,execfunc,action):
    
    
    (argnames, varargs, keywords, defaults)=inspect.getargspec(execfunc)        
    
    argsdefaults={}
    if defaults is not None:
        numdefaults=len(defaults)
        argsdefaults=dict(zip(argnames[-numdefaults:],defaults))
        # argsdefaults is a dictionary by argname of default values.
        pass
    if None in elementmatch_nsmap:
        del elementmatch_nsmap[None]  # Can not pass None entry
        pass
    # Add filters to elementmatch
    
    for elementfilter in filters:
        elementmatch+="[%s]" % (elementfilter)
        pass

    # Search for matching elements

    # sys.stderr.write("elementmatch=%s\n" % (elementmatch))
    elements=output.xpath(elementmatch,namespaces=elementmatch_nsmap,variables={"filepath":output.filehref.getpath(),"filename":os.path.split(output.filehref.getpath())[1]})


    if len(elements)==0:
        sys.stderr.write("Warning: step %s: no matching elements for output href %s\n" % (processtrak_prxdoc.getstepname(prxdoc,steptag),output.get_filehref().absurl()))
        pass
    

    elementpaths=[ output.savepath(element) for element in elements]

    # output.unlock_rw() # release output lock

    

    # Loop over each matching element
    for elementpath in elementpaths:

        modified_elements=set([])
        referenced_elements=set([])

        el_starttime=timestamp.now().isoformat()
        
        # Capture python stdio/stderr 
        errcapt=StringIO()
        stdouthandler.set_dest(errcapt)
        stderrhandler.set_dest(errcapt)

        status="success"

        output.should_be_rwlocked_once()

        try : 
            (modified_elements,referenced_elements)=procsteppython_runelement(output,prxdoc,prxnsmap,steptag,rootprocesspath,stepprocesspath,elementpath,stepglobals,argnames,argsdefaults,params,inputfilehref,ipythonmodelist,execfunc,action,scripthref,pycode_text,pycode_lineno)
            pass
        except KeyboardInterrupt: 
            # Don't want to hold off keyboard interrupts!
            raise
        except: 
            (exctype, excvalue) = sys.exc_info()[:2] 
            
            
            sys.stderr.write("%s while processing step %s element on element %s in file %s: %s\n" % (exctype.__name__,action,etxpath2human(elementpath,output.nsmap),output.filehref.getpath(),unicode(excvalue)))
            traceback.print_exc()
            
            status="exception"
            
            if debugmode and sys.stdin.isatty() and sys.stderr.isatty():
                # automatically start the debugger from an exception in debug mode (if stdin and stderr are ttys) 
                import pdb # Note: Should we consider downloading/installing ipdb (ipython support for pdb)???
                # run debugger in post-mortem mode. 
                pdb.post_mortem()
                pass


            pass

        stdouthandler.set_dest(None)
        stderrhandler.set_dest(None)

        output.should_be_rwlocked_once()

        rootprocess_el=output.restorepath(rootprocesspath)
        # Create lip:process element that contains lip:used tags listing all referenced elements
        element=output.restorepath(elementpath)
        # print "Reference location=%s" % (canonicalize_path.create_canonical_etxpath(output.filename,output.doc,rootprocess_el.getparent()))
        # print "Target location=%s" % (canonicalize_path.create_canonical_etxpath(output.filename,output.doc,element))
        # print "Relative location=%s" % (canonicalize_path.relative_etxpath_to(canonicalize_path.create_canonical_etxpath(output.filename,output.doc,rootprocess_el.getparent()),canonicalize_path.create_canonical_etxpath(output.filename,output.doc,element)))


        process_el=provenance.writeprocessprovenance(output,rootprocesspath,stepprocesspath,referenced_elements)
        
        # write timestamps
        provenance.write_timestamp(output,process_el,"lip:starttimestamp",el_starttime)
        provenance.write_timestamp(output,process_el,"lip:finishtimestamp")
        provenance.write_process_info(output,process_el)  # We always write process info to ensure uniqueness of our UUID. It would be better to merge with parent elements before calculating UUID.
        provenance.write_process_log(output,process_el,status,errcapt.getvalue())

        provenance.write_target(output,process_el,dcv.hrefvalue.fromelement(output,element).value())  # lip:target -- target of this particular iteration (ETXPath)
        
        # Generate uuid
        process_uuid=provenance.set_hash(output,rootprocess_el,process_el)
    
        # Mark all modified elements with our uuid
        provenance.mark_modified_elements(output,modified_elements,process_uuid)

        errcapt.close()
        del errcapt

        output.should_be_rwlocked_once() 

        pass

    pass

def procsteppython(scripthref,pycode_el,prxdoc,output,steptag,scripttag,rootprocesspath,initelementmatch,initelementmatch_nsmap,elementmatch,elementmatch_nsmap,params,filters,inputfilehref,debugmode,stdouthandler,stderrhandler,ipythonmodelist):
    # *** output should be rwlock'd exactly ONCE when this is called
    # *** Output will be rwlock'd exactly ONCE on return
    #     (but may have been unlocked in the interim)

    prxnsmap=dict(prxdoc.getroot().nsmap)

    stepglobals={}

    # !!!*** NON-REENTRANT
    # Temporarily adjust sys.path so as to add script's directory 
    
    syspath_save=sys.path
    syspath_new=copy.deepcopy(syspath_save)
    syspath_new.insert(0,os.path.split(scripthref.getpath())[0])
    sys.path=syspath_new

    if pycode_el is None: 
        #execfile(scripthref.getpath(),stepglobals)  # load in step
        
        with open(scripthref.getpath()) as f:
            code = compile(f.read(), scripthref.getpath(), 'exec')
            exec(code, stepglobals)
            pass
        
        pycode_text=None
        pycode_lineno=None
        pass
    else: 
        pycode_text=pycode_el.text
        pycode_lineno=pycode_el.sourceline
        # precede code with pycode_lineno blank lines so that parse errors, etc. get the right line number
        #pycode_parsed=ast.parse(("\n"*(pycode_lineno-1))+pycode_text,scriptpath)
        pycode_compiled=compile(("\n"*(pycode_lineno-1))+pycode_text,scripthref.getpath(),"exec")
        exec(pycode_compiled,stepglobals)
        pass
    sys.path=syspath_save
    
    # Find modules imported or referenced
    modules=set()
    for variable in stepglobals:
        if hasattr(variable,"__module__"):
            modulename=variable.__module__
            pass
        elif hasattr(variable,"__package__"):
            modulename=variable.__package__
            pass
        else: 
            continue
        modulenamesplit=modulename.split(".")
        for modulenamecomponentcnt in range(1,len(modulenamesplit)):
            trymodulename=".".join(modulenamesplit[:modulenamecomponentcnt])
            modules.add(trymodulename)
            pass
        pass
    # *** should Save module.__version__ and other version parameters with provenance!!!

    # create <lip:process> tag for this step 
    
    # output lock should be locked exactly once by caller
    output.should_be_rwlocked_once()
    #output.lock_rw()  # secure output lock

    rootprocess_el=output.restorepath(rootprocesspath)



    stepprocess_el=output.addelement(rootprocess_el,"lip:process")
    provenance.write_timestamp(output,stepprocess_el,"lip:starttimestamp")
    
    action=processtrak_prxdoc.getstepname(prxdoc,steptag)
    provenance.write_action(output,stepprocess_el,action)
    for module in (set(sys.modules.keys()) & modules):  # go through modules
        provenance.reference_pymodule(output,stepprocess_el,"lip:used",rootprocess_el.getparent(),module,warnlevel="none")
        pass

    provenance.write_process_info(output,stepprocess_el) # ensure uniqueness prior to uuid generation

    # Generate uuid
    stepprocess_uuid=provenance.set_hash(output,rootprocess_el,stepprocess_el)
    stepprocesspath=output.savepath(stepprocess_el)


    argkw={}

    initfunc=None
    
    # find "init" function or method
    if prxdoc.hasattr(steptag,"initfunction"):
        initfunc=stepglobals[prxdoc.getattr(steptag,"initfunction")]
        pass
    elif "initunlocked" in stepglobals:
        initfunc=stepglobals["initunlocked"]
        pass
    elif "init" in stepglobals : 
        initfunc=stepglobals["init"]
        pass

    if initfunc is not None:
        procsteppython_execfunc(scripthref,pycode_text,pycode_lineno,prxdoc,prxnsmap,output,steptag,scripttag,rootprocesspath,stepprocesspath,stepglobals,initelementmatch,initelementmatch_nsmap,params,[],inputfilehref,debugmode,stdouthandler,stderrhandler,ipythonmodelist,initfunc,action)
        pass
    
    
    # find "run" function or method
    if prxdoc.hasattr(steptag,"function"):
        runfunc=stepglobals[prxdoc.getattr(steptag,"function")]
        pass
    elif "rununlocked" in stepglobals:
        runfunc=stepglobals["rununlocked"]
        pass
    else : 
        runfunc=stepglobals["run"]
        pass


    procsteppython_execfunc(scripthref,pycode_text,pycode_lineno,prxdoc,prxnsmap,output,steptag,scripttag,rootprocesspath,stepprocesspath,stepglobals,elementmatch,elementmatch_nsmap,params,filters,inputfilehref,debugmode,stdouthandler,stderrhandler,ipythonmodelist,runfunc,action)

    print("") # add newline

    # output.lock_rw()
    stepprocess_el=output.restorepath(stepprocesspath)
    provenance.write_timestamp(output,stepprocess_el,"lip:finishtimestamp")
    # output.unlock_rw()
    

    pass


def procstep(prxdoc,out,steptag,filters,overall_starttime,debugmode,stdouthandler,stderrhandler,ipythonmodelist):
    # *** output should be unlocked when this is called

    defaultelementmatch="*" # defaults to all child elements of main tag
    defaultelementmatch_nsmap=None
    try: 
        defaultelementmatchel=prxdoc.xpathsingle("prx:elementmatch")
        defaultelementmatch=defaultelementmatchel.text
        defaultelementmatch_nsmap=defaultelementmatchel.nsmap
        pass
    except NameError:
        pass

    defaultinputfilematch="*" # defaults to matching anything
    try: 
        defaultinputfilematchel=prxdoc.xpathsingle("prx:inputfilematch")
        defaultinputfilematch=defaultinputfilematchel.text
        pass
    except NameError:
        pass

    
    scripttag=prxdoc.xpathsinglecontext(steptag,"prx:script")
    
    elementmatch=defaultelementmatch
    elementmatch_nsmap=defaultelementmatch_nsmap
    # sys.stderr.write("defaultelementmatch=%s\n" % (elementmatch))

    inputfilematch=defaultinputfilematch

    # try for <prx:elementmatch> in <step> 
    try: 
        elementmatchel=prxdoc.xpathsinglecontext(steptag,"prx:elementmatch")
        elementmatch=elementmatchel.text
        # sys.stderr.write("overrideelementmatch=%s\n" % (elementmatch))
        elementmatch_nsmap=elementmatchel.nsmap
        pass
    except NameError:
        pass

    # try for <prx:inputfilematch> in <step> 
    try: 
        inputfilematchel=prxdoc.xpathsinglecontext(steptag,"prx:inputfilematch")
        inputfilematch=inputfilematchel.text
        # sys.stderr.write("overrideinputfilematch=%s\n" % (inputfilematch))
        pass
    except NameError:
        pass

    
    # try for <prx:elementmatch> in <script> 
    try: 
        elementmatchel=prxdoc.xpathsinglecontext(scripttag,"prx:elementmatch")
        elementmatch=elementmatchel.text
        # sys.stderr.write("overrideelementmatch=%s\n" % (elementmatch))
        elementmatch_nsmap=elementmatchel.nsmap
        pass
    except NameError:
        pass

    # try for <prx:inputfilematch> in <script> 
    try: 
        inputfilematchel=prxdoc.xpathsinglecontext(scripttag,"prx:inputfilematch")
        inputfilematch=inputfilematchel.text
        # sys.stderr.write("overrideinputfilematch=%s\n" % (inputfilematch))
        pass
    except NameError:
        pass


    # return if we don't pass filename matching
    
    if not fnmatch.fnmatch(out.inputfilehref.get_bare_unquoted_filename(),inputfilematch):
        return
    


    
    
    initelementmatch="/*" # select root element
    initelementmatch_nsmap={}

    try: 
        initelementmatchel=prxdoc.xpathsinglecontext(scripttag,"prx:initelementmatch")
        initelementmatch=initelementmatchel.text
        initelementmatch_nsmap=initelementmatchel.nsmap
        pass
    except NameError:
        pass

                         
    pycode_el=None
    if prxdoc.hasattr(scripttag,"xlink:href"): 
        #scriptpath=prxdoc.get_href_fullpath(contextnode=scripttag)
        scripthref=dcv.hrefvalue.fromxml(prxdoc,scripttag)
        #scriptpath=scripthref.getpath()
        pass
    elif prxdoc.hasattr(scripttag,"name"): 
        scripthref=find_script_in_path(prxdoc.filehref,prxdoc.getattr(scripttag,"name"))
        pass
    else: 
        pycode_el=prxdoc.child(scripttag,"prx:pycode") # set to pycode tag or None
        scripthref=prxdoc.filehref
        if pycode_el is None: 
            raise ValueError("script %s does not specify file or python code" % (prxdoc.tostring(scripttag)))
        pass

    # Build parameter: dictionary by name of lists of stepparam objects
    params={}
    

    for paramel in prxdoc.xpathcontext(steptag,"prx:param|prx:script/prx:param"):
        paramname=prxdoc.getattr(paramel,"name")
        param=processtrak_stepparam.stepparam(name=paramname,prxdoc=prxdoc,element=paramel)

        if not param.name in params:
            params[param.name]=[]
            pass
        params[param.name].append(param)
        
        pass

    processtrak_common.open_or_lock_output(prxdoc,out,overall_starttime,copyfileinfo=None) # procsteppython/procstepmatlab are called with output locked exactly once
    try : 
        if pycode_el is not None or scripthref.get_bare_unquoted_filename().endswith(".py"):
            procsteppython(scripthref,pycode_el,prxdoc,out.output,steptag,scripttag,out.processpath,initelementmatch,initelementmatch_nsmap,elementmatch,elementmatch_nsmap,params,filters,out.inputfilehref,debugmode,stdouthandler,stderrhandler,ipythonmodelist)
            pass
        elif scripthref.get_bare_unquoted_filename().endswith(".m"):
            procstepmatlab(scripthref.getpath(),prxdoc,out.output,steptag,scripttag,out.processpath,elementmatch,elementmatch_nsmap,params,filters,out.inputfilehref,debugmode,ipythonmodelist)
            pass
        pass
    except: 
        raise
    finally: 
        out.output.unlock_rw() # procsteppython/procstepmatlab are called with output locked exactly once
        pass

    pass
