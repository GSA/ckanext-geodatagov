import hashlib
import urlparse
import logging
import paste.auth.auth_tkt
import mimetypes
from paste.auth.auth_tkt import maybe_encode, encode_ip_timestamp
from pylons import request
import ckan.lib.datapreview as datapreview

mimetypes.add_type('application/vnd.ms-fontobject', '.eot')

####  Monkey Patch libraris to make fips work ####

hashlib.md5 = hashlib.sha1
def calculate_digest(ip, timestamp, secret, userid, tokens, user_data):
     secret = maybe_encode(secret)
     userid = maybe_encode(userid)
     tokens = maybe_encode(tokens)
     user_data = maybe_encode(user_data)
     digest0 = hashlib.md5(
         encode_ip_timestamp(ip, timestamp) + secret + userid + '\0'
         + tokens + '\0' + user_data).hexdigest()[:32]
     digest = hashlib.md5(digest0 + secret).hexdigest()[:32]
     return digest
paste.auth.auth_tkt.calculate_digest = calculate_digest

#############################################################

from sqlalchemy import exc
from sqlalchemy import event
from sqlalchemy.pool import Pool

@event.listens_for(Pool, "checkout")
def ping_connection(dbapi_connection, connection_record, connection_proxy):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SELECT 1")
    except:
        raise exc.DisconnectionError()
    cursor.close()

import ckan.plugins as p
import ckan.model as model
import ckanext.harvest.plugin
import json
from ckan.logic.converters import convert_from_extras
from ckan.lib.navl.validators import ignore_missing
from sqlalchemy.util import OrderedDict
import ckanext.geodatagov.commands as cs

log = logging.getLogger(__name__)

try:
    from ckanext.harvest.logic.schema import harvest_source_show_package_schema
except ImportError, e:
    log.critical('Harvester not available %s' % str(e))


RESOURCE_MAPPING = {
    'text/html': ('HTML', 'Web Page'),
    'html': ('HTML', 'Web Page'),
    'application/zip': ('ZIP', 'Zip File'),
    'zip': ('ZIP', 'Zip File'),
    'application/xml': ('XML', 'XML File'),
    'xml': ('XML', 'XML File'),
    'application/x-netcdf': ('NetCDF', 'NetCDF File'),
    'NetCDF': ('NetCDF', 'NetCDF File'),
    'application/x-httpd-php': ('HTML', 'Web Page'),
    'application/pdf': ('PDF', 'PDF File'),
    'pdf': ('PDF', 'PDF File'),
    'application/x-msdos-program': ('EXE', 'Windows Executable Program'),
    'exe': ('EXE', 'Windows Executable Program'),
    'arcgis_rest': ('Esri REST', 'Esri Rest API Endpoint'),
    'esri rest': ('Esri REST', 'Esri Rest API Endpoint'),
    'application/vnd.ms-excel': ('Excel', 'Excel Document'),
    'excel': ('Excel', 'Excel Document'),
    'application/x-tar': ('TAR', 'TAR Compressed File'),
    'tar': ('TAR', 'TAR Compressed File'),
    'wms': ('WMS', 'Web Mapping Service'),
    'application/rar': ('RAR', 'RAR Compressed File'),
    'rar': ('RAR', 'RAR Compressed File'),
    'application/x-qgis': ('QGIS', 'QGIS File'),
    'qgis': ('QGIS', 'QGIS File'),
    'wfs': ('WFS', 'Web Feature Service'),
    'text/plain': ('TXT', 'Text File'),
    'txt': ('TXT', 'Text File'),
    'application/msaccess': ('Access', 'Access Database'),
    'access': ('Access', 'Access Database'),
    'image/jpeg': ('JPEG', 'JPEG Image File'),
    'jpg': ('JPG', 'JPG Image File'),
    'jpeg': ('JPG', 'JPG Image File'),
    'audio/prs.sid': ('MrSID', 'MrSID'),
    'mrsid': ('MrSID', 'MrSID'),
    'kml': ('KML', 'KML File'),
    'image/tiff': ('TIFF', 'TIFF Image File'),
    'tiff': ('TIFF', 'TIFF Image File'),
    'kmz': ('KMZ', 'KMZ File'),
    'wcs': ('WCS', 'Web Coverage Service'),
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ('OpenXML', 'OpenXML'),
    'openXML': ('OpenXML', 'OpenXML'),
    'text/x-perl': ('Perl', 'Perl Script'),
    'perl': ('Perl', 'Perl Script'),
    'application/msword': ('DOC', 'Microsoft Word File'),
    'doc': ('DOC', 'Microsoft Word File'),
    'text/csv': ('CSV', 'Comma Separated Values File'),
    'csv': ('CSV', 'Comma Separated Values File'),
    'image/x-ms-bmp': ('BMP', 'Bitmap Image File'),
    'bmp': ('BMP', 'Bitmap Image File'),
    'chemical/x-xyz': ('XYZ', 'XYZ'),
    'xyz': ('XYZ', 'XYZ'),
    'image/png': ('PNG', 'PNG Image File'),
    'png': ('PNG', 'PNG Image File'),
    'web map application': ('ArcGIS Online Map', 'ArcGIS Online Map'),
    'arcgis map preview': ('ArcGIS Map Preview', 'ArcGIS Map Preview'),
    'arcgis map service': ('ArcGIS Map Service', 'ArcGIS Map Service'),
}



