import unittest
import uuid
import os

from nose.tools import raises

from simplejson import loads
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

    def test_new_queue(self):
        from queuey.views import new_queue
        app_key = uuid.uuid4().hex
        request = testing.DummyRequest(headers={'ApplicationKey': app_key})
        info = new_queue(request)
        self.assertEqual(info['status'], 'ok')

    def test_delete_queue(self):
        from queuey.views import new_queue, delete_queue
        app_key = uuid.uuid4().hex
        request = testing.DummyRequest(headers={'ApplicationKey': app_key})
        info = new_queue(request)
        self.assertEqual(info['status'], 'ok')
        queue_name = info['queue_name']

        # Now delete it
        request = testing.DummyRequest(headers={'ApplicationKey': app_key})
        request.matchdict = {'queue_name': queue_name}
        info = delete_queue(request)
        self.assertEqual(info['status'], 'ok')

        # Ensure that we throw an error if the queue doesn't exist
        from queuey.exceptions import ApplicationNotRegistered
        @raises(ApplicationNotRegistered)
        def test_it():
            app_key = uuid.uuid4().hex
            request = testing.DummyRequest(headers={'ApplicationKey': app_key})
            request.matchdict = {'queue_name': queue_name}
            info = delete_queue(request)
        test_it()
