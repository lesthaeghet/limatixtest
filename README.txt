About LIMATIX
------------------

LIMATIX is a collection of tools for performing and recording scientific
experiments, based on the twin ideas of checklists and experiment logs.
It does not address the problem of data acquisition per se -- it assumes
you have another software package handling that. Instead, it addresses
the parallel problems of keeping track of procedures, recording which
procedures were performed, and keeping a log (like a laboratory notebook)
of the progress of an experiment. It also includes a tool (processtrak)
to assist in organizing and executing processing tasks.



Programs
--------
datacollect2 -- Main program for performing checklist-based experiment logging
dc_checklist -- Main program for standalone checklists and plans
dc_chx2chf -- create a filled checklist file from an unfilled .chx file
dc_getpath -- get the path to the datacollect2 installation
dc_glade   -- run the glade 3.6.7 user interface builder to create custom
              GUI interfaces
dc_gui     -- Run a custom GUI interface created with dc_glade
dc_paramdb2 -- Run a parameter database server with a simple tabular GUI
processtrak -- command line tool for controlling postprocessing steps
pt_checkprovenance -- Tool to check provenance status of processed experiment
                      logs
dc_ricohphoto -- Tool to use Ricoh WiFi camera to capture pictures of
                 and experiment
dc_xlg2dpd -- tool to extract a datacollect parameter dump (.dpd file) from
              an experiment log (OBSOLETE)
thermal2limatix -- Tool to convert obsolete XML namespaces to the new
                   limatix namespaces

Primary libraries in the limatix package
----------------------------------------
dc_value     -- value classes that support units and serialize to XML
xmldoc       -- representation of an XML document such as an experiment log,
                with routines to add and extract data.
provenance   -- Provenance tracking within XML documents
paramdb2     -- Database of parameters to be written to experiment log


Documentation
-------------
Primary LIMATIX documentation is in doc/LIMATIX.xhtml.
Some additional documentation on processtrak is in the presentation
that can be accessed as doc/processtrak.odp or doc/processtrak.pdf



Acknowledgments
---------------
Thanks to the LIMATIX proposal team for their input and support:
  Hui Hu, Iowa State University
  Amy Kaleita, Iowa State University 
  Brian Mennecke, Iowa State University  1960-2016 RIP
  Hridesh Rajan, Iowa State University
  Michael Thompson, Cornell University

Thanks also to Dave Forsyth and Carl Magnuson of TRI-Austin
for their input and support. 

Thanks to Joseph Hynek for providing the RF survey data used in the
ProcessTrak example. 

This material is based on work supported by the Air Force Research
Laboratory under Contract #FA8650-10-D-5210, Task Order #023 and
performed at Iowa State University; Case number XXXXXXXX.

This material is based on work supported by the NASA Early Stage
Innovation (ESI) program under grant #NNX15AD75G
