from pylons.i18n import _

from ckan.lib.base import BaseController, c, response, abort
import ckan.model as model

from ckanext.geodatagov.model import MiscsFeed

class GeodatagovMiscsController(BaseController):
    controller_path = 'ckanext.geodatagov.controllers:GeodatagovMiscsController'
    def feed(self):
        context = {'model': model, 'user': c.user}
        entry = model.Session.query(MiscsFeed).first()
        if not entry:
            # create the empty entry for the first time
            entry = MiscsFeed()
            entry.save()
        content = entry.feed
        if not content:
            abort(404, _('The feed is not ready yet.'))
        response.content_type = 'application/atom+xml; charset=utf-8'
        return content
