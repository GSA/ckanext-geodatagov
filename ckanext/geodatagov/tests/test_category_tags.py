
import logging
import json
import os
from ckan import plugins as p
from ckan.tests.helpers import reset_db
from ckan.tests import factories


log = logging.getLogger(__name__)


class TestCategoryTags(object):

    @classmethod
    def setup(cls):
        os.system("PGPASSWORD=ckan psql -h db -U ckan -d ckan -c 'drop extension IF EXISTS postgis cascade;'")
        reset_db()
        os.system("PGPASSWORD=ckan psql -h db -U ckan -d ckan -c 'create extension postgis;'")
        # PY2
        os.system("ckan -c test.ini harvester initdb")
        os.system("ckan -c test.ini spatial initdb")
        # echo "Downloading locations table"
        os.system("wget https://github.com/GSA/datagov-deploy/raw/71936f004be1882a506362670b82c710c64ef796/"
                  "ansible/roles/software/ec2/ansible/files/locations.sql.gz -O /tmp/locations.sql.gz")
        # echo "Creating locations table"
        os.system("gunzip -c /tmp/locations.sql.gz | PGPASSWORD=ckan psql -h db -U ckan -d ckan -v ON_ERROR_STOP=1")
        # echo "Cleaning"
        os.system("rm -f /tmp/locations.sql.gz")

    def create_datasets(self):
        organization = factories.Organization()
        self.group1 = factories.Group()
        self.group2 = factories.Group()
        self.dataset1 = factories.Dataset(owner_org=organization['id'], groups=[{"name": self.group1["name"]}])
        self.dataset2 = factories.Dataset(owner_org=organization['id'], groups=[{"name": self.group2["name"]}])
        sysadmin = factories.Sysadmin(name='testUpdate')
        self.user_name = sysadmin['name']

    def test_group_catagory_tag_update(self):
        self.create_datasets()
        context = {'user': self.user_name, 'ignore_auth': True}

        self.dataset1['categories'] = '["cat1"]'
        self.dataset1['group_id'] = self.group1["id"]
        p.toolkit.get_action('group_catagory_tag_update')(context, self.dataset1)
        expected_extra = {"key": "__category_tag_{}".format(self.group1["id"]),
                          "value": json.dumps(self.dataset1['categories'])}
        pkg_dict = p.toolkit.get_action('package_show')(context, {'id': self.dataset1["id"]})
        assert expected_extra in pkg_dict["extras"]

        # test if we preserve category tag extras while we update the dataset
        pkg_dict['Title'] = 'Change title 02'
        pkg_dict = p.toolkit.get_action('package_update')(context, pkg_dict)
        assert expected_extra in pkg_dict["extras"]

        self.dataset2['categories'] = '["cat2"]'
        self.dataset2['group_id'] = self.group2["id"]
        p.toolkit.get_action('group_catagory_tag_update')(context, self.dataset2)
        expected_extra = {"key": "__category_tag_{}".format(self.group2["id"]),
                          "value": json.dumps(self.dataset2['categories'])}
        pkg_dict = p.toolkit.get_action('package_show')(context, {'id': self.dataset2["id"]})
        assert expected_extra in pkg_dict["extras"]

        # test if we preserve category tag extras while we update the dataset
        pkg_dict['Title'] = 'Change title 03'
        pkg_dict = p.toolkit.get_action('package_update')(context, pkg_dict)
        assert expected_extra in pkg_dict["extras"]
