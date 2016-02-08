About datacollect2
------------------

datacollect2 is a checklist-based system for performing and recording
scientific experiments. It does not address the problem of data acquisition
per se -- it assumes you have another software package handling that.
Instead, it addresses the parallel problems of keeping track of procedures,
recording which procedures were performed, and keeping a log (like a
laboratory notebook) of the progress of an experiment. It also includes
a tool (dc_process) to assist in organizing and executing processing tasks.



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
dc_process -- command line tool for controlling postprocessing steps
dc_ricohphoto -- Tool to use Ricoh WiFi camera to capture pictures of
                 and experiment
dc_xlg2dpd -- tool to extract a datacollect parameter dump (.dpd file) from
              an experiment log

Primary Libraries
-----------------
dc_value     -- value classes that support units and serialize to XML
xmldoc       -- representation of an XML document such as an experiment log,
                with routines to add and extract data.
dc_provenance -- Provenance tracking within XML documents
paramdb2     -- Database of parameters to be written to experiment log
