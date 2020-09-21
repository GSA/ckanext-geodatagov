import json
import logging
from ckan.common import config
from nose.tools import assert_equal, assert_in

try:
    from ckan.tests.helpers import reset_db
    from ckan.tests import factories
except ImportError:
    from ckan.new_tests.helpers import reset_db
    from ckan.new_tests import factories

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
        
        f = open(path, 'r')
        str_data = f.read()
        f.close()
        try:
            data = json.loads(str_data)
        except Exception as e:
            error = 'Error parsing {}: {}'.format(str_data[:90], str(e)[:90])
            raise Exception(error)

        assert data