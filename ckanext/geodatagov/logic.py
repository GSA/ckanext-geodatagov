import json
import logging

import ckan.plugins as p
from ckan.logic import side_effect_free


log = logging.getLogger(__name__)

@side_effect_free
def location_search(context, data_dict):
    '''
    Basic bounding box geocoder for countries, US states, US counties
    and US postal codes.

    :param q: The search term. It must have at least 3 characters.
    :type q: string

    Returns an ordered list of locations matching the query, where the
    order is defined by the entity type (countries > states > counties > postal
    codes) and alphabetically.

    Each result contains the following keys:

    :param id: Location identifier
    :type id: integer
    :param text: Location display name
    :type text: string
    :param geom: GeoJSON-like representation of the bbox geometry
    :type geom: dict

    '''
    term = data_dict.get('q')
    if not term:
        raise p.toolkit.ValidationError({'q': 'Missing parameter'})

    if len(term) < 3:
        raise p.toolkit.ValidationError({'q': 'Provide at least three characters'})

    model = context['model']
    sql = '''SELECT id, display_name, ST_AsGeoJSON(the_geom) AS geom
            FROM locations
            WHERE lower(name) LIKE :term
            ORDER BY type_order, display_name'''
    q = model.Session.execute(sql, {'term': '{0}%'.format(term.lower())})

    out = []
    for row in q:
        out.append({'id': row['id'],
                    'text': row['display_name'],
                    'geom': json.loads(row['geom'])})
    return out
