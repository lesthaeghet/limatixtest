#! /usr/bin/env python
import sys
import os
import os.path


class dummy(object):
    pass

# trace symbolic link to find installed directory
thisfile=sys.modules[dummy.__module__].__file__
if os.path.islink(thisfile):
    installedfile=os.readlink(thisfile)
    if not os.path.isabs(installedfile):
        installedfile=os.path.join(os.path.dirname(thisfile),installedfile)
        pass
    pass
else:
    installedfile=thisfile
    pass

installeddir=os.path.dirname(installedfile)

if os.path.exists(os.path.join(installeddir,"../lib/checklist.py")):
    installeddir=os.path.join(installeddir,"../")
    pass
elif os.path.exists(os.path.join(installeddir,"../gui2/lib/checklist.py")):
    installeddir=os.path.join(installeddir,"../gui2")
    pass

def main():
    print(installeddir)
    pass
