<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:dir="http://doc.s3.amazonaws.com/2006-03-01">
<xsl:output method="text"/>
<xsl:strip-space elements="*"/>

<xsl:template match="/">
	<xsl:apply-templates select="dir:ListBucketResult"/>
</xsl:template>

<xsl:template match="dir:ListBucketResult">
	<xsl:for-each select="dir:CommonPrefixes">
		<xsl:value-of select="substring-after(dir:Prefix, $listing_path)"/>
		<xsl:text>&#xa;</xsl:text>
        </xsl:for-each>
	<xsl:for-each select="dir:Contents">
		<xsl:value-of select="substring-after(dir:Key, $listing_path)"/>
		<xsl:text>&#xa;</xsl:text>
	</xsl:for-each>
	<xsl:if test="dir:IsTruncated='true'">
                <xsl:text>&#62;</xsl:text>
		<xsl:value-of select="dir:NextMarker"/>
                <xsl:text>&#xa;</xsl:text>
        </xsl:if>
</xsl:template>

</xsl:stylesheet>
