import unittest
import uuid
import os

from nose.tools import raises


def setup_module():
    from queuey.storage.cassandra import CassandraMetadata
    host = os.environ.get('TEST_CASSANDRA_HOST', 'localhost')
    backend = CassandraMetadata(host)
    backend.app_fam.remove(backend.row_key)
    backend.app_fam.remove('myapp')


class TestCassandraStore(unittest.TestCase):
    def _makeOne(self):
        from queuey.storage.cassandra import CassandraQueueBackend
        host = os.environ.get('TEST_CASSANDRA_HOST', 'localhost')
        return CassandraQueueBackend(host)

    def test_parsehosts(self):
        from queuey.storage.cassandra import parse_hosts
        hosts = parse_hosts('localhost')
        self.assertEqual(hosts, ['localhost:9160'])

        hosts = parse_hosts('192.168.2.1,192.168.2.3:9180 , 192.168.2.19')
        self.assertEqual(hosts,
            ['192.168.2.1:9160', '192.168.2.3:9180', '192.168.2.19:9160'])

    def test_noqueue(self):
        backend = self._makeOne()
        queue_name = uuid.uuid4().hex
        existing = backend.retrieve(queue_name)
        self.assertEqual([], existing)

    def test_onemessage(self):
        backend = self._makeOne()
        payload = 'a rather boring payload'
        queue_name = uuid.uuid4().hex
        backend.push(queue_name, payload)
        existing = backend.retrieve(queue_name)
        self.assertEqual(existing[0][1], payload)

    def test_message_ordering(self):
        backend = self._makeOne()
        payload = 'a rather boring payload'
        another = 'another payload'
        queue_name = uuid.uuid4().hex
        backend.push(queue_name, payload)
        backend.push(queue_name, another)
        existing = backend.retrieve(queue_name)
        self.assertEqual(2, len(existing))
        self.assertEqual(existing[1][1], payload)

        existing = backend.retrieve(queue_name, order='ascending')
        self.assertEqual(existing[1][1], another)

    def test_message_addition(self):
        backend = self._makeOne()
        payload = 'a rather boring payload'
        queue_name = uuid.uuid4().hex
        backend.push(queue_name, payload)

        self.assertEqual(False, backend.exists(uuid.uuid4().hex))
        self.assertEqual(True, backend.exists(queue_name))


class TestCassandraMetadata(unittest.TestCase):
    def tearDown(self):
        backend = self._makeOne()
        backend.app_fam.remove('myapp')
        backend.app_fam.remove(backend.row_key)

    def _makeOne(self):
        from queuey.storage.cassandra import CassandraMetadata
        host = os.environ.get('TEST_CASSANDRA_HOST', 'localhost')
        return CassandraMetadata(host)

    def _makeQB(self):
        from queuey.storage.cassandra import CassandraQueueBackend
        host = os.environ.get('TEST_CASSANDRA_HOST', 'localhost')
        return CassandraQueueBackend(host)

    def test_register_application(self):
        from queuey.exceptions import ApplicationExists
        backend = self._makeOne()
        backend.register_application('notifications')

        # Ensure it works by testing for a raise here
        @raises(ApplicationExists)
        def testit():
            backend.register_application('notifications')
        testit()

    def test_add_queue(self):
        from queuey.exceptions import QueueAlreadyExists
        backend = self._makeOne()
        backend.register_application('myapp')
        backend.register_queue('myapp', 'fredrick')

        # Ensure we get an exception on a repeat
        @raises(QueueAlreadyExists)
        def testit():
            backend.register_queue('myapp', 'fredrick')
        testit()

    def test_add_queue_not_regged(self):
        from queuey.exceptions import ApplicationNotRegistered
        backend = self._makeOne()

        @raises(ApplicationNotRegistered)
        def testit():
            backend.register_queue('myapp', 'fredrick')
        testit()
