'''
Different harvesters for spatial metadata

    - CswHarvester - CSW servers with support for the ISO metadata profile
    - DocHarvester - An individual ISO resource
    - WafHarvester - An index page with links to ISO resources

'''
import cgitb
import warnings
from urlparse import urlparse
from datetime import datetime
from string import Template
from numbers import Number
import sys
import uuid
import os
import logging
import hashlib
import dateutil
import re

import requests
from lxml import etree
from pylons import config

from ckan import model
from ckan.model import Session, Package
from ckan.lib.munge import munge_title_to_name
from ckan.lib.helpers import json

from ckan import logic
from ckan.logic import get_action, ValidationError
from ckan.lib.navl.validators import not_empty

from ckanext.harvest.model import HarvestObject

from ckanext.spatial.model import GeminiDocument
from ckanext.spatial.harvesters import SpatialHarvester
from ckanext.spatial.validation import Validators

log = logging.getLogger(__name__)

def text_traceback():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = 'the original traceback:'.join(
            cgitb.text(sys.exc_info()).split('the original traceback:')[1:]
        ).strip()
    return res

# When developing, it might be helpful to 'export DEBUG=1' to reraise the
# exceptions, rather them being caught.
debug_exception_mode = bool(os.getenv('DEBUG'))

def guess_standard(content):
    lowered = content.lower()
    if '</gmd:MD_Metadata>'.lower() in lowered:
        return 'iso'
    if '</gmi:MI_Metadata>'.lower() in lowered:
        return 'iso'
    if '</metadata>'.lower() in lowered:
        return 'fgdc'
    return 'unknown'

def get_extra(harvest_object, key):
    for extra in harvest_object.extras:
        if extra.key == key:
            return extra.value
    return None



