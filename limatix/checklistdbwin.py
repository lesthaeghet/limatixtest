import sys
import os
import copy
import collections

try: 
    Counter=collections.Counter
    pass
except AttributeError:
    # python 2.6 and earlier don't have collections.Counter. 
    # Use local version py26counter.py instead
    import py26counter
    Counter=py26counter.Counter
    pass



import numpy as np

if "gi" in sys.modules:  # gtk3
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk as gtk
    from gi.repository import GObject as gobject
    pass
else : 
    # gtk2
    import gtk
    import gobject
    pass
    
from . import dc_value
from . import paramdb2 as pdb
from . import checklistdb


__pychecker__="no-argsused no-import"



###***!!! Should modify to request notifications from checklistdb!!!***
###*** Should modify to be able to show only certain checklists (e.g. open ones) http://faq.pygtk.org/index.py?req=show&file=faq13.048.htp


def attemptuniqify(entry,instructions):
    # apply abbreviation instructions to entry
    #   instructions are a list of tuples. 
    #    each tuple is (num of chars, True to copy chars or False to replace them with "...")

    entrypos=0
    instrpos=0
    entryresolved=""
    while entrypos < len(entry):
        
        if instrpos >= len(instructions):
            entryresolved+=entry[entrypos:]
            entrypos+=len(entry)-entrypos
            continue

        #sys.stderr.write("er=%s instr=%s\n" % (entryresolved,str(instructions[instrpos])))

        if instructions[instrpos][1] or instructions[instrpos][0] < 4:  # copy chars if we are told to or if the number to hide is less than 4
            entryresolved+=entry[entrypos:(entrypos+instructions[instrpos][0])]
            pass
        else:
            entryresolved+="..."
            pass
        entrypos+=instructions[instrpos][0]
        instrpos+=1

        pass
    #sys.stderr.write("entryresolved=%s\n\n" % (entryresolved))



    return entryresolved

def resolveuniqifyconflict(conflictlist):
    # idxaccumulator=collections.Counter()
    
    maxlen=0
    for entry in conflictlist:
        if len(entry) > maxlen:
            maxlen=len(entry)
            pass
        pass

    nparray=np.zeros((len(conflictlist),maxlen),dtype='U') # create character-by-character array
    for cnt in range(len(conflictlist)):
        nparray[cnt,:len(conflictlist[cnt])]=tuple(conflictlist[cnt])
        pass

    
    numunique=np.zeros(maxlen,np.uint32)
    for col in range(maxlen):
        numunique[col]=len(np.unique(nparray[:,col]))
        pass
    # translate into string where 's' means one single value for entire column, 'm' means multiple values
    uniquemap=''.join([ 's' if entry==1 else 'm' for entry in numunique])
    uniquesplit=uniquemap.split('m') 
    
    instructions=[]  # each instructions entry is tuple: (numchars,True) to copy the characters, (numchars,False) to replace them by "..."
    for cnt in range(len(uniquesplit)):
        entry=uniquesplit[cnt]
        if len(entry) > 3:
            instructions.append((len(entry),False))
        elif len(entry) > 0 : 
            instructions.append((len(entry),True))
            pass
        if cnt != len(uniquesplit)-1:
            instructions.append((1,True)) # copy the multiple-valued character (separator from the split)
            pass
        pass
    
    # join duplicate instructions
    pos=0
    while pos < len(instructions)-1:
        if instructions[pos][1] and instructions[pos+1][1]:
            instructions[pos]=(instructions[pos][0]+instructions[pos+1][0],True)
            del instructions[pos+1]
            pass
        else: 
            pos+=1
            pass
        pass

    resolvedlist=[]
    for entry in conflictlist: 
        entryresolved=attemptuniqify(entry,instructions)
        resolvedlist.append(entryresolved)
        pass
    return (resolvedlist,instructions)
    


