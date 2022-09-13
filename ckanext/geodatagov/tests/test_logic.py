import json

from ckan.tests.helpers import FunctionalTestBase
import ckan.lib.search as search
from ckan.tests import factories

from ckanext.geodatagov.logic import rollup_save_action


class TestLogic(FunctionalTestBase):

    @classmethod
    def setup(cls):
        search.clear_all()

    def create_datasets(self):
        self.group1 = factories.Group()
        organization = factories.Organization()

        self.dataset1 = factories.Dataset(  # NOQA
            title="Dataset 1",
            owner_org=organization['id'],
            groups=[
                {"name": self.group1['name']},
            ],
            extras=[])

        sysadmin = factories.Sysadmin(name='testUpdate')
        self.user_name = sysadmin['name']

    def test_rollup_save_action(self):
        """ test rollup_save_action for expected results """
        test_data = [
            {'key': 'harvest_object_id', 'value': 'to_be_ignored'},
            {'key': 'spatial', 'value': 'US'},
            {'key': 'extras_rollup', 'value': '{"some_extras_rollup": 123}'},
            {'key': 'everything_else', 'value': 'others'}
        ]
        ignored_extra = test_data[0]
        # spatial_extra = test_data[1]
        rollup_extra = test_data[2]
        other_extra = test_data[3]

        self.create_datasets()
        context = {'user': self.user_name, 'ignore_auth': True}

        self.dataset1['extras'] = test_data

        rollup_save_action(context, self.dataset1)
        # print(self.dataset1['extras'])
        # [
        #    {'value': 'to_be_ignored', 'key': 'harvest_object_id'},
        #    {'value': u'{"type":"Polygon","coordinates":[[...]]}',
        #     'key': 'spatial'},
        #    {'value': '{"some_extras_rollup": 1,
        #                "everything_else": "others",
        #                "old-spatial": "US"
        #               }',
        #     'key': 'extras_rollup'}
        # ]
        new_extras = self.dataset1['extras']
        new_extras_rollup = json.loads(next(
            item for item in new_extras if item['key'] == 'extras_rollup'
        )['value'])

        # harvest_object_id in one of EXTRAS_ROLLUP_KEY_IGNORE
        # it should not go into new_extras_rollup
        assert ignored_extra in new_extras
        assert ignored_extra['key'] not in new_extras_rollup.keys()

        # old spatial sees translation
        assert 'old-spatial' in new_extras_rollup.keys()
        assert 'Polygon' in next(
            item for item in new_extras if item['key'] == 'spatial'
        )['value']

        # all others should go into new_extras_rollup
        assert json.loads(rollup_extra['value'])['some_extras_rollup'] \
            == new_extras_rollup['some_extras_rollup']
        assert other_extra['key'] in new_extras_rollup.keys()
