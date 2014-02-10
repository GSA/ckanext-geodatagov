import collections
import os
import sys
import re
import csv
import datetime
import json
import urllib
import lxml.etree
import ckan
import ckan.model as model
import ckan.logic as logic
import ckan.lib.search as search
import ckan.logic.schema as schema
import ckan.lib.cli as cli
import requests
import ckanext.harvest.model as harvest_model
import xml.etree.ElementTree as ET
import ckan.lib.munge as munge
import ckan.plugins as p
from ckanext.geodatagov.harvesters.arcgis import _slugify


import logging
log = logging.getLogger()

class GeoGovCommand(cli.CkanCommand):
    '''
    Commands:

        paster geodatagov import-harvest-source <harvest_source_data> -c <config>
        paster geodatagov import-orgs <data> -c <config>
        paster geodatagov post-install-dbinit -c <config>
        paster geodatagov import-dms -c <config>
        paster geodatagov clean-deleted -c <config>
        paster geodatagov solr-tracking-update <tracking_start_date> -c <config>
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
        if cmd == 'solr-tracking-update':
            start_date = self.args[1] if len(self.args) > 1 else None
            self.solr_tracking_update(start_date)

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
        error_log = file('harvest_source_import_errors.txt' , 'w+')

        fields = ['DOCUUID', 'TITLE', 'OWNER', 'APPROVALSTATUS', 'HOST_URL',
        'PROTOCAL', 'PROTOCOL_TYPE', 'FREQUENCY', 'ORGID']

        user = logic.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})

        harvest_sources = open(sources_location)
        try:
            csv_reader = csv.reader(harvest_sources)
            for row in csv_reader:
                row = dict(zip(fields,row))

                ## neeeds some fix
                #if row['PROTOCOL_TYPE'].lower() not in ('waf', 'csw', 'z3950'):
                    #continue

                #frequency = row['FREQUENCY'].upper()
                #if frequency not in ('WEEKLY', 'MONTHLY', 'BIWEEKLY'):

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
            row = dict(zip(fields,row))
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
                logic.get_action('package_delete')(context, {"id":package_id})
            except Exception, e:
                print str(datetime.datetime.now()) + ' Error when deleting id ' + package_id
                print e


    def clean_deleted(self):
        print str(datetime.datetime.now()) + ' Starting delete'
        sql = '''begin; update package set state = 'to_delete' where state <> 'active' and revision_id in (select id from revision where timestamp < now() - interval '1 day');
        update package set state = 'to_delete' where owner_org is null;
        delete from package_role where package_id in (select id from package where state = 'to_delete' );
        delete from user_object_role where id not in (select user_object_role_id from package_role) and context = 'Package';
        delete from resource_revision where resource_group_id in (select id from resource_group where package_id in (select id from package where state = 'to_delete'));
        delete from resource_group_revision where package_id in (select id from package where state = 'to_delete');
        delete from package_tag_revision where package_id in (select id from package where state = 'to_delete');
        delete from member_revision where table_id in (select id from package where state = 'to_delete');
        delete from package_extra_revision where package_id in (select id from package where state = 'to_delete');
        delete from package_revision where id in (select id from package where state = 'to_delete');
        delete from package_tag where package_id in (select id from package where state = 'to_delete');
        delete from resource where resource_group_id in (select id from resource_group where package_id in (select id from package where state = 'to_delete'));
        delete from package_extra where package_id in (select id from package where state = 'to_delete');
        delete from member where table_id in (select id from package where state = 'to_delete');
        delete from resource_group where package_id  in (select id from package where state = 'to_delete');

        delete from harvest_object_error hoe using harvest_object ho where ho.id = hoe.harvest_object_id and package_id  in (select id from package where state = 'to_delete');
        delete from harvest_object_extra hoe using harvest_object ho where ho.id = hoe.harvest_object_id and package_id  in (select id from package where state = 'to_delete');
        delete from harvest_object where package_id in (select id from package where state = 'to_delete');

        delete from package where id in (select id from package where state = 'to_delete'); commit;'''
        model.Session.execute(sql)
        print str(datetime.datetime.now()) + ' Finished delete'


    def solr_tracking_update(self, start_date=None):
        if start_date:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        else:
            # No date given. See when we last have data for and get data
            # from 2 days before then in case new data is available.
            # If no date here then use 2013-09-01 as the start date
            sql = '''SELECT tracking_date from tracking_summary
                     ORDER BY tracking_date DESC LIMIT 1;'''
            result = model.Session.execute(sql).fetchall()
            if result:
                start_date = result[0]['tracking_date']
                start_date += datetime.timedelta(-2)
            else:
                start_date = '2013-09-01'

        sql = '''SELECT package_id FROM tracking_summary
                where package_id!='~~not~found~~'
                and tracking_date >= :start_date;'''
        q = model.Session.execute(sql, {'start_date': start_date})

        package_ids = set()
        for row in q:
            package_ids.add(row['package_id'])

        total = len(package_ids)
        not_found = 0
        print 'updating %i records on solr starting from %s' % (total, start_date)
        for index, package_id in enumerate(package_ids):
            print "updating %i/%i %s ..." % (index+1, total, package_id),
            try:
                search.rebuild(package_id)
            except ckan.logic.NotFound:
                print "Error: Not Found."
                not_found += 1
            except KeyboardInterrupt:
                print "Stopped."
                return
            except:
                raise
            else:
                print "Done."
        print 'All Done!' + " %i Not Found." % (not_found) if not_found else ""
#set([u'feed', u'webService', u'issued', u'modified', u'references', u'keyword', u'size', u'landingPage', u'title', u'temporal', u'theme', u'spatial', u'dataDictionary', u'description', u'format', u'granularity', u'accessLevel', u'accessURL', u'publisher', u'language', u'license', u'systemOfRecords', u'person', u'accrualPeriodicity', u'dataQuality', u'distribution', u'identifier', u'mbox'])


#{u'title': 6061, u'theme': 6061, u'accessLevel': 6061, u'publisher': 6061, u'identifier': 6061, u'description': 6060, u'accessURL': 6060, u'distribution': 6060, u'keyword': 6059, u'person': 6057, u'accrualPeriodicity': 6056, u'format': 6047, u'spatial': 6009, u'size': 5964, u'references': 5841, u'dataDictionary': 5841, u'temporal': 5830, u'modified': 5809, u'issued': 5793, u'mbox': 5547, u'granularity': 4434, u'license': 2048, u'dataQuality': 453}


