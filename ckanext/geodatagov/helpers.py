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
    'preview': ('csv', 'xls', 'txt', 'jpg', 'jpeg', 'png', 'gif', 'pdf'),
    # "web map application" is deprecated in favour of "arcgis online map"
    'map': ('wms', 'kml', 'kmz', 'georss', 'web map application', 'arcgis online map'),
}

def is_type_format(type, resource):
    if resource and type in types:
        format = resource.get('format', 'data').lower()
        if format in types[type]:
            return True
    return False

def is_web_format(resource):
    return is_type_format('web', resource)

def is_preview_format(resource):
    return is_type_format('preview', resource)

def is_map_format(resource):
    return is_type_format('map', resource)
    
def get_dynamic_menu():
    filename = os.path.join(os.path.dirname(__file__), 'dynamic_menu/menu.json')
    url = config.get('ckanext.geodatagov.dynamic_menu.url', '')
    if not url:
        url = config.get('ckanext.geodatagov.dynamic_menu.url_default', '')

    time_file = 0
    time_current = time.time()
    try:
        time_file = os.path.getmtime(filename)
    except:
        pass

    # check to see if file is older than .5 hour
    if (time_current - time_file) < 3600/2:
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
    json_menu_clean = None
    try:
        json_menu_clean = html_parser.unescape(json_menu)
    except:
        pass

    menus = ''
    if json_menu_clean:
        try:
            menus = json.loads(json_menu_clean)
        except:
            pass

    query = request.environ.get('QUERY_STRING', '');
    submenu_key = None
    category = None
    climate_generic_category = None

    if menus and query:
        query_dict = urlparse.parse_qs(query)
        organization_types = query_dict.get('organization_type', [])
        organizations = query_dict.get('organization', [])
        groups = query_dict.get('groups', [])
        # the three are exclusive
        if sorted([not not organization_types, not not organizations, not not groups]) == [False, False, True]:
            _keys = organization_types or organizations or groups
            if len(_keys) == 1:
                submenu_key = _keys[0]
                if groups:
                    # remove trailing numerics
                    submenu_key = re.sub(r'\d+$', '', submenu_key)
                    submenu_key = submenu_key.lower()

                    categories = query_dict.get('vocab_category_all', [])
                    # some special topic categories got their own sub menus.
                    if submenu_key == 'climate' and categories:
                        cat_food_list = ['Food Resilience', 'Food Production', 'Food Distribution', 'Food Safety and Nutrition', 'Food Security']
                        cat_coastal_list = ['Coastal Flooding']
                        cat_water_list = ['Water']
                        if set(cat_food_list).issuperset(categories):
                            category = 'foodresilience'
                        elif set(cat_coastal_list).issuperset(categories):
                            category = 'coastalflooding'
                        else: # climate special treatment
                            climate_generic_category = categories[0]
                            category = climate_generic_category.replace(" ", "-").lower()
                    submenu_key = category if category else submenu_key

                if submenu_key == 'agriculture':
                    submenu_key = 'food'
                elif submenu_key == 'businessusa':
                    submenu_key = 'business'
                elif submenu_key == 'County Government':
                    submenu_key = 'counties'
                elif submenu_key == 'State Government':
                    submenu_key = 'states'
                elif submenu_key == 'City Government':
                    submenu_key = 'cities'
                elif submenu_key == 'hhs-gov':
                    submenu_key = 'health'

    if submenu_key and menus.get(submenu_key + '_navigation'):
        submenus = []
        for submenu in menus[ submenu_key + '_navigation' ]:
            if re.search(r'/#$', submenu['link']):
                submenu['has_children'] = True
            submenus.append(submenu)
        menus['submenus'] = submenus

        name_pair = {
        'jobs-and-skills': 'Jobs & Skills',
        'development': 'Global Development',
        'research': 'Science & Research',
        'food': 'Agriculture',
        'coastalflooding': ['Climate', 'Coastal Flooding'],
        'foodresilience': ['Climate', 'Food Resilience'],
        }
        if category and climate_generic_category:
            name_pair[category] = ['Climate', climate_generic_category]

        parent = {}
        name = name_pair.get(submenu_key, submenu_key.capitalize())
        if type(name) is list:
            parent['key'] = name[0].lower() # hope nothing breaks here
            parent['url'] = '//www.data.gov/' + parent['key']
            parent['class'] = 'topic-' + parent['key']

        menus['topic_header'] = {
            'multi': True if parent else False,
            'url': '//www.data.gov/' + submenu_key if not parent else [parent['url'], '//www.data.gov/' + submenu_key],
            'name': name,
            'class': 'topic-' + submenu_key if not parent else parent['class'],
        }

    return menus

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