
import logging
import json
from nose.tools import assert_equal, assert_in
from ckan import plugins as p
try:
    from ckan.tests.helpers import reset_db
    from ckan.tests import factories
except ImportError:
    from ckan.new_tests.helpers import reset_db
    from ckan.new_tests import factories

log = logging.getLogger(__name__)


class TestCategoryTags(object):

    @classmethod
    def setup(cls):
        reset_db()
         

    def create_datasets(self):
        organization = factories.Organization()
        self.group1 = factories.Group()
        self.group2 = factories.Group()
        self.dataset1 = factories.Dataset(owner_org=organization['id'], groups=[{"name": self.group1["name"]}])
        self.dataset2 = factories.Dataset(owner_org=organization['id'], groups=[{"name": self.group2["name"]}])
        sysadmin = factories.Sysadmin(name='testUpdate')
        self.user_name = sysadmin['name'].encode('ascii')
       
    def test_group_catagory_tag_update(self):
        self.create_datasets()
        context = {'user': self.user_name, 'ignore_auth':True}

        self.dataset1['categories'] = '["cat1"]'
        self.dataset1['group_id'] = self.group1["id"]
        p.toolkit.get_action('group_catagory_tag_update')(context, self.dataset1)
        expected_extra = {"key": "__category_tag_{}".format(self.group1["id"]), "value": json.dumps(self.dataset1['categories'])}
        pkg_dict = p.toolkit.get_action('package_show')(context, {'id': self.dataset1["id"]})
        assert_in(expected_extra, pkg_dict["extras"])

        self.dataset2['categories'] = '["cat2"]'
        self.dataset2['group_id'] = self.group2["id"]
        p.toolkit.get_action('group_catagory_tag_update')(context, self.dataset2)
        expected_extra = {"key": "__category_tag_{}".format(self.group2["id"]), "value": json.dumps(self.dataset2['categories'])}
        pkg_dict = p.toolkit.get_action('package_show')(context, {'id': self.dataset2["id"]})
        assert_in(expected_extra, pkg_dict["extras"])


    # TODO
    # def test_update_and_check_tags(self):
    #     self.create_datasets()
    #     context = {'user': self.user_name, 'ignore_auth':True}

    #     pkg_dict = p.toolkit.get_action('package_update')(context, self.dataset1)
        
        
