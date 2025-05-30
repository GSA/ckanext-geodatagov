import pytest
import logging

from ckan.tests import factories


log = logging.getLogger(__name__)


@pytest.mark.usefixtures("with_plugins")
class TestFixPkg(object):

    @classmethod
    def setup_class(cls):
        cls.organization = factories.Organization()

    def test_fix_tags(self):
        dataset_extras = [
            {
                "key": "tags",
                "value": "tag01, tag02"
            }
        ]
        dataset = factories.Dataset(
            owner_org=self.organization['id'],
            extras=dataset_extras)

        assert "tag01" in [t['name'] for t in dataset['tags']]
        assert "tag02" in [t['name'] for t in dataset['tags']]

    def test_avoid_duplicated_tags(self):
        dataset_extras = [
            {
                "key": "tags",
                "value": "tag01, tag02"
            }
        ]
        dataset = factories.Dataset(
            owner_org=self.organization['id'],
            extras=dataset_extras,
            tags=[{'name': 'tag01'}])

        assert len(dataset['tags']) == 2
        assert "tag01" in [t['name'] for t in dataset['tags']]
        assert "tag02" in [t['name'] for t in dataset['tags']]
