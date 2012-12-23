import collections
import os
import sys
import re
import csv
import json
import urllib
import lxml.etree
import ckan
import ckan.model as model
import ckan.logic as logic
import ckan.lib.cli as cli
import requests
import ckanext.harvest.model as harvest_model
import xml.etree.ElementTree as ET


import logging
log = logging.getLogger()



class GeoGovCommand(cli.CkanCommand):
    '''
    Commands:

        paster ecportal import-harvest-source <data> -c <config>
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
            if not len(self.args) in [2, 3]:
                print GeoGovCommand.__doc__
                return

            self.import_data(self.args[1])

    def import_data(self, location):
        '''Import data from this mysql command
        select DOCUUID, TITLE, OWNER, APPROVALSTATUS, HOST_URL, 
        Protocol, PROTOCOL_TYPE, FREQUENCY 
        INTO OUTFILE '/tmp/resultall.csv' 
        from GPT_RESOURCE left join GPT_RESOURCE_DATA using(DOCUUID) 
        where frequency is not null;'''

        fields = ['DOCUUID', 'TITLE', 'OWNER', 'APPROVALSTATUS', 'HOST_URL', 
        'PROTOCAL', 'PROTOCOL_TYPE', 'FREQUENCY']

        harvest_sources = open(location)
        try:
            csv_reader = csv.reader(harvest_sources, delimiter='\t')
            for row in csv_reader:
                row = dict(zip(fields,row))

                ## neeeds some fix
                if row['PROTOCOL_TYPE'].lower() not in ('waf', 'csw', 'z3950'):
                    continue

                harvest_source = harvest_model.HarvestSource()
                harvest_source.id = row['DOCUUID'][1:-1].lower()
                harvest_source.title = row['TITLE']
                harvest_source.url = row['HOST_URL']

                ##need some thought on this conversion
                harvest_source.type = row['PROTOCOL_TYPE'].lower()

                harvest_source.frequency = row['FREQUENCY'].upper()

                if harvest_source.frequency not in ('WEEKLY', 'MONTHLY', 'BIWEEKLY'):
                    harvest_source.frequency = 'MANUAL'

                config = {
                          'OWNER': row['OWNER'],
                          'APPROVALSTATUS': row['APPROVALSTATUS'],
                         }

                root = ET.fromstring(row['PROTOCAL'])

                for child in root:
                    if child.text:
                        config[child.tag] = child.text

                harvest_source.config = json.dumps(config)
                model.Session.add(harvest_source)

        finally:
            model.Session.commit()
            harvest_sources.close()




