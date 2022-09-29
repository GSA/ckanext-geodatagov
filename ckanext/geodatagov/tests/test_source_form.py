from html.parser import HTMLParser
import logging

import ckanext.harvest.model as harvest_model

from ckan.tests import helpers, factories

log = logging.getLogger(__name__)


class SourceFormParser(HTMLParser):
    results = {
        'url': None,
        'source_type': None,
        'title': None,
        'name': None,
        'collection_metadata_url': None,
        'validator_profiles': None,
        'database': None,
        'port': None
    }

    def handle_starttag(self, tag, attrs):
        if tag == 'input':
            attr_dict = {}
            for attr in attrs:
                attr_dict[attr[0]] = attr[1]
            if attr_dict['name'] == 'url':
                self.results['url'] = attr_dict['value']
            if attr_dict['name'] == 'title':
                self.results['title'] = attr_dict['value']
            if attr_dict['name'] == 'name':
                self.results['name'] = attr_dict['value']
            if attr_dict['name'] == 'collection_metadata_url':
                self.results['collection_metadata_url'] = attr_dict['value']
            if attr_dict['name'] == 'database':
                self.results['database'] = attr_dict['value']
            if attr_dict['name'] == 'port':
                self.results['port'] = attr_dict['value']
            if 'checked' in attr_dict:
                if attr_dict['name'] == 'source_type':
                    if attr_dict['value'] != '':
                        self.results['source_type'] = attr_dict['value']
                if attr_dict['name'] == 'validator_profiles':
                    if attr_dict['value'] != '':
                        self.results['validator_profiles'] = attr_dict['value']

    def handle_endtag(self, tag):
        pass

    def handle_data(self, data):
        pass


class TestHarvestSourceForm(helpers.FunctionalTestBase):

    @classmethod
    def setup(cls):
        helpers.reset_db()

    @classmethod
    def setup_class(cls):
        super(TestHarvestSourceForm, cls).setup_class()
        harvest_model.setup()
        sysadmin = factories.Sysadmin()
        cls.extra_environ = {'REMOTE_USER': sysadmin['id']}

    def test_create_waf_collection_harvest_source_form(self):
        WAF_HARVEST_SOURCE_URL = 'https://meta.geo.census.gov/data/existing/decennial/GEO/GPMB/TIGERline/TIGER2018/concity/'
        COLLECTION_METADATA_URL = 'https://meta.geo.census.gov/data/existing/decennial/GEO/GPMB/TIGERline/TIGER2018/\
                                    SeriesInfo/SeriesCollection_tl_2018_concity.shp.iso.xml'
        self.app = self._get_test_app()

        # Create
        harvest_source_name = 'test-waf-collection-harvest-source'

        parser = SourceFormParser()
        form_data = {
            'url': WAF_HARVEST_SOURCE_URL,
            'source_type': 'waf-collection',
            'title': 'Test WAF colelction harvest source',
            'name': harvest_source_name,
            'collection_metadata_url': COLLECTION_METADATA_URL,
            'validator_profiles': 'iso19139ngdc'
        }
        res = self.app.post('/harvest/new', params=form_data, extra_environ=self.extra_environ)

        assert 'Error' not in res.body
        assert 'Missing value' not in res.body

        res_redirect = self.app.get('/harvest/edit/{}'.format(harvest_source_name), extra_environ=self.extra_environ)
        parser.feed(res_redirect.body)

        assert parser.results['collection_metadata_url'] == COLLECTION_METADATA_URL
        assert parser.results['url'] == WAF_HARVEST_SOURCE_URL
        assert parser.results['source_type'] == 'waf-collection'
        assert parser.results['validator_profiles'] == 'iso19139ngdc'

    def test_create_z3950_harvest_source_form(self):

        self.app = self._get_test_app()

        # Create
        harvest_source_name = u'test-harvest-source'

        parser = SourceFormParser()
        form_data = {
            'url': 'https://test.z3950.com/',
            'source_type': 'z3950',
            'title': 'Test Z3950 harvest source',
            'name': harvest_source_name,
            'database': 'test-database',
            'port': '9999'
        }

        res = self.app.post('/harvest/new', params=form_data, extra_environ=self.extra_environ)
        assert 'Error' not in res.body
        assert 'Missing value' not in res.body

        res_redirect = self.app.get('/harvest/edit/{}'.format(harvest_source_name), extra_environ=self.extra_environ)
        parser.feed(res_redirect.body)

        assert parser.results['url'] == 'https://test.z3950.com/'
        assert parser.results['source_type'] == 'z3950'
        assert parser.results['database'] == 'test-database'
        assert parser.results['port'] == '9999'
