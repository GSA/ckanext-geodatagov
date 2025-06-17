import logging

from ckanext.geodatagov.logic import translate_spatial

from utils import populate_locations_table


log = logging.getLogger(__name__)


class TestUpdateGeo(object):

    def setup_method(self):
        populate_locations_table()

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
        assert translate_spatial(
            '["CARTESIAN", [{"WestBoundingCoordinate": -69.864167, "NorthBoundingCoordinate": 70.843889, '
            '"EastBoundingCoordinate": -69.864167, "SouthBoundingCoordinate": 70.843889}, '
            '{"WestBoundingCoordinate": -68.156667, "NorthBoundingCoordinate": 70.313889, '
            '"EastBoundingCoordinate": -68.156667, "SouthBoundingCoordinate": 70.313889}, '
            '{"WestBoundingCoordinate": -70.52, "NorthBoundingCoordinate": 69.846667, '
            '"EastBoundingCoordinate": -70.52, "SouthBoundingCoordinate": 69.846667}, '
            '{"WestBoundingCoordinate": -70.52007, "NorthBoundingCoordinate": 70.843889, '
            '"EastBoundingCoordinate": -68.15668, "SouthBoundingCoordinate": 69.84673}]]'
        ) is None
