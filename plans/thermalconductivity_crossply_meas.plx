<?xml version="1.0" encoding="UTF-8"?>
<checklist xmlns="http://limatix.org/checklist" xmlns:chx="http://limatix.org/checklist" xmlns:dc="http://limatix.org/datacollect"  xmlns:xlink="http://www.w3.org/1999/xlink">
  <clinfo>Thermalconductivity measurement of cross-ply specimens</clinfo>
  <cltitle>Test thermal conductivity of specimens</cltitle>
  <dest autofilename="'thermalconductivity_crossply_meas.plf'"/>
  <rationale>Need to evaluate thermalconductivity specimens to know material properties to support modeling</rationale>
  


    <checkitem class="runchecklist" title="Perform prep on each specimen">
      <copychecklist xlink:href="thermalconductivity_prep.chx"/>
        <description>Prep procedure assembles specimen. Specimens TD-1, TD-2, TD-3, TD-4, TD-5, TD-6</description>
    </checkitem>

    <checkitem class="text" title="Test thermal conductivity tester waveform output">
        <description>Plug into USB and use terminal program to log and save output.</description>
    </checkitem>

    <checkitem class="text" title="Let samples equilibriate">
      <description>Samples need to be placed in the same room where they will be tested, so they have time to equilibriate to the environment.</description>
    </checkitem>
    

    <checkitem class="runchecklist" title="Perform test on each specimen">
      <copychecklist xlink:href="thermalconductivity_meas.chx"/>
        <description>Test each specimen with belt sander. Specimens TD-1, TD-2, TD-3, TD-4, TD-5, TD-6</description>
    </checkitem>

    <notes shared="true"/>
</checklist>
