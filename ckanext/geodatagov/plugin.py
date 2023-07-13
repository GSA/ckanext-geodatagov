import hashlib
import urllib.parse
import logging
import mimetypes

from ckan.plugins.toolkit import request, requires_ckan_version

from ckan.lib.munge import munge_tag
import ckanext.geodatagov.model as geodatagovmodel
from ckan import __version__ as ckan_version

requires_ckan_version("2.9")

from . import blueprint
import ckanext.geodatagov.cli as cli

mimetypes.add_type('application/vnd.ms-fontobject', '.eot')

# the patch below caused s3 upload fail. need to keep a copy of md5
hashlib.md5_orig = hashlib.md5

#  Monkey Patch libraris to make fips work # ## #
hashlib.md5 = hashlib.sha1

# ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ##

from sqlalchemy import exc
from sqlalchemy import event
from sqlalchemy.pool import Pool


@event.listens_for(Pool, "checkout")
def ping_connection(dbapi_connection, connection_record, connection_proxy):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SELECT 1")
    except BaseException:
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
except ImportError as e:
    log.critical('Harvester not available %s' % str(e))


RESOURCE_MAPPING = {

    # ArcGIS File Types
    'esri rest': ('Esri REST', 'Esri REST API Endpoint'),
    'arcgis_rest': ('Esri REST', 'Esri REST API Endpoint'),
    'web map application': ('ArcGIS Online Map', 'ArcGIS Online Map'),
    'arcgis map preview': ('ArcGIS Map Preview', 'ArcGIS Map Preview'),
    'arcgis map service': ('ArcGIS Map Service', 'ArcGIS Map Service'),
    'wms': ('WMS', 'ArcGIS Web Mapping Service'),
    'wfs': ('WFS', 'ArcGIS Web Feature Service'),
    'wcs': ('WCS', 'Web Coverage Service'),

    # CSS File Types
    'css': ('CSS', 'Cascading Style Sheet File'),
    'text/css': ('CSS', 'Cascading Style Sheet File'),

    # CSV File Types
    'csv': ('CSV', 'Comma Separated Values File'),
    'text/csv': ('CSV', 'Comma Separated Values File'),

    # EXE File Types
    'exe': ('EXE', 'Windows Executable Program'),
    'application/x-msdos-program': ('EXE', 'Windows Executable Program'),

    # HyperText Markup Language (HTML) File Types
    'htx': ('HTML', 'Web Page'),
    'htm': ('HTML', 'Web Page'),
    'html': ('HTML', 'Web Page'),
    'htmls': ('HTML', 'Web Page'),
    'xhtml': ('HTML', 'Web Page'),
    'text/html': ('HTML', 'Web Page'),
    'application/xhtml+xml': ('HTML', 'Web Page'),
    'application/x-httpd-php': ('HTML', 'Web Page'),

    # Image File Types - BITMAP
    'bm': ('BMP', 'Bitmap Image File'),
    'bmp': ('BMP', 'Bitmap Image File'),
    'pbm': ('BMP', 'Bitmap Image File'),
    'xbm': ('BMP', 'Bitmap Image File'),
    'image/bmp': ('BMP', 'Bitmap Image File'),
    'image/x-ms-bmp': ('BMP', 'Bitmap Image File'),
    'image/x-xbitmap': ('BMP', 'Bitmap Image File'),
    'image/x-windows-bmp': ('BMP', 'Bitmap Image File'),
    'image/x-portable-bitmap': ('BMP', 'Bitmap Image File'),

    # Image File Types - Graphics Interchange Format (GIF)
    'gif': ('GIF', 'GIF Image File'),
    'image/gif': ('GIF', 'GIF Image File'),

    # Image File Types - ICON
    'ico': ('ICO', 'Icon Image File'),
    'image/x-icon': ('ICO', 'Icon Image File'),

    # Image File Types - JPEG
    'jpe': ('JPEG', 'JPEG Image File'),
    'jpg': ('JPEG', 'JPEG Image File'),
    'jps': ('JPEG', 'JPEG Image File'),
    'jpeg': ('JPEG', 'JPEG Image File'),
    'pjpeg': ('JPEG', 'JPEG Image File'),
    'image/jpeg': ('JPEG', 'JPEG Image File'),
    'image/pjpeg': ('JPEG', 'JPEG Image File'),
    'image/x-jps': ('JPEG', 'JPEG Image File'),
    'image/x-citrix-jpeg': ('JPEG', 'JPEG Image File'),

    # Image File Types - PNG
    'png': ('PNG', 'PNG Image File'),
    'x-png': ('PNG', 'PNG Image File'),
    'image/png': ('PNG', 'PNG Image File'),
    'image/x-citrix-png': ('PNG', 'PNG Image File'),

    # Image File Types - Scalable Vector Graphics (SVG)
    'svg': ('SVG', 'SVG Image File'),
    'image/svg+xml': ('SVG', 'SVG Image File'),

    # Image File Types - Tagged Image File Format (TIFF)
    'tif': ('TIFF', 'TIFF Image File'),
    'tiff': ('TIFF', 'TIFF Image File'),
    'image/tiff': ('TIFF', 'TIFF Image File'),
    'image/x-tiff': ('TIFF', 'TIFF Image File'),

    # JSON File Types
    'json': ('JSON', 'JSON File'),
    'text/x-json': ('JSON', 'JSON File'),
    'application/json': ('JSON', 'JSON File'),

    # KML File Types
    'kml': ('KML', 'KML File'),
    'kmz': ('KML', 'KMZ File'),
    'application/vnd.google-earth.kml+xml': ('KML', 'KML File'),
    'application/vnd.google-earth.kmz': ('KML', 'KMZ File'),

    # MS Access File Types
    'mdb': ('ACCESS', 'MS Access Database'),
    'access': ('ACCESS', 'MS Access Database'),
    'application/mdb': ('ACCESS', 'MS Access Database'),
    'application/msaccess': ('ACCESS', 'MS Access Database'),
    'application/x-msaccess': ('ACCESS', 'MS Access Database'),
    'application/vnd.msaccess': ('ACCESS', 'MS Access Database'),
    'application/vnd.ms-access': ('ACCESS', 'MS Access Database'),

    # MS Excel File Types
    'xl': ('EXCEL', 'MS Excel File'),
    'xla': ('EXCEL', 'MS Excel File'),
    'xlb': ('EXCEL', 'MS Excel File'),
    'xlc': ('EXCEL', 'MS Excel File'),
    'xld': ('EXCEL', 'MS Excel File'),
    'xls': ('EXCEL', 'MS Excel File'),
    'xlsx': ('EXCEL', 'MS Excel File'),
    'xlsm': ('EXCEL', 'MS Excel File'),
    'excel': ('EXCEL', 'MS Excel File'),
    'openXML': ('EXCEL', 'MS Excel File'),
    'application/excel': ('EXCEL', 'MS Excel File'),
    'application/x-excel': ('EXCEL', 'MS Excel File'),
    'application/x-msexcel': ('EXCEL', 'MS Excel File'),
    'application/vnd.ms-excel': ('EXCEL', 'MS Excel File'),
    'application/vnd.ms-excel.sheet.macroEnabled.12': ('EXCEL', 'MS Excel File'),
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ('EXCEL', 'MS Excel File'),

    # MS PowerPoint File Types
    'ppt': ('POWERPOINT', 'MS PowerPoint File'),
    'pps': ('POWERPOINT', 'MS PowerPoint File'),
    'pptx': ('POWERPOINT', 'MS PowerPoint File'),
    'ppsx': ('POWERPOINT', 'MS PowerPoint File'),
    'pptm': ('POWERPOINT', 'MS PowerPoint File'),
    'ppsm': ('POWERPOINT', 'MS PowerPoint File'),
    'sldx': ('POWERPOINT', 'MS PowerPoint File'),
    'sldm': ('POWERPOINT', 'MS PowerPoint File'),
    'application/powerpoint': ('POWERPOINT', 'MS PowerPoint File'),
    'application/mspowerpoint': ('POWERPOINT', 'MS PowerPoint File'),
    'application/x-mspowerpoint': ('POWERPOINT', 'MS PowerPoint File'),
    'application/vnd.ms-powerpoint': ('POWERPOINT', 'MS PowerPoint File'),
    'application/vnd.ms-powerpoint.presentation.macroEnabled.12': ('POWERPOINT', 'MS PowerPoint File'),
    'application/vnd.ms-powerpoint.slideshow.macroEnabled.12': ('POWERPOINT', 'MS PowerPoint File'),
    'application/vnd.ms-powerpoint.slide.macroEnabled.12': ('POWERPOINT', 'MS PowerPoint File'),
    'application/vnd.openxmlformats-officedocument.presentationml.slide': ('POWERPOINT', 'MS PowerPoint File'),
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': ('POWERPOINT', 'MS PowerPoint File'),
    'application/vnd.openxmlformats-officedocument.presentationml.slideshow': ('POWERPOINT', 'MS PowerPoint File'),

    # MS Word File Types
    'doc': ('DOC', 'MS Word File'),
    'docx': ('DOC', 'MS Word File'),
    'docm': ('DOC', 'MS Word File'),
    'word': ('DOC', 'MS Word File'),
    'application/msword': ('DOC', 'MS Word File'),
    'application/vnd.ms-word.document.macroEnabled.12': ('DOC', 'MS Word File'),
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ('DOC', 'MS Word File'),

    # Network Common Data Form (NetCDF) File Types
    'nc': ('CDF', 'NetCDF File'),
    'cdf': ('CDF', 'NetCDF File'),
    'netcdf': ('CDF', 'NetCDF File'),
    'application/x-netcdf': ('NETCDF', 'NetCDF File'),

    # PDF File Types
    'pdf': ('PDF', 'PDF File'),
    'application/pdf': ('PDF', 'PDF File'),

    # PERL File Types
    'pl': ('PERL', 'Perl Script File'),
    'pm': ('PERL', 'Perl Module File'),
    'perl': ('PERL', 'Perl Script File'),
    'text/x-perl': ('PERL', 'Perl Script File'),

    # QGIS File Types
    'qgis': ('QGIS', 'QGIS File'),
    'application/x-qgis': ('QGIS', 'QGIS File'),

    # RAR File Types
    'rar': ('RAR', 'RAR Compressed File'),
    'application/rar': ('RAR', 'RAR Compressed File'),
    'application/vnd.rar': ('RAR', 'RAR Compressed File'),
    'application/x-rar-compressed': ('RAR', 'RAR Compressed File'),

    # Resource Description Framework (RDF) File Types
    'rdf': ('RDF', 'RDF File'),
    'application/rdf+xml': ('RDF', 'RDF File'),

    # Rich Text Format (RTF) File Types
    'rt': ('RICH TEXT', 'Rich Text File'),
    'rtf': ('RICH TEXT', 'Rich Text File'),
    'rtx': ('RICH TEXT', 'Rich Text File'),
    'text/richtext': ('RICH TEXT', 'Rich Text File'),
    'text/vnd.rn-realtext': ('RICH TEXT', 'Rich Text File'),
    'application/rtf': ('RICH TEXT', 'Rich Text File'),
    'application/x-rtf': ('RICH TEXT', 'Rich Text File'),

    # SID File Types - Primary association: Commodore64 (C64)?
    'sid': ('SID', 'SID File'),
    'mrsid': ('SID', 'SID File'),
    'audio/psid': ('SID', 'SID File'),
    'audio/x-psid': ('SID', 'SID File'),
    'audio/sidtune': ('SID', 'MID File'),
    'audio/x-sidtune': ('SID', 'SID File'),
    'audio/prs.sid': ('SID', 'SID File'),

    # Tab Separated Values (TSV) File Types
    'tsv': ('TSV', 'Tab Separated Values File'),
    'text/tab-separated-values': ('TSV', 'Tab Separated Values File'),

    # Tape Archive (TAR) File Types
    'tar': ('TAR', 'TAR Compressed File'),
    'application/x-tar': ('TAR', 'TAR Compressed File'),

    # Text File Types
    'txt': ('TEXT', 'Text File'),
    'text/plain': ('TEXT', 'Text File'),

    # Extensible Markup Language (XML) File Types
    'xml': ('XML', 'XML File'),
    'text/xml': ('XML', 'XML File'),
    'application/xml': ('XML', 'XML File'),

    # XYZ File Format File Types
    'xyz': ('XYZ', 'XYZ File'),
    'chemical/x-xyz': ('XYZ', 'XYZ File'),

    # ZIP File Types
    'zip': ('ZIP', 'Zip File'),
    'application/zip': ('ZIP', 'Zip File'),
    'multipart/x-zip': ('ZIP', 'Zip File'),
    'application/x-compressed': ('ZIP', 'Zip File'),
    'application/x-zip-compressed': ('ZIP', 'Zip File'),

}


