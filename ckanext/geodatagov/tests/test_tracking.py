import logging
import os
import pytest

import ckan.model as model
from ckan.tests import factories, helpers
from ckan.tests.helpers import reset_db
from click.testing import CliRunner
from ckan.model.meta import Session, metadata

import ckanext.geodatagov.cli as cli

log = logging.getLogger(__name__)

@pytest.mark.usefixtures("with_plugins")
class TestTracking(object):
    @classmethod
    def setup_class(cls):
        # https://github.com/ckan/ckan/issues/4764
        # drop extension postgis so we can reset db
        os.system("PGPASSWORD=ckan psql -h db -U ckan -d ckan -c 'drop extension IF EXISTS postgis cascade;'")
        reset_db()
        os.system("PGPASSWORD=ckan psql -h db -U ckan -d ckan -c 'create extension postgis;'")
        # echo "Downloading locations table"
        os.system("PGPASSWORD=ckan psql -h db -U ckan -d ckan -c 'DROP TABLE IF EXISTS locations;'")
        os.system("wget https://github.com/GSA/datagov-deploy/raw/71936f004be1882a506362670b82c710c64ef796/"
                  "ansible/roles/software/ec2/ansible/files/locations.sql.gz -O /tmp/locations.sql.gz")
        # echo "Creating locations table"
        os.system("gunzip -c /tmp/locations.sql.gz | PGPASSWORD=ckan psql -h db -U ckan -d ckan -v ON_ERROR_STOP=1")
        # echo "Cleaning"
        os.system("rm -f /tmp/locations.sql.gz")
        # os.system("ckan -c test.ini db upgrade -p harvest")
        metadata.create_all(bind=Session.bind)

    def create_datasets(self):

        organization = factories.Organization()
        self.dataset = factories.Dataset(owner_org=organization["id"])

        # total view should be 0 for a new dataset
        package = helpers.call_action("package_show", id=self.dataset["id"], include_tracking=True)
        assert package['tracking_summary']['total'] == 0

        # insert two raw tracking data
        sql = (
            "INSERT INTO tracking_raw (user_key, url, tracking_type, access_timestamp) VALUES"
            "('aaa','/dataset/{0}','page','2020-10-10'),"
            "('bbb','/dataset/{0}','page','2021-11-11')"
        ).format(self.dataset["name"])

        model.Session.execute(sql)
        model.Session.commit()

    @pytest.fixture
    def cli_result(self):
        self.create_datasets()

        runner = CliRunner()
        raw_cli_output = runner.invoke(
            cli.tracking_update,
            args=[],
        )

        return raw_cli_output

    def test_tracking_data_in_package_show(self, cli_result):
        assert cli_result.exit_code == 0

        pacakge = helpers.call_action("package_show", id=self.dataset["id"], include_tracking=True)
        assert pacakge['tracking_summary']['total'] == 2
        assert pacakge['tracking_summary']['recent'] == 1
