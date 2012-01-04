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

from queuey.exceptions import ApplicationNotRegistered
from queuey.validators import appkey_check
from queuey.validators import delete_check
from queuey.validators import message_get_check
from queuey.validators import messagebody_check
from queuey.validators import queuename_check
from queuey.validators import partition_check
from queuey.validators import partionheader_check


# Services
message_queue = Service(name='message_queues', path='/queue/')
queues = Service(name='queues', path='/queue/{queue_name:[a-z0-9]{32}}/')


@message_queue.post(permission='create_queue',
                    validators=(appkey_check, partition_check))
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
    partitions = request.validated['partitions']
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


@message_queue.get(permission='view_queue',
                   validators=(appkey_check, queuename_check))
def get_queue(request):
    """Get queue information

    Headers

        X-Application-Key - The applications key

    Query Params

        queue_name - The name of a specific queue to retrieve
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
    queue_name = request.validated['queue_name']
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


@queues.delete(permission='delete_queue',
               validators=(appkey_check, partionheader_check, delete_check))
def delete_queue(request):
    """Delete a queue

    Headers

        X-Application-Key - The applications key
        X-Partition - (`Optional`) A specific partition number to
                      delete from.

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


@queues.post(permission='new_message',
             validators=(appkey_check, partionheader_check, messagebody_check))
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


@queues.get(permission='view_message',
            validators=(appkey_check, message_get_check))
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
