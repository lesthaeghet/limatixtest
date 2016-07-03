# writespreadsheet.py:
# a processtrak script that writes your
# experiment log or a tabular portion of your
# experiment log to a .ods spreadsheet

# *** This is unfinished

import collections
import zipfile


# Example sheetspec
sheetspec=r"""
<sheetspec xmlns="http://limatix.org/processtrak" xmlns:pt="http://limatix.org/processtrak">
  <sheet name="My sheet" tableselect="prx:href(outputfile)/dc:experiment">  <!-- Can create multiple sheets, iterating over nodes found with selection. Selection is relative to the iterating context of the step -- i.e. the element found according to elementmatch. Can use nameselect="xpath_expression" in place of name="name". The nameselect expression will be reevaluated in the context of each tableselect selection -->
    <rows select="dc:measurement"/> <!-- relative to table selected in the <sheet> tag above -->
      <col select='dgsfile' type="href" label="DGS Filename"/>
      <col select='concat(substring(normalize-space(timestamp),6,2),"/",substring(normalize-space(timestamp),9,2),"/",substring(normalize-space(timestamp),3,2))' label="Date"/>
      <col select='substring(normalize-space(timestamp),12,8)' label="Time"/>
      <col select="takenby" label="Taken by"/>
      <col select="specimen" label="Specimen ID" type="string"/>
      <col select="number(excitation/t3)-number(excitation/t0)" label="Excitation length (s)"/>
      <col select="clamptorque" label="Clamp torque (in-oz)"/>
      <col select="transducerforce" label="Transducer static force (N)"/>
      <col select="(excitation/@type='burst')*excitation/f0" label="Burst frequency"/>
      <col select="transducerserial" label="Transducer serial number"/>
      <col select="couplant" label="Couplant"/>
      <col select="amplitude" label="Excitation amplitude (Volts)"/>
      <col select="elecenergy" label="Electrical Energy (Joules)"/>
      <col select="hae" label="HAE (m^2/s)"/>
      <col select="dynstress" label="Dynamic stress"/>
      <col select='crackheat' type="numeric" label="Crack heating, gaussian fit (K)"/>
      <col select="pixelsperinch" type="numeric" label="Pixels per inch"/>
      <col select="notes" type="string" label="Notes"/>

      <!-- colspec select='/run/@date' label="Date" type="string"/-->
  </sheet>
</sheetspec>
"""




