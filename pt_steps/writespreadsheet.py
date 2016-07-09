# writespreadsheet.py:
# a processtrak script that writes your
# experiment log or a tabular portion of your
# experiment log to a .ods spreadsheet


import collections
import zipfile
import sys
import copy

try:
    # py2.x
    from urllib import pathname2url
    from urllib import url2pathname
    from urllib import quote
    from urllib import unquote
    pass
except ImportError:
    # py3.x
    from urllib.request import pathname2url
    from urllib.request import url2pathname
    from urllib.parse import quote
    from urllib.parse import unquote
    pass


try: 
    import builtins  # python3
    pass
except ImportError: 
    import __builtin__ as builtins # python2
    pass


if not hasattr(builtins,"basestring"):
    basestring=str  # python3
    pass



from lxml import etree

from limatix import dc_value
from limatix import xmldoc

if sys.version_info[0] <= 2 and sys.version_info[1] < 7:
    zipfile_compression=zipfile.ZIP_STORED
    pass
else:
    zipfile_compression=zipfile.ZIP_DEFLATED
    pass


# Example sheetspec
sheetspec=r"""
<param name="prx_sheetspec" xmlns="http://limatix.org/processtrak" xmlns:pt="http://limatix.org/processtrak">
  <sheet name="My sheet" tableselect="dc:experiment">  <!-- Can create multiple sheets, iterating over nodes found with selection. Selection is relative to the iterating context of the step -- i.e. the element found according to elementmatch. Can use nameselect="xpath_expression" in place of name="name". The nameselect expression will be reevaluated in the context of each tableselect selection -->
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
      <col select='crackheat' type="numericunits" units="K" label="Crack heating, gaussian fit (K)"/>
      <col select="pixelsperinch" type="numericunits" label="Pixels per inch"/>
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
xmlns:pt="http://limatix.org/processtrak"
xmlns:prx="http://limatix.org/processtrak/processinginstructions"
xmlns:dcv="http://limatix.org/dcvalue"
xmlns:exsl="http://exslt.org/common"
extension-element-prefixes="dyn prx exsl"
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
  <xsl:apply-templates select="prx:sheetspec()"/>  <!-- This is what pulls in the sheetspec -->
</office:spreadsheet>
</office:body>
</office:document-content>
</xsl:template>




<xsl:template match="pt:sheet"> <!-- This template needs the xmlns context of the sheetspec !!! --> 
<xsl:variable name="name"><xsl:value-of select="@name"/></xsl:variable>
<xsl:variable name="nameselect"><xsl:value-of select="@nameselect"/></xsl:variable>
<xsl:variable name="sheet" select="."/>
<xsl:variable name="tableselect" select="@tableselect"/>

<!-- Switch context to matched element in .xlp file -->
<xsl:for-each select="prx:element()">
  <!-- will monkey-patch in sheetspec's nsmap to each tag with select= 
     containing dyn:evaluate -->
  <xsl:for-each select="dyn:evaluate($tableselect)">
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
      <xsl:variable name="rowsel" select="$sheet/pt:rows"/>
      <xsl:for-each select="dyn:evaluate($rowsel/@select)">
        <xsl:variable name="row" select="."/>
        <table:table-row table:style-name="ro1">
          <xsl:apply-templates select="$sheet/pt:col" mode="rows">
            <xsl:with-param name="row" select="$row"/>
          </xsl:apply-templates>
        </table:table-row>
      </xsl:for-each>
    </xsl:element> <!-- table:table -->
  </xsl:for-each>
</xsl:for-each>

</xsl:template>

<xsl:template match="pt:col" mode="headings">
  <table:table-cell office:value-type="string">
  <text:p>
    <xsl:value-of select='@label'/>
    <xsl:if test="string(@type)='numericunits'">
      <xsl:value-of select="' '"/>(<xsl:value-of select="@dcv:units"/>)</xsl:if></text:p></table:table-cell>
</xsl:template>

<xsl:template match="pt:col" mode="rows">
  <xsl:param name="row"/>
  <xsl:variable name="col" select="."/>
  <!-- Store cell content in a variable -->
  <!-- force context area over to the row element -->
  <xsl:for-each select="$row">
  <xsl:variable name="selection" select="dyn:evaluate($col/@select)"/>
  <xsl:choose>
    <xsl:when test="string($col/@type)='numericunits'">
      <xsl:element name="table:table-cell">
        <xsl:attribute name="office:value-type">float</xsl:attribute>
        <xsl:attribute name="office:value"><xsl:value-of select="prx:numericunitsvalue($selection,$col/@dcv:units)"/></xsl:attribute>
         <text:p><xsl:value-of select="prx:numericunitsvalue($selection,$col/@dcv:units)"/></text:p>
      </xsl:element>
    </xsl:when>
    <xsl:when test="string($col/@type)='numeric'">
      <xsl:element name="table:table-cell">
        <xsl:attribute name="office:value-type">float</xsl:attribute>
        <xsl:attribute name="office:value"><xsl:value-of select="$selection"/></xsl:attribute>
         <text:p><xsl:value-of select="$selection"/></text:p>
      </xsl:element>
    </xsl:when>
    <xsl:when test="string($col/@type)='href'">
      <table:table-cell office:value-type="string">
        <text:p><text:a xlink:type="simple"><xsl:attribute name="xlink:href"><xsl:value-of select="prx:hrefxlink($selection)"/></xsl:attribute><xsl:value-of select="prx:hrefxlink($selection)"/></text:a></text:p>
      </table:table-cell>
    </xsl:when>
    <xsl:otherwise>
      <table:table-cell office:value-type="string">
        <text:p><xsl:value-of select="normalize-space($selection)"/></text:p>
      </table:table-cell>
    </xsl:otherwise>
  </xsl:choose>
  </xsl:for-each>
</xsl:template>



</xsl:transform>

"""



