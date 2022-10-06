import base64
import datetime
import hashlib
import io
import json
import logging

import boto3
import ckan.model as model
import click
from botocore.config import Config
from botocore.exceptions import ClientError
from ckan.common import config
from ckan.lib.search import rebuild
from ckan.lib.search.common import make_connection
from ckan.lib.search.index import NoopSearchIndex, PackageSearchIndex

from ckanext.geodatagov.search import GeoPackageSearchQuery

_INDICES = {
    'package': PackageSearchIndex
}

# default constants
DEFAULT_LOG = "ckanext.geodatagov"
#   for sitemap_to_s3
UPLOAD_TO_S3 = True
PAGE_SIZE = 1000
MAX_PER_PAGE = 50000

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

    def write_xml(self, some_xml) -> None:
        self.xml += some_xml


def get_bucket(bucket_name: str):
    """Return s3 Bucket object, check access to bucket_name, create if needed.

        Refer to values in .env file in ckanext_geodatagov and
        .profile file in catalog repo for s3 config.
    """

    if not config.get("ckanext.s3sitemap.aws_use_ami_role"):
        aws_access_key_id = config.get("ckanext.s3sitemap.aws_access_key_id")
        aws_secret_access_key = config.get("ckanext.s3sitemap.aws_secret_access_key")
    else:
        aws_access_key_id, aws_secret_access_key = (None, None)

    endpoint_url = config.get("ckanext.s3sitemap.endpoint_url")
    s3 = boto3.client(
        "s3",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        endpoint_url=endpoint_url,
    )

    # make sure bucket exists and that we can access, create if not
    try:
        # this feels funky, but from official docs
        # https://docs.aws.amazon.com/AmazonS3/latest/userguide/example_s3_HeadBucket_section.html
        s3.head_bucket(Bucket=bucket_name)
    except ClientError:
        log.warn(f"s3 Bucket {bucket_name} doesn't exist, creating..")
        try:
            s3.create_bucket(Bucket=bucket_name)
        except Exception as e:
            log.error(f"s3 bucket creation: {e}")
            raise e

    return s3


def upload_to_key(upload_str: str, filename_on_s3: str) -> None:
    """Upload upload_str to s3 bucket"""

    bucket_name = config.get("ckanext.s3sitemap.aws_bucket_name")
    s3 = get_bucket(bucket_name)

    """
    md = hashlib.md5(upload_str.encode("utf-8")).digest()
    md5 = base64.b64encode(md).decode("utf-8")

    s3.put_object(
        Bucket=bucket_name, Key=filename_on_s3, Body=upload_str, ContentMD5=md5
    )
    """

    bytes_obj = io.BytesIO(bytes(upload_str.encode('utf-8')))
    s3.upload_fileobj(bytes_obj, bucket_name, filename_on_s3)


def upload(sitemaps: list) -> None:
    """Handle uploading sitemap files to s3"""
    bucket_path = config.get("ckanext.s3sitemap.aws_storage_path", "")
    s3_url = config.get("ckanext.s3sitemap.aws_s3_url")
    storage_path = config.get("ckanext.s3sitemap.aws_storage_path")

    current_time = datetime.datetime.now().strftime("%Y-%m-%d")
    sitemap_index = Sitemap('index', 0, 0)

    # write header
    sitemap_index.write_xml('<?xml version="1.0" encoding="UTF-8"?>\n')
    sitemap_index.write_xml('<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')

    for sitemap in sitemaps:
        # add to sitemap index file
        sitemap_index.write_xml("<sitemap>\n")
        loc = s3_url + storage_path + sitemap.filename_s3
        sitemap_index.write_xml(f"        <loc>{loc}</loc>\n")
        sitemap_index.write_xml(f"        <lastmod>{current_time}</lastmod>\n")
        sitemap_index.write_xml("    </sitemap>\n")

    sitemap_index.write_xml("</sitemapindex>\n")

    upload_to_key(sitemap_index.xml, bucket_path + "sitemap.xml")
    log.info("Sitemap index upload complete.")

    for sitemap in sitemaps:
        filename_on_s3 = bucket_path + sitemap.filename_s3
        upload_to_key(sitemap.xml, filename_on_s3)
        log.info(f"Sitemap file {sitemap.filename_s3} upload complete.")


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
@click.option("--dryrun", is_flag=True, help='inspect what will be updated')
@click.option("--cleanup_solr", is_flag=True, help='Only remove orphaned entries in Solr')
@click.option("--update_solr", is_flag=True, help=(
    '(Update solr entries with new data from DB) OR (Add DB data to Solr that is missing)'))
