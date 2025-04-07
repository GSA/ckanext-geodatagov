import json
import logging

from ckan import model
from ckan import plugins as p
from ckanext.harvest.model import HarvestSource
from ckan.logic import NotFound, NotAuthorized, get_action

log = logging.getLogger(__name__)

try:
    from ckanext.geodatagov.harvesters.base import VALIDATION_PROFILES
except ImportError as e:
    log.critical('Harvester not available %s' % str(e))


def get_validation_profiles():
    return VALIDATION_PROFILES


def get_validation_schema():
    try:
        from ckanext.datajson.harvester_base import VALIDATION_SCHEMA
    except ImportError:
        return None

    return VALIDATION_SCHEMA


def get_harvest_source_type(harvester_id):
    source_type = None
    try:
        package = p.toolkit.get_action('harvest_source_show')({}, {'id': harvester_id})
        source_type = package['source_type']
    except BaseException:
        pass

    return source_type


def get_harvest_source_config(harvester_id):
    source_config = {}
    keys_lookfor = [
        'default_groups',
        'private_datasets',
        'validator_profiles',
    ]
    try:
        harvest_source = HarvestSource.get(harvester_id)
        source_config = json.loads(harvest_source.config)
    except BaseException:
        pass

    # convert single string element list to string
    if source_config:
        for key in keys_lookfor:
            value = source_config.get(key, '')
            if type(value) is list:
                source_config[key] = value[0]
    return source_config


def count_collection_package(source_id, identifier):
    if not source_id or not identifier:
        return 0

    context = {'model': model, 'session': model.Session}
    package_search = get_action('package_search')
    search_params = {
        'fq': f'harvest_source_id:{source_id} isPartOf:"{identifier}" include_collection:true',
        'rows': 0,
    }

    search_result = package_search(context, search_params)

    return search_result['count'] if search_result['count'] else 0


def get_collection_package(source_id, identifier):
    context = {'model': model, 'session': model.Session}

    package_search = get_action('package_search')
    search_params = {
        'fq': f'harvest_source_id:"{source_id}" identifier:"{identifier}"',
        'rows': 1,
    }

    search_result = package_search(context, search_params)

    ret = None

    if search_result['results']:
        collection_package_id = search_result['results'][0]['id']

        try:
            package = p.toolkit.get_action('package_show')(
                context,
                {'id': collection_package_id}
            )
            ret = package
        except (NotFound, NotAuthorized):
            pass

    return ret


def string(value):
    return str(value)
