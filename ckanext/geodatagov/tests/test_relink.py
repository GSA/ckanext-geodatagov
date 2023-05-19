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
    def setup_class(self):
        reset_db()
        search.clear_all()

        organization = factories.Organization()
        # create two harvest sources
        self.source1 = harvest_factories.HarvestSourceObj(
            url="http://test1",
            name="test-ho-id1",
            title="Test relink 1",
            source_type="ckan",
            frequency="MANUAL"
        )
        self.source2 = harvest_factories.HarvestSourceObj(
            url="http://test2",
            name="test-ho-id2",
            title="Test relink 2",
            source_type="ckan",
            frequency="MANUAL"
        )

        # dataset 1 is for source 1
        self.dataset1 = factories.Dataset(owner_org=organization["id"])
        # with false hoid1 and true hoid2
        self.dataset1_hoid1 = HarvestObject(
            package_id=self.dataset1['id'],
            job=create_harvest_job(self.source1),
            import_finished=datetime.datetime.utcnow(),
            state='COMPLETE',
            report_status='',
            current=False
        )
        self.dataset1_hoid2 = HarvestObject(
            package_id=self.dataset1['id'],
            job=create_harvest_job(self.source2),
            import_finished=datetime.datetime.utcnow(),
            state='COMPLETE',
            current=True
        )
        self.dataset1_hoid1.save()
        self.dataset1_hoid2.save()

        # dataset 2 is for source 2
        self.dataset2 = factories.Dataset(owner_org=organization["id"])
        # with false hoid1 and true hoid2
        self.dataset2_hoid1 = HarvestObject(
            package_id=self.dataset2['id'],
            job=create_harvest_job(self.source2),
            import_finished=datetime.datetime.utcnow(),
            state='COMPLETE',
            report_status='',
            current=False
        )
        self.dataset2_hoid2 = HarvestObject(
            package_id=self.dataset2['id'],
            job=create_harvest_job(self.source2),
            import_finished=datetime.datetime.utcnow(),
            state='COMPLETE',
            current=True
        )
        self.dataset2_hoid1.save()
        self.dataset2_hoid2.save()

        search.rebuild()

        # check solr is using the current=True harvest object hoid2
        assert get_solr_hoid(self.dataset1['id']) == self.dataset1_hoid2.id
        assert get_solr_hoid(self.dataset2['id']) == self.dataset2_hoid2.id

        # make all harvest objects current=False, but hoid1 with newer import_finished
        self.dataset1_hoid1.current = False
        self.dataset1_hoid1.import_finished = datetime.datetime.utcnow()
        self.dataset1_hoid1.save()
        self.dataset1_hoid2.current = False
        self.dataset1_hoid2.save()

        self.dataset2_hoid1.current = False
        self.dataset2_hoid1.import_finished = datetime.datetime.utcnow()
        self.dataset2_hoid1.save()
        self.dataset2_hoid2.current = False
        self.dataset2_hoid2.save()

    @pytest.fixture
    def cli_result_source1(self):
        runner = CliRunner()
        raw_cli_output = runner.invoke(
            cli.harvest_object_relink,
            args=[self.source1.id],
        )

        return raw_cli_output

    @pytest.fixture
    def cli_result_all(self):
        runner = CliRunner()
        raw_cli_output = runner.invoke(
            cli.harvest_object_relink,
            args=[],
        )

        return raw_cli_output

    @pytest.mark.order1
    def test_relink_source1(self, cli_result_source1):
        """run harvest_object_relink and analyze results"""
        # check successful cli run
        assert cli_result_source1.exit_code == 0

        # check harvest object with newer import_finished is now current
        assert get_hoid_current(self.dataset1_hoid1.id) is True
        assert get_hoid_current(self.dataset1_hoid2.id) is False

        # check that solr has current harvest object for source1 dataset
        assert get_solr_hoid(self.dataset1['id']) == self.dataset1_hoid1.id

        # check that solr has not changed for source2 dataset
        assert get_solr_hoid(self.dataset2['id']) == self.dataset2_hoid2.id

    @pytest.mark.order2
    def test_relink_all(self, cli_result_all):
        """run harvest_object_relink and analyze results"""
        # check successful cli run
        assert cli_result_all.exit_code == 0

        # check harvest object with newer import_finished is now current
        assert get_hoid_current(self.dataset2_hoid1.id) is True
        assert get_hoid_current(self.dataset2_hoid2.id) is False

        # check that solr has current harvest object for both sources' datasets
        assert get_solr_hoid(self.dataset1['id']) == self.dataset1_hoid1.id
        assert get_solr_hoid(self.dataset2['id']) == self.dataset2_hoid1.id


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


def create_harvest_job(source):
    """
    Create a fictitious harvest job object and return it
    """
    try:
        job = harvest_factories.HarvestJobObj(source=source)
    except HarvestJobExists:  # not sure why
        job = source.get_jobs()[0]

    job.save()

    return job
