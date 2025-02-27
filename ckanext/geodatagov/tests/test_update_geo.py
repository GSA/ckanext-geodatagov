import logging

from ckan.tests.helpers import reset_db

from ckanext.geodatagov.logic import translate_spatial


log = logging.getLogger(__name__)


class TestUpdateGeo(object):

    @classmethod
    def setup(cls):
        reset_db()

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
