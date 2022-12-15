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

    def test_s3_upload_txt(self, txt_cli_result):
        """upload test.txt to s3 and make sure there's no errors"""
        # check successful cli run
        assert txt_cli_result.exit_code == 0

        endpoint_url = config.get("ckanext.s3sitemap.endpoint_url")
        bucket = config.get("ckanext.s3sitemap.aws_bucket_name")

        s3_response = requests.get(f"{endpoint_url}/{bucket}/test.txt")
        assert txt_cli_result.output.strip("\n") == s3_response.content.decode("utf8")

        # check content-type
        assert 'text/plain' == s3_response.headers['content-type']

    def test_s3_upload_html(self, html_cli_result):
        """upload test.html to s3 and make sure there's no errors"""
        # check successful cli run
        assert html_cli_result.exit_code == 0

        endpoint_url = config.get("ckanext.s3sitemap.endpoint_url")
        bucket = config.get("ckanext.s3sitemap.aws_bucket_name")

        # chcek content
        s3_response = requests.get(f"{endpoint_url}/{bucket}/test.html")
        assert html_cli_result.output.strip("\n") == s3_response.content.decode("utf8")

        # check content-type
        assert 'application/html' == s3_response.headers['content-type']
