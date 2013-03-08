import ckan.plugins as p
import ckan.model as model
import ckanext.harvest.plugin
import json
from ckanext.harvest.logic.schema import harvest_source_db_to_form_schema
from ckan.logic.converters import convert_from_extras
from ckan.lib.navl.validators import ignore_missing

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

class Demo(p.SingletonPlugin):

    p.implements(p.IConfigurer)
    p.implements(p.IPackageController, inherit=True)
    p.implements(p.ITemplateHelpers)


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

        for group_name in pkg_dict['groups']:
            group = model.Group.get(group_name)
            if 'organization_type' in group.extras:
                pkg_dict['organization_type'] = group.extras['organization_type']

        return pkg_dict

    def before_search(self, pkg_dict):

        fq = pkg_dict.get('fq', '')

        if 'collection_package_id' not in fq:
            pkg_dict['fq'] = pkg_dict.get('fq', '') + ' -collection_package_id:["" TO *]'

        return pkg_dict

    ## ITemplateHelpers

    def get_helpers(self):
        from ckanext.geodatagov import helpers as geodatagov_helpers
        return {
                'get_harvest_object_formats': geodatagov_helpers.get_harvest_object_formats,
                'get_harvest_source_link': geodatagov_helpers.get_harvest_source_link,
                'get_validation_profiles': geodatagov_helpers.get_validation_profiles,
                'get_reference_date' : geodatagov_helpers.get_reference_date,
                }
