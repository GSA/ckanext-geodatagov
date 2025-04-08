import logging
import pytest

from ckan.tests import factories
import ckan.lib.search as search
from ckan.tests.helpers import call_action

from ckanext.geodatagov.helpers import (count_collection_package,
    get_collection_package)

log = logging.getLogger(__name__)


@pytest.mark.usefixtures("with_plugins")
class TestCategoryTags(object):

    def create_datasets(self):
        self.SOURCE_ID = "this-source" # this should be a GUID, so only use alphanumeric and dash
        self.PARENT_ID = 'pa-rent: id' # this can be any string, so make it complex with colon and space

        organization = factories.Organization()

        self.datasets = {
            'parent': {'source_id': self.SOURCE_ID, 'identifier': self.PARENT_ID},
            'child1': {'source_id': self.SOURCE_ID, 'identifier': 'child1-id', 'isPartOf': self.PARENT_ID},
            'child2': {'source_id': self.SOURCE_ID, 'identifier': 'child2-id', 'isPartOf': self.PARENT_ID},
            'child3': {'source_id': self.SOURCE_ID, 'identifier': 'child3-id', 'isPartOf': 'parent-id-not'},
            'child4': {'source_id': 'not-this-source', 'identifier': 'child4-id', 'isPartOf': self.PARENT_ID},
            'child5': {'source_id': 'source:with:colon', 'identifier': 'id:with:colon', 'isPartOf': 'id:with:colon'},
        }

        for dataset in self.datasets.values():
          factories.Dataset(
              owner_org=organization['id'],
              extras=[
                  {'key': 'harvest_source_id', 'value': dataset['source_id']},
                  {'key': 'identifier', 'value': dataset['identifier']},
                  {'key': 'isPartOf', 'value': dataset.get('isPartOf', '')}
              ]
        )

        search.rebuild()

    def test_collections(self):
        self.create_datasets()

        # from any child we can find the parent
        collection_info = f"{self.datasets['child1']['source_id']} {self.datasets['child1']['isPartOf']}"
        parent = get_collection_package(collection_info)
        assert {'key': 'identifier', 'value': self.PARENT_ID} in parent['extras']

        # for the child from different source, there is no parent found
        collection_info = f"{self.datasets['child4']['source_id']} {self.datasets['child4']['isPartOf']}"
        parent = get_collection_package(collection_info)
        assert parent is None

        # only two the children datasets found
        count = count_collection_package(self.datasets['parent']['source_id'], self.datasets['parent']['identifier'])
        assert count == 2

        # no error for identifiers with special chars (colon)
        collection_info = f"{self.datasets['child5']['source_id']} {self.datasets['child5']['isPartOf']}"
        parent = get_collection_package(collection_info)
        assert parent is None

        # collection_info="source-id parent-id" works. can find two children datasets with collection_info.
        all_children = call_action(
            'package_search',
            q = '*:*',
            fq = f'collection_info:"{self.SOURCE_ID} {self.PARENT_ID}"',
        )
        assert all_children['count'] == 2

        dataset_identifiers = set()
        for dataset in all_children['results']:
            for extra in dataset['extras']:
                if extra['key'] == 'identifier':
                    dataset_identifiers.add(extra['value'])

        assert dataset_identifiers == {'child1-id', 'child2-id'}

        # toggle include_collection=true to have children datasets show or hide from search
        all_dataset = call_action(
            'package_search',
            q = '*:*',
        )
        assert all_dataset['count'] == 1

        all_dataset_include_collection = call_action(
            'package_search',
            q = '*:*',
            fq = 'include_collection:true',
        )
        assert all_dataset_include_collection['count'] == len(self.datasets)
