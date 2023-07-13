import logging

log = logging.getLogger(__name__)
import hashlib

import requests
from ckan import model
from ckan.lib.navl.validators import not_empty  # , ignore_empty

import ckanext.harvest.queue as queue
from ckanext.geodatagov.harvesters.base import (
    GeoDataGovWAFHarvester,
)  # , validate_profiles; , validate_profiles
from ckanext.harvest.model import HarvestObject
from ckanext.harvest.model import HarvestObjectExtra as HOExtra
from ckanext.geodatagov.helpers import string


class WAFCollectionHarvester(GeoDataGovWAFHarvester):
    def info(self):
        return {
            "name": "waf-collection",
            "title": "Web Accessible Folder (WAF) Homogeneous Collection",
            "description": "A Web Accessible Folder (WAF) displaying a list"
            "of spatial metadata documents with a collection record",
        }

    def extra_schema(self):
        extra_schema = super(WAFCollectionHarvester, self).extra_schema()
        extra_schema["collection_metadata_url"] = [not_empty, string]
        log.debug(
            "Getting extra schema for WAFCollectionHarvester: {}".format(extra_schema)
        )
        return extra_schema

    def get_package_dict(self, iso_values, harvest_object):

        package_dict = super(WAFCollectionHarvester, self).get_package_dict(
            iso_values, harvest_object
        )
        if not package_dict:
            return None

        collection_package_id = self._get_object_extra(
            harvest_object, "collection_package_id"
        )
        if collection_package_id:
            package_dict["extras"].append(
                dict(key="collection_package_id", value=collection_package_id)
            )

        collection_metadata = self._get_object_extra(
            harvest_object, "collection_metadata"
        )
        if collection_metadata:
            package_dict["extras"].append(
                dict(key="collection_metadata", value=collection_metadata)
            )
            status = self._get_object_extra(harvest_object, "status")
            if status == "change":
                self.force_import = True
            else:
                self.force_import = False

        return package_dict

    def gather_stage(self, harvest_job):
        log.debug("WafHarvester gather_stage for job: %r", harvest_job)

        self.harvest_job = harvest_job

        # Get source URL
        source_url = harvest_job.source.url

        self._set_source_config(harvest_job.source.config)

        collection_metadata_url = self.source_config.get("collection_metadata_url")

        if not collection_metadata_url:
            self._save_gather_error("collection url does not exist", harvest_job)
            return None

        try:
            # Ignore F841 unused variable because if commented, code does nothing
            response = requests.get(source_url, timeout=60)  # NOQA
            content = response.content  # NOQA
        except Exception as e:
            self._save_gather_error(
                "Unable to get content for URL: %s: %r" % (source_url, e), harvest_job
            )
            return None

        guid = hashlib.md5(collection_metadata_url.encode("utf8", "ignore")).hexdigest()

        existing_harvest_object = (
            model.Session.query(
                HarvestObject.guid, HarvestObject.package_id, HOExtra.value
            )
            .join(HOExtra, HarvestObject.extras)
            .filter(HOExtra.key == "collection_metadata")
            .filter(HOExtra.value == "true")
            .filter(True if HarvestObject.current else False)
            .filter(HarvestObject.harvest_source_id == harvest_job.source.id)
            .first()
        )

        if existing_harvest_object:
            status = "change"
            guid = existing_harvest_object.guid
            package_id = existing_harvest_object.package_id
        else:
            status, package_id = "new", None

        obj = HarvestObject(
            job=harvest_job,
            extras=[
                HOExtra(key="collection_metadata", value="true"),
                HOExtra(key="waf_location", value=collection_metadata_url),
                HOExtra(key="status", value=status),
            ],
            guid=guid,
            status=status,
            package_id=package_id,
        )
        queue.fetch_and_import_stages(self, obj)
        if obj.state == "ERROR":
            self._save_gather_error(
                "Collection object failed to harvest, not harvesting", harvest_job
            )
            return None

        return GeoDataGovWAFHarvester.gather_stage(
            self, harvest_job, collection_package_id=obj.package_id
        )
