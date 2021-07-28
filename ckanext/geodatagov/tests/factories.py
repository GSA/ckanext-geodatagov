import factory
import ckanext.harvest.model as harvest_model
try:
    from ckan.new_tests.factories import _get_action_user_name
except ImportError:
    from ckan.tests.factories import _get_action_user_name
from ckan.plugins import toolkit
import logging
log = logging.getLogger(__name__)


class HarvestSource(factory.Factory):
    FACTORY_FOR = harvest_model.HarvestSource
    _return_type = 'dict'

    class Meta:
        model = harvest_model.HarvestSource

    name = factory.Sequence(lambda n: 'test_source_{n}'.format(n=n))
    title = factory.Sequence(lambda n: 'test title {n}'.format(n=n))
    url = factory.Sequence(lambda n: 'http://{n}.test.com'.format(n=n))
    source_type = 'undefined'
    id = '{0}_id'.format(name).lower()

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."
        context = {'user': _get_action_user_name(kwargs)}
        if kwargs.get('owner_org', False):
            context['owner_org'] = kwargs['owner_org']
        # If there is an existing source for this URL, and we can't create
        # another source with that URL, just return the original one.
        log.info('Factory HarvestSource : {} : {}'.format(context, kwargs))
        try:
            source_dict = toolkit.get_action('harvest_source_show')(
                context, dict(url=kwargs['url']))
        except (KeyError, toolkit.ObjectNotFound):
            source_dict = toolkit.get_action('harvest_source_create')(
                context, kwargs)
        if cls._return_type == 'dict':
            return source_dict
        else:
            return cls.FACTORY_FOR.get(source_dict['id'])


class HarvestSourceObj(HarvestSource):
    _return_type = 'obj'


class CSWHarvestSourceObj(HarvestSourceObj):
    source_type = 'csw'


class WafCollectionHarvestSourceObj(HarvestSourceObj):
    source_type = 'waf-collection'


class WafHarvestSourceObj(HarvestSourceObj):
    source_type = 'waf'


class DataJsonHarvestSourceObj(HarvestSourceObj):
    source_type = 'datajson'


class HarvestJob(factory.Factory):
    FACTORY_FOR = harvest_model.HarvestJob
    _return_type = 'dict'

    class Meta:
        model = harvest_model.HarvestJob

    source = factory.SubFactory(HarvestSourceObj)

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."
        context = {'user': _get_action_user_name(kwargs)}
        if 'source_id' not in kwargs:
            kwargs['source_id'] = kwargs['source'].id
        if 'run' not in kwargs:
            kwargs['run'] = False
        job_dict = toolkit.get_action('harvest_job_create')(
            context, kwargs)
        if cls._return_type == 'dict':
            return job_dict
        else:
            return cls.FACTORY_FOR.get(job_dict['id'])


class HarvestJobObj(HarvestJob):
    _return_type = 'obj'


class HarvestObject(factory.Factory):
    FACTORY_FOR = harvest_model.HarvestObject
    _return_type = 'dict'

    class Meta:
        model = harvest_model.HarvestObject

    # source = factory.SubFactory(HarvestSourceObj)
    job = factory.SubFactory(HarvestJobObj)

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."
        context = {'user': _get_action_user_name(kwargs)}
        if 'job_id' not in kwargs:
            kwargs['job_id'] = kwargs['job'].id
            kwargs['source_id'] = kwargs['job'].source.id
        # Remove 'job' to avoid it getting added as a HarvestObjectExtra
        if 'job' in kwargs:
            kwargs.pop('job')
        job_dict = toolkit.get_action('harvest_object_create')(
            context, kwargs)
        if cls._return_type == 'dict':
            return job_dict
        else:
            return cls.FACTORY_FOR.get(job_dict['id'])


class HarvestObjectObj(HarvestObject):
    _return_type = 'obj'
