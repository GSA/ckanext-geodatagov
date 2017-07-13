from pylons.i18n import _

from ckan.lib.base import BaseController, c, response, abort
import ckan.model as model
import ckan.lib.helpers as h
from pylons import config
from pylons.controllers.util import redirect_to

from ckanext.geodatagov.model import MiscsFeed, MiscsTopicCSV

class GeodatagovMiscsController(BaseController):
    controller_path = 'ckanext.geodatagov.controllers:GeodatagovMiscsController'
    def feed(self):
        entry = model.Session.query(MiscsFeed).first()
        if not entry or not entry.feed:
            abort(404, _('The feed is not ready yet.'))
        response.content_type = 'application/atom+xml; charset=utf-8'
        return entry.feed

    def s3sitemap(self):
        s3sitemap_url = config.get('ckanext.s3sitemap.url')
        if not s3sitemap_url:
            abort(404, _('ckanext.s3sitemap.url is not defined in config.'))
        return redirect_to(s3sitemap_url)

    def csv(self, date=None):
        if date:
            entry = model.Session.query(MiscsTopicCSV) \
                    .filter_by(date=date) \
                    .first()
        else:
            entry = model.Session.query(MiscsTopicCSV) \
                    .order_by(MiscsTopicCSV.date.desc()) \
                    .first()
        if not entry or not entry.csv:
            abort(404, _('There is no csv entry yet.'))
        response.content_type = 'text/csv'
        response.content_disposition = 'attachment; filename="topics-%s.csv"' \
                % entry.date
        return entry.csv
