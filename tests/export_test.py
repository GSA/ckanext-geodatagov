import json
import os.path
import unittest

from ckanext.geodatagov.commands import GeoGovCommand

class ExportTest(unittest.TestCase):
    def setUp(self):
        TEST_DIR = os.path.dirname(__file__)
        with open(os.path.join(TEST_DIR, 'datasets.json')) as data_file:
            self.packages = json.load(data_file)

    def test_datasets_json_loaded(self):
        packages = self.packages
        assert isinstance(packages, list)
        assert len(packages) == 3

    def test_export_group_and_tags(self):
        result = GeoGovCommand.export_group_and_tags(self.packages)

        assert len(result) == 12

        assert result[8]['topic'] == 'BusinessUSA'
        assert result[9]['topic'] == 'Consumer'
        assert result[10]['topic'] == 'Energy'
        assert result[11]['topic'] == 'Finance'

        assert result[8]['topicCategories'] == ''
        assert result[9]['topicCategories'] == 'Finance'
        assert result[10]['topicCategories'] == 'Total Energy'
        assert result[11]['topicCategories'] == ''
