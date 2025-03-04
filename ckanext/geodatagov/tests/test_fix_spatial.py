import os

import ckan.plugins as p
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckan.model.meta import Session, metadata
import pytest

@pytest.mark.usefixtures("with_plugins")
class TestSpatialField(object):

    @classmethod
    def setup_class(cls):
        # echo "Downloading locations table"
        os.system("PGPASSWORD=ckan psql -h db -U ckan -d ckan -c 'DROP TABLE IF EXISTS locations;'")
        os.system("wget https://github.com/GSA/datagov-deploy/raw/71936f004be1882a506362670b82c710c64ef796/"
                  "ansible/roles/software/ec2/ansible/files/locations.sql.gz -O /tmp/locations.sql.gz")
        # echo "Creating locations table"
        os.system("gunzip -c /tmp/locations.sql.gz | PGPASSWORD=ckan psql -h db -U ckan -d ckan -v ON_ERROR_STOP=1")
        # echo "Cleaning"
        os.system("rm -f /tmp/locations.sql.gz")

        cls.user = factories.Sysadmin(name='spatial_user')

    def test_numeric_spatial_transformation(self):
        old_geo = '10.0,0.0,15.0,5.0'

        context = {'user': self.user['name'], 'ignore_auth': True}
        pkg = {
            'title': 'Spatial num',
            'name': 'spatial-num',
            'extras': [
                {'key': 'spatial', 'value': old_geo}
            ]
        }
        dataset = p.toolkit.get_action('package_create')(context, pkg)

        expected_spatial = ('{"type": "Polygon", "coordinates": [[[10.0, 0.0], [10.0, 5.0], [15.0, 5.0], '
                            '[15.0, 0.0], [10.0, 0.0]]]}')

        spatial_extra_exists = False
        for extra in dataset['extras']:
            if extra['key'] == 'spatial':
                spatial_extra_exists = True
                assert extra['value'] == expected_spatial

        assert spatial_extra_exists is True

        result = helpers.call_action(
            'package_search',
            extras={'ext_bbox': '9,-1,16,4'})
        assert result['count'] == 1
        assert result['results'][0]['id'] == dataset['id']

    def test_string_spatial_transformation(self):

        old_geo = 'California'
        # require locations table to be installed

        context = {'user': self.user['name'], 'ignore_auth': True}
        pkg = {
            'title': 'Spatial String',
            'name': 'spatial-str',
            'extras': [
                {'key': 'spatial', 'value': old_geo}
            ]
        }
        dataset = p.toolkit.get_action('package_create')(context, pkg)

        expected_spatial = ('{"type":"Polygon",'
                            '"coordinates":[[[-124.3926,32.5358],[-124.3926,42.0022],[-114.1252,42.0022],'
                            '[-114.1252,32.5358],[-124.3926,32.5358]]]}')
        spatial_extra_exists = False
        for extra in dataset['extras']:
            if extra['key'] == 'spatial':
                spatial_extra_exists = True
                assert extra['value'] == expected_spatial

        assert spatial_extra_exists is True

        result = helpers.call_action(
            'package_search',
            extras={'ext_bbox': '-125,31,-113,43'})

        assert result['count'] == 1
        assert result['results'][0]['id'] == dataset['id']

    def test_list_spatial_transformation(self):

        old_geo = '[[20.0, 10.0], [25.0, 15.0]]'

        context = {'user': self.user['name'], 'ignore_auth': True}
        pkg = {
            'title': 'Spatial List',
            'name': 'spatial-list',
            'extras': [
                {'key': 'spatial', 'value': old_geo}
            ]
        }
        dataset = p.toolkit.get_action('package_create')(context, pkg)

        expected_spatial = ('{"type": "Polygon", "coordinates": [[[20.0, 10.0], [20.0, 15.0], [25.0, 15.0], '
                            '[25.0, 10.0], [20.0, 10.0]]]}')
        spatial_extra_exists = False
        for extra in dataset['extras']:
            if extra['key'] == 'spatial':
                spatial_extra_exists = True
                assert extra['value'] == expected_spatial

        assert spatial_extra_exists is True

        result = helpers.call_action(
            'package_search',
            extras={'ext_bbox': '19,9,26,16'})

        assert result['count'] == 1
        assert result['results'][0]['id'] == dataset['id']

    def test_spatial_plus_sign(self):

        old_geo = '-179.231086,-14.601813,+179.859681,+71.441059'

        context = {'user': self.user['name'], 'ignore_auth': True}
        pkg = {
            'title': 'Spatial Plus Sign',
            'name': 'spatial-plus',
            'extras': [
                {'key': 'spatial', 'value': old_geo}
            ]
        }
        dataset = p.toolkit.get_action('package_create')(context, pkg)

        expected_spatial = ('{"type": "Polygon", "coordinates": [[[-179.231086, -14.601813], '
                            '[-179.231086, 71.441059], [179.859681, 71.441059], [179.859681, '
                            '-14.601813], [-179.231086, -14.601813]]]}')
        spatial_extra_exists = False
        for extra in dataset['extras']:
            if extra['key'] == 'spatial':
                spatial_extra_exists = True
                assert extra['value'] == expected_spatial

        assert spatial_extra_exists is True

    def test_bad_string_transformation(self):

        old_geo = 'US Domestic'
        # require locations table to be installed

        context = {'user': self.user['name'], 'ignore_auth': True}
        pkg = {
            'title': 'Spatial US Domestic',
            'name': 'spatial-usd',
            'extras': [
                {'key': 'spatial', 'value': old_geo}
            ]
        }
        dataset = p.toolkit.get_action('package_create')(context, pkg)

        expected_spatial = ""
        spatial_extra_exists = False
        for extra in dataset['extras']:
            if extra['key'] == 'spatial':
                spatial_extra_exists = True
                assert extra['value'] == expected_spatial
            if extra['key'] == 'old-spatial':
                assert extra['value'] == old_geo

        assert spatial_extra_exists is True