class prx_lookupfcn_ext(object):
    # etree extension prx:href that allows looking up other
    # documents via hypertext references
    extensions=None  # extensions parameter for etree.xpath
    xlpdocu=None  # actually output
    xlpelement=None # context element
    docdb=None   # Dictionary of xmldocs by href. Include output, prxdoc, and sheetspec
    sheetspec_el=None # sheetspec etree.Element within an xmldoc
    
    def __init__(self,docdb,sheetspec_el,xlpdocu,xlpelement):
        self.docdb=docdb
        self.sheetspec_el=sheetspec_el
        self.xlpdocu=xlpdocu
        self.xlpelement=xlpelement
        functions=('href','sheetspec','numericunitsvalue','hrefxlink','xlpdoc','element')
        self.extensions=etree.Extension(self,functions,ns="http://limatix.org/processtrak/processinginstructions")
        pass

    def xlpdoc(self,context):
        return self.xlpdocu.getroot()

    def element(self,context):
        #sys.stderr.write("\n\nelement()\n\n")
        #sys.stderr.write("\n\nelement() returning %s\n\n" % (str(context.context_node)))
        #return context.context_node 
        return self.xlpelement
    
    def numericunitsvalue(self,context,cellcontent,units):
        # Evaluate numeric units of a target element (in cellcontent)
        # according to specified units
            
        if isinstance(cellcontent,list):
            contextdoc=self.finddocument(context.context_node)
            if len(cellcontent) > 1:                
                raise ValueError("Can only evaluate numeric value of a single element: cellcontent = [ %s ]; context=%s" % ( ",".join([dc_value.hrefvalue.fromelement(self.finddocument(cellc),cellc).humanurl() for cellc in cellcontent ]), dc_value.hrefvalue.fromelement(contextdoc,cellcontent.context_node)))
            elif len(cellcontent) == 0:
                raise ValueError("Can not evaluate numeric value of empty element set: context=%s" % (dc_value.hrefvalue.fromelement(contextdoc,context.context_node).humanurl()))
            cellcontent=cellcontent[0]
        
            pass
       
        if isinstance(units,list):
            if len(units) < 1: 
                raise ValueError("Error evaluating units: did not find @dcv:units attribute")
            if len(units) > 1: 
                raise ValueError("Error evaluating units: Resolved to more than one @dcv:units attribute")
            units=units[0]
            pass
        if not isinstance(units,basestring):
            raise ValueError("Error evaluating units: Did not resolve to a string")
        


        #nuv=dc_value.numericunitsvalue.fromxml(self.finddocument(cellcontent),cellcontent).value(units=units)
        # We don't currently provide the document (which allows provenance
        # tracking) because libxslt just seems to be giving us 
        # random elements for which getparent() doesn't work
        nuv=dc_value.numericunitsvalue.fromxml(None,cellcontent).value(units=units)
        return nuv

    def hrefxlink(self,context,sourcelink):
        # return xlink:href attribute value for sourcelink
        # in given context

        contextxmldoc=self.finddocument(context.context_node)

        if isinstance(sourcelink,list):
            if len(sourcelink) < 1:
                #raise ValueError("hrefxlink: Empty source node set, context=%s" % (dc_value.hrefvalue.fromelement(contextxmldoc,context.context_node).humanurl()))
                return []
            elif len(sourcelink) > 1:
                raise ValueError("hrefxlink: Multiple source nodes %s, context=%s" % (",".join([dc_value.hrefvalue.fromelement(self.finddocument(cellc),cellc).humanurl() for cellc in sourcelink ]),dc_value.hrefvalue.fromelement(contextxmldoc,context.context_node).humanurl()))
            sourcelink=sourcelink[0]
            pass
        
        
        # create dummy xmldoc in given context
        dummydoc=xmldoc.xmldoc.newdoc("dummy",nsmap={ "xlink": "http://www.w3.org/1999/xlink" },contexthref=contextxmldoc.getcontexthref())

        hrefval=dc_value.hrefvalue(sourcelink.attrib["{http://www.w3.org/1999/xlink}href"],contexthref=self.finddocument(sourcelink).getcontexthref())
        hrefval.xmlrepr(dummydoc,dummydoc.getroot())
        xlinktext=dummydoc.getattr(dummydoc.getroot(),"xlink:href")
        return xlinktext
    
        

    def sheetspec(self,context):
        return self.sheetspec_el

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

    def finddocument(self,node):
        # find document root
        ancestor=node

        while ancestor is not None:
            oldancestor=ancestor
            ancestor=ancestor.getparent()
            pass
        docroot=oldancestor
        # Now search in docdb for a document with that root
        xmldoc=None
        for hrefv in self.docdb:
            if docroot is self.docdb[hrefv].getroot():
                xmldoc=self.docdb[hrefv]
                pass
            pass
        if xmldoc is None:
            #sys.stderr.write("docroot=%s; docdb=%s\n" % (str(docroot),str(self.docdb)))
            #raise ValueError("prx extension function called with context or node that is not in docdb")
            # if we couldn't find it the correct answer is almost
            # always xlpdocu
            return self.xlpdocu
            
        return xmldoc
            
    def href(self,context,node):

        contextxmldoc=self.finddocument(context.context_node)

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


