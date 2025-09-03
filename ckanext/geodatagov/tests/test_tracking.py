import logging
import pytest

import ckan.model as model
from ckan.tests import factories, helpers
from click.testing import CliRunner

import ckanext.geodatagov.cli as cli


log = logging.getLogger(__name__)


@pytest.mark.usefixtures("with_plugins")
class TestTracking(object):

    @classmethod
    def setup_class(cls):
        organization = factories.Organization()
        cls.dataset = factories.Dataset(owner_org=organization["id"])
        cls.dataset2 = factories.Dataset(owner_org=organization["id"])

        # insert three raw tracking data with today's date
        import datetime
        today = datetime.date.today().isoformat()
        sql = (
            "INSERT INTO tracking_raw (user_key, url, tracking_type, access_timestamp) VALUES"
            "('aaa','/dataset/{0}','page','{2}'),"
            "('bbb','/dataset/{1}','page','{2}'),"
            "('ccc','/dataset/{1}','page','{2}')"
        ).format(cls.dataset["name"], cls.dataset2["name"], today)

        model.Session.execute(sql)
        model.Session.commit()

    @pytest.fixture
    def cli_result(self):
        runner = CliRunner()
        raw_cli_output = runner.invoke(
            cli.tracking_update,
            args=[],
        )
        return raw_cli_output

    def test_tracking_data_in_package_show(self, cli_result):

        assert cli_result.exit_code == 0

        package = helpers.call_action("package_show", id=self.dataset["id"], include_tracking=True)
        
        assert package['tracking_summary']['total'] == 1
        assert package['tracking_summary']['recent'] == 1
    
    def test_sorting_working_in_package_search(self):

        response = helpers.call_action("package_search")

        # Confirm that the override is working as expected
        assert response['sort'] == 'score desc, views_recent desc'

        # Confirm the results are in the expected order
        results = response["results"]
        print(results)
        assert results[0]['name'] == self.dataset2['name']
        assert results[1]['name'] == self.dataset['name']
