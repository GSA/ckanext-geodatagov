import copy
from urllib2 import URLError
from nose.tools import assert_equal, assert_raises, assert_in
import json
from mock import patch, MagicMock, Mock
from requests.exceptions import HTTPError, RequestException

try:
    from ckan.tests.helpers import reset_db, call_action
    from ckan.tests.factories import Organization, Group, _get_action_user_name
except ImportError:
    from ckan.new_tests.helpers import reset_db, call_action
    from ckan.new_tests.factories import Organization, Group, _get_action_user_name
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


class TestCSWHarvester(object):

    @classmethod
    def setup_class(cls):
        log.info('Starting mock http server')
        mock_csw_source.serve()
        
    @classmethod
    def setup(cls):
        reset_db()
        harvest_model.setup()
        user_name = 'dummy'
        user = call_action('user_create',
                            name=user_name,
                            password='dummybummy',
                            email='dummy@dummy.com')
        org = call_action('organization_create',
                          context={'user': user_name},
                          name='test-org')
        

    def run_source(self, url):
        source = CSWHarvestSourceObj(url=url, owner_org='test-org')
        job = HarvestJobObj(source=source)

        harvester = GeoDataGovCSWHarvester()

        # gather stage
        log.info('GATHERING %s', url)
        obj_ids = harvester.gather_stage(job)
        log.info('job.gather_errors=%s', job.gather_errors)
        if len(job.gather_errors) > 0:
            raise Exception(job.gather_errors[0])
        
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
        if len(harvest_object.errors) > 0:
            raise Exception(harvest_object.errors[0])

        # fetch stage
        log.info('IMPORTING %s', url)
        result = harvester.import_stage(harvest_object)

        log.info('ho errors 2=%s', harvest_object.errors)
        log.info('result 2=%s', result)
        if len(harvest_object.errors) > 0:
            raise Exception(harvest_object.errors[0])

        log.info('ho pkg id=%s', harvest_object.package_id)
        dataset = model.Package.get(harvest_object.package_id)
        log.info('dataset name=%s', dataset.name)

        return harvest_object, result, dataset

    def test_sample3(self):
        # testing with data from geonode.state.gov 
        # getrecords XML: http://geonode.state.gov/catalogue/csw?service=CSW&version=2.0.2&request=GetRecords&ElementSetName=full&typenames=csw:Record&constraints=[]&esn=brief&outputschema=http://www.isotc211.org/2005/gmd&maxrecords=9&resulttype=results

        url = 'http://127.0.0.1:%s/sample3' % mock_csw_source.PORT
        self.run_source(url=url)

    def test_sample4(self):
        # testing with data from portal.opentopography.org/geoportal/csw
        # RECORDS
        # https://portal.opentopography.org/geoportal/csw?service=CSW&version=2.0.2&request=GetRecords&ElementSetName=full&typenames=csw:Record&resulttype=results&constraints=[]&esn=brief&outputschema=http://www.isotc211.org/2005/gmd&maxrecords=9
        # record by ID
        # https://portal.opentopography.org/geoportal/csw?service=CSW&version=2.0.2&request=GetRecordById&ElementSetName=full&typenames=csw:Record&outputschema=http://www.isotc211.org/2005/gmd&id=OT.102019.6341.1&esn=full

        url = 'http://127.0.0.1:%s/sample4' % mock_csw_source.PORT
        self.run_source(url=url)

    def test_datason_404(self):
        url = 'http://127.0.0.1:%s/404' % mock_csw_source.PORT
        with assert_raises(Exception) as e:
            self.run_source(url=url)
        assert 'HTTP Error 404' in str(e.exception)

    def test_datason_500(self):
        url = 'http://127.0.0.1:%s/500' % mock_csw_source.PORT
        with assert_raises(Exception) as e:
            self.run_source(url=url)
        assert 'HTTP Error 500' in str(e.exception)
