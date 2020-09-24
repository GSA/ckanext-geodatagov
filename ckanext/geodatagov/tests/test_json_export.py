import json
import logging
from nose.tools import assert_equal, assert_in
from nose.plugins.skip import SkipTest
try:
    from ckan.tests.helpers import reset_db
    from ckan.tests import factories
    from ckan.common import config
except ImportError:  # CKAN 2.3
    from ckan.new_tests.helpers import reset_db
    from ckan.new_tests import factories
    from pylons import config

from ckanext.geodatagov.commands import GeoGovCommand


log = logging.getLogger(__name__)


class TestJSONExport(object):

    @classmethod
    def setup(cls):
        reset_db()
        
    def create_datasets(self):

        org_extras = [{'key': 'organization_type', 'value': 'Federal Government'}]
        organization = factories.Organization(extras=org_extras)    
        dataset1 = factories.Dataset(owner_org=organization['id'])
        dataset2 = factories.Dataset(owner_org=organization['id'])
        
    def test_json_output(self):
        """ run json_export and analyze results """
        
        self.create_datasets()

        # skip AWS bucket if exists
        config['ckanext.geodatagov.aws_bucket_name'] = None
        
        cmd = GeoGovCommand('test')
        path, _ = cmd.jsonl_export()
        
        parsed_lines = 0
        with open(path, 'r') as f:
            line = f.readline()
            while line:
                data = json.loads(line)
                parsed_lines += 1
                line = f.readline()
        
        log.info('Data is JSON valid: {} parsed lines'.format(parsed_lines))
        assert parsed_lines > 0