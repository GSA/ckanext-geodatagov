import json
import logging

from ckan.tests.helpers import reset_db
from ckan.tests import factories

from ckanext.geodatagov.commands import GeoGovCommand
from ckanext.geodatagov.logic import translate_spatial


log = logging.getLogger(__name__)


class TestUpdateGeo(object):

    @classmethod
    def setup(cls):
        reset_db()

    def test_translations(self):
        """ test translate_spatial function """

        # Test place in locations table
        us = ('{"type":"Polygon","coordinates":[[[-124.733253,24.544245],[-124.733253,49.388611],'
              '[-66.954811,49.388611],[-66.954811,24.544245],[-124.733253,24.544245]]]}')
        assert translate_spatial('United States') == us
        california = ('{"type":"Polygon","coordinates":[[[-124.3926,32.5358],[-124.3926,42.0022],'
                      '[-114.1252,42.0022],[-114.1252,32.5358],[-124.3926,32.5358]]]}')
        assert translate_spatial('California') == california

        # test numeric versions
        assert translate_spatial('1.0,2.0,3.5,5.5') == ('{"type": "Polygon", "coordinates": '
                                                        '[[[1.0, 2.0], [1.0, 5.5], [3.5, 5.5], '
                                                        '[3.5, 2.0], [1.0, 2.0]]]}')
        # Test not existent places
        assert translate_spatial('not exists') is None
        assert translate_spatial('1.0,3.0') is None
        assert translate_spatial('US, Virginia, Fairfax, Reston') is None

    def create_datasets(self):

        user = factories.Sysadmin(name='sysadmin')  # NOQA
        self.dataset1 = factories.Dataset(
            extras=[
                {'key': 'spatial', 'value': 'United States'}
            ]
        )
        self.dataset2 = factories.Dataset(
            extras=[
                {'key': 'spatial', 'value': '34.1,25.2,26.2,27.9'}
            ]
        )
        self.dataset3 = factories.Dataset()

        polygon = {
            "type": "Polygon",
            "coordinates": [
                [
                    [2.05827, 49.8625],
                    [2.05827, 55.7447],
                    [-6.41736, 55.7447],
                    [-6.41736, 49.8625],
                    [2.05827, 49.8625]
                ]
            ]
        }
        self.dataset4 = factories.Dataset(
            extras=[
                {'key': 'spatial', 'value': json.dumps(polygon)}
            ]
        )

    def test_create_sitemap(self):
        """ Run update-dataset-geo-fields command and check results.
            We don't expect transformation because catalog-next
            already include transformation while save datasets """

        self.create_datasets()

        cmd = GeoGovCommand()
        cmd.user_name = 'sysadmin'
        results = cmd.update_dataset_geo_fields()

        assert results['total'] == 4
        assert results['failed'] == 0
        assert results['skipped'] == 4

        # this dataset transformed its spatial data
        d1 = results['datasets'][self.dataset1['id']]
        assert d1['skip'] == 'No rolled up spatial extra found'
        extras = {x['key']: x['value'] for x in self.dataset1['extras']}
        assert extras['old-spatial'] == 'United States'
        keys = list(json.loads(extras['spatial']).keys())
        assert 'coordinates' in keys

        # this dataset transformed its spatial data
        d2 = results['datasets'][self.dataset2['id']]
        assert d2['skip'] == 'No rolled up spatial extra found'
        extras = {x['key']: x['value'] for x in self.dataset2['extras']}
        assert extras['old-spatial'] == '34.1,25.2,26.2,27.9'
        keys = list(json.loads(extras['spatial']).keys())
        assert 'coordinates' in keys

        # this dataset don't have any spatial data
        d3 = results['datasets'][self.dataset3['id']]
        assert d3['skip'] == 'No rolled up extras'
        extras = {x['key']: x['value'] for x in self.dataset3['extras']}
        assert 'old-spatial' not in list(extras.keys())
        assert 'spatial' not in list(extras.keys())

        # This dataset already include good spatial data
        d4 = results['datasets'][self.dataset4['id']]
        assert d4['skip'] == 'No rolled up spatial extra found'
        extras = {x['key']: x['value'] for x in self.dataset4['extras']}
        assert 'old-spatial' in list(extras.keys())
        keys = list(json.loads(extras['spatial']).keys())
        assert 'coordinates' in keys
        assert extras['old-spatial'] == extras['spatial']
