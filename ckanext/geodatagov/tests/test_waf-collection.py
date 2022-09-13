import json
import logging
import pytest

import ckanext.harvest.model as harvest_model
import mock_static_file_server
from ckan import model
from ckanext.geodatagov.harvesters.waf_collection import WAFCollectionHarvester
from ckanext.spatial.validation import all_validators
from factories import HarvestJobObj, WafCollectionHarvestSourceObj

from ckan.tests.helpers import reset_db, call_action
from ckan.tests.factories import Organization

log = logging.getLogger(__name__)


class TestWafCollectionHarvester(object):

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
        existing_profiles = [v.name for v in all_validators]
        log.info('Existing validator profiles: {}'.format(existing_profiles))
        source = WafCollectionHarvestSourceObj(url=url,
                                               owner_org=self.organization['id'],
                                               # config=source_config,
                                               **sc)
        job = HarvestJobObj(source=source)

        self.harvester = WAFCollectionHarvester()

        # gather stage
        log.info('GATHERING %s', url)
        obj_ids = self.harvester.gather_stage(job)
        log.info('job.gather_errors=%s', job.gather_errors)
        if len(job.gather_errors) > 0:
            raise Exception(job.gather_errors[0])

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

    def get_datasets_from_waf_collection1_sample(self):
        """ harvest waf-collection1/ folder as waf-collection source """
        url = 'http://127.0.0.1:%s/waf-collection1/index.html' % mock_static_file_server.PORT

        collection_metadata = "http://127.0.0.1:%s/waf-collection1/cfg/SeriesCollection_tl_2013_county.shp.iso.xml" %\
            mock_static_file_server.PORT
        config = '{"collection_metadata_url": "%s", "validator_profiles": ["iso19139ngdc"], "private_datasets": false}' %\
            collection_metadata
        self.run_gather(url=url, source_config=config)
        self.run_fetch()
        datasets = self.run_import()

        return datasets

    def test_waf_collection1_datasets_count(self):
        """ Get datasets from waf-collection1/ folder as waf-collection source
            and test we have one dataset with the expected name """

        datasets = self.get_datasets_from_waf_collection1_sample()
        assert len(datasets) == 1
        dataset = datasets[0]
        assert dataset.name == 'tiger-line-shapefile-2013-nation-u-s-current-county-and-equivalent-national-shapefile'

    def test_waf_collection1_datasets_as_child(self):
        """ Harvest waf-collection1/ folder as waf-collection source
            and test we get one dataset and this dataset is a "child" (it have a "collection_package_id" extra)
            and is not a "parent" (do not include the collection_metadata extra) """

        datasets = self.get_datasets_from_waf_collection1_sample()
        dataset = datasets[0]

        extras = json.loads(dataset.extras['extras_rollup'])
        keys = [key for key in list(extras.keys())]
        assert 'collection_package_id' in keys
        assert 'collection_metadata' not in keys

    def test_waf_collection1_parent_exists(self):
        """ Harvest waf-collection1/ folder as waf-collection source
            and test parent dataset exists (include the collection_metadata=true extra) """

        datasets = self.get_datasets_from_waf_collection1_sample()
        dataset = datasets[0]
        extras = json.loads(dataset.extras['extras_rollup'])

        parent = call_action('package_show', context={'user': 'dummy'}, id=extras['collection_package_id'])
        parent_keys = [extra['key'] for extra in parent['extras']]
        assert 'collection_metadata' in parent_keys
        assert 'true' == [extra['value'] for extra in parent['extras'] if extra['key'] == 'collection_metadata'][0]

    def test_waf_collection1_parent_title(self):
        """ Harvest waf-collection1/ folder as waf-collection source
            and test parent dataset have the expected title and name """

        datasets = self.get_datasets_from_waf_collection1_sample()
        dataset = datasets[0]
        extras = json.loads(dataset.extras['extras_rollup'])

        parent = call_action('package_show', context={'user': 'dummy'}, id=extras['collection_package_id'])

        assert parent['title'] == ('TIGER/Line Shapefile, 2013, '
                                   'Series Information File for the Current county and Equivalent National Shapefile')
        assert parent['name'] == ('tiger-line-shapefile-2013-'
                                  'series-information-file-for-the-current-county-and-equivalent-nationa')

    def test_waf_collection_transformation_failed(self):
        url = 'http://127.0.0.1:%s/waf-collection2/index.html' % mock_static_file_server.PORT

        collection_metadata = "http://127.0.0.1:%s/waf-collection2/cfg/SeriesCollection_tl_2013_county.shp.iso.xml" %\
            mock_static_file_server.PORT
        config = '{"collection_metadata_url": "%s", "validator_profiles": ["iso19139ngdc"], "private_datasets": false}' %\
            collection_metadata
        self.run_gather(url=url, source_config=config)

        self.run_fetch()

        # we don't manage IS0 19110
        with pytest.raises(Exception) as e:
            self.run_import()
        assert 'Transformation to ISO failed' in str(e.value)
