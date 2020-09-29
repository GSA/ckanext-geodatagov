import json
import logging
from nose.tools import assert_equal, assert_in
from nose.plugins.skip import SkipTest
try:
    from ckan.tests.helpers import reset_db
    from ckan.tests import factories
    from ckan.common import config
except ImportError:  # CKAN 2.3
    from ckan.new_tests.helpers import reset_db
    from ckan.new_tests import factories
    from pylons import config

from ckanext.geodatagov.commands import GeoGovCommand


log = logging.getLogger(__name__)


class TestSitemapExport(object):

    @classmethod
    def setup(cls):
        reset_db()
        
    def create_datasets(self):

        organization = factories.Organization()
        self.dataset1 = factories.Dataset(owner_org=organization['id'])
        self.dataset2 = factories.Dataset(owner_org=organization['id'])
        self.dataset3 = factories.Dataset(owner_org=organization['id'])
        self.dataset4 = factories.Dataset(owner_org=organization['id'])
        
    def test_create_sitemap(self):
        """ run sitemap-to-s3 and analyze results """
        
        self.create_datasets()

        cmd = GeoGovCommand('test')
        file_list = cmd.sitemap_to_s3(upload_to_s3=False, page_size=100, max_per_page=100)
        
        files = 0
        for site_file in file_list:
            files += 1

            with open(site_file['path'], 'r') as f:
                xml_data = f.read()
                assert "/dataset/{}</loc>".format(self.dataset1['name']) in xml_data
                assert "/dataset/{}</loc>".format(self.dataset2['name']) in xml_data
                assert "/dataset/{}</loc>".format(self.dataset3['name']) in xml_data
                assert "/dataset/{}</loc>".format(self.dataset4['name']) in xml_data
        
        assert files == 1
