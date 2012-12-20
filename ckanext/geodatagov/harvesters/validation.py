from ckanext.spatial.validation import BaseValidator


class MinimalFGDCValidator(BaseValidator):

    name = 'fgdc-minimal'
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
