import unittest
import uuid
import os

from nose.tools import raises

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

    def test_add_app_key_wrapper(self):
        from queuey.views import add_app_key
        from queuey.views import new_queue
        from pyramid.httpexceptions import HTTPBadRequest

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

    def test_new_queue(self):
        from queuey.views import new_queue
        app_key = uuid.uuid4().hex
        request = testing.DummyRequest()
        request.app_key = app_key
        request.app_name = 'notifications'
        info = new_queue(request)
        self.assertEqual(info['status'], 'ok')
        self.assertEqual(info['partitions'], 1)
        self.assertEqual(info['application_name'], 'notifications')

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
