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
        request = testing.DummyRequest()
        request.app_key = app_key
        request.app_name = 'notifications'
        request.validated = {}
        if queue_name:
            request.matchdict = {'queue_name': queue_name}
        return request

    def _new_queue(self, app_key):
        from queuey.views import new_queue
        request = self._new_request(app_key)
        request.validated['partitions'] = 1
        return new_queue(request)

    def _get_queue(self, app_key, queue_name):
        from queuey.views import get_queue
        request = self._new_request(app_key)
        request.validated['queue_name'] = queue_name
        return get_queue(request)

    def _new_message(self, app_key, queue_name, body, partition=None):
        from queuey.views import new_message
        request = self._new_request(app_key, queue_name)
        if partition:
            request.validated['partition'] = int(partition)
        request.body = body
        return new_message(request)

    def _get_messages(self, app_key, queue_name, partition=None):
        from queuey.views import get_messages
        request = self._new_request(app_key, queue_name)
        request.validated['partition'] = int(partition) if partition else 1
        request.validated['limit'] = 100
        request.validated['since_timestamp'] = None
        request.validated['order'] = 'descending'
        return get_messages(request)

    def test_new_queue_and_info(self):
        app_key = uuid.uuid4().hex
        info = self._new_queue(app_key)
        self.assertEqual(info['status'], 'ok')
        self.assertEqual(info['partitions'], 1)
        self.assertEqual(info['application_name'], 'notifications')

        data = self._get_queue(app_key, info['queue_name'])
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['application_name'], 'notifications')

    def test_delete_queue(self):
        from queuey.views import delete_queue
        app_key = uuid.uuid4().hex
        info = self._new_queue(app_key)
        queue_name = info['queue_name']

        # Test truncate first
        request = self._new_request(app_key, queue_name)
        request.validated['delete'] = 'false'
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
        request.validated['delete'] = 'false'
        request.validated['messages'] = [key1]
        info = delete_queue(request)
        self.assertEqual(info['status'], 'ok')

    def test_new_messages_and_get(self):
        from queuey.views import get_messages
        app_key = uuid.uuid4().hex
        info = self._new_queue(app_key)
        queue_name = info['queue_name']

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
        request.validated['since_timestamp'] = now
        request.validated['order'] = 'ascending'
        request.validated['partition'] = 1
        request.validated['limit'] = 100
        info = get_messages(request)
        self.assertEqual(info['status'], 'ok')
        self.assertEqual(info['messages'][0]['body'], 'this is another message!')
        self.assertEqual(len(info['messages']), 1)

        request = self._new_request(app_key, queue_name)
        request.validated['since_timestamp'] = now
        request.validated['order'] = 'descending'
        request.validated['limit'] = '1'
        request.validated['partition'] = 1
        request.validated['limit'] = 100
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

        info = self._new_message(app_key, queue_name, 'this is a message!')
        self.assertEqual(info['status'], 'ok')
        part = info['partition']
        assert 'key' in info

        # Get the message
        info = self._get_messages(app_key, queue_name, partition=str(part))
        self.assertEqual(info['status'], 'ok')
        self.assertEqual(info['messages'][0]['body'], 'this is a message!')
