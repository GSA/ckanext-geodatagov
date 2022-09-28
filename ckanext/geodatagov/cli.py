import base64
import datetime
import hashlib
import json
import logging

import boto3
import click

from botocore.exceptions import ClientError

import ckan.model as model
import ckan.logic as logic
from ckanext.geodatagov.search import GeoPackageSearchQuery

from ckan.lib.search.common import make_connection
from ckan.lib.search.index import PackageSearchIndex, NoopSearchIndex
from ckan.common import config

_INDICES = {
    'package': PackageSearchIndex
}

# default constants
DEFAULT_LOG = "ckanext.geodatagov"
#   for sitemap_to_s3
UPLOAD_TO_S3 = True
PAGE_SIZE = 1000
MAX_PER_PAGE = 50000
DEFAULT_DRYRUN = False
DEFAULT_CLEANUP_SOLR = False
DEFAULT_UPDATE_SOLR = False

log = logging.getLogger(DEFAULT_LOG)


@click.group()
def geodatagov():
    pass


class Sitemap:
    """Sitemap object

    Accepts filename_number, start, page_size
    """

    def __init__(self, filename_number: int, start: int, page_size: int) -> None:
        self.filename_number = filename_number
        self.filename_s3 = f"sitemap-{filename_number}.xml"
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


def generate_md5_for_s3(filename: str) -> tuple:
    # hashlib.md5 was set as sha1 in plugin.py
    hash_md5 = hashlib.md5_orig()
    with open(filename, "rb") as f:
        # read chunks of 4096 bytes sequentially to be mem efficient
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    md5_hexstr = hash_md5.hexdigest()
    md5_bytes = base64.b64encode(hash_md5.digest())
    return (md5_hexstr, md5_bytes)


def get_s3(bucket_name: str):
    """Return s3 object, checks access to bucket_name parameter."""

    if not config.get("ckanext.s3sitemap.aws_use_ami_role"):
        aws_access_key_id = config.get("ckanext.s3sitemap.aws_access_key_id")
        aws_secret_access_key = config.get("ckanext.s3sitemap.aws_secret_access_key")
    else:
        aws_access_key_id, aws_secret_access_key = (None, None)

    localstack_endpoint = config.get("ckanext.s3sitemap.localstack_endpoint")
    if localstack_endpoint:
        # make locastack connection
        s3 = boto3.resource(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            endpoint_url=localstack_endpoint,
        )
    else:
        # make s3 connection
        s3 = boto3.resource(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )

    # make sure bucket exists and that we can access
    try:
        bucket = s3.Bucket(bucket_name)
        # this feels funky, but from official docs
        # https://docs.aws.amazon.com/AmazonS3/latest/userguide/example_s3_HeadBucket_section.html
        bucket.meta.client.head_bucket(Bucket=bucket_name)

        return s3

    except ClientError as err:
        log.error(
            f"s3 Bucket {bucket_name} doesn't exist or you don't have access to it"
        )
        log.debug(f"s3 bucket ClientError: {err}")
        raise err


def upload_to_key(s3, bucket_name, upload_str: str, filename_on_s3: str) -> None:
    try:
        upload_object = s3.Object(bucket_name, filename_on_s3)
        upload_object.put(Body=upload_str)
    except Exception as e:
        raise e


def upload(sitemaps: list) -> None:
    """Handle uploading sitemap files to s3"""
    bucket_name = config.get("ckanext.s3sitemap.aws_bucket_name")
    bucket_path = config.get("ckanext.s3sitemap.aws_storage_path", "")
    s3_url = config.get("ckanext.s3sitemap.aws_s3_url")
    storage_path = config.get("ckanext.s3sitemap.aws_storage_path")
    s3 = get_s3(bucket_name)

    current_time = datetime.datetime.now().strftime("%Y-%m-%d")
    sitemap_index = ""

    # write header
    sitemap_index += '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap_index += (
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    )

    for sitemap in sitemaps:
        filename_on_s3 = bucket_path + sitemap.filename_s3
        upload_to_key(s3, bucket_name, sitemap.xml, filename_on_s3)
        log.info(f"Sitemap file {sitemap.filename_s3} upload complete.")

        # add to sitemap index file
        sitemap_index += "    <sitemap>\n"
        loc = s3_url + storage_path + sitemap.filename_s3
        sitemap_index += f"        <loc>{loc}</loc>\n"
        sitemap_index += f"        <lastmod>{current_time}</lastmod>\n"
        sitemap_index += "    </sitemap>\n"

    sitemap_index += "</sitemapindex>\n"

    upload_to_key(s3, bucket_name, sitemap_index, bucket_path + "sitemap.xml")
    log.info("Sitemap index upload complete.")


