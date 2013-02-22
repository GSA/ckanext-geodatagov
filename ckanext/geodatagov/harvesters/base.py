import requests
from pylons import config


from ckanext.spatial.validation import Validators

from ckanext.spatial.harvesters.base import SpatialHarvester
from ckanext.spatial.harvesters import CSWHarvester, WAFHarvester, DocHarvester

from ckanext.geodatagov.harvesters.validation import MinimalFGDCValidator

class GeoDataGovHarvester(SpatialHarvester):

    def get_package_dict(self, iso_values, harvest_object):

        tags = iso_values.pop('tags')
        package_dict = super(GeoDataGovHarvester, self).get_package_dict(iso_values, harvest_object)
        package_dict['extras'].append({'key': tags, 'value': ', '.join(tags)})
        return package_dict

    def transform_to_iso(self, original_document, original_format, harvest_object):

        if original_format is not 'fgdc':
            return None

        transform_service = config.get('ckanext.geodatagov.fgdc2iso_service')
        if not transform_service:
            self._save_object_error('No FGDC to ISO transformation service', harvest_object, 'Import')
            return None

        # Validate against FGDC schema
        if self.source_config.get('validation_profiles'):
            profiles = self.source_config.get('validator_profiles')
        else:
            profiles = ['fgdc-minimal']
       
        validator = Validators(profiles=profiles)
        validator.add_validator(MinimalFGDCValidator)

        is_valid, profile, errors = self._validate_document(original_document, harvest_object,
                                                   validator=validator)
        if not is_valid:
            # TODO: Provide an option to continue anyway
            return None

        response = requests.post(transform_service,
                                 data=original_document.encode('utf8'),
                                 headers={'content-type': 'text/xml; charset=utf-8'})
        if response.status_code == 200:
            # XML coming from the conversion tool is already declared and encoded as utf-8
            return response.content
        else:
            msg = 'The transformation service returned an error for object {0}'
            if response.status_code and response.content:
                msg += ': [{0}] {1}'.format(response.status_code, response.content)
            elif response.error:
                msg += ': {0}'.format(response.error)
            self._save_object_error(msg ,harvest_object,'Import')
            return None


class GeoDataGovCSWHarvester(CSWHarvester, GeoDataGovHarvester):
    '''
    A Harvester for CSW servers, with customizations for geo.data.gov
    '''

class GeoDataGovWAFHarvester(WAFHarvester, GeoDataGovHarvester):
    '''
    A Harvester for Web Accessible Folders, with customizations for geo.data.gov
    '''

class GeoDataGovDocHarvester(DocHarvester, GeoDataGovHarvester):
    '''
    A Harvester for single spatial metadata docs, with customizations for geo.data.gov
    '''
