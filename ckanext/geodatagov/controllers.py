import urllib
import ckan.plugins as p
from pylons import config
import ckan.lib.helpers as h, json
from ckan.lib.base import BaseController, c, \
                          request, response, abort, redirect


import logging
log = logging.getLogger(__name__)

class ViewController(BaseController):

    def show(self):

        viewer_url = config.get('ckanext.geodatagov.spatial_preview.url')
        if not viewer_url:
            abort(500, 'Viewer URL not defined')
        
        params_to_forward = {}
        viewer_params = ['url', 'servicetype', 'srs']
        
        for key, value in request.params.iteritems():
            if key.lower() in viewer_params:
                params_to_forward[key] = value

        params_to_forward['mode'] = 'advanced'

        c.viewer_url = '{0}?{1}'.format(viewer_url.strip('?'), urllib.urlencode(params_to_forward))

        return p.toolkit.render('viewer.html')
