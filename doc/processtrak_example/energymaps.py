import numpy as np
import collections
import energymap
from limatix.dc_value import numericunitsvalue
from limatix import processtrak_procstep

# iterate energymap over a range of frequencies
def run(_xmldoc,_tag,_dest_href,freqstart_float,freqstep_float,freqend_float,leftlong_float,rightlong_float,botlat_float,toplat_float,xpixels_int,ypixels_int,windowwidth_meters_float):

    retlist=[]
    print("")  # just get newline
    
    for freq in np.arange(freqstart_float,freqend_float,freqstep_float):
        print("freq=%f" % (freq))
        energymapresultdict=energymap.run(_xmldoc,_tag,_dest_href,freq,leftlong_float,rightlong_float,botlat_float,toplat_float,xpixels_int,ypixels_int,windowwidth_meters_float)
        
        retlist.append(("freq",({ "frequency": str(freq)},
                                processtrak_procstep.resultelementfromdict(_xmldoc,energymapresultdict))))
              
        pass

    return retlist