class GeoDataGovHarvester(SpatialHarvester):
    '''

    All three harvesters share the same import stage
    '''

    force_import = False

    extent_template = Template('''
    {"type":"Polygon","coordinates":[[[$minx, $miny],[$minx, $maxy], [$maxx, $maxy], [$maxx, $miny], [$minx, $miny]]]}
    ''')

    def _validate_document(self, document_string, harvest_object, validator=None):
        if not validator:
            validator = self._get_validator()

        document_string = re.sub('<\?xml(.*)\?>','',document_string)
        xml = etree.fromstring(document_string)

        valid, messages = validator.is_valid(xml)
        if not valid:
            log.error('Errors found for object with GUID %s:' % harvest_object.guid)
            out = messages[0] + ':\n' + '\n'.join(messages[1:])
            self._save_object_error(out, harvest_object,'Import')

        return valid, messages

    def _get_package_dict(self, iso_values, harvest_object):

        #TODO: Big cleanup!

        tags = []
        for tag in iso_values['tags']:
            tag = tag[:50] if len(tag) > 50 else tag
            tags.append({'name':tag})

        package_dict = {
            'title': iso_values['title'],
            'notes': iso_values['abstract'],
            'tags': tags,
            'resources':[]
        }

        # TODO: still not clear
        '''
        if harvest_object.source.publisher_id:
            package_dict['groups'] = [{'id': harvest_object.source.publisher_id}]
        '''

        # Package name
        package = harvest_object.package
        if package is None or package.title != iso_values['title']:
            name = self.gen_new_name(iso_values['title'])
            if not name:
                name = self.gen_new_name(str(iso_values['guid']))
            if not name:
                raise Exception('Could not generate a unique name from the title or the GUID. Please choose a more unique title.')
            package_dict['name'] = name
        else:
            package_dict['name'] = package.name

        extras = {
            'published_by': harvest_object.source.publisher_id or '',
            'UKLP': 'True',
            'harvest_object_id': harvest_object.id
        }

        # Just add some of the metadata as extras, not the whole lot
        for name in [
            # Essentials
            'bbox-east-long',
            'bbox-north-lat',
            'bbox-south-lat',
            'bbox-west-long',
            'spatial-reference-system',
            'guid',
            # Usefuls
            'dataset-reference-date',
            'resource-type',
            'metadata-language', # Language
            'metadata-date', # Released
            'coupled-resource',
            'contact-email',
            'frequency-of-update',
            'spatial-data-service-type',
        ]:
            extras[name] = iso_values[name]

        extras['guid'] = harvest_object.guid

        extras['licence'] = iso_values.get('use-constraints', '')
        if len(extras['licence']):
            license_url_extracted = self._extract_first_license_url(extras['licence'])
            if license_url_extracted:
                extras['licence_url'] = license_url_extracted

        extras['access_constraints'] = iso_values.get('limitations-on-public-access','')
        if iso_values.has_key('temporal-extent-begin'):
            extras['temporal_coverage-from'] = iso_values['temporal-extent-begin']
        if iso_values.has_key('temporal-extent-end'):
            extras['temporal_coverage-to'] = iso_values['temporal-extent-end']

        # Save responsible organization roles
        parties = {}
        owners = []
        publishers = []
        for responsible_party in iso_values['responsible-organisation']:

            if responsible_party['role'] == 'owner':
                owners.append(responsible_party['organisation-name'])
            elif responsible_party['role'] == 'publisher':
                publishers.append(responsible_party['organisation-name'])

            if responsible_party['organisation-name'] in parties:
                if not responsible_party['role'] in parties[responsible_party['organisation-name']]:
                    parties[responsible_party['organisation-name']].append(responsible_party['role'])
            else:
                parties[responsible_party['organisation-name']] = [responsible_party['role']]

        parties_extra = []
        for party_name in parties:
            parties_extra.append('%s (%s)' % (party_name, ', '.join(parties[party_name])))
        extras['responsible-party'] = '; '.join(parties_extra)

        # Save provider in a separate extra:
        # first organization to have a role of 'owner', and if there is none, first one with
        # a role of 'publisher'
        if len(owners):
            extras['provider'] = owners[0]
        elif len(publishers):
            extras['provider'] = publishers[0]
        else:
            extras['provider'] = u''

        # Construct a GeoJSON extent so ckanext-spatial can register the extent geometry
        if extras['bbox-east-long'] and extras['bbox-south-lat'] \
           and extras['bbox-west-long'] and extras['bbox-north-lat']:

            extent_string = self.extent_template.substitute(
                    minx = extras['bbox-east-long'],
                    miny = extras['bbox-south-lat'],
                    maxx = extras['bbox-west-long'],
                    maxy = extras['bbox-north-lat']
                    )

            extras['spatial'] = extent_string.strip()
        else:
            log.debug('No spatial extent defined for this object')

        resource_locators = iso_values.get('resource-locator', [])

        if len(resource_locators):
            for resource_locator in resource_locators:
                url = resource_locator.get('url','')
                if url:
                    resource_format = ''
                    resource = {}
                    if extras['resource-type'] == 'service':
                        # Check if the service is a view service
                        test_url = url.split('?')[0] if '?' in url else url
                        if self._is_wms(test_url):
                            resource['verified'] = True
                            resource['verified_date'] = datetime.now().isoformat()
                            resource_format = 'WMS'
                    resource.update(
                        {
                            'url': url,
                            'name': resource_locator.get('name',''),
                            'description': resource_locator.get('description') if resource_locator.get('description') else 'Resource locator',
                            'format': resource_format or None,
                            'resource_locator_protocol': resource_locator.get('protocol',''),
                            'resource_locator_function':resource_locator.get('function','')

                        })
                    package_dict['resources'].append(resource)

            # Guess the best view service to use in WMS preview
            verified_view_resources = [r for r in package_dict['resources'] if 'verified' in r and r['format'] == 'WMS']
            if len(verified_view_resources):
                verified_view_resources[0]['ckan_recommended_wms_preview'] = True
            else:
                view_resources = [r for r in package_dict['resources'] if r['format'] == 'WMS']
                if len(view_resources):
                    view_resources[0]['ckan_recommended_wms_preview'] = True

        extras_as_dict = []
        for key,value in extras.iteritems():
            if isinstance(value,(basestring,Number)):
                extras_as_dict.append({'key':key,'value':value})
            else:
                extras_as_dict.append({'key':key,'value':json.dumps(value)})

        package_dict['extras'] = extras_as_dict

        return package_dict

    def import_stage(self, harvest_object):

        #TODO: exceptions

        log = logging.getLogger(__name__ + '.import')
        log.debug('Import stage for harvest object: %s', harvest_object.id)

        if not harvest_object:
            log.error('No harvest object received')
            return False

        self._set_config(harvest_object.source.config)

        status = get_extra(harvest_object, 'status')

        # Get the last harvested object (if any)
        previous_object = Session.query(HarvestObject) \
                          .filter(HarvestObject.guid==harvest_object.guid) \
                          .filter(HarvestObject.current==True) \
                          .first()

        if status == 'delete':
            # Delete package
            context = {'model':model, 'session':Session, 'user':'harvest'} #TODO: user

            get_action('package_delete')(context, {'id': harvest_object.package_id})
            log.info('Deleted package {0} with guid {1}'.format(harvest_object.package_id, harvest_object.guid))

            return True

        original_document = get_extra(harvest_object, 'original_document')
        if harvest_object.content is None and not original_document:
            self._save_object_error('Empty content for object {0}'.format(harvest_object.id), harvest_object, 'Import')
            return False

        # Check if it is a non ISO document
        original_format = get_extra(harvest_object, 'original_format')
        if original_format and original_format == 'fgdc':

            transform_service = config.get('ckanext.geodatagov.fgdc2iso_service')
            if not transform_service:
                self._save_object_error('No FGDC to ISO transformation service', harvest_object, 'Import')
                return False

            # Validate against FGDC schema
            is_valid, errors = self._validate_document(original_document, harvest_object,
                                                       validator=Validators(profiles=['fgdc']))
            if not is_valid:
                # TODO: Provide an option to continue anyway
                return False

            response = requests.post(transform_service, data=original_document.strip())
            if response.status_code == 200:
                harvest_object.content = response.content
                harvest_object.save()
            else:
                msg = 'The transformation service returned an error for object {0}'
                if response.status_code and response.content:
                    msg += ': [{0}] {1}'.format(response.status_code, response.content)
                elif response.error:
                    msg += ': {0}'.format(response.error)
                self._save_object_error(msg ,harvest_object,'Import')
                return False

        else:
            # Document is ISO, validate
            is_valid, errors = self._validate_document(harvest_object.content, harvest_object)
            if not is_valid:
                # TODO: Provide an option to continue anyway
                return False

        # Parse ISO document
        try:
            iso_values = GeminiDocument(harvest_object.content).read_values()
        except Exception, e:
            self._save_object_error('Error parsing ISO document for object {0}: {1}'.format(harvest_object.id,str(e)),
                                    harvest_object,'Import')
            return False

        # Flag previous object as not current anymore
        if previous_object:
            previous_object.current = False
            previous_object.add()

        # Update GUID with the one on the document
        iso_guid = iso_values['guid']
        if iso_guid and harvest_object.guid != iso_guid:
            # First make sure there already aren't current objects
            # with the same guid
            existing_object = Session.query(HarvestObject.id) \
                            .filter(HarvestObject.guid==iso_guid) \
                            .filter(HarvestObject.current==True) \
                            .first()
            if existing_object:
                self._save_object_error('Object {0} already has this guid {1}'.format(existing_object.id, iso_guid),
                                    harvest_object,'Import')
                return False

            harvest_object.guid = iso_guid
            harvest_object.add()

        # Generate GUID if not present (i.e. it's a manual import)
        if not harvest_object.guid:
            m = hashlib.md5()
            m.update(harvest_object.content.encode('utf8',errors='ignore'))
            harvest_object.guid = m.hexdigest()
            harvest_object.add()

        # Get document modified date
        try:
            metadata_modified_date = dateutil.parser.parse(iso_values['metadata-date'])
        except ValueError:
            self._save_object_error('Could not extract reference date for object {0} ({1})'
                        .format(harvest_object.id, iso_values['metadata-date']), harvest_object, 'Import')
            return False

        harvest_object.metadata_modified_date = metadata_modified_date
        harvest_object.add()

        # Build the package dict
        package_dict = self._get_package_dict(iso_values, harvest_object)

        # Create / update the package

        context = {'model':model,
                   'session':Session,
                   'user':'harvest', # TODO: user
                   'extras_as_string':True, # TODO: check if needed
                   'api_version': '2',
                   'return_id_only': True}

        # The default package schema does not like Upper case tags
        tag_schema = logic.schema.default_tags_schema()
        tag_schema['name'] = [not_empty, unicode]

        if status == 'new':
            package_schema = logic.schema.default_create_package_schema()
            package_schema['tags'] = tag_schema
            context['schema'] = package_schema

            # We need to explicitly provide a package ID, otherwise ckanext-spatial
            # won't be be able to link the extent to the package.
            package_dict['id'] = unicode(uuid.uuid4())
            package_schema['id'] = [unicode]

            try:
                package_id = get_action('package_create')(context, package_dict)
                log.info('Created new package %s with guid %s', package_id, harvest_object.guid)
            except ValidationError,e:
                self._save_object_error('Validation Error: %s' % str(e.error_summary), harvest_object, 'Import')
                return False

            # Save reference to the package on the object
            harvest_object.package_id = package_id
            harvest_object.add()

        elif status == 'change':

            # Check if the modified date is more recent
            if harvest_object.metadata_modified_date <= previous_object.metadata_modified_date:

                # Delete the previous object to avoid cluttering the object table
                previous_object.delete()

                log.info('Document with GUID %s unchanged, skipping...' % (harvest_object.guid))
            else:
                package_schema = logic.schema.default_update_package_schema()
                package_schema['tags'] = tag_schema
                context['schema'] = package_schema

                package_dict['id'] = harvest_object.package_id

                try:
                    package_id = get_action('package_update')(context, package_dict)
                    log.info('Updated package %s with guid %s', package_id, harvest_object.guid)
                except ValidationError,e:
                    self._save_object_error('Validation Error: %s' % str(e.error_summary), harvest_object, 'Import')
                    return False

        # Flag this object as the current one
        harvest_object.current = True
        harvest_object.add()

        model.Session.commit()


        return True


    def gen_new_name(self, title):
        name = munge_title_to_name(title).replace('_', '-')
        while '--' in name:
            name = name.replace('--', '-')
        pkg_obj = Session.query(Package).filter(Package.name == name).first()
        if pkg_obj:
            return name + str(uuid.uuid4())[:5]
        else:
            return name

    def _extract_first_license_url(self,licences):
        for licence in licences:
            o = urlparse(licence)
            if o.scheme and o.netloc:
                return licence
        return None

    def get_gemini_string_and_guid(self,content,url=None):
        xml = etree.fromstring(content)

        # The validator and GeminiDocument don't like the container
        metadata_tags = ['{http://www.isotc211.org/2005/gmd}MD_Metadata','{http://www.isotc211.org/2005/gmi}MI_Metadata']
        if xml.tag in metadata_tags:
            gemini_xml = xml
        else:
            for metadata_tag in metadata_tags:
                gemini_xml = xml.find(metadata_tag)
                if gemini_xml:
                    break

        if gemini_xml is None:
            self._save_gather_error('Content is not a valid Gemini document',self.harvest_job)

        valid, messages = self._get_validator().is_valid(gemini_xml)
        if not valid:
            out = messages[0] + ':\n' + '\n'.join(messages[1:])
            if url:
                self._save_gather_error('Validation error for %s - %s'% (url,out),self.harvest_job)
            else:
                self._save_gather_error('Validation error - %s'%out,self.harvest_job)

        gemini_string = etree.tostring(gemini_xml)
        gemini_document = GeminiDocument(gemini_string)
        gemini_values = gemini_document.read_values()
        gemini_guid = gemini_values['guid']

        return gemini_string, gemini_guid
