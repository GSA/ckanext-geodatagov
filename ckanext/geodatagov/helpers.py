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

def is_map_viewer_format(resource):
    viewer_url = config.get('ckanext.geodatagov.spatial_preview.url')
    viewer_formats = config.get('ckanext.geodatagov.spatial_preview.formats', 'wms kml kmz').strip().split(' ')

    return viewer_url and resource.get('url') and resource.get('format', '').lower() in viewer_formats

def get_map_viewer_params(resource, advanced=False):

    params= {
        'url': resource['url'],
        'serviceType': resource.get('format'),
    }
    if resource.get('default_srs'):
        params['srs'] = resource['default_srs']

    if advanced:
        params['mode'] == 'advanced'

    return urllib.urlencode(params)

def resource_preview_custom(resource, pkg_id):

    resource_format = resource.get('format', '').lower()


    if is_map_viewer_format(resource):
        viewer_url = config.get('ckanext.geodatagov.spatial_preview.url')

        url = '{viewer_url}?{params}'.format(
                viewer_url=viewer_url,
                params=get_map_viewer_params(resource))

        return p.toolkit.render_snippet("dataviewer/snippets/data_preview.html",
               data={'embed': False,
               'resource_url': url,
               'raw_resource_url': resource['url']})

    elif resource_format in ('web map application', 'arcgis online map') \
         and ('webmap=' in resource.get('url') or 'services=' in resource.get('url')):
        url = resource['url'].replace('viewer.html', 'embedViewer.html')

        return p.toolkit.render_snippet("dataviewer/snippets/data_preview.html",
               data={'embed': False,
               'resource_url': url,
               'raw_resource_url': resource['url']})

    return h.resource_preview(resource, pkg_id)

types = {
    'web': ('html', 'data', 'esri rest', 'gov', 'org', ''),
    'preview': ('csv', 'xls', 'txt', 'jpg', 'jpeg', 'png', 'gif'),
    # "web map application" is deprecated in favour of "arcgis online map"
    'map': ('wms', 'kml', 'kmz', 'georss', 'web map application', 'arcgis online map'),
    'plotly': ('csv', 'xls', 'excel', 'openxml', 'access', 'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/csv','text/tab-separated-values',
        'application/matlab-mattext/x-matlab', 'application/x-msaccess',
        'application/msaccess', 'application/x-hdf', 'application/x-bag'),
    'cartodb': ('csv', 'xls', 'excel', 'openxml', 'kml', 'geojson', 'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/csv', 'application/vnd.google-earth.kml+xml',
        'application/vnd.geo+json'),
    'arcgis': ('esri rest', 'wms', 'kml', 'kmz', 'application/vnd.google-earth.kml+xml', 'georss')
}

def is_type_format(type, resource):
    if resource and type in types:
        format = resource.get('format', 'data').lower()
        # TODO: convert mimetypes to formats so we dont have to do this.
        mimetype = resource.get('mimetype')
        if mimetype:
            mimetype = mimetype.lower()
        if format in types[type] or mimetype in types[type]:
            return True
    return False

def is_web_format(resource):
    return is_type_format('web', resource)

def is_preview_format(resource):
    return is_type_format('preview', resource)

def is_map_format(resource):
    return is_type_format('map', resource)

def is_plotly_format(resource):
    return is_type_format('plotly', resource)

def is_cartodb_format(resource):
    return is_type_format('cartodb', resource)

def is_arcgis_format(resource):
    return is_type_format('arcgis', resource)

def arcgis_format_query(resource):
    mimetype = resource.get('mimetype')
    kmlstring = re.compile('(kml|kmz)');
    if kmlstring.match(mimetype):
        return 'kml'
    else:
        # wms, georss
        return mimetype

def convert_resource_format(format):
    if format: format = format.lower()
    formats = RESOURCE_MAPPING.keys()
    if format in formats:
        format = RESOURCE_MAPPING[format][1]
    else:
        format = 'Web Page'

    return format

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
