

def check_status(xlpfile):

    xlp=xmldoc.xmldoc.loadfile(xlpfile,use_locking=True)
    xlp.disable_locking()  # locking is just to prevent messing with the file during
    
