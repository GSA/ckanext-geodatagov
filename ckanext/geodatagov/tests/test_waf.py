import json
import logging

import ckanext.harvest.model as harvest_model
import mock_static_file_server
from ckan import model
from ckan.logic import get_action
from ckanext.geodatagov.harvesters.base import GeoDataGovWAFHarvester
from factories import HarvestJobObj, WafHarvestSourceObj

from ckan.tests.helpers import reset_db
from ckan.tests.factories import Organization, Sysadmin


log = logging.getLogger(__name__)


class TestWafHarvester(object):

    @classmethod
    def setup_class(cls):
        log.info('Starting mock http server')
        mock_static_file_server.serve()

    @classmethod
    def setup(cls):
        reset_db()
        cls.organization = Organization()

    def run_gather(self, url, source_config):

        sc = json.loads(source_config)

        source = WafHarvestSourceObj(url=url,
                                     owner_org=self.organization['id'],
                                     config=source_config,
                                     **sc)

        log.info('Created source {}'.format(repr(source)))
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

        self.config1 = '{"validator_profiles": ["iso19139ngdc"], "private_datasets": "false"}'
        self.run_gather(url=url, source_config=self.config1)
        self.run_fetch()
        datasets = self.run_import()

        return datasets

    def get_datasets_from_waf_trim_tags(self):
        """ harvest waf-trim-tags/ folder as waf source """
        url = 'http://127.0.0.1:%s/waf-trim-tags/index.html' % mock_static_file_server.PORT

        self.config1 = '{"validator_profiles": ["iso19139ngdc"], "private_datasets": "false"}'
        self.run_gather(url=url, source_config=self.config1)
        self.run_fetch()
        datasets = self.run_import()

        return datasets

    def test_waf1_datasets_count(self):
        """ Get datasets from waf/ folder as waf source
            and test we have one dataset with the expected name """

        datasets = self.get_datasets_from_waf1_sample()
        assert len(datasets) == 2

    def test_datasets_from_waf_fgdc_sample(self):
        """ harvest waf-fgdc/ folder as waf source """
        url = 'http://127.0.0.1:%s/waf-fgdc/index.html' % mock_static_file_server.PORT

        self.config1 = '{"private_datasets": "false"}'
        self.run_gather(url=url, source_config=self.config1)
        self.run_fetch()
        datasets = self.run_import()

        assert len(datasets) == 1

    def test_waf1_datasets_privacy(self):
        """ Harvest waf1/ folder as waf source and check the datasets are public"""

        datasets = self.get_datasets_from_waf1_sample()
        for dataset in datasets:
            assert dataset.private is False

    def test_waf1_names(self):
        """ Harvest waf1/ folder as waf source and test we have the names we expect """

        expected_names = [
            '2016-cartographic-boundary-file-division-for-united-states-1-500000',
            'coastwatch-regions-in-hdf-format'
        ]
        datasets = self.get_datasets_from_waf1_sample()
        for dataset in datasets:
            assert dataset.name in expected_names

    def test_waf1_source_config(self):
        """ we expect the same config after the harvest process finishes """

        self.get_datasets_from_waf1_sample()
        # config with boolean values, fails (probable a CKAN bug)
        # we expect private_datasets as false, so cast the string to boolean
        # after passing to CKAN stuff
        expected = json.loads(self.config1)
        for key in expected:
            if expected[key] == 'false':
                expected[key] = False
        result = json.loads(self.job.source.config)
        assert expected == result

    def test_waf1_limit_tags(self):
        """ Expect tags to be compliant with the DB (under 100 characters) """
        self.get_datasets_from_waf1_sample()
        tag_objects = model.Tag.all().all()
        log.info("Tags Output Objects: %s", tag_objects)
        tag_list = [tag.name for tag in tag_objects]
        log.info("Tags Output list: %s", tag_list)
        tag_limit_errors = []
        for tag in tag_list:
            if len(tag) > 100:
                tag_limit_errors.append(tag)
        log.info("Tags that are greater than 100 character limit: %s", tag_limit_errors)
        assert (len(tag_limit_errors) == 0)

    def test_waf_trim_tags(self):
        """
            Expect tags to be split by delimiter chars ';,' and trimmed.
            string 'tag1    /tag1 &gt; &gt;    tag2,  tag3; > tag4&gt;tag5;,TAG6      '
            should be trimmed into a list
            ['tag1 /tag1', 'tag2', 'tag3', 'tag4', 'tag5', 'tag6']
        """

        self.get_datasets_from_waf_trim_tags()
        tag_objects = model.Tag.all().all()
        log.info("Tags Output Objects: %s", tag_objects)

        tag_list = [tag.name for tag in tag_objects]
        log.info("Tags Output list: %s", tag_list)

        expected_list = ['tag1 /tag1', 'tag2', 'tag3', 'tag4', 'tag5', 'tag6']
        bad_list = list(set(tag_list) - set(expected_list))
        log.info("Tags that are not trimmed: %s", bad_list)

        assert (tag_list == expected_list)

    def test_extras_rollup(self):
        """ Test https://github.com/GSA/datagov-deploy/issues/2166 """
        datasets = self.get_datasets_from_waf1_sample()
        package = datasets[0]
        pkg = package.as_dict()
        extras = pkg['extras']
        extras_rollup = json.loads(extras['extras_rollup'])
        log.info("Rolled up at create: {}".format(extras_rollup))

        assert extras_rollup

        log.info("extras_rollup package info: %s", package)
        sysadmin = Sysadmin(name='testUpdate')
        user_name = sysadmin['name']
        context = {'user': user_name}
        new_extras = [{'key': key, 'value': value} for key, value in list(extras.items())]

        get_action('package_update')(context, {
            "id": package.id,
            "title": "Test change",
            "extras": new_extras
        })

        updated_package = model.Package.get(package.id)
        extras_rollup = json.loads(updated_package.extras['extras_rollup'])
        assert 'extras_rollup' not in extras_rollup
