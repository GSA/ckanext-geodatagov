import json
import logging

from ckan import plugins as p
from ckanext.harvest.model import HarvestSource

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


def get_collection_package(collection_package_id):
    package = p.toolkit.get_action('package_show')({}, {'id': collection_package_id})
    return package


def string(value):
    return str(value)
