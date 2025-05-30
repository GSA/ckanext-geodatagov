import json
import logging
import pytest
from click.testing import CliRunner

from ckan.common import config
from ckan.lib.search.common import make_connection
import ckan.model as model
from ckanext.geodatagov.rebuild import rebuild
from ckan.tests import factories
from ckanext.harvest.model import HarvestObject
from ckanext.harvest.tests import factories as harvest_factories
from ckanext.harvest.logic import HarvestJobExists

import ckanext.geodatagov.cli as cli


log = logging.getLogger(__name__)


@pytest.mark.usefixtures("with_plugins")
class TestSolrDBSync(object):

    def create_datasets(self):

        organization = factories.Organization()
        self.dataset1 = factories.Dataset(owner_org=organization["id"])
        add_harvest_object(self.dataset1)
        self.dataset2 = factories.Dataset(owner_org=organization["id"])
        add_harvest_object(self.dataset2)
        self.dataset3 = factories.Dataset(owner_org=organization["id"])
        add_harvest_object(self.dataset3)
        self.dataset4 = factories.Dataset(owner_org=organization["id"])
        add_harvest_object(self.dataset4)
        self.dataset5 = factories.Dataset(owner_org=organization["id"])
        ho5 = add_harvest_object(self.dataset5)
        # dataset6 has no harvest object.
        self.dataset6 = factories.Dataset(owner_org=organization["id"])

        rebuild()

        # Case 1 - in DB, NOT in Solr
        # -- Everything is okay
        original_db = get_active_db_ids()
        original_solr = get_all_solr_ids()
        assert self.dataset1['id'] in original_db and self.dataset1['id'] in original_solr
        assert self.dataset2['id'] in original_db and self.dataset2['id'] in original_solr
        assert self.dataset3['id'] in original_db and self.dataset3['id'] in original_solr
        assert self.dataset4['id'] in original_db and self.dataset4['id'] in original_solr

        # -- Oh-no! Solr index got deleted
        package_index = cli.index_for(model.Package)
        package_index.remove_dict({'id': self.dataset1["id"]})
        case1_solr = get_all_solr_ids()

        # -- Verify solr index is what we think it is
        assert self.dataset1['id'] in original_db and self.dataset1['id'] not in case1_solr
        assert self.dataset2['id'] in original_db and self.dataset2['id'] in case1_solr
        assert self.dataset3['id'] in original_db and self.dataset3['id'] in case1_solr
        assert self.dataset4['id'] in original_db and self.dataset4['id'] in case1_solr

        # Case 2 - DB and Solr synced
        # -- There's no change in dataset 2

        # Case 3 - Newer data in DB
        # -- Yay! New data in DB
        sql = '''update package set metadata_modified = '2022-01-01 00:00:00' where id = '%s' ''' % (self.dataset3["id"])
        model.Session.execute(sql)
        model.Session.commit()

        # -- Verify DB date is different from Solr date
        assert get_db_id_time(self.dataset3["id"]) < get_solr_id_time(self.dataset3["id"])

        # Case 4 - NOT in DB, in Solr
        # -- Oh-no...again! Package got deleted in DB
        sql = '''update package set state = 'deleted' where id = '%s' ''' % (self.dataset4["id"])
        model.Session.execute(sql)
        model.Session.commit()

        # -- Verify package still in Solr and not in DB
        case4_db = get_active_db_ids()
        case4_solr = get_all_solr_ids()
        assert (self.dataset1['id'] in case4_db) and (self.dataset1['id'] not in case4_solr)
        assert (self.dataset2['id'] in case4_db) and (self.dataset2['id'] in case4_solr)
        assert (self.dataset3['id'] in case4_db) and (self.dataset3['id'] in case4_solr)
        assert (self.dataset4['id'] not in case4_db) and (self.dataset4['id'] in case4_solr)

        # Case 5 - changing harvest_object_id in DB makes Solr out of date
        # Solr starts with the same id as the current harvest_object.id
        assert get_solr_hoid(self.dataset5['id']) == ho5.id

        # mark the current harvest_object outdated
        ho5.current = False
        ho5.save()

        # a new harvest_object with a new id.
        add_harvest_object(self.dataset5, "newid")

        # Solr is unaware of the new id
        assert get_solr_hoid(self.dataset5['id']) != 'newid'

        # Case 6 - Remove dataset from SOLR
        # different from case 1, dataset6 should be added back to index after script run
        package_index.remove_dict({'id': self.dataset6["id"]})

    @pytest.fixture
    def cli_result(self):
        self.create_datasets()

        runner = CliRunner()
        raw_cli_output = runner.invoke(
            cli.db_solr_sync,
            args=[],
        )

        return raw_cli_output

    def test_solr_db_state_changes(self, cli_result):
        """run db-solr-sync and analyze results"""
        # check successful cli run
        assert cli_result.exit_code == 0

        final_db = get_active_db_ids()
        final_solr = get_all_solr_ids()

        assert self.dataset1['id'] in final_db and self.dataset1['id'] in final_solr
        assert self.dataset2['id'] in final_db and self.dataset2['id'] in final_solr
        assert self.dataset3['id'] in final_db and self.dataset3['id'] in final_solr
        assert get_db_id_time(self.dataset3["id"]) == get_solr_id_time(self.dataset3["id"])
        assert self.dataset4['id'] not in final_db and self.dataset4['id'] not in final_solr

        assert get_solr_hoid(self.dataset5['id']) == "newid"

        assert self.dataset6['id'] in final_db and self.dataset6['id'] not in final_solr


def get_active_db_ids():
    """
    Return a list of the IDs of all packages in DB.
    """
    db_package = [r[0] for r in model.Session.query(model.Package.id,
                  model.Package.metadata_modified).filter(model.Package.state != 'deleted').all()]
    return db_package


def get_db_id_time(id):
    """
    Return the modified datetime for a particular package id in DB.
    """
    return [r[0] for r in model.Session.query(model.Package.metadata_modified,
            model.Package.metadata_modified).filter(model.Package.id == id).all()]


def get_all_solr_ids():
    """
    Return a list of the IDs of all indexed packages.
    """
    query = "*:*"
    fq = "+site_id:\"%s\" " % config.get('ckan.site_id')
    fq += "+state:active "

    conn = make_connection()
    data = conn.search(query, fq=fq, rows=10, fl='id')

    return [r.get('id') for r in data.docs]


def get_solr_id_time(id):
    """
    Return the modified datetime for a particular package id.
    """
    query = "*:*"
    fq = "+site_id:\"%s\" " % config.get('ckan.site_id')
    fq += "+state:active "
    fq += "+id:%s" % (id)

    conn = make_connection()
    data = conn.search(query, fq=fq, rows=10, fl='metadata_modified')

    return [r.get('metadata_modified') for r in data.docs]


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


def add_harvest_object(dataset, id=None):

    ho = HarvestObject(
        package_id=dataset['id'],
        job=create_harvest_job(),
        current=True
    )
    if id:
        ho.id = id

    ho.save()
    return ho
