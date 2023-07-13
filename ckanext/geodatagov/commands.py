import base64
import csv
import datetime
import json
import hashlib
import logging
import math
import re
import requests
import time
import xml.etree.ElementTree as ET
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

import ckan
import ckan.model as model
import ckan.logic as logic
import ckan.lib.munge as munge
from ckan import plugins as p
from ckan.plugins.toolkit import config

from ckanext.harvest.model import HarvestSource, HarvestJob
from ckanext.geodatagov.model import MiscsFeed


# https://github.com/GSA/ckanext-geodatagov/issues/117
log = logging.getLogger('ckanext.geodatagov')

ckan_tmp_path = '/var/tmp/ckan'


class GeoGovCommand(p.SingletonPlugin):
    '''
    Commands:

        paster geodatagov import-harvest-source <harvest_source_data> -c <config>
        paster geodatagov import-orgs <data> -c <config>
        paster geodatagov post-install-dbinit -c <config>
        paster geodatagov import-dms -c <config>
        paster geodatagov import-doi -c <config>
        paster geodatagov clean-deleted -c <config>
        paster geodatagov combine-feeds -c <config>
        paster geodatagov harvest-job-cleanup -c <config>
        paster geodatagov export-csv -c <config>
        paster geodatagov update-dataset-geo-fields -c <config>
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

        if cmd == 'import-harvest-source':
            if not len(self.args) in [2]:
                print(GeoGovCommand.__doc__)
                return

            self.import_harvest_source(self.args[1])

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
        if cmd == 'import-doi':
            self.import_doi()
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
        if cmd == 'harvest-job-cleanup':
            self.harvest_job_cleanup()
        if cmd == 'export-csv':
            self.export_csv()
        # this code is defunct and will need to be refactored into cli.py
        """
        if cmd == "jsonl-export":
            self.jsonl_export()
        if cmd == 'metrics-csv':
            self.metrics_csv()
        """
        if cmd == 'update-dataset-geo-fields':
            self.update_dataset_geo_fields()

    def get_user_org_mapping(self, location):
        user_org_mapping = open(location)
        csv_reader = csv.reader(user_org_mapping)
        mapping = {}
        for row in csv_reader:
            mapping[row[0].lower()] = row[1]
        return mapping

    def import_harvest_source(self, sources_location):
        '''Import data from this mysql command
    select DOCUUID, TITLE, OWNER, APPROVALSTATUS, HOST_URL, Protocol, PROTOCOL_TYPE, FREQUENCY, USERNAME
        into outfile '/tmp/results_with_user.csv'
    from GPT_RESOURCE
    join GPT_USER on owner = USERID
        where frequency is not null;
