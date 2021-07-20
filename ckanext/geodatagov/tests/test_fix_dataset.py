from nose.tools import assert_in
from ckanext.geodatagov.logic import fix_dataset


def test_fix_dataset():
    data_dict = {
        "title": "test dataset",
        "extras": [
            {"key": "test-key", "value": "test value"},
            {"key": "tags", "value": "taG*01, tag (test) 02"}
        ]
    }

    data_dict = fix_dataset(data_dict)

    assert_in("tag01", [t['name'] for t in data_dict['tags']])
    assert_in("tag-test-02", [t['name'] for t in data_dict['tags']])
