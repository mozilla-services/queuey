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
        request = testing.DummyRequest(headers={'X-Application-Key': 'ff'})
        request.registry['app_keys'] = {'ff': 'notifications'}
        info = new_queue(request)
        self.assertEqual(info['status'], 'ok')
        self.assertEqual(info['partitions'], 1)
        self.assertEqual(info['application_name'], 'notifications')

        request.GET['queue_name'] = info['queue_name']
        data = get_queue(request)
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
        from queuey.views import new_queue, delete_queue
        app_key = uuid.uuid4().hex
        request = testing.DummyRequest(headers={'X-Application-Key': app_key})
        request.registry['app_keys'] = {app_key: 'notifications'}
        info = new_queue(request)
        self.assertEqual(info['status'], 'ok')
        queue_name = info['queue_name']

        # Delete with bad delete value
        request = testing.DummyRequest(headers={'X-Application-Key': app_key})
        request.registry['app_keys'] = {app_key: 'notifications'}
        request.matchdict = {'queue_name': queue_name}
        request.GET['delete'] = 'fred'
        info = delete_queue(request)
        assert "Delete must be 'false' if specified" in info.body

        # Test truncate first
        request = testing.DummyRequest(headers={'X-Application-Key': app_key})
        request.registry['app_keys'] = {app_key: 'notifications'}
        request.matchdict = {'queue_name': queue_name}
        request.GET['delete'] = 'false'
        info = delete_queue(request)
        self.assertEqual(info['status'], 'ok')

        # Now delete it
        request = testing.DummyRequest(headers={'X-Application-Key': app_key})
        request.registry['app_keys'] = {app_key: 'notifications'}
        request.matchdict = {'queue_name': queue_name}
        info = delete_queue(request)
        self.assertEqual(info['status'], 'ok')

    def test_new_messages_and_get(self):
        from queuey.views import new_queue, new_message, get_messages
        app_key = uuid.uuid4().hex
        request = testing.DummyRequest(headers={'X-Application-Key': app_key})
        request.registry['app_keys'] = {app_key: 'notifications'}
        info = new_queue(request)
        self.assertEqual(info['status'], 'ok')

        queue_name = info['queue_name']
        request.matchdict['queue_name'] = queue_name

        request.body = ''
        info = new_message(request)
        assert 'No body content present' in info.body

        request = testing.DummyRequest(headers={'X-Application-Key': app_key})
        request.registry['app_keys'] = {app_key: 'notifications'}
        request.matchdict['queue_name'] = queue_name
        request.body = 'this is a message!'
        info = new_message(request)
        self.assertEqual(info['status'], 'ok')
        self.assertEqual(info['partition'], 1)
        assert 'key' in info

        # Get the message
        request = testing.DummyRequest(headers={'X-Application-Key': app_key})
        request.registry['app_keys'] = {app_key: 'notifications'}
        request.matchdict['queue_name'] = queue_name
        info = get_messages(request)
        self.assertEqual(info['status'], 'ok')
        self.assertEqual(info['messages'][0]['body'], 'this is a message!')

        # Add another message, and fetch JUST that one
        now = time.time()
        request.body = 'this is another message!'
        info = new_message(request)
        self.assertEqual(info['status'], 'ok')
        self.assertEqual(info['partition'], 1)
        assert 'key' in info

        request = testing.DummyRequest(headers={'X-Application-Key': app_key})
        request.registry['app_keys'] = {app_key: 'notifications'}
        request.matchdict['queue_name'] = queue_name
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
        request = testing.DummyRequest(headers={'X-Application-Key': app_key})
        request.registry['app_keys'] = {app_key: 'notifications'}
        request.matchdict['queue_name'] = queue_name
        request.GET['order'] = 'backwards'
        info = get_messages(request)
        assert 'Order parameter must be either' in info.body

        request = testing.DummyRequest(headers={'X-Application-Key': app_key})
        request.registry['app_keys'] = {app_key: 'notifications'}
        request.matchdict['queue_name'] = queue_name
        request.GET['order'] = 'ascending'
        request.GET['limit'] = '1'
        info = get_messages(request)
        self.assertEqual(info['status'], 'ok')
        self.assertEqual(info['messages'][0]['body'], 'this is a message!')
        self.assertEqual(len(info['messages']), 1)

    def test_new_messages_with_partitions(self):
        from queuey.views import new_queue, new_message, get_messages
        app_key = uuid.uuid4().hex
        request = testing.DummyRequest(headers={'X-Application-Key': app_key})
        request.registry['app_keys'] = {app_key: 'notifications'}
        request.POST['partitions'] = 5
        info = new_queue(request)
        self.assertEqual(info['status'], 'ok')

        queue_name = info['queue_name']
        request.matchdict['queue_name'] = queue_name

        request.body = 'this is a message!'
        request.headers['X-Partition'] = '2'
        info = new_message(request)
        self.assertEqual(info['status'], 'ok')
        self.assertEqual(info['partition'], 2)

        # Bad partition
        request.headers['X-Partition'] = 'smith'
        info = new_message(request)
        assert "The 'X-Partition' header must be an integer" in info.body

        request = testing.DummyRequest(headers={'X-Application-Key': app_key})
        request.registry['app_keys'] = {app_key: 'notifications'}
        request.matchdict['queue_name'] = queue_name
        request.body = 'this is a message!'
        info = new_message(request)
        self.assertEqual(info['status'], 'ok')
        part = info['partition']
        assert 'key' in info

        # Get the message
        request = testing.DummyRequest(headers={'X-Application-Key': app_key})
        request.registry['app_keys'] = {app_key: 'notifications'}
        request.matchdict['queue_name'] = queue_name
        request.GET['partition'] = str(part)
        info = get_messages(request)
        self.assertEqual(info['status'], 'ok')
        self.assertEqual(info['messages'][0]['body'], 'this is a message!')

        # Invalid partition
        request.GET['partition'] = 'blah'

        info = get_messages(request)
        assert "partition must be an integer" in info.body
