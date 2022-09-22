import base64
import datetime
import hashlib
import json
import logging

import os
import boto3
import click
import math
import urllib3

from past.utils import old_div
from botocore.exceptions import ClientError
from ckan.plugins.toolkit import config

import ckan
import ckan.model as model
import ckan.lib.search as search
import ckan.logic as logic
from ckanext.geodatagov.search import GeoPackageSearchQuery

import sys
from ckan.lib.search.common import SearchError
from ckan.lib.search.index import PackageSearchIndex, NoopSearchIndex
from ckan.lib.search.query import (
    TagSearchQuery, ResourceSearchQuery, PackageSearchQuery
)

_INDICES = {
    'package': PackageSearchIndex
}

_QUERIES = {
    'tag': TagSearchQuery,
    'resource': ResourceSearchQuery,
    'package': PackageSearchQuery
}


# default constants
DEFAULT_LOG = "ckanext.geodatagov"
#   for sitemap_to_s3
UPLOAD_TO_S3 = True
PAGE_SIZE = 1000
MAX_PER_PAGE = 50000
DEFAULT_DRYRUN = False

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


def get_response(url):
    http = urllib3.PoolManager()
    CKAN_SOLR_USER = os.environ.get("CKAN_SOLR_USER", "")
    CKAN_SOLR_PASSWORD = os.environ.get("CKAN_SOLR_PASSWORD", "")
    headers = urllib3.make_headers(basic_auth="{}:{}".format(CKAN_SOLR_USER, CKAN_SOLR_PASSWORD))
    try:
        response = http.request('GET', url, headers=headers)
    except urllib3.HTTPError as e:
        print('The server couldn\'t fulfill the request.')
        print(('Error code: ', e.code))
        return 'error'
    except urllib3.URLError as e:
        print('We failed to reach a server.')
        print(('Reason: ', e.reason))
        return 'error'
    else:
        return response


# work in progress
@geodatagov.command()
def db_solr_sync():
    """db_solr_sync - work in progress"""
    log.info("db_solr_sync - work in progress...")
    print(str(datetime.datetime.now()) + ' Entering Database Solr Sync function.')

    url = config.get('solr_url') + "/select?q=*%3A*&sort=id+asc&fl=id%2Cmetadata_modified&wt=json&indent=true"
    response = get_response(url)

    if (response != 'error'):

        print(str(datetime.datetime.now()) + ' Deleting records from miscs_solr_sync.')
        sql = '''delete from miscs_solr_sync'''
        model.Session.execute(sql)
        model.Session.commit()

        f = response.data
        data = json.loads(f)
        print(data)
        rows = data.get('response').get('numFound')

        start = 0
        chunk_size = 1000

        print(str(datetime.datetime.now()) + ' Starting insertion of records in miscs_solr_sync .')

        for x in range(0, int(math.ceil(old_div(rows, chunk_size))) + 1):

            if (x == 0):
                start = 0

            print(str(datetime.datetime.now()) + ' Fetching ' + url + "&rows=" + str(chunk_size) + "&start=" + str(start))

            response = get_response(url + "&rows=" + str(chunk_size) + "&start=" + str(start))
            f = response.data
            data = json.loads(f)
            results = data.get('response').get('docs')

            print(str(datetime.datetime.now()) + ' Inserting ' + str(start) + ' - ' + str(
                start + int(data.get('responseHeader').get('params').get('rows')) - 1) + ' of ' + str(rows))

            for x in range(0, len(results)):
                sql = '''select count(id) as count from package where id = :pkg_id;'''
                q = model.Session.execute(sql, {'pkg_id': results[x]['id']})
                for row in q:
                    if (row['count'] == 0):
                        sql = '''delete from miscs_solr_sync where pkg_id = :pkg_id;'''
                        model.Session.execute(sql, {'pkg_id': results[x]['id']})
                        sql = '''insert into miscs_solr_sync (pkg_id, action) values (:pkg_id, :action);'''
                        model.Session.execute(sql, {'pkg_id': results[x]['id'], 'action': 'notfound'})
                        model.Session.commit()
                    else:
                        pkg_dict = logic.get_action('package_show')(
                            {'model': model, 'ignore_auth': True, 'validate': False},
                            {'id': results[x]['id']})
                        if (str(results[x]['metadata_modified'])[: 19] != pkg_dict['metadata_modified'][: 19]):
                            print(str(datetime.datetime.now()) + ' Action Type : outsync for Package Id: \
                                ' + results[x]['id'])
                            print(' ' * 26 + ' Modified Date from Solr: ' + str(results[x]['metadata_modified']))
                            print(' ' * 26 + ' Modified Date from Db: ' + pkg_dict['metadata_modified'])
                            sql = '''delete from miscs_solr_sync where pkg_id = :pkg_id;'''
                            model.Session.execute(sql, {'pkg_id': results[x]['id']})
                            sql = '''insert into miscs_solr_sync (pkg_id, action) values (:pkg_id, :action);'''
                            model.Session.execute(sql, {'pkg_id': results[x]['id'], 'action': 'outsync'})
                            model.Session.commit()
                        else:
                            sql = '''delete from miscs_solr_sync where pkg_id = :pkg_id;'''
                            model.Session.execute(sql, {'pkg_id': results[x]['id']})
                            sql = '''insert into miscs_solr_sync (pkg_id, action) values (:pkg_id, :action);'''
                            model.Session.execute(sql, {'pkg_id': results[x]['id'], 'action': 'insync'})
                            model.Session.commit()

            start = int(data.get('responseHeader').get('params').get('start')) + chunk_size

        print(str(datetime.datetime.now()) + ' Starting Database to Solr Sync')

        # sql = '''Select id from package where id not in (select pkg_id from miscs_solr_sync); '''
        sql = '''Select p.id as pkg_id from package p
                left join miscs_solr_sync sp on sp.pkg_id = p.id
                where sp.pkg_id is null; '''

        q = model.Session.execute(sql)
        pkg_ids = set()
        for row in q:
            pkg_ids.add(row['pkg_id'])
        for pkg_id in pkg_ids:
            try:
                print(str(datetime.datetime.now()) + ' Building Id: ' + pkg_id)
                search.rebuild(pkg_id)
            except ckan.logic.NotFound:
                print("Error: Not Found.")
            except KeyboardInterrupt:
                print("Stopped.")
                return
            except BaseException:
                raise

        sql = '''Select pkg_id from miscs_solr_sync where action = 'outsync'; '''
        q = model.Session.execute(sql)
        pkg_ids = set()
        for row in q:
            pkg_ids.add(row['pkg_id'])
        for pkg_id in pkg_ids:
            try:
                print(str(datetime.datetime.now()) + ' Rebuilding Id: ' + pkg_id)
                search.rebuild(pkg_id)
            except ckan.logic.NotFound:
                print("Error: Not Found.")
            except KeyboardInterrupt:
                print("Stopped.")
                return
            except BaseException:
                raise

        print(str(datetime.datetime.now()) + ' Starting Solr to Database Sync')

        sql = '''Select pkg_id from miscs_solr_sync where action = 'notfound'; '''
        q = model.Session.execute(sql)
        pkg_ids = set()
        for row in q:
            pkg_ids.add(row['pkg_id'])
        for pkg_id in pkg_ids:
            try:
                search.clear(pkg_id)
            except ckan.logic.NotFound:
                print("Error: Not Found.")
            except KeyboardInterrupt:
                print("Stopped.")
                return
            except BaseException:
                raise

        print(str(datetime.datetime.now()) + " All Sync Done.")


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


