import base64
import datetime
import hashlib
import sys
import json
import logging
import warnings
import cgitb
import tempfile
import boto3
import click
from botocore.config import Config
from typing import Optional

import ckan.model as model
import ckan.logic as logic
from ckan.common import config
from ckan.lib.search import rebuild
from ckan.lib.search.common import make_connection
from ckan.lib.search.index import NoopSearchIndex, PackageSearchIndex

from ckanext.geodatagov.search import GeoPackageSearchQuery

# default constants
#   for sitemap_to_s3
UPLOAD_TO_S3 = True
PAGE_SIZE = 1000
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
    """Sitemap object

    Accepts filename, start, page_size
    """

    def __init__(self, filename: str, start: int, page_size: int) -> None:
        self.filename = filename
        self.filename_s3 = f"sitemap-{filename}.xml"
        self.start = start
        self.page_size = page_size
        self.xml = ""

    def write_sitemap_header(self) -> None:
        self.xml += '<?xml version="1.0" encoding="UTF-8"?>\n'
        self.xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

    def write_pkgs(self, package_query: GeoPackageSearchQuery) -> None:

        pkgs = package_query.get_paginated_entity_name_modtime(
            max_results=self.page_size, start=self.start
        )
        for pkg in pkgs:
            self.xml += "    <url>\n"
            self.xml += f"        <loc>{config.get('ckan.site_url')}/dataset/{pkg.get('name')}</loc>\n"
            self.xml += f"        <lastmod>{pkg.get('metadata_modified').strftime('%Y-%m-%d')}</lastmod>\n"
            self.xml += "    </url>\n"

    def write_sitemap_footer(self) -> None:
        self.xml += "</urlset>\n"

    def to_json(self) -> str:
        return json.dumps(self, default=lambda o: o.__dict__)

    def write_xml(self, some_xml, add_newline=True) -> None:
        if add_newline:
            self.xml += f"{some_xml}\n"
        else:
            self.xml += some_xml


def get_s3() -> None:
    """Sets global S3 object, checks access to bucket BUCKET_NAME, creates if needed.

    Refer to values in .env file in ckanext_geodatagov and
    .profile file in catalog repo for s3 config.
    """

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


def upload_to_key(upload_str: str, filename_on_s3: str) -> None:
    """Upload upload_str to s3 bucket"""

    # Create temp file to upload
    temp_file = tempfile.NamedTemporaryFile()
    with open(temp_file.name, "w") as f:
        content = upload_str
        f.write(content)

    # Hash file and upload to S3
    md5 = base64.b64encode(hashsum(temp_file.name)).decode("utf-8")
    with open(temp_file.name, "rb") as f:
        resp = S3.put_object(
            Body=f, Bucket=BUCKET_NAME, Key=filename_on_s3, ContentMD5=md5
        )
        resp_metadata = resp.get("ResponseMetadata")
        if resp_metadata.get("HTTPStatusCode") == 200:
            log.info(
                f"File {filename_on_s3} upload complete to: \
                {S3_ENDPOINT_URL}/{BUCKET_NAME}/{filename_on_s3}"
            )
        else:
            log.error(f"File {filename_on_s3} upload failed. Error: {resp_metadata}")


def upload_sitemap_index(sitemaps: list) -> None:
    """Creates and uploads sitemap index xml file"""

    current_time = datetime.datetime.now().strftime("%Y-%m-%d")
    sitemap_index = Sitemap("index", 0, 0)
    sitemap_index.filename_s3 = "sitemap.xml"

    log.info("Creating sitemap index...")
    # write sitemap index
    sitemap_index.write_xml('<?xml version="1.0" encoding="UTF-8"?>')
    sitemap_index.write_xml(
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    )

    for sitemap in sitemaps:
        # add sitemaps to sitemap index file
        sitemap_index.write_xml("<sitemap>")
        loc = f"{S3_ENDPOINT_URL}/{BUCKET_NAME}/{sitemap.filename_s3}"
        sitemap_index.write_xml(f"<loc>{loc}</loc>")
        sitemap_index.write_xml(f"<lastmod>{current_time}</lastmod>")
        sitemap_index.write_xml("</sitemap>")
    sitemap_index.write_xml("</sitemapindex>")

    upload_to_key(sitemap_index.xml, f"{sitemap_index.filename_s3}")
    log.info(
        f"Sitemap index upload complete to: \
        {S3_ENDPOINT_URL}/{BUCKET_NAME}/{sitemap_index.filename_s3}"
    )


