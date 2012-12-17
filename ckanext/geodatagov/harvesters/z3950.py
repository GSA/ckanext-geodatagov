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


        # Get contents
        try:
            conn = zoom.Connection('source_url', self.config.get('port', 220))
            conn.databaseName = self.config.get('database_name', '')
            conn.preferredRecordSyntax = 'XML'
            conn.elementSetName = 'T'
            query = zoom.Query ('CCL', 'metadata')
            res = conn.search (query)
            for num, result in enumerate(res):
                pass



        except Exception,e:
            self._save_gather_error('Unable to get content for URL: %s: %r' % \
                                        (source_url, e),harvest_job)
            return None

        ######  Get current harvest object out of db ######



        for guid, package_id, modified_date, url in query:
            url_to_modified_db[url] = modified_date
            url_to_ids[url] = (guid, package_id)

        ######  Get current list of records from source ######

        url_to_modified_harvest = {} ## mapping of url to last_modified in harvest
        try:
            for url, modified_date in _extract_waf(content,source_url,scraper):
                url_to_modified_harvest[url] = modified_date
        except Exception,e:
            msg = 'Error extracting URLs from %s, error was %s' % (source_url, e)
            self._save_gather_error(msg,harvest_job)
            return None

        ######  Compare source and db ######

        harvest_locations = set(url_to_modified_harvest.keys())
        old_locations = set(url_to_modified_db.keys())

        new = harvest_locations - old_locations
        delete = old_locations - harvest_locations
        possible_changes = old_locations & harvest_locations
        change = []

        for item in possible_changes:
            if (not url_to_modified_harvest[item] or not url_to_modified_db[item] #if there is no date assume change
                or url_to_modified_harvest[item] > url_to_modified_db[item]):
                change.append(item)

        def create_extras(url, date, status):
            return [HOExtra(key='waf_modified_date', value=date),
                    HOExtra(key='waf_location', value=url),
                    HOExtra(key='status', value=status)]

        ids = []
        for location in new:
            guid=hashlib.md5(location.encode('utf8',errors='ignore')).hexdigest()
            obj = HarvestObject(job=harvest_job,
                                extras=create_extras(location,
                                                     url_to_modified_harvest[location],
                                                     'new'),
                                guid=guid
                               )
            obj.save()
            ids.append(obj.id)

        for location in change:
            obj = HarvestObject(job=harvest_job,
                                extras=create_extras(location,
                                                     url_to_modified_harvest[location],
                                                     'change'),
                                guid=url_to_ids[location][0],
                                package_id=url_to_ids[location][1],
                               )
            obj.save()
            ids.append(obj.id)

        for location in delete:
            obj = HarvestObject(job=harvest_job,
                                extras=create_extras('','', 'delete'),
                                guid=url_to_ids[location][0],
                                package_id=url_to_ids[location][1],
                               )
            model.Session.query(HarvestObject).\
                  filter_by(guid=url_to_ids[location][0]).\
                  update({'current': False}, False)

            obj.save()
            ids.append(obj.id)

        if len(ids) > 0:
            log.debug('{0} objects sent to the next stage: {1} new, {2} change, {3} delete'.format(
                len(ids), len(new), len(change), len(delete)))
            return ids
        else:
            self._save_gather_error('No records to change',
                                     harvest_job)
            return None

    def fetch_stage(self, harvest_object):

        # Check harvest object status
        status = get_extra(harvest_object,'status')

        if status == 'delete':
            # No need to fetch anything, just pass to the import stage
            return True

        # We need to fetch the remote document

        # Get location
        url = get_extra(harvest_object, 'waf_location')
        if not url:
            self._save_object_error(
                    'No location defined for object {0}'.format(harvest_object.id),
                    harvest_object)
            return False

        # Get contents
        try:
            content = self._get_content_as_unicode(url)
        except Exception, e:
            msg = 'Could not harvest WAF link {0}: {1}'.format(url, e)
            self._save_object_error(msg, harvest_object)
            return False

        # Check if it is an ISO document
        document_format = guess_standard(content)
        if document_format == 'iso':
            harvest_object.content = content
            harvest_object.save()
        else:
            extra = HOExtra(
                    object=harvest_object,
                    key='original_document',
                    value=content)
            extra.save()

            extra = HOExtra(
                    object=harvest_object,
                    key='original_format',
                    value=document_format)
            extra.save()

        return True

