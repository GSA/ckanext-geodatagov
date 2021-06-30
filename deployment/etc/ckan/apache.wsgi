import os
import hashlib
hashlib.md5 = hashlib.sha1
os.environ['OPENSSL_FORCE_FIPS_MODE']='1'
activate_this = os.path.join('/usr/lib/ckan/bin/activate_this.py')
execfile(activate_this, dict(__file__=activate_this))

import ckanext
try:
    from paste.deploy import loadapp
except ImportError:
    from ckan.plugins.toolkit.deploy import loadapp

config_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'production.ini')

try:
    from paste.script.util.logging_config import fileConfig
except ImportError:
    from ckan.plugins.toolkit.script.util.logging_config import fileConfig

fileConfig(config_filepath)
_application = loadapp('config:%s' % config_filepath)
def application(environ, start_response):
    environ.pop('REMOTE_USER', None)
    environ['wsgi.url_scheme'] = environ.get('HTTP_X_SCHEME', 'http')
    return _application(environ, start_response)
