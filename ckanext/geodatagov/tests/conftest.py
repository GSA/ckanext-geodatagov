import pytest

import utils


@pytest.fixture(scope="session", autouse=True)
def run_once_for_all_tests():
    utils.simple_http_server()

@pytest.fixture(scope="class", autouse=True)
def run_for_every_test_class():
    utils.reset_db_and_solr()