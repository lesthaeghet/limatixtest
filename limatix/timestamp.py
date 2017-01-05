import datetime
import re
import time

# push off pytz import until it is needed, because it screws up pychecker
#from pytz import reference

# Cribbed from dataguzzler-lib

# FixedOffset and UTC classes from Python Library Reference

ZERO = datetime.timedelta(0)
HOUR = datetime.timedelta(hours=1)
class UTC(datetime.tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO


class FixedOffset(datetime.tzinfo):
    """Fixed offset in minutes east from UTC."""

    def __init__(self, offset, name):
        self.__offset = datetime.timedelta(minutes = offset)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return ZERO

def getlocaltz() :
    from pytz import reference
    return reference.LocalTimezone()

def now():
    dtobj=datetime.datetime.now(getlocaltz())
    return dtobj

def roundtosecond(timestamp):
    year=timestamp.year
    month=timestamp.month
    day=timestamp.day
    hour=timestamp.hour
    minute=timestamp.minute
    second=timestamp.second
    microsecond=timestamp.microsecond
    tzinfo=timestamp.tzinfo

    microsecond=0
    retvalrounddown=datetime.datetime(year,month,day,hour,minute,second,microsecond,tzinfo)

    if (microsecond >= 500000):
        # round up
        return retvalrounddown+datetime.timedelta(seconds=1)
    else: 
        # round down
        return retvalrounddown
    pass

    

def readtimestamp(str):
    # returns datetime object

    matchobj=re.match(r"""(\d+)-(\d+)-(\d+)T(\d+):(\d+):(\d+)([.,](\d+))?(([+-])(\d\d):?(\d\d))""",str);
    # print str
    # print matchobj.groups()
    tzoffs_hours=int(matchobj.group(11))
    tzoffs_mins=int(matchobj.group(12))
    if matchobj.group(9)=="+":
        tzoffs=tzoffs_hours*60+tzoffs_mins
        pass
    else :
        tzoffs=-tzoffs_hours*60-tzoffs_mins
        pass
    tzinfo=FixedOffset(tzoffs,matchobj.group(10))
    if matchobj.group(8) is not None and len(matchobj.group(8)) > 0:
        micros=int(round(float("."+matchobj.group(8))*1e6))
        pass
    else :
        micros=0
        pass
    return datetime.datetime(int(matchobj.group(1)),int(matchobj.group(2)),int(matchobj.group(3)),int(matchobj.group(4)),int(matchobj.group(5)),int(matchobj.group(6)),micros,tzinfo)
    pass
