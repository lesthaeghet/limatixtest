import os
import os.path
import sys

import dg_timestamp

from lxml import etree 
import xmldoc
import paramdb2 as pdb



class explog(xmldoc.xmldoc):
    maintagname=None
    summarytagname=None
    paramdb=None
    paramdb_ext=None # etree_parmdb_ext extension object
    iohandlers=None

    # summaryparams must be registered with the document through creation using xmldoc.synced as the controller

    def __init__(self,filename,iohandlers,paramdb,maintagname="dc:experiment",summarytagname="dc:summary",oldfile=False,use_locking=False,debug=False): #autoflush=False,autoresync=False):  # if oldfile is False, create a new file, overwriting any preexisting file of the same name
        self.iohandlers=iohandlers
        self.paramdb=paramdb
        self.paramdb_ext=pdb.etree_paramdb_ext(paramdb)
        self.maintagname=maintagname
        self.summarytagname=summarytagname

        if oldfile:
            xmldoc.xmldoc.__init__(self,filename,maintagname=None,use_locking=use_locking,debug=debug) #autoflush=autoflush,autoresync=autoresync) # maintagname=None says "don't create a new file!" 
            # summaryel=self.getsingleelement("/%s/%s" % (self.maintagname,self.summarytagname)) # get the summary element
            pass
        else :
            xmldoc.xmldoc.__init__(self,filename,maintagname,use_locking=use_locking) #autoflush=autoflush,autoresync=autoresync)
            self.addelement(self.doc.getroot(),summarytagname)
            pass

        self.extensions.append(self.paramdb_ext.extensions)

        pass

    

    def set_iohandlers(self,iohandlers):
        self.iohandlers=iohandlers
        pass
    
    #def writesummaryparams(self) :
        # summary params should already be written to xml through auto-updates from paramdb
        #if self.filename is not None: 
        #    self.flush() # write to disk
        #    pass
    #    pass

    #def get_measnum(self):
    #
    #    measnum=0
    #    measnum_ns=self.xpath("/dc:experiment/dc:measurement[last()]/dc:measnum")
    #      if len(measnum_ns) > 0:
    #        measnum=int(measnum_ns[0].text)+1
    #        pass
    #    return measnum        



    def recordmeasurement(self,measnum,clinfo=None,cltitle=None,extrataglist=None):

        self.shouldbeunlocked()

        self.lock_rw()
        # self.resync()
        try : 

            root=self.getroot()
            meastag=self.addelement(root,"dc:measurement")

        
            # meastag=etree.Element("{http://thermal.cnde.iastate.edu/datacollect}measurement")
            paramlist=self.paramdb.keys()
            
            # write out measnum element
            measnumel=self.addsimpleelement(meastag,"dc:measnum",(measnum,))
            
            # measnumel=etree.Element("{http://thermal.cnde.iastate.edu/datacollect}measnum")
            # measnumel.text=str(self.get_measnum())
            # meastag.append(measnumel)
            
            # write out measrecordtimestamp element
            meastimestampel=self.addsimpleelement(meastag,"dc:recordmeastimestamp",(dg_timestamp.roundtosecond(dg_timestamp.now()).isoformat(),))        
            # meastimestampel=etree.Element("{http://thermal.cnde.iastate.edu/datacollect}recordmeastimestamp")
            # meastimestampel.text=dg_timestamp.roundtosecond(dg_timestamp.now()).isoformat()
            # meastag.append(meastimestampel)

            # write out clinfo and cltitle
            if clinfo is not None:
                clinfotag=self.addsimpleelement(meastag,"chx:clinfo",(clinfo,))

                # clinfotag=etree.Element("{http://thermal.cnde.iastate.edu/checklist}clinfo")
                # clinfotag.text=clinfo
                # meastag.append(clinfotag)
                
                pass

            if cltitle is not None:
                cltitletag=self.addsimpleelement(meastag,"chx:cltitle",(cltitle,))
                    
                # cltitletag=etree.Element("{http://thermal.cnde.iastate.edu/checklist}cltitle")
                # cltitletag.text=cltitle
                # meastag.append(cltitletag)

                pass
        
            for paramname in paramlist:
                if paramname in self.paramdb:
                    if not self.paramdb[paramname].hide_from_meas:

                        paramtag=self.addelement(meastag,"dc:"+paramname)
                        self.paramdb[paramname].dcvalue.xmlrepr(self,paramtag,defunits=self.paramdb[paramname].defunits) # xml_attribute=self.paramdb[paramname].xml_attribute)
                    
                        # paramtag=etree.Element("{http://thermal.cnde.iastate.edu/datacollect}"+paramname)                
                        # self.paramdb[paramname].dcvalue.xmlrepr(self,paramtag,defunits=self.paramdb[paramname].defunits)
                        # meastag.append(paramtag)
                        pass
                    pass
                
                pass
        
            if extrataglist is not None:
                for tag in extrataglist:
                    meastag.append(tag)
                    pass
                pass
            
            # self.doc.getroot().append(meastag)
            # self.flush()

            # sys.stderr.write("Attempting to flush out with measnum=%s\n" % (measnumel.text))
            pass
        except:
            raise
        finally:
            self.unlock_rw()
            pass
        # sys.stderr.write("self.doc=%s\n" % (str(self.doc)))

        self.shouldbeunlocked()

        # reset any parameters that must be cleared with measurement record

        for paramname in paramlist:
            if paramname in self.paramdb:
                if self.paramdb[paramname].reset_with_meas_record:
                    self.paramdb[paramname].requestvalstr_sync(None)
                    pass
                pass
            pass
        
        ## set measurement status
        # self.paramdb["measstatus"].requestvalstr("Appended %d bytes" % (len(etree.tostring(measnumel,pretty_print=True))))
        
        pass
    
    pass
