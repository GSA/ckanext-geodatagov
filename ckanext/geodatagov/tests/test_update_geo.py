import json
import logging
import xml.etree.ElementTree as ET
from ckan import plugins as p
from nose.tools import assert_equal, assert_in, assert_not_in

try:
    from ckan.tests.helpers import reset_db
    from ckan.tests import factories
    from ckan.common import config
except ImportError:  # CKAN 2.3
    from ckan.new_tests.helpers import reset_db
    from ckan.new_tests import factories
    from pylons import config

from nose.plugins.skip import SkipTest
from ckanext.geodatagov.commands import GeoGovCommand
from ckanext.geodatagov.logic import translate_spatial


log = logging.getLogger(__name__)


class TestUpdateGeo(object):

    @classmethod
    def setup(cls):
        if not p.toolkit.check_ckan_version(min_version='2.8'):
            raise SkipTest('Just for CKAN 2.8')
        reset_db()
    
    def test_translations(self):
        """ test translate_spatial function """
        
        # Test place in locations table 
        us = '{"type":"Polygon","coordinates":[[[-124.733253,24.544245],[-124.733253,49.388611],[-66.954811,49.388611],[-66.954811,24.544245],[-124.733253,24.544245]]]}'
        assert_equal(translate_spatial('United States'), us)
        california = '{"type":"Polygon","coordinates":[[[-124.3926,32.5358],[-124.3926,42.0022],[-114.1252,42.0022],[-114.1252,32.5358],[-124.3926,32.5358]]]}'
        assert_equal(translate_spatial('California'), california)
        
        # test numeric versions
        assert_equal(translate_spatial('1.0,2.0,3.5,5.5'), '{"type": "Polygon", "coordinates": [[[1.0, 2.0], [1.0, 5.5], [3.5, 5.5], [3.5, 2.0], [1.0, 2.0]]]}')
       
        # Test not existent places
        assert_equal(translate_spatial('not exists'), None)
        assert_equal(translate_spatial('1.0,3.0'), None)

    def create_datasets(self):

        user = factories.Sysadmin(name='sysadmin')
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
            "type":"Polygon",
            "coordinates":[
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

        cmd = GeoGovCommand('test')
        cmd.user_name = 'sysadmin'
        results = cmd.update_dataset_geo_fields()
        

        assert_equal(results['total'], 4)        
        assert_equal(results['failed'], 0)        
        assert_equal(results['skipped'], 4)        
        
        # this dataset transformed its spatial data
        d1 = results['datasets'][self.dataset1['id']]
        assert_equal(d1['skip'], 'No rolled up spatial extra found')
        extras = {x['key']: x['value'] for x in self.dataset1['extras']}
        assert_equal(extras['old-spatial'], 'United States')
        keys = json.loads(extras['spatial']).keys()
        assert_in('coordinates', keys) 
        
        # this dataset transformed its spatial data
        d2 = results['datasets'][self.dataset2['id']]
        assert_equal(d2['skip'], 'No rolled up spatial extra found')
        extras = {x['key']: x['value'] for x in self.dataset2['extras']}
        assert_equal(extras['old-spatial'], '34.1,25.2,26.2,27.9')
        keys = json.loads(extras['spatial']).keys()
        assert_in('coordinates', keys) 
        
        # this dataset don't have any spatial data
        d3 = results['datasets'][self.dataset3['id']]
        assert_equal(d3['skip'], 'No rolled up extras')
        extras = {x['key']: x['value'] for x in self.dataset3['extras']}
        assert_not_in('old-spatial', extras.keys())
        assert_not_in('spatial', extras.keys())
        
        # This dataset already include good spatial data
        d4 = results['datasets'][self.dataset4['id']]
        assert_equal(d4['skip'], 'No rolled up spatial extra found')
        extras = {x['key']: x['value'] for x in self.dataset4['extras']}
        assert_in('old-spatial', extras.keys())
        keys = json.loads(extras['spatial']).keys()
        assert_in('coordinates', keys) 
        assert_equal(extras['old-spatial'], extras['spatial'])
        