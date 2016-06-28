
import sys

from lxml import etree
import numpy as np
import traceback

import dbus
import dbus.service

from dbus.mainloop.glib import DBusGMainLoop
# import gobject

__pychecker__="no-import"

xpathnamespaces={"dc":"http://thermal.cnde.iastate.edu/datacollect","dcv":"http://limatix.org/dcvalue"}

bus_name="edu.iastate.cnde.thermal.datacollect2" # bus name / server

class dc_dbus_paramserver(dbus.service.Object):
    paramdb = None
    dbusloop = None
    checklists = None

    def __init__(self,paramdb,checklists=None):
        # checklists is an optional list of checklists 
        # currently being executed... used to match ID's for 
        # adding xml automeas entries.
        self.paramdb=paramdb
        self.checklists=checklists

        self.dbusloop=DBusGMainLoop(set_as_default=True)

        sessionbus=dbus.SessionBus()
        
        ret=sessionbus.request_name(bus_name,dbus.bus.NAME_FLAG_DO_NOT_QUEUE)
        if ret != dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER:
            print("Error %d reserving dbus name %s" % (ret,bus_name))
            print(" ")
            print("dbus is used to share parameters with Matlab/Octave")
            print("Make sure a copy of datacollect2 is not already running")
            print("If you need to run multiple copies simultaneously you can")
            print("run the second copy through dbus-launch to create a private")
            print("bus")
            print("Exiting...")
            sys.exit(1)
            pass

        bus_name_obj=dbus.service.BusName(bus_name,sessionbus)  
        dbus.service.Object.__init__(self,bus_name_obj,"/edu/iastate/cnde/thermal/datacollect2/paramdb2")
        
        pass

    @dbus.service.method(dbus_interface="edu.iastate.cnde.thermal.datacollect2.paramdb2",in_signature='s', out_signature='sddsss')
    def paramlookup(self,paramname):
        # print "got lookup; paramname=%s" % (paramname)

        try :
            dblrep=np.nan
            imagrep=np.nan
            units=""

            dcvalue=self.paramdb[str(paramname)].dcvalue
            classname=dcvalue.__class__.__name__

            # Complex Values Cannot Be Sent Through DBus - Must Leave as NaN - Resolve on the Other Side            
            if hasattr(dcvalue,"numvalue") and classname != "complexunitsvalue":
                dblrep=dcvalue.numvalue()
                pass

            if classname == "complexunitsvalue":
                dblrep=dcvalue.value().real
                imagrep=dcvalue.value().imag

            if hasattr(dcvalue,"units"):
                units=str(dcvalue.units())
                pass
            
            assert(classname[-5:]=="value")
            classdescr=classname[:-5]
            xmlobj=etree.Element("{http://limatix.org/datacollect}%s" % (str(paramname)),nsmap=xpathnamespaces)

            dcvalue.xmlrepr(None,xmlobj)

            # print units
            return (str(dcvalue),dblrep,imagrep,etree.tostring(xmlobj,encoding='utf8'),classdescr,units)
        except : 
            (exctype,excvalue)=sys.exc_info()[:2]
            print("ERROR %s %s" % (str(exctype.__name__),str(excvalue)))
            traceback.print_exc()
            return ("ERROR %s %s" % (str(exctype.__name__),str(excvalue)),np.nan,np.nan,"<xmlns:dc=\"http://limatix.org/datacollect\" dc:error/>","None","")
        pass


    @dbus.service.method(dbus_interface="edu.iastate.cnde.thermal.datacollect2.paramdb2",in_signature='ss', out_signature='sddsss')
    def paramlookupunits(self,paramname,unitreq):
        # parameter lookup & unit conversion to unitreq
        
        try :
            dblrep=np.nan
            imagrep=np.nan
            units=""
            
            dcvalue=self.paramdb[str(paramname)].dcvalue.inunits(unitreq)
            classname=dcvalue.__class__.__name__
            
            # Complex Values Cannot Be Sent Through DBus - Must Leave as NaN - Resolve on the Other Side
            if classname != "complexunitsvalue":
                dblrep=dcvalue.value()

            if classname == "complexunitsvalue":
                dblrep=dcvalue.value().real
                imagrep=dcvalue.value().imag

            units=str(dcvalue.units())          
            
            assert(classname[-5:]=="value")
            classdescr=classname[:-5]
            xmlobj=etree.Element("{http://limatix.org/datacollect}%s" % (str(paramname)),nsmap=xpathnamespaces)
            
            dcvalue.xmlrepr(None,xmlobj)
            
            # print units
            return (str(dcvalue),dblrep,imagrep,etree.tostring(xmlobj,encoding='utf8'),classdescr,units)
        except : 
            (exctype,excvalue)=sys.exc_info()[:2]
            print("ERROR %s %s" % (str(exctype.__name__),str(excvalue)))
            traceback.print_exc()
            return ("ERROR %s %s" % (str(exctype.__name__),str(excvalue)),np.nan,np.nan,"<xmlns:dc=\"http://limatix.org/datacollect\" dc:error/>","None","")
        pass
    
        


    @dbus.service.method(dbus_interface="edu.iastate.cnde.thermal.datacollect2.paramdb2",in_signature='ss', out_signature='sddsss')
    def requestvalxml(self,paramname,paramxml):
        # print "got lookup; paramname=%s" % (paramname)

        try :

            xml=etree.XML(paramxml)
            
            pdbentry=self.paramdb[paramname]

            dcvalue=pdbentry.paramtype.fromxml(None,xml,defunits=pdbentry.defunits)
            
            pdbentry.requestval_sync(dcvalue)

            return self.paramlookup(paramname)
        
        except : 
            (exctype,excvalue)=sys.exc_info()[:2]
            print("ERROR %s %s" % (str(exctype.__name__),str(excvalue)))
            traceback.print_exc()
            return ("ERROR %s %s" % (str(exctype.__name__),str(excvalue)),np.nan,np.nan,"<xmlns:dc=\"http://limatix.org/datacollect\" dc:error/>","None","")
        pass

    @dbus.service.method(dbus_interface="edu.iastate.cnde.thermal.datacollect2.paramdb2",in_signature='sds', out_signature='sddsss')
    def requestvalunits(self,paramname,value,units):
        # print "got lookup; paramname=%s" % (paramname)

        try :

            
            pdbentry=self.paramdb[paramname]

            dcvalue=pdbentry.paramtype(value,units=units,defunits=pdbentry.defunits)
            
            pdbentry.requestval_sync(dcvalue)


            return self.paramlookup(paramname)
        
        except : 
            (exctype,excvalue)=sys.exc_info()[:2]
            print("ERROR %s %s" % (str(exctype.__name__),str(excvalue)))
            traceback.print_exc()
            return ("ERROR %s %s" % (str(exctype.__name__),str(excvalue)),np.nan,np.nan,"<xmlns:dc=\"http://limatix.org/datacollect\" dc:error/>","None","")
        pass


    @dbus.service.method(dbus_interface="edu.iastate.cnde.thermal.datacollect2.paramdb2",in_signature='ss', out_signature='sddsss')
    def requestvalstr(self,paramname,paramstr):
        # print "got lookup; paramname=%s" % (paramname)

        try :

            pdbentry=self.paramdb[paramname]

            requestvalres=pdbentry.requestvalstr_sync(paramstr)
            # print "requestval returns %s" % (requestvalres)
            
            curvalue=self.paramlookup(paramname)
            # print "curvalue=%s" % (unicode(curvalue))
            return curvalue
        
        except : 
            (exctype,excvalue)=sys.exc_info()[:2]
            print("ERROR %s %s" % (str(exctype.__name__),str(excvalue)))
            traceback.print_exc()
            return ("ERROR %s %s" % (str(exctype.__name__),str(excvalue)),np.nan,np.nan,"<xmlns:dc=\"http://limatix.org/datacollect\" dc:error/>","None","")
        pass

    # Function to return a list of paramter names
    # Allows remote callers to discover what parameters are available
    @dbus.service.method(dbus_interface="edu.iastate.cnde.thermal.datacollect2.paramdb2",in_signature='', out_signature='asas')
    def getparamlist(self):
        try:
            paramlist = self.paramdb.keys()
            typelist = []
            for item in paramlist:
                typelist.append(self.paramdb[item].paramtype.__name__)
            return (paramlist,typelist)
        except:
            (exctype,excvalue)=sys.exc_info()[:2]
            print("ERROR %s %s" % (str(exctype.__name__),str(excvalue)))
            traceback.print_exc()
            return ([],[])

    # Function to check whether a parameter exists
    # Will return true if parameter exists - false if it doesn't
    @dbus.service.method(dbus_interface="edu.iastate.cnde.thermal.datacollect2.paramdb2",in_signature='s', out_signature='b')
    def paramexists(self, paramname):
        if paramname in self.paramdb:
            return True
        else:
            return False

    # call automeas() with a <automeas> tag containing parameters/values
    # returns empty string for success, otherwise error message
    @dbus.service.method(dbus_interface="edu.iastate.cnde.thermal.datacollect2.paramdb2",in_signature='ss', out_signature='s')
    def automeas(self,idstr,xmlsegment):
        try :
            idnum=int(idstr)
            for checklist in self.checklists: 
                for step in checklist.steps:
                    # sys.stderr.write("check id... %d vs. %d\n" % (id(step.stepobj),idnum))
                    if id(step.stepobj)==idnum:
                        # id matches... apply log entry here
                        parsedseg=etree.XML(xmlsegment)
                        
                        checklist.xmldoc.lock_rw()
                        try : 
                            xmltag=checklist.xmldoc.restorepath(step.xmlpath)

                        
                            # find or create 'autoexp' element to surround automeas
                            autoexps=xmltag.xpath('dc:autoexp',namespaces=xpathnamespaces)
                            if len(autoexps) > 0:
                                autoexp=autoexps[0]
                                pass
                            else :
                                autoexp=etree.Element('{http://limatix.org/datacollect}autoexp',nsmap=xpathnamespaces)
                                xmltag.append(autoexp)
                                pass

                            autoexp.append(parsedseg)
                            pass
                        except: 
                            raise
                        finally:
                            checklist.xmldoc.unlock_rw()
                            pass

                        return "" # empty string means no error
                    pass
                pass
            raise ValueError("No match to ID %s" % (idstr))
        except : 
            (exctype,excvalue)=sys.exc_info()[:2]
            print("ERROR %s %s" % (str(exctype.__name__),str(excvalue)))
            traceback.print_exc()
            return "ERROR %s %s" % (str(exctype.__name__),str(excvalue))
        pass


    
    pass



#DBusGMainLoop(set_as_default=True)

#testservice=testserver()

#loop = gobject.MainLoop()
#loop.run()
