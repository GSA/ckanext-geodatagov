import json
import logging

import ckan.plugins as p
from ckan.logic import side_effect_free
from ckan.logic.action import get as core_get
from ckanext.geodatagov.plugins import change_resource_details
import ckan.lib.munge as munge
import ckan.plugins as p
from ckanext.geodatagov.harvesters.arcgis import _slugify
import ckan.logic.schema as schema

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
    rollup = extras.pop('extras_rollup')
    if rollup:
        rollup = json.loads(rollup)
        for key, value in rollup.items():
            extras[key] = value
    return data_dict

def organization_show(context, data_dict):

    context.update({'limits': {'packages': 2}})

    return core_get.organization_show(context, data_dict)

def organization_list(context, data_dict):

    model = context['model']

    results = core_get.organization_list(context, data_dict)

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
           "keyword" : "extras__tags",
           "person": "extras__person",
           "accrualPeriodicity": "extras__frequency-of-update",
           "spatial": "extras__spatial-text",
           "references": "extras__references",
           "dataDictionary": "extras__data-dictiionary",
           "temporal": "extras__dataset-reference-date",
           "modified": "extras__metadata-date",
           "mbox": "extras__contact-email",
           "granularity": "extras__granularity",
           "license": "extras__licence",
           "dataQuality": "extras__data-quality"}

def create_data_dict(record):
    data_dict = {"extras":[{"key": "metadata-source", "value": "dms"},
                           {"key": "resource-type", "value": "Dataset"},
                          ],
                 "resources": []}
    extras = data_dict["extras"]

    distributions = record['distribution']

    for distribution in distributions:
        data_dict['resources'].append({'url': distribution['accessURL'],
                                      'format': distribution['format']})

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
    p.toolkit.check_access('group_catagory_tag_update', context)
    package_id = data_dict.get('id')
    group_id = data_dict.get('group_id')
    categories = data_dict.get('categories')

    model = context['model']
    group = model.Group.get(group_id)
    if not group:
        raise
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
    context['schema']['id'] = [p.toolkit.get_validator('not_empty')]
    context['return_id_only'] = True
    return p.toolkit.get_action('package_create')(context, new_package)

def datajson_update(context, data_dict):
    new_package = create_data_dict(data_dict)
    model = context['model']
    old_package = p.toolkit.get_action('package_show')(
        {'model': model, 'ignore_auth': True}, {"id":new_package['id']})
    old_resources = old_package['resources']
    new_package.pop('owner_org', None)
    new_package.pop('owner_name', None)
    for num, resource in enumerate(new_package['resources']):
        try:
            old_id = old_resources[num]['id']
            resource['id'] = old_id
        except IndexError:
            pass
    context['return_id_only'] = True
    p.toolkit.get_action('package_update')(context, new_package)

