import logging

import ckanext.harvest.model as harvest_model
from nose.tools import assert_equal, assert_not_in

from ckan.tests import helpers, factories

log = logging.getLogger(__name__)


class TestHarvestSourceForm(helpers.FunctionalTestBase):

    @classmethod
    def setup_class(cls):
        helpers.reset_db()

        super(TestHarvestSourceForm, cls).setup_class()
        harvest_model.setup()
        sysadmin = factories.Sysadmin()
        cls.extra_environ = {'REMOTE_USER': sysadmin['name'].encode('ascii')}

    def test_create_waf_collection_harvest_source_form(self):
        WAF_HARVEST_SOURCE_URL = 'https://meta.geo.census.gov/data/existing/decennial/GEO/GPMB/TIGERline/TIGER2018/concity/'
        COLLECTION_METADATA_URL = 'https://meta.geo.census.gov/data/existing/decennial/GEO/GPMB/TIGERline/TIGER2018/\
                                    SeriesInfo/SeriesCollection_tl_2018_concity.shp.iso.xml'
        self.app = self._get_test_app()

        # Create
        res = self.app.get('/harvest/new', extra_environ=self.extra_environ)

        harvest_source_name = 'test-waf-collection-harvest-source'
        fv = res.forms['source-new']
        fv['url'] = WAF_HARVEST_SOURCE_URL
        fv['source_type'] = 'waf-collection'
        fv['title'] = 'Test WAF colelction harvest source'
        fv['name'] = harvest_source_name
        fv['collection_metadata_url'] = COLLECTION_METADATA_URL
        fv['validator_profiles'] = 'iso19139ngdc'

        # Save
        res = fv.submit('save', extra_environ=self.extra_environ)
        assert_not_in('Error', res)
        assert_not_in('Missing value', res)

        # Go to the edit form
        res_redirect = self.app.get('/harvest/edit/{}'.format(harvest_source_name), extra_environ=self.extra_environ)

        # ensure we have the expected values
        fv = res_redirect.forms['source-new']
        assert_equal(fv['collection_metadata_url'].value, COLLECTION_METADATA_URL)
        assert_equal(fv['url'].value, WAF_HARVEST_SOURCE_URL)
        assert_equal(fv['source_type'].value, 'waf-collection')
        assert_equal(fv['validator_profiles'].value, 'iso19139ngdc')

    def test_create_z3950_harvest_source_form(self):

        self.app = self._get_test_app()

        # Create
        res = self.app.get('/harvest/new', extra_environ=self.extra_environ)

        harvest_source_name = u'test-harvest-source'
        fv = res.forms['source-new']
        fv['url'] = u'https://test.z3950.com/'
        fv['source_type'] = u'z3950'
        fv['title'] = u'Test Z3950 harvest source'
        fv['name'] = harvest_source_name
        fv['database'] = 'test-database'
        fv['port'] = '9999'

        # Save
        res = fv.submit('save', extra_environ=self.extra_environ)
        assert_not_in('Error', res)
        assert_not_in('Missing value', res)

        # Go to the edit form
        res_redirect = self.app.get('/harvest/edit/{}'.format(harvest_source_name), extra_environ=self.extra_environ)

        # ensure we have the expected values
        fv = res_redirect.forms['source-new']
        assert_equal(fv['url'].value, 'https://test.z3950.com/')
        assert_equal(fv['source_type'].value, 'z3950')
        assert_equal(fv['database'].value, 'test-database')
        assert_equal(fv['port'].value, '9999')
