from __future__ import print_function

import os
import json
import re
import copy
import urllib

import SimpleHTTPServer
import SocketServer
from threading import Thread

PORT = 8998


class MockCSWHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def do_GET(self):
        # test name is the first bit of the URL and makes CKAN behave
        # differently in some way.
        # Its value is recorded and then removed from the path
        self.test_name = None
        self.sample_datajson_file = None
        self.samples_path = 'data-samples'
        if self.path == 'https://sample1.com':
            self.sample_file = 'sample1'
            self.test_name = 'Esri'
        elif self.path == 'http://some404.com/data.json':
            self.test_name = 'e404'
            self.respond('Not found', status=404)
        elif self.path == 'http://some500.com/data.json':
            self.test_name = 'e500'
            self.respond('Error', status=500)
        
        if self.sample_file is not None:
            sample_file = '{}.json'.format(self.sample_file)
            self.respond_json_sample_file(file_path=sample_file)

        if self.test_name == None:
            self.respond('Mock CSW doesnt recognize that call', status=400)

    def respond_json(self, content_dict, status=200):
        return self.respond(json.dumps(content_dict), status=status,
                            content_type='application/json')
    
    def respond_json_sample_file(self, file_path, status=200):
        pt = os.path.join(self.samples_path, file_path)
        data = json.load(open(pt, 'r'))
        return self.respond(data, status=status,
                            content_type='application/json')

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

    print('Serving test HTTP server at port {}'.format(PORT))

    httpd_thread = Thread(target=httpd.serve_forever)
    httpd_thread.setDaemon(True)
    httpd_thread.start()
