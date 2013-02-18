import ckan.plugins as p
import ckan.model as model

def split_tags(tag):
    tags = []
    for tag in tag.split(','):
        tags.extend(tag.split('>'))
    return [tag.strip() for tag in tags]

class Demo(p.SingletonPlugin):

    p.implements(p.IConfigurer)
    p.implements(p.IPackageController, inherit=True)

    def update_config(self, config):
        # add template directory
        p.toolkit.add_template_directory(config, 'templates')
        p.toolkit.add_public_directory(config, 'public')


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
