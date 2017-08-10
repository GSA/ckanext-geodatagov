import csv
import datetime
import json
import xml.etree.ElementTree as ET
from urllib2 import Request, urlopen, URLError, HTTPError
from tempfile import mkstemp
import boto
import mimetypes
import hashlib
import base64

import time

import math

import logging
import gzip
from shutil import copyfile, copyfileobj

import os
import re
import ckan
import ckan.model as model
import ckan.logic as logic
import ckan.lib.search as search
import ckan.logic.schema as schema
import ckan.lib.cli as cli
import ckan.lib.helpers as h
import requests
from ckanext.harvest.model import HarvestSource, HarvestJob, HarvestSystemInfo
import ckan.lib.munge as munge
from pylons import config
from ckan import plugins as p
from ckanext.geodatagov.model import MiscsFeed, MiscsTopicCSV

log = logging.getLogger()
ckan_tmp_path = '/var/tmp/ckan'

class GeoGovCommand(cli.CkanCommand):
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
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__

    def command(self):
        '''
        Parse command line arguments and call appropriate method.
        '''
        if not self.args or self.args[0] in ['--help', '-h', 'help']:
            print GeoGovCommand.__doc__
            return

        cmd = self.args[0]
        self._load_config()

        user = logic.get_action('get_site_user')(
            {'model': model, 'ignore_auth': True}, {}
        )
        self.user_name = user['name']

        if cmd == 'import-harvest-source':
            if not len(self.args) in [2]:
                print GeoGovCommand.__doc__
                return

            self.import_harvest_source(self.args[1])

        if cmd == 'import-orgs':
            if not len(self.args) in [2, 3]:
                print GeoGovCommand.__doc__
                return

            self.import_organizations(self.args[1])
        if cmd == 'import-dms':
            if not len(self.args) in [2]:
                print GeoGovCommand.__doc__
                return
            self.import_dms(self.args[1])
        if cmd == 'import-doi':
            self.import_doi()
        if cmd == 'post-install-dbinit':
            f = open('/usr/lib/ckan/src/ckanext-geodatagov/what_to_alter.sql')
            print "running what_to_alter.sql"
            test = model.Session.execute(f.read())
            f = open('/usr/lib/ckan/src/ckanext-geodatagov/constraints.sql')
            print "running constraints.sql"
            test = model.Session.execute(f.read())
            model.Session.commit()
            print "Success"
        if cmd == 'clean-deleted':
            self.clean_deleted()
        if cmd == 'db_solr_sync':
            self.db_solr_sync()
        if cmd == 'combine-feeds':
            self.combine_feeds()
        if cmd == 'harvest-job-cleanup':
            self.harvest_job_cleanup()
        if cmd == 'harvest-object-relink':
            harvest_source_id = None
            if len(self.args) == 2:
                harvest_source_id = self.args[1]
            self.harvest_object_relink(harvest_source_id)
        if cmd == 'export-csv':
            self.export_csv()
        if cmd == 'sitemap-to-s3':
            self.sitemap_to_s3()
        if cmd == 'jsonl-export':
            self.jsonl_export()

    def get_user_org_mapping(self, location):
        user_org_mapping = open(location)
        fields = ['user', 'org']
        csv_reader = csv.reader(user_org_mapping)
        mapping = {}
        for row in csv_reader:
            mapping[row[0].lower()] = row[1]
        return mapping

    def import_harvest_source(self, sources_location):
        '''Import data from this mysql command
select DOCUUID, TITLE, OWNER, APPROVALSTATUS, HOST_URL, Protocol, PROTOCOL_TYPE, FREQUENCY, USERNAME into outfile '/tmp/results_with_user.csv' from GPT_RESOURCE join GPT_USER on owner = USERID where frequency is not null;
'''
        error_log = file('harvest_source_import_errors.txt', 'w+')

        fields = ['DOCUUID', 'TITLE', 'OWNER', 'APPROVALSTATUS', 'HOST_URL',
                  'PROTOCAL', 'PROTOCOL_TYPE', 'FREQUENCY', 'ORGID']

        user = logic.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})

        harvest_sources = open(sources_location)
        try:
            csv_reader = csv.reader(harvest_sources)
            for row in csv_reader:
                row = dict(zip(fields, row))

                ## neeeds some fix
                # if row['PROTOCOL_TYPE'].lower() not in ('waf', 'csw', 'z3950'):
                # continue

                # frequency = row['FREQUENCY'].upper()
                # if frequency not in ('WEEKLY', 'MONTHLY', 'BIWEEKLY'):

                frequency = 'MANUAL'

                config = {
                    'ORIGINAL_UUID': row['DOCUUID'][1:-1].lower()
                }

                protocal = row['PROTOCAL']
                protocal = protocal[protocal.find('<protocol'):]
                import re

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
                    harvest_source = logic.get_action('harvest_source_create')(
                        {'model': model, 'user': user['name'],
                         'session': model.Session, 'api_version': 3},
                        harvest_source_dict
                    )
                except ckan.logic.ValidationError, e:
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
            row = dict(zip(fields, row))
            org = logic.get_action('organization_create')(
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

        user = logic.get_action('get_site_user')(
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
                print str(datetime.datetime.now()) + ' Created id ' + package_id
                logic.get_action('datajson_create')(context, new_package)
            except Exception, e:
                print str(datetime.datetime.now()) + ' Error when creating id ' + package_id
                print e

        for package_id in collected_ids & existing_package_ids:
            context.pop('package', None)
            context.pop('group', None)
            new_package = to_import[package_id]
            try:
                logic.get_action('datajson_update')(context, new_package)
            except Exception, e:
                print str(datetime.datetime.now()) + ' Error when updating id ' + package_id
                print e
        for package_id in existing_package_ids - collected_ids:
            context.pop('package', None)
            context.pop('group', None)
            try:
                logic.get_action('package_delete')(context, {"id": package_id})
            except Exception, e:
                print str(datetime.datetime.now()) + ' Error when deleting id ' + package_id
                print e

    def import_doi(self):
        doi_url = config.get('ckanext.geodatagov.doi.url', '')
        if not doi_url:
            print 'ckanext.geodatagov.doi.url not defined in config.'
            return

        url_list = doi_url + 'api/search/dataset?qjson={"fl":"id,extras_harvest_object_id","q":"harvest_object_id:[\\\"\\\"%20TO%20*],%20metadata_type:geospatial","sort":"id%20asc","start":0,"limit":0}'
        url_dataset = doi_url + 'api/action/package_show?id='
        url_harvestobj = doi_url + 'harvest/object/'

        try:
            requested = requests.get(url_list, verify=False).json()
        except Exception, e:
            print str(datetime.datetime.now()) + ' Error when accessing doi list at ' + url_list
            print e
        total = requested['count']
        pagination = 1000
        to_import = {}
        for page in xrange(0, int(math.ceil(float(total) / pagination)) + 1):
            url_list_dataset = ""
            input_records = []
            start = page * pagination
            url_list_dataset = url_list.replace('"limit":0', '"limit":1000')
            url_list_dataset = url_list_dataset.replace('"start":0', '"start":' + str(start))
            try:
                input_records = requests.get(url_list_dataset, verify=False).json()
            except Exception, e:
                print str(datetime.datetime.now()) + ' Error when accessing doi list at ' + url_list
                print e
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
        user = logic.get_action('get_site_user')(
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

        print str(datetime.datetime.now()) + ' Start to import doi datasets.'
        print 'Datasets found on remote doi server: ' + str(len(collected_ids)) + ', on local: ' + str(
            len(existing_ids)) + '.'

        ids_to_add = collected_ids - existing_ids
        print 'Datasets to be added as new: ' + str(len(ids_to_add)) + '.'
        for num, doi_id in enumerate(ids_to_add):
            context.pop('package', None)
            context.pop('group', None)
            try:
                new_package = self.get_doi_package(url_dataset + doi_id)
                new_harvestobj = self.get_doi_harvestobj(url_harvestobj + to_import[doi_id])
            except Exception, e:
                print str(
                    datetime.datetime.now()) + ' Error when downlaoding doi id ' + doi_id + ' and harvest object ' + \
                      to_import[doi_id]
                print e

            context['harvestobj'] = new_harvestobj
            try:
                logic.get_action('doi_create')(context, new_package)
            except Exception, e:
                print str(datetime.datetime.now()) + ' Error when importing doi id ' + doi_id
                print e

        ids_to_update = collected_ids & existing_ids
        print 'Datasets to check for update: ' + str(len(ids_to_update)) + '.'
        for num, doi_id in enumerate(ids_to_update):
            context.pop('package', None)
            context.pop('group', None)
            try:
                new_package = self.get_doi_package(url_dataset + doi_id)
                new_harvestobj = self.get_doi_harvestobj(url_harvestobj + to_import[doi_id])
            except Exception, e:
                print str(
                    datetime.datetime.now()) + ' Error when downlaoding doi id ' + doi_id + ' and harvest object ' + \
                      to_import[doi_id]
                print e
            context['harvestobj'] = new_harvestobj
            try:
                logic.get_action('doi_update')(context, new_package)
            except Exception, e:
                print str(datetime.datetime.now()) + ' Error when updating doi id ' + doi_id
                print e

        ids_to_delete = existing_ids - collected_ids
        print 'Datasets to be deleted: ' + str(len(ids_to_delete)) + '.'
        for num, doi_id in enumerate(ids_to_delete):
            context.pop('package', None)
            context.pop('group', None)
            try:
                logic.get_action('package_delete')(context, {"id": doi_id})
                print str(datetime.datetime.now()) + ' Deleted doi id ' + doi_id
            except Exception, e:
                print str(datetime.datetime.now()) + ' Error when deleting doi id ' + doi_id
                print e

    def get_doi_package(self, url_dataset):
        dataset = requests.get(url_dataset, verify=False).json()
        dataset = dataset['result']
        return dataset

    def get_doi_harvestobj(self, url_harvestobj):
        harvestobj = requests.get(url_harvestobj, verify=False)
        return harvestobj.text

    def clean_deleted(self):
        print str(datetime.datetime.now()) + ' Starting delete'
        sql = '''begin; update package set state = 'to_delete' where state <> 'active' and revision_id in (select id from revision where timestamp < now() - interval '1 day');
        update package set state = 'to_delete' where owner_org is null;
        delete from package_role where package_id in (select id from package where state = 'to_delete' );
        delete from user_object_role where id not in (select user_object_role_id from package_role) and context = 'Package';
        delete from resource_revision where package_id in (select id from package where state = 'to_delete' );
        delete from package_tag_revision where package_id in (select id from package where state = 'to_delete');
        delete from member_revision where table_id in (select id from package where state = 'to_delete');
        delete from package_extra_revision where package_id in (select id from package where state = 'to_delete');
        delete from package_revision where id in (select id from package where state = 'to_delete');
        delete from package_tag where package_id in (select id from package where state = 'to_delete');
        delete from resource_view where resource_id in (select id from resource where package_id in (select id from package where state = 'to_delete'));
        delete from resource where package_id in (select id from package where state = 'to_delete');
        delete from package_extra where package_id in (select id from package where state = 'to_delete');
        delete from member where table_id in (select id from package where state = 'to_delete');

        delete from harvest_object_error hoe using harvest_object ho where ho.id = hoe.harvest_object_id and package_id  in (select id from package where state = 'to_delete');
        delete from harvest_object_extra hoe using harvest_object ho where ho.id = hoe.harvest_object_id and package_id  in (select id from package where state = 'to_delete');
        delete from harvest_object where package_id in (select id from package where state = 'to_delete');

        delete from package where id in (select id from package where state = 'to_delete'); commit;'''
        model.Session.execute(sql)
        print str(datetime.datetime.now()) + ' Finished delete'

    # set([u'feed', u'webService', u'issued', u'modified', u'references', u'keyword', u'size', u'landingPage', u'title', u'temporal', u'theme', u'spatial', u'dataDictionary', u'description', u'format', u'granularity', u'accessLevel', u'accessURL', u'publisher', u'language', u'license', u'systemOfRecords', u'person', u'accrualPeriodicity', u'dataQuality', u'distribution', u'identifier', u'mbox'])


    # {u'title': 6061, u'theme': 6061, u'accessLevel': 6061, u'publisher': 6061, u'identifier': 6061, u'description': 6060, u'accessURL': 6060, u'distribution': 6060, u'keyword': 6059, u'person': 6057, u'accrualPeriodicity': 6056, u'format': 6047, u'spatial': 6009, u'size': 5964, u'references': 5841, u'dataDictionary': 5841, u'temporal': 5830, u'modified': 5809, u'issued': 5793, u'mbox': 5547, u'granularity': 4434, u'license': 2048, u'dataQuality': 453}


    def db_solr_sync(self):

        print str(datetime.datetime.now()) + ' Entering Database Solr Sync function.'

        url = config.get('solr_url') + "/select?q=*%3A*&sort=id+asc&fl=id%2Cmetadata_modified&wt=json&indent=true"
        response = get_response(url)

        if (response != 'error'):

            print str(datetime.datetime.now()) + ' Deleting records from miscs_solr_sync.'
            sql = '''delete from miscs_solr_sync'''
            model.Session.execute(sql)
            model.Session.commit()

            f = response.read()
            data = json.loads(f)
            rows = data.get('response').get('numFound')

            start = 0
            chunk_size = 1000

            print str(datetime.datetime.now()) + ' Starting insertion of records in miscs_solr_sync .'

            for x in range(0, int(math.ceil(rows / chunk_size)) + 1):

                if (x == 0):
                    start = 0

                print str(datetime.datetime.now()) + ' Fetching ' + url + "&rows=" + str(chunk_size) + "&start=" + str(
                    start)

                response = get_response(url + "&rows=" + str(chunk_size) + "&start=" + str(start))
                f = response.read()
                data = json.loads(f)
                results = data.get('response').get('docs')

                print str(datetime.datetime.now()) + ' Inserting ' + str(start) + ' - ' + str(
                    start + int(data.get('responseHeader').get('params').get('rows')) - 1) + ' of ' + str(rows)

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
                            if (str(results[x]['metadata_modified'])[:19] != pkg_dict['metadata_modified'][:19]):
                                print str(datetime.datetime.now()) + ' Action Type : outsync for Package Id: ' + \
                                      results[x]['id']
                                print ' ' * 26 + ' Modified Date from Solr: ' + str(results[x]['metadata_modified'])
                                print ' ' * 26 + ' Modified Date from Db: ' + pkg_dict['metadata_modified']
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

            print str(datetime.datetime.now()) + ' Starting Database to Solr Sync'

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
                    print str(datetime.datetime.now()) + ' Building Id: ' + pkg_id
                    search.rebuild(pkg_id)
                except ckan.logic.NotFound:
                    print "Error: Not Found."
                except KeyboardInterrupt:
                    print "Stopped."
                    return
                except:
                    raise

            sql = '''Select pkg_id from miscs_solr_sync where action = 'outsync'; '''
            q = model.Session.execute(sql)
            pkg_ids = set()
            for row in q:
                pkg_ids.add(row['pkg_id'])
            for pkg_id in pkg_ids:
                try:
                    print str(datetime.datetime.now()) + ' Rebuilding Id: ' + pkg_id
                    search.rebuild(pkg_id)
                except ckan.logic.NotFound:
                    print "Error: Not Found."
                except KeyboardInterrupt:
                    print "Stopped."
                    return
                except:
                    raise

            print str(datetime.datetime.now()) + ' Starting Solr to Database Sync'

            sql = '''Select pkg_id from miscs_solr_sync where action = 'notfound'; '''
            q = model.Session.execute(sql)
            pkg_ids = set()
            for row in q:
                pkg_ids.add(row['pkg_id'])
            for pkg_id in pkg_ids:
                try:
                    search.clear(pkg_id)
                except ckan.logic.NotFound:
                    print "Error: Not Found."
                except KeyboardInterrupt:
                    print "Stopped."
                    return
                except:
                    raise

            print str(datetime.datetime.now()) + " All Sync Done."

    def combine_feeds(self):
        from xml.dom import minidom
        from xml.parsers.expat import ExpatError
        import urllib
        import codecs

        feed_url = config.get('ckan.site_url') + '/feeds/dataset.atom'
        # from http://boodebr.org/main/python/all-about-python-and-unicode#UNI_XML
        RE_XML_ILLEGAL = u'([\u0000-\u0008\u000b-\u000c\u000e-\u001f\ufffe-\uffff])' + \
                         u'|' + \
                         u'([%s-%s][^%s-%s])|([^%s-%s][%s-%s])|([%s-%s]$)|(^[%s-%s])' % \
                         (unichr(0xd800), unichr(0xdbff), unichr(0xdc00), unichr(0xdfff),
                          unichr(0xd800), unichr(0xdbff), unichr(0xdc00), unichr(0xdfff),
                          unichr(0xd800), unichr(0xdbff), unichr(0xdc00), unichr(0xdfff))

        def get_dom(url):
            retry = 5
            delay = 3
            while retry > 0:
                print '%s fetching %s' % (datetime.datetime.now(), url)
                try:
                    xml = urllib.urlopen(url_page_feed).read()
                    xml = re.sub(RE_XML_ILLEGAL, "?", xml)
                    dom = minidom.parseString(xml)
                except ExpatError:
                    print 'retry url: %s' % url
                    print 'deplay %s seconds...' % (delay ** (6 - retry))
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

        print '%s combined feeds updated' % datetime.datetime.now()


    def harvest_job_cleanup(self):
        msg = ''
        msg += str(datetime.datetime.now()) + ' Clean up stuck harvest jobs.\n'

        # is harvest job running regularly?
        from sqlalchemy.exc import ProgrammingError
        harvest_system_info = None
        try:
            harvest_system_info = model.Session.query(HarvestSystemInfo).filter_by(key='last_run_time').first()
        except ProgrammingError:
            msg += 'No HarvestSystemInfo table defined.'
            print msg
            email_log('harvest-job-cleanup', msg)
            return

        if not harvest_system_info:
            msg += 'Harvester is not running.'
            print msg
            email_log('harvest-job-cleanup', msg)
            return

        last_run_time = harvest_system_info.value
        last_run_time = time.mktime(time.strptime(last_run_time, '%Y-%m-%d %H:%M:%S.%f'))
        time_current = time.time()
        if (time_current - last_run_time) > 3600:
            msg += 'Harvester is not running, or not frequently enough.\n'
            print msg
            email_log('harvest-job-cleanup', msg)
            return

        harvest_pairs_1 = [] # stuck jobs with harvest objects
        harvest_pairs_2 = [] # stuck jobs without harvest objects
        # find those stuck jobs with harvest source
        create_time_limit = '12 hours'
        fetch_time_limit = '6 hours'
        sql = '''
            SELECT
                harvest_source_id, harvest_job_id
            FROM
              harvest_object
            WHERE
              harvest_job_id IN (
                SELECT id
                FROM harvest_job
                WHERE
                  status = 'Running'
                AND (
                  created IS NULL
                  OR
                  created < CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - INTERVAL :create_time_limit
                )
              )
              GROUP BY
                harvest_source_id, harvest_job_id
              HAVING
                MAX(import_finished) IS NULL
              OR
                MAX(import_finished) < CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - INTERVAL :fetch_time_limit
        '''
        results = model.Session.execute(sql, {
            'create_time_limit': create_time_limit,
            'fetch_time_limit': fetch_time_limit,
        })
        for row in results:
            harvest_pairs_1.append({
                'harvest_source_id': row['harvest_source_id'],
                'harvest_job_id': row['harvest_job_id']
            })

        # mark stuck harvest objects, and secretly truncate to minute
        # precision so that we can indentify them on UI.
        sql = '''
            UPDATE
                harvest_object
            SET
                state = 'STUCK',
                import_finished = date_trunc('minute',
                        CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
            WHERE
                state NOT IN ('COMPLETE', 'ERROR', 'STUCK')
            AND
                harvest_job_id = :harvest_job_id
        '''

        for item in harvest_pairs_1:
            model.Session.execute(sql, {'harvest_job_id': item['harvest_job_id']})
            model.Session.commit()

        # some may not even have harvest objects
        sql = '''
            SELECT
              harvest_job.source_id AS harvest_source_id,
              harvest_job.id AS harvest_job_id
            FROM
              harvest_job
            LEFT JOIN
              harvest_object
            ON
              harvest_job.id = harvest_object.harvest_job_id
            WHERE
              harvest_object.id is NULL
            AND
              harvest_job.status = 'Running'
            AND (
              harvest_job.created IS NULL
              OR
              harvest_job.created < CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - INTERVAL :create_time_limit
            )
        '''
        results = model.Session.execute(sql, {
            'create_time_limit': create_time_limit,
        })
        for row in results:
            harvest_pairs_2.append({
                'harvest_source_id': row['harvest_source_id'],
                'harvest_job_id': row['harvest_job_id']
            })

        # secretly truncate to minute precision to indicate a reset job.
        sql = '''
            UPDATE
                harvest_job
            SET
                status = 'Finished',
                finished = date_trunc('minute', CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
            WHERE
                id = :harvest_job_id
        '''

        for item in harvest_pairs_1 + harvest_pairs_2:
            model.Session.execute(sql, {'harvest_job_id': item['harvest_job_id']})
            model.Session.commit()
            if item in harvest_pairs_1:
                self.harvest_object_relink(item['harvest_source_id'])

            source_package = p.toolkit.get_action('harvest_source_show')({},
                    {'id': item['harvest_source_id']})
            source_info = ('organization: {0}, title: {1}, name: {2}, id: {3},'
                    ' frequency: {4}, last_job_finished: {5}').format(
                        source_package['organization']['title'] + " (" + \
                                source_package['organization']['name'] + ")",
                        source_package['title'],
                        source_package['name'],
                        source_package['id'],
                        source_package['frequency'],
                        "N/A" if not source_package['status'].get('last_job') \
                              else source_package['status']['last_job'].get('finished')
                    )
            msg += str(datetime.datetime.now()) + (' Harvest job %s was '
                    'forced to finish. Harvest source info: %s.\n\n') \
                    % (item['harvest_job_id'], source_info)

        if not (harvest_pairs_1 + harvest_pairs_2):
            msg += str(datetime.datetime.now()) + ' Nothing to do.\n'
        else:
            email_log('harvest-job-cleanup', msg)

        print msg

    def harvest_object_relink(self, harvest_source_id=None):
        print '%s: Fix packages which lost harvest objects for harvest source %s.' % \
                (datetime.datetime.now(), harvest_source_id if harvest_source_id else 'all')

        pkgs_problematic = set()
        # find packages that has no current harvest object
        sql = '''
            WITH temp_ho AS (
              SELECT DISTINCT package_id
                      FROM harvest_object
                      WHERE current
            )
            SELECT DISTINCT harvest_object.package_id
            FROM harvest_object
            LEFT JOIN temp_ho
            ON harvest_object.package_id = temp_ho.package_id
            WHERE
                temp_ho.package_id IS NULL
            AND
                harvest_object.state = 'COMPLETE'
        '''
        if harvest_source_id:
            sql += '''
            AND
                harvest_object.harvest_source_id = :harvest_source_id
            '''
            results = model.Session.execute(sql,
                    {'harvest_source_id': harvest_source_id})
        else:
            results = model.Session.execute(sql)

        for row in results:
            pkgs_problematic.add(row['package_id'])
        total = len(pkgs_problematic)
        print '%s packages to be fixed.' % total

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
        for id in pkgs_problematic:
            result = model.Session.execute(sql, {'id': id}).fetchall()
            model.Session.commit()
            count = count + 1
            if result:
                print '%s: %s/%s id %s fixed. Now pushing to solr... ' % (datetime.datetime.now(), count, total, id),
                try:
                    search.rebuild(id)
                except KeyboardInterrupt:
                    print "Stopped."
                    return
                except:
                    raise
                print 'Done.'
            else:
                print '%s: %s/%s id %s has no valid harvest object. Need to inspect mannully. ' % (
                    datetime.datetime.now(), count, total, id)

        if not pkgs_problematic:
            print '%s: All harvest objects look good. Nothing to do. ' % datetime.datetime.now()

    @staticmethod
    def export_group_and_tags(packages):
        domain = 'https://catalog.data.gov'
        result = []
        for pkg in packages:
            package = dict()

            package_groups = pkg.get('groups')
            if not package_groups:
                continue

            extras = dict([(x['key'], x['value']) for x in pkg['extras']])
            package['title'] = pkg.get('title').encode('ascii', 'xmlcharrefreplace')
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

    def export_csv(self):
        print 'export started...'

        # cron job
        # paster --plugin=ckanext-geodatagov geodatagov export-csv --config=/etc/ckan/production.ini

        # Exported CSV header list:
        # - Dataset Title
        # - Dataset URL
        # - Organization Name
        # - Organization Link
        # - Harvest Source Name
        # - Harvest Source Link
        # - Topic Name
        # - Topic Categories

        import io
        import csv

        limit = 100
        page = 1

        import pprint

        result = []

        while True:
            data_dict = {
                'q': 'groups:*',
                # 'fq': fq,
                # 'facet.field': facets.keys(),
                'rows': limit,
                # 'sort': sort_by,
                'start': (page - 1) * limit
                # 'extras': search_extras
            }

            query = logic.get_action('package_search')({'model': model, 'ignore_auth': True}, data_dict)

            page += 1
            # import pprint
            # pprint.pprint(packages)

            if not query['results']:
                break

            packages = query['results']
            result = result + GeoGovCommand.export_group_and_tags(packages)

        if not result:
            print 'nothing to do'
            return

        import datetime

        print 'writing into db...'

        date_suffix = datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d')
        csv_output = io.BytesIO()

        fieldnames = ['Dataset Title', 'Dataset URL', 'Organization Name', 'Organization Link',
                      'Harvest Source Name', 'Harvest Source Link', 'Topic Name', 'Topic Categories']
        writer = csv.writer(csv_output)
        writer.writerow(fieldnames)
        for pkg in result:
            try:
                writer.writerow(
                    [
                        pkg['title'],
                        pkg['url'],
                        pkg['organization'],
                        pkg['organizationUrl'],
                        pkg['harvestSourceTitle'],
                        pkg['harvestSourceUrl'],
                        pkg['topic'],
                        pkg['topicCategories']
                    ]
                )
            except UnicodeEncodeError:
                pprint.pprint(pkg)

        content = csv_output.getvalue()

        entry = model.Session.query(MiscsTopicCSV) \
                .filter_by(date=date_suffix) \
                .first()
        if not entry:
            # create the empty entry for the first time
            entry = MiscsTopicCSV()
            entry.date = date_suffix
        entry.csv = content
        entry.save()

        print 'csv file topics-%s.csv is ready.' % date_suffix

    def sitemap_to_s3(self):
        print str(datetime.datetime.now()) + ' sitemap is being generated...'

        # cron job
        # paster --plugin=ckanext-geodatagov geodatagov sitemap-to-s3 --config=/etc/ckan/production.ini
        # sql = '''Select id from package where id not in (select pkg_id from miscs_solr_sync); '''

        package_query = search.query_for(model.Package)
        count = package_query.get_count()
        if not count:
            print '0 record found.'
            return
        print '%i records to go.' % count

        start = 0
        page_size = 1000

        # write to a temp file
        DIR_S3SITEMAP = "/tmp/s3sitemap/"
        if not os.path.exists(DIR_S3SITEMAP):
            os.makedirs(DIR_S3SITEMAP)
        fd, path = mkstemp(suffix=".xml", prefix="sitemap-", dir=DIR_S3SITEMAP)
        fd_gz, path_gz = mkstemp(suffix=".xml.gz", prefix="sitemap-", dir=DIR_S3SITEMAP)
        # write header
        os.write(fd, '<?xml version="1.0" encoding="UTF-8"?>\n')
        os.write(fd, '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')

        for x in range(0, int(math.ceil(count / page_size)) + 1):
            pkgs = package_query.get_paginated_entity_name_modtime(
                max_results=page_size, start=start
            )

            for pkg in pkgs:
                os.write(fd, '    <url>\n')
                os.write(fd, '        <loc>%s</loc>\n' % (
                    config.get('ckan.site_url') + pkg.get('name'),
                ))
                os.write(fd, '        <lastmod>%s</lastmod>\n' % (
                    pkg.get('metadata_modified').strftime('%Y-%m-%d'),
                ))
                os.write(fd, '    </url>\n')
            print '%i to %i of %i records done.' % (
                start + 1, min(start + page_size, count), count
            )
            start = start + page_size

        # write footer
        os.write(fd, '</urlset>\n')
        os.close(fd)
        os.close(fd_gz)

        print 'compress and send to s3...'

        with open(path, 'rb') as f_in, gzip.open(path_gz, 'wb') as f_out:
            copyfileobj(f_in, f_out)

        bucket_name = config.get('ckanext.geodatagov.aws_bucket_name')
        bucket_path = config.get('ckanext.geodatagov.s3sitemap.aws_storage_path', '')

        bucket = get_s3_bucket(bucket_name)
        upload_to_key(bucket, path_gz, bucket_path + 'sitemap.xml.gz')

        os.remove(path)
        os.remove(path_gz)
        print str(datetime.datetime.now()) + ' Done.'


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
        fq = 'collection_package_id:* OR *:* AND type:dataset AND organization_type:"Federal Government"'
        data_dict = {
            'fq': fq,
            'rows': 0
        }
        query = p.toolkit.get_action('package_search')(context, data_dict)

        count = query['count']
        pages = int(math.ceil(1.0*count/PAGINATION_SIZE))

        message = '{0:.19} jsonl is being generated, {1} pages, total {2} datasets to go.'.format(
                    str(datetime.datetime.now()),
                    pages,
                    count
        )
        print message
        for i in range(pages):
            message = '{0:.19} doing page {1}/{2}...'.format(
                    str(datetime.datetime.now()),
                    i + 1,
                    pages
            )
            print message

            data_dict = {
                'fq': fq,
                'rows': PAGINATION_SIZE,
                'start': i * PAGINATION_SIZE
            }
            query = p.toolkit.get_action('package_search')(context, data_dict)
            datasets = query['results']

            for n, dataset in enumerate(datasets):
                os.write(fd, '%s\n' % dataset)

        os.close(fd)
        os.close(fd_gz)

        print 'compress and send to s3...'

        with open(path, 'rb') as f_in, gzip.open(path_gz, 'wb') as f_out:
            copyfileobj(f_in, f_out)

        bucket_name = config.get('ckanext.geodatagov.aws_bucket_name')
        bucket_path = config.get('ckanext.geodatagov.jsonlexport.aws_storage_path', '')
        bucket = get_s3_bucket(bucket_name)

        # TODO: archive old keys
        # bucket.copy_key('foo/file.tgz', 'somebucketname', bucket_path + 'dataset.jsonl.gz')

        upload_to_key(bucket, path_gz, bucket_path + 'dataset.jsonl.gz')

        os.remove(path)
        os.remove(path_gz)
        print '{0:.19} Done.'.format(str(datetime.datetime.now()))


def get_response(url):
    req = Request(url)
    try:
        response = urlopen(req)
    except HTTPError as e:
        print 'The server couldn\'t fulfill the request.'
        print 'Error code: ', e.code
        return 'error'
    except URLError as e:
        print 'We failed to reach a server.'
        print 'Reason: ', e.reason
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
    except Exception, e:
        log.error('Error: %s; email: %s' % (e, email))


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
            raise Exception('Could not find bucket {0}: {1}'.\
                    format(bucket_name, str(e)))
        elif e.status == 403:
            raise Exception('Access to bucket {0} denied'.\
                    format(bucket_name))
        else:
            raise

    return bucket


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


def upload_to_key(bucket, upload_filename, filename_on_s3):
    content_type, x = mimetypes.guess_type(upload_filename)
    headers = {}
    if content_type:
        headers.update({'Content-Type': content_type})
    k = boto.s3.key.Key(bucket)
    try:
        k.key = filename_on_s3
        k.set_contents_from_filename(
            upload_filename,
            headers = headers,
            md5 = generate_md5_for_s3(upload_filename)
        )
    except Exception as e:
        raise e
    finally:
        k.close()
