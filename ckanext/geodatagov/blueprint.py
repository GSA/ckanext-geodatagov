import ckan.model as model
from ckan.plugins.toolkit import abort

from flask import Blueprint
from flask.wrappers import Response as response

from ckanext.geodatagov.model import MiscsFeed


datapusher = Blueprint('geodatagov', __name__)


def feed():
    entry = model.Session.query(MiscsFeed).first()
    if not entry or not entry.feed:
        abort(404, 'The feed is not ready yet.')
    response.content_type = 'application/atom+xml; charset=utf-8'
    return entry.feed


datapusher.add_url_rule('/usasearch-custom-feed.xml',
                        view_func=feed)
