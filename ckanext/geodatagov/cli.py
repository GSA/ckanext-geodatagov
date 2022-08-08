import base64
import datetime
import hashlib
import json
import logging
import math
import mimetypes
import os
from email.policy import default
from tempfile import mkstemp

import boto
import ckan.plugins as p
import click
from ckan import model
from ckan.plugins.toolkit import config
from past.utils import old_div

from ckanext.geodatagov.search import GeoPackageSearchQuery

# default constants
DEFAULT_LOG = "ckanext.geodatagov"
#   for sitemap_to_s3
UPLOAD_TO_S3 = True
PAGE_SIZE = 1000
MAX_PER_PAGE = 50000

log = logging.getLogger(DEFAULT_LOG)


def get_commands():
    return [sitemap_to_s3]


@click.group("geodatagov")
def geodatagov():
    pass


def generate_md5_for_s3(filename):
    # hashlib.md5 was set as sha1 in plugin.py
    hash_md5 = hashlib.md5_orig()
    with open(filename, "rb") as f:
        # read chunks of 4096 bytes sequentially to be mem efficient
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    md5_1 = hash_md5.hexdigest()
    md5_2 = base64.b64encode(hash_md5.digest())
    return (md5_1, md5_2)


def get_s3_bucket(bucket_name):
    if not config.get("ckanext.s3sitemap.aws_use_ami_role"):
        p_key = config.get("ckanext.s3sitemap.aws_access_key_id")
        s_key = config.get("ckanext.s3sitemap.aws_secret_access_key")
    else:
        p_key, s_key = (None, None)

    # make s3 connection
    S3_conn = boto.connect_s3(p_key, s_key)

    # make sure bucket exists and that we can access
    try:
        bucket = S3_conn.get_bucket(bucket_name)
    except boto.exception.S3ResponseError as e:
        if e.status == 404:
            raise Exception(
                "Could not find bucket {0}: {1}".format(bucket_name, str(e))
            )
        elif e.status == 403:
            raise Exception("Access to bucket {0} denied".format(bucket_name))
        else:
            raise

    return bucket


def upload_to_key(bucket, upload_filename, filename_on_s3, content_calc=False):
    headers = {}

    # force .gz file to be downoaded
    _, file_extension = os.path.splitext(upload_filename)
    if file_extension == ".gz":
        headers.update({"Content-Type": "application/gzip"})
        headers.update({"Content-Encoding": ""})

    # if needed, help s3 to figure out the content type and encoding
    if content_calc:
        content_type, content_encoding = mimetypes.guess_type(upload_filename)
        if content_type:
            headers.update({"Content-Type": content_type})
        if content_encoding:
            headers.update({"Content-Encoding": content_encoding})

    k = boto.s3.key.Key(bucket)
    try:
        k.key = filename_on_s3
        k.set_contents_from_filename(
            upload_filename, headers=headers, md5=generate_md5_for_s3(upload_filename)
        )
    except Exception as e:
        raise e
    finally:
        k.close()


