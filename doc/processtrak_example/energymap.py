import numpy as np
import scipy
import scipy.misc
import sys

import PIL
import PIL.ImageDraw
import PIL.ImageFont

#from geopy.distance import great_circle
import urllib
import os
import os.path
import posixpath
import ast

from limatix.dc_value import hrefvalue

def run(_xmldoc,_tag,_dest_href,frequency_float,leftlong_float,rightlong_float,botlat_float,toplat_float,xpixels_int,ypixels_int,windowwidth_meters_float):
    
    latbase=np.arange(ypixels_int,dtype='d')*(botlat_float-toplat_float)/ypixels_int + toplat_float


    longbase=np.arange(xpixels_int,dtype='d')*(rightlong_float-leftlong_float)/xpixels_int + leftlong_float
    
    # sys.stderr.write("latbase=%s\n" % (str(latbase)))
    # sys.stderr.write("longbase=%s\n" % (str(longbase)))


    hzlow=_xmldoc.xpathsinglefloat("(dc:measurement/spectrumlog/mergedspectrumlog)[1]/hzlow")
    hzhigh=_xmldoc.xpathsinglefloat("(dc:measurement/spectrumlog/mergedspectrumlog)[1]/hzhigh")
    hzstep=_xmldoc.xpathsinglefloat("(dc:measurement/spectrumlog/mergedspectrumlog)[1]/hzstep")

    freqidx=int(round((frequency_float-hzlow)/hzstep))
    
    
    logentries=_xmldoc.xpath("dc:measurement/spectrumlog/mergedspectrumlog[gpscoords]") # extract all log entries with gps coordinates

    # filter log entries, making sure we have the right number of frequency indices in them
    numfreqs=round((hzhigh-hzlow)/hzstep)

    #print numfreqs
    #print 
    
    uselogentries=[ logentries[entrynum]  for entrynum in range(len(logentries)) if len(_xmldoc.xpathsinglecontextstr(logentries[entrynum],"dBs")[1:-1].split(','))==numfreqs ]

    # print("Energymap: Checking number of frequency lines filtered %d entries down to %d" % (len(logentries),len(uselogentries)))
    
    
    dBss=_xmldoc.xpathcontextnumpystr(uselogentries,"dBs")

    SignalAmplitudes = np.array([ dBs[1:-1].split(',')[freqidx] for dBs in dBss ],dtype='d')

    gpscoord_strs=_xmldoc.xpathcontextnumpystr(uselogentries,"gpscoords")

    # create list of gps coordinates of log entries
    gpscoords=np.array([ast.literal_eval(gpscoord_str) for gpscoord_str in gpscoord_strs],dtype='d')

    # distmtx is distance in meters
    numlong=longbase.shape[0]
    numlat=latbase.shape[0]
    numgps=gpscoords.shape[0]
    #distmtx=np.zeros((numlong,numlat,numgps),dtype='d')
    Rearth=6378e3
    meters_per_degree_latitude=2.0*np.pi*Rearth/360.0
    radius_at_latitude=Rearth*np.cos(latbase[0]*np.pi/180.0)
    meters_per_degree_longitude=2.0*np.pi*radius_at_latitude/360.0

    (longmtx,latmtx)=np.meshgrid(longbase,latbase,indexing='ij')
    #sys.stderr.write("\n\ngpscoords shape"+str(gpscoords.shape)+"\n\n")
    longdistmtx=longmtx.reshape(numlong,numlat,1)-gpscoords[:,1].reshape(1,1,numgps)
    latdistmtx=latmtx.reshape(numlong,numlat,1)-gpscoords[:,0].reshape(1,1,numgps)
    distmtx=np.sqrt((longdistmtx*meters_per_degree_longitude)**2.0 +  (latdistmtx*meters_per_degree_latitude)**2.0)
    
    #for latcnt in range(latbase.shape[0]):
    #    sys.stderr.write("latcnt=%d/%d\n" % (latcnt,latbase.shape[0]))
    #    for longcnt in range(longbase.shape[0]):
    #        
    #        distmtx[latcnt,longcnt,:] = [ great_circle((latbase[latcnt],longbase[longcnt]),gpscoord).meters for gpscoord in gpscoords ]
    #        
    #        pass
    #    pass
    # Weight accourding to Gaussian basis funtion
    #Weights=(1.0/(windowwidth_meters_float*np.sqrt(2*np.pi)))*np.exp(-distmtx**2.0/(2.0*windowwidth_meters_float**2.0))
    # Weight accourding to Exponential basis funtion
    Weights=(1.0/(windowwidth_meters_float*np.sqrt(2*np.pi)))*np.exp(-np.abs(distmtx)/(2.0*windowwidth_meters_float))
    # Weights axis: 0: latcnt
    #               1: longcnt
    #               2: logentry


    #sys.stderr.write("Weights=%s\n" % (str(Weights)))
    #sys.stderr.write("distmtx=%s\n" % (str(distmtx)))
    #sys.stderr.write("Shortest distance=%f meters\n" % (np.min(distmtx)))
    # sum Weight*signal amplitudes... and divide by total weight for each pixel
    amplmtx=np.tensordot(Weights,SignalAmplitudes,(2,0))/np.sum(Weights,2)


    #outpng="%s_9.0f%fl%fr%fb%ft%f.png" % (os.path.splitext(os.path.split(_xmldoc.filehref.getpath())[1])[0],hzlow+hzstep*freqidx,leftlong.value(),rightlong.value(),botlat.value(),toplat.value())

    outpng="%s_9.0f%fl%fr%fb%ft%f.png" % (posixpath.splitext(_xmldoc.filehref.get_bare_unquoted_filename())[0],hzlow+hzstep*freqidx,leftlong_float,rightlong_float,botlat_float,toplat_float)

    
    #outpng_path=os.path.join(os.path.split(rflogpath)[0],outpng)
    outpng_href=hrefvalue(outpng,contexthref=_dest_href)
    
    #outpng_href=hrefvalue(urllib.pathname2url(outpng_path),contextdir=_xmldoc.getcontextdir())
    
    outkml="%s_9.0f%fl%fr%fb%ft%f.kml" % (os.path.splitext(os.path.split(_xmldoc.filehref.getpath())[1])[0],hzlow+hzstep*freqidx,leftlong_float,rightlong_float,botlat_float,toplat_float)
    outkml_href=hrefvalue(outkml,_dest_href)  #os.path.join(os.path.split(rflogpath)[0],outkml)
    
    PILimg=scipy.misc.toimage(amplmtx.transpose(),cmin=amplmtx.min(),cmax=amplmtx.max())

    infotext="min=%3.0f dB; max=%3.0f dB f=%.1f MHz" % (amplmtx.min(),amplmtx.max(),frequency_float/1.e6)
    draw=PIL.ImageDraw.Draw(PILimg)
    draw.text((0,0),infotext,255 ,font=PIL.ImageFont.load_default()) #(255,255,255)
    draw.text((0,18),infotext,0,font=PIL.ImageFont.load_default())
    
    PILimg.save(outpng_href.getpath())

    # Generate kml file
    rflogs=_xmldoc.xpath("rflog") # extract all rflog entries
    kmlgpscoordinates=[] # list of coordinate strings
    for rflog in rflogs:
        rflogentries=_xmldoc.xpathcontext(rflog,"mergedspectrumlog[gpscoords]") # extract all log entries with gps coordinates
        rflogentry_gpscoord_strs=_xmldoc.xpathcontextnumpystr(rflogentries,"gpscoords")
            
        # create list of gps coordinates of log entries
        rflogentry_gpscoords=np.array([ast.literal_eval(gpscoord_str) for gpscoord_str in rflogentry_gpscoord_strs],dtype='d')
        
        kmlgpscoordinates.append("\n".join(["%.12f,%.12f,0.0" % (gpscoord[1],gpscoord[0]) for gpscoord in rflogentry_gpscoords]))
        pass

    kmlgpstracks=""
    for kmlgpscoordstr in kmlgpscoordinates:
        kmlgpstracks+=r"""
    <Placemark>
      <name>GPS Track</name>
      <description>GPS Track</description>
      <styleUrl>#trackstyle</styleUrl>
      <LineString>
        <altitudeMode>clampToGround</altitudeMode>
        <coordinates>%s
        </coordinates>
      </LineString>
    </Placemark>
""" % (kmlgpscoordstr)
        pass
        #kmlgpscoordinates="\n".join(["%.12f,%.12f,0.0" % (gpscoord[1],gpscoord[0]) for gpscoord in gpscoords])  # kmls take longitude, latitude, altitude
    outkmfh=open(outkml_href.getpath(),"w")
    outkmfh.write(r"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Folder>
    <name>%s</name>
    <description>%s</description>
    <Style id="trackstyle">
      <LineStyle>
        <color>ff0000ff</color>
        <width>3</width>
      </LineStyle>
    </Style>
    <GroundOverlay>
      <name>%f Hz</name>
      <description>%f Hz</description>
      <color>7f00ff00</color> <!-- ABGR: alpha 7f blue 00 green ff red 00 -->
      <Icon>
        <href>%s</href>
      </Icon>
      <LatLonBox>
        <north>%.15f</north>
        <south>%.15f</south>
        <east>%.15f</east>
        <west>%.15f</west>
      </LatLonBox>
    </GroundOverlay>
    %s
  </Folder>
    </kml>""" % (infotext,infotext,hzlow+hzstep*freqidx,hzlow+hzstep*freqidx,
                 outpng_href.attempt_relative_url(outkml_href),toplat_float,botlat_float,rightlong_float,leftlong_float,kmlgpstracks))
    outkmfh.close()
    
    metadata={"frequency": str(hzlow+hzstep*freqidx),
                                  "leftlong": str(leftlong_float),
                                  "rightlong": str(rightlong_float),
                                  "botlat": str(botlat_float),
                                  "toplat": str(toplat_float) }
    
    return { "amplitudematrix": (metadata,repr(amplmtx)),
             "imagemap": (metadata,outpng_href),
             "kmlmap": (metadata,outkml_href) }

