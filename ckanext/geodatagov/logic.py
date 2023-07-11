import datetime
import hashlib
import logging
import json
import re
import time
import uuid

from ckan.lib.navl.validators import not_empty
from ckan.logic import side_effect_free
import ckan.logic.schema as schema
from ckan.logic.action import get as core_get
import ckan.model as model
import ckan.plugins as p
from ckanext.geodatagov.plugin import change_resource_details, split_tags
from ckanext.geodatagov.harvesters.arcgis import _slugify
from ckanext.geodatagov.helpers import string
from ckanext.harvest.model import HarvestObject  # , HarvestJob

from ckan.common import config

log = logging.getLogger(__name__)


@side_effect_free
def location_search(context, data_dict):
    '''
    Basic bounding box geocoder for countries, US states, US counties
    and US postal codes.

    :param q: The search term. It must have at least 3 characters.
    :type q: string

    Returns an ordered list of locations matching the query, where the
    order is defined by the entity type (countries > states > counties > postal
    codes) and alphabetically.

    Each result contains the following keys:

    :param id: Location identifier
    :type id: integer
    :param text: Location display name
    :type text: string
    :param geom: GeoJSON-like representation of the bbox geometry
    :type geom: dict

    '''
    term = data_dict.get('q')
    if not term:
        raise p.toolkit.ValidationError({'q': 'Missing parameter'})

    if len(term) < 3:
        raise p.toolkit.ValidationError({'q': 'Provide at least three characters'})

    model = context['model']
    sql = '''SELECT id, display_name, ST_AsGeoJSON(the_geom) AS geom
            FROM locations
            WHERE lower(name) LIKE :term
            ORDER BY type_order, display_name'''
    q = model.Session.execute(sql, {'term': '{0}%'.format(term.lower())})

    out = []
    for row in q:
        out.append({'id': row['id'],
                    'text': row['display_name'],
                    'geom': json.loads(row['geom'])})
    return out


def group_show(context, data_dict):

    context.update({'limits': {'packages': 2}})

    return core_get.group_show(context, data_dict)


def package_show_rest(context, data_dict):

    data_dict = core_get.package_show_rest(context, data_dict)
    extras = data_dict.get('extras', {})
    rollup = extras.pop('extras_rollup', None)
    if rollup:
        rollup = json.loads(rollup)
        for key, value in rollup.items():
            extras[key] = value
    return data_dict


def organization_show(context, data_dict):

    context.update({'limits': {'packages': 2}})

    return core_get.organization_show(context, data_dict)


@side_effect_free
def organization_list(context, data_dict):

    model = context['model']

    results = core_get.organization_list(context, data_dict)

    if not data_dict.get('all_fields'):
        return results

    query_results = model.Session.query(
        model.GroupExtra.group_id,
        model.GroupExtra.value
    ).filter_by(
        key='organization_type'
    ).filter(
        model.GroupExtra.group_id.in_([group['id'] for group in results])
    ).all()

    lookup = dict((row[0], row[1]) for row in query_results)

    for group in results:
        organization_type = lookup.get(group['id'])
        if organization_type:
            group['organization_type'] = organization_type

    return results


def resource_show(context, data_dict):
    resource = core_get.resource_show(context, data_dict)
    change_resource_details(resource)
    return resource


MAPPING = {"title": "title",
           "theme": "extras__theme",
           "accessLevel": "extras__access-level",
           "identifier": "id",
           "organizationId": "owner_org",
           "organizationName": "owner_name",
           "description": "notes",
           "keyword": "extras__tags",
           "person": "extras__person",
           "accrualPeriodicity": "extras__frequency-of-update",
           "spatial": "extras__spatial-text",
           "references": "extras__references",
           "dataDictionary": "extras__data-dictiionary",
           "temporal": "extras__dataset-reference-date",
           "issued": "extras__issued",
           "modified": "extras__metadata-date",
           "mbox": "extras__contact-email",
           "granularity": "extras__granularity",
           "license": "extras__licence",
           "dataQuality": "extras__data-quality"}