def split_tags(tag):
    tags = []
    for tag in tag.split(','):
        tags.extend(tag.split('>'))
    return [tag.strip().lower() for tag in tags]

##copied from harvest but deals withe single item list keys like validation
def harvest_source_convert_from_config(key,data,errors,context):
    config = data[key]
    if config:
        config_dict = json.loads(config)
        for key, value in config_dict.iteritems():
            if isinstance(value, list):
                data[(key,)] = value[0]
            else:
                data[(key,)] = value

class DataGovHarvest(ckanext.harvest.plugin.Harvest):

    def package_form(self):
        return 'source/geodatagov_source_form.html'

    def show_package_schema(self):
        '''
        Returns the schema for mapping package data from the database into a
        format suitable for the form
        '''

        schema = harvest_source_show_package_schema()
        schema['config'] = [convert_from_extras, harvest_source_convert_from_config, ignore_missing]
        return schema

    def dataset_facets(self, facets_dict, package_type):

        if package_type <> 'harvest':
            return facets_dict

        return OrderedDict([('organization_type', 'Organization Types'),
                            ('frequency', 'Frequency'),
                            ('source_type','Type'),
                            ('organization', 'Organizations'),
                            #('publisher', 'Publisher'),							
                           ])

    def organization_facets(self, facets_dict, organization_type, package_type):

        if package_type <> 'harvest':
            return facets_dict

        return OrderedDict([('frequency', 'Frequency'),
                            ('source_type','Type'),
                            #('publisher', 'Publisher'),
                           ])

def get_filename_and_extension(resource):
    url = resource.get('url').rstrip('/')
    if '?' in url:
        return '', ''
    if 'URL' in url:
        return '', ''
    url = urlparse.urlparse(url).path
    split = url.split('/')
    last_part = split[-1]
    ending = last_part.split('.')[-1].lower()
    if len(ending) in [2,3,4] and len(last_part) > 4 and len(split) > 1:
        return last_part, ending
    return '', ''


def change_resource_details(resource):
    formats = RESOURCE_MAPPING.keys()
    resource_format = resource.get('format', '').lower().lstrip('.')
    filename, extension = get_filename_and_extension(resource)
    if not resource_format:
        resource_format = extension
    if resource_format in formats:
        resource['format'] = RESOURCE_MAPPING[resource_format][0]
        if resource.get('name', '') in ['Unnamed resource', '', None]:
            resource['name'] = RESOURCE_MAPPING[resource_format][1]
            if filename:
                resource['name'] = resource['name']
    elif resource.get('name', '') in ['Unnamed resource', '', None]:
        if extension and not resource_format:
            resource['format'] = extension.upper()
        resource['name'] = 'Web Page'

    if filename and not resource.get('description'):
        resource['description'] = filename


def related_create_auth_fn(context, data_dict=None):
    return {'success': False}


def related_update_auth_fn(context, data_dict=None):
    return {'success': False}


