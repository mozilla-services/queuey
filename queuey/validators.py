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


def delete_check(request):
    """Checks if a delete arg is present, and it must be false"""
    if 'delete' in request.GET:
        if request.GET['delete'] == 'false':
            request.validated['delete'] = 'false'
        else:
            request.errors.add('url', 'delete', "Delete must be 'false' if "
                               "specified.")


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
