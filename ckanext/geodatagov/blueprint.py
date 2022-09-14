import ckan.model as model
from ckan.plugins.toolkit import abort

from flask import Blueprint
from flask.wrappers import Response as response

from ckanext.geodatagov.model import MiscsFeed, MiscsTopicCSV


datapusher = Blueprint('geodatagov', __name__)


def feed():
    entry = model.Session.query(MiscsFeed).first()
    if not entry or not entry.feed:
        abort(404, 'The feed is not ready yet.')
    response.content_type = 'application/atom+xml; charset=utf-8'
    return entry.feed


def csv(date=None):
    if date:
        entry = model.Session.query(MiscsTopicCSV) \
            .filter_by(date=date) \
            .first()
    else:
        entry = model.Session.query(MiscsTopicCSV) \
            .order_by(MiscsTopicCSV.date.desc()) \
            .first()
    if not entry or not entry.csv:
        abort(404, 'There is no csv entry yet.')
    response.content_type = 'text/csv'
    response.content_disposition = 'attachment; filename="topics-%s.csv"' % entry.date
    return entry.csv


datapusher.add_url_rule('/usasearch-custom-feed.xml',
                        view_func=feed)
datapusher.add_url_rule('/topics-csv/{date}',
                        view_func=csv)
datapusher.add_url_rule('/topics-csv',
                        view_func=csv)
