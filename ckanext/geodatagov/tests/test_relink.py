import json
import logging
import datetime

import pytest
from ckan.common import config
from ckan.lib.search.common import make_connection
import ckan.model as model
import ckan.lib.search as search
from ckan.tests import factories
from ckan.tests.helpers import reset_db
from click.testing import CliRunner

from ckanext.harvest.model import HarvestObject
from ckanext.harvest.tests import factories as harvest_factories
from ckanext.harvest.logic import HarvestJobExists

import ckanext.geodatagov.cli as cli

log = logging.getLogger(__name__)


class TestRelink(object):
    @classmethod
    def setup_class(cls):
        reset_db()
        search.clear_all()

    def create_datasets(self):

        organization = factories.Organization()
        self.dataset1 = factories.Dataset(owner_org=organization["id"])

        self.dataset1_hoid1 = HarvestObject(
            package_id=self.dataset1['id'],
            job=create_harvest_job(),
            import_finished = datetime.datetime.utcnow()
            state='COMPLETE',
            report_status='',
            current=False
        )
        self.dataset1_hoid1.save()

        self.dataset1_hoid2 = HarvestObject(
            package_id=self.dataset1['id'],
            job=create_harvest_job(),
            import_finished = datetime.datetime.utcnow(),
            state='COMPLETE',
            current=True
        )
        self.dataset1_hoid2.save()

        search.rebuild()

        # check solr is using the current=True harvest object
        assert get_solr_hoid(self.dataset1['id']) == self.dataset1_hoid2.id

        # make all harvest objects current=False, but one with newer import_finished
        self.dataset1_hoid1.current = False
        self.dataset1_hoid1.import_finished = datetime.datetime.utcnow()
        self.dataset1_hoid1.save()
        self.dataset1_hoid2.current = False
        self.dataset1_hoid2.save()

    @pytest.fixture
    def cli_result(self):
        self.create_datasets()

        runner = CliRunner()
        raw_cli_output = runner.invoke(
            cli.harvest_object_relink,
            args=[],
        )

        return raw_cli_output

    def test_relink_current_harvest_object(self, cli_result):
        """run harvest_object_relink and analyze results"""
        # check successful cli run
        assert cli_result.exit_code == 0

        # check harvest object with newer import_finished is now current
        assert get_hoid_current(self.dataset1_hoid1.id) is True
        assert get_hoid_current(self.dataset1_hoid2.id) is False

        # check that solr has current harvest object
        assert get_solr_hoid(self.dataset1['id']) == self.dataset1_hoid1.id


def get_hoid_current(id):
    """
    Return the current value for a particular harvest object in DB.
    """
    return model.Session.query(
        HarvestObject.current).filter(HarvestObject.id == id).first()[0]


def get_solr_hoid(id):
    """
    Return the harvest_object_id for a particular package id in Solr.
    """
    query = "*:*"
    fq = "+site_id:\"%s\" " % config.get('ckan.site_id')
    fq += "+state:active "
    fq += "+id:%s" % (id)

    conn = make_connection()
    data = conn.search(query, fq=fq, rows=10, fl='validated_data_dict')

    harvest_object_id = None
    if data.docs:
        data_dict = json.loads(data.docs[0].get("validated_data_dict"))
        for extra in data_dict.get("extras", []):
            if extra["key"] == "harvest_object_id":
                harvest_object_id = extra["value"]
                break

    return harvest_object_id


def create_harvest_job():
    """
    Create a fictitious harvest job object and return it
    """
    SOURCE_DICT = {
        "url": "http://test",
        "name": "test-ho-id",
        "title": "Test source harvest object id",
        "source_type": "ckan",
        "frequency": "MANUAL"
    }
    source = harvest_factories.HarvestSourceObj(**SOURCE_DICT)
    try:
        job = harvest_factories.HarvestJobObj(source=source)
    except HarvestJobExists:  # not sure why
        job = source.get_jobs()[0]

    job.save()

    return job