def uniqify(listofstrings):
    # given a list of strings, insert ellipsis as possible to keep different strings different 
    
    # get unique strings
    stringset=set(listofstrings)
    

    # Create a reverse mapping of abbreviations to strings
    reversemap={}
    for entry in stringset:
        if len(entry) < 7: 
            reversemap[entry]=entry
            pass
        else: 
            abbreviated=entry[0:3]+"..."
            if abbreviated in reversemap:
                if isinstance(reversemap[abbreviated],tuple):
                    # if it's a tuple then it points at our previous attempts to resolve
                    (conflictlist,resolvedlist,instructions)=reversemap[abbreviated]
                    
                    conflictlist.append(entry)

                    #import pdb as pythondb
                    #try: 
                        # re-resolve
                    entryresolved=attemptuniqify(entry,instructions)
                    #except: 
                    #    pythondb.post_mortem()

                    if entryresolved in reversemap:
                        # previous method failed
                        # remove current resolution
                        for cnt in range(len(resolvedlist)):
                            del reversemap[resolvedlist[cnt]]
                            pass
                        # develop new resolution
                        (resolvedlist,instructions)=resolveuniqifyconflict(conflictlist)

                        # apply new resolution
                        for cnt in range(len(conflictlist)):
                            reversemap[resolvedlist[cnt]]=conflictlist[cnt]
                            pass
                        reversemap[abbreviated]=(conflictlist,resolvedlist,instructions)
                        pass
                    else: 
                        resolvedlist.append(entryresolved)
                        reversemap[entryresolved]=entry
                        pass

                    pass
                else : 
                    conflictlist=[entry,reversemap[abbreviated]]
                    (resolvedlist,instructions)=resolveuniqifyconflict(conflictlist)
                    reversemap[abbreviated]=(conflictlist,resolvedlist,instructions)
                    # apply
                    for cnt in range(len(conflictlist)):
                        reversemap[resolvedlist[cnt]]=conflictlist[cnt]
                        pass

                    pass
                pass
            else :
                # this prefix is not present... insert it 
                reversemap[abbreviated]=entry
                pass
            pass
        pass


    # Remove record of previous resolve attempts
    for abbreviated in reversemap.keys():
        if isinstance(reversemap[abbreviated],tuple):
            del reversemap[abbreviated]
            pass
        pass

    
    #  Create forward mapping
    forwardmap = dict((reversemap[abbrev],abbrev) for abbrev in reversemap)

    return [forwardmap[s] for s in listofstrings]


# doabbrev is no longer used
def doabbrev(listofobjs,objattr,objabbrevattr,separator="_"): 
    # go through listofobjs and place abbreviations for attribute objattr in attribute objabrrevattr
    
    # split according to underscores
    # find maximum length

    listofstrings=[ getattr(obj,objattr) if getattr(obj,objattr) is not None else "None" for obj in listofobjs ] 
    #import pdb as pythondb
    #try:
    splitstrings=[ s.split(separator) for s in listofstrings ]
    #except: 
    #    pythondb.post_mortem()

    splitabbrevstrings=copy.copy(splitstrings)
    # Create abbreviated strings for each substring
    maxcols=0
    for cnt in range(len(splitstrings)):
        if len(splitstrings[cnt]) > maxcols:
            maxcols=len(splitstrings[cnt])
            pass
        pass
        

    for cnt in range(maxcols):
        fulllist=[ line[cnt] if cnt < len(line) else None for line in splitabbrevstrings ]
        fulllistshort=[ fulllistentry for fulllistentry in fulllist if fulllistentry is not None]
        abbrevlistshort=uniqify(fulllistshort)
        
        shortcnt=0
        abbrevlist=[]
        for longcnt in range(len(fulllist)):
            if fulllist[longcnt] is None:
                abbrevlist.append(None)
                pass
            else:
                abbrevlist.append(abbrevlistshort[shortcnt])
                shortcnt+=1
                pass
            pass
        assert(shortcnt==len(abbrevlistshort))

        for cnt2 in range(len(splitstrings)):
            if abbrevlist[cnt2] is not None:
                splitabbrevstrings[cnt2][cnt]=abbrevlist[cnt2]
                pass
            pass
        pass


    

    common=[]
    mergecount=1

    while mergecount > 0:
        mergecount=0
    
        # find most common combinations of words
        accumulator=Counter()
        for entry in splitstrings: 
            for pos in range(len(entry)-1):
                accumulator[separator.join(entry[pos:(pos+2)])]+=1
                pass
            
        mc=accumulator.most_common()
        for cnt in range(len(mc)):
            (num,strng)=mc[cnt]
            if num < len(listofstrings)/10:  # we don't try to join things repeated less than 10% of the time
                break

            # merge this string
            for cnt2 in range(len(splitstrings)):
                entry=splitstrings[cnt2]
                abbreventry=splitabbrevstrings[cnt2]
                for pos in range(len(abbreventry)-1):
                    if strng==separator.join(entry[pos:(pos+2)]):
                        mergecount+=1
                        common.append(strng)

                        entry[pos]=strng
                        del entry[pos+1]

                        # merge abbreviated entry for these strings too
                        abbreventry[pos]=strng
                        del abbreventry[pos+1]


                        break
                    pass
                pass
            pass

        pass

    # Uniqify common substrings
    commonuniqueabbrev=uniqify(common)

    # make quick lookup for common substrings
    commonabbrevdict=dict( (common[cnt],commonuniqueabbrev[cnt]) for cnt in range(len(common)))

    # search out these common substrings and replace them
    for line in splitabbrevstrings:
        for col in range(len(line)):
            if line[col] in commonabbrevdict:
                line[col]=commonabbrevdict[line[col]]
                pass
            pass
        pass

    # Merge everything back together and save in attribute
    
    for cnt in range(len(splitabbrevstrings)):
        setattr(listofobjs[cnt],objabbrevattr,separator.join(splitabbrevstrings[cnt]))
        pass

    return 

