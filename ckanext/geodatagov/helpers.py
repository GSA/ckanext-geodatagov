import urllib, urllib2, json, re, HTMLParser, urlparse
import os, time
import logging

from pylons import config, request

from ckan import plugins as p
from ckan.lib import helpers as h
from ckanext.geodatagov.plugins import RESOURCE_MAPPING
from ckanext.harvest.model import HarvestSource
#from routes import url_for as _routes_default_url_for

log = logging.getLogger(__name__)

try:
    from ckanext.geodatagov.harvesters.base import VALIDATION_PROFILES
except ImportError, e:
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
        source_type =  package['source_type']
    except:
        pass

    return source_type


def get_harvest_source_config(harvester_id):
    source_config = None
    try:
        harvest_source = HarvestSource.get(harvester_id)
        source_config = json.loads(harvest_source.config)
    except:
        pass

    # convert single string element list to string
    if source_config:
        default_groups = source_config.get('default_groups', '')
        if type(default_groups) is list:
            source_config['default_groups'] = default_groups[0]
        private_datasets = source_config.get('private_datasets', '')
        if type(private_datasets) is list:
            source_config['private_datasets'] = private_datasets[0]
    return source_config


def get_collection_package(collection_package_id):
    package = p.toolkit.get_action('package_show')({}, {'id': collection_package_id})
    return package