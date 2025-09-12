import logging

from ckan import model
from ckan import plugins as p
from ckan.logic import NotFound, NotAuthorized, get_action

log = logging.getLogger(__name__)


def count_collection_package(source_id, identifier):
    if not source_id or not identifier:
        return 0

    context = {'model': model, 'session': model.Session}
    package_search = get_action('package_search')
    search_params = {
        'fq': f'harvest_source_id:{source_id} isPartOf:"{identifier}"',
        'rows': 0,
    }

    search_result = package_search(context, search_params)

    return search_result['count'] if search_result['count'] else 0


def get_collection_package(collection_info):
    context = {'model': model, 'session': model.Session}

    package_search = get_action('package_search')

    # collection_info is a string like "source-id parent-id"
    # source_id is a GUID, not supposed to have spaces, therefore we can
    # split it into source_id and identifier at the first space
    source_id, identifier = collection_info.split(" ", 1)
    search_params = {
        'fq': f'harvest_source_id:"{source_id}" identifier:"{identifier}"',
        'rows': 1,
    }

    search_result = package_search(context, search_params)

    ret = None

    if search_result['results']:
        collection_package_id = search_result['results'][0]['id']

        try:
            package = p.toolkit.get_action('package_show')(
                context,
                {'id': collection_package_id}
            )
            ret = package
        except (NotFound, NotAuthorized):
            pass

    return ret


def string(value):
    return str(value)