transformation = r"""<?xml version="1.0" encoding="utf-8"?>
<xsl:transform xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
xmlns:dyn="http://exslt.org/dynamic"
xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"
xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
xmlns:xlink="http://www.w3.org/1999/xlink"
xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0"
xmlns:number="urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0"
xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"
xmlns:chart="urn:oasis:names:tc:opendocument:xmlns:chart:1.0"
xmlns:dr3d="urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0"
xmlns:math="http://www.w3.org/1998/Math/MathML"
xmlns:form="urn:oasis:names:tc:opendocument:xmlns:form:1.0"
xmlns:script="urn:oasis:names:tc:opendocument:xmlns:script:1.0"
xmlns:dom="http://www.w3.org/2001/xml-events"
xmlns:xforms="http://www.w3.org/2002/xforms"
xmlns:xsd="http://www.w3.org/2001/XMLSchema"
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
extension-element-prefixes="dyn"
version="1.0">

<xsl:output method='xml' indent='yes'/>

<xsl:param name="datestamp"/>
<xsl:param name="sheetspecname"/>
<xsl:param name="filespecname"/>
  
<xsl:template match='/'>

<!-- Opendocument boilerplate -->
<office:document-content office:version="1.0">  <!-- for ODF 1.2 conformance, change "1.0" to "1.2" -->
<office:scripts/>
<office:automatic-styles>
  <style:style style:name="co1" style:family="table-column">
    <style:table-column-properties fo:break-before="auto" style:column-width="0.8925in"/>
  </style:style>
  <style:style style:name="ro1" style:family="table-row">
    <style:table-row-properties style:row-height="0.1681in" fo:break-before="auto" style:use-optimal-row-height="true"/>
  </style:style>
  <style:style style:name="ta1" style:family="table" style:master-page-name="Default">
    <style:table-properties table:display="true" style:writing-mode="lr-tb"/>
  </style:style>
</office:automatic-styles>

<office:body><office:spreadsheet>
  <xsl:apply-templates/>
</office:spreadsheet>
</office:body>
</office:document-content>
</xsl:template>




<xsl:template match="pt:sheet"> <!-- This template needs the xmlns context of the sheetspec !!! --> 
<xsl:variable name="name"><xsl:value-of select="@name"/></xsl:variable>
<xsl:variable name="nameselect"><xsl:value-of select="@nameselect"/></xsl:variable>
<xsl:variable name="sheet" select="."/>
<!-- will monkey-patch in sheetspec's nsmap to each tag with select= 
     containing dyn:evaluate -->
<xsl:for-each select="dyn:evaluate(@tableselect)">
  <xsl:element name="table:table">
    <xsl:attribute name="table:name">
      <xsl:choose>
        <xsl:when test="string-length($nameselect) &gt; 0">
          <xsl:value-of select="dyn:evaluate($nameselect)"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:value-of select="$name"/> 
        </xsl:otherwise>
      </xsl:choose>
    </xsl:attribute>
  <xsl:attribute name="table:style-name">ta1</xsl:attribute>
  <xsl:attribute name="table:print">false</xsl:attribute>
  <table:table-column table:style-name="co1" table:default-cell-style-name="Default"/>
  <table:table-row table:style-name="ro1">
    <table:table-cell office:value-type="string">
    <text:p><xsl:value-of select="title"/></text:p>  
    </table:table-cell>
  </table:table-row>
  <table:table-row table:style-name="ro1">
    <table:table-cell/>
  </table:table-row>
  <table:table-row table:style-name="ro1">
    <table:table-cell office:value-type="string">
    <text:p>MACHINE-GENERATED: DO NOT EDIT! </text:p>  
    </table:table-cell>
  </table:table-row>
  <table:table-row table:style-name="ro1">
    <table:table-cell office:value-type="string">
    <text:p>Converter: </text:p>  
    </table:table-cell>
    <table:table-cell office:value-type="string">
    <text:p>writespreadsheet.py</text:p>  
    </table:table-cell>
    <!-- <table:table-cell office:value-type="string">
    <text:p>Filespec:</text:p>  
    </table:table-cell>
    <table:table-cell office:value-type="string">
    <text:p><xsl:value-of select="$filespecname"/></text:p>  
    </table:table-cell> -->
    <table:table-cell office:value-type="string">
    <table:table-cell office:value-type="string">
    <text:p>Datestamp:</text:p>  
    </table:table-cell>
    <table:table-cell office:value-type="string">
    <text:p><xsl:value-of select="$datestamp"/></text:p>  
    </table:table-cell>
  </table:table-row>
  <table:table-row table:style-name="ro1">
    <table:table-cell/>
  </table:table-row>
  
  <table:table-row table:style-name="ro1">
    <xsl:apply-templates select="$sheet/pt:col" mode="headings"/>
  </table:table-row>

  <xsl:for-each select="dyn:evaluate($sheet/pt:rows/@select)">
    <xsl:variable name="row" select="."/>
    <table:table-row table:style-name="ro1">
      <xsl:apply-templates select="$sheet/pt:col" mode="rows">
        <xsl:with-param name="row" select="$row"/>
      </xsl:apply-templates>
    </table:table-row>
  </xsl:for-each>
  
</xsl:element> <!-- table:table -->

</xsl:template>

<xsl:template match="pt:col" mode="headings">
  <table:table-cell office:value-type="string">
  <text:p>
    <xsl:value-of select='@label'/>
  </text:p>
</table:table-cell>
</xsl:template>

<xsl:template match="pt:col" mode="rows">
  <xsl:param name="row"/>
  <xsl:variable name="col" select="."/>
  <!-- Store cell content in a variable -->
  <xsl:variable name="cellcontent">
    <!-- force context area over to the row element -->
    <xsl:for-each select="$row">
      <xsl:value-of select='dyn:evaluate($col/@select)'/>
    </xsl:for-each>
  </xsl:variable>
  <xsl:choose>
    <xsl:when test="string($col/@type)='numericunits'">
      <xsl:element name="table:table-cell">
        <xsl:attribute name="office:value-type">float</xsl:attribute>
        <xsl:attribute name="office:value"><xsl:value-of select="normalize-space($cellcontent)"/></xsl:attribute>
         <text:p><xsl:value-of select="normalize-space($cellcontent)"/></text:p>
      </xsl:element>
    </xsl:when>
    <xsl:otherwise>
      <table:table-cell office:value-type="string">
        <text:p><xsl:value-of select="normalize-space($cellcontent)"/></text:p>
      </table:table-cell>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>



</xsl:transform>

"""


