
import sys
import csv

from lxml import etree
from limatix.dc_value import hrefvalue
from limatix import processtrak_procstep


def run(_xmldoc,_tag,dc_rflog):
    
    input_href=hrefvalue.fromxml(_xmldoc,dc_rflog)
    inputfile=input_href.getpath() # name of input file
    
    infh=open(inputfile,"r")
    csvreader=csv.reader(infh,skipinitialspace=True)

    # # remove any old spectrum log entries in this rflog tag
    # oldspectrumlogentries=_xmldoc.xpathcontext(_tag,"spectrumlog")
    # for element in oldspectrumlogentries:
    #     _xmldoc.removeelement(element)
    #     pass

    # import limatix.provenance
    # print("extract_rflog_entries: print_current_used()")
    # limatix.provenance.print_current_used()

    resultlist=[]
    rowcnt=0
    for row in csvreader:
        date=row[0]
        time=row[1]

        datetimestr="%sT%s" % (date,time)

        spectrumlogdict={ "hzlow": row[2],
                          "hzhigh": row[3],
                          "hzstep": row[4],
                          "dBs": str([ float(numstring) for numstring in row[6:]]) }
            
        spectrumlog=processtrak_procstep.resultelementfromdict(_xmldoc,spectrumlogdict)

        resultlist.append(("spectrumlog",({"datetime": datetimestr,"index": str(rowcnt)},spectrumlog)))

        rowcnt+=1
        
        # spectrumlog=_xmldoc.addelement(_tag,"spectrumlog")
        # datetime=_xmldoc.addelement(spectrumlog,"datetime")
        # _xmldoc.settext(datetime,datetimestr)


        #_xmldoc.addsimpleelement(spectrumlog,"hzlow",(row[2],))
        #_xmldoc.addsimpleelement(spectrumlog,"hzhigh",(row[3],))
        #_xmldoc.addsimpleelement(spectrumlog,"hzstep",(row[4],))
        #_xmldoc.addsimpleelement(spectrumlog,"dBs",(str([ float(numstring) for numstring in row[6:]]),))
        pass

    # print("extract_rflog_entries_end: print_current_used()")
    # datacollect2.dc_provenance.print_current_used()
    return resultlist
    

