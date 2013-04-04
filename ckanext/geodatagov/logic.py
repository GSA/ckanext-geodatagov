import logging

from ckan.logic.action import get as core_get
from ckanext.geodatagov.plugins import change_resource_details

log = logging.getLogger(__name__)

def group_show(context, data_dict):

    context.update({'limits': {'packages': 2}})

    return core_get.group_show(context, data_dict)

def organization_show(context, data_dict):

    context.update({'limits': {'packages': 2}})

    return core_get.organization_show(context, data_dict)

def organization_list(context, data_dict):

    model = context['model']

    results = core_get.organization_list(context, data_dict)

    query_results = model.Session.query(
        model.GroupExtra.group_id,
        model.GroupExtra.value
    ).filter_by(
        key='organization_type'
    ).filter(
        model.GroupExtra.group_id.in_([group['id'] for group in results])
    ).all()


    lookup = dict((row[0], row[1]) for row in query_results)

    for group in results:
        organization_type = lookup.get(group['id'])
        if organization_type:
            group['organization_type'] = organization_type

    return results

def resource_show(context, data_dict):
    resource = core_get.resource_show(context, data_dict)
    change_resource_details(resource)
    return resource








