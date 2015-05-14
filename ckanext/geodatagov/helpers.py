import urllib, urllib2, json, re, HTMLParser, urlparse
import os, time
import logging

from pylons import config, request

from ckan import plugins as p
from ckan.lib import helpers as h
from ckanext.geodatagov.plugins import RESOURCE_MAPPING
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

def remove_extra_chars(str_value):
    # this will remove brackets for list and dict values.
    import ast
    new_value = None

    try:
        new_value = ast.literal_eval(str_value)
    except:
        pass

    if type(new_value) is list:
        new_value = [i.strip() for i in new_value]
        ret = ', '.join(new_value)
    elif type(new_value) is dict:
        ret = ', '.join('{0}:{1}'.format(key, val) for key, val in new_value.items())
    else:
        ret = str_value

    return ret

def schema11_key_mod(key):
    key_map = {
        'Catalog @Context': 'Metadata Context',
        'Catalog @Id': 'Metadata Catalog ID',
        'Catalog Conformsto': 'Schema Version',
        'Catalog DescribedBy': 'Data Dictionary',

        # 'Identifier': 'Unique Identifier',
        'Modified': 'Last Update',
        'Accesslevel': 'Public Access Level',
        'Bureaucode' : 'Bureau Code',
        'Programcode': 'Program Code',
        'Accrualperiodicity': 'Frequency',
        'Conformsto': 'Data Standard',
        'Dataquality': 'Data Quality',
        'Describedby': 'Data Dictionary',
        'Describedbytype': 'Data Dictionary Type',
        'Issued': 'Release Date',
        'Landingpage': 'Homepage URL',
        'Primaryitinvestmentuii': 'Primary IT Investment UII',
        'References': 'Related Documents',
        'Systemofrecords': 'System of Records',
        'Theme': 'Category',
    }

    return key_map.get(key, key)

def schema11_frequency_mod(value):
    frequency_map = {
        'R/P10Y': 'Decennial',
        'R/P4Y': 'Quadrennial',
        'R/P1Y': 'Annual',
        'R/P2M': 'Bimonthly',
        'R/P0.5M': 'Bimonthly',
        'R/P3.5D': 'Semiweekly',
        'R/P1D': 'Daily',
        'R/P2W': 'Biweekly',
        'R/P0.5W': 'Biweekly',
        'R/P6M': 'Semiannual',
        'R/P2Y': 'Biennial',
        'R/P3Y': 'Triennial',
        'R/P0.33W': 'Three times a week',
        'R/P0.33M': 'Three times a month',
        'R/PT1S': 'Continuously updated',
        'R/P1M': 'Monthly',
        'R/P3M': 'Quarterly',
        'R/P0.5M': 'Semimonthly',
        'R/P4M': 'Three times a year',
        'R/P1W': 'Weekly',
    }
    return frequency_map.get(value, value)
