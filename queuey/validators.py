# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import uuid

import simplejson


def appkey_check(request):
    if 'X-Application-Key' not in request.headers:
        request.errors.add('header', 'X-Application-Key', 'You must provide '
                           'a valid application key.')
        return
    app_key = request.headers['X-Application-Key']
    app_name = request.registry['app_keys'].get(app_key)
    if not app_name:
        request.errors.add('header', 'X-Application-Key', 'You must provide '
                           'a valid application key.')
        return
    request.app_name = app_name
    request.app_key = app_key


def partition_check(request):
    """Checks that partition is correct if supplied"""
    partitions = request.POST.get('partitions')
    if not partitions:
        request.validated['partitions'] = 1
        return
    try:
        request.validated['partitions'] = int(partitions)
    except (ValueError, TypeError):
        request.errors.add('body', 'partitions', "Partitions parameter is "
                           "invalid")


def queuename_check(request):
    """Checks that a queue-name was specified"""
    queue_name = request.GET.get('queue_name')
    if not queue_name:
        request.errors.add('url', 'queue_name', "No queue_name specified.")
    else:
        request.validated['queue_name'] = queue_name


def queuename_postcheck(request):
    queue_name = request.POST.get('queue_name', uuid.uuid4().hex)
    request.validated['queue_name'] = queue_name


def delete_check(request):
    """Checks if a delete arg is present, and it must be false"""
    if 'delete' in request.GET:
        if request.GET['delete'] == 'false':
            request.validated['delete'] = 'false'
        else:
            request.errors.add('url', 'delete', "Delete must be 'false' if "
                               "specified.")

    if len(request.body) > 0:
        try:
            body = simplejson.loads(request.body)
        except simplejson.JSONDecodeError:
            request.errors.add('body', '', "Body was present but not JSON.")
            return
        if not isinstance(body, dict):
            request.errors.add('body', '', "Body must be a JSON dict.")
        if 'messages' not in body:
            request.errors.add('body', 'messages', "Not present in JSON body.")
        if 'messages' in body and not body['messages']:
            request.errors.add('body', 'messages', "Invalid messages "
                               "argument, must be a list of message keys.")

        if not request.errors:
            request.validated['messages'] = body['messages']


def partionheader_check(request):
    """Checks for a X-Partition header"""
    partition = request.headers.get('X-Partition')
    if partition:
        try:
            request.validated['partition'] = int(partition)
        except (ValueError, TypeError):
            request.errors.add('header', 'X-Partition', "The 'X-Partition' "
                               "header must be an integer.")


def messagebody_check(request):
    if len(request.body) <= 0:
        request.errors.add('body', "[Content]", "No body content present.")


def message_get_check(request):
    """Checks for the valid arguments for get messages"""
    request.validated['limit'] = valid_int(request, request.GET, 'limit') \
        or 100
    request.validated['since_timestamp'] = valid_float(request, request.GET,
                                                      'since_timestamp')
    request.validated['partition'] = valid_int(request, request.GET,
                                               'partition') or 1

    order = request.GET.get('order', 'descending')
    if order and order not in ['ascending', 'descending']:
        request.errors.add('url', 'order', "Order parameter must be either "
                           "'descending' or 'ascending'.")
    else:
        request.validated['order'] = order


def valid_int(request, dct, name):
    """Gets the name from the dct and ensures its an int if present"""
    if name not in dct:
        return None
    try:
        return int(dct[name])
    except (ValueError, TypeError):
        request.errors.add('url', name, "%s must be an integer." % name)


def valid_float(request, dct, name):
    """Gets the name from the dct and ensures its an float if present"""
    if name not in dct:
        return None
    try:
        return float(dct[name])
    except (ValueError, TypeError):
        request.errors.add('url', name, "%s must be a float" % name)