def db_solr_sync(dryrun, cleanup_solr, update_solr):
    ''' db solr sync '''
    if dryrun:
        log.info('Starting dryrun to update index.')

    package_index = index_for(model.Package)

    # get active packages from DB
    active_package = [(r[0], r[1].replace(microsecond=0)) for r in model.Session.query(model.Package.id,
                      model.Package.metadata_modified).filter(model.Package.state != 'deleted').all()]
    log.info(f"total {len(active_package)} DB active_package")

    # get indexed packages from solr
    indexed_package = set(get_all_entity_ids_and_date(max_results=2000000))
    log.info(f"total {len(indexed_package)} solr indexed_package")

    solr_package = indexed_package - set(active_package)
    db_package = set(active_package) - indexed_package

    work_list = {}
    for id, _ in (solr_package):
        work_list[id] = "solr"
    for id, _ in (db_package):
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
        for id in set_cleanup:
            log.info(f"deleting index with {id} \n")
            try:
                package_index.remove_dict({'id': id})
            except Exception as e:
                log.error(u'Error while delete index %s: %s' % (id, repr(e)))
        package_index.commit()
        log.info('Finished cleaning solr entries.')

    if not dryrun and set_update and (update_solr or both):
        log.info("rebuilding indexes\n")
        try:
            rebuild(package_ids=set_update, defer_commit=True)
        except Exception as e:
            log.error(u'Error while rebuild index %s: %s' % (id, repr(e)))
        package_index.commit()
        log.info('Finished updating solr entries.')


@geodatagov.command()
def test_command():
    ''' Basic cli command with normal result '''
    print("This is a good test!")
    return True


@datagovs3.command()
def s3_test():
    ''' Basic cli command to talk to s3 '''

    # Grab all of the necessary config and create S3 client
    bucket_name = config.get("ckanext.s3sitemap.aws_bucket_name")
    s3 = boto3.client(
        's3',
        aws_access_key_id=config.get("ckanext.s3sitemap.aws_access_key_id"),
        aws_secret_access_key=config.get("ckanext.s3sitemap.aws_secret_access_key"),
        region_name=config.get("ckanext.s3sitemap.region_name"),
        endpoint_url=config.get("ckanext.s3sitemap.endpoint_url"),
        config=Config(s3={'addressing_style': 'auto'})
    )

    # Only for local testing: create bucket if needed
    try:
        s3.create_bucket(Bucket=bucket_name)
    except Exception:
        pass

    # Create test file to upload
    # Print the contents out, so test can validate results
    with open('test.txt', 'w') as f:
        content = 'Yay!  I was created at %s' % str(datetime.datetime.now())
        f.write(content)
        print(content)

    # Hash file and upload to S3
    md5 = base64.b64encode(hashsum('test.txt')).decode("utf-8")
    with open('test.txt', "rb") as f:
        s3.put_object(Body=f, Bucket=bucket_name, Key='test.txt', ContentMD5=md5)


def hashsum(path, hex=False, hash_type=hashlib.md5):
    # Courtesy of https://stackoverflow.com/a/15020115
    hashinst = hash_type()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(hashinst.block_size * 128), b''):
            hashinst.update(chunk)
    return hashinst.hexdigest() if hex else hashinst.digest()


# IClick
def get_commands() -> list:
    """List of commands to pass to ckan"""

    return [geodatagov]


# IClick
def get_commands2() -> list:
    """List of commands to pass to ckan"""

    return [datagovs3]
