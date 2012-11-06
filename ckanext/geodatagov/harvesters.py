'''
Different harvesters for spatial metadata

    - CswHarvester - CSW servers with support for the ISO metadata profile
    - DocHarvester - An individual ISO resource
    - WafHarvester - An index page with links to ISO resources

'''
import cgitb
import warnings
from urlparse import urlparse, urljoin
from datetime import datetime
from string import Template
from numbers import Number
import sys
import uuid
import os
import logging
import hashlib

import dateutil.parser
import pyparsing as parse
import requests
from lxml import etree
from sqlalchemy.sql import update, bindparam
from sqlalchemy.orm import aliased

from ckan import model
from ckan.model import Session, Package
from ckan.lib.munge import munge_title_to_name
from ckan.plugins.core import SingletonPlugin, implements
from ckan.lib.helpers import json

from ckan import logic
from ckan.logic import get_action, ValidationError
from ckan.lib.navl.validators import not_empty

from ckanext.harvest.interfaces import IHarvester
from ckanext.harvest.model import HarvestObject
from ckanext.harvest.model import HarvestObjectExtra as HOExtra

from ckanext.spatial.model import GeminiDocument
from ckanext.spatial.harvesters import SpatialHarvester
from ckanext.spatial.lib.csw_client import CswService

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

