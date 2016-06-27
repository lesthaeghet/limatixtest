from __future__ import print_function

import sys

# This module MUST be imported as a first step before other modules get loaded.
# Then immediately create the handlers, e.g.

# from datacollect2.dc_process_stdiocapture import stdiohandler
# stdouthandler=stdiohandler(sys.stdout,None)
# sys.stdout=stdouthandler

# stderrhandler=stdiohandler(sys.stderr,None)
# sys.stderr=stderrhandler

class stdiohandler(object):
    orig=None  # original handle to forward to 
    encoding=None
    closed=False
    errors=None
    fileno=None
    isatty=None
    mode=None
    name=None
    newlines=None
    seek=None
    softspace=None
    tell=None
    flush=None
    truncate=None
    readlines=None
    readline=None

    def write(self,text):
        self.orig.write(text)
        if self.dest is not None:
            self.dest.write(text)
            pass
        
        pass

    def writeline(self,iterable):
        for entry in iterable:
            self.write(entry)
            pass

        pass
    def set_dest(self,dest):
        self.dest=dest
        pass

    def __init__(self,orig,dest):
        self.orig=orig
        self.dest=dest
        self.encoding=orig.encoding
        self.errors=orig.errors
        self.fileno=orig.fileno
        self.isatty=orig.isatty
        self.mode=orig.mode
        self.name=orig.name
        self.newlines=orig.newlines
        self.seek=orig.seek
        if hasattr(orig,"softspace"): # not present in python3
            self.softspace=orig.softspace
            pass
        
        self.tell=orig.tell
        self.flush=orig.flush
        self.truncate=orig.truncate
        self.readlines=orig.readlines
        self.readline=orig.readline
        pass
    pass
