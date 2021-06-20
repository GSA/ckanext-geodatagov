import logging
from ckan.common import config
# from ckan.lib.search.common import make_connection
# from ckan.lib.search.query import SearchQuery

from ckan.lib.search import make_connection, PackageSearchQuery  # , SolrSettings


log = logging.getLogger(__name__)


class GeoPackageSearchQuery(PackageSearchQuery):
    def get_count(self):
        """
        Return the count of all indexed packages.
        """
        query = "*: *"
        fq = "+site_id: \"%s\" " % config.get('ckan.site_id')
        fq += "+state: active "

        conn = make_connection()

        try:
            data = conn.search(query, fq=fq, rows=0)
        except Exception as e:
            error = 'Error in GeoPackageSearchQuery.get_count: {}'.format(e)
            log.error(error)
            print(error)

        return data.hits

    def get_paginated_entity_name_modtime(self, max_results=1000, start=0):
        """
        Return a list of the name and metadata_modified s of indexed packages.
        """
        query = "*: *"
        fq = "+site_id: \"%s\" " % config.get('ckan.site_id')
        fq += "+state: active "

        conn = make_connection()
        try:
            data = conn.search(query,
                               fq=fq,
                               rows=max_results,
                               fields='name,metadata_modified',
                               start=start,
                               sort='metadata_created asc')
        except Exception as e:
            error = 'Error in GeoPackageSearchQuery.get_paginated_entity_name_modtime: {}'.format(e)
            log.error(error)
            print(error)

        return [{'name': r.get('name'),
                'metadata_modified': r.get('metadata_modified')}
                for r in data.docs]
