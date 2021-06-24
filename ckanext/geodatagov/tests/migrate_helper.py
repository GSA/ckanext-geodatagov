# encoding: utf-8

from __future__ import with_statement
# from alembic import context
from sqlalchemy import engine_from_config, pool
# from logging.config import fileConfig
from ckan.model import init_model
from ckan.model.meta import metadata

# config = context.config
target_metadata = metadata

# exclude_tables = config.get_section('alembic:exclude').get('tables', '').split(',')

def include_object(object, name, type_, reflected, compare_to):    
    if type_ == "table" and name in exclude_tables:
        return False
    else:
        return True

def run_migrations_offline():
    """Run migrations in 'offline' mode.
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.
    Calls to context.execute() here emit the given string to the
    script output.
    """
    pass
    # url = config.get_main_option(u"sqlalchemy.url")
    # context.configure(
    #     url=url, target_metadata=target_metadata, literal_binds=True,
    #     include_object=include_object)

    # with context.begin_transaction():
    #     context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = engine_from_config(
        # config.get_section(config.config_ini_section),
        prefix=u'sqlalchemy.',
        poolclass=pool.NullPool
    )
    connection = connectable.connect()
    init_model(connectable)

    # context.configure(connection=connection,
    #                   target_metadata=target_metadata,
    #                   include_object=include_object)

    # with context.begin_transaction():
    #     context.run_migrations()


# if context.is_offline_mode():
#     run_migrations_offline()
# else:
#     run_migrations_online()
