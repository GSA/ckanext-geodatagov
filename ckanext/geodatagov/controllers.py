from pylons.i18n import _

from ckan.lib.base import BaseController, response, abort  # , c
import ckan.model as model

from ckanext.geodatagov.model import MiscsFeed, MiscsTopicCSV


class GeodatagovMiscsController(BaseController):
    controller_path = 'ckanext.geodatagov.controllers:GeodatagovMiscsController'

    def feed(self):
        entry = model.Session.query(MiscsFeed).first()
        if not entry or not entry.feed:
            abort(404, _('The feed is not ready yet.'))
        response.content_type = 'application/atom+xml; charset=utf-8'
        return entry.feed

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
        response.content_disposition = 'attachment; filename="topics-%s.csv"' % entry.date
        return entry.csv
