import logging

from ckan.plugins.core import SingletonPlugin, implements

from ckanext.harvest.interfaces import IHarvester
from ckanext.harvest.model import HarvestObject

from ckanext.geodatagov.harvesters.base import GeoDataGovHarvester, debug_exception_mode

class DocHarvester(GeoDataGovHarvester, SingletonPlugin):
    '''
    A Harvester for individual spatial metadata documents
    TODO: Move to new logic
    '''

    implements(IHarvester)

    def info(self):
        return {
            'name': 'single-doc',
            'title': 'Single spatial metadata document',
            'description': 'A single spatial metadata document'
            }

    def gather_stage(self,harvest_job):
        log = logging.getLogger(__name__ + '.individual.gather')
        log.debug('DocHarvester gather_stage for job: %r', harvest_job)

        self.harvest_job = harvest_job

        # Get source URL
        url = harvest_job.source.url

        self._set_config(harvest_job.source.config)

        # Get contents
        try:
            content = self._get_content(url)
        except Exception,e:
            self._save_gather_error('Unable to get content for URL: %s: %r' % \
                                        (url, e),harvest_job)
            return None
        try:
            # We need to extract the guid to pass it to the next stage
            gemini_string, gemini_guid = self.get_gemini_string_and_guid(content,url)

            if gemini_guid:
                # Create a new HarvestObject for this identifier
                # Generally the content will be set in the fetch stage, but as we alredy
                # have it, we might as well save a request
                obj = HarvestObject(guid=gemini_guid,
                                    job=harvest_job,
                                    content=gemini_string)
                obj.save()

                log.info('Got GUID %s' % gemini_guid)
                return [obj.id]
            else:
                self._save_gather_error('Could not get the GUID for source %s' % url, harvest_job)
                return None
        except Exception, e:
            self._save_gather_error('Error parsing the document. Is this a valid  document?: %s [%r]'% (url,e),harvest_job)
            if debug_exception_mode:
                raise
            return None


    def fetch_stage(self,harvest_object):
        # The fetching was already done in the previous stage
        return True