def split_tags(tag):
    tags = []
    for tag in tag.split(', '):
        tags.extend(tag.split('>'))
    return [munge_tag(tag) for tag in tags if munge_tag(tag) != '']


# copied from harvest but deals withe single item list keys like validation
def harvest_source_convert_from_config(key, data, errors, context):
    config = data[key]
    if config:
        config_dict = json.loads(config)
        for key, value in list(config_dict.items()):
            if isinstance(value, list):
                data[(key, )] = value[0]
            else:
                data[(key, )] = value


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

        if package_type != 'harvest':
            return facets_dict

        return OrderedDict([('organization_type', 'Organization Types'),
                            ('frequency', 'Frequency'),
                            ('source_type', 'Type'),
                            ('organization', 'Organizations'),
                            # ('publisher', 'Publisher'),
                            ])

    def organization_facets(self, facets_dict, organization_type, package_type):

        if package_type != 'harvest':
            return facets_dict

        return OrderedDict([('frequency', 'Frequency'),
                            ('source_type', 'Type'),
                            # ('publisher', 'Publisher'),
                            ])


def get_filename_and_extension(resource):
    url = resource.get('url').rstrip('/')
    if '?' in url:
        return '', ''
    if 'URL' in url:
        return '', ''
    url = urllib.parse.urlparse(url).path
    split = url.split('/')
    last_part = split[-1]
    ending = last_part.split('.')[-1].lower()
    if len(ending) in [2, 3, 4] and len(last_part) > 4 and len(split) > 1:
        return last_part, ending
    return '', ''


