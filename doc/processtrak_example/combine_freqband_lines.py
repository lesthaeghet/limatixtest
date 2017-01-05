# Merge the <spectrumlog> entries, each of which only has a partial spectrum
# into a <mergedspectrumlog> with the full spectrum
import sys
import ast

from limatix import processtrak_procstep

def run(_xmldoc,_tag,frequencyerrorthreshold_numericunits):

    frequencyerrorthreshold_float=frequencyerrorthreshold_numericunits.value('Hz')
    datetimestr=_xmldoc.getattr(_tag,"datetime")

    # print("datetime=%s\n" % (datetimestr))
    spectrumtags=[_tag]
    # Find following siblings with the same datetime 
    spectrumtags.extend(_xmldoc.xpathcontext(_tag,"following-sibling::spectrumlog[string(@datetime)='%s']" % (datetimestr)))

    # print("\ndatetime=%s; len(spectrumtags)=%d\n" % (datetimestr,len(spectrumtags)))

    hznext=_xmldoc.xpathsinglecontextfloat(_tag,"hzlow")
    combined_hzlow=hznext
    combined_step=_xmldoc.xpathsinglecontextfloat(_tag,"hzstep")
    dbs=[]
    for spectrumtag in spectrumtags:
        hzlow=_xmldoc.xpathsinglecontextfloat(spectrumtag,"hzlow")
        if abs(hzlow-hznext) > frequencyerrorthreshold_float:
            raise ValueError("Frequency mismatch: hzlow=%f, hznext=%f, threshold=%f" % (hzlow,hznext,frequencyerrorthreshold_float))
        hzhigh=_xmldoc.xpathsinglecontextfloat(spectrumtag,"hzhigh")
        hzstep=_xmldoc.xpathsinglecontextfloat(spectrumtag,"hzstep")
        assert(hzstep==combined_step)
        combined_hzhigh=hzhigh

        # extract the "dBs' tag for this line
        dblist=ast.literal_eval(_xmldoc.gettext(_xmldoc.xpathsinglecontext(spectrumtag,"dBs")))

        assert(round((hzhigh-hzlow)/hzstep)==len(dblist)-1) # make sure we got the right number of data elements

        # append contents to dbs list, dropping last element because that will be redundant with next group (but inconsistent?)
        dbs.extend(dblist[:-1])

        # step to net frequency
        hznext+=combined_step*(len(dblist)-1)
        pass

    #parenttag=_xmldoc.getparent(_tag)

    ## Remove any preexisting mergedspectrumlog
    #oldmerged=_xmldoc.xpathcontext(parenttag,"mergedspectrumlog[string(datetime)='%s']" % (datetimestr))
    #for oldelement in oldmerged:
    #    _xmldoc.removeelement(oldelement)
    #    pass


    # print("combinednum=%d" % (len(dbs)))
    
    # Create mergedspectrumlog
    
    #merged=_xmldoc.addelement(parenttag,"mergedspectrumlog")
    #_xmldoc.addsimpleelement(merged,"datetime",(datetimestr,))
    #_xmldoc.addsimpleelement(merged,"hzlow",(combined_hzlow,))
    #_xmldoc.addsimpleelement(merged,"hzhigh",(combined_hzhigh,))
    #_xmldoc.addsimpleelement(merged,"hzstep",(combined_step,))
    #_xmldoc.addsimpleelement(merged,"dBs",(str(dbs),))
    mergedresultdict={ "hzlow": combined_hzlow,
                       "hzhigh": combined_hzhigh,
                       "hzstep": combined_step,
                       "dBs": str(dbs) }
    
    merged=processtrak_procstep.resultelementfromdict(_xmldoc,mergedresultdict)
    
    return {"mergedspectrumlog": ({"datetime": datetimestr},merged) }
