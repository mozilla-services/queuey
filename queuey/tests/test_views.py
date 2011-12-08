import unittest
import uuid
import os
import time

from nose.tools import raises

from pyramid import testing
from pyramid.httpexceptions import HTTPBadRequest
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

    def test_add_app_key_wrapper(self):
        from queuey.views import add_app_key
        from queuey.views import new_queue

        app_key = uuid.uuid4().hex
        request = testing.DummyRequest(headers={'X-Application-Key': app_key})
        request.registry['app_keys'] = {app_key: 'notty'}

        def view_wrap(context, request):
            return new_queue(request)
        new_view = add_app_key(view_wrap)
        info = new_view(None, request)
        self.assertEqual(info['status'], 'ok')
        self.assertEqual(info['partitions'], 1)
        self.assertEqual(info['application_name'], 'notty')

        @raises(HTTPBadRequest)
        def testit():
            request = testing.DummyRequest()
            new_view(None, request)
        testit()

        @raises(HTTPBadRequest)
        def testits():
            request = testing.DummyRequest(headers={'X-Application-Key': app_key})
            request.registry['app_keys'] = {}
            new_view(None, request)
        testits()

    def test_new_queue_and_info(self):
        from queuey.views import new_queue, get_queue
        app_key = uuid.uuid4().hex
        request = testing.DummyRequest()
        request.app_key = app_key
        request.app_name = 'notifications'
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

        @raises(HTTPBadRequest)
        def testit():
            get_queue(request)
        testit()

    def test_delete_queue(self):
        from queuey.views import new_queue, delete_queue
        app_key = uuid.uuid4().hex
        request = testing.DummyRequest()
        request.app_key = app_key
        request.app_name = 'notifications'
        info = new_queue(request)
        self.assertEqual(info['status'], 'ok')
        queue_name = info['queue_name']

        # Now delete it
        request = testing.DummyRequest()
        request.app_key = app_key
        request.app_name = 'notifications'
        request.matchdict = {'queue_name': queue_name}
        info = delete_queue(request)
        self.assertEqual(info['status'], 'ok')

    def test_new_messages_and_get(self):
        from queuey.views import new_queue, new_message, get_messages
        app_key = uuid.uuid4().hex
        request = testing.DummyRequest()
        request.app_key = app_key
        request.app_name = 'notifications'
        info = new_queue(request)
        self.assertEqual(info['status'], 'ok')

        queue_name = info['queue_name']
        request.matchdict['queue_name'] = queue_name

        @raises(HTTPBadRequest)
        def testit():
            request.body = ''
            new_message(request)
        testit()

        request.body = 'this is a message!'
        info = new_message(request)
        self.assertEqual(info['status'], 'ok')
        self.assertEqual(info['partition'], 1)
        assert 'key' in info

        # Get the message
        request = testing.DummyRequest()
        request.app_key = app_key
        request.app_name = 'notifications'
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

        request = testing.DummyRequest()
        request.app_key = app_key
        request.app_name = 'notifications'
        request.matchdict['queue_name'] = queue_name
        request.GET['since_timestamp'] = str(now)
        request.GET['order'] = 'ascending'
        info = get_messages(request)
        self.assertEqual(info['status'], 'ok')
        self.assertEqual(info['messages'][0]['body'], 'this is another message!')
        self.assertEqual(len(info['messages']), 1)

        del request.GET['since_timestamp']
        request.GET['order'] = 'ascending'
        request.GET['limit'] = '1'
        info = get_messages(request)
        self.assertEqual(info['status'], 'ok')
        self.assertEqual(info['messages'][0]['body'], 'this is a message!')
        self.assertEqual(len(info['messages']), 1)