ORG_MAPPING = {'natiional-park-service': 'nps-gov',
               'u-s-fish-and-wildlife-service': 'fws-gov',
               'u-s-geological-survey': 'usgs-gov',
               'bureau-of-land-management': 'blm-gov',
               'bureau-of-ocean-energy-management': 'boem-gov',
               'office-of-surface-mining': 'osmre-gov',
               'bureau-of-reclamation': 'usbr-gov'}


def create_data_dict(record):
    data_dict = {"extras": [{"key": "metadata-source", "value": "dms"},
                            {"key": "resource-type", "value": "Dataset"}, ],
                 "resources": []}
    extras = data_dict["extras"]

    distributions = record['distribution']

    for distribution in distributions:
        data_dict['resources'].append({'url': distribution['accessURL'],
                                       'format': distribution['format'],
                                       'size_text': distribution.get('size')})

    for key, value in record.items():
        new_key = MAPPING.get(key)
        if not new_key:
            continue
        if not value:
            continue

        if new_key.startswith('extras__'):
            extras.append({"key": new_key[8:], "value": value})
        else:
            data_dict[new_key] = value

    return data_dict


def group_catagory_tag_update(context, data_dict):
    """ If data_dict include "categories" a new
        extra will be added:
            __category_tag_{group.id} = categories
        """
    p.toolkit.check_access('group_catagory_tag_update', context)
    categories = data_dict.get('categories', None)
    if categories is None:
        return data_dict

    package_id = data_dict.get('id')
    group_id = data_dict.get('group_id')

    model = context['model']
    group = model.Group.get(group_id)
    if not group:
        raise Exception('A group is required')
    key = '__category_tag_%s' % group.id

    pkg_dict = p.toolkit.get_action('package_show')(context, {'id': package_id})

    extras = pkg_dict['extras']
    new_extras = []
    for extra in extras:
        if extra.get('key') != key:
            new_extras.append(extra)

    if categories:
        new_extras.append({'key': key, 'value': json.dumps(categories)})

    pkg_dict['extras'] = new_extras

    pkg_dict = p.toolkit.get_action('package_update')(context, pkg_dict)

    return data_dict


def datajson_create(context, data_dict):
    model = context['model']
    new_package = create_data_dict(data_dict)
    owner_org = model.Group.get(new_package['owner_org'])
    group_name = new_package.pop('owner_name', None)
    new_package['name'] = _slugify(new_package['title'])[:80]
    existing_package = model.Package.get(new_package['name'])
    if existing_package:
        new_package['name'] = new_package['name'] + '-' + new_package['id'].lower()

    if not owner_org:
        p.toolkit.get_action('organization_create')(
            context,
            {'name': new_package['owner_org'], 'title': group_name,
             'extras': [{'key': 'organization_type', 'value': "Federal Government"}]})

    context['schema'] = schema.default_create_package_schema()
    context['schema']['id'] = [not_empty]
    context['return_id_only'] = True
    return p.toolkit.get_action('package_create')(context, new_package)


def datajson_update(context, data_dict):
    new_package = create_data_dict(data_dict)
    model = context['model']
    owner_org = model.Group.get(new_package['owner_org'])
    group_name = new_package.pop('owner_name', None)
    old_package = p.toolkit.get_action('package_show')(
        {'model': model, 'ignore_auth': True}, {"id": new_package['id']})
    old_resources = old_package['resources']

    if not owner_org:
        p.toolkit.get_action('organization_create')(
            context,
            {'name': new_package['owner_org'], 'title': group_name,
             'extras': [{'key': 'organization_type', 'value': "Federal Government"}]})

    for num, resource in enumerate(new_package['resources']):
        try:
            old_id = old_resources[num]['id']
            resource['id'] = old_id
        except IndexError:
            pass
    context['return_id_only'] = True
    p.toolkit.get_action('package_update')(context, new_package)


