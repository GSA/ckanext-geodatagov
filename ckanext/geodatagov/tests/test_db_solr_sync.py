import logging

import pytest
import ckan.model as model
from ckan.tests import factories
from ckan.tests.helpers import reset_db
from click.testing import CliRunner

import ckanext.geodatagov.cli as cli

log = logging.getLogger(__name__)


class TestSolrDBSync(object):
    @classmethod
    def setup(cls):
        reset_db()

    def create_datasets(self):

        organization = factories.Organization()
        self.dataset1 = factories.Dataset(owner_org=organization["id"])
        self.dataset2 = factories.Dataset(owner_org=organization["id"])
        self.dataset3 = factories.Dataset(owner_org=organization["id"])
        self.dataset4 = factories.Dataset(owner_org=organization["id"])

        # Case 1 - in DB, NOT in Solr
        package_index = cli.index_for(model.Package)
        package_index.remove_dict({'id': self.dataset1["id"]})

        # Case 2 - DB and Solr synced
        # dataset 2

        # Case 3 - Newer data in DB
        sql = '''update package set metadata_modified = '2022-01-01 00:00:00' where id = '%s' ''' % (self.dataset3["id"])
        model.Session.execute(sql)
        model.Session.commit()

        # Case 4 - NOT in DB, in Solr
        sql = '''update package set state = 'deleted' where id = '%s' ''' % (self.dataset4["id"])
        model.Session.execute(sql)
        model.Session.commit()

    @pytest.fixture
    def cli_result(self):
        self.create_datasets()

        runner = CliRunner()
        raw_cli_output = runner.invoke(
            cli.db_solr_sync,
            args=[],
        )

        return raw_cli_output

    @staticmethod
    def test_cli_text_output(cli_result):
        # check successful cli run
        assert cli_result.exit_code == 0

        print(cli_result.output)
        assert False

    def test_solr_db_state_changes(self, cli_result):
        """run db-solr-sync and analyze results"""

        changes = cli_result
        print(changes)

        assert False
