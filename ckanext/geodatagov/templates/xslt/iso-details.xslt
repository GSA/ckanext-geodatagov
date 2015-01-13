<?xml version="1.0" encoding="UTF-8"?>
<!--

 This file was adapted originally from Esri Geoportal Server source code.
 Changes:
    * Allow standalone rendering (create a complete HTML file)
    * Support both gmd:MD_Metadata and gmi:MI_Metadata
    * Define properties in file

 =====================================================
 ESRI Geoportal Server
 Copyright ©2010 Esri. 
 =====================================================

 This product was created based on contributions from Esri, Inc for the Geoportal, Ontology Service, CSW clients, Publishing Client, Flex Widget, Silverlight Widget, and OpenLS Connector.

  

 This product includes software developed at

 Esri. (http://www.esri.com/).
 =====================================================


 See the NOTICE file distributed with
 this work for additional information regarding copyright ownership.
 Esri Inc. licenses this file to You under the Apache License, Version 2.0
 (the "License"); you may not use this file except in compliance with
 the License.  You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
-->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:gml="http://www.opengis.net/gml" 
    xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco" xmlns:srv="http://www.isotc211.org/2005/srv"
    xmlns:gmi="http://www.isotc211.org/2005/gmi">
    <xsl:output indent="yes" method="html" omit-xml-declaration="yes"/>
    <xsl:template match="/">
        <html>
            <head>
                <style>
                    .iso_section_title {font-family: Verdana, Arial, Helvetica, sans-serif; font-size: 12pt; font-weight: bold; color: #333333}
                    .iso_body {font-family: Verdana, Arial, Helvetica, sans-serif; font-size: 10pt; line-height: 16pt; color: #333333}
                    .iso_body .toolbarTitle {font-family: Verdana, Arial, Helvetica, sans-serif; font-size: 14pt; color: #333333; margin:0px;}
                    .iso_body .headTitle {  font-family: Verdana, Arial, Helvetica, sans-serif; font-size: 11pt; color: #333333; font-weight: bold}
                    .iso_body dl {margin-left: 20px;}
                    .iso_body em {font-family: Verdana, Arial, Helvetica, sans-serif; font-size: 10pt; font-weight: bold; color: #333333}
                    .iso_body a:link {color: #B66B36; text-decoration: underline}
                    .iso_body a:visited {color: #B66B36; text-decoration: underline}
                    .iso_body a:hover {color: #4E6816; text-decoration: underline}
                    .iso_body li {font-family: Verdana, Arial, Helvetica, sans-serif; font-size: 10pt; line-height: 14pt; color: #333333}
                    hr { background-color: #CCCCCC; border: 0 none; height: 1px; }
                </style>
                <script type="text/javascript">
                    var mdeEnvelopeIds = new Array('envelope_west','envelope_south','envelope_east','envelope_north');
                </script>
            </head>
            <body>
                <xsl:variable name="root" select="/gmd:MD_Metadata | /gmi:MI_Metadata" />
                <div class="iso_body">
                    <xsl:call-template name="Page_Title">
                        <xsl:with-param name="root" select="$root" />
                    </xsl:call-template>
                    <xsl:call-template name="Metadata_Info">
                        <xsl:with-param name="root" select="$root" />
                    </xsl:call-template>

                    <xsl:call-template name="Identification_Info">		
                        <xsl:with-param name="root" select="$root" />
                    </xsl:call-template>

                    <xsl:if test="$root/gmd:distributionInfo">
                        <xsl:call-template name="Distribution_Info">
                            <xsl:with-param name="root" select="$root" />
                        </xsl:call-template>
                    </xsl:if>
                    <xsl:if test="$root/gmd:dataQualityInfo">					
                        <xsl:call-template name="Data_Quality_Info">
                            <xsl:with-param name="root" select="$root" />
                        </xsl:call-template>
                    </xsl:if>
                </div>
            </body>
        </html>
	</xsl:template>

	<xsl:template name="Page_Title">
            <xsl:param name="root" />
		<h1 class="toolbarTitle"><xsl:value-of select="$root/gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString | $root/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString"/></h1>
		<hr/>
	</xsl:template>
	
	<xsl:template name="Metadata_Info" >
            <xsl:param name="root" />
		<div class="iso_section_title"><xsl:call-template name="get_property"><xsl:with-param name="key">catalog.iso19139.MD_Metadata.section.metadata</xsl:with-param></xsl:call-template></div>
		<dl>

			<xsl:for-each select="$root/gmd:fileIdentifier">				
			<dt>
				<em><xsl:call-template name="get_property"><xsl:with-param name="key">catalog.iso19139.MD_Metadata.<xsl:value-of select="local-name()" /></xsl:with-param></xsl:call-template>: </em>
				<xsl:value-of select="$root/gmd:fileIdentifier/gco:CharacterString"/>
			</dt>
			</xsl:for-each>
			<xsl:if test="$root/gmd:language">				
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.MD_Metadata.<xsl:value-of select="local-name($root/gmd:language)" /></xsl:with-param>
				</xsl:call-template>: </em>
				<xsl:choose>
					<xsl:when test=" string-length($root/gmd:language/gmd:LanguageCode/@codeListValue) > 0">
							<xsl:call-template name="get_property">
								<xsl:with-param name="key">catalog.mdCode.language.iso639_2.<xsl:value-of select="$root/gmd:language/gmd:LanguageCode/@codeListValue" /></xsl:with-param>
							</xsl:call-template>
					</xsl:when>
					<xsl:otherwise>
						<xsl:value-of select="$root/gmd:language/gco:CharacterString"/>
					</xsl:otherwise>
				</xsl:choose>
			</dt>
			</xsl:if>
			<xsl:if test="$root/gmd:characterSet">				
			<dt>
				<em>						
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.MD_Metadata.<xsl:value-of select="local-name($root/gmd:characterSet)" />: </xsl:with-param>
				</xsl:call-template>: </em>
				<xsl:value-of select="$root/gmd:characterSet"/>
			</dt>
			</xsl:if>
			<xsl:if test="$root/gmd:parentIdentifier">				
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.MD_Metadata.<xsl:value-of select="local-name($root/gmd:parentIdentifier)" /></xsl:with-param>
				</xsl:call-template>: </em>
				<xsl:value-of select="$root/gmd:parentIdentifier/gco:CharacterString"/>
			</dt>
			</xsl:if>
			<xsl:if test="$root/gmd:hierarchyLevel/gmd:MD_ScopeCode">			
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.gemini.MD_Metadata.hierarchyLevel</xsl:with-param>
				</xsl:call-template>: </em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.<xsl:value-of select="local-name($root/gmd:hierarchyLevel/gmd:MD_ScopeCode)" />.<xsl:value-of select="$root/gmd:hierarchyLevel/gmd:MD_ScopeCode/@codeListValue" />
				</xsl:with-param>
				</xsl:call-template>						
			</dt>
			</xsl:if>

			<xsl:for-each select="$root/gmd:contact">			
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_ResponsibleParty</xsl:with-param>
				</xsl:call-template>: </em>
				<xsl:apply-templates select="gmd:CI_ResponsibleParty"/>							
			</dt>
			</xsl:for-each>
			
							
			<xsl:if test="$root/gmd:dateStamp">			
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.MD_Metadata.<xsl:value-of select="local-name($root/gmd:dateStamp)" /></xsl:with-param>
				</xsl:call-template>: </em>
				<xsl:value-of select="$root/gmd:dateStamp/gco:Date"/>
			</dt>
			</xsl:if>	
			<xsl:if test="$root/gmd:metadataStandardName">			
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.MD_Metadata.<xsl:value-of select="local-name($root/gmd:metadataStandardName)" /></xsl:with-param>
				</xsl:call-template>: </em>
				<xsl:value-of select="$root/gmd:metadataStandardName/gco:CharacterString"/>
			</dt>
			</xsl:if>	
			<xsl:if test="$root/gmd:metadataStandardVersion">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.MD_Metadata.<xsl:value-of select="local-name($root/gmd:metadataStandardVersion)" /></xsl:with-param>
				</xsl:call-template>: </em>
				<xsl:value-of select="$root/gmd:metadataStandardVersion/gco:CharacterString"/>
			</dt>
			</xsl:if>
		</dl>	
	</xsl:template>
	
	<xsl:template name="Identification_Info" >
            <xsl:param name="root" />
		<xsl:for-each select="$root/gmd:identificationInfo">
			<xsl:if test="gmd:MD_DataIdentification">
				<div class="iso_section_title"><xsl:call-template name="get_property"><xsl:with-param name="key">catalog.iso19139.MD_Metadata.MD_DataIdentification</xsl:with-param></xsl:call-template></div>
				<xsl:apply-templates select="gmd:MD_DataIdentification"/>
			</xsl:if>
			<xsl:if test="srv:SV_ServiceIdentification">
			    <div class="iso_section_title"><xsl:call-template name="get_property"><xsl:with-param name="key">catalog.iso19139.MD_Metadata.MD_ServiceIdentification</xsl:with-param></xsl:call-template></div> 
				<xsl:apply-templates select="srv:SV_ServiceIdentification"/>		
			</xsl:if>	
		</xsl:for-each>
	</xsl:template>

	<xsl:template match="gmd:MD_DataIdentification | srv:SV_ServiceIdentification">	
		<dl>
			<xsl:for-each select="gmd:abstract">			
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.AbstractMD_Identification.<xsl:value-of select="local-name()" /></xsl:with-param>
				</xsl:call-template>: </em>					
				<xsl:value-of select="gco:CharacterString"/>
			</dt>
			</xsl:for-each>
			<xsl:for-each select="gmd:purpose">			
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.AbstractMD_Identification.<xsl:value-of select="local-name()" /></xsl:with-param>
				</xsl:call-template>: </em>							
				<xsl:value-of select="gco:CharacterString"/>
			</dt>
			</xsl:for-each>							
			<xsl:for-each select="gmd:language">			
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.MD_DataIdentification.<xsl:value-of select="local-name()" /></xsl:with-param>
				</xsl:call-template>: </em>						
				<xsl:choose>
					<xsl:when test=" string-length(gmd:LanguageCode/@codeListValue) > 0">
							<xsl:call-template name="get_property">
								<xsl:with-param name="key">catalog.mdCode.language.iso639_2.<xsl:value-of select="gmd:LanguageCode/@codeListValue" /></xsl:with-param>
							</xsl:call-template>
					</xsl:when>
					<xsl:otherwise>
						<xsl:value-of select="gco:CharacterString"/>
					</xsl:otherwise>
				</xsl:choose>				
			</dt>
			</xsl:for-each>	
			<xsl:if test="gmd:graphicOverview">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.MD_Metadata.section.identification.graphicOverview</xsl:with-param>
				</xsl:call-template>: </em>								
			</dt>
			<dt>
				<xsl:apply-templates select="gmd:graphicOverview/gmd:MD_BrowseGraphic"/>
			</dt>					
			</xsl:if>						
			<xsl:if test="gmd:citation">

			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_Citation</xsl:with-param>
				</xsl:call-template>: </em>
			</dt>

			<dt>
				<xsl:apply-templates select="gmd:citation/gmd:CI_Citation"/>
			</dt>
			</xsl:if>
			<xsl:if test="gmd:pointOfContact">			
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.AbstractMD_Identification.pointOfContact</xsl:with-param>
				</xsl:call-template>: </em>						
			</dt>					
			<dt>
				<xsl:apply-templates select="gmd:pointOfContact/gmd:CI_ResponsibleParty"/>
			</dt>
			</xsl:if>
			<xsl:if test="gmd:spatialRepresentationType/gmd:MD_SpatialRepresentationTypeCode/@codeListValue">			
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.MD_DataIdentification.spatialRepresentationType</xsl:with-param>
				</xsl:call-template>: </em>							
				
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.MD_SpatialRepresentationTypeCode.<xsl:value-of select="gmd:spatialRepresentationType/gmd:MD_SpatialRepresentationTypeCode/@codeListValue" /></xsl:with-param>
				</xsl:call-template>						
			</dt>
			</xsl:if>	
			<xsl:if test="gmd:spatialResolution/gmd:MD_Resolution/gmd:equivalentScale">			
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.MD_Resolution.equivalentScale</xsl:with-param>
				</xsl:call-template>: </em>						
				<xsl:text>1:</xsl:text><xsl:value-of select="gmd:spatialResolution/gmd:MD_Resolution/gmd:equivalentScale"/>
			</dt>
			</xsl:if>	
			<xsl:if test="gmd:topicCategory/gmd:MD_TopicCategoryCode">			
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.MD_DataIdentification.topicCategory</xsl:with-param>
				</xsl:call-template>: </em>
				
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.MD_TopicCategoryCode.<xsl:value-of select="gmd:topicCategory/gmd:MD_TopicCategoryCode"/></xsl:with-param>
				</xsl:call-template>
			</dt>
			</xsl:if>
			<xsl:if test="gmd:descriptiveKeywords">			
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.AbstractMD_Identification.descriptiveKeywords</xsl:with-param>
				</xsl:call-template>: </em>						
			</dt>
			<dt>
				<xsl:apply-templates select="gmd:descriptiveKeywords/gmd:MD_Keywords"/>
			</dt>
			</xsl:if>					
			<xsl:if test="gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox">			
			<dt> 
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.MD_Metadata.section.identification.extent.geographicElement</xsl:with-param>
				</xsl:call-template>: </em>						
			</dt>
			<dt>
        <xsl:apply-templates select="gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox"/></dt>							
			<dt>
				<div id="interactiveMap" style="width:600px; height:300px; cursor:hand; cursor:pointer; margin: 20px;"></div>
			</dt>
			</xsl:if>
			<xsl:if test="srv:serviceType/gco:LocalName">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.SV_ServiceIdentification.serviceType</xsl:with-param>
				</xsl:call-template>: </em>
				<xsl:value-of select="srv:serviceType/gco:LocalName"/>
			</dt>					
			</xsl:if>
			<xsl:for-each select="srv:serviceTypeVersion/gco:CharacterString">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.SV_ServiceIdentification.serviceTypeVersion</xsl:with-param>
				</xsl:call-template>: </em>
				<xsl:value-of select="."/>
			</dt>					
			</xsl:for-each>
			<xsl:if test="srv:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox">			
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.SV_ServiceIdentification.extent</xsl:with-param>
				</xsl:call-template>: </em>
			</dt>
			<dt>
		        <xsl:apply-templates select="srv:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox"/>
			</dt>
			<dt>
				<div id="interactiveMap" style="width:600px; height:300px; cursor:hand; cursor:pointer; margin: 20px;"></div>
			</dt>       
			</xsl:if>					
			<xsl:for-each select="srv:containsOperations/srv:SV_OperationMetadata">			
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.SV_Operation</xsl:with-param>
				</xsl:call-template>: </em>		
			</dt>
			<dt>
				<xsl:apply-templates select="."/>
			</dt>
			</xsl:for-each>
			<xsl:for-each select="gmd:resourceConstraints/gmd:MD_Constraints">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.MD_Metadata.section.identification.resourceConstraints</xsl:with-param>
				</xsl:call-template>: </em>
				<xsl:value-of select="gmd:useLimitation/gco:CharacterString"/>
			</dt>
			</xsl:for-each>
			<xsl:for-each select="gmd:resourceConstraints/gmd:MD_LegalConstraints">
					<dt>
						<em>
						<xsl:call-template name="get_property">
						<xsl:with-param name="key">catalog.iso19139.MD_LegalConstraints</xsl:with-param>
						</xsl:call-template>: </em>
					</dt>
					<dt>
						<xsl:apply-templates select="."/>
					</dt>
			</xsl:for-each>
			<xsl:for-each select="gmd:resourceConstraints/gmd:MD_SecurityConstraints">
					<dt>
						<em>
						<xsl:call-template name="get_property">
						<xsl:with-param name="key">catalog.iso19139.MD_SecurityConstraints</xsl:with-param>
						</xsl:call-template>: </em>							
					</dt>
					<dt>
						<xsl:apply-templates select="."/>
					</dt>
			</xsl:for-each>					
		</dl>
	</xsl:template>	

	<xsl:template match="gmd:citedResponsibleParty/gmd:CI_ResponsibleParty | gmd:pointOfContact/gmd:CI_ResponsibleParty | gmd:CI_ResponsibleParty">
		<dl>
			<xsl:for-each select="gmd:individualName">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_ResponsibleParty.<xsl:value-of select="local-name()"/></xsl:with-param>
				</xsl:call-template>: </em>						
				<xsl:value-of select="gco:CharacterString"/>
			</dt>
			</xsl:for-each>
			<xsl:for-each select="gmd:organisationName">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_ResponsibleParty.<xsl:value-of select="local-name()"/></xsl:with-param>
				</xsl:call-template>: </em>
				<xsl:value-of select="gco:CharacterString"/>
			</dt>
			</xsl:for-each>
			<xsl:for-each select="gmd:positionName">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_ResponsibleParty.<xsl:value-of select="local-name()"/></xsl:with-param>
				</xsl:call-template>: </em>
				<xsl:value-of select="gco:CharacterString"/>
			</dt>
			</xsl:for-each>		
			<xsl:for-each select="gmd:role">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_ResponsibleParty.<xsl:value-of select="local-name()"/></xsl:with-param>
				</xsl:call-template>: </em>
				
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_RoleCode.<xsl:value-of select="gmd:CI_RoleCode/@codeListValue"/></xsl:with-param>
				</xsl:call-template>
									
			</dt>
			</xsl:for-each>		
			<xsl:for-each select="gmd:contactInfo">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_ResponsibleParty.contactInfo</xsl:with-param>
				</xsl:call-template>: </em>					
					
					<xsl:apply-templates select="gmd:CI_Contact"/>
				
			</dt>
			</xsl:for-each>										
		</dl>
	</xsl:template>

	<xsl:template match="gmd:citation/gmd:CI_Citation | gmd:specification/gmd:CI_Citation">
		<dl>
			<xsl:for-each select="gmd:title">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_Citation.<xsl:value-of select="local-name()"/></xsl:with-param>
				</xsl:call-template>: </em>						
				<xsl:value-of select="gco:CharacterString"/>
			</dt>
			</xsl:for-each>
			<xsl:for-each select="gmd:alternateTitle">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_Citation.<xsl:value-of select="local-name()"/></xsl:with-param>
				</xsl:call-template>: </em>
				<xsl:value-of select="gco:CharacterString"/>
			</dt>
			</xsl:for-each>
			<xsl:for-each select="gmd:date">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_Citation.<xsl:value-of select="local-name()"/></xsl:with-param>
				</xsl:call-template>: </em>
			</dt>
			<dt>
				<xsl:apply-templates select="gmd:CI_Date"/>
			</dt>
			</xsl:for-each>												
			<xsl:for-each select="gmd:edition">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_Citation.<xsl:value-of select="local-name()"/></xsl:with-param>
				</xsl:call-template>: </em>
				<xsl:value-of select="gco:CharacterString"/>
			</dt>
			</xsl:for-each>	
			<xsl:for-each select="gmd:editionDate">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_Citation.<xsl:value-of select="local-name()"/></xsl:with-param>
				</xsl:call-template>: </em>
				<xsl:value-of select="gco:Date"/>
			</dt>
			</xsl:for-each>
			<xsl:for-each select="gmd:identifier">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_Citation.<xsl:value-of select="local-name()"/></xsl:with-param>
				</xsl:call-template>: </em>
				<xsl:apply-templates select="gmd:MD_Identifier/gmd:code/gco:CharacterString"/>
			</dt>
			</xsl:for-each>
			<xsl:if test="gmd:citedResponsibleParty">
			<dt>
					<xsl:apply-templates select="gmd:citedResponsibleParty/gmd:CI_ResponsibleParty"/>
			</dt>
			</xsl:if>				
		</dl>
	</xsl:template>

	<xsl:template match="gmd:CI_Date">
		<dl>
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_Date.date</xsl:with-param>
				</xsl:call-template>: </em>
				<xsl:value-of select="gmd:date/gco:Date"/>
			</dt>
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_Date.dateType</xsl:with-param>
				</xsl:call-template>: </em>
				
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_DateTypeCode.<xsl:value-of select="gmd:dateType/gmd:CI_DateTypeCode/@codeListValue"/></xsl:with-param>
				</xsl:call-template>
			</dt>
		</dl>
	</xsl:template>

	<xsl:template match="gmd:contactInfo/gmd:CI_Contact | gmd:CI_Contact">
		<dl>
			<xsl:if test="gmd:phone/gmd:CI_Telephone/gmd:voice">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_Telephone.voice</xsl:with-param>
				</xsl:call-template>: </em>					
				<xsl:value-of select="gmd:phone/gmd:CI_Telephone/gmd:voice/gco:CharacterString"/>
			</dt>
			</xsl:if>
			<xsl:if test="gmd:phone/gmd:CI_Telephone/gmd:facsimile">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_Telephone.facsimile</xsl:with-param>
				</xsl:call-template>: </em>								
				<xsl:value-of select="gmd:phone/gmd:CI_Telephone/gmd:facsimile/gco:CharacterString"/>
			</dt>
			</xsl:if>				
			<xsl:if test="gmd:address/gmd:CI_Address/gmd:deliveryPoint">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_Address.deliveryPoint</xsl:with-param>
				</xsl:call-template>: </em>						
				<xsl:value-of select="gmd:address/gmd:CI_Address/gmd:deliveryPoint"/>
			</dt>
			</xsl:if>
			<xsl:if test="gmd:address/gmd:CI_Address/gmd:city">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_Address.city</xsl:with-param>
				</xsl:call-template>: </em>							
				<xsl:value-of select="gmd:address/gmd:CI_Address/gmd:city"/>
			</dt>
			</xsl:if>					
			<xsl:if test="gmd:address/gmd:CI_Address/gmd:administrativeArea">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_Address.administrativeArea</xsl:with-param>
				</xsl:call-template>: </em>						
				<xsl:value-of select="gmd:address/gmd:CI_Address/gmd:administrativeArea"/>
			</dt>
			</xsl:if>		
			<xsl:if test="gmd:address/gmd:CI_Address/gmd:postalCode">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_Address.postalCode</xsl:with-param>
				</xsl:call-template>: </em>						
				<xsl:value-of select="gmd:address/gmd:CI_Address/gmd:postalCode"/>
			</dt>
			</xsl:if>												
			<xsl:if test="gmd:address/gmd:CI_Address/gmd:country">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_Address.country</xsl:with-param>
				</xsl:call-template>: </em>		
				<xsl:value-of select="gmd:address/gmd:CI_Address/gmd:country"/>
			</dt>
			</xsl:if>			
			<xsl:if test="gmd:address/gmd:CI_Address/gmd:electronicMailAddress">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_Address.electronicMailAddress</xsl:with-param>
				</xsl:call-template>: </em>							
				<a >
					<xsl:attribute name="href">mailto:<xsl:value-of select="gmd:address/gmd:CI_Address/gmd:electronicMailAddress"/></xsl:attribute>
					<xsl:value-of select="gmd:address/gmd:CI_Address/gmd:electronicMailAddress"/>
				</a>
			</dt>
			</xsl:if>	
			<xsl:if test="gmd:onlineResource">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.CI_Contact.onlineResource</xsl:with-param>
				</xsl:call-template>: </em>							
				
					<a >
						<xsl:attribute name="href"><xsl:value-of select="gmd:onlineResource/gmd:CI_OnlineResource/gmd:linkage/gmd:URL"/></xsl:attribute>
						<xsl:value-of select="gmd:onlineResource/gmd:CI_OnlineResource/gmd:linkage/gmd:URL"/>
					</a>
					
			</dt>
			</xsl:if>						
		</dl>
	</xsl:template>

	<xsl:template match="gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox | srv:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox">
		<dl>
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.EX_GeographicBoundingBox.westBoundLongitude</xsl:with-param>
				</xsl:call-template>: </em>
				<span id="mdDetails:envelope_west"><xsl:value-of select="gmd:westBoundLongitude/gco:Decimal"/></span>
			</dt>		
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.EX_GeographicBoundingBox.eastBoundLongitude</xsl:with-param>
				</xsl:call-template>: </em>							
				<span id="mdDetails:envelope_east"><xsl:value-of select="gmd:eastBoundLongitude/gco:Decimal"/></span>
			</dt>	
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.EX_GeographicBoundingBox.northBoundLatitude</xsl:with-param>
				</xsl:call-template>: </em>			
				<span id="mdDetails:envelope_north"><xsl:value-of select="gmd:northBoundLatitude/gco:Decimal"/></span>
			</dt>						
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.EX_GeographicBoundingBox.southBoundLatitude</xsl:with-param>
				</xsl:call-template>: </em>							
				<span id="mdDetails:envelope_south"><xsl:value-of select="gmd:southBoundLatitude/gco:Decimal"/></span>
			</dt>	
		</dl>
	</xsl:template>

	<xsl:template match="gmd:descriptiveKeywords/gmd:MD_Keywords">
		<dl>
			<xsl:for-each select="gmd:keyword/gco:CharacterString">			
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.MD_Keywords.keyword</xsl:with-param>
				</xsl:call-template>: </em>							
				<xsl:value-of select="."/>
			</dt>
			</xsl:for-each>
			<xsl:if test="gmd:thesaurusName/gmd:CI_Citation/gmd:title/gco:CharacterString">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.MD_Keywords.thesaurusName</xsl:with-param>
				</xsl:call-template>: </em>						
				<xsl:value-of select="gmd:thesaurusName/gmd:CI_Citation/gmd:title/gco:CharacterString"/>
			</dt>
			</xsl:if>
		</dl>
	</xsl:template>	
	
	<xsl:template match="gmd:MD_LegalConstraints | gmd:resourceConstraints/gmd:MD_LegalConstraints">
		<dl>
			<xsl:if test="gmd:accessConstraints">
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.MD_LegalConstraints.accessConstraints</xsl:with-param>
					</xsl:call-template>: </em>	
					
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.MD_RestrictionCode.<xsl:value-of select="gmd:accessConstraints/gmd:MD_RestrictionCode/@codeListValue"/></xsl:with-param>
					</xsl:call-template>
				</dt>
			</xsl:if>						
			<xsl:if test="gmd:useConstraints">
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.MD_LegalConstraints.useConstraints</xsl:with-param>
					</xsl:call-template>: </em>							
					
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.MD_RestrictionCode.<xsl:value-of select="gmd:useConstraints/gmd:MD_RestrictionCode/@codeListValue"/></xsl:with-param>
					</xsl:call-template>
				</dt>
			</xsl:if>
			<xsl:if test="gmd:otherConstraints">
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.MD_LegalConstraints.otherConstraints</xsl:with-param>
					</xsl:call-template>: </em>							
					<xsl:value-of select="gmd:otherConstraints/gco:CharacterString"/>						
				</dt>
			</xsl:if>
		</dl>
	</xsl:template>	

	<xsl:template match="gmd:MD_SecurityConstraints">
		<dl>
			<xsl:if test="gmd:classification">
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.MD_SecurityConstraints.classification</xsl:with-param>
					</xsl:call-template>: </em>								
					<xsl:value-of select="gmd:classification/gmd:MD_ClassificationCode/@codeListValue"/>
				</dt>
			</xsl:if>						
			<xsl:if test="gmd:userNote">
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.MD_SecurityConstraints.userNote</xsl:with-param>
					</xsl:call-template>: </em>								
					<xsl:value-of select="gmd:userNote/gco:CharacterString"/>
				</dt>
			</xsl:if>
			<xsl:if test="gmd:classificationSystem">
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.MD_SecurityConstraints.classificationSystem</xsl:with-param>
					</xsl:call-template>: </em>							
					<xsl:value-of select="gmd:classificationSystem/gco:CharacterString"/>
				</dt>
			</xsl:if>
			<xsl:if test="gmd:handlingDescription">
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.MD_SecurityConstraints.handlingDescription</xsl:with-param>
					</xsl:call-template>: </em>								
					<xsl:value-of select="gmd:handlingDescription/gco:CharacterString"/>
				</dt>
			</xsl:if>
		</dl>
	</xsl:template>		

	<xsl:template name="Distribution_Info" >
        <xsl:param name="root" />
		<div class="iso_section_title"><xsl:call-template name="get_property"><xsl:with-param name="key">catalog.iso19139.MD_Distribution</xsl:with-param></xsl:call-template></div>
		<dl>
			<xsl:for-each select="$root/gmd:distributionInfo/gmd:MD_Distribution/gmd:distributionFormat"	>
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.MD_Distribution.distributionFormat</xsl:with-param>
					</xsl:call-template>: </em>		
				</dt>
				<dt>
					<xsl:apply-templates select="."/>
				</dt>
			</xsl:for-each>
			<xsl:for-each select="$root/gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine"	>
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.MD_Distribution.transferOptions</xsl:with-param>
					</xsl:call-template>: </em>								
				</dt>
				<dt>
					<xsl:apply-templates select="gmd:CI_OnlineResource"/>
				</dt>
			</xsl:for-each>
			<xsl:for-each select="$root/gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor"	>
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.MD_Distribution.distributor</xsl:with-param>
					</xsl:call-template>: </em>								
				</dt>
				<dt>
					<xsl:apply-templates select="."/>
				</dt>
			</xsl:for-each>					
		</dl>
	</xsl:template>
	
	<xsl:template name="Data_Quality_Info" >
        <xsl:param name="root" />
		<div class="iso_section_title"><xsl:call-template name="get_property"><xsl:with-param name="key">catalog.iso19139.MD_Metadata.dataQualityInfo</xsl:with-param></xsl:call-template></div>
		<dl>
			<xsl:if test="$root/gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:scope/gmd:DQ_Scope/gmd:level/gmd:MD_ScopeCode">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.DQ_DataQuality.scope</xsl:with-param>
				</xsl:call-template>: </em>								
				
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.MD_ScopeCode.<xsl:value-of select="$root/gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:scope/gmd:DQ_Scope/gmd:level/gmd:MD_ScopeCode/@codeListValue"/></xsl:with-param>
				</xsl:call-template>						
			</dt>
			</xsl:if>
			<xsl:for-each select="$root/gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/*/gmd:result">
				<xsl:if test="gmd:DQ_ConformanceResult">
					<dt>
						<em>
						<xsl:call-template name="get_property">
						<xsl:with-param name="key">catalog.iso19139.DQ_ConformanceResult</xsl:with-param>
						</xsl:call-template>: </em>									
					</dt>
					<dt>
						<xsl:apply-templates select="gmd:DQ_ConformanceResult"/>
					</dt>
				</xsl:if>
			</xsl:for-each>
			<xsl:for-each select="$root/gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:statement">
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.DQ_DataQuality.lineage</xsl:with-param>
					</xsl:call-template>: </em>	
					<xsl:value-of select="$root/gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:statement/gco:CharacterString"/>
				</dt>
			</xsl:for-each>					
		</dl>
	</xsl:template>

	<xsl:template match="gmd:DQ_ConformanceResult">
		<dl>
			<xsl:if test="gmd:pass">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.DQ_ConformanceResult.pass.Boolean</xsl:with-param>
				</xsl:call-template>: </em>							
				<xsl:value-of select="gmd:pass"/>
			</dt>
			</xsl:if>
			<xsl:if test="gmd:explanation">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.DQ_ConformanceResult.explanation</xsl:with-param>
				</xsl:call-template>: </em>							
				<xsl:value-of select="gmd:explanation/gco:CharacterString"/>
			</dt>
			</xsl:if>
			<xsl:if test="gmd:specification">
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.DQ_ConformanceResult.specification</xsl:with-param>
				</xsl:call-template>: </em>							
			</dt>
			<dt>
				<xsl:apply-templates select="gmd:specification/gmd:CI_Citation"/>
			</dt>					
			</xsl:if>					
		</dl>
	</xsl:template>	

    <!-- TODO -->
	<xsl:template match="gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor">
		<dl>
			<xsl:for-each select="gmd:MD_Distributor/gmd:distributorFormat">
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.MD_Distributor.distributorFormat</xsl:with-param>
					</xsl:call-template>: </em>							
				</dt>
				<dt>
					<xsl:apply-templates select="."/>
				</dt>	
			</xsl:for-each>
			<xsl:for-each select="gmd:MD_Distributor/gmd:distributorTransferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine">
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.CI_OnlineResource</xsl:with-param>
					</xsl:call-template>: </em>					
				</dt>
				<dt>
					<xsl:apply-templates select="gmd:CI_OnlineResource"/>
				</dt>	
			</xsl:for-each>
			<xsl:for-each select="gmd:MD_Distributor/gmd:distributorContact">
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.MD_Distributor.distributorContact</xsl:with-param>
					</xsl:call-template>: </em>					
				</dt>
				<dt>
					<xsl:apply-templates select="gmd:CI_ResponsibleParty"/>
				</dt>	
			</xsl:for-each>							
		</dl>
	</xsl:template>

	<xsl:template match="gmd:CI_OnlineResource | srv:connectPoint/gmd:CI_OnlineResource">
		<dl>
			<xsl:if test="gmd:linkage/gmd:URL">
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.CI_OnlineResource.linkage</xsl:with-param>
					</xsl:call-template>: </em>							
					
						<a>
						<xsl:attribute name="href"><xsl:value-of select="gmd:linkage/gmd:URL"/></xsl:attribute>
						<xsl:value-of select="gmd:linkage/gmd:URL"/>
						</a>
					
				</dt>						
			</xsl:if>
			<xsl:for-each select="gmd:protocol">
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.CI_OnlineResource.protocol</xsl:with-param>
					</xsl:call-template>: </em>								
					<xsl:value-of select="gmd:protocol"/>
				</dt>						
			</xsl:for-each>
			<xsl:for-each select="gmd:applicationProfile">
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.CI_OnlineResource.applicationProfile</xsl:with-param>
					</xsl:call-template>: </em>								
					<xsl:value-of select="gmd:applicationProfile"/>
				</dt>						
			</xsl:for-each>
			<xsl:for-each select="gmd:name">
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.CI_OnlineResource.name</xsl:with-param>
					</xsl:call-template>: </em>								
					<xsl:value-of select="gmd:name"/>
				</dt>						
			</xsl:for-each>					
			<xsl:for-each select="gmd:description">
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.CI_OnlineResource.description</xsl:with-param>
					</xsl:call-template>: </em>								
					<xsl:value-of select="gmd:description"/>
				</dt>						
			</xsl:for-each>						
			<xsl:for-each select="gmd:function">
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.CI_OnlineResource.function</xsl:with-param>
					</xsl:call-template>: </em>								
					
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.CI_OnLineFunctionCode.<xsl:value-of select="gmd:CI_OnLineFunctionCode/@codeListValue"/></xsl:with-param>
					</xsl:call-template>							
				</dt>						
			</xsl:for-each>		
		</dl>
	</xsl:template>

    <!-- TODO -->
	<xsl:template match="gmd:distributionInfo/gmd:MD_Distribution/gmd:distributionFormat">
		<dl>
			<xsl:if test="gmd:MD_Format/gmd:name">
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.MD_Format.name</xsl:with-param>
					</xsl:call-template>: </em>		
					<xsl:value-of select="gmd:MD_Format/gmd:name"/>
				</dt>					
			</xsl:if>
			<xsl:if test="gmd:MD_Format/gmd:version">
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.MD_Format.version</xsl:with-param>
					</xsl:call-template>: </em>								
					<xsl:value-of select="gmd:MD_Format/gmd:version"/>
				</dt>							
			</xsl:if>
			<xsl:if test="gmd:MD_Format/gmd:amendmentNumber">
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.MD_Format.amendmentNumber</xsl:with-param>
					</xsl:call-template>: </em>								
					<xsl:value-of select="gmd:MD_Format/gmd:amendmentNumber"/>
				</dt>							
			</xsl:if>
			<xsl:if test="gmd:MD_Format/gmd:specification">
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.MD_Format.specification</xsl:with-param>
					</xsl:call-template>: </em>								
					<xsl:value-of select="gmd:MD_Format/gmd:specification"/>
				</dt>						
			</xsl:if>			
			<xsl:if test="gmd:MD_Format/gmd:fileDecompressionTechnique">
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.MD_Format.fileDecompressionTechnique</xsl:with-param>
					</xsl:call-template>: </em>								
					<xsl:value-of select="gmd:MD_Format/gmd:fileDecompressionTechnique"/>
				</dt>	
			</xsl:if>
			<xsl:if test="gmd:MD_Format/gmd:formatDistributor">
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.MD_Format.formatDistributor</xsl:with-param>
					</xsl:call-template>: </em>								
					<xsl:apply-templates select="gmd:MD_Format/gmd:formatDistributor"/>
				</dt>						
			</xsl:if>
		</dl>
	</xsl:template>

	<xsl:template match="srv:containsOperations/srv:SV_OperationMetadata">
		<dl>
			<xsl:if test="srv:operationName/gco:CharacterString">			
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.SV_OperationMetadata.operationName</xsl:with-param>
				</xsl:call-template>: </em>							
				<xsl:value-of select="srv:operationName/gco:CharacterString"/>
			</dt>
			</xsl:if>
			<xsl:if test="srv:operationName/gco:CharacterString">			
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.SV_OperationMetadata.operationName</xsl:with-param>
				</xsl:call-template>: </em>							
				<xsl:value-of select="srv:operationName/gco:CharacterString"/>
			</dt>
			</xsl:if>
			<xsl:for-each select="srv:DCP">			
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.SV_PlatformSpecificServiceSpecification.DCP</xsl:with-param>
				</xsl:call-template>: </em>							
				
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.DCPList.<xsl:value-of select="srv:DCPList/@codeListValue"/></xsl:with-param>
				</xsl:call-template>						
			</dt>
			</xsl:for-each>					
			<xsl:if test="srv:operationDescription/gco:CharacterString">			
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.SV_OperationMetadata.operationDescription</xsl:with-param>
				</xsl:call-template>: </em>							
				<xsl:value-of select="srv:operationDescription/gco:CharacterString"/>
			</dt>
			</xsl:if>
			<xsl:for-each select="srv:connectPoint/gmd:CI_OnlineResource">			
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.SV_Operation</xsl:with-param>
				</xsl:call-template>: </em>							
			</dt>
			<dt>
				<xsl:apply-templates select="."/>
			</dt>
			</xsl:for-each>					
		</dl>			
	</xsl:template>	

	<xsl:template match="gmd:graphicOverview/gmd:MD_BrowseGraphic">
		<dl>
			<xsl:if test="gmd:fileName">
			<dt>
				<img>
					<xsl:attribute name="src"><xsl:value-of select="gmd:fileName"/></xsl:attribute>
				</img>
			</dt>
			<dt>
				<em>
				<xsl:call-template name="get_property">
				<xsl:with-param name="key">catalog.iso19139.MD_BrowseGraphic</xsl:with-param>
				</xsl:call-template>: </em>							
				<xsl:value-of select="gmd:fileName"/>
			</dt>
			</xsl:if>
			<xsl:if test="gmd:fileType">
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.MD_BrowseGraphic.fileType</xsl:with-param>
					</xsl:call-template>: </em>							
					<xsl:value-of select="gmd:fileType"/>
				</dt>
			</xsl:if>
			<xsl:if test="gmd:fileDescription">
				<dt>
					<em>
					<xsl:call-template name="get_property">
					<xsl:with-param name="key">catalog.iso19139.MD_BrowseGraphic.fileDescription</xsl:with-param>
					</xsl:call-template>: </em>								
					<xsl:value-of select="gmd:fileDescription"/>
				</dt>
			</xsl:if>
		</dl>
	</xsl:template>


	<!--                     -->
	<!--   Properties   -->
	<!--                     -->
	<xsl:template name="get_property">
		<xsl:param name="key" />
	<!-- Converted parameters from gpt.properties -->
		<xsl:choose>	
			<xsl:when test=' $key = &quot;catalog.iso19139.gco.CodeListValue.codeList&quot; '>Code List</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.gco.CodeListValue.codeListValue&quot; '>Code Value</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.gco.CodeListValue.codeSpace&quot; '>Code Space</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.gco.ObjectIdentification.id&quot; '>id</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.gco.ObjectIdentification.uuid&quot; '>uuid</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.gco.ObjectReference.uuidref&quot; '>uuidref</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.MD_Identification&quot; '>Metadata Identification</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.MD_DataIdentification&quot; '>Data Identification</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.MD_ServiceIdentification&quot; '>Service Identification</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.MD_BrowseGraphic&quot; '>Browse Graphic</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.Multiplicity&quot; '>Multiplicity</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.Multiplicity.range&quot; '>Range</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MultiplicityRange&quot; '>Multiplicity Range</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MultiplicityRange.lower&quot; '>Lower</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MultiplicityRange.upper&quot; '>Upper</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.Length&quot; '>Length</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.Length.km&quot; '>kilometers</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.Length.m&quot; '>meters</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.Length.mi&quot; '>miles</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.Length.ft&quot; '>feet</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.Length.uom&quot; '>Units of Measure</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ApplicationSchemaInformation&quot; '>Application Schema Information</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ApplicationSchemaInformation.name&quot; '>Name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ApplicationSchemaInformation.schemaLanguage&quot; '>Schema Language</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ApplicationSchemaInformation.constraintLanguage&quot; '>Constraint Language</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ApplicationSchemaInformation.schemaAscii&quot; '>Schema Ascii</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ApplicationSchemaInformation.graphicsFile&quot; '>Graphics File</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ApplicationSchemaInformation.softwareDevelopmentFile&quot; '>Software Development File</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ApplicationSchemaInformation.softwareDevelopmentFileFormat&quot; '>Software Development File Format</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_ResponsibleParty&quot; '>Responsible Party</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_ResponsibleParty.individualName&quot; '>Individual Name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_ResponsibleParty.organisationName&quot; '>Organisation Name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_ResponsibleParty.positionName&quot; '>Position Name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_ResponsibleParty.contactInfo&quot; '>Contact Info</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_ResponsibleParty.role&quot; '>Role</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Contact&quot; '>Contact</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Contact.phone&quot; '>Phone</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Contact.address&quot; '>Address</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Contact.onlineResource&quot; '>Online Resource</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Contact.hoursOfService&quot; '>Hours Of Service</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Contact.contactInstructions&quot; '>Contact Instructions</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Telephone&quot; '>Telephone</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Telephone.voice&quot; '>Voice</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Telephone.facsimile&quot; '>Fax</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Address&quot; '>Address</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Address.deliveryPoint&quot; '>Delivery Point</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Address.city&quot; '>City</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Address.administrativeArea&quot; '>Administrative Area</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Address.postalCode&quot; '>Postal Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Address.country&quot; '>Country</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Address.electronicMailAddress&quot; '>E-Mail Address</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_OnlineResource&quot; '>Online Resource</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_OnlineResource.linkage&quot; '>URL</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_OnlineResource.protocol&quot; '>Protocol</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_OnlineResource.applicationProfile&quot; '>Application Profile</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_OnlineResource.name&quot; '>Name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_OnlineResource.description&quot; '>Description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_OnlineResource.function&quot; '>Function</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_OnLineFunctionCode&quot; '>OnLine Function Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_OnLineFunctionCode.caption&quot; '>Function</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_OnLineFunctionCode.download&quot; '>Download</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_OnLineFunctionCode.information&quot; '>Information</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_OnLineFunctionCode.offlineAccess&quot; '>Offline Access</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_OnLineFunctionCode.order&quot; '>Order</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_OnLineFunctionCode.search&quot; '>Search</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_RoleCode&quot; '>Role Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_RoleCode.caption&quot; '>Role</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_RoleCode.resourceProvider&quot; '>Resource Provider</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_RoleCode.custodian&quot; '>Custodian</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_RoleCode.owner&quot; '>Owner</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_RoleCode.user&quot; '>User</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_RoleCode.distributor&quot; '>Distributor</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_RoleCode.originator&quot; '>Originator</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_RoleCode.pointOfContact&quot; '>Point Of Contact</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_RoleCode.principalInvestigator&quot; '>Principal Investigator</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_RoleCode.processor&quot; '>Processor</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_RoleCode.publisher&quot; '>Publisher</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_RoleCode.author&quot; '>Author</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Date&quot; '>Date</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Date.date&quot; '>Date</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Date.dateType&quot; '>Date Type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_DateTypeCode&quot; '>Date Type Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_DateTypeCode.creation&quot; '>Creation Date</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_DateTypeCode.publication&quot; '>Publication Date</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_DateTypeCode.revision&quot; '>Revision Date</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_PresentationFormCode&quot; '>Presentation Form Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_PresentationFormCode.documentDigital&quot; '>Document Digital</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_PresentationFormCode.documentHardcopy&quot; '>Document Hardcopy</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_PresentationFormCode.imageDigital&quot; '>Image Digital</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_PresentationFormCode.imageHardcopy&quot; '>Image Hardcopy</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_PresentationFormCode.mapDigital&quot; '>Map Digital</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_PresentationFormCode.mapHardcopy&quot; '>Map Hardcopy</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_PresentationFormCode.modelDigital&quot; '>Model Digital</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_PresentationFormCode.modelHardcopy&quot; '>Model Hardcopy</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_PresentationFormCode.profileDigital&quot; '>Profile Digital</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_PresentationFormCode.profileHardcopy&quot; '>Profile Hardcopy</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_PresentationFormCode.tableDigital&quot; '>Table Digital</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_PresentationFormCode.tableHardcopy&quot; '>Table Hardcopy</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_PresentationFormCode.videoDigital&quot; '>Video Digital</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_PresentationFormCode.videoHardcopy&quot; '>Video Hardcopy</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Series&quot; '>Series</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Series.name&quot; '>Name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Series.issueIdentification&quot; '>Issue Identification</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Series.page&quot; '>Page</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Citation&quot; '>Citation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Citation.title&quot; '>Title</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Citation.alternateTitle&quot; '>Alternate Title</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Citation.date&quot; '>Date</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Citation.edition&quot; '>Edition</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Citation.editionDate&quot; '>Edition Date</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Citation.identifier&quot; '>Identifier</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Citation.citedResponsibleParty&quot; '>Cited Responsible Party</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Citation.presentationForm&quot; '>Presentation Form</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Citation.series&quot; '>Series</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Citation.otherCitationDetails&quot; '>Other Citation Details</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Citation.ISBN&quot; '>ISBN</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Citation.ISSN&quot; '>ISSN</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Citation.specification.title&quot; '>Specification Title</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.CI_Citation.specification.date&quot; '>Specification Date</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Constraints&quot; '>Usage Constraints</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Constraints.useLimitation&quot; '>Use Limitation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_LegalConstraints&quot; '>Legal Constraints</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_LegalConstraints.accessConstraints&quot; '>Access Constraints</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_LegalConstraints.useConstraints&quot; '>Use Constraints</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_LegalConstraints.otherConstraints&quot; '>Other Constraints</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_SecurityConstraints&quot; '>Security Constraints</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_SecurityConstraints.classification&quot; '>Classification</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_SecurityConstraints.userNote&quot; '>User Note</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_SecurityConstraints.classificationSystem&quot; '>Classification System</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_SecurityConstraints.handlingDescription&quot; '>Handling Description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ClassificationCode&quot; '>Classification Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ClassificationCode.unclassified&quot; '>Unclassified</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ClassificationCode.restricted&quot; '>Restricted</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ClassificationCode.confidential&quot; '>Confidential</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ClassificationCode.secret&quot; '>Secret</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ClassificationCode.topSecret&quot; '>Top Secret</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_RestrictionCode&quot; '>Restriction Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_RestrictionCode.copyright&quot; '>Copyright</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_RestrictionCode.patent&quot; '>Patent</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_RestrictionCode.patentPending&quot; '>Patent Pending</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_RestrictionCode.trademark&quot; '>Trademark</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_RestrictionCode.license&quot; '>License</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_RestrictionCode.intellectualPropertyRights&quot; '>Intellectual Property Rights</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_RestrictionCode.restricted&quot; '>Restricted</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_RestrictionCode.otherRestrictions&quot; '>Other Restrictions</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DigitalTransferOptions&quot; '>Digital Transfer Options</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DigitalTransferOptions.unitsOfDistribution&quot; '>Units Of Distribution</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DigitalTransferOptions.transferSize&quot; '>Transfer Size</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DigitalTransferOptions.onLine&quot; '>Online</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DigitalTransferOptions.offLine&quot; '>Offline</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Distribution&quot; '>Distribution</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Distribution.distributionFormat&quot; '>Distribution Format</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Distribution.distributor&quot; '>Distributor</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Distribution.transferOptions&quot; '>Transfer Options</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Distributor&quot; '>Distributor</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Distributor.distributorContact&quot; '>Distributor Contact</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Distributor.distributionOrderProcess&quot; '>Distribution Order Process</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Distributor.distributorFormat&quot; '>Distributor Format</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Distributor.distributorTransferOptions&quot; '>Distributor Transfer Options</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Format&quot; '>Format</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Format.name&quot; '>Format Name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Format.version&quot; '>Format Version</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Format.amendmentNumber&quot; '>Amendment Number</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Format.specification&quot; '>Specification</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Format.fileDecompressionTechnique&quot; '>File Decompression Technique</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Format.formatDistributor&quot; '>Format Distributor</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Medium&quot; '>Medium</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Medium.name&quot; '>Name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Medium.density&quot; '>Density</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Medium.densityUnits&quot; '>Density Units</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Medium.volumes&quot; '>Volumes</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Medium.mediumFormat&quot; '>Medium Format</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Medium.mediumNote&quot; '>Medium Note</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_StandardOrderProcess&quot; '>Standard Order Process</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_StandardOrderProcess.fees&quot; '>Fees</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_StandardOrderProcess.plannedAvailableDateTime&quot; '>Planned Available Date/Time</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_StandardOrderProcess.orderingInstructions&quot; '>Ordering Instructions</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_StandardOrderProcess.turnaround&quot; '>Turnaround</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DistributionUnits&quot; '>Distribution Units</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumFormatCode&quot; '>Medium Format Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumFormatCode.cpio&quot; '>cpio</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumFormatCode.tar&quot; '>tar</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumFormatCode.highSierra&quot; '>highSierra</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumFormatCode.iso9660&quot; '>iso9660</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumFormatCode.iso9660RockRidge&quot; '>iso9660RockRidge</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumFormatCode.iso9660AppleHFS&quot; '>iso9660AppleHFS</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumNameCode&quot; '>Medium Name Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumNameCode.cdRom&quot; '>CD Rom</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumNameCode.dvd&quot; '>DVD</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumNameCode.dvdRom&quot; '>DVD Rom</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumNameCode.3halfInchFloppy&quot; '>3.5 Inch Floppy</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumNameCode.5quarterInchFloppy&quot; '>5.25 Inch Floppy</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumNameCode.7trackTape&quot; '>7 Track Tape</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumNameCode.9trackType&quot; '>9 Track Type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumNameCode.3480Cartridge&quot; '>3480 Cartridge</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumNameCode.3490Cartridge&quot; '>3490 Cartridge</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumNameCode.3580Cartridge&quot; '>3580 Cartridge</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumNameCode.4mmCartridgeTape&quot; '>4mm Cartridge Tape</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumNameCode.8mmCartridgeTape&quot; '>8mm Cartridge Tape</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumNameCode.1quarterInchCartridgeTape&quot; '>1.25 Inch Cartridge Tape</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumNameCode.digitalLinearTape&quot; '>Digital Linear Tape</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumNameCode.onLine&quot; '>Online</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumNameCode.satellite&quot; '>Satellite</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumNameCode.telephoneLink&quot; '>Telephone Link</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MediumNameCode.hardcopy&quot; '>Hard Copy</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractEX_GeographicExtent&quot; '>Geographic Extent</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractEX_GeographicExtent.extentTypeCode&quot; '>Extent type code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.EX_Extent&quot; '>Extent</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.EX_Extent.description&quot; '>Description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.EX_Extent.geographicElement&quot; '>Spatial Extent</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.EX_Extent.temporalElement&quot; '>Temporal Extent</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.EX_Extent.verticalElement&quot; '>Vertical Extent</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.EX_GeographicExtent&quot; '>Spatial Extent</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.EX_TemporalExtent&quot; '>Temporal Extent</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.EX_TemporalExtent.extent&quot; '>Extent</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.EX_TemporalExtent.beginPosition&quot; '>Begin Date</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.EX_TemporalExtent.endPosition&quot; '>End Date</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.EX_VerticalExtent&quot; '>Vertical Extent</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.EX_VerticalExtent.minimumValue&quot; '>Minimum value</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.EX_VerticalExtent.maximumValue&quot; '>Maximum value</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.EX_VerticalExtent.verticalCRS&quot; '>Vertical CRS</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.EX_GeographicBoundingBox&quot; '>Geographic Bounding Box</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.EX_GeographicBoundingBox.westBoundLongitude&quot; '>West Bounding Longitude</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.EX_GeographicBoundingBox.eastBoundLongitude&quot; '>East Bounding Longitude</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.EX_GeographicBoundingBox.southBoundLatitude&quot; '>South Bounding Latitude</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.EX_GeographicBoundingBox.northBoundLatitude&quot; '>North Bounding Latitude</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractMD_Identification&quot; '>Resource Identification</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractMD_Identification.citation&quot; '>Citation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractMD_Identification.abstract&quot; '>Abstract</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractMD_Identification.purpose&quot; '>Purpose</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractMD_Identification.credit&quot; '>Credit</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractMD_Identification.status&quot; '>Status</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractMD_Identification.pointOfContact&quot; '>Point Of Contact</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractMD_Identification.resourceMaintenance&quot; '>Maintenance</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractMD_Identification.graphicOverview&quot; '>Graphic Overview</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractMD_Identification.resourceFormat&quot; '>Format</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractMD_Identification.descriptiveKeywords&quot; '>Keyword Collection</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractMD_Identification.resourceSpecificUsage&quot; '>Usage</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractMD_Identification.resourceConstraints&quot; '>Constraints</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractMD_Identification.aggregationInfo&quot; '>Aggregation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_Association&quot; '>Association</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_AggregateInformation&quot; '>Aggregate Information</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_AggregateInformation.aggregateDataSetName&quot; '>Aggregate Dataset Name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_AggregateInformation.aggregateDataSetIdentifier&quot; '>Aggregate Dataset Identifier</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_AggregateInformation.associationType&quot; '>Association Type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_AggregateInformation.initiativeType&quot; '>Initiative Type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_BrowseGraphic&quot; '>Browse Graphic</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_BrowseGraphic.fileName&quot; '>Browse Graphic URL</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_BrowseGraphic.fileDescription&quot; '>Browse Graphic Caption</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_BrowseGraphic.fileType&quot; '>Browse Graphic Type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DataIdentification&quot; '>Data Identification</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DataIdentification.spatialRepresentationType&quot; '>Representation Type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DataIdentification.spatialResolution&quot; '>Resolution</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DataIdentification.language&quot; '>Language</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DataIdentification.characterSet&quot; '>Character Set</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DataIdentification.topicCategory&quot; '>Topic Category</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DataIdentification.environmentDescription&quot; '>Environment Description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DataIdentification.extent&quot; '>Extent</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DataIdentification.supplementalInformation&quot; '>Supplemental</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Keywords&quot; '>Keywords</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Keywords.keyword&quot; '>Keyword</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Keywords.type&quot; '>Keyword Type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Keywords.thesaurusName&quot; '>Associated Thesaurus</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Keywords.keyword.delimited&quot; '>Keywords (use comma or newline to separate)</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_RepresentativeFraction&quot; '>Representative Fraction</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_RepresentativeFraction.denominator&quot; '>Denominator</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Resolution&quot; '>Resolution</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Resolution.equivalentScale&quot; '>Equivalent Scale</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Resolution.distance&quot; '>Distance</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Usage&quot; '>Usage</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Usage.specificUsage&quot; '>Specific Usage</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Usage.usageDateTime&quot; '>Usage Date/Time</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Usage.userDeterminedLimitations&quot; '>User Determined Limitations</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Usage.userContactInfo&quot; '>User Contact Info</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_AssociationTypeCode&quot; '>Association Type Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_AssociationTypeCode.crossReference&quot; '>Cross Reference</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_AssociationTypeCode.largerWorkCitation&quot; '>Larger Work Citation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_AssociationTypeCode.partOfSeamlessDatabase&quot; '>Part Of Seamless Database</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_AssociationTypeCode.source&quot; '>Source</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_AssociationTypeCode.stereoMate&quot; '>Stereo Mate</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_InitiativeTypeCode&quot; '>Initiative Type Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_InitiativeTypeCode.campaign&quot; '>Campaign</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_InitiativeTypeCode.collection&quot; '>Collection</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_InitiativeTypeCode.exercise&quot; '>Exercise</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_InitiativeTypeCode.experiment&quot; '>Experiment</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_InitiativeTypeCode.investigation&quot; '>Investigation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_InitiativeTypeCode.mission&quot; '>Mission</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_InitiativeTypeCode.sensor&quot; '>Sensor</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_InitiativeTypeCode.operation&quot; '>Operation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_InitiativeTypeCode.platform&quot; '>Platform</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_InitiativeTypeCode.process&quot; '>Process</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_InitiativeTypeCode.program&quot; '>Program</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_InitiativeTypeCode.project&quot; '>Project</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_InitiativeTypeCode.study&quot; '>Study</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_InitiativeTypeCode.task&quot; '>Task</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_InitiativeTypeCode.trial&quot; '>Trial</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode&quot; '>Character Set Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.ucs2&quot; '>ucs2</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.ucs2&quot; '>ucs2</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.ucs4&quot; '>ucs4</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.utf7&quot; '>utf7</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.utf8&quot; '>utf8</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.utf16&quot; '>utf16</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.8859part1&quot; '>8859part1</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.8859part2&quot; '>8859part2</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.8859part3&quot; '>8859part3</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.8859part4&quot; '>8859part4</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.8859part5&quot; '>8859part5</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.8859part6&quot; '>8859part6</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.8859part7&quot; '>8859part7</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.8859part8&quot; '>8859part8</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.8859part9&quot; '>8859part9</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.8859part10&quot; '>8859part10</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.8859part11&quot; '>8859part11</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.8859part13&quot; '>8859part13</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.8859part14&quot; '>8859part14</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.8859part15&quot; '>8859part15</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.8859part16&quot; '>8859part16</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.jis&quot; '>jis</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.shiftJIS&quot; '>shiftJIS</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.eucJP&quot; '>eucJP</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.usAscii&quot; '>usAscii</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.ebcdic&quot; '>ebcdic</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.eucKR&quot; '>eucKR</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.big5&quot; '>big5</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CharacterSetCode.GB2312&quot; '>GB2312</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_KeywordTypeCode&quot; '>Keyword Type Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_KeywordTypeCode.discipline&quot; '>Discipline</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_KeywordTypeCode.place&quot; '>Place</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_KeywordTypeCode.stratum&quot; '>Stratum</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_KeywordTypeCode.temporal&quot; '>Temporal</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_KeywordTypeCode.theme&quot; '>Theme</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ProgressCode&quot; '>Progress Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ProgressCode.completed&quot; '>Completed</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ProgressCode.historicalArchive&quot; '>Historical Archive</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ProgressCode.obsolete&quot; '>Obsolete</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ProgressCode.onGoing&quot; '>On Going</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ProgressCode.planned&quot; '>Planned</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ProgressCode.required&quot; '>Required</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ProgressCode.underDevelopment&quot; '>Under Development</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_SpatialRepresentationTypeCode&quot; '>Spatial Representation Type Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_SpatialRepresentationTypeCode.vector&quot; '>Vector</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_SpatialRepresentationTypeCode.grid&quot; '>Grid</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_SpatialRepresentationTypeCode.textTable&quot; '>Text Table</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_SpatialRepresentationTypeCode.tin&quot; '>TIN</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_SpatialRepresentationTypeCode.stereoModel&quot; '>Stereo Model</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_SpatialRepresentationTypeCode.video&quot; '>Video</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopicCategoryCode&quot; '>Topic Category Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopicCategoryCode.boundaries&quot; '>Administrative and Political Boundaries</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopicCategoryCode.farming&quot; '>Agriculture and Farming</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopicCategoryCode.climatologyMeteorologyAtmosphere&quot; '>Atmosphere and Climatic</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopicCategoryCode.biota&quot; '>Biology and Ecology</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopicCategoryCode.economy&quot; '>Business and Economic</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopicCategoryCode.planningCadastre&quot; '>Cadastral</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopicCategoryCode.society&quot; '>Cultural, Society and Demography</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopicCategoryCode.elevation&quot; '>Elevation and Derived Products</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopicCategoryCode.environment&quot; '>Environment and Conservation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopicCategoryCode.structure&quot; '>Facilities and Structures</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopicCategoryCode.geoscientificInformation&quot; '>Geological and Geophysical</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopicCategoryCode.health&quot; '>Human Health and Disease</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopicCategoryCode.imageryBaseMapsEarthCover&quot; '>Imagery and Base Maps</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopicCategoryCode.inlandWaters&quot; '>Inland Water Resources</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopicCategoryCode.location&quot; '>Locations and Geodetic Networks</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopicCategoryCode.intelligenceMilitary&quot; '>Military</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopicCategoryCode.oceans&quot; '>Oceans and Estuaries</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopicCategoryCode.transportation&quot; '>Transportation Networks</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopicCategoryCode.utilitiesCommunication&quot; '>Utilities and Communication</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.XTN_Identification&quot; '>Identification</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.XTN_Identification.citation.title&quot; '>Resource Title</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.XTN_Identification.citation.date&quot; '>Resource Date</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.XTN_Identification.citation.identifier&quot; '>Unique Resource Identifier</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.XTN_Identification.citation.MD_Identifier&quot; '>URI</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.XTN_Identification.citation.RS_Identifier&quot; '>ID Plus Code Space</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.XTN_Identification.abstract&quot; '>Resource Abstract</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.XTN_Identification.language&quot; '>Resource Language</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.XTN_Identification.topicCategory&quot; '>Topic Category</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.XTN_Identification.spatialRepresentationType&quot; '>Spatial Representation Type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.XTN_Identification.spatialResolution&quot; '>Spatial Resolution</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.LocalisedCharacterString&quot; '>Localised Character String</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.LocalisedCharacterString.id&quot; '>ID</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.LocalisedCharacterString.locale&quot; '>Locale</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.LocalisedCharacterString.textNode&quot; '>Text</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.PT_FreeText&quot; '>Free Text</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.PT_FreeText.textGroup&quot; '>Text Group</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.PT_Locale&quot; '>PT_Locale</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.PT_Locale.languageCode&quot; '>Language Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.PT_Locale.country&quot; '>country</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.PT_Locale.characterEncoding&quot; '>Character Encoding</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.PT_LocaleContainer&quot; '>Locale Container</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.PT_LocaleContainer.description&quot; '>Description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.PT_LocaleContainer.locale&quot; '>Locale</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.PT_LocaleContainer.date&quot; '>Date</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.PT_LocaleContainer.responsibleParty&quot; '>Responsible Party</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.PT_LocaleContainer.localisedString&quot; '>Localised String</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MaintenanceInformation&quot; '>Maintenance Information</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MaintenanceInformation.maintenanceAndUpdateFrequency&quot; '>Frequency</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MaintenanceInformation.dateOfNextUpdate&quot; '>Date Of Next Update</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MaintenanceInformation.userDefinedMaintenanceFrequency&quot; '>User Defined Maintenance Frequency</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MaintenanceInformation.updateScope&quot; '>Update Scope</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MaintenanceInformation.updateScopeDescription&quot; '>Update Scope Description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MaintenanceInformation.maintenanceNote&quot; '>Maintenance Note</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MaintenanceInformation.contact&quot; '>Contact</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ScopeDescription&quot; '>Scope Description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ScopeDescription.attributes&quot; '>Attributes</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ScopeDescription.features&quot; '>Features</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ScopeDescription.featureInstances&quot; '>Feature Instances</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ScopeDescription.attributeInstances&quot; '>Attribute Instances</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ScopeDescription.dataset&quot; '>Dataset</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ScopeDescription.other&quot; '>Other</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MaintenanceFrequencyCode&quot; '>Maintenance Frequency Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MaintenanceFrequencyCode.continual&quot; '>Continual</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MaintenanceFrequencyCode.daily&quot; '>Daily</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MaintenanceFrequencyCode.weekly&quot; '>Weekly</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MaintenanceFrequencyCode.fortnightly&quot; '>Fortnightly</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MaintenanceFrequencyCode.monthly&quot; '>Monthly</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MaintenanceFrequencyCode.quarterly&quot; '>Quarterly</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MaintenanceFrequencyCode.biannually&quot; '>Biannually</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MaintenanceFrequencyCode.annually&quot; '>annually</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MaintenanceFrequencyCode.asNeeded&quot; '>As Needed</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MaintenanceFrequencyCode.irregular&quot; '>Irregular</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MaintenanceFrequencyCode.notPlanned&quot; '>Not Planned</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MaintenanceFrequencyCode.unknown&quot; '>Unknown</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ScopeCode&quot; '>Scope Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ScopeCode.attribute&quot; '>Attribute</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ScopeCode.attributeType&quot; '>Attribute Type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ScopeCode.collectionHardware&quot; '>Collection Hardware</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ScopeCode.collectionSession&quot; '>Collection Session</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ScopeCode.dataset&quot; '>Dataset</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ScopeCode.series&quot; '>Series</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ScopeCode.nonGeographicDataset&quot; '>Non-geographic Dataset</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ScopeCode.dimensionGroup&quot; '>Dimension Group</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ScopeCode.feature&quot; '>Feature</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ScopeCode.featureType&quot; '>Feature Type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ScopeCode.propertyType&quot; '>Property Type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ScopeCode.fieldSession&quot; '>Field Session</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ScopeCode.software&quot; '>Software</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ScopeCode.service&quot; '>Service</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ScopeCode.model&quot; '>Model</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ScopeCode.tile&quot; '>Tile</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractDS_Aggregate&quot; '>Aggregate</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractDS_Aggregate.composedOf&quot; '>Composed Of</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractDS_Aggregate.seriesMetadata&quot; '>Series Metadata</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractDS_Aggregate.subset&quot; '>Subset</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractDS_Aggregate.superset&quot; '>Superset</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_DataSet&quot; '>Data Set</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_DataSet.has&quot; '>Has Metadata</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DS_DataSet.partOf&quot; '>Is Part Of</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata&quot; '>ISO 19139 Metadata</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.fileIdentifier&quot; '>File Identifier</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.language&quot; '>Metadata Language</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.characterSet&quot; '>Character Set</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.parentIdentifier&quot; '>Parent Identifier</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.hierarchyLevel&quot; '>Hierarchy Level</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.hierarchyLevelName&quot; '>Hierarchy Level Name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.contact&quot; '>Metadata Contact</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.contact.help&quot; '>Here is some help <a href="http://www.esri.com">Esri</a> target="_blank"</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.dateStamp&quot; '>Metadata Date</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.metadataStandardName&quot; '>Metadata Standard Name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.metadataStandardVersion&quot; '>Metadata Standard Version</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.dataSetURI&quot; '>Dataset URI</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.locale&quot; '>Locale</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.spatialRepresentationInfo&quot; '>Spatial Representation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.referenceSystemInfo&quot; '>Reference System</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.metadataExtensionInfo&quot; '>Metadata Extension</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.identificationInfo&quot; '>Identification</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.contentInfo&quot; '>Content</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.distributionInfo&quot; '>Distribution</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.dataQualityInfo&quot; '>Quality</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.portrayalCatalogueInfo&quot; '>Portrayal Catalogue</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.metadataConstraints&quot; '>Constraints</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.applicationSchemaInfo&quot; '>Application Schema</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.metadataMaintenance&quot; '>Maintenance</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.series&quot; '>Series</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.describes&quot; '>Describes</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.propertyType&quot; '>Property Type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.featureType&quot; '>Feature Type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.featureAttribute&quot; '>Feature Attribute</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.metadata&quot; '>Metadata</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.metadata.identifier&quot; '>Identifier</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.metadata.contact&quot; '>Contact</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.metadata.date&quot; '>Date</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.metadata.standard&quot; '>Standard</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.metadata.reference&quot; '>Reference</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.identification&quot; '>Identification</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.identification.citation&quot; '>Citation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.identification.abstract&quot; '>Abstract</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.identification.contact&quot; '>Contact</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.identification.graphicOverview&quot; '>Thumbnail</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.identification.descriptiveKeywords&quot; '>Keywords</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.identification.otherKeywords&quot; '>Other Keywords</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.identification.resourceConstraints&quot; '>Constraints</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.identification.resource&quot; '>Resource</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.identification.representation&quot; '>Representation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.identification.language&quot; '>Language</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.identification.classification&quot; '>Classification</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.identification.extent&quot; '>Extent</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.identification.extent.geographicElement&quot; '>Spatial Extent</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.identification.extent.temporalElement&quot; '>Temporal Extent</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.identification.service.serviceType&quot; '>Service Type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.identification.service.couplingType&quot; '>Coupling Type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.identification.service.operation&quot; '>Operation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.identification.service.operatesOn&quot; '>Operates On</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.distribution&quot; '>Distribution</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.quality&quot; '>Quality</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.quality.scope&quot; '>Scope</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.quality.conformance&quot; '>Conformance</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Metadata.section.quality.lineage&quot; '>Lineage</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ExtendedElementInformation&quot; '>Extended Element Information</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ExtendedElementInformation.name&quot; '>Name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ExtendedElementInformation.shortName&quot; '>Short Name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ExtendedElementInformation.domainCode&quot; '>Domain Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ExtendedElementInformation.definition&quot; '>Definition</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ExtendedElementInformation.obligation&quot; '>Obligation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ExtendedElementInformation.condition&quot; '>Condition</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ExtendedElementInformation.dataType&quot; '>Data Type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ExtendedElementInformation.maximumOccurrence&quot; '>Maximum Occurrence</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ExtendedElementInformation.domainValue&quot; '>Domain Value</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ExtendedElementInformation.parentEntity&quot; '>Parent Entity</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ExtendedElementInformation.rule&quot; '>Rule</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ExtendedElementInformation.rationale&quot; '>Rationale</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ExtendedElementInformation.source&quot; '>Source</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MetadataExtensionInformation&quot; '>Metadata Extension Information</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MetadataExtensionInformation.extensionOnLineResource&quot; '>Extension Online Resource</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_MetadataExtensionInformation.extendedElementInformation&quot; '>Extended Element Information</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DatatypeCode&quot; '>Datatype Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DatatypeCode.class&quot; '>Class</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DatatypeCode.codelist&quot; '>Codelist</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DatatypeCode.enumeration&quot; '>Enumeration</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DatatypeCode.codelistElement&quot; '>Codelist Element</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DatatypeCode.abstractClass&quot; '>Abstract Class</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DatatypeCode.aggregateClass&quot; '>Aggregate Class</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DatatypeCode.specifiedClass&quot; '>Specified Class</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DatatypeCode.datatypeClass&quot; '>Datatype Class</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DatatypeCode.interfaceClass&quot; '>Interface Class</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DatatypeCode.unionClass&quot; '>Union Class</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DatatypeCode.metaClass&quot; '>Meta Class</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DatatypeCode.typeClass&quot; '>Type Class</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DatatypeCode.characterString&quot; '>Character String</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DatatypeCode.integer&quot; '>Integer</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DatatypeCode.association&quot; '>Association</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ObligationCode&quot; '>Obligation Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ObligationCode.mandatory&quot; '>Mandatory</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ObligationCode.optional&quot; '>Optional</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ObligationCode.conditional&quot; '>Conditional</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_PortrayalCatalogueReference&quot; '>Portrayal Catalogue Reference</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_PortrayalCatalogueReference.portrayalCatalogueCitation&quot; '>Citation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractRS_ReferenceSystem&quot; '>Reference System</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractRS_ReferenceSystem.name&quot; '>Name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractRS_ReferenceSystem.domainOfValidity&quot; '>Domain Of Validity</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Identifier&quot; '>Identifier</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Identifier.authority&quot; '>Authority</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Identifier.code&quot; '>Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ReferenceSystem&quot; '>MD_ReferenceSystem</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ReferenceSystem.referenceSystemIdentifier&quot; '>Reference System Identifier</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.RS_Identifier&quot; '>Identifier</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.RS_Identifier.authority&quot; '>Authority</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.RS_Identifier.code&quot; '>Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.RS_Identifier.codeSpace&quot; '>Code Space</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.RS_Identifier.version&quot; '>Version</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Dimension&quot; '>Dimension</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Dimension.dimensionName&quot; '>Dimension Name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Dimension.dimensionSize&quot; '>Dimension Size</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Dimension.resolution&quot; '>Resolution</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_GeometricObjects&quot; '>Geometric Objects</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_GeometricObjects.geometricObjectType&quot; '>Geometric Object Type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_GeometricObjects.geometricObjectCount&quot; '>Geometric Object Count</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Georectified&quot; '>Georectified</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Georectified.checkPointAvailability&quot; '>Check Point Availability</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Georectified.checkPointDescription&quot; '>Check Point Description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Georectified.cornerPoints&quot; '>Corner Points</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Georectified.centerPoint&quot; '>Center Point</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Georectified.pointInPixel&quot; '>Point In Pixel</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Georectified.transformationDimensionDescription&quot; '>Transformation Dimension Description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Georectified.transformationDimensionMapping&quot; '>Transformation Dimension Mapping</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Georeferenceable&quot; '>Georeferenceable</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Georeferenceable.controlPointAvailability&quot; '>Control Point Availability</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Georeferenceable.orientationParameterAvailability&quot; '>Orientation Parameter Availability</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Georeferenceable.orientationParameterDescription&quot; '>Orientation Parameter Description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Georeferenceable.georeferencedParameters&quot; '>Georeferenced Parameters</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Georeferenceable.parameterCitation&quot; '>Parameter Citation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_GridSpatialRepresentation&quot; '>Grid Representation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_GridSpatialRepresentation.numberOfDimensions&quot; '>Number Of Dimensions</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_GridSpatialRepresentation.axisDimensionProperties&quot; '>Axis Dimension Properties</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_GridSpatialRepresentation.cellGeometry&quot; '>Cell Geometry</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_GridSpatialRepresentation.transformationParameterAvailability&quot; '>Transformation Parameter Availability</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_VectorSpatialRepresentation&quot; '>Vector Representation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_VectorSpatialRepresentation.topologyLevel&quot; '>Topology Level</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_VectorSpatialRepresentation.geometricObjects&quot; '>Geometric Objects</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CellGeometryCode&quot; '>Cell Geometry Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CellGeometryCode.point&quot; '>Each cell represents a point</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CellGeometryCode.area&quot; '>Each cell represents an area</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DimensionNameTypeCode&quot; '>Dimension Name Type Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DimensionNameTypeCode.row&quot; '>Ordinate (y) Axis</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DimensionNameTypeCode.column&quot; '>Ordinate (x) Axis</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DimensionNameTypeCode.vertical&quot; '>Vertical (z) Axis)</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DimensionNameTypeCode.track&quot; '>Along the direction of motion of the scan point</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DimensionNameTypeCode.crossTrack&quot; '>Perpendicular to the direction of motion of the scan point</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DimensionNameTypeCode.line&quot; '>Scan line of a sensor</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DimensionNameTypeCode.sample&quot; '>Element along a scan line</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_DimensionNameTypeCode.time&quot; '>Duration</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_GeometricObjectTypeCode&quot; '>Geometric Object Type Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_GeometricObjectTypeCode.complex&quot; '>Complex</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_GeometricObjectTypeCode.composite&quot; '>Composite</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_GeometricObjectTypeCode.curve&quot; '>Curve</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_GeometricObjectTypeCode.point&quot; '>Point</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_GeometricObjectTypeCode.solid&quot; '>Solid</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_GeometricObjectTypeCode.surface&quot; '>Surface</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_PixelOrientationCode&quot; '>Pixel Orientation Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_PixelOrientationCode.center&quot; '>Center of the pixel</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_PixelOrientationCode.lowerLeft&quot; '>Lower-left corner</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_PixelOrientationCode.lowerRight&quot; '>Lower-right corner</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_PixelOrientationCode.upperRight&quot; '>Upper-right corner</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_PixelOrientationCode.upperLeft&quot; '>Upper-left corner</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopologyLevelCode&quot; '>Topology Level Code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopologyLevelCode.geometryOnly&quot; '>Geometry Only</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopologyLevelCode.topology1D&quot; '>Topology 1D</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopologyLevelCode.planarGraph&quot; '>Planar Graph</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopologyLevelCode.fullPlanarGraph&quot; '>Full Planar Graph</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopologyLevelCode.surfaceGraph&quot; '>Surface Graph</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopologyLevelCode.fullSurfaceGraph&quot; '>Full Surface Graph</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopologyLevelCode.topology3D&quot; '>Topology 3D</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopologyLevelCode.fullTopology3D&quot; '>Full Topology 3D</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_TopologyLevelCode.abstract&quot; '>Abstract</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_DataQuality&quot; '>Data Quality</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_DataQuality.scope&quot; '>Scope</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_DataQuality.report&quot; '>Report</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_DataQuality.lineage&quot; '>Lineage</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_Scope&quot; '>Scope</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_Scope.level&quot; '>Level</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_Scope.extent&quot; '>Extent</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_Scope.levelDescription&quot; '>Level description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractDQ_Element&quot; '>Element</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractDQ_Element.nameOfMeasure&quot; '>Name of measure</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractDQ_Element.measureIdentification&quot; '>Measure identification</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractDQ_Element.measureDescription&quot; '>Measure description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractDQ_Element.evaluationMethodType&quot; '>Evaluation method type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractDQ_Element.evaluationMethodDescription&quot; '>Evaluation method description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractDQ_Element.evaluationProcedure&quot; '>Evaluation procedure</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractDQ_Element.dateTime&quot; '>Date/time</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractDQ_Element.result&quot; '>Result</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_AbsoluteExternalPositionalAccuracy&quot; '>External accuracy</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_GriddedDataPositionalAccuracy&quot; '>Gridded accuracy</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_RelativeInternalPositionalAccuracy&quot; '>Internal accuracy</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_NonQuantitiveAttributeAccuracy&quot; '>Non Quantitative accuracy</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_QuantitativeAttributeAccuracy&quot; '>Quantitative accuracy</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_AccuracyOfATimeMeasurement&quot; '>Time measurement accuracy</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_CompletenessOmission&quot; '>Completeness omission</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_CompletenessCommission&quot; '>Completeness commission</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_ConceptualConsistency&quot; '>Conceptual consistency</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_DomainConsistency&quot; '>Domain consistency</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_FormatConsistency&quot; '>Format consistency</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_TemporalAccuracy&quot; '>Temporal accuracy</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_TemporalConsistency&quot; '>Temporal consistency</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_TemporalValidity&quot; '>Temporal validity</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_ThematicAccuracy&quot; '>Thematic accuracy</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_ThematicClassificationCorrectness&quot; '>Thematic correctness</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_TopologicalConsistency&quot; '>Topological consistency</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_QuantitativeResult&quot; '>Quantitative</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_QuantitativeResult.valueType&quot; '>Value type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_QuantitativeResult.errorStatistic&quot; '>Error statistic</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_QuantitativeResult.value&quot; '>Value</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_QuantitativeResult.valueUnit&quot; '>Value unit</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_ConformanceResult&quot; '>Conformance Result</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_ConformanceResult.specification&quot; '>Specification</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_ConformanceResult.explanation&quot; '>Explanation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_ConformanceResult.pass&quot; '>Degree</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_ConformanceResult.pass.Boolean&quot; '>Validation Performed</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_ConformanceResult.pass.Boolean.true&quot; '>Conformant</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DQ_ConformanceResult.pass.Boolean.false&quot; '>Non Conformant</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.LI_Lineage&quot; '>Lineage</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.LI_Lineage.statement&quot; '>Lineage Statement</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.LI_Lineage.processStep&quot; '>Process step</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.LI_Lineage.source&quot; '>Source</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.LI_ProcessStep&quot; '>Process step</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.LI_ProcessStep.description&quot; '>Description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.LI_ProcessStep.rationale&quot; '>Rationale</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.LI_ProcessStep.dateTime&quot; '>Date/time</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.LI_ProcessStep.processor&quot; '>Processor</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.LI_ProcessStep.source&quot; '>Source</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.LI_Source&quot; '>Source</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.LI_Source.description&quot; '>Description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.LI_Source.scaleDenominator&quot; '>Scale denominator</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.LI_Source.sourceReferenceSystem&quot; '>Source reference system</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.LI_Source.sourceCitation&quot; '>Source citation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.LI_Source.sourceExtent&quot; '>Source extent</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.LI_Source.sourceStep&quot; '>Source step</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.XTN_Scope.level&quot; '>Scope (quality information applies to)</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.AbstractTimePrimitive&quot; '>AbstractTimePrimitive</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.StandardObjectProperties&quot; '>Standard object properties</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.StandardObjectProperties.metaDataProperty&quot; '>Metadata property</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.StandardObjectProperties.description&quot; '>Description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.StandardObjectProperties.descriptionReference&quot; '>Description reference</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.StandardObjectProperties.name&quot; '>Name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.StandardObjectProperties.identifier&quot; '>Identifier</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_FeatureCatalogueDescription&quot; '>Feature catalogue description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_FeatureCatalogueDescription.complianceCode&quot; '>Compliance code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_FeatureCatalogueDescription.language&quot; '>Language</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_FeatureCatalogueDescription.includedWithDataset&quot; '>Included with dataset</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_FeatureCatalogueDescription.featureTypes&quot; '>Feature types</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_FeatureCatalogueDescription.featureCatalogueCitation&quot; '>Citation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CoverageDescription&quot; '>Coverage description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CoverageDescription.attributeDescription&quot; '>Attribute description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CoverageDescription.contentType&quot; '>Content type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CoverageDescription.dimension&quot; '>Dimension</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CoverageContentTypeCode&quot; '>Coverage content type code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CoverageContentTypeCode.image&quot; '>Image</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CoverageContentTypeCode.thematicClassification&quot; '>Thematic classification</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_CoverageContentTypeCode.physicalMeasurement&quot; '>Physical measurement</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_RangeDimension&quot; '>Range dimension</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_RangeDimension.sequenceIdentifier&quot; '>Sequence identifier</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_RangeDimension.descriptor&quot; '>Descriptor</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Band&quot; '>Band</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Band.sequenceIdentifier&quot; '>Sequence identifier</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Band.descriptor&quot; '>Descriptor</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Band.minValue&quot; '>Minimum value</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Band.maxValue&quot; '>Maximum value</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Band.units&quot; '>Units</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Band.peakResponse&quot; '>Peak response</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Band.bitsPerValue&quot; '>Bits per value</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Band.toneGradation&quot; '>Tone gradation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Band.scaleFactor&quot; '>Scale factor</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_Band.offset&quot; '>Offset</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImageDescription&quot; '>Image description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImageDescription.attributeDescription&quot; '>Attribute description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImageDescription.contentType&quot; '>Content type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImageDescription.dimension&quot; '>Dimension</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImageDescription.illuminationElevationAngle&quot; '>Illumination elevation angle</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImageDescription.illuminationAzimuthAngle&quot; '>Illumination azimuth angle</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImageDescription.imagingCondition&quot; '>Imaging condition</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImageDescription.imageQualityCode&quot; '>Imaging quality code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImageDescription.cloudCoverPercentage&quot; '>Cloud cover percentage</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImageDescription.processingLevelCode&quot; '>Processing level code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImageDescription.compressionGenerationQuantity&quot; '>Compression generation quantity</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImageDescription.triangulationIndicator&quot; '>Triangulation indicator</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImageDescription.radiometricCalibrationDataAvailability&quot; '>Radiometric calibration data availability</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImageDescription.cameraCalibrationInformationAvailability&quot; '>Camera calibration information availability</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImageDescription.filmDistortionInformationAvailability&quot; '>Film distortion information availability</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImageDescription.lensDistortionInformationAvailability&quot; '>Lens distortion information availability</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImagingConditionCode&quot; '>Imaging condition code</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImagingConditionCode.blurredImage&quot; '>Blurred image</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImagingConditionCode.cloud&quot; '>Cloud</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImagingConditionCode.degradingObliquity&quot; '>Degrading obliquity</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImagingConditionCode.fog&quot; '>Fog</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImagingConditionCode.heavySmokeOrDust&quot; '>Heavy smoke or dust</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImagingConditionCode.night&quot; '>Night</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImagingConditionCode.rain&quot; '>Rain</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImagingConditionCode.semiDarkness&quot; '>Semi-darkness</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImagingConditionCode.shadow&quot; '>Shadow</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.MD_ImagingConditionCode.snow&quot; '>Snow</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_Operation&quot; '>Operation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_Operation.operationName&quot; '>Operation name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_Operation.dependsOn&quot; '>Depends on</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_Operation.parameter&quot; '>Parameter</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_PortSpecification&quot; '>Port specification</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_PortSpecification.binding&quot; '>Binding</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_PortSpecification.address&quot; '>Address</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_Interface&quot; '>Interface</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_Interface.typeName&quot; '>Type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_Interface.theSV_Port&quot; '>Port</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_Interface.operation&quot; '>Operation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_Service&quot; '>Service</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_Service.specification&quot; '>Specification</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_Service.theSV_Port&quot; '>Port</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_Port&quot; '>Port</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_Port.theSV_Interface&quot; '>Interface</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_ServiceType&quot; '>Service type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_ServiceSpecification&quot; '>Service specification</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_ServiceSpecification.name&quot; '>Name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_ServiceSpecification.opModel&quot; '>Model</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_ServiceSpecification.typeSpec&quot; '>Type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_ServiceSpecification.theSV_Interface&quot; '>Interface</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_PlatformNeutralServiceSpecification&quot; '>Platform neutral service specification</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_PlatformNeutralServiceSpecification.name&quot; '>Name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_PlatformNeutralServiceSpecification.opModel&quot; '>Model</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_PlatformNeutralServiceSpecification.serviceType&quot; '>Type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_PlatformNeutralServiceSpecification.implSpec&quot; '>Platform specific service specification</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_PlatformSpecificServiceSpecification&quot; '>Platform specific service specification</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_PlatformSpecificServiceSpecification.name&quot; '>Name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_PlatformSpecificServiceSpecification.opModel&quot; '>Model</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_PlatformSpecificServiceSpecification.serviceType&quot; '>Type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_PlatformSpecificServiceSpecification.implSpec&quot; '>Platform specific service specification</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_PlatformSpecificServiceSpecification.DCP&quot; '>DCP</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_PlatformSpecificServiceSpecification.implementation&quot; '>Implementation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_ParameterDirection&quot; '>Parameter direction</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_Paramater&quot; '>Parameter</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_Paramater.name&quot; '>Name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_Paramater.direction&quot; '>Direction</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_Paramater.description&quot; '>Description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_Paramater.optionality&quot; '>Optionality</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_Paramater.repeatability&quot; '>Repeatability</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_Paramater.valueType&quot; '>Value type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DCPList&quot; '>DCP List</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DCPList.XML&quot; '>XML</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DCPList.CORBA&quot; '>CORBA</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DCPList.JAVA&quot; '>JAVA</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DCPList.COM&quot; '>COM</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DCPList.SQL&quot; '>SQL</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.DCPList.WebServices&quot; '>WebServices</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_OperationMetadata&quot; '>Operation Metadata</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_OperationMetadata.operationName&quot; '>Operation Name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_OperationMetadata.DCP&quot; '>DCP</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_OperationMetadata.operationDescription&quot; '>Operation description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_OperationMetadata.invocationName&quot; '>Invocation name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_OperationMetadata.parameters&quot; '>Parameters</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_OperationMetadata.connectPoint&quot; '>Connect Point</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_OperationMetadata.dependsOn&quot; '>Depends on</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_CoupledResource&quot; '>Coupled resource</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_CoupledResource.operationName&quot; '>Operation name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_CoupledResource.identifier&quot; '>Identifier</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_OperationChainMetadata&quot; '>Operation chain metadata</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_OperationChainMetadata.name&quot; '>Name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_OperationChainMetadata.description&quot; '>Description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_OperationChainMetadata.operation&quot; '>Operation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_OperationChain&quot; '>Operation chain</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_OperationChain.name&quot; '>Name</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_OperationChain.description&quot; '>Description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_OperationChain.operation&quot; '>Operation</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_ServiceIdentification&quot; '>Service identification</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_ServiceIdentification.serviceType&quot; '>Service Type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_ServiceIdentification.serviceTypeVersion&quot; '>Service type version</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_ServiceIdentification.accessProperties&quot; '>Access properties</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_ServiceIdentification.restrictions&quot; '>Restrictions</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_ServiceIdentification.keywords&quot; '>Keywords</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_ServiceIdentification.extent&quot; '>Extent</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_ServiceIdentification.coupledResource&quot; '>Coupled resource</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_ServiceIdentification.couplingType&quot; '>Coupling type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_ServiceIdentification.containsOperations&quot; '>Contains operations</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_ServiceIdentification.operatesOn&quot; '>Operates on</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_CouplingType&quot; '>Coupling Type</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_CouplingType.loose&quot; '>Loose</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_CouplingType.mixed&quot; '>Mixed</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.SV_CouplingType.tight&quot; '>Tight</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.EX_GeographicDescription&quot; '>Geographic Description</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.EX_GeographicDescription.geographicIdentifier&quot; '>Geographic Identifier</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.EX_VerticalExtent.verticalCRS.href&quot; '>Reference (e.g. urn:ogc:def:crs:EPSG::5701 )</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.TM_Primitive.indeterminatePosition&quot; '>Indeterminate Position</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.TM_Primitive.indeterminatePosition.before&quot; '>Before</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.TM_Primitive.indeterminatePosition.after&quot; '>After</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.TM_Primitive.indeterminatePosition.now&quot; '>Now</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.TM_Primitive.indeterminatePosition.unknown&quot; '>Unknown</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.object.uuidref&quot; '>UUID Reference</xsl:when>
			<xsl:when test=' $key = &quot;catalog.iso19139.object.xlink.href&quot; '>XLink Reference</xsl:when>
			<!-- ISO 639-2 language code -->
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.ger&quot; '>German</xsl:when>
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.dut&quot; '>Dutch</xsl:when>
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.eng&quot; '>English</xsl:when>
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.fre&quot; '>French</xsl:when>
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.ita&quot; '>Italian</xsl:when>			
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.kor&quot; '>Korean</xsl:when>
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.lit&quot; '>Lithuanian</xsl:when>
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.nor&quot; '>Norwegian</xsl:when>			
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.pol&quot; '>Polish</xsl:when>			
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.por&quot; '>Portuguese</xsl:when>
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.rus&quot; '>Russian</xsl:when>
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.spa&quot; '>Spanish</xsl:when>
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.swe&quot; '>Swedish</xsl:when>
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.tur&quot; '>Turkish</xsl:when>
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.chi&quot; '>Chinese</xsl:when>
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.bul&quot; '>Bulgarian</xsl:when>
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.cze&quot; '>Czech</xsl:when>
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.dan&quot; '>Danish</xsl:when>
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.est&quot; '>Estonian</xsl:when>
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.fin&quot; '>Finnish</xsl:when>
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.gre&quot; '>Greek</xsl:when>
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.hun&quot; '>Hungarian</xsl:when>
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.gle&quot; '>Gaelic (Irish)</xsl:when>
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.lav&quot; '>Latvian</xsl:when>
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.mlt&quot; '>Maltese</xsl:when>
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.rum&quot; '>Romanian</xsl:when>
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.slo&quot; '>Slovak</xsl:when>
			<xsl:when test=' $key = &quot;catalog.mdCode.language.iso639_2.slv&quot; '>Slovenian</xsl:when>
			
			<xsl:when test=' $key = &quot;catalog.gemini.MD_Metadata.hierarchyLevel&quot; '>Resource Type</xsl:when>
		</xsl:choose>
	</xsl:template>

</xsl:stylesheet>