def doi_create(context, data_dict):
    model = context['model']
    new_package = data_dict
    source_hash = hashlib.sha1(json.dumps(data_dict, sort_keys=True)).hexdigest()
    new_package["extras"].append({"key": "source_hash", "value": source_hash})
    new_package["extras"].append({"key": "metadata-source", "value": "doi"})
    new_package["extras"].append({"key": "source_doi_import_identifier", "value": True})
    owner_org = model.Group.get(ORG_MAPPING.get(new_package['organization']['name']))
    if not owner_org:
        print(str((datetime.datetime.now()) + ' Fail to import doi id ' + new_package['id'] + ''
                  '. Organization ' + new_package['organization']['name'] + ' does not exist.'))
        return
    new_package['owner_org'] = owner_org.name
    group_name = new_package.pop('owner_name', None)  # NOQA F841
    new_package['name'] = _slugify(new_package['title'])[:80]
    existing_package = model.Package.get(new_package['name'])
    if existing_package:
        new_package['name'] = new_package['name'] + '-' + str(int(time.time()))

    resources = []
    for resource in new_package['resources']:
        resource.pop('resource_group_id', None)
        resource.pop('revision_id', None)
        resource.pop('id', None)
        resources.append(resource)
    new_package['resources'] = resources

    obj = HarvestObject(
        guid=uuid.uuid4().hex,
        job=context['harvest_job'],
        content=context['harvestobj'])
    obj.save()
    new_package["extras"].append({"key": "harvest_object_id", "value": obj.id})

    context['schema'] = schema.default_create_package_schema()
    context['schema']['id'] = [not_empty]
    context['return_id_only'] = True
    p.toolkit.get_action('package_create')(context, new_package)
    print(str(datetime.datetime.now()) + ' Imported doi id ' + new_package['id'])


def doi_update(context, data_dict):
    model = context['model']
    new_package = data_dict
    source_hash = hashlib.sha1(json.dumps(data_dict, sort_keys=True)).hexdigest()
    old_package = p.toolkit.get_action('package_show')(
        {'model': model, 'ignore_auth': True}, {"id": new_package['id']})
    for extra in old_package['extras']:
        if extra['key'] == 'source_hash':
            old_source_hash = extra['value']
            break
    else:
        old_source_hash = None

    if source_hash == old_source_hash and old_package.get('state') == 'active':
        print(str(datetime.datetime.now()) + ' No change for doi id ' + new_package['id'])
        return

    new_package["extras"].append({"key": "source_hash", "value": source_hash})
    new_package["extras"].append({"key": "metadata-source", "value": "doi"})
    new_package["extras"].append({"key": "source_doi_import_identifier", "value": True})
    new_package.pop("name", None)
    owner_org = model.Group.get(ORG_MAPPING.get(new_package['organization']['name']))
    if not owner_org:
        print(str(datetime.datetime.now()) + ' Fail to update doi id ' + new_package['id'] + ''
              '. Organization ' + new_package['organization']['name'] + ' does not exist.')
        return
    new_package['owner_org'] = owner_org.name
    group_name = new_package.pop('owner_name', None)  # NOQA F841

    resources = []
    for resource in new_package['resources']:
        resource.pop('resource_group_id', None)
        resource.pop('revision_id', None)
        resource.pop('id', None)
        resources.append(resource)
    new_package['resources'] = resources

    obj = HarvestObject(
        guid=uuid.uuid4().hex,
        job=context['harvest_job'],
        content=context['harvestobj'])
    obj.save()
    new_package["extras"].append({"key": "harvest_object_id", "value": obj.id})

    context['return_id_only'] = True
    p.toolkit.get_action('package_update')(context, new_package)
    print(str(datetime.datetime.now()) + ' Updated doi id ' + new_package['id'])


def preserve_category_tags(context, data_dict):
    """ Look category tags in previous version before update dataset """

    # get groups from previous dataset version
    pkg_dict = p.toolkit.get_action('package_show')(context, {'id': data_dict['id']})
    if 'groups' not in data_dict:
        data_dict['groups'] = pkg_dict.get('groups', [])

    # search __category_tag_'s in previous dataset version
    cats = {}
    for extra in pkg_dict.get('extras', []):
        if extra['key'].startswith('__category_tag_'):
            cats[extra['key']] = extra['value']

    # check extras in new datasets and append
    extras = data_dict.get('extras', [])
    for item in extras:
        if item['key'] in cats:
            del cats[item['key']]
    for cat in cats:
        extras.append({'key': cat, 'value': cats[cat]})