'''
        error_log = open('harvest_source_import_errors.txt', 'w+')

        fields = ['DOCUUID', 'TITLE', 'OWNER', 'APPROVALSTATUS', 'HOST_URL',
                  'PROTOCAL', 'PROTOCOL_TYPE', 'FREQUENCY', 'ORGID']

        user = logic.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})

        harvest_sources = open(sources_location)
        try:
            csv_reader = csv.reader(harvest_sources)
            import re
            for row in csv_reader:
                row = dict(list(zip(fields, row)))

                # neeeds some fix
                # if row['PROTOCOL_TYPE'].lower() not in ('waf', 'csw', 'z3950'):
                # continue

                # frequency = row['FREQUENCY'].upper()
                # if frequency not in ('WEEKLY', 'MONTHLY', 'BIWEEKLY'):

                frequency = 'MANUAL'

                config = {
                    'ORIGINAL_UUID': row['DOCUUID'][1: -1].lower()
                }

                protocal = row['PROTOCAL']
                protocal = protocal[protocal.find('<protocol'):]

                protocal = re.sub('<protocol.*?>', '<protocol>', protocal)

                root = ET.fromstring(protocal[protocal.find('<protocol'):])

                for child in root:
                    if child.text:
                        config[child.tag] = child.text

                harvest_source_dict = {
                    'name': munge.munge_title_to_name(row['TITLE']),
                    'title': row['TITLE'],
                    'url': row['HOST_URL'],
                    'source_type': row['PROTOCOL_TYPE'].lower(),
                    'frequency': frequency,
                    'config': json.dumps(config),
                    'owner_org': row['ORGID']
                }
                harvest_source_dict.update(config)

                try:
                    harvest_source = logic.get_action('harvest_source_create')(  # NOQA F841
                        {'model': model, 'user': user['name'],
                         'session': model.Session, 'api_version': 3},
                        harvest_source_dict
                    )
                except ckan.logic.ValidationError as e:
                    error_log.write(json.dumps(harvest_source_dict))
                    error_log.write(str(e))
                    error_log.write('\n')

        finally:
            model.Session.commit()
            harvest_sources.close()
            error_log.close()

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

    def import_dms(self, url):

        input_records = requests.get(url).json()
        to_import = {}
        for record in input_records:
            to_import[record['identifier']] = record

        user = logic.get_action('get_site_user')(  # NOQA F841
            {'model': model, 'ignore_auth': True}, {}
        )

        collected_ids = set(to_import.keys())

        existing_package_ids = set([row[0] for row in
                                    model.Session.query(model.Package.id).from_statement(
                                        '''select p.id
                                        from package p
                                        join package_extra pe on p.id = pe.package_id
                                        where pe.key = 'metadata-source' and pe.value = 'dms'
                                        and p.state = 'active' ''')])

        context = {}
        context['user'] = self.user_name

        for num, package_id in enumerate(collected_ids - existing_package_ids):
            context.pop('package', None)
            context.pop('group', None)
            new_package = to_import[package_id]
            try:
                log.info('Creating id=%s', package_id)
                logic.get_action('datajson_create')(context, new_package)
            except Exception:
                log.exception('Error when creating id=%s', package_id)

        for package_id in collected_ids & existing_package_ids:
            context.pop('package', None)
            context.pop('group', None)
            new_package = to_import[package_id]
            try:
                logic.get_action('datajson_update')(context, new_package)
            except Exception:
                log.exception('Error when updating id=%s', package_id)

        for package_id in existing_package_ids - collected_ids:
            context.pop('package', None)
            context.pop('group', None)
            try:
                logic.get_action('package_delete')(context, {"id": package_id})
            except Exception:
                log.exception('Error when deleting id=%s', package_id)

    def import_doi(self):
        doi_url = config.get('ckanext.geodatagov.doi.url', '')
        if not doi_url:
            log.error('ckanext.geodatagov.doi.url not defined in config.')
            return

        url_list = doi_url + ('api/search/dataset?qjson={'
                              '"fl": "id,extras_harvest_object_id",'
                              '"q": "harvest_object_id: [\\\"\\\"%20TO%20*],%20metadata_type: geospatial",'
                              '"sort": "id%20asc","start": 0,"limit": 0}')
        url_dataset = doi_url + 'api/action/package_show?id='
        url_harvestobj = doi_url + 'harvest/object/'

        try:
            requested = requests.get(url_list, verify=False).json()
        except Exception:
            log.exception('Error when accessing doi list at %s', url_list)

        total = requested['count']
        pagination = 1000
        to_import = {}
        for page in range(0, int(math.ceil(float(total) / pagination)) + 1):
            url_list_dataset = ""
            input_records = []
            start = page * pagination
            url_list_dataset = url_list.replace('"limit": 0', '"limit": 1000')
            url_list_dataset = url_list_dataset.replace('"start": 0', '"start": ' + str(start))
            try:
                input_records = requests.get(url_list_dataset, verify=False).json()
            except Exception:
                log.exception('Error when accessing doi list at %s', url_list)

            input_records = input_records['results']
            for record in input_records:
                to_import[record['id']] = record['extras']['harvest_object_id']

        collected_ids = set(to_import.keys())

        existing_ids = set([row[0] for row in
                            model.Session.query(model.Package.id).from_statement(
                                '''select p.id
                                from package p
                                join package_extra pe on p.id = pe.package_id
                                where pe.key = 'metadata-source' and pe.value = 'doi' ''')])

        context = {}
        user = logic.get_action('get_site_user')(  # NOQA F841
            {'model': model, 'ignore_auth': True}, {}
        )
        context['user'] = self.user_name

        source_name = 'import-doi'
        source_pkg = model.Package.get(source_name)
        if not source_pkg:
            log.error('Harvest source %s does not exist', source_name)
            return
        source_id = source_pkg.id
        source = HarvestSource.get(source_id)
        if not source:
            log.error('Harvest source %s does not exist', source_id)
            return

        # Check if the source is active
        if not source.active:
            log.warn('Harvest job cannot be created for inactive source %s', source_id)
            raise Exception('Can not create jobs on inactive sources')

        job = HarvestJob()
        job.source = source
        job.save()
        context['harvest_job'] = job

        log.info('Start to import doi datasets.')
        log.info('Datasets found on remote doi server: %s, on local: %s', len(collected_ids), len(existing_ids))

        ids_to_add = collected_ids - existing_ids
        log.info('Datasets to be added as new: %s', len(ids_to_add))
        for num, doi_id in enumerate(ids_to_add):
            context.pop('package', None)
            context.pop('group', None)
            try:
                new_package = self.get_doi_package(url_dataset + doi_id)
                new_harvestobj = self.get_doi_harvestobj(url_harvestobj + to_import[doi_id])
            except Exception:
                log.exception('Error when downlaoding doi id=%s and harvest object %s', doi_id, to_import[doi_id])

            context['harvestobj'] = new_harvestobj
            try:
                logic.get_action('doi_create')(context, new_package)
            except Exception:
                log.exception('Error when importing doi id=%s', doi_id)

        ids_to_update = collected_ids & existing_ids
        log.info('Datasets to check for update: %s', len(ids_to_update))
        for num, doi_id in enumerate(ids_to_update):
            context.pop('package', None)
            context.pop('group', None)
            try:
                new_package = self.get_doi_package(url_dataset + doi_id)
                new_harvestobj = self.get_doi_harvestobj(url_harvestobj + to_import[doi_id])
            except Exception:
                log.exception('Error when downlaoding doi id=%s and harvest object %s', doi_id, to_import[doi_id])

            context['harvestobj'] = new_harvestobj
            try:
                logic.get_action('doi_update')(context, new_package)
            except Exception:
                log.exception('Error when updating doi id=%s', doi_id)

        ids_to_delete = existing_ids - collected_ids
        log.info('Datasets to be deleted: %s', len(ids_to_delete))
        for num, doi_id in enumerate(ids_to_delete):
            context.pop('package', None)
            context.pop('group', None)
            try:
                logic.get_action('package_delete')(context, {"id": doi_id})
                log.info('Deleted doi id=%s', doi_id)
            except Exception:
                log.exception('Error when deleting doi id=%s', doi_id)

    def get_doi_package(self, url_dataset):
        dataset = requests.get(url_dataset, verify=False).json()
        dataset = dataset['result']
        return dataset

    def get_doi_harvestobj(self, url_harvestobj):
        harvestobj = requests.get(url_harvestobj, verify=False)
        return harvestobj.text

    def clean_deleted(self):
        log.info('Starting delete for clean-deleted')
        # TODO make the 90-day purge configurable
        sql = '''begin;
        update package p
        set state = 'to_delete'
        where id in (
          select p.id
          from package p, revision r
          where p.state <> 'active' and p.revision_id = r.id and r.timestamp < now() - interval '90 day'
          limit 1000
        );

        update package set state = 'to_delete' where owner_org is null;
        delete from package_role where package_id in (select id from package where state = 'to_delete' );

        /*
         * This query is obsurdly inefficient, but explains what we're after with the left outer join.
         * delete from user_object_role
                where id not in (select user_object_role_id from package_role) and context = 'Package';
         */
        delete from user_object_role where id in (
          select uor.id
          from user_object_role uor
          left outer join package_role pr ON pr.user_object_role_id = uor.id
          where pr.user_object_role_id is NULL and uor.context = 'Package'
        );

        delete from resource_revision where package_id in (select id from package where state = 'to_delete' );
        delete from package_tag_revision where package_id in (select id from package where state = 'to_delete');
        delete from member_revision where table_id in (select id from package where state = 'to_delete');
        delete from package_extra_revision where package_id in (select id from package where state = 'to_delete');
        delete from package_revision where id in (select id from package where state = 'to_delete');
        delete from package_tag where package_id in (select id from package where state = 'to_delete');
        delete from resource_view where resource_id in (select id from resource
            where package_id in (select id from package where state = 'to_delete'));
        delete from resource where package_id in (select id from package where state = 'to_delete');
        delete from package_extra where package_id in (select id from package where state = 'to_delete');
        delete from member where table_id in (select id from package where state = 'to_delete');
        delete from related_dataset where dataset_id in (select id from package where state = 'to_delete');

        delete from harvest_object_error hoe using harvest_object ho
            where ho.id = hoe.harvest_object_id and package_id  in (select id from package where state = 'to_delete');
        delete from harvest_object_extra hoe using harvest_object ho
            where ho.id = hoe.harvest_object_id and package_id  in (select id from package where state = 'to_delete');
        delete from harvest_object where package_id in (select id from package where state = 'to_delete');

        delete from package where state = 'to_delete';
        commit;
        '''
        model.Session.execute(sql)
        log.info('Finished delete for clean-deleted')

    # set([u'feed', u'webService', u'issued', u'modified', u'references', u'keyword', u'size',
    #      u'landingPage', u'title', u'temporal', u'theme', u'spatial', u'dataDictionary', u'description',
    #      u'format', u'granularity', u'accessLevel', u'accessURL', u'publisher', u'language', u'license',
    #      u'systemOfRecords', u'person', u'accrualPeriodicity', u'dataQuality', u'distribution', u'identifier', u'mbox'])

    # {u'title': 6061, u'theme': 6061, u'accessLevel': 6061, u'publisher': 6061, u'identifier': 6061,
    #  u'description': 6060, u'accessURL': 6060, u'distribution': 6060, u'keyword': 6059, u'person': 6057,
    #  u'accrualPeriodicity': 6056, u'format': 6047, u'spatial': 6009, u'size': 5964, u'references': 5841,
    #  u'dataDictionary': 5841, u'temporal': 5830, u'modified': 5809, u'issued': 5793, u'mbox': 5547,
    #  u'granularity': 4434, u'license': 2048, u'dataQuality': 453}

    def combine_feeds(self):
        from xml.dom import minidom
        from xml.parsers.expat import ExpatError
        import urllib.error
        import urllib.parse
        import urllib.request

        feed_url = config.get('ckan.site_url') + '/feeds/dataset.atom'
        # from http://boodebr.org/main/python/all-about-python-and-unicode#UNI_XML
        RE_XML_ILLEGAL = u'([\u0000-\u0008\u000b-\u000c\u000e-\u001f\ufffe-\uffff])' + \
                         u'|' + \
                         u'([%s-%s][^%s-%s])|([^%s-%s][%s-%s])|([%s-%s]$)|(^[%s-%s])' % \
                         (chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff),
                          chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff),
                          chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff))

        def get_dom(url):
            retry = 5
            delay = 3
            while retry > 0:
                print('%s fetching %s' % (datetime.datetime.now(), url))
                try:
                    xml = urllib.request.urlopen(url_page_feed).read()
                    xml = re.sub(RE_XML_ILLEGAL, "?", xml)
                    dom = minidom.parseString(xml)
                except ExpatError:
                    print('retry url: %s' % url)
                    print('deplay %s seconds...' % (delay ** (6 - retry)))
                    time.sleep(delay ** (6 - retry))
                    retry = retry - 1
                    continue

                return dom
            raise Exception('Can not connect to %s after multiple tries' % url)

        feed = None
        for page in range(0, 20):
            url_page_feed = feed_url + '?page=' + str(page + 1)
            if not feed:
                dom = get_dom(url_page_feed)
                feed = dom.getElementsByTagName('feed')[0]
                for child in feed.childNodes:
                    if child.getAttribute('rel') in ['next', 'first', 'last']:
                        feed.removeChild(child)
            else:
                dom = get_dom(url_page_feed)
                entrylist = dom.getElementsByTagName('entry')
                for entry in entrylist:
                    feed.appendChild(entry)

        if not feed:
            raise Exception('Can not read any feed')

        doc = minidom.Document()
        doc.appendChild(feed)
        output = doc.toxml('utf-8')
        entry = model.Session.query(MiscsFeed).first()
        if not entry:
            # create the empty entry for the first time
            entry = MiscsFeed()
        entry.feed = output
        entry.save()

        print('%s combined feeds updated' % datetime.datetime.now())

    def harvest_job_cleanup(self):
        if p.toolkit.check_ckan_version(min_version='2.8'):
            print('Task removed since new ckanext-harvest include ckan.harvest.timeout to mark as finished stuck jobs')
            return

    @staticmethod
    def export_group_and_tags(packages, domain='https://catalog.data.gov'):

        result = []
        for pkg in packages:
            package = dict()

            package_groups = pkg.get('groups')
            if not package_groups:
                continue

            extras = dict([(x['key'], x['value']) for x in pkg['extras']])
            package['title'] = pkg.get('title')
            package['url'] = domain + '/dataset/' + pkg.get('name')
            package['organization'] = pkg.get('organization').get('title')
            package['organizationUrl'] = domain + '/organization/' + pkg.get('organization').get('name')
            package['harvestSourceTitle'] = extras.get('harvest_source_title', '')
            package['harvestSourceUrl'] = ''
            harvest_source_id = extras.get('harvest_source_id')
            if harvest_source_id:
                package['harvestSourceUrl'] = domain + '/harvest/' + harvest_source_id

            for group in package_groups:
                package = package.copy()
                category_tag = '__category_tag_' + group.get('id')
                package_categories = extras.get(category_tag)

                package['topic'] = group.get('title')
                package['topicCategories'] = ''
                if package_categories:
                    package_categories = package_categories.strip('"[],').split('","')
                    package['topicCategories'] = ';'.join(package_categories)

                result.append(package)
        return result

    # this code is defunct and will need to be refactored into cli.py
    """
    def jsonl_export(self):

        '''
        cron job
        paster --plugin=ckanext-geodatagov geodatagov jsonl-export --config=/etc/ckan/production.ini
        '''

        PAGINATION_SIZE = 1000

        # write to a temp file
        DIR_JSONL = "/tmp/jsonl/"
        if not os.path.exists(DIR_JSONL):
            os.makedirs(DIR_JSONL)
        fd, path = mkstemp(suffix=".json", prefix="jsonl-", dir=DIR_JSONL)
        fd_gz, path_gz = mkstemp(suffix=".json.gz", prefix="jsonl-", dir=DIR_JSONL)

        context = {}
        fq = 'collection_package_id: * OR *:* AND type:dataset AND organization_type:"Federal Government"'
        data_dict = {
            'fq': fq,
            'rows': 0
        }
        query = p.toolkit.get_action('package_search')(context, data_dict)

        count = query['count']
        pages = int(math.ceil(old_div(1.0 * count, PAGINATION_SIZE)))

        message = '{0:.19} jsonl is being generated, {1} pages, total {2} datasets to go.'.format(
            str(datetime.datetime.now()),
            pages,
            count
        )
        print(message)
        for i in range(pages):
            message = '{0:.19} doing page {1}/{2}...'.format(
                str(datetime.datetime.now()),
                i + 1,
                pages
            )
            print(message)

            data_dict = {
                'fq': fq,
                'rows': PAGINATION_SIZE,
                'start': i * PAGINATION_SIZE
            }
            attempts = 1
            while attempts < 50:
                try:
                    query = p.toolkit.get_action('package_search')(context, data_dict)
                except KeyboardInterrupt:
                    raise
                except BaseException:
                    log.error("Unexpected error: %s", sys.exc_info()[0])
                else:
                    datasets = query['results']
                    break
                wait_time = 2 * attempts  # wait longer with each failed attempt
                log.info('wait %s seconds before next attempt...' % wait_time)
                time.sleep(wait_time)
                attempts += 1

            for n, dataset in enumerate(datasets):
                os.write(fd, ('%s\n' % json.dumps(dataset)).encode('utf-8'))

        os.close(fd)
        os.close(fd_gz)

        print('Compressing ...')

        with open(path, 'rb') as f_in, gzip.open(path_gz, 'wb') as f_out:
            copyfileobj(f_in, f_out)

        bucket_name = config.get('ckanext.geodatagov.aws_bucket_name', None)
        if bucket_name is not None:
            print('Sending to s3 ...')
            bucket = get_s3_bucket(bucket_name)
            bucket_path = config.get('ckanext.geodatagov.jsonlexport.aws_storage_path', '')
            # TODO: archive old keys
            # bucket.copy_key('foo/file.tgz', 'somebucketname', bucket_path + 'dataset.jsonl.gz')
            upload_to_key(bucket, path_gz, bucket_path + 'dataset.jsonl.gz')
            # just remove if it was moved to AWS
            os.remove(path)
            os.remove(path_gz)
        else:
            print("No AWS destination, saved at: {}, {}".format(path, path_gz))

        print('{0:.19} Done.'.format(str(datetime.datetime.now())))

        # for local tests, return paths
        if bucket_name is None:
            return path, path_gz
        else:
            return None
    """

    # this code is defunct and will need to be refactored into cli.py
    """
    def metrics_csv(self):
        print(str(datetime.datetime.now()) + ' metrics_csv is being generated...')

        # cron job
        # paster --plugin=ckanext-geodatagov geodatagov metrics_csv --config=/etc/ckan/production.ini

        today = datetime.datetime.today().date()
        first_of_month = today.replace(day=1)
        end_date = first_of_month - datetime.timedelta(days=1)

        start_date_approximate = end_date - datetime.timedelta(days=85)
        start_date = start_date_approximate.replace(day=1)

        print(("starting date: ", start_date))
        print(("end date: ", end_date))

        fd, path = mkstemp(suffix=".csv", prefix="metrics")

        sql_METRICS_CSV = '''
                SELECT package_id,
                       p.title AS "Dataset Title",
                       g.title AS "Organization Name",
                       sum(count) AS "Views per Month",
                       to_char(tracking_date, 'MM-YYYY') AS "Date",
                       to_char(tracking_date, 'YYYY-MM') AS "Date2"
                FROM tracking_summary ts
                INNER JOIN package p ON p.id = ts.package_id
                INNER JOIN public.group g ON g.id = p.owner_org
                WHERE tracking_date >= :start_date AND tracking_date <= :end_date
                GROUP BY 1, 2, 3, 5, 6 HAVING sum(count) > 0
                ORDER BY to_char(tracking_date, 'YYYY-MM') DESC, p.title;
                '''

        metrics_csv = model.Session.execute(sql_METRICS_CSV, {'start_date': start_date, 'end_date': end_date})

        with os.fdopen(fd, "w") as write_file:
            csv_writer = csv.writer(write_file)
            header_row = ["Package Id", "Dataset Title", "Organiation Name", "Views per Month", "Date", "Date2"]
            csv_writer.writerow(header_row)
            for row in metrics_csv:
                new_row = []
                for r in row:
                    try:
                        new_row.append(r.encode('utf8'))
                    except BaseException:
                        new_row.append(r)
                csv_writer.writerow(new_row)

        print('Send to S3...')

        bucket_name = config.get('ckanext.geodatagov.aws_bucket_name')
        bucket_path = config.get('ckanext.geodatagov.metrics_csv.aws_storage_path', '')
        bucket = get_s3_bucket(bucket_name)

        upload_to_key(bucket, path,
                      '%smetrics-%s.csv' % (bucket_path, end_date))

        os.remove(path)

        print(str(datetime.datetime.now()) + ' Done.')
        """

    def update_dataset_geo_fields(self):
        """ Re-index dataset with geofields
            Catalog-classic use `spatial` field with string values (like _California_) or
            raw coordinates (like _-17.4,34.2,-17.1,24.6_). Catalog-next take this data and
            transform it into a valid GeoJson polygon (with the `translate_spatial` function).
            On `package_create` or `package_update` this transformation will happend but
            datasets already harvested will not be updated automatically.
            """

        # iterate over all datasets

        search_backend = config.get('ckanext.spatial.search_backend', 'postgis')
        if search_backend != 'solr-bbox':
            raise ValueError('Solr is not your default search backend (ckanext.spatial.search_backend)')

        datasets = model.Session.query(model.Package).all()
        total = len(datasets)
        print('Transforming {} datasets.'.format(total))
        c = 0
        transformed = 0
        failed = 0
        skipped = 0
        results = {
            'datasets': {}
        }
        for dataset in datasets:
            c += 1
            print('Transforming {}/{}: {}. {} skipped, {} failed, {} transformed'.
                  format(c, total, dataset.name, skipped, failed, transformed))
            results['datasets'][dataset.id] = {'name': dataset.name}
            dataset_dict = dataset.as_dict()
            extras = dataset_dict['extras']
            rolled_up = extras.get('extras_rollup', None)
            if rolled_up is None:
                results['datasets'][dataset.id]['skip'] = 'No rolled up extras'
                skipped += 1
                continue
            new_extras_rollup = json.loads(rolled_up)

            old_spatial = new_extras_rollup.get('spatial', None)
            if old_spatial is None:
                results['datasets'][dataset.id]['skip'] = 'No rolled up spatial extra found'
                skipped += 1
                continue
            print(' - Old Spatial found "{}"'.format(old_spatial))

            try:
                # check if already we have spatial valid data
                json.loads(old_spatial)
                results['datasets'][dataset.id]['spatial-already-done'] = old_spatial
                skipped += 1
                continue
            except BaseException:
                pass

            # update package, the translate_spatial function will fix spatial data
            context = {'user': self.user_name, 'ignore_auth': True}
            old_pkg = p.toolkit.get_action('package_show')(context, {'id': dataset.id})
            pkg_dict = p.toolkit.get_action('package_update')(context, old_pkg)

            # check the results
            extras = pkg_dict['extras']
            new_spatial = None
            for extra in extras:
                if extra['key'] == 'spatial':
                    if old_spatial != extra['value']:
                        transformed += 1
                        new_spatial = extra['value']
                        results['datasets'][dataset.id]['transformation'] = [old_spatial, new_spatial]
                    else:
                        results['datasets'][dataset.id]['transformation'] = [old_spatial, 'not found']

            if new_spatial is None:
                failed += 1
                new_spatial = '**** NOT FOUND ****'

            print(' - NEW Spatial: "{}"'.format(new_spatial))

        print('Final results {} total datasets. {} skipped, {} failed, {} transformed'.
              format(total, skipped, failed, transformed))

        results.update({
            'total': c,
            'transformed': transformed,
            'skipped': skipped,
            'failed': failed
        })
        return results


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
