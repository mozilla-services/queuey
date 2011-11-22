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
from datetime import datetime
import uuid

from cornice.service import Service
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.response import Response
import simplejson as json

from queuey.exceptions import ApplicationNotRegistered

# Services
message_queue = Service(name='message_queues', path='/queue/')
queues = Service(name='queues', path='/queue/{queue_name}/')


@message_queue.post(permission='create_queue')
def new_queue(request):
    """Create a new queue

    Creates a new queue.

    POST params

        queue_name - (Optional) A UUID4 hex string to use as the
                     queue name.

    Returns a JSON response indicating the status, and the name of the
    queue.

    Example success response::

        {'status': 'ok', 'queue_name': 'ea2f39c0de9a4b9db6463123641631de'}

    """
    app_key = _extract_app_key(request.headers)
    meta = request.registry['backend_metadata']
    queue_name = request.POST.get('queue_name', uuid.uuid4().hex)
    try:
        meta.register_queue(app_key, queue_name)
    except ApplicationNotRegistered:
        meta.register_application(app_key)
        meta.register_queue(app_key, queue_name)
    return {'status': 'ok', 'queue_name': queue_name}


@queues.delete(permission='delete_queue')
def delete_queue(request):
    """Delete a queue

    URL Params

        queue_name - A UUID4 hex string to use as the queue name.

    Example success response::

        {'status': 'ok'}

    """
    app_key, queue_name = _extract_app_queue_info(request)
    storage = request.registry['backend_storage']
    if request.params.get('delete') == 'false':
        storage.truncate(queue_name)
    else:
        meta = request.registry['backend_metadata']
        meta.remove_queue(app_key, queue_name)
        storage.truncate(queue_name)
    return {'status': 'ok'}


@queues.post(permission='new_message')
def new_message(request):
    """Post a message to a queue

    URL Params

        queue_name - A UUID4 hex string to use as the queue name.

    POST body

        A message string to store.

    Example success response::

        {'status': 'ok'}

    """
    app_key, queue_name = _extract_app_queue_info(request)
    if not request.body:
        raise HTTPBadRequest("Failure to provide message body.")
    storage = request.registry['backend_storage']
    storage.push(queue_name, request.POST['message'])
    return {'status': 'ok'}


@queues.get()
def get_messages(request):
    """Get messages from a queue

    URL Params

        queue_name - A UUID4 hex string to use as the queue name.

    Query Params

        since_timestamp - (`Optional`) All messages newer than this timestamp,
                          should be formatted as seconds since epoch in GMT
        limit           - (`Optional`) Only return N amount of messages
        order           - (`Optional`) Order of messages, can be set to either
                          `ascending` or `descending`. Defaults to `descending`.

    Messages are returned in order of newest to oldest.

    """
    queue_name = _extract_queue_name(request)

    limit = request.GET.get('limit')
    if limit:
        try:
            limit = int(limit)
        except ValueError:
            raise HTTPBadRequest("Invalid limit param provided")

    order = request.GET.get('order')
    if order and order not in ['ascending', 'descending']:
        raise HTTPBadRequest("Invalid order param provided")

    timestamp = request.GET.get('since_timestamp')
    if timestamp:
        try:
            timestamp = int(timestamp)
        except ValueError:
            raise HTTPBadRequest("Timestamp parameter must be an integer")
        try:
            timestamp = datetime.utcfromtimestamp(timestamp)
        except ValueError:
            raise HTTPBadRequest("Timestamp parameter is invalid")

    storage = request.registry['backend_storage']
    # Retrieve and fixup the structure, avoid deserializing the
    # JSON content from the db
    messages = storage.retrieve(queue_name, limit, timestamp, order)
    message_data = [{'key': key.hex, 'body': body} for key, body in messages]
    envelope = json.dumps({'status': 'ok', 'messages': message_data})
    return Response(body=envelope, content_type='application/json')


## Utility extraction methods

def _extract_app_key(headers):
    app_key = headers.get('ApplicationKey')
    if not app_key:
        raise HTTPBadRequest("Failure to provide ApplicationKey")
    return app_key


def _extract_queue_name(request):
    queue_name = request.matchdict.get('queue_name')
    if not queue_name:
        raise HTTPBadRequest("Failure to provide queue_name")
    return queue_name


def _extract_app_queue_info(request):
    app_key, queue_name = _extract_app_key(request.headers), \
        _extract_queue_name(request)
    return app_key, queue_name
