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

    assert "tag01" in [t['name'] for t in data_dict['tags']]
    assert "tag-test-02" in [t['name'] for t in data_dict['tags']]