class Demo(p.SingletonPlugin):

    p.implements(p.IConfigurer)
    p.implements(p.IConfigurable)
    p.implements(p.IPackageController, inherit=True)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IActions, inherit=True)
    p.implements(p.IAuthFunctions)
    p.implements(p.IFacets, inherit=True)
    edit_url = None

    p.implements(p.IRoutes, inherit=True)

    UPDATE_CATEGORY_ACTIONS = ['package_update', 'dataset_update']
    ROLLUP_SAVE_ACTIONS = ['package_create', 'dataset_create', 'package_update', 'dataset_update']

    # source ignored as queried diretly
    EXTRAS_ROLLUP_KEY_IGNORE = ["metadata-source", "tags"]

    def before_action(self, action_name, context, data_dict):
        if action_name in self.UPDATE_CATEGORY_ACTIONS:
            pkg_dict = p.toolkit.get_action('package_show')(context, {'id': data_dict['id']})
            if 'groups' not in data_dict:
                data_dict['groups'] = pkg_dict.get('groups', [])
            cats = {}
            for extra in pkg_dict.get('extras', []):
                if extra['key'].startswith('__category_tag_'):
                        cats[extra['key']] = extra['value']
            extras = data_dict.get('extras', [])
            for item in extras:
                if item['key'] in cats:
                    del cats[item['key']]
            for cat in cats:
                extras.append({'key': cat, 'value': cats[cat]})

        ### make sure rollup happens after any other actions
        if action_name in self.ROLLUP_SAVE_ACTIONS:
            extras_rollup = {}
            new_extras = []
            for extra in data_dict.get('extras', []):
                if extra['key'] in self.EXTRAS_ROLLUP_KEY_IGNORE:
                    new_extras.append(extra)
                else:
                    extras_rollup[extra['key']] = extra['value']
            if extras_rollup:
                new_extras.append({'key': 'extras_rollup',
                                   'value': json.dumps(extras_rollup)})
            data_dict['extras'] = new_extras

    ## IRoutes
    def before_map(self, map):
        controller = 'ckanext.geodatagov.controllers:ViewController'
        map.connect('map_viewer', '/viewer',controller=controller, action='show')
        map.redirect('/', '/dataset')
        return map

    ## IConfigurer
    def update_config(self, config):
        # add template directory
        p.toolkit.add_template_directory(config, 'templates')
        p.toolkit.add_public_directory(config, 'public')
        p.toolkit.add_resource('fanstatic_library', 'geodatagov')

    def configure(self, config):
        self.__class__.edit_url = config.get('saml2.user_edit')


    @classmethod
    def saml2_user_edit_url(cls):
        return cls.edit_url

    ## IPackageController

    def before_view(self, pkg_dict):

        for num, extra in enumerate(pkg_dict.get('extras', [])):
            if extra['key'] == 'tags':
                tags = pkg_dict.get('tags', [])
                tags.extend([dict(name=tag, display_name=tag) for tag
                             in split_tags(extra['value'])])
                pkg_dict['tags'] = tags
                pkg_dict['extras'].pop(num)
                break

        organization = pkg_dict.get('organization')
        if organization:
            result = model.Session.query(model.GroupExtra.value).filter_by(
                key='organization_type', group_id=organization['id']).first()
            if result:
                organization['organization_type'] = result[0]


        return pkg_dict

    def before_index(self, pkg_dict):

        tags = pkg_dict.get('tags', [])
        tags.extend(tag for tag in split_tags(pkg_dict.get('extras_tags','')))
        pkg_dict['tags'] = tags

        org_name = pkg_dict['organization']
        group = model.Group.get(org_name)
        if group and ('organization_type' in group.extras):
            pkg_dict['organization_type'] = group.extras['organization_type']

        title_string = pkg_dict.get('title_string')
        if title_string:
            pkg_dict['title_string'] = title_string.strip().lower()

        # category tags
        cats = {}
        for extra in pkg_dict:
            if extra.startswith('__category_tag_'):
                cat = pkg_dict[extra]
                if cat:
                    try:
                        cat_list = json.loads(cat)
                        cats['vocab_%s' % extra] = cat_list
                        new_list = cats.get('vocab_category_all', [])
                        new_list.extend(cat_list)
                        cats['vocab_category_all'] = new_list
                    except ValueError:
                        pass
        pkg_dict.update(cats)

        return pkg_dict

    def before_search(self, pkg_dict):

        fq = pkg_dict.get('fq', '')

        if pkg_dict.get('sort') in (None, 'rank'):
            pkg_dict['sort'] = 'views_recent desc'
		
        if pkg_dict.get('sort') in ('none'):
            pkg_dict['sort'] = 'score desc, name asc'

        # only show collections on bulk update page and when the facet is explictely added

        if 'collection_package_id' not in fq and 'bulk_process' not in request.path:
            pkg_dict['fq'] = fq + ' -collection_package_id:["" TO *]'

        return pkg_dict


    def after_show(self, context, data_dict):

        current_extras = data_dict.get('extras', [])
        new_extras =[]
        for extra in current_extras:
            if extra['key'] == 'extras_rollup':
                rolledup_extras = json.loads(extra['value'])
                for key, value in rolledup_extras.iteritems():
                    new_extras.append({"key": key, "value": value})
            else:
                new_extras.append(extra)
        data_dict['extras'] = new_extras

        if 'resources' in data_dict:
            for resource in data_dict['resources']:
                change_resource_details(resource)
        return data_dict

    ## ITemplateHelpers

    def get_helpers(self):
        from ckanext.geodatagov import helpers as geodatagov_helpers
        return {
                'get_harvest_object_formats': geodatagov_helpers.get_harvest_object_formats,
                'get_harvest_source_link': geodatagov_helpers.get_harvest_source_link,
                'get_validation_profiles': geodatagov_helpers.get_validation_profiles,
                'get_validation_schema': geodatagov_helpers.get_validation_schema,
                'get_collection_package': geodatagov_helpers.get_collection_package,
                'resource_preview_custom': geodatagov_helpers.resource_preview_custom,
                'is_web_format': geodatagov_helpers.is_web_format,
                'saml2_user_edit_url': self.saml2_user_edit_url,
                'is_preview_format': geodatagov_helpers.is_preview_format,
                'is_preview_available': geodatagov_helpers.is_preview_available,
                'is_map_format': geodatagov_helpers.is_map_format,
                'is_map_viewer_format' : geodatagov_helpers.is_map_viewer_format,
                'get_map_viewer_params': geodatagov_helpers.get_map_viewer_params,
                'render_datetime_datagov': geodatagov_helpers.render_datetime_datagov,
                'get_dynamic_menu': geodatagov_helpers.get_dynamic_menu,
                'get_harvest_source_type': geodatagov_helpers.get_harvest_source_type,
                }

    ## IActions

    def get_actions(self):

        from ckanext.geodatagov import logic as geodatagov_logic

        return {
            'resource_show': geodatagov_logic.resource_show,
            'organization_show': geodatagov_logic.organization_show,
            'location_search': geodatagov_logic.location_search,
            'organization_list': geodatagov_logic.organization_list,
            'group_show': geodatagov_logic.group_show,
            'group_catagory_tag_update': geodatagov_logic.group_catagory_tag_update,
            'datajson_create': geodatagov_logic.datajson_create,
            'datajson_update': geodatagov_logic.datajson_update,
            'package_show_rest': geodatagov_logic.package_show_rest,
        }

    ## IAuthFunctions

    def get_auth_functions(self):

        from ckanext.geodatagov import auth as geodatagov_auth

        return {
            'related_create': geodatagov_auth.related_create,
            'related_update': geodatagov_auth.related_update,
            'group_catagory_tag_update': geodatagov_auth.group_catagory_tag_update,
        }

    ## IFacets

    def dataset_facets(self, facets_dict, package_type):

        if package_type != 'dataset':
            return facets_dict

        return OrderedDict([('metadata_type','Dataset Type'),
                            ('tags','Tags'),
                            ('res_format', 'Formats'),
                            ('groups', 'Topics'),
                            ('organization_type', 'Organization Types'),
                            ('organization', 'Organizations'),
                            ('publisher', 'Publisher'),
                            ('vocab_category_all', 'Topic Categories'),                            
                           ## ('extras_progress', 'Progress'),
                           ])

    def organization_facets(self, facets_dict, organization_type, package_type):

        if not package_type:
            return OrderedDict([('metadata_type','Dataset Type'),
                                ('tags','Tags'),
                                ('res_format', 'Formats'),
                                ('groups', 'Topics'),
                                ('harvest_source_title', 'Harvest Source'),
                                ('capacity', 'Visibility'),
                                ('dataset_type', 'Resource Type'),
                                ('publisher', 'Publisher'),
                               ])
        else:
            return facets_dict

    def group_facets(self, facets_dict, organization_type, package_type):

        # get the categories key
        group_id = p.toolkit.c.group_dict['id']
        key = 'vocab___category_tag_%s' % group_id
        if not package_type:
            return OrderedDict([('metadata_type','Dataset Type'),
                                ('organization_type', 'Organization Types'),
                                ('tags','Tags'),
                                ('res_format', 'Formats'),
                                ('organization', 'Organizations'),
                                (key, 'Categories'),
                                #('publisher', 'Publisher'),
                               ])
        else:
            return facets_dict