def query_for(_type):
    """ Get a SearchQuery instance sub-class suitable for the specified
        type. """
    try:
        _type_n = _normalize_type(_type)
        return _QUERIES[_type_n]()
    except KeyError:
        raise SearchError("Unknown search type: %s" % _type)


@geodatagov.command()
@click.option("--dryrun", default=DEFAULT_DRYRUN, type=click.BOOL, help='inspect what will be delected')
def remove_orphaned_solr(dryrun):
    ''' remove_orphaned_solr '''
    if dryrun:
        log.info('Starting dryrun to remove index.')

    package_index = index_for(model.Package)

    package_ids = [r[0] for r in model.Session.query(model.Package.id).
                   filter(model.Package.state != 'deleted').all()]

    deleted_package_ids = [r[0] for r in model.Session.query(model.Package.id).
                filter(model.Package.state == 'deleted').all()]
    log.info(f"The DB_deleted_package_ids: {deleted_package_ids}")

    package_query = query_for(model.Package)
    indexed_pkg_ids = set(package_query.get_all_entity_ids())

    for id in deleted_package_ids:
        if id in indexed_pkg_ids:
            log.info(f"The deleted_id {id} is in solr")
        else:
            log.info(f"The deleted_id {id} NOT is in solr")

    log.info(f"total solr_indexed_ids: {len(indexed_pkg_ids)}; total DB_ids: {len(package_ids)}")

    # Packages orphaned
    package_ids = indexed_pkg_ids - set(package_ids)

    if len(package_ids) == 0:
        log.info('solr is good.')
        return

    total_packages = len(package_ids)

    log.info(f'Start to remove {total_packages} orphaned solr entries...')
    for counter, pkg_id in enumerate(package_ids):
        log.info(f"removing index {counter+1}/{total_packages} with id {pkg_id} \n")
        try:
            if not dryrun:
                package_index.delete_package({'id': pkg_id})
        except Exception as e:
            log.error(u'Error while delete index %s: %s' % (pkg_id, repr(e)))

    model.Session.commit()
    log.info('Finished removing solr entries.')


# IClick
def get_commands() -> list:
    """List of commands to pass to ckan"""

    return [geodatagov]