EXTRAS_ROLLUP_KEY_IGNORE = [
    # source ignored as queried diretly:
    "metadata-source",
    "tags",
    # ignore keys from ckan harvest source:
    "harvest_object_id",
    "harvest_source_id",
    "harvest_source_title",
]


def rollup_save_action(context, data_dict):
    """ to run before create actions """
    extras_rollup = {}
    new_extras = []
    new_extras_rollup = {}

    for extra in data_dict.get('extras', []):
        if extra['key'] in EXTRAS_ROLLUP_KEY_IGNORE:
            new_extras.append(extra)
        elif extra['key'] == "extras_rollup":
            new_extras_rollup = json.loads(extra['value'])
        else:
            extras_rollup[extra['key']] = extra['value']

    # update new values
    new_extras_rollup.update(extras_rollup)

    # If we use SOLR, try to index (with ckanext-spatial) a valid spatial data
    if p.toolkit.check_ckan_version(min_version='2.8'):
        search_backend = config.get('ckanext.spatial.search_backend', 'postgis')
        log.debug('Search backend {}'.format(search_backend))
        if search_backend == 'solr-bbox':
            old_spatial = new_extras_rollup.get('spatial', None)
            if old_spatial is not None:
                log.info('Old Spatial found {}'.format(old_spatial))

                # TODO look for more not-found location names
                if old_spatial in ['National', 'US']:
                    old_spatial = 'United States'

                new_spatial = translate_spatial(old_spatial)
                if new_spatial is not None:
                    log.info('New Spatial transformed {}'.format(new_spatial))
                    # add the real spatial
                    new_extras.append({'key': 'spatial', 'value': new_spatial})
                    # remove rolled spatial to skip run this process again
                    new_extras_rollup['old-spatial'] = new_extras_rollup.pop('spatial')
                else:
                    log.info('New spatial could not be created')
                    new_extras.append({'key': 'spatial', 'value': ''})
                    new_extras_rollup['old-spatial'] = new_extras_rollup.pop('spatial')

    if new_extras_rollup:
        new_extras.append({'key': 'extras_rollup', 'value': json.dumps(new_extras_rollup)})

    data_dict['extras'] = new_extras


