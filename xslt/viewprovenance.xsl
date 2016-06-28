<?xml version="1.0" encoding="UTF-8"?>
<!-- viewprovenance.xsl


To apply this stylesheet, either use xsltproc:
xsltproc viewprovenance.xsl xlp_file.xlp > xlp_file_viewprovenance.xhtml

or edit your .xlp file to include an xml-stylesheet line at the top:
<?xml-stylesheet type="text/xsl" href="viewprovenance.xsl"?>
and make sure this file is in the same directory

(if running Chrome/Chromium web browser , run it with the
  - -allow-file-access-from-files command-line parameter) 
  ^^^ remove the space between those hyphens!
-->


<xsl:stylesheet version="1.0"
		xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
		xmlns:html="http://www.w3.org/1999/xhtml"
		xmlns:dcp="http://limatix.org/provenance"
		xmlns:xlink="http://www.w3.org/1999/xlink">
  
  <xsl:output method="xml" media-type="application/xhtml+xml" encoding="utf-8"/>


  <xsl:template match="/">
    <html:html>
      <html:head>
	<html:script language="javascript"><![CDATA[
        function xlinknsresolver(prefix) {
	  var ns={
            'xlink': 'http://www.w3.org/1999/xlink',
	  };
	  return ns[prefix] || null;
	}


	function assert(condition) {
	  if (!condition) {
            throw "Assertion failed";
          }
        }

	function fixupxpointerlinks() {
	  // note: ***!!! contains below should eventually be switched to starts-with!!! ... here and in XSLT below

          var xmlcopydiv=document.getElementsByClassName("viewprovenancexmlcontent")[0];
	  var xmlorigrootnode=document.evaluate("*[1]",xmlcopydiv,null,XPathResult.FIRST_ORDERED_NODE_TYPE,null).singleNodeValue;

	  var xmlcopydocument = document.implementation.createDocument(xmlorigrootnode.namespaceURI, xmlorigrootnode.nodeName, null);

	  // Copy attributes
	  for (var attrnum=0;attrnum < xmlorigrootnode.attributes.length;attrnum++) {
	    var attr=xmlorigrootnode.attributes[attrnum];
            xmlcopydocument.documentElement.setAttributeNS(attr.namespaceURI,attr.name,attr.value);
	  }
	  // Copy children
	  for (var childnum=0;childnum < xmlorigrootnode.children.length;childnum++) {
	    var child=xmlorigrootnode.children[childnum];
	    xmlcopydocument.documentElement.appendChild(xmlcopydocument.importNode(child,true));
	  }

 	  // Now that we've copied it, remove XML tree from main DOM tree so it doesn't mess with us
	  xmlcopydiv.removeChild(xmlorigrootnode);

	  
	  var needylinks=document.evaluate("//*[starts-with(@xlink:href,'#') and contains(@xlink:href,'xpath1(')]",document,xlinknsresolver,XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE,null);

	  /* ***!!! BUG ***!!! This does not correctly handle
	    * Unescaping of carat (^) XPointer escapes -- see xpointer framework
	    * XPointer Methods other than xmlns()/xpath1()
	    * cases where the order within the fragment is not strictly
	    nsmap()nsmap()xpath1() */
	  for (var needylinknum=0; needylinknum < needylinks.snapshotLength;needylinknum++) {
	    var needylink=needylinks.snapshotItem(needylinknum);
	    var anchor=needylink.parentNode;
	    assert(anchor.localName=='a');

	    var xpointerexp=unescape(needylink.getAttributeNS("http://www.w3.org/1999/xlink","href").split("#",2)[1]).trim();


	    // Extract namespace mappings from leading xmlns()
	    var nsmap={};
	    
	    while (xpointerexp.startsWith("xmlns(")) {
              xpointerexp=xpointerexp.substring(6);
	      var equalspos=xpointerexp.indexOf('=');
	      var nspre=xpointerexp.substring(0,equalspos).trim();
	      var parenpos=xpointerexp.indexOf(')');
	      var nsuri=xpointerexp.substring(equalspos+1,parenpos).trim();
	      nsmap[nspre]=nsuri;
              xpointerexp=xpointerexp.substring(parenpos+1).trim();
	      
	    }
	    
	    if (!xpointerexp.startsWith("xpath1(")) {
	      continue;
	    }

	    if (!xpointerexp.endsWith(")")) {
	      continue;
	    }
	    var parenpos=xpointerexp.indexOf(')');
	    var xpath1exp=xpointerexp.substring(7,parenpos).trim();
	    
	    var documentnsresolver=document.createNSResolver(needylink);

	    
	    
	    var pointednode=xmlcopydocument.evaluate(xpath1exp,xmlcopydocument,function(nspre) { return nsmap[nspre] || documentnsresolver(nspre) || null;},XPathResult.FIRST_ORDERED_NODE_TYPE,null).singleNodeValue;
	    var pointednodeid=pointednode.getAttributeNS("http://limatix.org/provenance","vprovid");
	    
	    anchor.setAttribute("href","#xsltid="+pointednodeid);
	    
	  }
	
	}	
]]></html:script>
      </html:head>
      <html:body onload="fixupxpointerlinks()">
	<html:pre>
	  <xsl:apply-templates mode="xml-to-string"/>
	</html:pre>
	<html:div style="display: none;" class="viewprovenancexmlcontent">
	  <!-- Here we include an almost-verbatim copy of the original XML document,
	       with id= attributes set according to the XSLT-generated ids,
	       so that the javascript can look up the ids to generate the
	       correct html fragment link -->
	  <xsl:apply-templates mode="copy-with-ids"/>
	  
	</html:div>
      </html:body>
    </html:html>
  </xsl:template>


  <xsl:template match="@*|processing-instruction()|comment()" mode="copy-with-ids">
    <xsl:copy>
      <xsl:apply-templates select="@*|node()" mode="copy-with-ids"/>
    </xsl:copy>
  </xsl:template>  

  <xsl:template match="*" mode="copy-with-ids">
    <xsl:element name="{name()}">
      <xsl:attribute name="dcp:vprovid"><xsl:value-of select="generate-id()"/></xsl:attribute>
      <xsl:apply-templates select="@*|node()" mode="copy-with-ids"/>
    </xsl:element>
  </xsl:template>  

  
  <xsl:template mode="xml-to-string" match="@dcp:wasgeneratedby|@usedwasgeneratedby">
    <xsl:value-of select="' '"/><html:a>
      <xsl:attribute name="href">#<xsl:value-of select="."/></xsl:attribute>
      <xsl:value-of select="name()"/>="<xsl:value-of select="."/>"</html:a> </xsl:template>
    
  
  <!-- Wrap hrefs with hyperlinks -->
  <xsl:template mode="xml-to-string" match="@xlink:href">
    <xsl:value-of select="' '"/><html:a>
    <xsl:choose>
      <!-- NOTE: ***!!! contains below should eventually be changed to starts-with... here and above -->
      <xsl:when test="starts-with(.,'#') and contains(.,'xpath1(')">
	<!-- intra-document xpointer that will be fixed-up by the Javascript
	     insert xlink:href, though-->
	<xsl:attribute name="xlink:href">
	  <xsl:value-of select="."/>
	</xsl:attribute>
      </xsl:when>
      <xsl:otherwise>
	<!-- regular link.... include verbatim -->	
	<xsl:attribute name="href">
	  <xsl:value-of select="."/>
	</xsl:attribute>
      </xsl:otherwise>
    </xsl:choose>
    <xsl:value-of select="name()"/>="<xsl:value-of select="."/>"</html:a></xsl:template>
    
    <xsl:template mode="xml-to-string" match="@*">
    <xsl:value-of select="' '"/><xsl:value-of select="name()"/>="<xsl:value-of select="."/>"</xsl:template>
  <xsl:template mode="xml-to-string" match="text()"><xsl:value-of select="."/></xsl:template>

  <xsl:template mode="xml-to-string" match="dcp:process"><html:a><xsl:attribute name="name">uuid=<xsl:value-of select="@uuid"/>;</xsl:attribute>&lt;<xsl:value-of select="name()"/><xsl:apply-templates mode="xml-to-string" select="@*"/>&gt;</html:a><xsl:apply-templates mode="xml-to-string" select="*|text()"/>&lt;/<xsl:value-of select="name()"/>&gt;</xsl:template>

  
  <xsl:template mode="xml-to-string" match="*"><html:a><xsl:attribute name="name">xsltid=<xsl:value-of select="generate-id()"/></xsl:attribute>&lt;<xsl:value-of select="name()"/><xsl:apply-templates mode="xml-to-string" select="@*"/>&gt;</html:a><xsl:apply-templates mode="xml-to-string" select="*|text()"/>&lt;/<xsl:value-of select="name()"/>&gt;</xsl:template>

    


</xsl:stylesheet>

  


