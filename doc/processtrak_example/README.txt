This is an example of the use of ProcessTrak for data analysis.
Thanks to Joseph Hynek for providing the data and for his permission
to share the data.

It is from an RF (radio frequency) survey of the Creston, IA area.
The bulk data files are in the creston_jan2016/ subdirectory.

RF spectrum data was captured from a vehicle and stored in .csv format.
Simultaneously, GPS tracking data was captured using a cellphone.

The two datasets are merged to create geographic maps of estimated RF intensity
at different frequencies.

You can adjust the comments in the process_spectrum.prx file to use
EITHER the creston_jan2016.xlg experiment log file as input OR the
creston_jan2016.xls spreadsheet file as input. To use the spreadsheet file
you will need to have the xlrd Python package installed. 

The steps are
----------------------------------------------------------------
copyinput              (this step is always implicitly present,
                       and copies the experiment log to the
		       processed experiment log.)
extract_rflog_entries  Extract data from the rflog csv files into
                       the XML experiment log
combine_freqband_lines Merge adjacent spectrum entries for different
                       frequency subbands into a merged spectrum
		       covering the entire frequency band of
		       interest
mergegps               Merge in GPS data by aligning times.
energymap              Generate .png images of RF energy at different
                       frequencies using matplotlib. Also create .kml
		       (Google Earth) files for rendering these images
		       as geographic overlays.
generatespreadsheet    Generate a summary spreadsheet listing the
                       frequencies, .png images, and .kml overlays.