def guess_standard(url):

    content = requests.get(url, timeout=60).content
    if content:
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

    def import_stage(self, harvest_object):
        log = logging.getLogger(__name__ + '.import')
        log.debug('Import stage for harvest object: %s', harvest_object.id)

        if not harvest_object:
            log.error('No harvest object received')
            return False

        self._set_config(harvest_object.source.config)

        # Save a reference
        self.obj = harvest_object

        if harvest_object.content is None:
            self._save_object_error('Empty content for object %s' % harvest_object.id,harvest_object,'Import')
            return False
        try:
            # Generate GUID if not present (i.e. it's a manual import)
            if not self.obj.guid:
                m = hashlib.md5()
                m.update(self.obj.content.encode('utf8',errors='ignore'))
                self.obj.guid = m.hexdigest()
                self.obj.save()

            self.import_gemini_object(harvest_object.content)
            return True
        except Exception, e:
            log.error('Exception during import: %s' % text_traceback())
            if not str(e).strip():
                self._save_object_error('Error importing document.', harvest_object, 'Import')
            else:
                self._save_object_error('Error importing document: %s' % str(e), harvest_object, 'Import')

            if debug_exception_mode:
                raise

    def import_gemini_object(self, gemini_string):
        log = logging.getLogger(__name__ + '.import')
        xml = etree.fromstring(gemini_string)

        valid, messages = self._get_validator().is_valid(xml)
        if not valid:
            log.error('Errors found for object with GUID %s:' % self.obj.guid)
            out = messages[0] + ':\n' + '\n'.join(messages[1:])
            self._save_object_error(out,self.obj,'Import')

        unicode_gemini_string = etree.tostring(xml, encoding=unicode, pretty_print=True)

        self.write_package_from_gemini_string(unicode_gemini_string)


    def write_package_from_gemini_string(self, content):
        '''Create or update a Package based on some content that has
        come from a URL.
        '''
        log = logging.getLogger(__name__ + '.import')
        package = None
        gemini_document = GeminiDocument(content)
        gemini_values = gemini_document.read_values()
        gemini_guid = gemini_values['guid']

        if not gemini_guid:
            if self.obj.guid:
                gemini_guid = self.obj.guid
            else:
                raise Exception('Could not determine GUID for object %s' % self.obj.id)

        # Save the metadata reference date in the Harvest Object
        try:
            metadata_modified_date = datetime.strptime(gemini_values['metadata-date'],'%Y-%m-%d')
        except ValueError:
            try:
                metadata_modified_date = datetime.strptime(gemini_values['metadata-date'],'%Y-%m-%dT%H:%M:%S')
            except:
                raise Exception('Could not extract reference date for GUID %s (%s)' \
                        % (gemini_guid,gemini_values['metadata-date']))

        self.obj.metadata_modified_date = metadata_modified_date
        self.obj.save()

        last_harvested_object = Session.query(HarvestObject) \
                            .filter(HarvestObject.guid==gemini_guid) \
                            .filter(HarvestObject.current==True) \
                            .all()

        if len(last_harvested_object) == 1:
            last_harvested_object = last_harvested_object[0]
        elif len(last_harvested_object) > 1:
                raise Exception('Application Error: more than one current record for GUID %s' % gemini_guid)

        reactivate_package = False
        if last_harvested_object:
            # We've previously harvested this (i.e. it's an update)

            # Use metadata modified date instead of content to determine if the package
            # needs to be updated
            if last_harvested_object.metadata_modified_date is None \
                or last_harvested_object.metadata_modified_date < self.obj.metadata_modified_date \
                or self.force_import \
                or (last_harvested_object.metadata_modified_date == self.obj.metadata_modified_date and
                    last_harvested_object.source.active is False):

                if self.force_import:
                    log.info('Import forced for object %s with GUID %s' % (self.obj.id,gemini_guid))
                else:
                    log.info('Package for object with GUID %s needs to be created or updated' % gemini_guid)

                package = last_harvested_object.package

                # If the package has a deleted state, we will only update it and reactivate it if the
                # new document has a more recent modified date
                if package and package.state == u'deleted':
                    if last_harvested_object.metadata_modified_date < self.obj.metadata_modified_date:
                        log.info('Package for object with GUID %s will be re-activated' % gemini_guid)
                        reactivate_package = True
                    else:
                         log.info('Remote record with GUID %s is not more recent than a deleted package, skipping... ' % gemini_guid)
                         return None

            else:
                if last_harvested_object.content != self.obj.content and \
                 last_harvested_object.metadata_modified_date == self.obj.metadata_modified_date:
                    raise Exception('The contents of document with GUID %s changed, but the metadata date has not been updated' % gemini_guid)
                else:
                    # The content hasn't changed, no need to update the package
                    log.info('Document with GUID %s unchanged, skipping...' % (gemini_guid))
                return None
        else:
            log.info('No package with guid %s found, let''s create one' % gemini_guid)

        extras = {
            'published_by': self.obj.source.publisher_id or '',
            'UKLP': 'True',
            'harvest_object_id': self.obj.id
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
            extras[name] = gemini_values[name]

        if not extras['guid']:
            extras['guid'] = self.obj.guid

        extras['licence'] = gemini_values.get('use-constraints', '')
        if len(extras['licence']):
            license_url_extracted = self._extract_first_license_url(extras['licence'])
            if license_url_extracted:
                extras['licence_url'] = license_url_extracted

        extras['access_constraints'] = gemini_values.get('limitations-on-public-access','')
        if gemini_values.has_key('temporal-extent-begin'):
            extras['temporal_coverage-from'] = gemini_values['temporal-extent-begin']
        if gemini_values.has_key('temporal-extent-end'):
            extras['temporal_coverage-to'] = gemini_values['temporal-extent-end']

        # Save responsible organization roles
        parties = {}
        owners = []
        publishers = []
        for responsible_party in gemini_values['responsible-organisation']:

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
        extent_string = self.extent_template.substitute(
                minx = extras['bbox-east-long'],
                miny = extras['bbox-south-lat'],
                maxx = extras['bbox-west-long'],
                maxy = extras['bbox-north-lat']
                )

        extras['spatial'] = extent_string.strip()

        tags = []
        for tag in gemini_values['tags']:
            tag = tag[:50] if len(tag) > 50 else tag
            tags.append({'name':tag})

        package_dict = {
            'title': gemini_values['title'],
            'notes': gemini_values['abstract'],
            'tags': tags,
            'resources':[]
        }

        if self.obj.source.publisher_id:
            package_dict['groups'] = [{'id':self.obj.source.publisher_id}]


        if reactivate_package:
            package_dict['state'] = u'active'

        if package is None or package.title != gemini_values['title']:
            name = self.gen_new_name(gemini_values['title'])
            if not name:
                name = self.gen_new_name(str(gemini_guid))
            if not name:
                raise Exception('Could not generate a unique name from the title or the GUID. Please choose a more unique title.')
            package_dict['name'] = name
        else:
            package_dict['name'] = package.name

        resource_locators = gemini_values.get('resource-locator', [])

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

        if package == None:
            # Create new package from data.
            package_id = self._create_package_from_data(package_dict)
            log.info('Created new package ID %s with guid %s', package_id, gemini_guid)
        else:
            package_id = self._create_package_from_data(package_dict, package=package)
            log.info('Updated existing package ID %s with existing guid %s', package_id, gemini_guid)

        # Flag the other objects of this source as not current anymore
        from ckanext.harvest.model import harvest_object_table
        u = update(harvest_object_table) \
                .where(harvest_object_table.c.package_id==bindparam('b_package_id')) \
                .values(current=False)
        Session.execute(u, params={'b_package_id':package_id})
        Session.commit()

        # Refresh current object from session, otherwise the
        # import paster command fails
        Session.remove()
        Session.add(self.obj)
        Session.refresh(self.obj)

        # Set reference to package in the HarvestObject and flag it as
        # the current one
        if not self.obj.package_id:
            self.obj.package_id = package_id

        self.obj.current = True
        self.obj.save()

        return package_id

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

    def _create_package_from_data(self, package_dict, package = None):

        if not package:
            package_schema = logic.schema.default_create_package_schema()
        else:
            package_schema = logic.schema.default_update_package_schema()

        # The default package schema does not like Upper case tags
        tag_schema = logic.schema.default_tags_schema()
        tag_schema['name'] = [not_empty,unicode]
        package_schema['tags'] = tag_schema

        # TODO: user
        context = {'model':model,
                   'session':Session,
                   'user':'harvest',
                   'schema':package_schema,
                   'extras_as_string':True,
                   'api_version': '2',
                   'return_id_only': True}
        if not package:
            # We need to explicitly provide a package ID, otherwise ckanext-spatial
            # won't be be able to link the extent to the package.
            package_dict['id'] = unicode(uuid.uuid4())
            package_schema['id'] = [unicode]

            action_function = get_action('package_create')
        else:
            action_function = get_action('package_update')
            package_dict['id'] = package.id

        try:
            package_id = action_function(context, package_dict)
        except ValidationError,e:
            raise Exception('Validation Error: %s' % str(e.error_summary))
            if debug_exception_mode:
                raise

        return package_id

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

class CswHarvester(GeoDataGovHarvester, SingletonPlugin):
    '''
    A Harvester for CSW servers
    '''
    implements(IHarvester)

    csw=None

    def info(self):
        return {
            'name': 'csw',
            'title': 'CSW Server',
            'description': 'A server that implements OGC\'s Catalog Service for the Web (CSW) standard'
            }

    def gather_stage(self, harvest_job):
        log = logging.getLogger(__name__ + '.CSW.gather')
        log.debug('CswHarvester gather_stage for job: %r', harvest_job)
        # Get source URL
        url = harvest_job.source.url

        self._set_config(harvest_job.source.config)

        try:
            self._setup_csw_client(url)
        except Exception, e:
            self._save_gather_error('Error contacting the CSW server: %s' % e, harvest_job)
            return None


        log.debug('Starting gathering for %s' % url)
        used_identifiers = []
        ids = []
        try:
            for identifier in self.csw.getidentifiers(page=10):
                try:
                    log.info('Got identifier %s from the CSW', identifier)
                    if identifier in used_identifiers:
                        log.error('CSW identifier %r already used, skipping...' % identifier)
                        continue
                    if identifier is None:
                        log.error('CSW returned identifier %r, skipping...' % identifier)
                        ## log an error here? happens with the dutch data
                        continue

                    # Create a new HarvestObject for this identifier
                    obj = HarvestObject(guid=identifier, job=harvest_job)
                    obj.save()

                    ids.append(obj.id)
                    used_identifiers.append(identifier)
                except Exception, e:
                    self._save_gather_error('Error for the identifier %s [%r]' % (identifier,e), harvest_job)
                    continue

        except Exception, e:
            log.error('Exception: %s' % text_traceback())
            self._save_gather_error('Error gathering the identifiers from the CSW server [%s]' % str(e), harvest_job)
            return None

        if len(ids) == 0:
            self._save_gather_error('No records received from the CSW server', harvest_job)
            return None

        return ids

    def fetch_stage(self,harvest_object):
        log = logging.getLogger(__name__ + '.CSW.fetch')
        log.debug('CswHarvester fetch_stage for object: %s', harvest_object.id)

        url = harvest_object.source.url
        try:
            self._setup_csw_client(url)
        except Exception, e:
            self._save_object_error('Error contacting the CSW server: %s' % e,
                                    harvest_object)
            return False

        identifier = harvest_object.guid
        try:
            record = self.csw.getrecordbyid([identifier])
        except Exception, e:
            self._save_object_error('Error getting the CSW record with GUID %s' % identifier, harvest_object)
            return False

        if record is None:
            self._save_object_error('Empty record for GUID %s' % identifier,
                                    harvest_object)
            return False

        try:
            # Save the fetch contents in the HarvestObject
            harvest_object.content = record['xml']
            harvest_object.save()
        except Exception,e:
            self._save_object_error('Error saving the harvest object for GUID %s [%r]' % \
                                    (identifier, e), harvest_object)
            return False

        log.debug('XML content saved (len %s)', len(record['xml']))
        return True

    def _setup_csw_client(self, url):
        self.csw = CswService(url)


class DocHarvester(GeoDataGovHarvester, SingletonPlugin):
    '''
    A Harvester for individual spatial metadata documents
    '''

    implements(IHarvester)

    def info(self):
        return {
            'name': 'single-doc',
            'title': 'Single spatial metadata document',
            'description': 'A single spatial metadata document'
            }

    def gather_stage(self,harvest_job):
        log = logging.getLogger(__name__ + '.individual.gather')
        log.debug('DocHarvester gather_stage for job: %r', harvest_job)

        self.harvest_job = harvest_job

        # Get source URL
        url = harvest_job.source.url

        self._set_config(harvest_job.source.config)

        # Get contents
        try:
            content = self._get_content(url)
        except Exception,e:
            self._save_gather_error('Unable to get content for URL: %s: %r' % \
                                        (url, e),harvest_job)
            return None
        try:
            # We need to extract the guid to pass it to the next stage
            gemini_string, gemini_guid = self.get_gemini_string_and_guid(content,url)

            if gemini_guid:
                # Create a new HarvestObject for this identifier
                # Generally the content will be set in the fetch stage, but as we alredy
                # have it, we might as well save a request
                obj = HarvestObject(guid=gemini_guid,
                                    job=harvest_job,
                                    content=gemini_string)
                obj.save()

                log.info('Got GUID %s' % gemini_guid)
                return [obj.id]
            else:
                self._save_gather_error('Could not get the GUID for source %s' % url, harvest_job)
                return None
        except Exception, e:
            self._save_gather_error('Error parsing the document. Is this a valid  document?: %s [%r]'% (url,e),harvest_job)
            if debug_exception_mode:
                raise
            return None


    def fetch_stage(self,harvest_object):
        # The fetching was already done in the previous stage
        return True


class WafHarvester(GeoDataGovHarvester, SingletonPlugin):
    '''
    A Harvester for WAF (Web Accessible Folders) containing spatial metadata documents.
    e.g. Apache serving a directory of ISO 19139 files.
    '''

    implements(IHarvester)

    def info(self):
        return {
            'name': 'waf',
            'title': 'Web Accessible Folder (WAF)',
            'description': 'A Web Accessible Folder (WAF) displaying a list of spatial metadata documents'
            }

    def gather_stage(self,harvest_job):
        log = logging.getLogger(__name__ + '.WAF.gather')
        log.debug('WafHarvester gather_stage for job: %r', harvest_job)

        self.harvest_job = harvest_job

        # Get source URL
        url = harvest_job.source.url

        self._set_config(harvest_job.source.config)

        # Get contents
        try:
            response = requests.get(url, timeout=60)
            content = response.content
            scraper = _get_scraper(response.headers.get('server'))
        except Exception,e:
            self._save_gather_error('Unable to get content for URL: %s: %r' % \
                                        (url, e),harvest_job)
            return None


        ######  Get current harvest object out of db ######

        url_to_modified_db = {} ## mapping of url to last_modified in db
        url_to_guid = {} ## mapping of url to guid in db


        HOExtraAlias1 = aliased(HOExtra)
        HOExtraAlias2 = aliased(HOExtra)
        query = model.Session.query(HarvestObject.guid, HOExtraAlias1.value, HOExtraAlias2.value).\
                                    join(HOExtraAlias1, HarvestObject.extras).\
                                    join(HOExtraAlias2, HarvestObject.extras).\
                                    filter(HOExtraAlias1.key=='waf_modified_date').\
                                    filter(HOExtraAlias2.key=='waf_location').\
                                    filter(HarvestObject.current==True).\
                                    filter(HarvestObject.harvest_source_id==harvest_job.source.id)


        for guid, modified_date, url in query:
            url_to_modified_db[url] = modified_date
            url_to_guid[url] = guid

        ######  Get current list of records from source ######

        url_to_modified_harvest = {} ## mapping of url to last_modified in harvest
        try:
            for url, modified_date in _extract_waf(content,url,scraper):
                url_to_modified_harvest[url] = modified_date
        except Exception,e:
            msg = 'Error extracting URLs from %s, error was %s' % (url, e)
            self._save_gather_error(msg,harvest_job)
            return None



        ######  Compare source and db ######

        harvest_locations = set(url_to_modified_harvest.keys())
        old_locations = set(url_to_modified_db.keys())

        new = harvest_locations - old_locations
        delete = old_locations - harvest_locations
        possible_changes = old_locations & harvest_locations
        change = []

        for item in possible_changes:
            if (not url_to_modified_harvest[item] or not url_to_modified_db[item] #if there is no date assume change
                or url_to_modified_harvest[item] > url_to_modified_db[item]):
                change.append(item)

        def create_extras(url, date, status):
            return [HOExtra(key='waf_modified_date', value=date),
                    HOExtra(key='waf_location', value=url),
                    HOExtra(key='status', value=status)]

        ids = []
        for location in new:
            obj = HarvestObject(job=harvest_job,
                                extras=create_extras(url,
                                                     url_to_modified_harvest[location],
                                                     'new')
                               )
            obj.save()
            ids.append(obj.id)

        for location in change:
            obj = HarvestObject(job=harvest_job,
                                extras=create_extras(url,
                                                     url_to_modified_harvest[location],
                                                     'change'),
                                guid=url_to_guid[url]
                               )
            obj.save()
            ids.append(obj.id)

        for location in delete:
            obj = HarvestObject(job=harvest_job,
                                extras=create_extras('','', 'delete'),
                                guid=url_to_guid[url]
                               )
            obj.save()
            ids.append(obj.id)

        if len(ids) > 0:
            return ids
        else:
            self._save_gather_error('No records to change',
                                     harvest_job)
            return None

    def fetch_stage(self,harvest_object):

        # Check harvest object status
        status = get_extra(harvest_object,'status')

        if status == 'delete':
            # No need to fetch anything, just pass to the import stage
            return True

        elif status in ('new','change'):
            # We need to fetch the remote document

            # Get location
            url = get_extra(harvest_object, 'waf_location')
            if not url:
                self._save_object_error(
                        'No location defined for object {0}'.format(harvest_object.id)
                        ,harvest_object)
                return False

            # Get contents
            try:
                content = self._get_content(url)
            except Exception, e:
                msg = 'Could not harvest WAF link {0}: {1}'.format(url, e)
                self._save_object_error(msg,harvest_object)
                return False

            # Check if it is an ISO document
            document_format = guess_standard(content)

            if document_format == 'iso':
                try:
                    document_string, guid = self.get_gemini_string_and_guid(content,url)
                    if guid:
                        log.debug('Got GUID %s' % guid)
                        harvest_object.guid = guid
                        harvest_object.content = document_string
                        harvest_object.save()

                except Exception,e:
                    msg = 'Could not get GUID for source {0}: {1}'.format(url, e)
                    self._save_object_error(msg,harvest_object)
                    return False
            else:
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

                if status == 'new':
                    m = hashlib.md5()
                    m.update(url.encode('utf8',errors='ignore'))
                    harvest_object.guid = m.hexdigest()
                    harvest_object.save()

            return True


apache  = parse.SkipTo(parse.CaselessLiteral("<a href="), include=True).suppress() \
        + parse.quotedString.setParseAction(parse.removeQuotes).setResultsName('url') \
        + parse.SkipTo("</a>", include=True).suppress() \
        + parse.Optional(parse.Literal('</td><td align="right">')).suppress() \
        + parse.Optional(parse.Combine(
            parse.Word(parse.alphanums+'-') +
            parse.Word(parse.alphanums+':')
        ,adjacent=False, joinString=' ').setResultsName('date')
        )

iis =      parse.SkipTo("<br>").suppress() \
         + parse.OneOrMore("<br>").suppress() \
         + parse.Optional(parse.Combine(
           parse.Word(parse.alphanums+'/') +
           parse.Word(parse.alphanums+':') +
           parse.Word(parse.alphas)
         , adjacent=False, joinString=' ').setResultsName('date')
         ) \
         + parse.Word(parse.nums).suppress() \
         + parse.Literal('<A HREF=').suppress() \
         + parse.quotedString.setParseAction(parse.removeQuotes).setResultsName('url')

other = parse.SkipTo(parse.CaselessLiteral("<a href="), include=True).suppress() \
        + parse.quotedString.setParseAction(parse.removeQuotes).setResultsName('url')


scrapers = {'apache': parse.OneOrMore(parse.Group(apache)),
            'other': parse.OneOrMore(parse.Group(other)),
            'iis': parse.OneOrMore(parse.Group(iis))}

def _get_scraper(server):
    if not server or 'apache' in server.lower():
        return 'apache'
    if server == 'Microsoft-IIS/7.5':
        return 'iis'
    else:
        return 'other'

def _extract_waf(content, base_url, scraper, results = None, depth=0):
    if results is None:
        results = []

    base_url = base_url.rstrip('/').split('/')
    if 'index' in base_url[-1]:
        base_url.pop()
    base_url = '/'.join(base_url)
    base_url += '/'

    parsed = scrapers[scraper].parseString(content)

    for record in parsed:
        url = record.url
        if not url:
            continue
        if url.startswith('_'):
            continue
        if '?' in url:
            continue
        if '#' in url:
            continue
        if 'mailto:' in url:
            continue
        if '..' not in url and url[0] != '/' and url[-1] == '/':
            new_depth = depth + 1
            if depth > 10:
                print 'max depth reached'
                continue
            new_url = urljoin(base_url, url)
            if not new_url.startswith(base_url):
                continue
            print 'new_url', new_url
            try:
                response = requests.get(new_url)
                content = response.content
            except Exception, e:
                print str(e)
                continue
            _extract_waf(content, new_url, scraper, results, new_depth)
            continue
        if not url.endswith('.xml'):
            continue
        date = record.date
        if date:
            try:
                date = str(dateutil.parser.parse(date))
            except Exception, e:
                raise
                date = None
        results.append((urljoin(base_url, record.url), date))

    return results


