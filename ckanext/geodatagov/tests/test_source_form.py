from nose.tools import assert_equal, assert_in, assert_not_in
import ckanext.harvest.model as harvest_model

try:
    from ckan.tests import helpers, factories
except ImportError: 
    from ckan.new_tests import helpers, factories

class TestHarvestSourceForm(helpers.FunctionalTestBase):

    @classmethod
    def setup_class(cls):

        helpers.reset_db()
        super(TestHarvestSourceForm, cls).setup_class()
        harvest_model.setup()
        sysadmin = factories.Sysadmin()
        cls.extra_environ = {'REMOTE_USER': sysadmin['name'].encode('ascii')}


    def test_create_harvest_source_form(self):

        self.app = self._get_test_app()
        
        # Create
        res = self.app.get('/harvest/new', extra_environ=self.extra_environ)
        
        harvest_source_name = u'test-harvest-source'
        fv = res.forms['source-new']
        fv['url'] = u'https://meta.geo.census.gov/data/existing/decennial/GEO/GPMB/TIGERline/TIGER2018/concity/'
        fv['source_type'] = u'waf-collection'
        fv['title'] = u'Test harvest source'
        fv['name'] = harvest_source_name
        fv['collection_metadata_url'] = 'https://meta.geo.census.gov/data/existing/decennial/GEO/GPMB/TIGERline/TIGER2018/SeriesInfo/SeriesCollection_tl_2018_concity.shp.iso.xml'

        # Save
        res = fv.submit('save', extra_environ=self.extra_environ)
        assert_not_in('Error', res)
        assert_not_in('Missing value', res)

        # Go to the edit form
        res_redirect = self.app.get('/harvest/edit/{}'.format(harvest_source_name), extra_environ=self.extra_environ)
        
        # ensure we have the expected values
        fv = res_redirect.forms['source-new']
        assert_equal(fv['collection_metadata_url'].value, 'https://meta.geo.census.gov/data/existing/decennial/GEO/GPMB/TIGERline/TIGER2018/SeriesInfo/SeriesCollection_tl_2018_concity.shp.iso.xml')
        assert_equal(fv['url'].value, 'https://meta.geo.census.gov/data/existing/decennial/GEO/GPMB/TIGERline/TIGER2018/concity/')
        assert_equal(fv['source_type'].value, 'waf-collection')
