import urllib.parse
import requests
import json
import logging
import unicodedata
import re
import uuid
from string import Template

from ckan import logic
from ckan import model
from ckan.model import Session
from ckanext.harvest.model import HarvestObject
from ckanext.harvest.model import HarvestObjectExtra as HOExtra
from ckanext.harvest.interfaces import IHarvester
from ckan.plugins.core import SingletonPlugin, implements
from ckanext.spatial.harvesters.base import SpatialHarvester
from ckan.logic import get_action, ValidationError
from ckan.lib.navl.validators import not_empty, ignore_empty
from ckan.logic.validators import boolean_validator
from html.parser import HTMLParser

from ckan.plugins.toolkit import add_template_directory, add_resource, requires_ckan_version
from ckan.plugins import IConfigurer

from ckanext.geodatagov.helpers import string as custom_string

requires_ckan_version("2.9")


TYPES = ['Web Map', 'KML', 'Mobile Application',
         'Web Mapping Application', 'WMS', 'Map Service']


# from http://code.activestate.com/recipes/577257-slugify-make-a-string-usable-in-a-url-or-filename/
_slugify_strip_re = re.compile(r'[^\w\s-]')
_slugify_hyphenate_re = re.compile(r'[-\s]+')


def _slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.

    From Django's "django/template/defaultfilters.py".
    """
    if not isinstance(value, str):
        value = str(value)
    value = unicodedata.normalize('NFKD', value)
    value = str(_slugify_strip_re.sub('', value).strip().lower())
    return _slugify_hyphenate_re.sub('-', value)


# from http://stackoverflow.com/questions/753052/strip-html-from-strings-in-python
class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.convert_charrefs = True
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()


class ArcGISHarvester(SpatialHarvester, SingletonPlugin):

    implements(IConfigurer)
    implements(IHarvester)

    # IConfigurer
    def update_config(self, config):
        add_template_directory(config, 'templates')
        add_resource('fanstatic_library', 'geodatagov')

    extent_template = Template(('{"type": "Polygon", '
                                '"coordinates": [[[$minx, $miny], '
                                '[$minx, $maxy], [$maxx, $maxy], '
                                '[$maxx, $miny], [$minx, $miny]]]}'))

    def info(self):
        '''
        Harvesting implementations must provide this method, which will return a
        dictionary containing different descriptors of the harvester. The
        returned dictionary should contain:

        * name: machine-readable name. This will be the value stored in the
          database, and the one used by ckanext-harvest to call the appropiate
          harvester.
        * title: human-readable name. This will appear in the form's select box
          in the WUI.
        * description: a small description of what the harvester does. This will
          appear on the form as a guidance to the user.

        A complete example may be::

            {
                'name': 'csw',
                'title': 'CSW Server',
                'description': 'A server that implements OGC's Catalog Service
                                for the Web (CSW) standard'
            }

        returns: A dictionary with the harvester descriptors
        '''
        return {
            'name': 'arcgis',
            'title': 'ArcGIS REST API',
            'description': 'An ArcGIS REST API endpoint'
        }

    def extra_schema(self):
        return {
            'private_datasets': [ignore_empty, boolean_validator],
            'extra_search_criteria': [ignore_empty, custom_string],
        }

    def gather_stage(self, harvest_job):

        self.harvest_job = harvest_job
        source_url = harvest_job.source.url + '/'
        source_config = json.loads(harvest_job.source.config or '{}')
        extra_search_criteria = source_config.get('extra_search_criteria')

        num = 100

        modified_from = 0
        modified_to = 999999999999999999

        query_template = 'modified:%5B{modified_from}%20TO%20{modified_to}%5D'

        if extra_search_criteria:
            query_template = query_template + ' AND (%s)' % extra_search_criteria

        # accountid:0123456789ABCDEF

        query = query_template.format(
            modified_from=str(modified_from).rjust(18, '0'),
            modified_to=str(modified_to).rjust(18, '0'),
        )

        start = 0

        new_metadata = {}

        while start != -1:
            search_path = 'sharing/search?f=pjson&q={query}&num={num}&start={start}'.format(
                query=query,
                num=num,
                start=start,
            )
            try:
                url = urllib.parse.urljoin(str(source_url), str(search_path))
            except TypeError as e:
                self._save_gather_error('Unable to build url (%s, %s): %s' %
                                        (str(source_url), str(search_path), e), harvest_job)

            try:
                r = requests.get(url)
                r.raise_for_status()
            except requests.exceptions.RequestException as e:
                self._save_gather_error('Unable to get content for URL: %s: %r' %
                                        (url, e), harvest_job)
                return None

            results = r.json()

            for result in results['results']:
                if result['type'] not in TYPES:
                    continue
                new_metadata[result['id']] = result
            start = results['nextStart']

        existing_guids = dict()
        query = model.Session.query(HarvestObject.guid, HOExtra.value).\
            filter(True if HarvestObject.current else False).\
            join(HOExtra, HarvestObject.extras).\
            filter(True if HOExtra.key == 'arcgis_modified_date' else False).\
            filter(HarvestObject.harvest_source_id == harvest_job.source.id)

        for (guid, value) in query:
            existing_guids[guid] = value

        new = set(new_metadata) - set(existing_guids)

        harvest_objects = []

        for guid in new:
            date = str(new_metadata[guid]['modified'])
            obj = HarvestObject(job=harvest_job,
                                content=json.dumps(new_metadata[guid]),
                                extras=[HOExtra(key='arcgis_modified_date', value=date),
                                        HOExtra(key='format', value='arcgis_json'),
                                        HOExtra(key='status', value='new')],
                                guid=guid
                                )
            obj.save()
            harvest_objects.append(obj.id)

        deleted = set(existing_guids) - set(new_metadata)

        for guid in deleted:
            obj = HarvestObject(job=harvest_job,
                                extras=[HOExtra(key='status', value='delete')],
                                guid=guid
                                )
            obj.save()
            harvest_objects.append(obj.id)

        changed = set(existing_guids) & set(new_metadata)

        for guid in changed:
            date = str(new_metadata[guid]['modified'])
            if date == existing_guids[guid]:
                continue
            obj = HarvestObject(job=harvest_job,
                                content=json.dumps(new_metadata[guid]),
                                extras=[HOExtra(key='arcgis_modified_date', value=date),
                                        HOExtra(key='format', value='arcgis_json'),
                                        HOExtra(key='status', value='changed')],
                                guid=guid
                                )
            obj.save()
            harvest_objects.append(obj.id)

        return harvest_objects

    def fetch_stage(self, harvest_object):
        return True

    def import_stage(self, harvest_object):

        log = logging.getLogger(__name__ + '.import')
        log.debug('Import stage for harvest object: %s', harvest_object.id)

        if not harvest_object:
            log.error('No harvest object received')
            return False

        source_config = json.loads(harvest_object.source.config or '{}')  # NOQA F841

        status = self._get_object_extra(harvest_object, 'status')

        # Get the last harvested object (if any)
        previous_object = Session.query(HarvestObject) \
            .filter(HarvestObject.guid == harvest_object.guid) \
            .filter(True if HarvestObject.current else False) \
            .first()

        if previous_object:
            previous_object.current = False
            harvest_object.package_id = previous_object.package_id
            previous_object.add()

        context = {'model': model, 'session': Session, 'ignore_auth': True}
        context['user'] = get_action('get_site_user')(context, {})['name']
        context['api_version'] = 3
        context['extras_as_string'] = True
        context['ignore_auth'] = False

        if status == 'delete':
            # Delete package
            get_action('package_delete')(context, {'id': harvest_object.package_id})
            log.info('Deleted package {0} with guid {1}'.format(harvest_object.package_id, harvest_object.guid))
            previous_object.save()
            return True

        if harvest_object.content is None:
            self._save_object_error('Empty content for object {0}'.format(harvest_object.id), harvest_object, 'Import')
            return False

        content = json.loads(harvest_object.content)

        package_dict = self.make_package_dict(harvest_object, content)
        if not package_dict:
            return False

        if status == 'new':
            package_schema = logic.schema.default_create_package_schema()
        else:
            package_schema = logic.schema.default_update_package_schema()

        tag_schema = logic.schema.default_tags_schema()
        tag_schema['name'] = [not_empty, custom_string]
        package_schema['tags'] = tag_schema
        context['schema'] = package_schema  # TODO: user

        harvest_object.current = True
        harvest_object.add()

        if status == 'new':
            # We need to explicitly provide a package ID, otherwise ckanext-spatial
            # won't be be able to link the extent to the package.
            package_dict['id'] = str(uuid.uuid4())
            package_schema['id'] = [custom_string]

            # Save reference to the package on the object
            harvest_object.package_id = package_dict['id']
            harvest_object.add()
            # Defer constraints and flush so the dataset can be indexed with
            # the harvest object id (on the after_show hook from the harvester
            # plugin)
            model.Session.execute('SET CONSTRAINTS harvest_object_package_id_fkey DEFERRED')
            model.Session.flush()

            package_dict['private'] = self.source_config.get('private_datasets', False)

            try:
                package_id = get_action('package_create')(context, package_dict)
                log.info('Created new package %s with guid %s', package_id, harvest_object.guid)
            except ValidationError as e:
                self._save_object_error('Validation Error: %s' % str(e.error_summary), harvest_object, 'Import')
                return False
        elif status == 'changed':
            if previous_object:
                previous_object.current = False
                previous_object.add()
            package_schema = logic.schema.default_update_package_schema()
            package_dict['id'] = harvest_object.package_id
            try:
                package_id = get_action('package_update')(context, package_dict)
                log.info('Updated package %s with guid %s', package_id, harvest_object.guid)
            except ValidationError as e:
                self._save_object_error('Validation Error: %s' % str(e.error_summary), harvest_object, 'Import')
                return False

        model.Session.commit()
        return True

    def make_package_dict(self, harvest_object, content):

        # try hard to get unique name
        name = _slugify(content.get('title') or content.get('item', ''))

        if not name or len(name) < 5:
            name = content['id']

        name = name[:60]
        existing_pkg = model.Package.get(name)
        if existing_pkg and existing_pkg.id != harvest_object.package_id:
            name = name + '_' + content['id']
        title = content.get('title')
        tag_list = [tag.strip('"').strip() for tag in content.get('tags', [])]
        tags = ','.join(tag_list)

        notes = strip_tags(content.get('description') or '')
        if not notes:
            notes = strip_tags(content.get('snippet') or '')

        extras = [dict(key='guid', value=harvest_object.guid),
                  dict(key='metadata_source', value='arcgis'),
                  dict(key='metadata_type', value='geospatial'),
                  dict(key='tags', value=tags)]

        extent = content.get('extent')
        if extent:
            extent_string = self.extent_template.substitute(
                minx=extent[0][0],
                miny=extent[0][1],
                maxx=extent[1][0],
                maxy=extent[1][1],
            )
            extras.append(dict(key='spatial', value=extent_string.strip()))

        source_url = harvest_object.source.url.rstrip('/') + '/'

        resources = []

        # map service has 2 resources
        resource_url = content.get('url')
        if content['type'] in ['Map Service']:
            resources.append(
                {'url': resource_url, 'name': name,
                 'format': 'ArcGIS Map Service'})

        format = content['type'].upper()

        if content['type'] in ['Web Map']:
            resource_url = urllib.parse.urljoin(
                source_url,
                'home/webmap/viewer.html?webmap=' + content['id']
            )

        if content['type'] in ['Map Service']:
            resource_url = urllib.parse.urljoin(
                source_url,
                'home/webmap/viewer.html?services=' + content['id']
            )
            format = 'ArcGIS MAP Preview'

        if not resource_url:
            self._save_object_error('Validation Error: url not in record', harvest_object, 'Import')
            return False

        if not resource_url.startswith('http'):
            resource_url = urllib.parse.urljoin(
                source_url, resource_url)

        if content['type'] in ['Web Map', 'Web Mapping Application']:
            format = 'Web Map Application'

        resource = {'url': resource_url, 'name': name,
                    'format': format}

        resources.append(resource)

        pkg = model.Package.get(harvest_object.package_id)
        if pkg:
            resource['id'] = pkg.resources[0].id

        package_dict = dict(
            name=name.lower(),
            title=title,
            notes=notes,
            extras=extras,
            resources=resources
        )

        source_dataset = model.Package.get(harvest_object.source.id)
        if source_dataset.owner_org:
            package_dict['owner_org'] = source_dataset.owner_org

        return package_dict
