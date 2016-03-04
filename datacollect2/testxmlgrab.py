import os
import os.path
import sys
import dc_xmlgrab2


fname='testallspecimens_somecleaned.xlg'
fpath='/tmp'

filename=os.path.join(fpath,fname)
meastags=dc_xmlgrab2.dc_xmlgrab(filename,"/dc:experiment/dc:measurement")

# for some reason the hae is NaN for a lot of the tags, and for those the units are m^2/second instead of m^2/s ???
hae=dc_xmlgrab2.dc_xml2numpy(meastags,"dc:hae")
haeunits=dc_xmlgrab2.dc_xml2numpystr(meastags,"dc:hae/@dcv:units")

print hae
print haeunits