def run(_prxdoc,_step,_xmldoc,_element,prx_sheetspec_doc,prx_sheetspec,prx_outfilenamexpath_doc,prx_outfilenamexpath,linktag="prx:spreadsheet"):


    docdb={}
    docdb[_prxdoc.get_filehref()]=_prxdoc
    docdb[_xmldoc.get_filehref()]=_xmldoc
    
    #sheetspec=prx_sheetspec_xmltree.get_xmldoc()
    docdb[prx_sheetspec_doc.get_filehref()]=prx_sheetspec_doc # don't wrap it in another xmldoc, so context lookups work properly
    
    stylesheet=etree.XML(transformation)

    
    prx_lookupfcn=prx_lookupfcn_ext(docdb,prx_sheetspec,_xmldoc,_element)  # .getroot())

    # Monkeypatch in nsmap from sheetspec into
    # all xsl:elements of stylesheet with a select attribute that contains
    # dyn:evaluate
    els_to_patch=stylesheet.xpath("//xsl:*[contains(@select,'dyn:evaluate')]",namespaces={"xsl": "http://www.w3.org/1999/XSL/Transform"})
    for el in els_to_patch:
        parent=el.getparent()
        index=parent.index(el)
        
        parent.remove(el)

        # New element, with desired nsmap and copying all attributes
        newel=etree.Element(el.tag,nsmap=prx_sheetspec.nsmap,attrib=el.attrib)
        # Move element's children
        newel[:]=el[:]
        
        newel.text=el.text
        newel.tail=el.tail
        
        parent.insert(index,newel)
        pass
        
    # stylesheetdoc=etree.ElementTree(stylesheet)
    # stylesheetdoc.write("/tmp/foo.xsl")
    
    
    
    transform=etree.XSLT(stylesheet,extensions=prx_lookupfcn.extensions)
    ods=transform(etree.XML("<dummy/>"))  # Stylesheet calls sheetspec() function to get actual sheetspec. This avoids cutting sheespec out of its source document. 

    # result=etree.tostring(ods)

    resultdoc=xmldoc.xmldoc.frometree(ods,contexthref=_xmldoc.getcontexthref())
    
    # evaluate prx_outfilenamexpath

    namespaces=copy.deepcopy(prx_outfilenamexpath.nsmap)
    if None in namespaces:
        del namespaces[None]  # nsmap param cannot have None
        pass
                             
    
    prx_outfilename= _xmldoc.xpathcontext(_element,prx_outfilenamexpath_doc.getattr(prx_outfilenamexpath,"select"),namespaces=namespaces)

    if not prx_outfilename.endswith(".ods"):
        raise ValueError("Output spreadsheet requires .ods extension")

    ## put in dest dir if present
    #dest=_xmldoc.xpathsingle("dc:summary/dc:dest",default=None,namespaces={"dc": "http://limatix.org/datacollect"} )

    #if dest is None:
        # Put in same directory as _xmldoc
    outdirhref=_xmldoc.getcontexthref().leafless()
    #    pass
    #else:
    #    outdirhref=dc_value.hrefvalue.fromxml(_xmldoc,dest).leafless()
    #    pass
    
        
    prx_outfilehref=dc_value.hrefvalue(quote(prx_outfilename),contexthref=outdirhref) 

    # ods spreadsheet context is a "content.xml" file inside the .ods file interpreted as a directory
    odscontext=dc_value.hrefvalue(quote(prx_outfilename)+"/",contexthref=outdirhref) 
    resultdoc.setcontexthref(dc_value.hrefvalue("content.xml",contexthref=odscontext))  # fix up xlink hrefs
   
    write_output(prx_outfilehref.getpath(),resultdoc.tostring())

    return {linktag: prx_outfilehref}

