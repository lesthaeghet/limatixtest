
import sys
import datetime as pydatetime
import pytz
import collections
import time

#sys.path.append('/usr/local/datacollect2/lib')

from limatix.dc_value import stringvalue
from limatix.dc_value import hrefvalue
from limatix import xmldoc

gpxcache=None
gpxtimescache=None


def argmin(iterable):
    return min(enumerate(iterable), key=lambda x: x[1])[0]


def run(_xmldoc,_tag,timezone_str):
    global gpxcache   # Not ideal, as it screws up provenance, but it makes a huge performance difference
    global gpxtimescache

    if gpxcache is None:
        gpxdata=collections.OrderedDict()  # dictionary by time of location

        gpxlogels=_xmldoc.xpath("dc:measurement/dc:gpslog")
        for gpxlogel in gpxlogels:
            gpxhref=hrefvalue.fromxml(_xmldoc,gpxlogel)
            gpxpath=gpxhref.getpath()
            gpxdoc=xmldoc.xmldoc.loadfile(gpxpath,nsmap={"gpx": "http://www.topografix.com/GPX/1/1"})
            trkpts=gpxdoc.xpath("gpx:trk/gpx:trkseg/gpx:trkpt")
            #sys.stderr.write("trkpts=%s\n" % (str(trkpts)))
            for trkpt in trkpts:
                timestamp=gpxdoc.xpathsinglecontextstr(trkpt,"gpx:time")
                lat=gpxdoc.getattr(trkpt,"lat") # in decimal degrees
                longitude=gpxdoc.getattr(trkpt,"lon")
                gpxdata[timestamp]=(lat,longitude)
                pass
            pass
        gpxtimes=[ pytz.utc.localize(pydatetime.datetime(*time.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")[:6])) for timestamp in gpxdata.keys() ]
        gpxcache=gpxdata
        gpxtimescache=gpxtimes
        pass
    else:
        gpxdata=gpxcache
        gpxtimes=gpxtimescache
        pass
    
    tzobject=pytz.timezone(timezone_str)

    datetime_str=_xmldoc.getattr(_tag,"datetime")
    dtobj=tzobject.localize(pydatetime.datetime(*time.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S")[:6]))  # create timezone-aware object

    timediffs= [ abs(dtobj-gpxtime) for gpxtime in gpxtimes ]
    minidx=argmin(timediffs)
    sys.stderr.write("min(timediffs)=%s\n" % (str((timediffs[minidx]))))
    
    if timediffs[minidx] < pydatetime.timedelta(seconds=120):
        ret={ "gpscoords": str(gpxdata[list(gpxdata.keys())[minidx]]) }
        pass
    else:
        ret={}
        pass
    return ret
  
