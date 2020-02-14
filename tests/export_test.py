import json
import os

import pkg_resources
from ckanext import geodatagov

test_file = pkg_resources.resource_filename(__name__, "datasets.json")


with open(test_file) as data_file:
    packages = json.load(data_file)

assert isinstance(packages, list)
assert len(packages) == 3


def export_group_and_tags(packages):
    domain = 'https://catalog.data.gov'
    result = []
    for pkg in packages:
        package = dict()

        package_groups = pkg.get('groups')
        if not package_groups:
            continue

        extras = dict([(x['key'], x['value']) for x in pkg['extras']])
        package['title'] = pkg.get('title').encode('ascii', 'xmlcharrefreplace')
        package['url'] = domain + '/dataset/' + pkg.get('name')
        package['organization'] = pkg.get('organization').get('title')
        package['organizationUrl'] = domain + '/organization/' + pkg.get('organization').get('name')
        package['harvestSourceTitle'] = extras.get('harvest_source_title', '')
        package['harvestSourceUrl'] = ''
        harvest_source_id = extras.get('harvest_source_id')
        if harvest_source_id:
            package['harvestSourceUrl'] = domain + '/harvest/' + harvest_source_id

        for group in package_groups:
            package = package.copy()
            category_tag = '__category_tag_' + group.get('id')
            package_categories = extras.get(category_tag)

            package['topic'] = group.get('title')
            package['topicCategories'] = ''
            if package_categories:
                package_categories = package_categories.strip('"[],').split('","')
                package['topicCategories'] = ';'.join(package_categories)

            result.append(package)
    return result


result = export_group_and_tags(packages)

assert len(result) == 12

assert result[8]['topic'] == 'BusinessUSA'
assert result[9]['topic'] == 'Consumer'
assert result[10]['topic'] == 'Energy'
assert result[11]['topic'] == 'Finance'

assert result[8]['topicCategories'] == ''
assert result[9]['topicCategories'] == 'Finance'
assert result[10]['topicCategories'] == 'Total Energy'
assert result[11]['topicCategories'] == ''
