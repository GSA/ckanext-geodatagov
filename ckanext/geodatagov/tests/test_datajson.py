import json
import os
import pytest

from ckan.tests.helpers import reset_db
from ckan.tests.factories import Organization
from ckan import model
from ckan.model.meta import Session, metadata
from factories import (DataJsonHarvestSourceObj,
                       HarvestJobObj)
import ckanext.harvest.model as harvest_model
from ckanext.datajson.harvester_datajson import DataJsonHarvester
import mock_static_file_server
import logging


log = logging.getLogger(__name__)

@pytest.mark.usefixtures("with_plugins")
class TestDataJsonHarvester(object):

    @classmethod
    def setup_class(cls):
        log.info('Starting mock http server')
        mock_static_file_server.serve(port=8996)        

    def setup_method(self):
        # https://github.com/ckan/ckan/issues/4764
        # drop extension postgis so we can reset db
        os.system("PGPASSWORD=ckan psql -h db -U ckan -d ckan -c 'drop extension IF EXISTS postgis cascade;'")
        reset_db()
        os.system("PGPASSWORD=ckan psql -h db -U ckan -d ckan -c 'create extension postgis;'")
        # echo "Downloading locations table"
        os.system("wget https://github.com/GSA/datagov-deploy/raw/71936f004be1882a506362670b82c710c64ef796/"
                  "ansible/roles/software/ec2/ansible/files/locations.sql.gz -O /tmp/locations.sql.gz")
        # echo "Creating locations table"
        os.system("PGPASSWORD=ckan psql -h db -U ckan -d ckan -c 'DROP TABLE IF EXISTS locations;'")
        os.system("gunzip -c /tmp/locations.sql.gz | PGPASSWORD=ckan psql -h db -U ckan -d ckan -v ON_ERROR_STOP=1")
        # echo "Cleaning"
        os.system("rm -f /tmp/locations.sql.gz")
        # os.system("ckan -c test.ini db upgrade -p harvest")
        metadata.create_all(bind=Session.bind)

    def run_gather(self, url):
        source = DataJsonHarvestSourceObj(url=url, owner_org=self.organization['id'])
        job = HarvestJobObj(source=source)

        self.harvester = DataJsonHarvester()

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

    def test_sample5_data(self):
        self.organization = Organization()

        # testing with data from https://www.consumerfinance.gov/data.json
        url = 'http://127.0.0.1:8996/sample5_data.json'
        obj_ids = self.run_gather(url=url)
        assert len(obj_ids) == 2
        self.run_fetch()
        datasets = self.run_import()
        assert len(datasets) == 2
        titles = ['Consumer Complaint Database',
                  'Home Mortgage Disclosure Act Data for the years 2007-2014']
        for dataset in datasets:
            assert dataset.title in titles
            # test we get the spatial as we want: https://github.com/GSA/catalog.data.gov/issues/55
            # we expect a data transformation here
            pkg = dataset.as_dict()
            extras = json.loads(pkg["extras"]['extras_rollup'])

            assert pkg["extras"]["spatial"] == ('{"type":"Polygon",'
                                                '"coordinates":[[[-124.733253,24.544245],'
                                                '[-124.733253,49.388611],'
                                                '[-66.954811,49.388611],'
                                                '[-66.954811,24.544245],'
                                                '[-124.733253,24.544245]]]}')
            assert extras['old-spatial'] == 'United States'
            assert extras['programCode'] == ['000:000']
