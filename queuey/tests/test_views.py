import unittest
import uuid

from simplejson import loads
from pyramid import testing

class ViewTests(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

        # Create the metadata
        from queuey.storage.cassandra import CassandraMetadata
        from queuey.storage.cassandra import CassandraQueueBackend
        self.config.registry['backend_metadata'] = CassandraMetadata()
        self.config.registry['backend_storage'] = CassandraQueueBackend()

    def tearDown(self):
        testing.tearDown()

    def test_new_queue(self):
        from queuey.views import new_queue
        app_key = uuid.uuid4().hex
        request = testing.DummyRequest(headers={'ApplicationKey': app_key})
        info = new_queue(request)
        self.assertEqual(info['status'], 'ok')
