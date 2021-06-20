import os

from ckanext.spatial.validation import BaseValidator, XsdValidator, FGDCSchema


class MinimalFGDCValidator(BaseValidator):

    name = 'fgdc_minimal'
    title = 'FGDC Minimal Validation'

    _elements = [
        ('Identification Citation Title', '/metadata/idinfo/citation/citeinfo/title'),
        ('Identification Citation Originator', '/metadata/idinfo/citation/citeinfo/origin'),
        ('Identification Citation Publication Date', '/metadata/idinfo/citation/citeinfo/pubdate'),
        ('Identification Description Abstract', '/metadata/idinfo/descript/abstract'),
        ('Identification Spatial Domain West Bounding Coordinate', '/metadata/idinfo/spdom/bounding/westbc'),
        ('Identification Spatial Domain East Bounding Coordinate', '/metadata/idinfo/spdom/bounding/eastbc'),
        ('Identification Spatial Domain North Bounding Coordinate', '/metadata/idinfo/spdom/bounding/northbc'),
        ('Identification Spatial Domain South Bounding Coordinate', '/metadata/idinfo/spdom/bounding/southbc'),
        ('Metadata Reference Information Contact Address Type', '/metadata/metainfo/metc/cntinfo/cntaddr/addrtype'),
        ('Metadata Reference Information Contact Address State', '/metadata/metainfo/metc/cntinfo/cntaddr/state'),
    ]

    @classmethod
    def is_valid(cls, xml):

        errors = []

        for title, xpath in cls._elements:
            element = xml.xpath(xpath)
            if len(element) == 0 or not element[0].text:
                errors.append(('Element not found: {0}'.format(title), None))
        if len(errors):
            return False, errors

        return True, []


class FGDCValidator(XsdValidator):
    '''
    Base class for FGDC XSD validators
    '''

    @classmethod
    def is_valid(cls, xml):
        xsd_filepath = os.path.join(os.path.dirname(__file__),
                                    cls._xsd_path, cls._xsd_file)
        return cls._is_valid(xml, xsd_filepath, 'FGDC Schema ({0})'.format(cls._xsd_file))


class FGDC1998Schema(FGDCSchema):
    '''
    XSD based validation for FGDC metadata documents, version FGDC-STD-001-1998

    This is the same version present on ckanext-spatial

    '''

    name = 'fgdc_std_001_1998'
    title = 'FGDC CSDGM Version 2.0, 1998 (FGDC-STD-001-1998)'


class FGDC1999Schema(FGDCValidator):
    '''
    XSD based validation for FGDC metadata documents, version FGDC-STD-001.1-1999

    Source: http://www.ncddc.noaa.gov/metadata-standards/metadata-xml/

    '''
    _xsd_path = 'xml/fgdc-std-001.1-1999'
    _xsd_file = 'fgdc-std-001.1-1999.xsd'

    name = 'fgdc_std_001.1_1999'
    title = 'FGDC CSDGM Biological Data Profile (FGDC-STD-001.1-1999)'


class FGDC2001Schema(FGDCValidator):
    '''
    XSD based validation for FGDC metadata documents, version FGDC-STD-001.2-2001

    Source: http://www.ncddc.noaa.gov/metadata-standards/metadata-xml/

    '''
    _xsd_path = 'xml/fgdc-std-001.2-2001'
    _xsd_file = 'fgdc-std-001.2-2001.xsd'

    name = 'fgdc_std_001.2_2001'
    title = 'FGDC CSDGM Metadata Profile for Shoreline Data (FGDC-STD-001.2-2001)'


class FGDC2002Schema(FGDCValidator):
    '''
    XSD based validation for FGDC metadata documents, version FGDC-STD-0012-2002

    Source: http://www.ncddc.noaa.gov/metadata-standards/metadata-xml/

    '''
    _xsd_path = 'xml/fgdc-std-012-2002'
    _xsd_file = 'fgdc-std-012-2002.xsd'

    name = 'fgdc_std_012_2002'
    title = 'FGDC Extensions for Remote Sensing (FGDC-STD-012-2002)'
