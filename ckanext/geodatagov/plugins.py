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

import ckan.plugins as p
import ckan.model as model
import ckanext.harvest.plugin
import json
from ckan.logic.converters import convert_from_extras
from ckan.lib.navl.validators import ignore_missing
from sqlalchemy.util import OrderedDict

log = logging.getLogger(__name__)

try:
    from ckanext.harvest.logic.schema import harvest_source_db_to_form_schema
except ImportError, e:
    log.critical('Harvester not available %s' % str(e))


RESOURCE_MAPPING = {
    'text/html': 'HTML',
    'application/zip': 'ZIP',
    'application/xml': 'XML',
    'application/x-netcdf': 'NetCDF',
    'application/x-httpd-php': 'HTML',
    'application/pdf': 'PDF',
    'application/x-msdos-program': 'EXE',
    'arcgis_rest': 'Esri REST',
    'application/vnd.ms-excel': 'Excel',
    'application/x-tar': 'TAR',
    'wms': 'WMS',
    'application/rar': 'RAR',
    'application/x-qgis': 'QGIS',
    'wfs': ' WFS',
    'text/plain': 'TXT',
    'application/msaccess': 'Access',
    'image/jpeg': 'JPEG',
    'audio/prs.sid': 'MrSID',
    'kml': 'KML',
    'image/tiff': 'TIFF',
    'kmz': 'KMZ',
    'wcs': 'WCS',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'OpenXML',
    'text/x-perl': 'Perl',
    'application/msword': 'DOC',
    'text/csv': 'CSV',
    'image/x-ms-bmp': 'BMP',
    'chemical/x-xyz': 'XYZ',
    'image/png': 'PNG',
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

    def db_to_form_schema(self):
        '''
        Returns the schema for mapping package data from the database into a
        format suitable for the form
        '''
        schema = harvest_source_db_to_form_schema()
        schema['config'] = [convert_from_extras, harvest_source_convert_from_config, ignore_missing]
        return schema

    def dataset_facets(self, facets_dict, package_type):

        if package_type <> 'harvest':
            return facets_dict

        return OrderedDict([('frequency', 'Frequency'),
                            ('source_type','Type'),
                            ('organization_type', 'Organization Types'),
                           ])

    def organization_facets(self, facets_dict, organization_type, package_type):

        if package_type <> 'harvest':
            return facets_dict

        return OrderedDict([('frequency', 'Frequency'),
                            ('source_type','Type'),
                           ])

class Demo(p.SingletonPlugin):

    p.implements(p.IConfigurer)
    p.implements(p.IPackageController, inherit=True)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IFacets, inherit=True)


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
            formats = RESOURCE_MAPPING.keys()
            for resource in data_dict['resources']:
                if resource['format'] in formats:
                    resource['format'] = RESOURCE_MAPPING[resource['format']]

        return data_dict

    ## ITemplateHelpers

    def get_helpers(self):
        from ckanext.geodatagov import helpers as geodatagov_helpers
        return {
                'get_harvest_object_formats': geodatagov_helpers.get_harvest_object_formats,
                'get_harvest_source_link': geodatagov_helpers.get_harvest_source_link,
                'get_validation_profiles': geodatagov_helpers.get_validation_profiles,
                'get_collection_package': geodatagov_helpers.get_collection_package,
                }

    def dataset_facets(self, facets_dict, package_type):

        if package_type != 'dataset':
            return facets_dict

        return OrderedDict([('organization', 'Organizations'),
                            ('groups', 'Groups'),
                            ('tags','Tags'),
                            ('res_format', 'Formats'),
                            ('organization_type', 'Organization Types'),
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
            return OrderedDict([('tags','Tags'),
                                ('res_format', 'Formats'),
                                ('organization', 'Organizations'),
                                ('organization_type', 'Organization Types'),
                               ])
        else:
            return facets_dict