@geodatagov.command("sitemap_to_s3")
@click.option("--upload_to_s3", default=UPLOAD_TO_S3)
@click.option("--page_size", default=PAGE_SIZE)
@click.option("--max_per_page", default=MAX_PER_PAGE)
def sitemap_to_s3(upload_to_s3, page_size, max_per_page):
    log.info("sitemap is being generated...")

    # cron job
    # paster --plugin=ckanext-geodatagov geodatagov sitemap-to-s3 --config=/etc/ckan/production.ini
    # sql = '''Select id from package where id not in (select pkg_id from miscs_solr_sync); '''

    package_query = GeoPackageSearchQuery()
    count = package_query.get_count()
    log.info(f"{count} records found")
    if not count:
        log.info("Nothing to process, exiting.")
        return

    start = 0
    filename_number = 1
    file_list = []

    # write to a temp file
    DIR_S3SITEMAP = "/tmp/s3sitemap/"
    if not os.path.exists(DIR_S3SITEMAP):
        os.makedirs(DIR_S3SITEMAP)

    fd, path = mkstemp(
        suffix=".xml", prefix="sitemap-%s-" % filename_number, dir=DIR_S3SITEMAP
    )
    # write header
    os.write(fd, '<?xml version="1.0" encoding="UTF-8"?>\n'.encode("utf-8"))
    os.write(
        fd,
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'.encode(
            "utf-8"
        ),
    )
    file_list.append({"path": path, "filename_s3": "sitemap-%s.xml" % filename_number})

    for x in range(0, int(math.ceil(old_div(count, page_size))) + 1):
        pkgs = package_query.get_paginated_entity_name_modtime(
            max_results=page_size, start=start
        )

        for pkg in pkgs:
            os.write(fd, "    <url>\n".encode("utf-8"))
            os.write(
                fd,
                (
                    "        <loc>%s</loc>\n"
                    % (
                        "%s/dataset/%s"
                        % (config.get("ckan.site_url"), pkg.get("name")),
                    )
                ).encode("utf-8"),
            )
            os.write(
                fd,
                (
                    "        <lastmod>%s</lastmod>\n"
                    % (pkg.get("metadata_modified").strftime("%Y-%m-%d"),)
                ).encode("utf-8"),
            )
            os.write(fd, "    </url>\n".encode("utf-8"))
        log.info(
            "%i to %i of %i records done.",
            start + 1,
            min(start + page_size, count),
            count,
        )
        start = start + page_size

        if start % max_per_page == 0 and x != int(math.ceil(old_div(count, page_size))):

            # write footer
            os.write(fd, "</urlset>\n".encode("utf-8"))
            os.close(fd)

            log.info("done with %s.", path)

            filename_number = filename_number + 1
            fd, path = mkstemp(
                suffix=".xml", prefix="sitemap-%s-" % filename_number, dir=DIR_S3SITEMAP
            )
            # write header
            os.write(fd, '<?xml version="1.0" encoding="UTF-8"?>\n'.encode("utf-8"))
            os.write(
                fd,
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'.encode(
                    "utf-8"
                ),
            )

            file_list.append(
                {"path": path, "filename_s3": "sitemap-%s.xml" % filename_number}
            )

    # write footer
    os.write(fd, "</urlset>\n".encode("utf-8"))
    os.close(fd)

    log.info("done with %s.", path)

    if not upload_to_s3:
        log.info("Skip upload and finish.")
        print("Done locally: File list\n{}".format(json.dumps(file_list, indent=4)))
        return file_list

    bucket_name = config.get("ckanext.geodatagov.aws_bucket_name")
    bucket_path = config.get("ckanext.geodatagov.s3sitemap.aws_storage_path", "")
    bucket = get_s3_bucket(bucket_name)

    fd, path = mkstemp(suffix=".xml", prefix="sitemap-", dir=DIR_S3SITEMAP)

    # write header
    os.write(fd, '<?xml version="1.0" encoding="UTF-8"?>\n'.encode("utf-8"))
    os.write(
        fd,
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'.encode(
            "utf-8"
        ),
    )

    current_time = datetime.datetime.now().strftime("%Y-%m-%d")
    for item in file_list:
        upload_to_key(bucket, item["path"], bucket_path + item["filename_s3"])
        os.remove(item["path"])

        # add to sitemap index file
        os.write(fd, "    <sitemap>\n".encode("utf-8"))
        os.write(
            fd,
            (
                "        <loc>%s</loc>\n"
                % (
                    config.get("ckanext.geodatagov.s3sitemap.aws_s3_url")
                    + config.get("ckanext.geodatagov.s3sitemap.aws_storage_path")
                    + item["filename_s3"],
                )
            ).encode("utf-8"),
        )
        os.write(
            fd, ("        <lastmod>%s</lastmod>\n" % (current_time,)).encode("utf-8")
        )
        os.write(fd, "    </sitemap>\n".encode("utf-8"))
    os.write(fd, "</sitemapindex>\n".encode("utf-8"))
    os.close(fd)

    upload_to_key(bucket, path, bucket_path + "sitemap.xml")
    os.remove(path)

    log.info("Sitemap upload complete.")
