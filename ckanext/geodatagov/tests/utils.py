import http.server
import logging
import socketserver
from threading import Thread
import os

from ckan.tests.helpers import reset_db
from ckan.model.meta import Session, metadata
import ckan.lib.search as search


log = logging.getLogger(__name__)

PORT = 8999


def simple_http_server(port=PORT):
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


def populate_locations_table():
    # download locations.sql.gz if not present
    if not os.path.exists('/tmp/locations.sql.gz'):
        os.system(
            "wget https://github.com/GSA/datagov-deploy/raw/71936f004be1882a506362670b82c710c64ef796/"
            "ansible/roles/software/ec2/ansible/files/locations.sql.gz "
            "-O /tmp/locations.sql.gz"
        )
    # echo "Creating locations table"
    os.system("PGPASSWORD=ckan psql -h db -U ckan -d ckan -c 'DROP TABLE IF EXISTS locations;'")
    os.system("PGPASSWORD=ckan psql -h db -U ckan -d ckan -c 'DROP SEQUENCE IF EXISTS locations_id_seq;'")
    os.system("gunzip -c /tmp/locations.sql.gz | PGPASSWORD=ckan psql -h db -U ckan -d ckan -v ON_ERROR_STOP=1")


def reset_db_and_solr():
    # https://github.com/ckan/ckan/issues/4764
    # drop extension postgis so we can reset db
    try:
        os.system(
            "PGPASSWORD=ckan psql -h db -U ckan -d ckan -c "
            "'SELECT pg_terminate_backend(pg_stat_activity.pid) "
            " FROM pg_stat_activity WHERE "
            " datname = current_database() AND"
            " pid <> pg_backend_pid();'"
        )
    except Exception:
        pass
    os.system("PGPASSWORD=ckan psql -h db -U ckan -d ckan -c 'drop extension IF EXISTS postgis cascade;'")
    try:
        reset_db()
    except Exception:
        pass
    os.system("PGPASSWORD=ckan psql -h db -U ckan -d ckan -c 'create extension postgis;'")
    # add back tables from extensions
    metadata.create_all(bind=Session.bind)

    search.clear_all()
