import urllib, urllib2, json, re, HTMLParser
from urllib2 import Request, urlopen, URLError, HTTPError
import os, time
import logging

from pylons import config

from ckan import plugins as p
from ckan.lib import helpers as h
import ckan.lib.datapreview as datapreview
#from routes import url_for as _routes_default_url_for

log = logging.getLogger(__name__)

try:
    from ckanext.geodatagov.harvesters.base import VALIDATION_PROFILES
except ImportError, e:
    log.critical('Harvester not available %s' % str(e))


def render_datetime_datagov(date_str):
    try:
        value = h.render_datetime(date_str)
    except (ValueError, TypeError):
        return date_str
    return value

def get_validation_profiles():
    return VALIDATION_PROFILES

def get_validation_schema():
    try:
        from ckanext.datajson.harvester_base import VALIDATION_SCHEMA
    except ImportError:
        return None

    return VALIDATION_SCHEMA

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

def get_harvest_source_type(harvester_id):
    source_type = None
    try:
        package = p.toolkit.get_action('harvest_source_show')({}, {'id': harvester_id})
        source_type =  package['source_type']
    except:
        pass

    return source_type

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
}

def is_type_format(type, resource):
    if resource and type in types:
        format = resource.get('format', 'data').lower()
        if format in types[type]:
            return True
    return False

def is_preview_available(resource, pkg_id):

    if not resource.get('url', 'data'):
        return False
	
    format_lower = resource.get('format', 'data').lower()

    if (format_lower in ['csv', 'txt']):
     type = 'csv'
    elif (format_lower == 'xls'):
	 type = 'xls'
    elif (format_lower in ['jpg', 'jpeg', 'png', 'gif']):
	 type = format_lower
    else:
	 return False
	  
    direct_embed = config.get('ckan.preview.direct', '').split()
    if not direct_embed:
        direct_embed = datapreview.DEFAULT_DIRECT_EMBED
		
    loadable_in_iframe = config.get('ckan.preview.loadable', '').split()
    if not loadable_in_iframe:
        loadable_in_iframe = datapreview.DEFAULT_LOADABLE_IFRAME
	
    package = p.toolkit.get_action('package_show')({}, {'id': pkg_id})
    data_dict = {'resource': resource, 'package': package}	

    if (not datapreview.can_be_previewed(data_dict) and format_lower not in direct_embed and format_lower not in loadable_in_iframe):
	 return False

    if(format_lower in direct_embed):
     return True

    url = "http://jsonpdataproxy.appspot.com/?callback=result&url=" + resource.get('url') + "&max-results=1000&type=" + type + "&_=" + str(int(time.time()))

    return preview_response(url)
	
def preview_response(url):
    
    req = Request(url)
    try:
      response = urlopen(req)
    except HTTPError as e:
      log.error("The server couldn\'t fulfill the request. Error code: " + str(e.code))
      return False
    except URLError as e:
      log.error("We failed to reach a server. Reason: " + e.reason)
      return False
    else:
      f = response.read()
      data = json.loads(f[7:-1]) 
      error_exists = data.get('error', 0)
	
    if (error_exists != 0):
      return False
	
    return True
	
def is_web_format(resource):
    return is_type_format('web', resource)

def is_preview_format(resource):
    return is_type_format('preview', resource)

def is_map_format(resource):
    return is_type_format('map', resource)

def get_dynamic_menu():
    filename = os.path.join(os.path.dirname(__file__), 'dynamic_menu/menu.json')
    url = 'http://www.data.gov/wp-content/plugins/datagov-custom/wp_download_links.php'
    time_file = 0
    time_current = time.time()
    try:
        time_file = os.path.getmtime(filename)
    except:
        pass

    # check to see if file is older than 1 hour
    if (time_current - time_file) < 3600:
        file_obj = open(filename)
        file_conent = file_obj.read()
    else:
        # it means file is old, or does not exist
        # fetch new content
        if os.path.exists(filename):
            sec_timeout = 5
        else:
            sec_timeout = 20 # longer urlopen timeout if there is no backup file.

        try:
            resource = urllib2.urlopen(url, timeout=sec_timeout)
        except:
            file_obj = open(filename)
            file_conent = file_obj.read()
            # touch the file, so that it wont keep re-trying and slow down page loading
            os.utime(filename, None)
        else:
            file_obj = open(filename, 'w+')
            file_conent = resource.read()
            file_obj.write(file_conent)

    file_obj.close()
    # remove jsonp wrapper "jsonCallback(JSON);"
    re_obj = re.compile(r"^jsonCallback\((.*)\);$", re.DOTALL)
    json_menu = re_obj.sub(r"\1", file_conent)
    # unescape &amp; or alike
    html_parser =  HTMLParser.HTMLParser()
    json_menu = html_parser.unescape(json_menu)

    menus = json.loads(json_menu)

    return menus
