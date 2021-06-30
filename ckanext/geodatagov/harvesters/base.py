from future import standard_library
standard_library.install_aliases()
from builtins import str
import re
# import json
import logging
log = logging.getLogger(__name__)
import urllib.parse

import requests
from lxml import etree

from ckan import plugins as p
from ckan.plugins.toolkit import config

from ckan.logic.validators import boolean_validator
from ckan.lib.navl.validators import ignore_empty
from ckan.lib.navl.dictization_functions import Invalid
from ckanext.harvest.model import HarvestObjectExtra as HOExtra
from ckanext.spatial.harvesters.base import guess_standard

from ckanext.spatial.validation import Validators
from ckanext.spatial.harvesters.base import SpatialHarvester
from ckanext.spatial.harvesters import CSWHarvester, WAFHarvester, DocHarvester

from ckanext.geodatagov.validation import (MinimalFGDCValidator, FGDC1998Schema,
                                           FGDC1999Schema, FGDC2001Schema, FGDC2002Schema)


custom_validators = [
    MinimalFGDCValidator, FGDC1998Schema, FGDC1999Schema, FGDC2001Schema, FGDC2002Schema]


VALIDATION_PROFILES = [('', 'Autodetect'),
                       ('iso19139ngdc', 'ISO 19115 Metadata (ISO 19139 XSD)'),
                       ]
for custom_validator in custom_validators:
    VALIDATION_PROFILES.append((custom_validator.name, custom_validator.title))


def validate_profiles(profile):
    if isinstance(profile, list) and len(profile) == 1:
        profile = profile[0]
    validation_profile_names = [p[0] for p in VALIDATION_PROFILES]
    log.debug('Validate {} ({}) in profiles func {}'.format(profile, type(profile), validation_profile_names))

    if profile not in validation_profile_names:
        log.error('Profile {} not found in {}'.format(profile, validation_profile_names))
        raise Invalid('Unknown validation profile: {0}'.format(profile))

    return [str(profile)]


def default_groups_validator(value):
    # Check if default groups exist
    try:
        p.toolkit.get_action('group_show')({}, {'id': value})
    except p.toolkit.ObjectNotFound:
        raise ValueError('Default group not found {0}'.format(value))

    return value


def trim_tags(tags):
    # deal with something like
    # EARTH    SCIENCE > ATMOSPHERE > ATMOSPHERIC    ELECTRICITY > ATMOSPHERIC CONDUCTIVITY
    # Truncate individual keywords to 100 characters since DB fields is varchar 100
    new_tags = set()
    for tag in tags:
        trimmed = re.split(r'[;,>]', tag)
        trimmed = [t.lower().strip() for t in trimmed]
        trimmed = [' '.join(t.split())[:100] for t in trimmed if t != '']
        new_tags.update(trimmed)
    return list(new_tags)


