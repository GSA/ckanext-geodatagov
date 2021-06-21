from builtins import str
from builtins import object
from nose.tools import assert_raises

from ckan.tests.helpers import reset_db
from ckan.tests.factories import Organization
from ckan import model
from factories import (CSWHarvestSourceObj,
                       HarvestJobObj)

import ckanext.harvest.model as harvest_model
from ckanext.geodatagov.harvesters.base import GeoDataGovCSWHarvester
import logging
log = logging.getLogger(__name__)

import mock_csw_source


class TestCSWHarvester(object):

    @classmethod
    def setup_class(cls):
        log.info('Starting mock http server')
        mock_csw_source.serve()

    @classmethod
    def setup(cls):
        model.Repository.tables_created_and_initialised = True
        reset_db()
        cls.organization = Organization()

    def run_gather(self, url):
        source = CSWHarvestSourceObj(url=url, owner_org=self.organization['id'])
        job = HarvestJobObj(source=source)

        self.harvester = GeoDataGovCSWHarvester()

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

    def test_sample3(self):
        # testing with data from geonode.state.gov
        # getrecords XML:
        '''
            http://geonode.state.gov/catalogue/csw?service=CSW&version=2.0.2&request=GetRecords
            &ElementSetName=full&typenames=csw:Record&constraints=[]&esn=brief
            &outputschema=http://www.isotc211.org/2005/gmd&maxrecords=9&resulttype=results
        '''

        url = 'http://127.0.0.1:%s/sample3' % mock_csw_source.PORT
        obj_ids = self.run_gather(url=url)
        assert len(obj_ids) == 2
        self.run_fetch()
        datasets = self.run_import()
        assert len(datasets) == 2
        titles = ['Syria_RefugeeSites_2015Apr16_HIU_USDoS',
                  'Syria_IDPSites_2015Jun11_HIU_USDoS']
        for dataset in datasets:
            assert dataset.title in titles

    def test_sample4(self):
        # testing with data from portal.opentopography.org/geoportal/csw
        # RECORDS
        # https://portal.opentopography.org/geoportal/csw?service=CSW&version=2.0.2&request=GetRecords&ElementSetName=full&typenames=csw:Record&resulttype=results&constraints=[]&esn=brief&outputschema=http://www.isotc211.org/2005/gmd&maxrecords=9
        # record by ID
        # https://portal.opentopography.org/geoportal/csw?service=CSW&version=2.0.2&request=GetRecordById&ElementSetName=full&typenames=csw:Record&outputschema=http://www.isotc211.org/2005/gmd&id=OT.102019.6341.1&esn=full

        url = 'http://127.0.0.1:%s/sample4' % mock_csw_source.PORT
        obj_ids = self.run_gather(url=url)
        assert len(obj_ids) == 2
        self.run_fetch()
        datasets = self.run_import()
        assert len(datasets) == 2
        titles = ['Alteration of Groundwater Flow due to Slow Landslide Failure, CA',
                  'High Resolution Topography of House Range Fault, Utah']
        for dataset in datasets:
            assert dataset.title in titles

    def test_404(self):
        url = 'http://127.0.0.1:%s/404' % mock_csw_source.PORT
        with assert_raises(Exception) as e:
            self.run_gather(url=url)
        assert 'HTTP Error 404' in str(e.exception)

    def test_500(self):
        url = 'http://127.0.0.1:%s/500' % mock_csw_source.PORT
        with assert_raises(Exception) as e:
            self.run_gather(url=url)
        assert 'HTTP Error 500' in str(e.exception)
