import xmldoc
import traceback

try :
    import dbus
    # An exception here usually means a libexpat conflict. To work around on RHEL6, see the patched version on thermal in /root/python_ownexpat that built python-2.6.6-36sdh4.el6.x86_64.rpm
    # This version uses a namespaced copy of expat rather than the system version
    pass
except:
    traceback.print_exc()
    pass


# import dbus.service

import dc_value
from lxml import etree

# import gobject

bus_name="edu.iastate.cnde.thermal.datacollect2" # bus name / server
bus_object="/edu/iastate/cnde/thermal/datacollect2/paramdb2" # object
bus_interface="edu.iastate.cnde.thermal.datacollect2.paramdb2" # interface... like a Java interface


def dc_param(name):
    sessionbus=dbus.SessionBus()

    proxy=sessionbus.get_object(bus_name,bus_object)

    (stringrep,doublerep,imagrep,xmlrep,valueclassname,units)=proxy.paramlookup(name,dbus_interface=bus_interface)

    if valueclassname is None or valueclassname=="None":
        raise KeyError(name)
    
    valueclass=getattr(dc_value,valueclassname+"value")
    valueobj=valueclass.fromxml(None,etree.XML(xmlrep))
    return valueobj

# Get List of Parameters
def dc_getparamlist():
    sessionbus = dbus.SessionBus()
    proxy = sessionbus.get_object(bus_name, bus_object)
    (paramlist, typelist) = proxy.getparamlist()
    outlist = []
    outtypes = []
    # Convert to normal python types
    for item in paramlist:
        outlist.append(str(item))
    for item in typelist:
        outtypes.append(str(item))
    return (outlist,outtypes)

# Check if parameter exists
def dc_paramexists(paramname):
    sessionbus = dbus.SessionBus()
    proxy = sessionbus.get_object(bus_name, bus_object)
    if proxy.paramexists(paramname):
        return True
    else:
        return False

# Note that this is inherently synchronous. It returns the actual new value
def dc_requestval(name,dcvalueobj):
    sessionbus=dbus.SessionBus()

    proxy=sessionbus.get_object(bus_name,bus_object)

    reqxmlrep=etree.Element("{http://thermal.cnde.iastate.edu/datacollect}"+name,nsmap={"dc":"http://thermal.cnde.iastate.edu/datacollect","dcv":"http://thermal.cnde.iastate.edu/dcvalue"})
    dcvalueobj.xmlrepr(None,reqxmlrep)
    reqxmlstr=etree.tostring(reqxmlrep,encoding="utf-8")

    (stringrep,doublerep,imagrep,xmlrep,valueclassname,units)=proxy.requestvalxml(name,reqxmlstr,dbus_interface=bus_interface)

    if valueclassname is None or valueclassname=="None":
        raise KeyError(name)
    
    valueclass=getattr(dc_value,valueclassname+"value")
    valueobj=valueclass.fromxml(None,etree.XML(xmlrep))
    return valueobj

# Note that this is inherently synchronous. It returns the actual new value
def dc_requestvalstr(name,strrep):
    sessionbus=dbus.SessionBus()

    proxy=sessionbus.get_object(bus_name,bus_object)


    (stringrep,doublerep,imagrep,xmlrep,valueclassname,units)=proxy.requestvalstr(name,strrep,dbus_interface=bus_interface)

    if valueclassname is None or valueclassname=="None":
        raise KeyError(name)
    
    valueclass=getattr(dc_value,valueclassname+"value")
    valueobj=valueclass.fromxml(None,etree.XML(xmlrep))
    return valueobj

# dc_automeas creates the <dc:automeas> tags used for
# automated measurement logging. 
# You need to give it the id provided by the script button 
# in datacollect so that datacollect will know where to 
# send your data.

# It works like a regular
# xmldoc (use addelement("/","dc:foo") to add an element, 
# then dc_value.xmlrepr() to populate it with a value. 
# Alternatively use addsimpleelement("/","dc:foo",(value,units))
#
# Finally, call the saveautomeas() method to pass it off 
# to datacollect. It will immediately be written to the checklist, 
# and written to the experiment log once the done button is selected.

class dc_automeas(xmldoc.xmldoc):
    idstr=None
    def __init__(self,idstr):
         xmldoc.xmldoc.__init__(self,None,"dc:automeas")
         self.idstr=idstr
         pass
    
    def saveautomeas(self):
        sessionbus=dbus.SessionBus()
        
        proxy=sessionbus.get_object(bus_name,bus_object)

        result=proxy.automeas(self.idstr,etree.tostring(self.doc,encoding="utf-8"),dbus_interface=bus_interface)
        if len(result) > 0:
            raise ValueError("Error return from automeas(): %s" % (str(result)))
        pass
    pass
