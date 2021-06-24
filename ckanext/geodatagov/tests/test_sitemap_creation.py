from builtins import object
import logging
import xml.etree.ElementTree as ET

from nose.tools import assert_equal  # , assert_in

from ckan.tests.helpers import reset_db
from ckan.tests import factories
from ckan import model

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
        datasets = 0
        for site_file in file_list:
            files += 1
            """ expected something like
                <?xml version="1.0" encoding="UTF-8"?>
                <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                    <url>
                        <loc>http://ckan:5000/dataset/test_dataset_01</loc>
                        <lastmod>2020-09-29</lastmod>
                    </url>
                    <url>
                        <loc>http://ckan:5000/dataset/test_dataset_02</loc>
                        <lastmod>2020-09-29</lastmod>
                    </url>
                    ...
                </urlset>
            """
            log.info('Opening file {}'.format(site_file['path']))
            tree = ET.parse(site_file['path'])
            root = tree.getroot()
            log.info('XML Root {}'.format(root))
            assert_equal(root.tag, '{http://www.sitemaps.org/schemas/sitemap/0.9}urlset')

            prev_last_mod = ''

            dataset1_found = False
            dataset2_found = False
            dataset3_found = False
            dataset4_found = False

            for url in root:
                for child in url:
                    if child.tag == '{http://www.sitemaps.org/schemas/sitemap/0.9}loc':
                        dataset_url = child.text
                        dataset_name = dataset_url.split('/')[-1]
                        if dataset_name == self.dataset1['name']:
                            dataset1_found = True
                        elif dataset_name == self.dataset2['name']:
                            dataset2_found = True
                        elif dataset_name == self.dataset3['name']:
                            dataset3_found = True
                        elif dataset_name == self.dataset4['name']:
                            dataset4_found = True
                        datasets += 1
                    elif child.tag == '{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod':
                        last_mod = child.text
                        log.info('{} >= {} '.format(prev_last_mod, last_mod))
                        assert last_mod >= prev_last_mod
                        prev_last_mod = last_mod
                    else:
                        raise Exception('Unexpected tag')

        assert_equal(files, 1)
        assert datasets >= 4  # at least this four
        assert dataset1_found
        assert dataset2_found
        assert dataset3_found
        assert dataset4_found
