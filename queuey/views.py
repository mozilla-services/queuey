# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import random

from pyramid.view import view_config

from queuey import validators

from queuey.resources import Application
from queuey.resources import Queue


# Our invalid schema catch-all
@view_config(context='colander.Invalid', renderer='json')
@view_config(context='queuey.security.InvalidBrowserID', renderer='json')
@view_config(context='queuey.security.InvalidApplicationKey', renderer='json')
@view_config(context='queuey.resources.InvalidQueueName', renderer='json')
def bad_params(context, request):
    exc = request.exception
    cls_name = exc.__class__.__name__
    if cls_name == 'Invalid':
        errors = exc.asdict()
    else:
        errors = {cls_name: exc.message}
    return {
        'status': 'error',
        'error_msg': errors
    }


@view_config(context=Application, request_method='POST', renderer='json',
             permission='create_queue')
def create_queue(context, request):
    """Create a new queue

    POST params

        queue_name - (`Optional`) Name of the queue to create
        partitions - (`Optional`) How many partitions the queue should
                     have (defaults to 1)
        type       - (`Optional`) Type of queue to create, defaults to
                     'private' which requires authentication to access
        consistency - (`Optional`) Level of consistency for the queue,
                      defaults to 'strong'.
        permissions - (`Optional`) List of BrowserID's separated with a
                      comma if there's more than one

    Returns a JSON response indicating the status, the UUID4 hex
    string of the queue name (if not supplied), and the partitions
    created.

    Example success response::

        {
            'status': 'ok',
            'application_name': 'notifications',
            'queue_name': 'ea2f39c0de9a4b9db6463123641631de',
            'partitions': 1,
            'type': 'user',
            'consistency': 'strong'
        }

    """
    schema = validators.NewQueue().bind()
    params = schema.deserialize(request.POST)
    context.register_queue(**params)
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
    """Post a message to a queue

    POST params

        A form body containing a single message and optional partition
        value, or a set of message and partition pairs by number.

        Example single message (shown as dict)::

            {
                'message': 'this is a message',
                'partition': '1'
            }

        Example multiple message (shown as dict)::

            {
                'message-1': 'this is message 1',
                'message-2': 'this is message 2',
                'partition-2': '3'
            }

        The second example lets the first message go to the default
        partition (1), while the second message is sent to partition
        2.

    Example success response::

        {
            'status': 'ok',
            'key': '3a6592301e0911e190b1002500f0fa7c',
            'timestamp': 1323976306.988889,
            'partition': 1
        }

    """
    queue_name = request.matchdict['queue_name']
    partition = request.validated.get('partition')
    if not partition:
        meta = request.registry['backend_metadata']
        info = meta.queue_information(request.app_key, queue_name)
        partitions = info['partitions']
        partition = random.randint(1, partitions)

    storage = request.registry['backend_storage']
    message_key, timestamp = storage.push('%s-%s' % (queue_name, partition),
                                          request.body)
    return {
        'status': 'ok',
        'key': message_key,
        'timestamp': timestamp,
        'partition': partition
    }


@view_config(context=Queue, request_method='GET', renderer='json',
             permission='view')
def get_messages(request):
    """Get messages from a queue

    Query Params

        since_timestamp - (`Optional`) All messages newer than this timestamp,
                          should be formatted as seconds since epoch in GMT
        limit           - (`Optional`) Only return N amount of messages
        order           - (`Optional`) Order of messages, can be set to either
                          `ascending` or `descending`. Defaults to `descending`.
        partition       - (`Optional`) A specific partition number to retrieve
                          messages from. Defaults to retrieving messages from
                          partition 1.

    Messages are returned in order of newest to oldest.

    Example response::

        {
            'status': 'ok',
            'messages': [
                {
                    'key': '3a6592301e0911e190b1002500f0fa7c',
                    'timestamp': 1323973966282.637,
                    'body': 'jlaijwiel2432532jilj'
                },
                {
                    'key': '3a8553d71e0911e19262002500f0fa7c',
                    'timestamp': 1323973966918.241,
                    'body': 'ion12oibasdfjioawneilnf'
                }
            ]
        }

    """
    queue_name = request.matchdict['queue_name']
    storage = request.registry['backend_storage']
    messages = storage.retrieve(
        '%s-%s' % (queue_name, request.validated['partition']),
        request.validated['limit'],
        request.validated['since_timestamp'],
        request.validated['order'])
    message_data = [{
        'key': key.hex,
        'timestamp': timestamp,
        'body': body} for key, timestamp, body in messages]
    return {'status': 'ok', 'messages': message_data}


@view_config(context=Queue, name='info', request_method='GET', renderer='json',
             permission='info')
def queue_info(context, request):
    """Get queue information

    Returns a JSON response indicating the status, and the information
    about the queue.

    Example response::

        {
            'status': 'ok',
            'application_name': 'notifications',
            'queue_name': 'ea2f39c0de9a4b9db6463123641631de',
            'partitions': 1,
            'created': 1322521547,
            'count': 932
        }

    """
    return dict(
        status='ok',
        application_name=context.application,
        queue_name=context.queue_name,
        partitions=context.partitions,
        created=context.created,
        count=context.count
    )


def delete_queue(request):
    """Delete a queue

    URL Params

        queue_name - A UUID4 hex string to use as the queue name.

    JSON Body Params (`Optional`)

        messages - A list of message keys to delete

    Query Params

        delete - (`Optional`) If set to false, the queue will be deleted
                 but remain registered

    Example success response::

        {'status': 'ok'}

    If individual messages are being deleted, the partition will default
    to partition 1 if no ``X-Partition`` header is supplied.

    """
    queue_name = request.matchdict['queue_name']
    storage = request.registry['backend_storage']
    meta = request.registry['backend_metadata']
    if 'messages' in request.validated:
        partition = request.validated.get('partition', 1)
        storage.delete('%s-%s' % (queue_name, partition),
                       *request.validated['messages'])
    else:
        info = meta.queue_information(request.app_key, queue_name)
        partitions = info['partitions']

        for num in range(1, partitions + 1):
            storage.truncate('%s-%s' % (queue_name, num))

    if request.validated.get('delete') != 'false':
        meta.remove_queue(request.app_key, queue_name)
    return {'status': 'ok'}
