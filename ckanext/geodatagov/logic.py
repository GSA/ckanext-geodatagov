import logging

from ckan.logic.action import get as core_get

log = logging.getLogger(__name__)

def group_show(context, data_dict):

    context.update({'limits': {'packages': 2}})

    return core_get.group_show(context, data_dict)

def organization_show(context, data_dict):

    context.update({'limits': {'packages': 2}})

    return core_get.organization_show(context, data_dict)