def change_resource_details(resource):
    formats = list(RESOURCE_MAPPING.keys())
    resource_format = resource.get('format', '').lower().lstrip('.')
    filename, extension = get_filename_and_extension(resource)
    if not resource_format:
        resource_format = extension
    if resource.get('name', '') in ['Unnamed resource', '', None]:
        resource['no_real_name'] = True
    if resource_format in formats:
        resource['format'] = RESOURCE_MAPPING[resource_format][0]
        if resource.get('name', '') in ['Unnamed resource', '', None]:
            resource['name'] = RESOURCE_MAPPING[resource_format][1]
            if filename:
                resource['name'] = resource['name']
    elif resource.get('name', '') in ['Unnamed resource', '', None]:
        if extension and not resource_format:
            resource['format'] = extension.upper()
        resource['name'] = 'Web Resource'

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
    p.implements(p.IClick)

    def get_commands(self) -> list:
        return cli.get_commands()

    # IConfigurer
    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'templates')
        p.toolkit.add_resource('fanstatic_library', 'geodatagov')

    edit_url = None

    def configure(self, config):
        log.info('plugin initialized: %s', self.__class__.__name__)
        self.__class__.edit_url = config.get('saml2.user_edit')

    @classmethod
    def saml2_user_edit_url(cls):
        return cls.edit_url

    # IPackageController

    def before_dataset_view(self, pkg_dict):

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
            result = model.Session.query(model.GroupExtra.value).filter_by(
                key='terms_of_use', state='active',
                group_id=organization['id']).first()
            if result:
                organization['terms_of_use'] = result[0]

        return pkg_dict

    def before_dataset_index(self, pkg_dict):

        tags = pkg_dict.get('tags', [])
        tags.extend(tag for tag in split_tags(pkg_dict.get('extras_tags', '')))
        pkg_dict['tags'] = tags

        org_name = pkg_dict['organization']
        group = model.Group.get(org_name)
        if group and ('organization_type' in group.extras):
            pkg_dict['organization_type'] = group.extras['organization_type']
        if group and ('terms_of_use' in group.extras):
            pkg_dict['terms_of_use'] = group.extras['terms_of_use']

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

    def before_dataset_search(self, search_params):

        fq = search_params.get('fq', '')

        if search_params.get('sort') in (None, 'rank'):
            search_params['sort'] = 'views_recent desc'

        if search_params.get('sort') in ('none'):
            search_params['sort'] = 'score desc, name asc'

        # only show collections on bulk update page and when the facet is explictely added
        try:
            path = request.path
        except BaseException:
            # when there is no requests we get a
            # TypeError: No object (name: request) has been registered for this thread
            path = ''

        if 'collection_package_id' not in fq and 'bulk_process' not in path:
            log.info('Added FQ to collection_package_id')
            fq += ' -collection_package_id:["" TO *]'
        else:
            log.info('NOT Added FQ to collection_package_id')

        search_params['fq'] = fq
        return search_params

    def after_dataset_show(self, context, data_dict):

        current_extras = data_dict.get('extras', [])
        new_extras = []
        for extra in current_extras:
            if extra['key'] == 'extras_rollup':
                rolledup_extras = json.loads(extra['value'])
                for key, value in list(rolledup_extras.items()):
                    new_extras.append({"key": key, "value": value})
            else:
                new_extras.append(extra)
        data_dict['extras'] = new_extras

        if 'resources' in data_dict:
            for resource in data_dict['resources']:
                change_resource_details(resource)
        return data_dict

    # ITemplateHelpers

    def get_helpers(self):
        from ckanext.geodatagov import helpers as geodatagov_helpers
        return {
            'get_validation_profiles': geodatagov_helpers.get_validation_profiles,
            'get_validation_schema': geodatagov_helpers.get_validation_schema,
            'saml2_user_edit_url': self.saml2_user_edit_url,
            'get_harvest_source_type': geodatagov_helpers.get_harvest_source_type,
            'get_harvest_source_config': geodatagov_helpers.get_harvest_source_config,
            'get_collection_package': geodatagov_helpers.get_collection_package,
        }

    # IActions

    def get_actions(self):

        from ckanext.geodatagov import logic as geodatagov_logic

        actions = {
            'resource_show': geodatagov_logic.resource_show,
            'organization_show': geodatagov_logic.organization_show,
            'location_search': geodatagov_logic.location_search,
            'organization_list': geodatagov_logic.organization_list,
            'group_show': geodatagov_logic.group_show,
            'group_catagory_tag_update': geodatagov_logic.group_catagory_tag_update,
            'datajson_create': geodatagov_logic.datajson_create,
            'datajson_update': geodatagov_logic.datajson_update,
            'doi_create': geodatagov_logic.doi_create,
            'doi_update': geodatagov_logic.doi_update,
            'package_show_rest': geodatagov_logic.package_show_rest
        }

        if p.toolkit.check_ckan_version(min_version='2.8'):
            # "chain" actions to avoid using unexistent decorator at CKAN 2.3
            log.info('adding chained actions to {}'.format(ckan_version))
            update_func = geodatagov_logic.package_update
            update_func.chained_action = True

            create_func = geodatagov_logic.package_create
            create_func.chained_action = True

            actions.update({
                'package_update': update_func,
                'package_create': create_func})

        log.info('get_actions {} {}'.format(ckan_version, actions))

        return actions

    # IAuthFunctions

    def get_auth_functions(self):

        from ckanext.geodatagov import auth as geodatagov_auth

        return {
            'related_create': geodatagov_auth.related_create,
            'related_update': geodatagov_auth.related_update,
            'group_catagory_tag_update': geodatagov_auth.group_catagory_tag_update,
        }


class Miscs(p.SingletonPlugin):
    ''' Places for something that has nowhere to go otherwise.
    '''
    p.implements(p.IConfigurer)
    p.implements(p.IConfigurable)
    p.implements(p.IBlueprint)

    # IConfigurer
    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'templates')
        p.toolkit.add_resource('fanstatic_library', 'geodatagov')

    # IConfigurable
    def configure(self, config):
        log.info('plugin initialized: %s', self.__class__.__name__)
        geodatagovmodel.setup()

    def get_blueprint(self):
        return blueprint.datapusher


class S3Test(p.SingletonPlugin):

    p.implements(p.IClick)

    def get_commands(self) -> list:
        return cli.get_commands2()
