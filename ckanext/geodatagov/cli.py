import base64
import cgitb
import datetime
import hashlib
import json
import logging
import sys
import tempfile
import warnings
from typing import Optional

import boto3
import ckan.logic as logic
import ckan.model as model
import click
from botocore.config import Config
from ckan.common import config
from ckan.lib.search import rebuild
from ckan.lib.search.common import make_connection
from ckan.lib.search.index import NoopSearchIndex, PackageSearchIndex
from sqlalchemy import func, and_

from ckanext.geodatagov.search import GeoPackageSearchQuery
from ckanext.harvest.model import HarvestJob, HarvestObject

# default constants
#   for sitemap_to_s3
UPLOAD_TO_S3 = True
PAGE_SIZE = 10000
MAX_PER_PAGE = 50000
#   for db_solr_sync
_INDICES = {"package": PackageSearchIndex}
#   for logging
DEFAULT_LOG = "ckanext.geodatagov"
log = logging.getLogger(DEFAULT_LOG)


@click.group()
def geodatagov():
    pass


@click.group()
def datagovs3():
    pass


class Sitemap:

    def __init__(self, file_num: str, start: int, page_size: int) -> None:
        self.file_num = file_num
        self.start = start
        self.page_size = page_size
        self.xml = ""

    def write_xml(self, some_xml, add_newline=True) -> None:
        if add_newline:
            self.xml += f"{some_xml}\n"
        else:
            self.xml += some_xml

    def to_json(self) -> str:
        return json.dumps(self, default=lambda o: o.__dict__)

    def write_sitemap_header(self, index=False) -> None:
        self.write_xml('<?xml version="1.0" encoding="UTF-8"?>')
        if index:
            self.write_xml('<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
        else:
            self.write_xml('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')


class SitemapData(Sitemap):

    def __init__(self, file_num: str, start: int, page_size: int) -> None:
        super().__init__(file_num, start, page_size)
        self.filename_s3 = f"sitemap/sitemap-{file_num}.xml"

    def write_pkgs(self, package_query: GeoPackageSearchQuery) -> None:

        pkgs = package_query.get_paginated_entity_name_modtime(
            max_results=self.page_size, start=self.start
        )
        for pkg in pkgs:
            self.write_xml("<url>")
            self.write_xml(
                f"<loc>{config.get('ckan.site_url')}/dataset/{pkg.get('name')}</loc>"
            )
            self.write_xml(
                f"<lastmod>{pkg.get('metadata_modified').strftime('%Y-%m-%d')}</lastmod>"
            )
            self.write_xml("</url>")

    def write_sitemap_footer(self) -> None:
        self.write_xml("</urlset>")


class SitemapIndex(Sitemap):

    def __init__(self, file_num: str, start: int, page_size: int) -> None:
        super().__init__(file_num, start, page_size)
        self.filename_s3 = "sitemap.xml"

    def write_table_of_contents(self, number_of_sitemaps):
        current_time = datetime.datetime.now().strftime("%Y-%m-%d")

        log.info("Creating sitemap index...")

        for file_num in range(number_of_sitemaps):
            # add sitemaps to sitemap index file
            self.write_xml("<sitemap>")
            loc = f"{config.get('ckan.site_url')}/sitemap/sitemap-{file_num}.xml"
            self.write_xml(f"<loc>{loc}</loc>")
            self.write_xml(f"<lastmod>{current_time}</lastmod>")
            self.write_xml("</sitemap>")
        self.write_xml("</sitemapindex>")


def get_s3() -> None:
    """Sets global CKAN_SITE_URL, S3 object, checks access to bucket BUCKET_NAME, creates if needed.

    Refer to values in .env file in ckanext_geodatagov and
    .profile file in catalog repo for s3 config.
    """

    global CKAN_SITE_URL
    CKAN_SITE_URL = config.get("ckan.site_url")

    log.info("Setting S3 globals...")
    global S3
    global BUCKET_NAME
    # global S3_STORAGE_PATH
    global S3_ENDPOINT_URL

    BUCKET_NAME = config.get("ckanext.s3sitemap.aws_bucket_name")
    # S3_STORAGE_PATH = config.get("ckanext.s3sitemap.aws_storage_path")
    S3_ENDPOINT_URL = config.get("ckanext.s3sitemap.endpoint_url")

    # Grab all of the necessary config and create S3 client
    S3 = boto3.client(
        "s3",
        aws_access_key_id=config.get("ckanext.s3sitemap.aws_access_key_id"),
        aws_secret_access_key=config.get("ckanext.s3sitemap.aws_secret_access_key"),
        region_name=config.get("ckanext.s3sitemap.region_name"),
        endpoint_url=S3_ENDPOINT_URL,
        config=Config(s3={"addressing_style": "auto"}),
    )

    # Only for local testing: create bucket if needed
    try:
        S3.create_bucket(Bucket=BUCKET_NAME)
    except Exception:
        pass


def get_content_type(filename: str) -> str:
    """Attempts to guess MIME type by filename extension

    Returns content-type str
    """

    if filename[-3:].lower() == "xml":
        content_type = "application/xml"
    elif filename[-4:].lower() == "html":
        content_type = "application/html"
    elif filename[-3:].lower() == "txt":
        content_type = "text/plain"
    else:
        raise Exception(f"Unknown Content-Type for upload file {filename}")

    return content_type


def upload_to_key(upload_str: str, filename_on_s3: str) -> None:
    """Upload upload_str to s3 bucket"""

    # Create temp file to upload
    temp_file = tempfile.NamedTemporaryFile()
    with open(temp_file.name, "w") as f:
        content = upload_str
        f.write(content)

    # Hash file and upload to S3
    md5 = base64.b64encode(hashsum(temp_file.name)).decode("utf-8")
    content_type = get_content_type(filename_on_s3)
    with open(temp_file.name, "rb") as f:
        resp = S3.put_object(
            Body=f,
            Bucket=BUCKET_NAME,
            Key=filename_on_s3,
            ContentMD5=md5,
            ContentType=content_type,
        )
        resp_metadata = resp.get("ResponseMetadata")
        if resp_metadata.get("HTTPStatusCode") == 200:
            log.info(
                f"File {filename_on_s3} upload complete to: \
                {S3_ENDPOINT_URL}/{BUCKET_NAME}/{filename_on_s3}"
            )
        else:
            log.error(f"File {filename_on_s3} upload failed. Error: {resp_metadata}")

    del temp_file


def upload_sitemap_file(sitemap: list) -> None:
    """Handles uploading sitemap files to s3"""

    log.info("Uploading sitemap file...")
    upload_to_key(sitemap.xml, sitemap.filename_s3)
    log.info(
        f"Sitemap file {sitemap.filename_s3} upload complete to: \
        {S3_ENDPOINT_URL}/{BUCKET_NAME}/{sitemap.filename_s3}"
    )


@geodatagov.command()
@click.option("--upload_to_s3", default=UPLOAD_TO_S3, type=click.BOOL)
@click.option("--page_size", default=PAGE_SIZE, type=click.INT)
@click.option("--max_per_page", default=MAX_PER_PAGE, type=click.INT)
def sitemap_to_s3(upload_to_s3: bool, page_size: int, max_per_page: int):
    """Generates sitemap and uploads to s3"""
    log.info("Sitemap is being generated...")

    package_query = GeoPackageSearchQuery()
    count = package_query.get_count()
    log.info(f"{count} records found")
    if not count:
        log.info("Nothing to process, exiting.")
        return

    start = 0

    num_of_pages = (count // page_size) + 1

    # Create + Upload Sitemap Index File
    sitemap_index = SitemapIndex("index", 0, 0)
    sitemap_index.write_sitemap_header(index=True)
    sitemap_index.write_table_of_contents(num_of_pages)

    if upload_to_s3:
        # set global S3 object and vars
        get_s3()
        upload_to_key(sitemap_index.xml, sitemap_index.filename_s3)
        log.info(
            f"Sitemap index upload complete to: \
            {S3_ENDPOINT_URL}/{BUCKET_NAME}/{sitemap_index.filename_s3}"
        )

    for file_num in range(1, num_of_pages + 1):
        sitemap = SitemapData(str(file_num), start, page_size)
        sitemap.write_sitemap_header()
        sitemap.write_pkgs(package_query)
        sitemap.write_sitemap_footer()

        log.info(
            f"{start+1} to {min(start + page_size, count)} of {count} records done."
        )

        # large block removed here, I'm not convinced that it was ever hit
        # if issues arise around max_per_page, re-add here
        # see https://github.com/GSA/ckanext-geodatagov/blob/
        # 597610699434bde9415a48ed0b1085bfa0e9720f/ckanext/geodatagov/cli.py#L183

        log.info(f"done with {sitemap.filename_s3}.")

        start += page_size

        if upload_to_s3:
            log.info(f"Uploading {sitemap.filename_s3}...")
            upload_sitemap_file(sitemap)
        else:
            log.info(f"Skip upload and return local copy of sitemap {file_num}.")
            print(json.dumps(sitemap.to_json(), indent=4))

        del sitemap


def _normalize_type(_type):
    if isinstance(_type, model.domain_object.DomainObject):
        _type = _type.__class__
    if isinstance(_type, type):
        _type = _type.__name__
    return _type.strip().lower()


def index_for(_type):
    """Get a SearchIndex instance sub-class suitable for
    the specified type."""
    try:
        _type_n = _normalize_type(_type)
        return _INDICES[_type_n]()
    except KeyError:
        log.warn("Unknown search type: %s" % _type)
        return NoopSearchIndex()


def get_all_entity_ids_date_hoid():
    """
    Return a list of the IDs and metadata_modified of all indexed packages.

    harvest_object_id is not readily available from solr result. It has to
    be extracted from a json object validated_data_dict. Due to the large size
    of validated_data_dict, Solr result has to be processed in batches at 10000
    pagination to avoid out-of-memory.
    """
    query = "*:*"
    fq = '+site_id:"%s" ' % config.get("ckan.site_id")
    fq += "+state:active "
    fq += "+type:dataset "

    ret_all = []

    start = 0
    page_size = 10000
    conn = make_connection()

    log.info(f"Now loading SOLR packages using page size {page_size}...")

    while True:
        log.info(f"loading packages starting from {start}")
        data = conn.search(query, fq=fq, start=start, rows=page_size, fl="id, metadata_modified, validated_data_dict")

        if not data:
            break

        for r in data.docs:
            harvest_object_id = None
            data_dict = json.loads(r.get("validated_data_dict"))
            for extra in data_dict.get("extras", []):
                if extra["key"] == "harvest_object_id":
                    harvest_object_id = extra["value"]
                    break

            ret_all.append((r.get("id"), r.get("metadata_modified"), harvest_object_id))

        start += page_size

    return ret_all


def delete_packages(package_ids):
    """
    Delete solr indexes for a list of packages and defer the commit to the end.
    """
    TYPE_FIELD = "entity_type"
    PACKAGE_TYPE = "package"
    commit = False
    conn = make_connection()
    site_id = config.get("ckan.site_id")
    for id in package_ids:
        query = f'+{TYPE_FIELD}:{PACKAGE_TYPE} AND +(id:"{id}" OR name:"{id}") AND +site_id:"{site_id}"'
        try:
            log.info(f"deleting index with {id}")
            conn.delete(q=query, commit=commit)
        except Exception as e:
            log.error(f"Error while delete index {id}: {repr(e)}")
    conn.commit(waitSearcher=False)


@geodatagov.command()
@click.option("--dryrun", is_flag=True, help="inspect what will be updated")
@click.option(
    "--cleanup_solr", is_flag=True, help="Only remove orphaned entries in Solr"
)
@click.option(
    "--update_solr",
    is_flag=True,
    help=(
        "(Update solr entries with new data from DB) OR (Add DB data to Solr that is missing)"
    ),
)
def db_solr_sync(dryrun, cleanup_solr, update_solr):
    """db solr sync"""
    if dryrun:
        log.info("Starting dryrun to update index.")

    package_index = index_for(model.Package)

    # get active packages from DB
    active_package = [
        (r[0], r[1].replace(microsecond=0), r[2])
        for r in model.Session.query(
            model.Package.id,
            model.Package.metadata_modified,
            HarvestObject.id
        )
        .join(
            HarvestObject,
            and_(
                HarvestObject.package_id == model.Package.id,
                HarvestObject.current == True  # noqa: E712
            ),
            isouter=True
        )
        .filter(
            model.Package.type == "dataset",
            model.Package.state == "active"
        )
        .order_by(HarvestObject.import_finished)
        .all()
    ]

    # in case an id comes with multiple harvest_object_id,
    # this removes anything but the latest
    # after which we have a dict formatted as
    # {
    #   'some_id': (some_mod_date, some_ho_id)
    #   ...
    # }
    cleaning = {}
    for id, metadata_modified, harvest_object_id in active_package:
        cleaning[id] = (metadata_modified, harvest_object_id)

    # now it is cleaned, change dict back to a set.
    # after which we are back to a set formatted as
    # {(some_id, some_mod_date, some_ho_id), ...}
    active_package = {(k,) + cleaning[k] for k in cleaning}
    # pick out those packages without harvest_object_id
    active_package_id_wo_ho = {k for k in cleaning if cleaning[k][1] is None}

    log.info(f"total {len(active_package)} DB active_package")

    # get indexed packages from solr
    indexed_package = set(get_all_entity_ids_date_hoid())
    log.info(f"total {len(indexed_package)} solr indexed_package")

    solr_package = indexed_package - active_package
    db_package = active_package - indexed_package

    work_list = {}
    for id, *_ in solr_package:
        work_list[id] = "solr"
    for id, *_ in db_package:
        if id in work_list:
            work_list[id] = "solr-db"
        else:
            work_list[id] = "db"

    both = cleanup_solr == update_solr
    set_cleanup = {i if work_list[i] == "solr" else None for i in work_list} - {None}
    set_update = work_list.keys() - set_cleanup - active_package_id_wo_ho
    log.info(f"{len(set_cleanup)} packages need to be removed from Solr")
    log.info(f"{len(set_update)} packages need to be updated/added to Solr")
    log.info(f"{len(active_package_id_wo_ho)} packages without harvest_object need to be mannually deleted")

    if not dryrun and set_cleanup and (cleanup_solr or both):
        log.info("Deleting indexes")
        delete_packages(set_cleanup)
        package_index.commit()
        log.info("Finished cleaning solr entries.")

    if not dryrun and set_update and (update_solr or both):
        log.info("Rebuilding indexes")
        try:
            rebuild(package_ids=set_update, defer_commit=True)
        except Exception as e:
            log.error("Error while rebuild index %s: %s" % (id, repr(e)))
        package_index.commit()
        log.info("Finished updating solr entries.")
        log.info("Here is the first a few dataset ids that are rebuilt:")
        count = 0
        max = 10
        for id in set_update:
            count = count + 1
            if count > max:
                break
            log.info(f"{count}: {id}")

    # dryrun or not, we are printing out the active_package_id_wo_ho
    if active_package_id_wo_ho:
        log.info("Packages without harvest_object.")
        print(*active_package_id_wo_ho, sep='\n')


@geodatagov.command()
def check_stuck_jobs():
    """check stuck harvest jobs"""

    log.info("Starting check stuck harvest jobs.")

    # get stuck jobs which run more than 1 day
    stuck_jobs = (
        model.Session.query(
            model.Package.id,
            model.Package.title.label("source_name"),
            model.Group.title.label("org_name"),
            HarvestJob.created,
            HarvestJob.gather_started.label("gather_started"),
            HarvestJob.gather_finished.label("gather_finished"),
            func.now().label('current'),
            (func.now() - HarvestJob.created).label('time_diff'))
        .join(model.Group, model.Package.owner_org == model.Group.id)
        .join(HarvestJob, HarvestJob.source_id == model.Package.id)
        .filter(func.extract("day", func.now() - HarvestJob.created) >= 1,
                HarvestJob.status == "Running")
        .all()
    )

    log.info(f"total {len(stuck_jobs)} stuck harvest jobs")

    for job in stuck_jobs:
        message = "source_id: " + job.id + \
                  " | created_time: " + str(job.created) + \
                  " | current_time: " + str(job.current) + \
                  " | gather_started: " + str(job.gather_started) + \
                  " | gather_finished: " + str(job.gather_finished) + \
                  " | running_length: " + str(job.time_diff) + \
                  " | source_title: " + job.source_name + \
                  " | organization: " + job.org_name

        log.info(message)

    sys.exit(len(stuck_jobs))


@geodatagov.command()
def test_command():
    """Basic cli command with normal result"""
    print("This is a good test!")
    return True


@geodatagov.command()
@click.argument("harvest_source_id", required=False)
def harvest_object_relink(harvest_source_id: Optional[str]):
    '''
    Fix erroneous harvest objects for a harvest source or all harvest sources.
    Some packages are left with no current harvest object after a harvesting job. This function
    will fix the problem by making the latest COMPLETED harvest object current.
    '''
    log.info("Relinking harvest objects for harvest source {}.".format(
        harvest_source_id if harvest_source_id else 'all'
    ))

    # find packages that has no current harvest object
    sql = '''
        WITH package_with_current AS (
            SELECT package_id FROM harvest_object WHERE current
        )
        SELECT distinct(p.id) FROM package p
        JOIN harvest_object h ON p.id = h.package_id
        LEFT JOIN package_with_current c ON p.id = c.package_id
        WHERE p.state='active' AND p.type='dataset' AND c.package_id IS NULL
    '''
    if harvest_source_id:
        sql += '''
        AND
            h.harvest_source_id = :harvest_source_id
        '''
        results = model.Session.execute(sql,
                                        {'harvest_source_id': harvest_source_id})
    else:
        results = model.Session.execute(sql)

    pkgs_problematic = {row['id'] for row in results}
    total = len(pkgs_problematic)
    log.info(f'{total} packages to be fixed.')

    # set last complete harvest object to be current
    sql = '''
        UPDATE harvest_object
        SET current = 't'
        WHERE
            package_id = :id
        AND
            state = 'COMPLETE'
        AND
            import_finished = (
                SELECT MAX(import_finished)
                FROM harvest_object
                WHERE
                    state = 'COMPLETE'
                AND
                    report_status <> 'deleted'
                AND
                    package_id = :id
            )
        RETURNING 1
    '''
    count = 0
    pkgs_to_index = set()
    for id in pkgs_problematic:
        result = model.Session.execute(sql, {'id': id}).fetchall()
        model.Session.commit()
        count = count + 1
        if result:
            log.info(f'{count}/{total}: {id} fixed in DB. Addded to solr index queue.')
            pkgs_to_index.add(id)
        else:
            log.info(f'{count}/{total}: {id} has no valid harvest object. Need to inspect manually.')

    if pkgs_to_index:
        log.info("Rebuilding indexes")
        package_index = index_for(model.Package)

        try:
            rebuild(package_ids=pkgs_to_index, defer_commit=True)
        except Exception as e:
            log.error("Error while rebuild index %s: %s" % (id, repr(e)))
        package_index.commit()
        log.info("Finished updating solr entries.")


@geodatagov.command()
@click.argument("start_date", required=False)
def tracking_update(start_date: Optional[str]):
    """ckan tracking update with customized options and output"""
    engine = model.meta.engine
    assert engine
    update_all(engine, start_date)


def update_all(engine, start_date=None):
    from ckan.cli.tracking import update_tracking

    if start_date:
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    else:
        # No date given. See when we last have data for and get data
        # from 2 days before then in case new data is available.
        # If no date here then use 2011-01-01 as the start date
        sql = """SELECT tracking_date from tracking_summary
                    ORDER BY tracking_date DESC LIMIT 1;"""
        result = engine.execute(sql).fetchall()
        if result:
            start_date = result[0]["tracking_date"]
            start_date += datetime.timedelta(-2)
            # convert date to datetime
            combine = datetime.datetime.combine
            start_date = combine(start_date, datetime.time(0))
        else:
            start_date = datetime.datetime(2011, 1, 1)
    start_date_solrsync = start_date
    end_date = datetime.datetime.now()
    while start_date < end_date:
        stop_date = start_date + datetime.timedelta(1)
        update_tracking(engine, start_date)
        log.info("tracking updated for {}".format(start_date))
        start_date = stop_date
    update_tracking_solr(engine, start_date_solrsync)


def update_tracking_solr(engine, start_date):
    sql = """SELECT distinct(package_id) FROM tracking_summary
            where package_id!='~~not~found~~'
            and tracking_date >= %s;"""
    results = engine.execute(sql, start_date)
    package_ids = set()
    for row in results:
        package_ids.add(row["package_id"])
    total = len(package_ids)
    log.info(
        "{} package index{} to be rebuilt starting from {}".format(
            total, "" if total < 2 else "es", start_date
        )
    )

    context = {
        "model": model,
        "ignore_auth": True,
        "validate": False,
        "use_cache": False,
    }
    package_index = index_for(model.Package)
    quiet = False
    force = True
    defer_commit = True
    for counter, pkg_id in enumerate(package_ids):
        if not quiet:
            log.info("Indexing dataset {}/{}: {}".format(counter + 1, total, pkg_id))
        try:
            package_index.update_dict(
                logic.get_action("package_show")(context, {"id": pkg_id}), defer_commit
            )
        except Exception as e:
            log.error("Error while indexing dataset %s: %s" % (pkg_id, repr(e)))
            if force:
                log.error(text_traceback())
                continue
            else:
                raise

    package_index.commit()


def text_traceback():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = "the original traceback:".join(
            cgitb.text(sys.exc_info()).split("the original traceback:")[1:]
        ).strip()
    return res


@datagovs3.command()
@click.argument("file_type", required=True)
def s3_test(file_type: str):
    """Tests cli command talking to s3"""

    content = f"Yay! I was created at {str(datetime.datetime.now())}"

    if file_type == "html":
        upload_str = "<!DOCTYPE html>"
        upload_str += "<html>"
        upload_str += "<head><title>Test Upload</title></head>"
        upload_str += f"<body><p>{content}</b></body>"
        upload_str += "</html>"
    elif file_type == "txt":
        upload_str = content
    else:
        raise Exception(f"Unsupported file type: {file_type}")

    # Set S3 globals
    get_s3()

    # Upload test file
    print(upload_str)  # output to be checked by test_s3test
    upload_to_key(upload_str, f"test.{file_type}")


def hashsum(path: str, hash_type=hashlib.md5):
    """Accepts file path str, returns hash byes-like object"""
    # Courtesy of https://stackoverflow.com/a/15020115
    hashinst = hash_type()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(hashinst.block_size * 128), b""):
            hashinst.update(chunk)
    # TODO hex?
    return hashinst.digest()


# IClick
def get_commands() -> list:
    """List of commands to pass to ckan"""

    return [geodatagov]


# IClick
def get_commands2() -> list:
    """List of commands to pass to ckan"""

    return [datagovs3]