class GeoDataGovHarvester(SpatialHarvester):

    def extra_schema(self):
        log.debug('Getting extra schema for GeoDataGovHarvester')
        return {
            'private_datasets': [ignore_empty, boolean_validator],
            'default_groups': [ignore_empty, default_groups_validator, lambda value: [value]],
            'validator_profiles': [ignore_empty, validate_profiles],
        }

    def get_package_dict(self, iso_values, harvest_object):

        self._set_source_config(harvest_object.source.config)

        package_dict = super(GeoDataGovHarvester, self).get_package_dict(iso_values, harvest_object)
        if not package_dict:
            return None

        package_dict['private'] = self.source_config.get('private_datasets', False)

        default_groups = self.source_config.get('default_groups', None)
        if default_groups and len(default_groups):
            package_dict['groups'] = []
            for group in default_groups:
                package_dict['groups'].append({'name': group})

        # root level tags not needed any more
        package_dict['tags'] = []
        for tag in trim_tags(iso_values.get('tags', [])):
            package_dict['tags'].append({'name': tag})

        package_dict['extras'].append({'key': 'metadata_type', 'value': 'geospatial'})

        return package_dict

    def transform_to_iso(self, original_document, original_format, harvest_object):

        if original_format != 'fgdc':
            return None

        transform_service = config.get('ckanext.geodatagov.fgdc2iso_service')
        if not transform_service:
            self._save_object_error('No FGDC to ISO transformation service', harvest_object, 'Import')
            return None

        # Validate against FGDC schema

        if self.source_config.get('validator_profiles'):
            profiles = self.source_config.get('validator_profiles')
        else:
            profiles = ['fgdc_minimal']
        log.debug('Validates profiles for transform iso {}'.format(profiles))

        validator = Validators(profiles=profiles)
        for custom_validator in custom_validators:
            log.debug('Add validator: {}'.format(custom_validator))
            validator.add_validator(custom_validator)

        is_valid, profile, errors = self._validate_document(original_document, harvest_object,
                                                            validator=validator)
        if not is_valid:
            log.error('Invalid document: {} with profile {}'.format(errors, profile))
            # TODO: Provide an option to continue anyway
            return None

        original_document = re.sub('<\?xml(.*)\?>', '', original_document)  # NOQA W605 

        tree = etree.fromstring(original_document)
        comments = tree.xpath('//comment()')

        for comment in comments:
            p = comment.getparent()
            if p:
                p.remove(comment)

        ptvctcnt = tree.xpath('//ptvctcnt')
        for node in ptvctcnt:
            p = node.getparent()
            if p and not node.text:
                p.remove(node)

        themekt = tree.xpath('//placekt')
        for num, node in enumerate(themekt):
            p = node.getparent()
            # remove all but first
            if p and num > 0:
                p.remove(node)

        original_document = etree.tostring(tree)

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
            self._save_object_error(msg, harvest_object, 'Import')
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
    def info(self):
        return {
            'name': 'single-doc',
            'title': 'Single spatial metadata document',
            'description': 'A single FGDC or ISO 19139 .xml file'
        }


class GeoDataGovGeoportalHarvester(CSWHarvester, GeoDataGovHarvester):
    '''
    A Harvester for CSW servers, with customizations for geo.data.gov
    '''
    def info(self):
        return {
            'name': 'geoportal',
            'title': 'Geoportal Server',
            'description': 'A Geoportal Server CSW endpoint',
        }

    def output_schema(self):
        return 'csw'

    def fetch_stage(self, harvest_object):

        log.debug('CswHarvester fetch_stage for object: %s', harvest_object.id)

        url = harvest_object.source.url

        identifier = harvest_object.guid

        parts = urllib.parse.urlparse(url)
        url = urllib.parse.urlunparse((
            parts.scheme,
            parts.netloc,
            '/'.join(parts.path.rstrip('/').split('/')[:-2]),
            None, None, None)
        )
        url = url.rstrip('/') + '/rest/document?id=%s' % identifier
        try:
            response = requests.get(url)
            content = response.content
        except Exception:
            self._save_object_error('Error getting the record with GUID %s from %s' %
                                    (identifier, url), harvest_object)
            return False

        try:
            # Save the fetch contents in the HarvestObject
            # Contents come from csw_client already declared and encoded as utf-8
            # Remove original XML declaration
            content = re.sub('<\?xml(.*)\?>', '', content)  # NOQA W605

            document_format = guess_standard(content)
            if document_format == 'iso':
                harvest_object.content = content
                harvest_object.save()
            elif document_format == 'fgdc':
                extra = HOExtra(
                    object=harvest_object,
                    key='original_document',
                    value=content)
                extra.save()

                extra = HOExtra(
                    object=harvest_object,
                    key='original_format',
                    value=document_format)
                extra.save()
            else:
                harvest_object.report_status = 'ignored'
                harvest_object.save()
                return False
        except Exception as e:
            self._save_object_error('Error saving the harvest object for GUID %s [%r]' %
                                    (identifier, e), harvest_object)
            return False

        log.debug('XML content saved (len %s)', len(content))
        return True