@geodatagov.command()
@click.option("--upload_to_s3", default=UPLOAD_TO_S3, type=click.BOOL)
@click.option("--page_size", default=PAGE_SIZE, type=click.INT)
@click.option("--max_per_page", default=MAX_PER_PAGE, type=click.INT)
def sitemap_to_s3(upload_to_s3, page_size: int, max_per_page: int):
    """Generates sitemap and uploads to s3"""
    log.info("Sitemap is being generated...")

    package_query = GeoPackageSearchQuery()
    count = package_query.get_count()
    log.info(f"{count} records found")
    if not count:
        log.info("Nothing to process, exiting.")
        return

    start = 0
    filename_number = 1
    sitemaps = []

    paginations = (count // page_size) + 1
    for _ in range(paginations):
        sitemap = Sitemap(filename_number, start, page_size)
        sitemap.write_sitemap_header()
        sitemap.write_pkgs(package_query)
        sitemap.write_sitemap_footer()

        log.info(
            f"{start+1} to {min(start + page_size, count)} of {count} records done."
        )

        start += page_size

        # large block removed here, I'm not convinced that it was ever hit
        # if issues arise around max_per_page, re-add here
        # see https://github.com/GSA/ckanext-geodatagov/blob/
        # 597610699434bde9415a48ed0b1085bfa0e9720f/ckanext/geodatagov/cli.py#L183

        log.info(f"done with {sitemap.filename_s3}.")
        sitemaps.append(sitemap)

    if upload_to_s3:
        upload(sitemaps)
    else:
        log.info("Skip upload and finish.")
        # TODO does the json.dumps(sitemaps) work?
        dump = [sitemap.to_json() for sitemap in sitemaps]
        print(f"Done locally: Sitemap list\n{json.dumps(dump, indent=4)}")


def _normalize_type(_type):
    if isinstance(_type, model.domain_object.DomainObject):
        _type = _type.__class__
    if isinstance(_type, type):
        _type = _type.__name__
    return _type.strip().lower()


def index_for(_type):
    """ Get a SearchIndex instance sub-class suitable for
        the specified type. """
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
    fq = "+site_id:\"%s\" " % config.get('ckan.site_id')
    fq += "+state:active "

    conn = make_connection()
    data = conn.search(query, fq=fq, rows=max_results, fl='id, metadata_modified')

    return [(r.get('id'), r.get('metadata_modified')) for r in data.docs]


@geodatagov.command()
@click.option("--dryrun", default=DEFAULT_DRYRUN, type=click.BOOL, help='inspect what will be updated')
@click.option("--cleanup_solr", default=DEFAULT_CLEANUP_SOLR, type=click.BOOL, help='Only remove orphaned entries in Solr')
@click.option("--update_solr", default=DEFAULT_UPDATE_SOLR, type=click.BOOL, help=(
    '(Update solr entries with new data from DB) OR (Add DB data to Solr that is missing)'))
def db_solr_sync(dryrun, cleanup_solr, update_solr):
    ''' db solr sync (option: --dryrun=True) '''
    if dryrun:
        log.info('Starting dryrun to update index.')

    package_index = index_for(model.Package)
    context = {'model': model, 'ignore_auth': True, 'validate': False, 'use_cache': False}

    # get active packages from DB
    active_package = [(r[0], r[1].replace(microsecond=0)) for r in model.Session.query(model.Package.id,
                      model.Package.metadata_modified).filter(model.Package.state != 'deleted').all()]

    # get indexed packages from solr
    indexed_package = set(get_all_entity_ids_and_date(max_results=2000000))
    log.info(f"total {len(indexed_package)} solr indexed_package and {len(active_package)} DB active_package")

    solr_package = indexed_package - set(active_package)
    db_package = set(active_package) - indexed_package

    work_list = {}
    for id, date in (solr_package):
        work_list[id] = {"solr": date}
    for id, date in (db_package):
        if id in work_list:
            work_list[id].update({"db": date})
        else:
            work_list[id] = {"db": date}

    both = cleanup_solr == update_solr
    count_to_cleanup = sum([1 if work_list[i].keys() == ["solr"] else 0 for i in work_list])
    count_to_update = len(work_list) - count_to_cleanup

    if len(work_list) > 0:
        log.info(f"{count_to_cleanup} packages need to be removed from Solr")
        log.info(f"{count_to_update} packages need to be updated/added to Solr")
        for id in work_list:
            pkg_dict = logic.get_action('package_show')(context, {'id': id})
            if list(work_list[id].keys()) == ["solr"] and (cleanup_solr or both):
                log.info(f"deleting index with {id} \n")
                try:
                    if not dryrun:
                        package_index.remove_dict({'id': id})
                except Exception as e:
                    log.error(u'Error while delete index %s: %s' % (id, repr(e)))
            else:
                log.info(f"updating index with {id} \n")
                try:
                    if not dryrun:
                        package_index.remove_dict(pkg_dict)
                        package_index.insert_dict(pkg_dict)
                except Exception as e:
                    log.error(u'Error while rebuild index %s: %s' % (id, repr(e)))
    else:
        log.info('Solr is good.')
        return

    model.Session.commit()
    log.info('Finished updating solr entries.')


# IClick
def get_commands() -> list:
    """List of commands to pass to ckan"""

    return [geodatagov]