def timestamp_abbreviate(isotimestamp):
    (date,time)=isotimestamp.split("T")
    (year,month,day)=date.split("-")
    timesplit=time.split(":")
    hour=timesplit[0]
    minute=timesplit[1]
    return "%s-%sT%s:%s" % (month,day,hour,minute)

class checklistdbwin(gtk.Window):
    contexthref=None
    paramdb=None  
    clparamname=None
    clparamname2=None
    popupcallback=None
    popupcallbackargs=None
    
    allchecklists=None
    allplans=None
    liststorerows=None # count of rows in the liststore
    liststore=None  # the gtk.ListStore that mirrors the paramdb database
    treeview=None  # TreeView that displays the ListStore
    checklists=None # list of class checklistdb.checklistentry

    checklistsbyabsurl=None # Dictionary of checklists, indexed by entry.filehref.absurl()

    scrolled=None # gtk.ScrolledWindow object
    viewport=None # vtk.Viewport object

    # Must match titles and types, in __init__ (below), and bottom of liststoreupdate() (below)... also be sure to update query_tooltip() and see also doabbrev() calls. 
    COLUMN_ORIGHREF=0
    #COLUMN_CLINFO=1
    #COLUMN_CLTYPE=2
    COLUMN_FILENAME=1
    COLUMN_MEASNUM=2
    COLUMN_STARTTIMESTAMP=3
    COLUMN_IS_OPEN=4
    COLUMN_ALLCHECKED=5
    COLUMN_IS_DONE=6
    COLUMN_EXTRA_HREF=7  # hidden
    COLUMN_EXTRA_SHOWTHISROW=8 # hidden, flag for whether this row should be shown or filtered (not yet implemented)

    def __init__(self,contexthref,paramdb,clparamname,clparamname2=None,popupcallback=None,popupcallbackargs=[],allchecklists=False,allplans=False):
        gobject.GObject.__init__(self)
        self.contexthref=contexthref
        self.paramdb=paramdb
        self.clparamname=clparamname
        self.clparamname2=clparamname2
        #self.explogwin=explogwin
        self.popupcallback=popupcallback
        self.popupcallbackargs=popupcallbackargs
        
        self.allchecklists=allchecklists
        self.allplans=allplans

        self.checklists=[]
        self.liststorerows=0

        if clparamname2 is not None:
            self.set_title("datacollect2 %s/%s" % (clparamname,clparamname2))
            pass
        else:
            self.set_title("datacollect2 %s" % (clparamname))
            pass
        
        titles=["Orig Name","Filename","Measnum","Start Timestamp","Open","All Checked","Done"]

        types=[gobject.TYPE_STRING,gobject.TYPE_STRING,gobject.TYPE_LONG,gobject.TYPE_STRING,gobject.TYPE_BOOLEAN,gobject.TYPE_BOOLEAN,gobject.TYPE_BOOLEAN,gobject.TYPE_STRING,gobject.TYPE_BOOLEAN]
        
        self.liststore=gtk.ListStore(*types)
        
        self.set_property("default-width",1100)
        self.set_property("default-height",350)

        self.liststoreupdate()


        self.treeview=gtk.TreeView(self.liststore)

        # Create columns
        for colnum in range(len(titles)):
            renderer=gtk.CellRendererText()
            # print "column: %s" % (titles[tagnum])
            # if colnum==self.COLUMN_VALUE: # Value column
            #    renderer.set_property('editable', True)
            #    renderer.connect('edited',self.cell_edited_callback)
            #    pass
            column=gtk.TreeViewColumn(titles[colnum],renderer,text=colnum)  #,background=self.COLUMN_BGCOLOR)  # background=self.COLUMN_BGCOLOR sets column number to extract background colorcursop
            column.set_resizable(True)
            column.set_max_width(300)
            
            column.set_sort_column_id(colnum)
            self.treeview.append_column(column)
            pass

        
        self.scrolled=gtk.ScrolledWindow()
        
        # gtk3 defines Gtk.PolicyType
        if hasattr(gtk,"PolicyType") and hasattr(gtk.PolicyType,"AUTOMATIC"):
            self.scrolled.set_policy(gtk.PolicyType.AUTOMATIC,gtk.PolicyType.ALWAYS)
            pass
        else :
            self.scrolled.set_policy(gtk.POLICY_AUTOMATIC,gtk.POLICY_ALWAYS)
            pass

        self.viewport=gtk.Viewport()
        if self.treeview is not None:
            self.viewport.add(self.treeview)
            pass
        
        self.scrolled.add(self.viewport)
        self.add(self.scrolled)

        self.connect("delete-event",self.closehandler)

        self.treeview.connect("row-activated",self.rowactivate)

        # set up tooltips
        self.treeview.set_property('has-tooltip',True)
        self.treeview.connect("query-tooltip",self.query_tooltip)

        self.show_all()
        

        checklistdb.requestopennotify(self.liststoreupdate)
        checklistdb.requestfilenamenotify(self.liststoreupdate)
        checklistdb.requestresetnotify(self.liststoreupdate)
        checklistdb.requestdonenotify(self.liststoreupdate)
        checklistdb.requestclosenotify(self.liststoreupdate)


        pass

    def query_tooltip(self,widget,x,y,keyboard_mode,tooltip):

        #sys.stderr.write("query_tooltip\n")
        # reference: http://www.gtkforums.com/viewtopic.php?t=2590
        # reference: https://developer.gnome.org/gtk3/stable/GtkTooltip.html#GtkTooltip.description
        # reference: Evolution's mail-component.c query_tooltip_cb() function
        context=self.treeview.get_tooltip_context(x,y,keyboard_mode)
        if not context:
            return False
        else: 
            (model,path,tviter)=context
            #sys.stderr.write("query_tooltip got context\n")

            # Determine column
            if keyboard_mode:
                cursor=self.treeview.get_cursor()
                if cursor is None:
                    return False
                (pathjunk,column)=cursor
                pass
            else: 
                #sys.stderr.write("query_tooltip mouse mode x=%d, y=%d\n" % (x,y))

                path_at_pos=self.treeview.get_path_at_pos(x,y)
                if path_at_pos is None:
                    return False
                (pathjunk,column,relx,rely)=path_at_pos
                
                #sys.stderr.write("query_tooltip got path\n")
                self.treeview.set_tooltip_cell(tooltip,path,column,None)

                # convert column (gtk.TreeViewColumn object) to columnum
                # This is a hack... there must be a better way. 
                columnnum=column.get_sort_column_id() # since we set this property to match up with colnum when we created the TreeViewColumns. 

                #model.get(tviter,column)
                href_absurl=model.get_value(tviter,self.COLUMN_EXTRA_HREF)
                checklistentry=None
                if href_absurl in self.checklistsbyabsurl:
                    checklistentry=self.checklistsbyabsurl[href_absurl]
                    pass
                #sys.stderr.write("query_tooltip got href %s\n" % (href))

                ## find checklistentry
                #checklistentry=None
                #for entry in self.checklists:
                #    if entry.filehref==href:
                #        checklistentry=entry
                #        break
                #    pass
                
                if checklistentry is None:
                    return False # no checklist found
                
                # only need columns that are abbreviated here...
                if columnnum==self.COLUMN_ORIGHREF:
                    text=checklistentry.orighref.absurl()
                    pass
                #elif columnnum==self.COLUMN_CLINFO:
                #    text=checklistentry.clinfo
                #    pass
                elif columnnum==self.COLUMN_FILENAME:
                    text=checklistentry.filehref.absurl()
                    pass
                elif columnnum==self.COLUMN_MEASNUM:
                    if checklistentry.measnum is not None:
                        text=str(checklistentry.measnum)
                        pass
                    else:
                        text=""
                        pass
                    pass                
                elif columnnum==self.COLUMN_STARTTIMESTAMP:
                    text=checklistentry.starttimestamp
                    pass

                else : 
                    #sys.stderr.write("Unknown column: %s\n" % (str(columnnum)))
                    return False
                    pass

                tooltip.set_text(text)
                return True
            pass
            
            


    def closehandler(self,widget,event):
        # returns False to close, True to cancel
        self.hide()
        return True
        #return False  # don't actually close stuff so it can be reopened
        #del self.paramdb
        #del self.clparamname
        #del self.allchecklists
        #del self.allplans
        #del self.liststore
        #del self.treeview
        #del self.checklists
        #del self.scrolled
        #del self.viewport

        #return False

    def rowactivate(self,widget,path,column):
        cur_iter=self.liststore.get_iter(path)
        href_absurl=self.liststore.get_value(cur_iter,self.COLUMN_EXTRA_HREF)

        #import pdb as pythondb
        #pythondb.set_trace()
        
        if href_absurl not in self.checklistsbyabsurl:
            return  # Can't find href in our database (?)
        
        href=self.checklistsbyabsurl[href_absurl].filehref
        self.popupcallback(href,*self.popupcallbackargs)
        pass


    def liststoreupdate(self,*args,**kwargs):
        # all parameters ignored -- just present so it can 
        # be used by notifiers with arbitrary parameters

        # self.checklists is a list of class checklistdb.checklistentry

        # indexes for easy lookup
        checklistsbyhref=dict((entry.filehref,entry) for entry in self.checklists)
        checklistsbyid=dict((id(entry.checklist),entry) for entry in self.checklists if entry.checklist is not None)


        
        updchecklists=checklistdb.getchecklists(self.contexthref,self.paramdb,self.clparamname,self.clparamname2,allchecklists=self.allchecklists,allplans=self.allplans)
        updchecklistsbyhref=dict((entry.filehref,entry) for entry in updchecklists)
        updchecklistsbyid=dict((id(entry.checklist),entry) for entry in updchecklists if entry.checklist is not None)

        # go through current list of checklists, search for any that have been removed
        clnum=0
        while clnum < len(self.checklists):
            if self.checklists[clnum].filehref not in updchecklistsbyhref and id(self.checklists[clnum]) not in updchecklistsbyid:
                # Remove


                #if hasattr(gtk.TreeRowReference,"new"): # gtk3 requires use of gtk.TreeRowReference.new and gtk.TreePath
                #    TreeRowRef=gtk.TreeRowReference.new(self.liststore,gtk.TreePath((clnum,)))
                #    pass
                #else : 
                #    TreeRowRef=gtk.TreeRowReference(self.liststore,(clnum,)))
                #    pass
                #self.liststore.remove(self.liststore.get_iter(TreeRowRef.get_path()))

                # remove from liststore
                self.liststore.remove(self.liststore.iter_nth_child(None,clnum))
                self.liststorerows-=1
                del self.checklists[clnum]  # remove from our list
                # no increment
                pass
            else : 
                clnum+=1
                pass
            pass

        # look for any checklists that have changed path

        for clid in checklistsbyid:
            oldhref=checklistsbyid[clid].filehref
            newhref=None
            if clid in updchecklistsbyid:
                newhref=updchecklistsbyid[clid].filehref
                pass
            if ((oldhref is None) ^ (newhref is None)) or oldhref != newhref:  # ^ is XOR ... use this because can't compare hrefs to None
                if newhref is None or newhref.ismem(): # a reset ... leave this entry under its old name; add a new entry
                    checklistsbyid[clid].checklist=None  # old checklist no longer has a checklist object

                    # The new (resetted) checklist will get a new entry below when we sort through by name
                    pass
                else : 
                    # self.liststore.set_value(self.liststore.iter_nth_child(None,rownumsbyid[clid])),self.COLUMN_FILENAME,newpath)
                    checklistsbyid[clid].filehref=newhref
                    pass
                pass
            pass
        
        # rebuild checklistsbyid according to modified list of checklists. 
        checklistsbyid=dict((id(entry.checklist),entry) for entry in self.checklists if entry.checklist is not None)

        # rebuild checklistsbyhref according to modified list of checklists. 
        checklistsbyhref=dict((entry.filehref,entry) for entry in self.checklists)

        # be able to look up row numbers by checklist id
        rownumsbyentryid={}
        for cnt in range(len(self.checklists)):
            # sys.stderr.write("%s: id(%d) -> row %d\n" % (str(self.checklists[cnt]),id(self.checklists[cnt]),cnt))
            rownumsbyentryid[id(self.checklists[cnt])]=cnt
            pass



        # now go through by name and add entries as needed
        for checklist in updchecklists: 
            if checklist.filehref not in checklistsbyhref: 
                # need to add this one
                self.checklists.append(checklist)
                # Don't forget to add to the liststore somewhere!
                pass
            else : 
                # copy in new information --- replace old entry
                self.checklists[rownumsbyentryid[id(checklistsbyhref[checklist.filehref])]]=checklist
                pass
                
            pass


        ## be able to look up row numbers by canonpath
        #rownumsbycanonpath={}
        #for cnt in range(len(self.checklists)):
        #    rownumsbycanonpath[self.checklists[cnt].canonicalpath]=cnt
        #    pass

        
        # be able to look up row numbers by checklist id
        # rebuild because new entries may have been added
        rownumsbyentryid={}
        for cnt in range(len(self.checklists)):
            #sys.stderr.write("%s: id(%d) -> row %d\n" % (str(self.checklists[cnt]),id(self.checklists[cnt]),cnt))
            rownumsbyentryid[id(self.checklists[cnt])]=cnt
            pass


        # Now go through self.checklists and abbreviate long filenames, etc. 
        
        #doabbrev(self.checklists,"filename","filename_abbrev")
        
        #doabbrev(self.checklists,"starttimestamp","starttimestamp_abbrev",separator=":")
        #doabbrev(self.checklists,"clinfo","clinfo_abbrev")
        #doabbrev(self.checklists,"origfilename","origfilename_abbrev",separator="/")
            
        self.checklistsbyabsurl=dict((entry.filehref.absurl(),entry) for entry in self.checklists)


        # fill in a row for each entry
        rownum=0
        for entry in self.checklists: 
            # add row if necessary
            if rownum >= self.liststorerows:
                self.liststore.append()
                self.liststorerows+=1
                pass
            clid=id(entry)

            # first (0) column is abbreviated orighref
            #import pdb as pythondb
            #try:
            #
            orighreffilepart=""
            if entry.orighref is not None:
                orighreffilepart=entry.orighref.get_bare_unquoted_filename()
                pass
            
            if self.liststore.get_value(self.liststore.iter_nth_child(None,rownumsbyentryid[clid]),self.COLUMN_ORIGHREF) != orighreffilepart:
                self.liststore.set_value(self.liststore.iter_nth_child(None,rownumsbyentryid[clid]),self.COLUMN_ORIGHREF, orighreffilepart)
            # 2nd (1) column is abbreviated clinfo
            #import pdb as pythondb
            #try:
            #
            #if self.liststore.get_value(self.liststore.iter_nth_child(None,rownumsbyentryid[clid]),self.COLUMN_CLINFO) != entry.clinfo_abbrev:
            #    self.liststore.set_value(self.liststore.iter_nth_child(None,rownumsbyentryid[clid]),self.COLUMN_CLINFO, entry.clinfo_abbrev)
            #    pass
            #    pass
            #except:
            #    pythondb.post_mortem()
            #    pass

            ## 3rd column (2) is CLTYPE
            #if self.liststore.get_value(self.liststore.iter_nth_child(None,rownumsbyentryid[clid]),self.COLUMN_CLTYPE) != entry.cltype:
            #    self.liststore.set_value(self.liststore.iter_nth_child(None,rownumsbyentryid[clid]),self.COLUMN_CLTYPE, entry.cltype)
            #    pass
                
            
            # 2nd (1) column is abbreviated filename
            filename=""
            if entry.filename is not None:
                filename=entry.filename
                pass
            
            if self.liststore.get_value(self.liststore.iter_nth_child(None,rownumsbyentryid[clid]),self.COLUMN_FILENAME) != filename:
                self.liststore.set_value(self.liststore.iter_nth_child(None,rownumsbyentryid[clid]),self.COLUMN_FILENAME, filename)
                pass

            # 3rd (2) column is measnum
            #sys.stderr.write("entry.measnum=%s\n" % (str(entry.measnum)))
            measnum=-1
            if entry.measnum is not None:
                measnum=entry.measnum
                pass
            
            if self.liststore.get_value(self.liststore.iter_nth_child(None,rownumsbyentryid[clid]),self.COLUMN_MEASNUM) != measnum:
                self.liststore.set_value(self.liststore.iter_nth_child(None,rownumsbyentryid[clid]),self.COLUMN_MEASNUM, measnum)
                pass
            
            starttimestamp=""
            if entry.starttimestamp is not None and entry.starttimestamp != "":
                starttimestamp=timestamp_abbreviate(entry.starttimestamp)
                pass
            # 4th (3) column is abbreviated starting timestamp
            if self.liststore.get_value(self.liststore.iter_nth_child(None,rownumsbyentryid[clid]),self.COLUMN_STARTTIMESTAMP) != starttimestamp:
                self.liststore.set_value(self.liststore.iter_nth_child(None,rownumsbyentryid[clid]),self.COLUMN_STARTTIMESTAMP, starttimestamp)
                pass

            # 5th (4) column is is_open
            if self.liststore.get_value(self.liststore.iter_nth_child(None,rownumsbyentryid[clid]),self.COLUMN_IS_OPEN) != entry.is_open:
                self.liststore.set_value(self.liststore.iter_nth_child(None,rownumsbyentryid[clid]),self.COLUMN_IS_OPEN, entry.is_open)
                pass

            # 6th (5) column is allchecked
            if self.liststore.get_value(self.liststore.iter_nth_child(None,rownumsbyentryid[clid]),self.COLUMN_ALLCHECKED) != entry.allchecked:
                self.liststore.set_value(self.liststore.iter_nth_child(None,rownumsbyentryid[clid]),self.COLUMN_ALLCHECKED, entry.allchecked)
                pass

            # 7th (6) column is is_done
            if self.liststore.get_value(self.liststore.iter_nth_child(None,rownumsbyentryid[clid]),self.COLUMN_IS_DONE) != entry.is_done:
                self.liststore.set_value(self.liststore.iter_nth_child(None,rownumsbyentryid[clid]),self.COLUMN_IS_DONE, entry.is_done)
                pass


            # 8th (7) column is EXTRA_HREF
            if self.liststore.get_value(self.liststore.iter_nth_child(None,rownumsbyentryid[clid]),self.COLUMN_EXTRA_HREF) != entry.filehref.absurl():
                self.liststore.set_value(self.liststore.iter_nth_child(None,rownumsbyentryid[clid]),self.COLUMN_EXTRA_HREF, entry.filehref.absurl())
                pass

            # 9th (8) column is EXTRA_SHOWTHISROW (not yet implemented)
                
            rownum+=1
            pass
        pass
    pass

