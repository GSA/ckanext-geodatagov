import copy
from urllib2 import URLError
from nose.tools import assert_equal, assert_raises, assert_in
import json
from mock import patch, MagicMock, Mock
from requests.exceptions import HTTPError, RequestException

try:
    from ckan.tests.helpers import reset_db, call_action
    from ckan.tests.factories import Organization, Group
except ImportError:
    from ckan.new_tests.helpers import reset_db, call_action
    from ckan.new_tests.factories import Organization, Group
from ckan import model
from ckan.plugins import toolkit
from ckan.lib.munge import munge_title_to_name
from factories import (CSWHarvestSourceObj,
                       HarvestJobObj)

import ckanext.harvest.model as harvest_model
from ckanext.harvest.harvesters.base import HarvesterBase
from ckanext.geodatagov.harvesters.base import GeoDataGovCSWHarvester
import logging
log = logging.getLogger(__name__)

import mock_csw_source

# Start data json sources server we can test harvesting against it
mock_csw_source.serve()


class TestCSWHarvester(object):
    @classmethod
    def setup(cls):
        reset_db()
        harvest_model.setup()

    def run_source(self, url):
        source = CSWHarvestSourceObj(url=url)
        job = HarvestJobObj(source=source)

        harvester = GeoDataGovCSWHarvester()

        # gather stage
        log.info('GATHERING %s', url)
        obj_ids = harvester.gather_stage(job)
        log.info('job.gather_errors=%s', job.gather_errors)
        log.info('obj_ids=%s', obj_ids)
        if obj_ids is None or len(obj_ids) == 0:
            # nothing to see
            return

        harvest_object = harvest_model.HarvestObject.get(obj_ids[0])
        log.info('ho guid=%s', harvest_object.guid)
        log.info('ho content=%s', harvest_object.content)

        # fetch stage
        log.info('FETCHING %s', url)
        result = harvester.fetch_stage(harvest_object)

        log.info('ho errors=%s', harvest_object.errors)
        log.info('result 1=%s', result)

        # fetch stage
        log.info('IMPORTING %s', url)
        result = harvester.import_stage(harvest_object)

        log.info('ho errors 2=%s', harvest_object.errors)
        log.info('result 2=%s', result)
        log.info('ho pkg id=%s', harvest_object.package_id)
        dataset = model.Package.get(harvest_object.package_id)
        log.info('dataset name=%s', dataset.name)

        return harvest_object, result, dataset

    def test_sample1(self):
        url = 'http://127.0.0.1:%s/sample1' % mock_csw_source.PORT
        harvest_object, result, dataset = self.run_source(url=url)
        #TODO
        raise NotImplementedError

    def test_datason_404(self):
        url = 'http://127.0.0.1:%s/404' % mock_csw_source.PORT
        with assert_raises(URLError) as harvest_context:
            self.run_source(url=url)
        
    def test_datason_500(self):
        url = 'http://127.0.0.1:%s/500' % mock_csw_source.PORT
        with assert_raises(URLError) as harvest_context:
            self.run_source(url=url)