def upload_sitemap_files(sitemaps: list) -> None:
    """Handles uploading sitemap files to s3"""

    log.info(f"Uploading {len(sitemaps)} sitemap files...")
    for sitemap in sitemaps:
        filename_on_s3 = f"{sitemap.filename_s3}"
        upload_to_key(sitemap.xml, filename_on_s3)
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
    filename = 1
    sitemaps = []

    paginations = (count // page_size) + 1
    for _ in range(paginations):
        sitemap = Sitemap(str(filename), start, page_size)
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
        sitemaps.append(sitemap)

        start += page_size
        filename += 1

    if upload_to_s3:
        log.info("Starting S3 uploads...")
        # set global S3 object and vars
        get_s3()

        upload_sitemap_index(sitemaps)
        upload_sitemap_files(sitemaps)
    else:
        log.info("Skip upload and finish.")
        dump = [sitemap.to_json() for sitemap in sitemaps]
        print(f"Done locally: Sitemap list\n{json.dumps(dump, indent=4)}")


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


def get_all_entity_ids_and_date(max_results: int = 1000):
    """
    Return a list of the IDs and metadata_modified of all indexed packages.
    """
    query = "*:*"
    fq = '+site_id:"%s" ' % config.get("ckan.site_id")
    fq += "+state:active "

    conn = make_connection()
    data = conn.search(query, fq=fq, rows=max_results, fl="id, metadata_modified")

    return [(r.get("id"), r.get("metadata_modified")) for r in data.docs]


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
        (r[0], r[1].replace(microsecond=0))
        for r in model.Session.query(model.Package.id, model.Package.metadata_modified)
        .filter(model.Package.state != "deleted")
        .all()
    ]
    log.info(f"total {len(active_package)} DB active_package")

    # get indexed packages from solr
    indexed_package = set(get_all_entity_ids_and_date(max_results=2000000))
    log.info(f"total {len(indexed_package)} solr indexed_package")

    solr_package = indexed_package - set(active_package)
    db_package = set(active_package) - indexed_package

    work_list = {}
    for id, _ in solr_package:
        work_list[id] = "solr"
    for id, _ in db_package:
        if id in work_list:
            work_list[id] = "solr-db"
        else:
            work_list[id] = "db"

    both = cleanup_solr == update_solr
    set_cleanup = {i if work_list[i] == "solr" else None for i in work_list} - {None}
    set_update = work_list.keys() - set_cleanup
    log.info(f"{len(set_cleanup)} packages need to be removed from Solr")
    log.info(f"{len(set_update)} packages need to be updated/added to Solr")

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


@geodatagov.command()
def test_command():
    """Basic cli command with normal result"""
    print("This is a good test!")
    return True


@geodatagov.command()
@click.argument(u'start_date', required=False)
def tracking_update(start_date: Optional[str]):
    """ckan tracking update with customized options and output"""
    engine = model.meta.engine
    assert engine
    update_all(engine, start_date)


def update_all(engine, start_date=None):
    from ckan.cli.tracking import update_tracking
    if start_date:
        start_date = datetime.datetime.strptime(start_date, u'%Y-%m-%d')
    else:
        # No date given. See when we last have data for and get data
        # from 2 days before then in case new data is available.
        # If no date here then use 2011-01-01 as the start date
        sql = u'''SELECT tracking_date from tracking_summary
                    ORDER BY tracking_date DESC LIMIT 1;'''
        result = engine.execute(sql).fetchall()
        if result:
            start_date = result[0][u'tracking_date']
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
        log.info(u'tracking updated for {}'.format(start_date))
        start_date = stop_date
    update_tracking_solr(engine, start_date_solrsync)


def update_tracking_solr(engine, start_date):
    sql = u'''SELECT distinct(package_id) FROM tracking_summary
            where package_id!='~~not~found~~'
            and tracking_date >= %s;'''
    results = engine.execute(sql, start_date)
    package_ids = set()
    for row in results:
        package_ids.add(row[u'package_id'])
    total = len(package_ids)
    log.info(u'{} package index{} to be rebuilt starting from {}'.format(
        total, u'' if total < 2 else u'es', start_date)
    )

    context = {'model': model, 'ignore_auth': True, 'validate': False,
               'use_cache': False}
    package_index = index_for(model.Package)
    quiet = False
    force = True
    defer_commit = True
    for counter, pkg_id in enumerate(package_ids):
        if not quiet:
            log.info(u'Indexing dataset {}/{}: {}'.format(
                counter + 1, total, pkg_id)
            )
        try:
            package_index.update_dict(
                logic.get_action('package_show')(
                    context,
                    {'id': pkg_id}
                ),
                defer_commit
            )
        except Exception as e:
            log.error(u'Error while indexing dataset %s: %s' %
                      (pkg_id, repr(e)))
            if force:
                log.error(text_traceback())
                continue
            else:
                raise

    package_index.commit()


def text_traceback():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = 'the original traceback:'.join(
            cgitb.text(sys.exc_info()).split('the original traceback:')[1:]
        ).strip()
    return res


@datagovs3.command()
def s3_test():
    """Tests cli command talking to s3"""

    # Set S3 globals
    get_s3()

    # Upload test file
    content = f"Yay! I was created at {str(datetime.datetime.now())}"
    print(content)  # output to be checked by test_s3test
    upload_to_key(content, "test.txt")


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
