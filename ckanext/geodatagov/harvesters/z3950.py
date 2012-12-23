import logging
import hashlib
import requests
from sqlalchemy.orm import aliased
from PyZ3950 import zoom

from ckan import model

from ckan.plugins.core import SingletonPlugin, implements

from ckanext.harvest.interfaces import IHarvester
from ckanext.harvest.model import HarvestObject
from ckanext.harvest.model import HarvestObjectExtra as HOExtra

from ckanext.geodatagov.harvesters.base import GeoDataGovHarvester, get_extra, guess_standard


class Z3950Harvester(GeoDataGovHarvester, SingletonPlugin):
    '''
    A Harvester for z3950.
    '''

    implements(IHarvester)

    def info(self):
        return {
            'name': 'z3950',
            'title': 'z3950',
            'description': 'z3950 database'
            }

    def gather_stage(self,harvest_job):

        log = logging.getLogger(__name__ + '.WAF.gather')
        log.debug('z3950Harvester gather_stage for job: %r', harvest_job)

        self.harvest_job = harvest_job

        # Get source URL
        source_url = harvest_job.source.url

        self._set_config(harvest_job.source.config)

        # get current objects out of db
        query = model.Session.query(HarvestObject.guid, HarvestObject.package_id).filter(HarvestObject.current==True).\
                                    filter(HarvestObject.harvest_source_id==harvest_job.source.id)

        guid_to_package_id = dict((res[0], res[1]) for res in query)
        current_guids = set(guid_to_package_id.keys())
        current_guids_in_harvest = set()

        # Get contents
        try:
            conn = zoom.Connection(source_url, self.config.get('port', 210))
            conn.databaseName = self.config.get('database', '')
            conn.preferredRecordSyntax = 'XML'
            conn.elementSetName = 'T'
            query = zoom.Query ('CCL', 'metadata')
            res = conn.search (query)
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
        except Exception,e:
            self._save_gather_error('Unable to get content for URL: %s: %r' % \
                                        (source_url, e),harvest_job)
            return None


    def fetch_stage(self, harvest_object):
        return True

