# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from pyramid.view import view_config
import ujson

from queuey import validators

from queuey.resources import Application
from queuey.resources import Queue
from queuey.resources import MessageBatch


class InvalidParameter(Exception):
    """Raised in views to flag a bad parameter"""
    status = 400


class UJSONRendererFactory:
    def __init__(self, info):
        pass

    def __call__(self, value, system):
        return ujson.dumps(value)


# Our invalid schema catch-all
@view_config(context=InvalidParameter, renderer='json')
@view_config(context='colander.Invalid', renderer='json')
@view_config(context='queuey.security.InvalidBrowserID', renderer='json')
@view_config(context='queuey.security.InvalidApplicationKey', renderer='json')
@view_config(context='queuey.resources.InvalidQueueName', renderer='json')
@view_config(context='queuey.resources.InvalidUpdate', renderer='json')
@view_config(context='queuey.resources.InvalidMessageID', renderer='json')
@view_config(context='queuey.storage.StorageUnavailable', renderer='json')
def bad_params(context, request):
    exc = request.exception
    cls_name = exc.__class__.__name__
    if cls_name == 'Invalid':
        errors = exc.asdict()
        request.response.status = 400
    elif cls_name == 'StorageUnavailable':
        request.response.status = 500
        errors = {'storage': 'Back-end storage unavailable. If this is a '
                             'queue request that includes counts, try '
                             'ommitting the count.'}
    else:
        request.response.status = getattr(exc, 'status', 401)
        errors = {cls_name: str(exc)}
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
    return dict(status='ok', **params)


@view_config(context=Application, request_method='GET', renderer='json',
             permission='view_queues')
def queue_list(context, request):
    params = validators.QueueList().deserialize(request.GET)
    return {
        'status': 'ok',
        'queues': context.queue_list(**params)
    }


@view_config(context=Queue, request_method='PUT', renderer='json',
             permission='create_queue')
def update_queue(context, request):
    params = validators.UpdateQueue().deserialize(request.POST)
    context.update_metadata(**params)
    return dict(
        status='ok',
        queue_name=context.queue_name,
        partitions=context.partitions,
        created=context.created,
        principles=context.principles,
        type=context.type
    )


@view_config(context=Queue, request_method='POST',
             header="Content-Type:application/json", renderer='json',
             permission='create')
def new_messages(context, request):
    request.response.status = 201
    try:
        msgs = ujson.loads(request.body)['messages']
    except:
        # A bare except like this is horrible, but we need to toss this right
        raise InvalidParameter("Unable to properly deserialize JSON body.")
    schema = validators.MessageList().bind(max_partition=context.partitions)
    msgs = schema.deserialize(msgs)
    return {
        'status': 'ok',
        'messages': context.push_batch(msgs)
    }


@view_config(context=Queue, request_method='POST', renderer='json',
             permission='create')
def new_message(context, request):
    request.response.status = 201
    msg = {'body': request.body,
           'ttl': request.headers.get('X-TTL'),
           'partition': request.headers.get('X-Partition')}
    schema = validators.Message().bind(max_partition=context.partitions)
    msg = schema.deserialize(msg)
    return {
        'status': 'ok',
        'messages': context.push_batch([msg])
    }


@view_config(context=Queue, request_method='GET', renderer='json',
             permission='view')
def get_messages(context, request):
    params = validators.GetMessages().deserialize(request.GET)
    return {
        'status': 'ok',
        'messages': context.get_messages(**params)
    }


@view_config(context=Queue, request_method='DELETE', renderer='json',
             permission='delete_queue')
@view_config(context=MessageBatch, request_method='DELETE', renderer='json',
             permission='delete')
def delete(context, request):
    context.delete()
    return {'status': 'ok'}
