import logging
from typing import Collection, Optional

import ckan.logic as logic
import ckan.model as model
from ckan.lib.search import index_for, query_for, text_traceback
from ckan.lib.search.common import config
from ckan.types import Context

log = logging.getLogger(__name__)


def rebuild(
    package_id: Optional[str] = None,
    only_missing: bool = False,
    force: bool = False,
    defer_commit: bool = False,
    package_ids: Optional[Collection[str]] = None,
    quiet: bool = False,
    clear: bool = False,
):
    """
    Rebuilds the search index.

    If a dataset id is provided, only this dataset will be reindexed.
    When reindexing all datasets, if only_missing is True, only the
    datasets not already indexed will be processed. If force equals
    True, if an exception is found, the exception will be logged, but
    the process will carry on.
    """
    log.info("Rebuilding search index...")

    package_index = index_for(model.Package)
    context: Context = {"ignore_auth": True, "validate": False, "use_cache": False}

    if package_id:
        pkg_dict = logic.get_action("package_show")(context, {"id": package_id})
        log.info("Indexing package %r...", pkg_dict["name"])
        package_index.remove_dict(pkg_dict)
        package_index.insert_dict(pkg_dict)
    elif package_ids is not None:
        for package_id in package_ids:
            pkg_dict = logic.get_action("package_show")(context, {"id": package_id})
            log.info("Indexing package %r...", pkg_dict["name"])
            try:
                package_index.update_dict(pkg_dict, True)
            except Exception as e:
                log.error("Error while indexing package %s: %s" % (package_id, repr(e)))
                if force:
                    log.error(text_traceback())
                    continue
                else:
                    raise
    # If no package_id or package_ids is provided, rebuild the index for all packages
    else:
        packages = model.Session.query(model.Package.id)
        if config.get("ckan.search.remove_deleted_packages"):
            packages = packages.filter(model.Package.state != "deleted")

        package_ids = [r[0] for r in packages.all()]

        if only_missing:
            log.info("Indexing only missing packages...")
            package_query = query_for(model.Package)
            indexed_pkg_ids = set(
                package_query.get_all_entity_ids(max_results=len(package_ids))
            )
            # Packages not indexed
            package_ids = set(package_ids) - indexed_pkg_ids

            if len(package_ids) == 0:
                log.info("All datasets are already indexed")
                return
        else:
            log.info("Rebuilding the whole index...")
            # When refreshing, the index is not previously cleared
            if clear:
                package_index.clear()

        total_packages = len(package_ids)
        for counter, pkg_id in enumerate(package_ids):
            if not quiet:
                log.info(
                    "\rIndexing dataset {0}/{1}".format(counter + 1, total_packages)
                )
            try:
                package_index.update_dict(
                    logic.get_action("package_show")(context, {"id": pkg_id}),
                    defer_commit,
                )
            except Exception as e:
                log.error("Error while indexing dataset %s: %s" % (pkg_id, repr(e)))
                if force:
                    log.error(text_traceback())
                    continue
                else:
                    raise

    model.Session.commit()
    log.info("Finished rebuilding search index.")
