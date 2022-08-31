import base64
import datetime
import hashlib
import json
import logging

import boto3
import click
from botocore.exceptions import ClientError
from ckan.plugins.toolkit import config

from ckanext.geodatagov.search import GeoPackageSearchQuery

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

    import ipdb

    ipdb.set_trace()

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

    # TODO REMOVE
    import ipdb

    ipdb.set_trace()

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


# IClick
def get_commands() -> list:
    """List of commands to pass to ckan"""

    return [geodatagov]
