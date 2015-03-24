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
from ckanext.harvest.model import HarvestSource, HarvestJob
import xml.etree.ElementTree as ET
import ckan.lib.munge as munge
import ckan.plugins as p
from ckanext.geodatagov.harvesters.arcgis import _slugify
from pylons import config
from urllib2 import Request, urlopen, URLError, HTTPError
import time
import math

import logging
log = logging.getLogger()

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

    def import_doi(self):
        doi_url = config.get('ckanext.geodatagov.doi.url', '')
        if not doi_url:
            print 'ckanext.geodatagov.doi.url not defined in config.'
            return

        url_list =  doi_url + 'api/search/dataset?qjson={"fl":"id,extras_harvest_object_id","q":"harvest_object_id:[\\\"\\\"%20TO%20*],%20metadata_type:geospatial","sort":"id%20asc","start":0,"limit":0}'
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
        for page in xrange(0, int(math.ceil(float(total)/pagination)) + 1):
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
        source_id =  source_pkg.id
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
        print 'Datasets found on remote doi server: ' + str(len(collected_ids)) + ', on local: ' + str(len(existing_ids)) + '.'

        ids_to_add = collected_ids - existing_ids
        print 'Datasets to be added as new: ' + str(len(ids_to_add)) + '.'
        for num, doi_id in enumerate(ids_to_add):
            context.pop('package', None)
            context.pop('group', None)
            try:
                new_package = self.get_doi_package(url_dataset + doi_id)
                new_harvestobj = self.get_doi_harvestobj(url_harvestobj + to_import[doi_id])
            except Exception, e:
                print str(datetime.datetime.now()) + ' Error when downlaoding doi id ' + doi_id + ' and harvest object ' + to_import[doi_id]
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
                print str(datetime.datetime.now()) + ' Error when downlaoding doi id ' + doi_id + ' and harvest object ' + to_import[doi_id]
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
                logic.get_action('package_delete')(context, {"id":doi_id})
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

#set([u'feed', u'webService', u'issued', u'modified', u'references', u'keyword', u'size', u'landingPage', u'title', u'temporal', u'theme', u'spatial', u'dataDictionary', u'description', u'format', u'granularity', u'accessLevel', u'accessURL', u'publisher', u'language', u'license', u'systemOfRecords', u'person', u'accrualPeriodicity', u'dataQuality', u'distribution', u'identifier', u'mbox'])


#{u'title': 6061, u'theme': 6061, u'accessLevel': 6061, u'publisher': 6061, u'identifier': 6061, u'description': 6060, u'accessURL': 6060, u'distribution': 6060, u'keyword': 6059, u'person': 6057, u'accrualPeriodicity': 6056, u'format': 6047, u'spatial': 6009, u'size': 5964, u'references': 5841, u'dataDictionary': 5841, u'temporal': 5830, u'modified': 5809, u'issued': 5793, u'mbox': 5547, u'granularity': 4434, u'license': 2048, u'dataQuality': 453}


    def db_solr_sync(self):

        print str(datetime.datetime.now()) + ' Entering Database Solr Sync function.'

        url = config.get('solr_url') + "/select?q=*%3A*&sort=id+asc&fl=id%2Cmetadata_modified&wt=json&indent=true"
        response = get_response(url)
    
        if (response != 'error'):

          print str(datetime.datetime.now()) + ' Deleting records from solr_pkg_ids.'		
          sql = '''delete from solr_pkg_ids'''
          model.Session.execute(sql)
          model.Session.commit()
		
          f = response.read()
          data = json.loads(f)
          rows = data.get('response').get('numFound')

          start = 0
          chunk_size = 1000         

          print str(datetime.datetime.now()) + ' Starting insertion of records in solr_pkg_ids .'
 
          for x in range(0, int(math.ceil(rows/chunk_size))+1):
		  
            if(x == 0):
               start = 0
			
            print str(datetime.datetime.now()) + ' Fetching ' + url + "&rows=" + str(chunk_size) + "&start=" + str(start)			  
			  
            response = get_response(url + "&rows=" + str(chunk_size) + "&start=" + str(start))
            f = response.read()
            data = json.loads(f)
            results = data.get('response').get('docs')

            print str(datetime.datetime.now()) + ' Inserting ' + str(start) + ' - ' + str(start + int(data.get('responseHeader').get('params').get('rows')) - 1) + ' of ' + str(rows)			
			
            for x in range(0, len(results)):
                sql = '''select count(id) as count from package where id = :pkg_id;'''
                q = model.Session.execute(sql, {'pkg_id' : results[x]['id']})            
                for row in q:
                   if(row['count'] == 0):
                     sql = '''insert into solr_pkg_ids (pkg_id, action) values (:pkg_id, :action);'''
                     model.Session.execute(sql, {'pkg_id' : results[x]['id'], 'action' : 'notfound' })
                     model.Session.commit()			
                   else:
                     pkg_dict = logic.get_action('package_show')(
                                    {'model': model, 'ignore_auth': True, 'validate': False},
                                    {'id': results[x]['id']})
                     if(str(results[x]['metadata_modified'])[:19] != pkg_dict['metadata_modified'][:19]):
                       print str(datetime.datetime.now()) + ' Action Type : outsync for Package Id: ' + results[x]['id']
                       print ' ' * 26 +                     ' Modified Date from Solr: ' + str(results[x]['metadata_modified'])
                       print ' ' * 26 +                     ' Modified Date from Db: ' + pkg_dict['metadata_modified']
                       sql = '''insert into solr_pkg_ids (pkg_id, action) values (:pkg_id, :action);'''
                       model.Session.execute(sql, {'pkg_id' : results[x]['id'], 'action' : 'outsync' })
                       model.Session.commit()
                     else:
                       sql = '''insert into solr_pkg_ids (pkg_id, action) values (:pkg_id, :action);'''
                       model.Session.execute(sql, {'pkg_id' : results[x]['id'], 'action' : 'insync' })
                       model.Session.commit()
                     
            start = int(data.get('responseHeader').get('params').get('start')) + chunk_size			       
          
          print str(datetime.datetime.now()) + ' Starting Database to Solr Sync'           
          
          #sql = '''Select id from package where id not in (select pkg_id from solr_pkg_ids); '''
          sql = '''Select p.id as pkg_id from package p
                   left join solr_pkg_ids sp on sp.pkg_id = p.id
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
          
          sql = '''Select pkg_id from solr_pkg_ids where action = 'outsync'; '''
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
          
          sql = '''Select pkg_id from solr_pkg_ids where action = 'notfound'; '''
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
                          (unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff),
                           unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff),
                           unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff))

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
                    retry = retry -1
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

        filename = '/usr/lib/ckan/src/ckanext-geodatagov/ckanext/geodatagov/dynamic_menu/usasearch-custom-feed.xml'
        with codecs.open(filename, "w", "utf-8") as out:
            doc.writexml(out, encoding="UTF-8")

        print '%s combined feeds written to %s' % (datetime.datetime.now(),
            filename)

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