import logging
import hashlib
from PyZ3950 import zoom

from ckan import model

from ckan.plugins.core import SingletonPlugin, implements
from ckan.plugins import IConfigurer

from ckanext.harvest.interfaces import IHarvester
from ckanext.harvest.model import HarvestObject
from ckanext.harvest.model import HarvestObjectExtra as HOExtra

from ckanext.geodatagov.harvesters import GeoDataGovHarvester

from ckan.lib.navl.validators import not_empty, convert_int, ignore_empty
from ckan.logic.validators import boolean_validator

from ckan.plugins.toolkit import add_template_directory, add_resource, requires_ckan_version
from ckanext.geodatagov.helpers import string

requires_ckan_version("2.9")


class Z3950Harvester(GeoDataGovHarvester, SingletonPlugin):
    '''
    A Harvester for z3950.
    '''

    implements(IConfigurer)
    implements(IHarvester)

    # IConfigurer
    def update_config(self, config):
        add_template_directory(config, 'templates')
        add_resource('fanstatic_library', 'geodatagov')

    def info(self):
        return {
            'name': 'z3950',
            'title': 'Z39.50',
            'description': 'A remote database supporting the Z39.50 protocol'
        }

    def extra_schema(self):
        return {'private_datasets': [ignore_empty, boolean_validator],
                'database': [not_empty, string],
                'port': [not_empty, convert_int]}

    def gather_stage(self, harvest_job):

        log = logging.getLogger(__name__ + '.WAF.gather')
        log.debug('z3950Harvester gather_stage for job: %r', harvest_job)

        self.harvest_job = harvest_job

        # Get source URL
        source_url = harvest_job.source.url

        self._set_source_config(harvest_job.source.config)

        # get current objects out of db
        query = model.Session.query(HarvestObject.guid, HarvestObject.package_id).filter(
            True if HarvestObject.current else False).\
            filter(HarvestObject.harvest_source_id == harvest_job.source.id)

        guid_to_package_id = dict((res[0], res[1]) for res in query)
        current_guids = set(guid_to_package_id.keys())
        current_guids_in_harvest = set()

        # Get contents
        try:
            conn = zoom.Connection(source_url, int(self.source_config.get('port', 210)))
            conn.databaseName = self.source_config.get('database', '')
            conn.preferredRecordSyntax = 'XML'
            conn.elementSetName = 'T'
            query = zoom.Query('CCL', 'metadata')
            res = conn.search(query)
            ids = []
            for num, result in enumerate(res):
                hash = hashlib.md5(result.data).hexdigest()
                if hash in current_guids:
                    current_guids_in_harvest.add(hash)
                else:
                    obj = HarvestObject(job=harvest_job, guid=hash, extras=[
                        HOExtra(key='status', value='new'),
                        HOExtra(key='original_document', value=result.data.decode('latin-1')),
                        HOExtra(key='original_format', value='fgdc')
                    ])
                    obj.save()
                    ids.append(obj.id)
            for guid in (current_guids - current_guids_in_harvest):
                obj = HarvestObject(job=harvest_job,
                                    guid=guid,
                                    package_id=guid_to_package_id[guid],
                                    extras=[HOExtra(key='status', value='delete')])
                obj.save()
                ids.append(obj.id)
            return ids
        except Exception as e:
            self._save_gather_error('Unable to get content for URL: %s: %r' %
                                    (source_url, e), harvest_job)
            return None

    def fetch_stage(self, harvest_object):
        return True
