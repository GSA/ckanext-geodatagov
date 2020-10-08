from datetime import datetime
import json
import logging
import pkg_resources
from nose.tools import assert_equal, assert_in

try:
    from ckan.tests.helpers import reset_db, FunctionalTestBase
    from ckan.tests import factories
    from ckan.common import config
except ImportError:  # CKAN 2.3
    from ckan.new_tests.helpers import reset_db, FunctionalTestBase
    from ckan.new_tests import factories
    from pylons import config

from ckanext.geodatagov.commands import GeoGovCommand


log = logging.getLogger(__name__)


class TestExportCSV(FunctionalTestBase):

    @classmethod
    def setup(cls):
        reset_db()
        
    def test_export_group_and_tags(self):

        test_file = pkg_resources.resource_filename(__name__, "/data-samples/datasets_category_tags.json")

        f = open(test_file)
        packages = json.load(f)
        f.close()

        cmd = GeoGovCommand('test')
        results = cmd.export_group_and_tags(packages)
        
        assert_equal(len(results), 12)

        for result in results:
            assert_equal(result['organization'], 'Department of Housing and Urban Development, Federal Government')
            assert_equal(result['organizationUrl'], 'https://catalog.data.gov/organization/hud-gov')
            assert_equal(result['harvestSourceUrl'], 'https://catalog.data.gov/harvest/991bcaf7-498f-4657-bed2-f6594e1bfbe7')
            
	    assert_equal(results[0]['topic'], 'BusinessUSA')
        assert_equal(results[1]['topic'], 'Consumer')
        assert_equal(results[2]['topic'], 'Energy')
        assert_equal(results[3]['topic'], 'Finance')
        assert_equal(results[4]['topic'], 'BusinessUSA')
        assert_equal(results[5]['topic'], 'Consumer')
        assert_equal(results[6]['topic'], 'Energy')
        assert_equal(results[7]['topic'], 'Finance')
        assert_equal(results[8]['topic'], 'BusinessUSA')
        assert_equal(results[9]['topic'], 'Consumer')
        assert_equal(results[10]['topic'], 'Energy')
        assert_equal(results[11]['topic'], 'Finance')

        assert_equal(results[0]['topicCategories'], '')
        assert_equal(results[1]['topicCategories'], 'Finance')
        assert_equal(results[2]['topicCategories'], 'Total Energy')
        assert_equal(results[3]['topicCategories'], '')
        assert_equal(results[4]['topicCategories'], '')
        assert_equal(results[5]['topicCategories'], 'Finance')
        assert_equal(results[6]['topicCategories'], 'Total Energy')
        assert_equal(results[7]['topicCategories'], '')
        assert_equal(results[8]['topicCategories'], '')
        assert_equal(results[9]['topicCategories'], 'Finance')
        assert_equal(results[10]['topicCategories'], 'Total Energy')
        assert_equal(results[11]['topicCategories'], '')


    def test_export_csv(self):
        """ run json_export and analyze results """
        
        self.create_datasets()
        
        cmd = GeoGovCommand('test')
        results, entry = cmd.export_csv()
        
        # total results = groups in packages 
        assert_equal(len(results), 8)

        r = results[0]
        assert_equal(r['title'], "Dataset 1")
        # CKAN 2.3 give us "Test Group 0" and CKAN 2.8 "Test Group 00"
        assert_in(r['topic'], ["Test Group 0", "Test Group 00"])
        assert_equal(r['topicCategories'], "g1c1")
        
        r = results[1]
        assert_equal(r['title'], "Dataset 1")
        assert_in(r['topic'], ["Test Group 1", "Test Group 01"])
        assert_equal(r['topicCategories'], "")
        
        r = results[2]
        assert_equal(r['title'], "Dataset 2")
        assert_in(r['topic'], ["Test Group 1", "Test Group 01"])
        assert_equal(r['topicCategories'], "g2c1;g2c2")
    
        r = results[3]
        assert_equal(r['title'], "Dataset 2")
        assert_in(r['topic'], ["Test Group 2", "Test Group 02"])
        assert_equal(r['topicCategories'], "")

        r = results[4]
        assert_equal(r['title'], "Dataset 3")
        assert_in(r['topic'], ["Test Group 2", "Test Group 02"])
        assert_equal(r['topicCategories'], "g3c1;g3c2")
        
        r = results[5]
        assert_equal(r['title'], "Dataset 3")
        assert_in(r['topic'], ["Test Group 3", "Test Group 03"])
        assert_equal(r['topicCategories'], "")

        r = results[6]
        assert_equal(r['title'], "Dataset 4")
        assert_in(r['topic'], ["Test Group 0", "Test Group 00"])
        assert_equal(r['topicCategories'], "")
        
        r = results[7]
        assert_equal(r['title'], "Dataset 4")
        assert_in(r['topic'], ["Test Group 3", "Test Group 03"])
        assert_equal(r['topicCategories'], "g4c1")

        assert_equal(entry.date, datetime.strftime(datetime.now(), '%Y%m%d'))

        # look for all topics in the CSV 
        topics_found = []
        for cat in self.category_tags:
            topic = ';'.join(cat['value'].strip('"[],').split('","'))
            assert_in(topic, entry.csv)
            topics_found.append(cat['value'])
                
    def test_topics_csv_url(self):
        """ test the /topics-csv url """
        self.create_datasets()
        cmd = GeoGovCommand('test')
        results, entry = cmd.export_csv()

        self.app = self._get_test_app()
        res = self.app.get('/topics-csv')
        for cat in self.category_tags:
            topic = ';'.join(cat['value'].strip('"[],').split('","'))
            assert_in(topic, res)
            
    def create_datasets(self):

        group1 = factories.Group()
        group1_cat = {"key": "__category_tag_{}".format(group1['id']), "value": "[\"g1c1\"]"}
        group2 = factories.Group()
        group2_cat = {"key": "__category_tag_{}".format(group2['id']), "value": "[\"g2c1\",\"g2c2\"]"}
        group3 = factories.Group()
        group3_cat = {"key": "__category_tag_{}".format(group3['id']), "value": "[\"g3c1\",\"g3c2\"]"}
        group4 = factories.Group()
        group4_cat = {"key": "__category_tag_{}".format(group4['id']), "value": "[\"g4c1\"]"}
        
        self.category_tags = [group1_cat, group2_cat, group3_cat, group4_cat]
        organization = factories.Organization()    
        
        dataset1 = factories.Dataset(
            title="Dataset 1",
            owner_org=organization['id'],
            groups=[
                {"name": group1['name']},
                {"name": group2['name']}
            ],
            extras=[group1_cat])
        
        dataset2 = factories.Dataset(
            title="Dataset 2",
            owner_org=organization['id'],
            groups=[
                {"name": group2['name']},
                {"name": group3['name']}
            ],
            extras=[group2_cat])
        
        dataset3 = factories.Dataset(
            title="Dataset 3",
            owner_org=organization['id'],
            groups=[
                {"name": group3['name']},
                {"name": group4['name']}
            ],
            extras=[group3_cat])

        dataset4 = factories.Dataset(
            title="Dataset 4",
            owner_org=organization['id'],
            groups=[
                {"name": group4['name']},
                {"name": group1['name']}
            ],
            extras=[group4_cat])
    