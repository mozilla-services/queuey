# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import random

from pyramid.view import view_config

from queuey import validators

from queuey.resources import Application
from queuey.resources import Queue


class InvalidParameter(Exception):
    """Raised in views to flag a bad parameter"""


def _fixup_dict(dct):
    """Colander has an issue with unflatten that requires a leading ."""
    return dict(('.' + k, v) for k, v in dct.items())


# Our invalid schema catch-all
@view_config(context=InvalidParameter, renderer='json')
@view_config(context='colander.Invalid', renderer='json')
@view_config(context='queuey.security.InvalidBrowserID', renderer='json')
@view_config(context='queuey.security.InvalidApplicationKey', renderer='json')
@view_config(context='queuey.resources.InvalidQueueName', renderer='json')
@view_config(context='queuey.resources.InvalidUpdate', renderer='json')
def bad_params(context, request):
    exc = request.exception
    cls_name = exc.__class__.__name__
    if cls_name == 'Invalid':
        request.response.status = 400
        errors = exc.asdict()
    elif cls_name == 'InvalidParameter':
        request.response.status = 400
        errors = {cls_name: exc.message}
    elif cls_name == 'InvalidUpdate':
        request.response.status = 400
        errors = {cls_name: exc.message}
    elif cls_name == 'InvalidQueueName':
        request.response.status = 404
        errors = {cls_name: exc.message}
    else:
        errors = {cls_name: exc.message}
        request.response.status = 401
    return {
        'status': 'error',
        'error_msg': errors
    }


@view_config(context=Application, request_method='POST', renderer='json',
             permission='create_queue')
def create_queue(context, request):
    schema = validators.NewQueue().bind()
    params = schema.deserialize(request.POST)
    context.register_queue(**params)
    request.response.status = 201
    return dict(status='ok', application_name=context.application_name,
                **params)


@view_config(context=Application, request_method='GET', renderer='json',
             permission='view_queues')
def queue_list(context, request):
    params = validators.QueueList().deserialize(request.GET)
    return {
        'status': 'ok',
        'queues': context.queue_list(**params)
    }


@view_config(context=Queue, request_method='POST', renderer='json',
             permission='create')
def new_message(context, request):
    request.response.status = 201
    if 'body' in request.POST:
        # Single message, use appropriate schema
        msgs = [validators.Message().deserialize(request.POST)]
    else:
        # Multiple messages, fixup the dict for colander first
        msgs = _fixup_dict(request.POST)
        schema = validators.Messages()
        try:
            msgs = schema.unflatten(msgs)
        except Exception:
            msgs = {}
        msgs = schema.deserialize(msgs)['message']

    # Assign partitions
    for msg in msgs:
        if not msg['partition']:
            msg['partition'] = random.randint(1, context.partitions)

    return {
        'status': 'ok',
        'messages': context.push_batch(msgs)
    }


@view_config(context=Queue, request_method='GET', renderer='json',
             permission='view')
def get_messages(context, request):
    params = validators.GetMessages().deserialize(request.GET)
    return {
        'status': 'ok',
        'messages': context.get_messages(**params)
    }


@view_config(context=Queue, request_method='PUT', renderer='json',
             permission='create')
def update_queue(context, request):
    params = validators.UpdateQueue().deserialize(request.POST)
    context.update_metadata(**params)
    return queue_info(context, request)


@view_config(context=Queue, name='info', request_method='GET', renderer='json',
             permission='info')
def queue_info(context, request):
    return dict(
        status='ok',
        application_name=context.application,
        queue_name=context.queue_name,
        partitions=context.partitions,
        created=context.created,
        count=context.count,
        principles=context.principles,
        type=context.type
    )


@view_config(context=Queue, request_method='DELETE', renderer='json',
             permission='delete')
def delete_queue(context, request):
    params = validators.DeleteMessages().deserialize(request.GET)
    if params['messages'] and len(params['partitions']) > 1:
        raise InvalidParameter("Partitions can only be a single value if "
                               "messages are provided.")
    if params['messages']:
        del params['delete_registration']
        context.delete_messages(**params)
    else:
        del params['messages']
        context.delete(**params)
    return {'status': 'ok'}
