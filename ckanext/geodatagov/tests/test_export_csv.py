from datetime import datetime
import json
import logging
import pkg_resources

from ckan.tests.helpers import FunctionalTestBase
import ckan.lib.search as search
from ckan.tests import factories

from ckanext.geodatagov.commands import GeoGovCommand


log = logging.getLogger(__name__)


class TestExportCSV(FunctionalTestBase):

    @classmethod
    def setup(cls):
        search.clear_all()

    def test_export_csv(self):
        """ run json_export and analyze results """

        self.create_datasets()

        cmd = GeoGovCommand()
        results, entry = cmd.export_csv()

        # total results = groups in packages
        assert len(results) == 8

        r = results[0]
        assert r['title'] == "Dataset 1"
        assert r['topic'] == self.group1['title']
        assert r['topicCategories'] == "g1c1"

        r = results[1]
        assert r['title'] == "Dataset 1"
        assert r['topic'] == self.group2['title']
        assert r['topicCategories'] == ""

        r = results[2]
        assert r['title'] == "Dataset 2"
        assert r['topic'] == self.group2['title']
        assert r['topicCategories'] == "g2c1;g2c2"

        r = results[3]
        assert r['title'] == "Dataset 2"
        assert r['topic'] == self.group3['title']
        assert r['topicCategories'] == ""

        r = results[4]
        assert r['title'] == "Dataset 3"
        assert r['topic'] == self.group3['title']
        assert r['topicCategories'] == "g3c1;g3c2"

        r = results[5]
        assert r['title'] == "Dataset 3"
        assert r['topic'] == self.group4['title']
        assert r['topicCategories'] == ""

        r = results[6]
        assert r['title'] == "Dataset 4"
        assert r['topic'] == self.group1['title']
        assert r['topicCategories'] == ""

        r = results[7]
        assert r['title'] == "Dataset 4"
        assert r['topic'] == self.group4['title']
        assert r['topicCategories'] == "g4c1"

        assert entry.date, datetime.strftime(datetime.now() == '%Y%m%d')

        # look for all topics in the CSV
        topics_found = []
        for cat in self.category_tags:
            topic = ';'.join(cat['value'].strip('"[],').split('","'))
            assert topic in entry.csv
            topics_found.append(cat['value'])

    def test_topics_csv_url(self):
        """ test the /topics-csv url """
        self.create_datasets()
        cmd = GeoGovCommand()
        results, entry = cmd.export_csv()

        self.app = self._get_test_app()
        res = self.app.get('/topics-csv')
        for cat in self.category_tags:
            topic = ';'.join(cat['value'].strip('"[],').split('","'))
            assert topic in res

    def create_datasets(self):

        self.group1 = factories.Group()
        group1_cat = {"key": "__category_tag_{}".format(self.group1['id']), "value": "[\"g1c1\"]"}
        self.group2 = factories.Group()
        group2_cat = {"key": "__category_tag_{}".format(self.group2['id']), "value": "[\"g2c1\",\"g2c2\"]"}
        self.group3 = factories.Group()
        group3_cat = {"key": "__category_tag_{}".format(self.group3['id']), "value": "[\"g3c1\",\"g3c2\"]"}
        self.group4 = factories.Group()
        group4_cat = {"key": "__category_tag_{}".format(self.group4['id']), "value": "[\"g4c1\"]"}

        self.category_tags = [group1_cat, group2_cat, group3_cat, group4_cat]
        organization = factories.Organization()

        dataset1 = factories.Dataset(  # NOQA
            title="Dataset 1",
            owner_org=organization['id'],
            groups=[
                {"name": self.group1['name']},
                {"name": self.group2['name']}
            ],
            extras=[group1_cat])

        dataset2 = factories.Dataset(  # NOQA
            title="Dataset 2",
            owner_org=organization['id'],
            groups=[
                {"name": self.group2['name']},
                {"name": self.group3['name']}
            ],
            extras=[group2_cat])

        dataset3 = factories.Dataset(  # NOQA
            title="Dataset 3",
            owner_org=organization['id'],
            groups=[
                {"name": self.group3['name']},
                {"name": self.group4['name']}
            ],
            extras=[group3_cat])

        dataset4 = factories.Dataset(  # NOQA
            title="Dataset 4",
            owner_org=organization['id'],
            groups=[
                {"name": self.group4['name']},
                {"name": self.group1['name']}
            ],
            extras=[group4_cat])

    def test_static_export_group_and_tags(self):

        test_file = pkg_resources.resource_filename(__name__, "/data-samples/datasets_category_tags.json")

        f = open(test_file)
        packages = json.load(f)
        f.close()

        cmd = GeoGovCommand()
        results = cmd.export_group_and_tags(packages)

        assert len(results) == 12

        for result in results:
            assert result['organization'], 'Department of Housing and Urban Development == Federal Government'
            assert result['organizationUrl'] == 'https://catalog.data.gov/organization/hud-gov'
            assert result['harvestSourceUrl'] == 'https://catalog.data.gov/harvest/991bcaf7-498f-4657-bed2-f6594e1bfbe7'

        assert results[0]['topic'] == 'BusinessUSA'
        assert results[1]['topic'] == 'Consumer'
        assert results[2]['topic'] == 'Energy'
        assert results[3]['topic'] == 'Finance'
        assert results[4]['topic'] == 'BusinessUSA'
        assert results[5]['topic'] == 'Consumer'
        assert results[6]['topic'] == 'Energy'
        assert results[7]['topic'] == 'Finance'
        assert results[8]['topic'] == 'BusinessUSA'
        assert results[9]['topic'] == 'Consumer'
        assert results[10]['topic'] == 'Energy'
        assert results[11]['topic'] == 'Finance'

        assert results[0]['topicCategories'] == ''
        assert results[1]['topicCategories'] == 'Finance'
        assert results[2]['topicCategories'] == 'Total Energy'
        assert results[3]['topicCategories'] == ''
        assert results[4]['topicCategories'] == ''
        assert results[5]['topicCategories'] == 'Finance'
        assert results[6]['topicCategories'] == 'Total Energy'
        assert results[7]['topicCategories'] == ''
        assert results[8]['topicCategories'] == ''
        assert results[9]['topicCategories'] == 'Finance'
        assert results[10]['topicCategories'] == 'Total Energy'
        assert results[11]['topicCategories'] == ''