def translate_spatial(old_spatial):
    """ catalog-classic use a non-valid spatial extra.
        Sometimes uses words (like "California") or raw coordinates (like "-96.8518,43.4659,-96.5944,43.6345")
        catalog-next use ckan/spatial and require spatial to be valid geojson
        When possible we need to transform this data so before_index at
        ckanext-spatial could save in solr.
        To save in solr we need a polygon like this:
        {
            "type":"Polygon",
            "coordinates":[
                [
                    [2.05827, 49.8625],
                    [2.05827, 55.7447],
                    [-6.41736, 55.7447],
                    [-6.41736, 49.8625],
                    [2.05827, 49.8625]
                ]
            ]
        } """

    geojson_tpl = ('{{"type": "Polygon", '
                   '"coordinates": [[[{minx}, {miny}], [{minx}, {maxy}], '
                   '[{maxx}, {maxy}], [{maxx}, {miny}], [{minx}, {miny}]]]}}')

    # Replace all things that create bad JSON, https://github.com/GSA/data.gov/issues/3549
    # all instances of '+', '[+23, -1]' is not valid, but '[23, -1]' is valid
    old_spatial_transformed = old_spatial.replace('+', '')
    # all trailing decimals, '[34., 2]' is not valid, but '[34.0, 2]' and '[34, 2]' are valid
    old_spatial_transformed = old_spatial_transformed.replace('.,', ',').replace('.]', ']')
    # '-98, 29, -83, 35.' is not valid
    if old_spatial_transformed[-1] == '.':
        old_spatial_transformed = old_spatial_transformed[0:-1]
    # all leading 0s, '[-089.63,  30.36]' is not valid, '[-89.63,  30.36]' is valid
    old_spatial_transformed = re.sub(r'(^|\s)(-?)0+((0|[1-9][0-9]*)(\.[0-9]*)?)', r'\1\2\3', old_spatial_transformed)
    # if spatial is a space-separated number list, set the new spatial to 'null'
    try:
        numbers_with_spaces = [int(i) for i in old_spatial_transformed.split(' ')]
        if all(isinstance(x, int) for x in numbers_with_spaces):
            old_spatial_transformed = ''
    except ValueError:
        pass

    # If we have 4 numbers separated by commas, transform them as GeoJSON
    parts = old_spatial_transformed.strip().split(',')
    if len(parts) == 4 and all(is_number(x) for x in parts):
        minx, miny, maxx, maxy = parts
        params = {"minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy}
        new_spatial = geojson_tpl.format(**params)
        return new_spatial

    # Analyze with type of data is JSON valid
    try:
        geometry = json.loads(old_spatial_transformed)  # NOQA F841
        # If we have 2 lists of 2 numbers, transform them as GeoJSON
        if (isinstance(geometry, list) and len(geometry) == 2):
            min, max = geometry
            params = {"minx": min[0], "miny": min[1], "maxx": max[0], "maxy": max[1]}
            new_spatial = geojson_tpl.format(**params)
            return new_spatial
        else:
            # If we already have a good geometry, use it
            return old_spatial_transformed
    except BaseException:
        log.info('JSON that could not be parsed\n\t{}'.format(old_spatial_transformed))

    try:
        return get_geo_from_string(old_spatial)
    except AttributeError:
        pass

    return ''


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def get_geo_from_string(location_name):
    """ get a geometry from the locations table using the location name (e.g. California, New York)
        If not table or location_name not exists, return None"""

    sql = 'SELECT ST_AsGeoJSON(the_geom) AS geom FROM locations WHERE name = :location_name;'
    try:  # maybe locations table is not installed
        row = model.Session.execute(sql, {"location_name": location_name}).first()
    except Exception as e:
        log.error('Error querying "{}" locations table {}:\n\t"{}"'.format(location_name, e, sql))
        model.Session.rollback()
        return None

    return None if row is None else row['geom']


def package_update(up_func, context, data_dict):
    """ before_package_update for CKAN 2.8 """
    preserve_category_tags(context, data_dict)
    rollup_save_action(context, data_dict)
    data_dict = fix_dataset(data_dict)
    return up_func(context, data_dict)


def package_create(up_func, context, data_dict):
    """ before_package_create for CKAN 2.8 """
    rollup_save_action(context, data_dict)
    data_dict = fix_dataset(data_dict)
    # TODO: This fix is bad, find a better one :(
    if 'schema' in context.keys():
        context['schema']['id'] = [string]
        context['schema']['tags']['name'] = [not_empty, string]
    return up_func(context, data_dict)


def fix_dataset(data_dict):
    """ final changes before create or update a dataset """
    # stop using tags as extras
    # CKAN don't allow extras with the same name as fields
    extra_tags = None
    for extra in data_dict['extras']:
        if extra['key'] == 'tags':
            extra_tags = extra['value']
            log.info('extra tags found\n\t{}'.format(extra_tags))
            # remove, it will generate an error
            data_dict['extras'].remove(extra)

    if extra_tags is not None:
        tags = data_dict.get('tags', [])
        extra_tags = [dict(name=tag, display_name=tag) for tag in split_tags(extra_tags)]
        log.info('dataset tag found \n\t{}\nUpdate with\n\t{}'.format(tags, extra_tags))
        # avoid duplicates
        final_tags = extra_tags
        for tag in tags:
            if tag['name'] not in [et['name'] for et in extra_tags]:
                final_tags.append(tag)
        data_dict['tags'] = final_tags

    return data_dict
