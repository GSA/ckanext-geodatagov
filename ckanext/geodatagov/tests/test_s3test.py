import logging

import pytest
import requests
from ckan.common import config
from click.testing import CliRunner, Result

import ckanext.geodatagov.cli as cli

log = logging.getLogger(__name__)


class TestS3TestCommand(object):
    @pytest.fixture
    def txt_cli_result(self) -> Result:

        runner = CliRunner()
        raw_cli_output = runner.invoke(
            cli.s3_test,
            args=['txt'],
        )

        return raw_cli_output

    @pytest.fixture
    def html_cli_result(self) -> Result:

        runner = CliRunner()
        raw_cli_output = runner.invoke(
            cli.s3_test,
            args=['html'],
        )

        return raw_cli_output

    def test_s3_upload(self, html_cli_result, txt_cli_result):
        """upload test.txt to s3 and make sure there's no errors"""
        # check successful cli run
        assert html_cli_result.exit_code == 0
        assert txt_cli_result.exit_code == 0

        endpoint_url = config.get("ckanext.s3sitemap.endpoint_url")
        bucket = config.get("ckanext.s3sitemap.aws_bucket_name")

        uploaded_html_file = requests.get(f"{endpoint_url}/{bucket}/test-html.html")
        assert html_cli_result.output.strip("\n") == uploaded_html_file.content.decode("utf8")

        uploaded_txt_file = requests.get(f"{endpoint_url}/{bucket}/test.txt")
        assert txt_cli_result.output.strip("\n") == uploaded_txt_file.content.decode("utf8")
