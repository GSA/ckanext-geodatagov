import logging
from sqlalchemy import Table, Column, types

import ckan.model as model
import ckan.model.meta as meta
import ckan.model.domain_object as domain_object

log = logging.getLogger(__name__)

miscs_feed_table = None
miscs_topic_csv_table = None


class MiscsFeedException(Exception):
    pass


class MiscsFeed(domain_object.DomainObject):
    pass


class MiscsTopicCSVException(Exception):
    pass


class MiscsTopicCSV(domain_object.DomainObject):
    pass


class MiscsSolrSyncException(Exception):
    pass


class MiscsSolrSync(domain_object.DomainObject):
    pass


def setup():

    if miscs_feed_table is None:
        define_miscs_feed_table()
        log.debug('Geodatagov Miscs Feed table defined in memory')

    if model.package_table.exists():
        if not miscs_feed_table.exists():
            miscs_feed_table.create()
            log.debug('Geodatagov Miscs Feed table created')
        else:
            log.debug('Geodatagov Miscs Feed table already exists')
    else:
        log.debug('Geodatagov Miscs Feed table creation deferred')

    if miscs_topic_csv_table is None:
        define_miscs_topic_csv_table()
        log.debug('Geodatagov Miscs Topic CSV table defined in memory')

    if model.package_table.exists():
        if not miscs_topic_csv_table.exists():
            miscs_topic_csv_table.create()
            log.debug('Geodatagov Miscs Topic CSV table created')
        else:
            log.debug('Geodatagov Miscs Topic CSV table already exists')
    else:
        log.debug('Geodatagov Miscs Topic CSV table creation deferred')


def define_miscs_feed_table():
    global miscs_feed_table
    miscs_feed_table = Table('miscs_feed', meta.metadata,
                             Column('id', types.UnicodeText, primary_key=True, default=model.types.make_uuid),
                             Column('feed', types.UnicodeText, nullable=False, default=u''),
                             )

    meta.mapper(MiscsFeed, miscs_feed_table)


def define_miscs_topic_csv_table():
    global miscs_topic_csv_table
    miscs_topic_csv_table = Table('miscs_topic_csv', meta.metadata,
                                  Column('id', types.UnicodeText, primary_key=True, default=model.types.make_uuid),
                                  Column('date', types.UnicodeText, index=True, unique=True, nullable=False, default=u''),
                                  Column('csv', types.UnicodeText, nullable=False, default=u''),
                                  )

    meta.mapper(MiscsTopicCSV, miscs_topic_csv_table)
