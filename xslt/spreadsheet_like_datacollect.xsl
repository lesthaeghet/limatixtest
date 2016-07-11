<xsl:stylesheet version="1.0"
		xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
		xmlns:xlink="http://www.w3.org/1999/xlink" 
		xmlns:dc="http://limatix.org/datacollect" 
		xmlns:lip="http://limatix.org/provenance" 
		xmlns:ls="http://limatix.org/spreadsheet" 
		xmlns:dcv="http://limatix.org/dcvalue" 
		xmlns:prx="http://limatix.org/processtrak/processinginstructions">
  <!-- spreadsheet_like_datacollect.xsl: This can be used as an xslt filter
       to convert processtrak's interpretation of a spreadsheet to 
       something more similar to what datacollect generates
         * Main tag changed from ls:sheet to dc:experiment
         * Rows changed from ls:row to dc:measurement
         * Other ls: tags changed to dc: namespace
         * attributes unchanged 

       To use add <xslt name="spreadheet_like_datacollect.xsl">
       inside the <inputfile> tag for your spreadsheet

  -->

  <xsl:output method="xml" encoding="utf-8"/>
  
  <!-- Convert /ls:sheet to dc:experiment -->
  <xsl:template match="/ls:sheet">
    <dc:experiment>
      <xsl:apply-templates/>
    </dc:experiment>
  </xsl:template>
  
  <!-- Convert ls:row to dc:measurement -->
  <xsl:template match="ls:row">
   <dc:measurement>
      <xsl:apply-templates/>
    </dc:measurement>
  </xsl:template>

  <!-- Convert ls:rownum to dc:measnum -->
  <xsl:template match="ls:rownum">
   <dc:measnum>
      <xsl:apply-templates/>
    </dc:measnum>
  </xsl:template>

  <!-- Convert ls:namespace elements to dc: -->
  <xsl:template match="ls:*">
    <xsl:element name="dc:{local-name()}" namespace="http://limatix.org/datacollect"><xsl:apply-templates select="@*|node()"/>
    </xsl:element>
  </xsl:template>

  <!-- Copy everything else verbatim -->
  <xsl:template match="@*|node()">
    <xsl:copy><xsl:apply-templates select="@*|node()"/></xsl:copy>
  </xsl:template>
</xsl:stylesheet>
