import logging
import requests

import pytest
from click.testing import CliRunner, Result

import ckanext.geodatagov.cli as cli

log = logging.getLogger(__name__)


class TestS3TestCommand(object):

    @pytest.fixture
    def cli_result(self) -> Result:

        runner = CliRunner()
        raw_cli_output = runner.invoke(
            cli.s3_test,
            args=[],
        )

        return raw_cli_output

    def test_s3_upload(self, cli_result):
        """upload test.txt to s3 and make sure there's no errors"""
        # check successful cli run
        assert cli_result.exit_code == 0

        uploaded_file = requests.get('http://localstack-container:4566/catalog-sitemap/test.txt')

        assert cli_result.output.strip('\n') == uploaded_file.content.decode('utf8')