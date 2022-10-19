import logging

import pytest
from ckan.common import config
from ckan.lib.search.common import make_connection
import ckan.model as model
import ckan.lib.search as search
from ckan.tests import factories
from ckan.tests.helpers import reset_db
from click.testing import CliRunner

import ckanext.geodatagov.cli as cli

log = logging.getLogger(__name__)


class TestSolrDBSync(object):
    @classmethod
    def setup_class(cls):
        reset_db()
        search.clear_all()

    def create_datasets(self):

        organization = factories.Organization()
        self.dataset1 = factories.Dataset(owner_org=organization["id"])
        self.dataset2 = factories.Dataset(owner_org=organization["id"])
        self.dataset3 = factories.Dataset(owner_org=organization["id"])
        self.dataset4 = factories.Dataset(owner_org=organization["id"])
        search.rebuild()

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
