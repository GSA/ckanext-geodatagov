
import http.server
import logging
import socketserver
from threading import Thread
import os
log = logging.getLogger(__name__)


PORT = 8999


def serve(port=PORT):
    '''Serves test XML files over HTTP'''

    # Make sure we serve from the tests' XML directory
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          'data-samples'))

    Handler = http.server.SimpleHTTPRequestHandler

    class TestServer(socketserver.TCPServer):
        allow_reuse_address = True

    skip_connection = False
    try:
        httpd = TestServer(("", port), Handler)
    except Exception as e:
        print('Serve error {}'.format(e))
        skip_connection = True

    if skip_connection is False:
        info = 'Serving test HTTP server at port', port
        print(info)
        log.info(info)

        httpd_thread = Thread(target=httpd.serve_forever)
        httpd_thread.setDaemon(True)
        httpd_thread.start()
