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
import unittest
import uuid
import os
import time

import simplejson

from pyramid import testing
from pyramid.util import DottedNameResolver

dotted_resolver = DottedNameResolver(None)


class ViewTests(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

        storage_settings = dict(
            filter(lambda x: x[0].startswith('TEST_STORAGE_'),
                   os.environ.items()))
        metadata_settings = dict(
            filter(lambda x: x[0].startswith('TEST_METADATA_'),
                   os.environ.items()))

        for obj in [storage_settings, metadata_settings]:
            for key in obj:
                prefix = 'storage.' if 'STORAGE' in key else 'metadata.'
                k = key.lstrip('TEST_STORAGE_')
                k = k.lstrip('TEST_METADATA_')
                k = k.lower()
                obj[prefix + k] = obj.pop(key)
        from queuey.storage import configure_from_settings

        # Create the metadata
        self.config.registry['backend_storage'] = configure_from_settings(
            'storage', storage_settings)
        self.config.registry['backend_metadata'] = configure_from_settings(
            'metadata', metadata_settings)

    def tearDown(self):
        testing.tearDown()

    def _new_request(self, app_key, queue_name=None):
        request = testing.DummyRequest(headers={'X-Application-Key': app_key})
        request.registry['app_keys'] = {app_key: 'notifications'}
        if queue_name:
            request.matchdict = {'queue_name': queue_name}
        return request

    def _new_queue(self, app_key):
        from queuey.views import new_queue
        return new_queue(self._new_request(app_key))

    def _get_queue(self, app_key, queue_name):
        from queuey.views import get_queue
        request = self._new_request(app_key)
        request.GET['queue_name'] = queue_name
        return get_queue(request)

    def _new_message(self, app_key, queue_name, body, partition=None):
        from queuey.views import new_message
        request = self._new_request(app_key, queue_name)
        if partition:
            request.headers['X-Partition'] = partition
        request.body = body
        return new_message(request)

    def _get_messages(self, app_key, queue_name, partition=None):
        from queuey.views import get_messages
        request = self._new_request(app_key, queue_name)
        if partition:
            request.GET['partition'] = partition
        return get_messages(request)

    def test_bad_app_key(self):
        from queuey.views import new_queue
        app_key = uuid.uuid4().hex
        request = testing.DummyRequest(headers={'X-Application-Key': 'ff'})
        request.registry['app_keys'] = {app_key: 'notifications'}
        info = new_queue(request)
        assert "You must provide a valid application key" in info.body

    def test_new_queue_and_info(self):
        from queuey.views import new_queue, get_queue
        app_key = uuid.uuid4().hex
        info = self._new_queue(app_key)
        self.assertEqual(info['status'], 'ok')
        self.assertEqual(info['partitions'], 1)
        self.assertEqual(info['application_name'], 'notifications')

        data = self._get_queue(app_key, info['queue_name'])
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['application_name'], 'notifications')

        request = testing.DummyRequest()
        request.app_key = app_key
        request.app_name = 'notifications'

        # Bad queue
        data = get_queue(request)
        assert "No queue_name specified" in data.body

        # bad partition
        request = testing.DummyRequest()
        request.app_key = app_key
        request.app_name = 'notifications'
        request.POST['partitions'] = 'fred'
        resp = new_queue(request)
        assert 'Partitions parameter is invalid' in resp.body

    def test_delete_queue(self):
        from queuey.views import delete_queue
        app_key = uuid.uuid4().hex
        info = self._new_queue(app_key)
        queue_name = info['queue_name']

        # Delete with bad delete value
        request = self._new_request(app_key, queue_name)
        request.GET['delete'] = 'fred'
        info = delete_queue(request)
        assert "Delete must be 'false' if specified" in info.body

        # Test truncate first
        request = self._new_request(app_key, queue_name)
        request.GET['delete'] = 'false'
        info = delete_queue(request)
        self.assertEqual(info['status'], 'ok')

        # Now delete it
        request = self._new_request(app_key, queue_name)
        info = delete_queue(request)
        self.assertEqual(info['status'], 'ok')

    def test_delete_queue_messages(self):
        from queuey.views import delete_queue
        app_key = uuid.uuid4().hex
        info = self._new_queue(app_key)
        queue_name = info['queue_name']

        key1 = self._new_message(app_key, queue_name, 'hello all!')['key']

        request = self._new_request(app_key, queue_name)
        request.GET['delete'] = 'false'
        request.body = simplejson.dumps({'messages': [key1]})
        info = delete_queue(request)
        self.assertEqual(info['status'], 'ok')

        # Bad body
        request.body = 'meff'
        info = delete_queue(request)
        assert 'Body was present but not JSON' in info.body

        request.body = simplejson.dumps(range(20))
        info = delete_queue(request)
        assert 'Body must be a JSON dict' in info.body

        request.body = simplejson.dumps({'messages': []})
        info = delete_queue(request)
        assert 'Invalid messages' in info.body

    def test_new_messages_and_get(self):
        from queuey.views import get_messages
        app_key = uuid.uuid4().hex
        info = self._new_queue(app_key)
        queue_name = info['queue_name']

        info = self._new_message(app_key, queue_name, '')
        assert 'No body content present' in info.body

        info = self._new_message(app_key, queue_name, 'this is a message!')
        self.assertEqual(info['status'], 'ok')
        self.assertEqual(info['partition'], 1)
        assert 'key' in info

        # Get the message
        info = self._get_messages(app_key, queue_name)
        self.assertEqual(info['status'], 'ok')
        self.assertEqual(info['messages'][0]['body'], 'this is a message!')

        # Add another message, and fetch JUST that one
        now = time.time()
        info = self._new_message(app_key, queue_name, 'this is another message!')
        self.assertEqual(info['status'], 'ok')
        self.assertEqual(info['partition'], 1)
        assert 'key' in info

        request = self._new_request(app_key, queue_name)
        request.GET['since_timestamp'] = repr(now)
        request.GET['order'] = 'ascending'
        info = get_messages(request)
        self.assertEqual(info['status'], 'ok')
        self.assertEqual(info['messages'][0]['body'], 'this is another message!')
        self.assertEqual(len(info['messages']), 1)

        # Bad float
        request.GET['since_timestamp'] = 'smith'
        info = get_messages(request)
        assert 'since_timestamp must be a float' in info.body
        del request.GET['since_timestamp']

        # Bad order
        request = self._new_request(app_key, queue_name)
        request.GET['order'] = 'backwards'
        info = get_messages(request)
        assert 'Order parameter must be either' in info.body

        request = self._new_request(app_key, queue_name)
        request.GET['order'] = 'ascending'
        request.GET['limit'] = '1'
        info = get_messages(request)
        self.assertEqual(info['status'], 'ok')
        self.assertEqual(info['messages'][0]['body'], 'this is a message!')
        self.assertEqual(len(info['messages']), 1)

    def test_new_messages_with_partitions(self):
        app_key = uuid.uuid4().hex
        info = self._new_queue(app_key)
        queue_name = info['queue_name']

        info = self._new_message(app_key, queue_name, 'this is a message!',
                                 partition='2')
        self.assertEqual(info['status'], 'ok')
        self.assertEqual(info['partition'], 2)

        # Bad partition
        info = self._new_message(app_key, queue_name, 'this is a message!',
                                 partition='smith')
        assert "The 'X-Partition' header must be an integer" in info.body

        info = self._new_message(app_key, queue_name, 'this is a message!')
        self.assertEqual(info['status'], 'ok')
        part = info['partition']
        assert 'key' in info

        # Get the message
        info = self._get_messages(app_key, queue_name, partition=str(part))
        self.assertEqual(info['status'], 'ok')
        self.assertEqual(info['messages'][0]['body'], 'this is a message!')

        # Invalid partition
        info = self._get_messages(app_key, queue_name, partition='blah')
        assert "partition must be an integer" in info.body
