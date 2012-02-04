# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import unittest
import uuid
import time
import os

from nose.tools import raises
import mock


def setup_module():
    from queuey.storage.cassandra import CassandraMetadata
    host = os.environ.get('TEST_CASSANDRA_HOST', 'localhost')
    backend = CassandraMetadata(host)
    backend.app_fam.remove(backend.row_key)
    backend.app_fam.remove('myapp')


class TestCassandraStore(unittest.TestCase):
    def _makeOne(self, **kwargs):
        from queuey.storage.cassandra import CassandraQueueBackend
        host = os.environ.get('TEST_CASSANDRA_HOST', 'localhost')
        return CassandraQueueBackend(host, **kwargs)

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
        self.assertEqual(existing[0][2], payload)

    def test_delay(self):
        backend = self._makeOne(delay=10)
        payload = 'a rather boring payload'
        queue_name = uuid.uuid4().hex
        backend.push(queue_name, payload)
        existing = backend.retrieve(queue_name)
        self.assertEqual(existing, [])
        time_func = time.time
        with mock.patch('time.time') as mock_time:
            mock_time.return_value = time_func() + 9
            existing = backend.retrieve(queue_name)
            self.assertEqual(existing, [])
            mock_time.return_value = time_func() + 10
            existing = backend.retrieve(queue_name)
            self.assertEqual(existing[0][2], payload)

    def test_message_ordering(self):
        backend = self._makeOne()
        payload = 'a rather boring payload'
        another = 'another payload'
        queue_name = uuid.uuid4().hex
        backend.push(queue_name, payload)
        last = backend.push(queue_name, another)[0]
        last_uuid = uuid.UUID(hex=last)
        existing = backend.retrieve(queue_name)
        self.assertEqual(2, len(existing))
        self.assertEqual(existing[1][2], payload)

        existing = backend.retrieve(queue_name, order='ascending')
        self.assertEqual(existing[1][2], another)

        # Add a limit
        existing = backend.retrieve(queue_name, limit=1)
        self.assertEqual(existing[0][2], another)
        self.assertEqual(len(existing), 1)

        # Add a timestamp
        second_value = (last_uuid.time - 0x01b21dd213814000L) * 100 / 1e9
        second_value = second_value
        existing = backend.retrieve(queue_name, timestamp=second_value,
                                    order='ascending')
        self.assertEqual(existing[0][2], another)
        self.assertEqual(len(existing), 1)

    def test_message_removal(self):
        backend = self._makeOne()
        payload = 'a rather boring payload'
        another = 'another payload'
        queue_name = uuid.uuid4().hex
        backend.push(queue_name, payload)
        backend.push(queue_name, another)
        existing = backend.retrieve(queue_name)
        self.assertEqual(2, len(existing))

        backend.truncate(queue_name)
        existing = backend.retrieve(queue_name)
        self.assertEqual(0, len(existing))

    def test_message_delete(self):
        backend = self._makeOne()
        payload = 'a rather boring payload'
        another = 'another payload'
        queue_name = uuid.uuid4().hex
        key1 = backend.push(queue_name, payload)[0]
        key2 = backend.push(queue_name, another)[0]
        existing = backend.retrieve(queue_name)
        self.assertEqual(2, len(existing))

        backend.delete(queue_name, key2)
        existing = backend.retrieve(queue_name)
        self.assertEqual(1, len(existing))

        backend.delete(queue_name, key1)
        existing = backend.retrieve(queue_name)
        self.assertEqual(0, len(existing))

    def test_message_counting(self):
        backend = self._makeOne()
        payload = 'a rather boring payload'
        queue_name = uuid.uuid4().hex
        for x in range(4):
            backend.push(queue_name, payload)
            self.assertEqual(x + 1, backend.count(queue_name))

        # Test non-existing row
        self.assertEqual(backend.count('no row'), 0)

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
        backend.register_queue('myapp', 'fredrick', 1)

        # Ensure we get an exception on a repeat
        @raises(QueueAlreadyExists)
        def testit():
            backend.register_queue('myapp', 'fredrick', 1)
        testit()

    def test_add_queue_not_regged(self):
        from queuey.exceptions import ApplicationNotRegistered
        backend = self._makeOne()

        @raises(ApplicationNotRegistered)
        def testit():
            backend.register_queue('myapp', 'fredrick', 1)
        testit()

    def test_remove_queue(self):
        from queuey.exceptions import ApplicationNotRegistered
        from queuey.exceptions import QueueDoesNotExist
        backend = self._makeOne()

        @raises(ApplicationNotRegistered)
        def testit():
            backend.remove_queue('myapp', 'nosuchqueue')
        testit()

        backend.register_application('myapp')
        backend.register_queue('myapp', 'fredrick', 1)
        backend.remove_queue('myapp', 'fredrick')

        @raises(QueueDoesNotExist)
        def testits():
            backend.remove_queue('myapp', 'nosuchqueue')
        testits()

    def test_queue_info(self):
        from queuey.exceptions import QueueDoesNotExist
        backend = self._makeOne()
        backend.register_application('myapp')
        backend.register_queue('myapp', 'fredrick', 3)

        info = backend.queue_information('myapp', 'fredrick')
        self.assertEqual(info['partitions'], 3)

        @raises(QueueDoesNotExist)
        def testit():
            backend.queue_information('myapp', 'asdfasdf')
        testit()
