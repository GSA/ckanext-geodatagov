import base64
import csv
import hashlib
import logging
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

import ckan.model as model
import ckan.logic as logic
from ckan import plugins as p
from ckan.plugins.toolkit import config


# https://github.com/GSA/ckanext-geodatagov/issues/117
log = logging.getLogger('ckanext.geodatagov')

ckan_tmp_path = '/var/tmp/ckan'


class GeoGovCommand(p.SingletonPlugin):
    '''
    Commands:

        paster geodatagov import-orgs <data> -c <config>
        paster geodatagov post-install-dbinit -c <config>
        paster geodatagov import-dms -c <config>
        paster geodatagov import-doi -c <config>
        paster geodatagov clean-deleted -c <config>
        paster geodatagov combine-feeds -c <config>
        paster geodatagov export-csv -c <config>
    '''
    p.implements(p.IClick)
    summary = __doc__.split('\n')[0]
    usage = __doc__

    def command(self):
        '''
        Parse command line arguments and call appropriate method.
        '''
        if not self.args or self.args[0] in ['--help', '-h', 'help']:
            print(GeoGovCommand.__doc__)
            return

        cmd = self.args[0]
        self._load_config()

        user = logic.get_action('get_site_user')(
            {'model': model, 'ignore_auth': True}, {}
        )
        self.user_name = user['name']

        if cmd == 'import-orgs':
            if not len(self.args) in [2, 3]:
                print(GeoGovCommand.__doc__)
                return

            self.import_organizations(self.args[1])
        if cmd == 'import-dms':
            if not len(self.args) in [2]:
                print(GeoGovCommand.__doc__)
                return
            self.import_dms(self.args[1])
        if cmd == 'post-install-dbinit':
            f = open('/usr/lib/ckan/src/ckanext-geodatagov/what_to_alter.sql')
            print("running what_to_alter.sql")
            test = model.Session.execute(f.read())
            f = open('/usr/lib/ckan/src/ckanext-geodatagov/constraints.sql')
            print("running constraints.sql")
            test = model.Session.execute(f.read())  # NOQA F841
            model.Session.commit()  # NOQA F841
            print("Success")
        if cmd == 'clean-deleted':
            self.clean_deleted()
        if cmd == 'combine-feeds':
            self.combine_feeds()
        if cmd == 'export-csv':
            self.export_csv()
        # this code is defunct and will need to be refactored into cli.py
        """
        if cmd == "jsonl-export":
            self.jsonl_export()
        if cmd == 'metrics-csv':
            self.metrics_csv()
        """

    def get_user_org_mapping(self, location):
        user_org_mapping = open(location)
        csv_reader = csv.reader(user_org_mapping)
        mapping = {}
        for row in csv_reader:
            mapping[row[0].lower()] = row[1]
        return mapping

    def import_organizations(self, location):
        fields = ['title', 'type', 'name']

        user = logic.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
        organizations = open(location)

        csv_reader = csv.reader(organizations)

        all_rows = set()
        for row in csv_reader:
            all_rows.add(tuple(row))

        for num, row in enumerate(all_rows):
            row = dict(list(zip(fields, row)))
            org = logic.get_action('organization_create')(  # NOQA F841
                {'model': model, 'user': user['name'],
                 'session': model.Session},
                {'name': row['name'],
                 'title': row['title'],
                 'extras': [{'key': 'organization_type',
                             'value': row['type']}]
                 }
            )


def get_response(url):
    req = Request(url)
    try:
        response = urlopen(req)
    except HTTPError as e:
        print('The server couldn\'t fulfill the request.')
        print(('Error code: ', e.code))
        return 'error'
    except URLError as e:
        print('We failed to reach a server.')
        print(('Reason: ', e.reason))
        return 'error'
    else:
        return response


def email_log(log_type, msg):
    import ckan.lib.mailer as mailer

    email_address = config.get('email_to')
    email = {'recipient_name': email_address,
             'recipient_email': email_address,
             'subject': log_type + ' Log',
             'body': msg,
             }
    try:
        mailer.mail_recipient(**email)
    except Exception as e:
        log.error('Error: %s; email: %s' % (e, email))


# this code is defunct and will need to be refactored into cli.py
"""
def get_s3_bucket(bucket_name):
    if not config.get('ckanext.s3sitemap.aws_use_ami_role'):
        p_key = config.get('ckanext.s3sitemap.aws_access_key_id')
        s_key = config.get('ckanext.s3sitemap.aws_secret_access_key')
    else:
        p_key, s_key = (None, None)

    # make s3 connection
    S3_conn = boto.connect_s3(p_key, s_key)

    # make sure bucket exists and that we can access
    try:
        bucket = S3_conn.get_bucket(bucket_name)
    except boto.exception.S3ResponseError as e:
        if e.status == 404:
            raise Exception('Could not find bucket {0}: {1}'.
                            format(bucket_name, str(e)))
        elif e.status == 403:
            raise Exception('Access to bucket {0} denied'.
                            format(bucket_name))
        else:
            raise

    return bucket
"""


def generate_md5_for_s3(filename):
    # hashlib.md5 was set as sha1 in plugin.py
    hash_md5 = hashlib.md5_orig()
    with open(filename, 'rb') as f:
        # read chunks of 4096 bytes sequentially to be mem efficient
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    md5_1 = hash_md5.hexdigest()
    md5_2 = base64.b64encode(hash_md5.digest())
    return (md5_1, md5_2)


# this code is defunct and will need to be refactored into cli.py
"""
def upload_to_key(bucket, upload_filename, filename_on_s3, content_calc=False):
    headers = {}

    # force .gz file to be downoaded
    _throwaway, file_extension = os.path.splitext(upload_filename)
    if file_extension == '.gz':
        headers.update({'Content-Type': 'application/gzip'})
        headers.update({'Content-Encoding': ''})

    # if needed, help s3 to figure out the content type and encoding
    if content_calc:
        content_type, content_encoding = mimetypes.guess_type(upload_filename)
        if content_type:
            headers.update({'Content-Type': content_type})
        if content_encoding:
            headers.update({'Content-Encoding': content_encoding})

    k = boto.s3.key.Key(bucket)
    try:
        k.key = filename_on_s3
        k.set_contents_from_filename(
            upload_filename,
            headers=headers,
            md5=generate_md5_for_s3(upload_filename)
        )
    except Exception as e:
        raise e
    finally:
        k.close()
"""
