from __future__ import print_function

import os
import json
import re
import copy
import urllib
import xml.etree.ElementTree as ET
import SimpleHTTPServer
import SocketServer
from threading import Thread
import logging
log = logging.getLogger("harvester")

PORT = 8998


class MockCSWHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def do_GET(self):
        log.info('GET mock at: {}'.format(self.path))
        # test name is the first bit of the URL and makes CKAN behave
        # differently in some way.
        # Its value is recorded and then removed from the path
        self.test_name = None
        self.sample_file = None
        self.samples_path = 'ckanext/geodatagov/tests/data-samples'
        if self.path.startswith('/sample'):
            n = self.path[7]
            self.sample_file = 'sample{}'.format(n)
            self.test_name = 'Sample {}'.format(n)
        elif self.path.startswith('/404'):
            self.test_name = 'e404'
            self.respond('Not found', status=404)
        elif self.path.startswith('/500'):
            self.test_name = 'e500'
            self.respond('Error', status=500)
        
        if self.sample_file is not None:
            sample_file = '{}.xml'.format(self.sample_file)
            self.respond_xml_sample_file(file_path=sample_file)

        if self.test_name == None:
            self.respond('Mock CSW doesnt recognize that call', status=400)

    def do_POST(self):
        # get params
        self.data_string = self.rfile.read(int(self.headers['Content-Length']))
        """ sample 
        <?xml version="1.0" encoding="ISO-8859-1" standalone="no"?>
<csw:GetRecords xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" xmlns:ogc="http://www.opengis.net/ogc" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" outputSchema="http://www.isotc211.org/2005/gmd" outputFormat="application/xml" version="2.0.2" service="CSW" resultType="results" maxRecords="10" xsi:schemaLocation="http://www.opengis.net/cat/csw/2.0.2 http://schemas.opengis.net/csw/2.0.2/CSW-discovery.xsd"><csw:Query typeNames="csw:Record"><csw:ElementSetName>brief</csw:ElementSetName><ogc:SortBy><ogc:SortProperty><ogc:PropertyName>dc:identifier</ogc:PropertyName><ogc:SortOrder>ASC</ogc:SortOrder></ogc:SortProperty></ogc:SortBy></csw:Query></csw:GetRecords>
        """
        # for JSON data = json.loads(self.data_string)
        
        myroot = ET.fromstring(data)
        
        self.test_name = None
        self.sample_file = None
        self.samples_path = 'ckanext/geodatagov/tests/data-samples'
        if self.path.startswith('/sample'):
            n = self.path[7]
            if 'GetRecords' in myroot.tag:
                self.sample_file = 'sample{}_getrecords2.xml'.format(n)
            elif 'GetRecordById' in myroot.tag:
                self.sample_file = 'sample{}_id_{}.xml'.format(n, data['id'])
            self.test_name = 'Sample {}'.format(n)
        
        if self.sample_file is not None:
            self.respond_xml_sample_file(file_path=self.sample_file)

        if self.test_name == None:
            self.respond('Mock CSW doesnt recognize that call', status=400)
        
    def respond_json(self, content_dict, status=200):
        return self.respond(json.dumps(content_dict), status=status,
                            content_type='application/json')
    
    def respond_json_sample_file(self, file_path, status=200):
        pt = os.path.join(self.samples_path, file_path)
        data = open(pt, 'r')
        content = data.read()
        log.info('mock respond {}'.format(content[:90]))
        return self.respond(content=content, status=status,
                            content_type='application/json')

    def respond_xml_sample_file(self, file_path, status=200):
        pt = os.path.join(self.samples_path, file_path)
        data = open(pt, 'r')
        content = data.read()
        log.info('mock respond {}'.format(content[:90]))
        return self.respond(content=content, status=status,
                            content_type='application/xml')

    def respond(self, content, status=200, content_type='application/json'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.end_headers()
        self.wfile.write(content)
        self.wfile.close()


def serve(port=PORT):
    '''Runs a CKAN-alike app (over HTTP) that is used for harvesting tests'''

    class TestServer(SocketServer.TCPServer):
        allow_reuse_address = True

    httpd = TestServer(("", PORT), MockCSWHandler)

    info = 'Serving test HTTP server at port {}'.format(PORT)
    print(info)
    log.info(info)

    httpd_thread = Thread(target=httpd.serve_forever)
    httpd_thread.setDaemon(True)
    httpd_thread.start()
