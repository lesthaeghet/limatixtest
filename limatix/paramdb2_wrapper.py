#!/usr/bin/env python
###############################################################################
## Dataguzzler: A Platform for High Performance Laboratory Data Acquisition  ##
## Copyright (c) 2006-2014, Iowa State University                            ##
##                                                                           ##
## All rights reserved.                                                      ##
##                                                                           ##
## Redistribution and use in source and binary forms, with or without        ##
## modification, are permitted provided that the following conditions are    ##
## met:                                                                      ##
##                                                                           ##
##    * Redistributions of source code must retain the above copyright       ##
##      notice, this list of conditions and the following disclaimer.        ##
##    * Redistributions in binary form must reproduce the above copyright    ##
##      notice, this list of conditions and the following disclaimer in      ##
##      the documentation and/or other materials provided with the           ##
##      distribution.                                                        ##
##    * Neither the name of Iowa State University nor the names of its       ##
##      contributors may be used to endorse or promote products derived      ##
##      from this software without specific prior written permission.        ##
##                                                                           ##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS       ##
## "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT         ##
## LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR     ##
## A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT      ##
## OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,     ##
## SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED  ##
## TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR    ##
## PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF    ##
## LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING      ##
## NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS        ##
## SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.              ##
##                                                                           ##
##                                                                           ##
##    Copyright (C) 2006-2014 Iowa State University                          ##
##                                                                           ##
##    This library is free software; you can redistribute it and/or          ##
##    modify it under the terms of the GNU Lesser General Public             ##
##    License as published by the Free Software Foundation; either           ##
##    version 2.1 of the License, or (at your option) any later version.     ##
##                                                                           ##
##    This library is distributed in the hope that it will be useful,        ##
##    but WITHOUT ANY WARRANTY; without even the implied warranty of         ##
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU      ##
##    Lesser General Public License for more details.                        ##
##                                                                           ##
##    You should have received a copy of the GNU Lesser General Public       ##
##    License along with this library; if not, write to the Free Software    ##
##    Foundation, Inc.,                                                      ##
##    51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA           ##
##                                                                           ##
##    As a special exception, third party data acquisition libraries         ##
##    or hardware drivers may be treated as if they were a major component   ##
##    of the operating system; therefore the special exception in GPLV2,     ##
##    section 3 applies to them.                                             ##
###############################################################################
"""
Dataguzzler: A Platform for High Performance Laboratory Data Acquisition
Copyright (C) 2006-2014 Iowa State University

This module contains funcionality needed to use paramdb inside other Python
scripts.  It will launch a dbus session in a new process and start
responding to requests until it is stopped.  An example use case for this
module is when using Python to call and run MATLAB COMSOL automation
scripts.  Many of these modules depend on dc_param to capture values and
this is not feasable in the context of a Python automation script.  This
wrapper fills that void.

The suggested method to import this module is the following:

>>> import paramdb2_wrapper as pdb2

This module contains a class object to act as a storage container.
"""

import sys
if "gi" in sys.modules or (__name__ == "__main__" and "--gtk3" in sys.argv):  # gtk3
    import gi
    gi.require_version('Gtk','3.0')  # gtk3
    from gi.repository import GObject as gobject
    pass
else : 
    # gtk2
    import gobject
    pass

import subprocess
import cPickle
#import dg_units
#dg_units.units_config('insert_basic_units')
# sys.path.append('/usr/local/dataguzzler/gui2/lib')
# import dg_io
from dc_value import numericunitsvalue as numericunitsv
from dc_value import complexunitsvalue as complexunitsv
from dc_value import stringvalue as stringv
from dc_value import excitationparamsvalue as excitationparamsv
from paramdb2 import autocontroller_specimendb
from paramdb2 import autocontroller_xducerdb
from paramdb2 import autocontroller_xmlfile
from paramdb2 import optionscontroller_xmlfile
import paramdb2 as pdb2
from dc_dbus_paramserver import dc_dbus_paramserver

class _dummy(object):
    pass

class paramdb2_wrapper(object):
    """
    Wrapper Class for Paramdb2

    Initialization of this class will create an empty list that can be
    populated with the addcmd function.  Commands should follow the
    same format as within a typical dcc file.  The parameter database
    is provided in this context as 'paramdb' just as it is within the
    context of dcc files.  M4 includes will not be executed and will
    return in error.

    Call the run function to start the gobject main loop and enable the
    dbus service to respond to requests.  Terminate the loop by calling
    the stop function.

    Usage:
      >>> # Set Up Server
      >>> import paramdb2_wrapper as pdb2
      >>> pdbobj = pdb2.paramdb2_wrapper()
      >>> pdbobj.addcmd("paramdb.addparam('specimen', stringv)")
      >>> pdbobj.addcmd(''' paramdb.addparam("spclength", numericunitsv, 
      	defunits="mm", build=lambda param, 
      	paramdb=paramdb: autocontroller_xmlfile(param, 
      	'/databrowse/specimens/%s.sdb', ['specimen'], 
      	"specimen:geometry/specimen:dimension[@direction='length'][1]/.", 
      	[], namespaces={'specimen':'http://limatix.org/specimen'}),
		non_settable=True) ''')
      >>> pdbobj.run()

      >>> # Test Output - Ran in a Separate Process
      >>> from dc_dbus_paramclient import dc_param, dc_requestvalstr
      >>> dc_requestvalstr('specimen', 'C13-UTCVBT-006A')
      <dc_value.stringvalue at 0x279b310>
      >>> dc_param('spclength').value()
      255.16

    """

    dcclist = None	# DCC Items
    _p = None       # Process Object

    def __init__(self):
        """
        Initialize Wrapper Class

        Arguments:
          None
        """

        # Set Up Parameters
        self._p = None
        self.dcclist = []
        pass

    def addcmd(self, cmd):
    	self.dcclist.append(cmd)

    def run(self):
        """
        Start dbus service loop in subprocess

        Arguments:
          None
        """

        # Make Sure We Aren't Already Running
        if self._p is not None:
            raise Exception("Paramdb Process Already Running")

        # Determine File Location
        thisfile = sys.modules[_dummy.__module__].__file__

        # Start Process - Close File Descriptors As Well To Prevent Possible Issues
        subprocessargs=[sys.executable, thisfile]
        if not "gtk" in sys.modules and not "gobject" in sys.modules:  # gtk3
            subprocessargs.append("--gtk3")
            pass
        
        self._p = subprocess.Popen(subprocessargs, stdin=subprocess.PIPE, stdout=sys.stdout, stderr=sys.stderr, close_fds=True)

        # Pickle Paramdb and Send to Subprocess
        data = cPickle.dumps(self.dcclist).replace("\n", "\\()")
        self._p.stdin.write(data + "\n")
        pass

    def stop(self):
        """
        Stop dbus service loop

        Arguments:
          None
        """

        # Make Sure We Are Actually Running
        if self._p is None:
            raise Exception("Paramdb Process Not Running")

        # Kill Process
        self._p.kill()
        self._p = None
        pass

    pass


if __name__ == "__main__":
    """
    Subprocess Code - DO NOT RUN DIRECTLY
    """

    # Read In Data From Pickle
    data = sys.stdin.readline()
    dcclist = cPickle.loads(data.replace("\\()", "\n"))

    # Create Paramdb
    paramdb = pdb2.paramdb(None)

    # Loop and Add
    for dccitem in dcclist:
    	eval(dccitem)

    # Start Param Server
    paramserver = dc_dbus_paramserver(paramdb, None)
    loop = gobject.MainLoop()
    loop.run()
    pass

