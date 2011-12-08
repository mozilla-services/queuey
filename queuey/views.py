# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Mozilla Message Queue
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
# Ben Bangert (bbangert@mozilla.com)
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
import random
import uuid

from cornice.service import Service
from pyramid.httpexceptions import HTTPBadRequest

from queuey.exceptions import ApplicationNotRegistered
from queuey.validators import partition_check
from queuey.validators import valid_int
from queuey.validators import valid_float


def add_app_key(view):
    def app_key_wrapper(context, request):
        if 'X-Application-Key' not in request.headers:
            raise HTTPBadRequest("No 'X-Application-Key' header found")
        app_key = request.headers['X-Application-Key']
        app_name = request.registry['app_keys'].get(app_key)
        if not app_name:
            raise HTTPBadRequest("Bad Application Key")
        request.app_name = app_name
        request.app_key = app_key
        return view(context, request)
    return app_key_wrapper


# Services
message_queue = Service(name='message_queues', path='/queue/',
                        decorator=add_app_key)
queues = Service(name='queues', path='/queue/{queue_name:[a-z0-9]{32}}/',
                 decorator=add_app_key)


@message_queue.post(permission='create_queue')
def new_queue(request):
    """Create a new queue

    Headers

        X-Application-Key - The applications key

    POST params

        partitions - (`Optional`) How many partitions the queue should
                     have (defaults to 1)

    Returns a JSON response indicating the status, the UUID4 hex
    string of the queue, and the partitions created.

    Example success response::

        {
            'status': 'ok',
            'application_name': 'notifications',
            'queue_name': 'ea2f39c0de9a4b9db6463123641631de',
            'partitions': 1
        }

    """
    partitions = partition_check(request)
    meta = request.registry['backend_metadata']
    queue_name = uuid.uuid4().hex
    try:
        meta.register_queue(request.app_key, queue_name, partitions)
    except ApplicationNotRegistered:
        meta.register_application(request.app_key)
        meta.register_queue(request.app_key, queue_name, partitions)

    return {
        'status': 'ok',
        'application_name': request.app_name,
        'queue_name': queue_name,
        'partitions': partitions,
    }


@message_queue.get(permission='view_queue')
def get_queue(request):
    """Get queue information

    Headers

        X-Application-Key - The applications key

    GET params

        queue_name (`Optional`) - The name of a specific queue to retrieve
                                information about

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
    queue_name = request.GET.get('queue_name')
    if not queue_name:
        raise HTTPBadRequest("No queue_name provided")

    meta = request.registry['backend_metadata']
    storage = request.registry['backend_storage']
    queue_info = meta.queue_information(request.app_key, queue_name)
    count = 0
    for num in range(1, queue_info['partitions'] + 1):
        count += storage.count('%s-%s' % (queue_name, num))
    queue_info['status'] = 'ok'
    queue_info['application_name'] = request.app_name
    queue_info['count'] = count
    return queue_info


@queues.delete(permission='delete_queue')
def delete_queue(request):
    """Delete a queue

    Headers

        X-Application-Key - The applications key


    URL Params

        queue_name - A UUID4 hex string to use as the queue name.
        delete - (`Optional`) If set to false, the queue will be deleted
                 but remain registered

    Example success response::

        {'status': 'ok'}

    """
    queue_name = request.matchdict['queue_name']
    storage = request.registry['backend_storage']
    meta = request.registry['backend_metadata']
    info = meta.queue_information(request.app_key, queue_name)
    partitions = info['partitions']

    for num in range(1, partitions + 1):
        storage.truncate('%s-%s' % (queue_name, num))

    if request.params.get('delete') != 'false':
        meta.remove_queue(request.app_key, queue_name)
    return {'status': 'ok'}


@queues.post(permission='new_message')
def new_message(request):
    """Post a message to a queue

    Headers

        X-Application-Key - The applications key
        X-Partition - (`Optional`) A specific partition number to
                      insert the message into. Defaults to a random
                      partition number for the amount of partitions
                      registered.

    URL Params

        queue_name - A UUID4 hex string to use as the queue name.

    POST body

        A message string to store.

    Example success response::

        {
            'status': 'ok',
            'key': '3a6592301e0911e190b1002500f0fa7c',
            'partition': 1
        }

    """
    queue_name = request.matchdict['queue_name']
    if len(request.body) <= 0:
        raise HTTPBadRequest("Failure to provide message body.")

    if 'X-Partition' in request.headers:
        try:
            partition = int(request.headers['X-Partition'])
        except (ValueError, TypeError):
            return HTTPBadRequest("Invalid 'X-Partition' header value")
    else:
        meta = request.registry['backend_metadata']
        info = meta.queue_information(request.app_key, queue_name)
        partitions = info['partitions']
        partition = random.randint(1, partitions)

    storage = request.registry['backend_storage']
    message_key = storage.push('%s-%s' % (queue_name, partition),
                               request.body)
    return {
        'status': 'ok',
        'key': message_key.hex,
        'partition': partition
    }


@queues.get(permission='view_message')
def get_messages(request):
    """Get messages from a queue

    Headers

        X-Application-Key - The applications key

    URL Params

        queue_name - A UUID4 hex string to use as the queue name.

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
                    'body': 'jlaijwiel2432532jilj'
                },
                {
                    'key': '3a8553d71e0911e19262002500f0fa7c',
                    'body': 'ion12oibasdfjioawneilnf'
                }
            ]
        }

    """
    queue_name = request.matchdict['queue_name']
    limit = valid_int(request.GET, 'limit')
    timestamp = valid_float(request.GET, 'since_timestamp')

    order = request.GET.get('order', 'descending')
    if order and order not in ['ascending', 'descending']:
        raise HTTPBadRequest("Order parameter is invalid")

    partition = 1
    if 'partition' in request.GET:
        try:
            partition = int(request.GET['partition'])
        except (ValueError, TypeError):
            return HTTPBadRequest("Partition parameter is invalid")

    storage = request.registry['backend_storage']
    messages = storage.retrieve('%s-%s' % (queue_name, partition), limit,
                                timestamp, order)
    message_data = [{'key': key.hex, 'body': body} for key, body in messages]
    return {'status': 'ok', 'messages': message_data}
