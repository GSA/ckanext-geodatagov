import logging

from ckan.tests.helpers import reset_db
from ckan.tests import factories


# import json
# from ckan.common import config
# from ckanext.geodatagov.commands import GeoGovCommand

log = logging.getLogger(__name__)


class TestJSONExport(object):

    @classmethod
    def setup(cls):
        reset_db()

    def create_datasets(self):

        org_extras = [{'key': 'organization_type', 'value': 'Federal Government'}]
        organization = factories.Organization(extras=org_extras)
        dataset1 = factories.Dataset(owner_org=organization['id'])  # NOQA
        dataset2 = factories.Dataset(owner_org=organization['id'])  # NOQA

    # TODO: Fix this test when `jsonl_export` is no longer defunct
    '''
    def test_json_output(self):
        """ run json_export and analyze results """

        self.create_datasets()

        # skip AWS bucket if exists
        config['ckanext.geodatagov.aws_bucket_name'] = None

        cmd = GeoGovCommand()
        path, _ = cmd.jsonl_export()

        parsed_lines = 0
        with open(path, 'r') as f:
            line = f.readline()
            while line:
                data = json.loads(line)  # NOQA
                parsed_lines += 1
                line = f.readline()

        log.info('Data is JSON valid: {} parsed lines'.format(parsed_lines))
        assert parsed_lines > 0
    '''
