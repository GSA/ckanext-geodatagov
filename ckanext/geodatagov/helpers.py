import urllib
import logging

from pylons import config

from ckan import plugins as p
from ckan.lib import helpers as h

log = logging.getLogger(__name__)

try:
    from ckanext.geodatagov.harvesters.base import VALIDATION_PROFILES
except ImportError, e:
    log.critical('Harvester not available %s' % str(e))


def get_validation_profiles():
    return VALIDATION_PROFILES

def get_harvest_object_formats(harvest_object_id):
    try:
        obj = p.toolkit.get_action('harvest_object_show')({}, {'id': harvest_object_id})
    except p.toolkit.ObjectNotFound:
        log.info('Harvest object not found {0}:'.format(harvest_object_id))
        return {}

    def get_extra(obj, key, default=None):
        for k, v in obj['extras'].iteritems():
            if k == key:
                return v
        return default

    def format_title(format_name):
        format_titles = {
            'iso': 'ISO-19139',
            'fgdc': 'FGDC',
            'arcgis_json': 'ArcGIS JSON'
        }
        return format_titles[format_name] if format_name in format_titles else format_name

    def format_type(format_name):
        if not format_name:
            return ''

        if format_name in ('iso', 'fgdc'):
            format_type = 'xml'
        elif format_name in ('arcgis'):
            format_type = 'json'
        else:
            format_type = ''
        return format_type


    format_name = get_extra(obj, 'format', 'iso')
    original_format_name = get_extra(obj, 'original_format')

    return {
            'object_format': format_title(format_name),
            'object_format_type': format_type(format_name),
            'original_format': format_title(original_format_name),
            'original_format_type': format_type(original_format_name),
            }

def get_collection_package(collection_package_id):
    package = p.toolkit.get_action('package_show')({}, {'id': collection_package_id})
    return package

def get_harvest_source_link(package_dict):
    harvest_source_id = h.get_pkg_dict_extra(package_dict, 'harvest_source_id', None)
    harvest_source_title = h.get_pkg_dict_extra(package_dict, 'harvest_source_title', None)

    if harvest_source_id and harvest_source_title:
       msg = p.toolkit._('Harvested from')
       url = h.url_for('harvest_read', id=harvest_source_id)
       link = '{msg} <a href="{url}">{title}</a>'.format(url=url, msg=msg, title=harvest_source_title)
       return p.toolkit.literal(link)

    return ''

def resource_preview_custom(resource, pkg_id):

    viewer_url = config.get('ckanext.geodatagov.spatial_preview.url')
    formats = config.get('ckanext.geodatagov.spatial_preview.formats', 'wms kml kmz').strip().split(' ')

    if viewer_url and resource.get('url') and resource.get('format','').lower() in formats:
        params= {
            'url': resource['url'],
            'serviceType': resource['format'].lower(),
        }
        if resource.get('default_srs'):
            params['srs'] = resource['default_srs']

        url = '{viewer_url}?{params}'.format(
                viewer_url=viewer_url,
                params=urllib.urlencode(params))

        return p.toolkit.render_snippet("dataviewer/snippets/data_preview.html",
               data={'embed': False,
               'resource_url': url,
               'raw_resource_url': resource['url']})

    return h.resource_preview(resource, pkg_id)

WEB_FORMATS = ('html', 'data')

def is_web_format(resource):
    if (resource):
        format = resource.get('format', 'data').lower()
        if (format in WEB_FORMATS):
            return True
    return False

def get_homepage_stats():
    '''Return a few key stats'''
    return (
        ('Datasets', 50000, '#'),
        ('Collection Datasets', 10000, ''),
        ('Applications', 100, ''),
    )

def get_latest_datasets(limit=4):
    '''Return a list of the latest datasets on the site.'''
    response = p.toolkit.get_action('package_search')(
            data_dict={'sort': 'metadata_modified desc', 'rows': limit})
    return response['results']
