import hashlib
import logging
import paste.auth.auth_tkt
from paste.auth.auth_tkt import maybe_encode, encode_ip_timestamp
from pylons import request

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
    'application/msaccess': ('Acesss', 'Access Database'),
    'access': ('Acesss', 'Access Database'),
    'image/jpeg': ('JPEG', 'JPEG Image File'),
    'jpeg': ('JPEG', 'JPEG Image File'),
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
    'text/csv': ('CSV', 'Comma Seperated Values File'),
    'csv': ('CSV', 'Comma Seperated Values File'),
    'image/x-ms-bmp': ('BMP', 'Bitmap Image File'),
    'bmp': ('BMP', 'Bitmap Image File'),
    'chemical/x-xyz': ('XYZ', 'XYZ'),
    'xyz': ('XYZ', 'XYZ'),
    'image/png': ('PNG', 'PNG Image File'),
    'png': ('PNG', 'PNG Image File'),
}



def split_tags(tag):
    tags = []
    for tag in tag.split(','):
        tags.extend(tag.split('>'))
    return [tag.strip() for tag in tags]

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
                           ])

    def organization_facets(self, facets_dict, organization_type, package_type):

        if package_type <> 'harvest':
            return facets_dict

        return OrderedDict([('frequency', 'Frequency'),
                            ('source_type','Type'),
                           ])

def get_filename_and_extension(resource):
    url = resource.get('url').rstrip('/')
    if '?' in url:
        return '', ''
    split = url.split('/')
    last_part = split[-1]
    ending = last_part.split('.')[-1].lower()
    if len(ending) in [2,3,4] and len(last_part) > 4 and len(split) > 1:
        return last_part, ending
    return '', ''


def change_resource_details(resource):
    formats = RESOURCE_MAPPING.keys()
    resource_format = resource.get('format', '').lower()
    filename, extension = get_filename_and_extension(resource)
    if not resource_format:
        resource_format = extension
    if resource_format in formats:
        resource['format'] = RESOURCE_MAPPING[resource_format][0]
        if resource.get('name') == 'Unnamed resource':
            resource['name'] = RESOURCE_MAPPING[resource_format][1]
            if filename:
                resource['name'] = resource['name']
    elif resource.get('name') == 'Unnamed resource':
        if extension:
            resource['format'] = extension.upper()
        resource['name'] = 'Web Page'

    if filename and not resource.get('description'):
        resource['description'] = filename


class Demo(p.SingletonPlugin):

    p.implements(p.IConfigurer)
    p.implements(p.IPackageController, inherit=True)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.IFacets, inherit=True)
    p.implements(p.IActions)

    def update_config(self, config):
        # add template directory
        p.toolkit.add_template_directory(config, 'templates')
        p.toolkit.add_public_directory(config, 'public')
        p.toolkit.add_resource('fanstatic_library', 'geodatagov')


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

        return pkg_dict

    def before_search(self, pkg_dict):

        fq = pkg_dict.get('fq', '')

        # only show collections on bulk update page and when the facet is explictely added

        if 'collection_package_id' not in fq and 'bulk_process' not in request.path:
            pkg_dict['fq'] = fq + ' -collection_package_id:["" TO *]'

        return pkg_dict


    def after_show(self, context, data_dict):

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
                'get_collection_package': geodatagov_helpers.get_collection_package,
                'resource_preview_custom': geodatagov_helpers.resource_preview_custom,
                'is_web_format': geodatagov_helpers.is_web_format,
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
        }

    ## IAuthFunctions

    def get_auth_functions(self):

        from ckanext.geodatagov import auth as geodatagov_auth

        return {
            'related_create': geodatagov_auth.related_create,
            'related_update': geodatagov_auth.related_update,
            'user_create': geodatagov_auth.user_create,
        }

    ## IFacets

    def dataset_facets(self, facets_dict, package_type):

        if package_type != 'dataset':
            return facets_dict

        return OrderedDict([('tags','Tags'),
                            ('res_format', 'Formats'),
                            ('groups', 'Groups'),
                            ('organization_type', 'Organization Types'),
                            ('organization', 'Organizations'),
                           ])

    def organization_facets(self, facets_dict, organization_type, package_type):

        if not package_type:
            return OrderedDict([('tags','Tags'),
                                ('res_format', 'Formats'),
                                ('groups', 'Groups'),
                                ('harvest_source_title', 'Harvest Source'),
                                ('capacity', 'Visibility'),
                                ('dataset_type', 'Dataset Type'),
                               ])
        else:
            return facets_dict

    def group_facets(self, facets_dict, organization_type, package_type):

        if not package_type:
            return OrderedDict([('organization_type', 'Organization Types'),
                                ('tags','Tags'),
                                ('res_format', 'Formats'),
                                ('organization', 'Organizations'),
                               ])
        else:
            return facets_dict
