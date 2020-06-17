import os

import SimpleHTTPServer
import SocketServer
from threading import Thread
import logging
log = logging.getLogger(__name__)


PORT = 8999


def serve(port=PORT):
    '''Serves test XML files over HTTP'''
    
    # Make sure we serve from the tests' XML directory
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          'data-samples'))

    Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
    
    class TestServer(SocketServer.TCPServer):
        allow_reuse_address = True
    
    try:
        httpd = TestServer(("", port), Handler)
    except Exception, e:
        print('Serve error {}'.format(e))
        if 'Address in use' not in str(e):
            raise

    info = 'Serving test HTTP server at port', port
    print info
    log.info(info)

    httpd_thread = Thread(target=httpd.serve_forever)
    httpd_thread.setDaemon(True)
    httpd_thread.start()
