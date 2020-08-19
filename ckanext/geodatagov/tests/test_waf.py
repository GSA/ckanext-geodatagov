import json
import logging

import ckanext.harvest.model as harvest_model
import mock_static_file_server
from ckan import model
from ckanext.geodatagov.harvesters.base import GeoDataGovWAFHarvester
from factories import HarvestJobObj, WafHarvestSourceObj
from nose.tools import assert_equal, assert_in, assert_not_in, assert_raises

try:
    from ckan.tests.helpers import reset_db, call_action
    from ckan.tests.factories import Organization, Group, _get_action_user_name, Sysadmin
except ImportError:
    from ckan.new_tests.helpers import reset_db, call_action
    from ckan.new_tests.factories import Organization, Group, _get_action_user_name, Sysadmin

log = logging.getLogger(__name__)


class TestWafHarvester(object):

    @classmethod
    def setup_class(cls):
        log.info('Starting mock http server')
        mock_static_file_server.serve()

    @classmethod
    def setup(cls):
        reset_db()
        harvest_model.setup()
        sysadmin = Sysadmin(name='dummy')
        user_name = sysadmin['name'].encode('ascii')
        call_action('organization_create',
                    context={'user': user_name},
                    name='test-org')

    def run_gather(self, url, source_config):

        sc = json.loads(source_config)
        
        source = WafHarvestSourceObj(url=url,
                                    owner_org='test-org',
                                    config=source_config,
                                    **sc)
        self.job = HarvestJobObj(source=source)

        self.harvester = GeoDataGovWAFHarvester()
        
        # gather stage
        log.info('GATHERING %s', url)
        obj_ids = self.harvester.gather_stage(self.job)
        log.info('job.gather_errors=%s', self.job.gather_errors)
        if len(self.job.gather_errors) > 0:
            raise Exception(self.job.gather_errors[0])

        log.info('obj_ids=%s', obj_ids)
        if obj_ids is None or len(obj_ids) == 0:
            # nothing to see
            return

        self.harvest_objects = []
        for obj_id in obj_ids:
            harvest_object = harvest_model.HarvestObject.get(obj_id)
            log.info('ho guid=%s', harvest_object.guid)
            log.info('ho content=%s', harvest_object.content)
            self.harvest_objects.append(harvest_object)

        # this is a list of harvestObjects IDs. One for dataset
        return obj_ids

    def run_fetch(self):
        # fetch stage
        for harvest_object in self.harvest_objects:
            log.info('FETCHING %s' % harvest_object.id)
            result = self.harvester.fetch_stage(harvest_object)

            log.info('ho errors=%s', harvest_object.errors)
            log.info('result 1=%s', result)
            if len(harvest_object.errors) > 0:
                raise Exception(harvest_object.errors[0])

    def run_import(self):
        # fetch stage
        datasets = []
        for harvest_object in self.harvest_objects:
            log.info('IMPORTING %s' % harvest_object.id)
            result = self.harvester.import_stage(harvest_object)

            log.info('ho errors 2=%s', harvest_object.errors)
            log.info('result 2=%s', result)
            if len(harvest_object.errors) > 0:
                raise Exception(harvest_object.errors[0])

            log.info('ho pkg id=%s', harvest_object.package_id)
            dataset = model.Package.get(harvest_object.package_id)
            datasets.append(dataset)
            log.info('dataset name=%s', dataset.name)

        return datasets

    def get_datasets_from_waf1_sample(self):
        """ harvest waf1/ folder as waf source """
        url = 'http://127.0.0.1:%s/waf1/index.html' % mock_static_file_server.PORT

        self.config1 = '{"private_datasets": false, "validator_profiles": ["iso19139ngdc"]}'
        self.run_gather(url=url, source_config=self.config1)
        self.run_fetch()
        datasets = self.run_import()

        return datasets

    def test_waf1_datasets_count(self):
        """ Get datasets from waf/ folder as waf source
            and test we have one dataset with the expected name """

        datasets = self.get_datasets_from_waf1_sample()
        assert_equal(len(datasets), 1)
        
    def test_waf1_datasets_privacy(self):
        """ Harvest waf1/ folder as waf source and check the datasets are public"""

        datasets = self.get_datasets_from_waf1_sample()
        for dataset in datasets:
            assert_equal(dataset.private, False)
    
    def test_waf1_names(self):
        """ Harvest waf1/ folder as waf source and test we have the names we expect """

        expected_names = ['2016-cartographic-boundary-file-division-for-united-states-1-500000']
        datasets = self.get_datasets_from_waf1_sample()
        for dataset in datasets:
            assert_in(dataset.name, expected_names)
    
    def test_waf1_source_config(self):
        """ we expect the same config after the harvest process finishes """

        self.get_datasets_from_waf1_sample()
        assert_equal(self.job.source.config, self.config1)
        