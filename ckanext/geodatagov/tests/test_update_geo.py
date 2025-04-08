import logging

from ckanext.geodatagov.logic import translate_spatial, is_geojson

from utils import populate_locations_table


log = logging.getLogger(__name__)


class TestUpdateGeo(object):

    def setup_method(self):
        populate_locations_table()

    def test_is_geojson(self):
        valid_test_cases = [ {
            "type": "Point",
                "coordinates": [125.6, 10.1]
        },
        { "type": "Polygon",
            "coordinates": [
                [ [100.0, 0.0], [101.0, 0.0], [101.0, 1.0],
                    [100.0, 1.0], [100.0, 0.0] ]
                ]
        },
        { "type": "LineString",
            "coordinates": [
                [102.0, 0.0], [103.0, 1.0], [104.0, 0.0], [105.0, 1.0]
                ]
        }
        ]

        for case in valid_test_cases:
            assert is_geojson(case)
        
        invalid_test_cases = [
            "invalid type",
            {},
            { "type": "envelope",
               "coordinates": [
                    [102.0, 0.0], [103.0, 1.0], [104.0, 0.0], [105.0, 1.0]
                    ]
            },
            { "type": "Polygon",
               "coordinates": []
            }
        ]

        for case in invalid_test_cases:
            assert is_geojson(case) is False
                
    def test_translations(self):
        """ test translate_spatial function """

        # Test place in locations table
        us = ('{"type":"Polygon","coordinates":[[[-124.733253,24.544245],[-124.733253,49.388611],'
              '[-66.954811,49.388611],[-66.954811,24.544245],[-124.733253,24.544245]]]}')
        assert translate_spatial('United States') == us
        california = ('{"type":"Polygon","coordinates":[[[-124.3926,32.5358],[-124.3926,42.0022],'
                      '[-114.1252,42.0022],[-114.1252,32.5358],[-124.3926,32.5358]]]}')
        assert translate_spatial('California') == california

        # test numeric versions
        assert translate_spatial('1.0,2.0,3.5,5.5') == ('{"type": "Polygon", "coordinates": '
                                                        '[[[1.0, 2.0], [1.0, 5.5], [3.5, 5.5], '
                                                        '[3.5, 2.0], [1.0, 2.0]]]}')
        # Test not existent places
        assert translate_spatial('not exists') is None
        assert translate_spatial('1.0,3.0') is None
        assert translate_spatial('US, Virginia, Fairfax, Reston') is None