class href_lookupfcn_ext(object):
    # etree extension prx:href that allows looking up other
    # documents via hypertext references
    extensions=None  # extensions parameter for etree.xpath
    docdb=None   # Dictionary of xmldocs by href. Include output, prxdoc, and sheetspec
    sheetspec=None # sheetspec etree.Element within its own xmldoc
    
    def __init__(self,docdb,sheetspec):
        self.docdb=docdb
        self.sheetspec=sheetspec
        functions=('href','sheetspec')
        self.extensions=etree.Extension(self,functions,ns="http://limatix.org/processtrak/processinginstructions")
        pass

    def sheetspec(self,context):
        return self.sheetspec

    def href_eval_href(self,hrefobj):
        if hrefobj not in self.docdb:
            self.docdb[hrefobj]=xmldoc.xmldoc.loadhref(hrefobj)
            pass
        return self.docdb[hrefobj].doc.getroot()
    
    def href_eval_node(self,contextxmldoc,context,node):
        if isinstance(node,basestring):
            hrefobj=dc_value.hrefvalue(node,contexthref=contextxmldoc.getcontexthref())
            return self.href_eval_href(hrefobj)
        elif isinstance(node,collections.Sequence):
            result=[]
            for subnode in node:
                result.append(self.href_eval_node(contextxmldoc,context,subnode))
                pass
            return result
        else:   # Should be a single node
            hrefobj=dc_value.hrefvalue.fromxml(contextxmldoc,node)
            return self.href_eval_href(hrefobj)
        pass
    
    def href(self,context,node):
        # find document root
        ancestor=context.context_node

        while ancestor is not None:
            oldancestor=ancestor
            ancestor=ancestor.getparent()
            pass
        docroot=oldancestor

        # Now search in docdb for a document with that root
        contextxmldoc=None
        for hrefv in self.docdb:
            if docroot is self.docdb[hrefv].getroot():
                contextxmldoc=self.docdb[hrefv]
                pass
            pass
        if contextxmldoc is None:
            raise ValueError("prx:href() extension function called from context that is not in docdb")

        return self.hrefevalnode(contextxmldoc,context,node)
    pass


def write_output(outfilename,result):

    outfile=zipfile.ZipFile(outfilename,"w",zipfile_compression);

    if sys.version_info[0] <= 2 and sys.version_info[1] < 7:
        outfile.writestr("mimetype","application/vnd.oasis.opendocument.spreadsheet");
        pass
    else :
        # on Python 2.7 can explicitly specify lack of compression for this file alone 
        outfile.writestr("mimetype","application/vnd.oasis.opendocument.spreadsheet",compress_type=zipfile.ZIP_STORED)
        pass
    
    #  ODF 1.2 will require manifest:version="1.2" as an attribute to manifest:manifest
    outfile.writestr("META-INF/manifest.xml",r"""<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0">
 <manifest:file-entry manifest:media-type="application/vnd.oasis.opendocument.spreadsheet" manifest:full-path="/"/>
 <manifest:file-entry manifest:media-type="text/xml" manifest:full-path="content.xml"/>
 <!-- manifest:file-entry manifest:media-type="text/xml" manifest:full-path="styles.xml"/-->
 <!-- manifest:file-entry manifest:media-type="text/xml" manifest:full-path="meta.xml"/-->
 <!-- manifest:file-entry manifest:media-type="text/xml" manifest:full-path="settings.xml"/-->
</manifest:manifest>
""");

    # Write out result of processing as content.xml
    outfile.writestr("content.xml",result);
    
    outfile.close()
    pass


def run(_prxdoc,_xmldoc,_element,prx_sheetspec,prx_outfilenamexpath):


    docdb={}
    docdb[_prxdoc.get_filehref()]=_prxdoc
    docdb[_xmldoc.get_filehref()]=_xmldoc
    
    #sheetspec=prx_sheetspec_xmltree.get_xmldoc()
    docdb[sheetspec.get_filehref()]=sheetspec # don't wrap it in another xmldoc, so context lookups work properly
    

    href_lookupfcn=href_lookupfcn_ext(docdb,sheetspec.getroot())

    stylesheet=etree.XML(transformation)

    # !!!*** Need to monkeypatch in nsmap from sheetspec into
    # all elements of stylesheet with a select attribute that contains
    # dyn:evaluate
    
    transform=etree.XSLT(stylesheet,extensions=href_lookupfcn_ext.extensions)
    ods=transform(sheetspec)

    result=etree.tostring(ods)

    # need to evaluate prx_outfilenamexpath

    write_output(outfilename,result):

    return {"prx:spreadsheet": 
