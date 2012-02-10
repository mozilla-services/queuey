# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import unittest
import uuid
import os

from nose.tools import eq_


class TestCassandraStore(unittest.TestCase):
    def _makeOne(self, **kwargs):
        from queuey.storage.cassandra import CassandraQueueBackend
        host = os.environ.get('TEST_CASSANDRA_HOST', 'localhost')
        return CassandraQueueBackend(host, **kwargs)

    def test_parsehosts(self):
        from queuey.storage.cassandra import parse_hosts
        hosts = parse_hosts('localhost')
        eq_(hosts, ['localhost:9160'])

        hosts = parse_hosts('192.168.2.1,192.168.2.3:9180 , 192.168.2.19')
        eq_(hosts,
            ['192.168.2.1:9160', '192.168.2.3:9180', '192.168.2.19:9160'])

    def test_noqueue(self):
        backend = self._makeOne()
        queue_name = uuid.uuid4().hex
        existing = backend.retrieve_batch('weak', 'myapp', queue_name)
        eq_([], existing)

    def test_onemessage(self):
        backend = self._makeOne()
        payload = 'a rather boring payload'
        queue_name = uuid.uuid4().hex
        backend.push('weak', 'myapp', queue_name, payload)
        existing = backend.retrieve_batch('weak', 'myapp', [queue_name])
        eq_(existing[0]['body'], payload)

    def test_message_ordering(self):
        backend = self._makeOne()
        payload = 'a rather boring payload'
        another = 'another payload'
        queue_name = uuid.uuid4().hex
        backend.push('weak', 'myapp', queue_name, payload)
        middle = backend.push('weak', 'myapp', queue_name, another)
        backend.push('weak', 'myapp', queue_name, "more stuff")

        existing = backend.retrieve_batch('weak', 'myapp', [queue_name],
                                          order='descending')
        eq_(3, len(existing))
        eq_(existing[1]['body'], another)

        existing = backend.retrieve_batch('weak', 'myapp', [queue_name])
        eq_(3, len(existing))
        eq_(existing[0]['body'], payload)

        # Add a limit
        existing = backend.retrieve_batch('weak', 'myapp', [queue_name],
                                          limit=1, order='descending')
        eq_(existing[0]['body'], "more stuff")
        eq_(len(existing), 1)

        # Add the prior value
        existing = backend.retrieve_batch(
            'weak', 'myapp', [queue_name], start_at=middle[0])
        eq_(existing[0]['body'], another)
        eq_(len(existing), 2)

    def test_message_removal(self):
        backend = self._makeOne()
        payload = 'a rather boring payload'
        another = 'another payload'
        queue_name = uuid.uuid4().hex
        backend.push('weak', 'myapp', queue_name, payload)
        backend.push('weak', 'myapp', queue_name, another)
        existing = backend.retrieve_batch('weak', 'myapp', [queue_name])
        eq_(2, len(existing))

        backend.truncate('weak', 'myapp', queue_name)
        existing = backend.retrieve_batch('weak', 'myapp', [queue_name])
        eq_(0, len(existing))

    def test_message_retrieve(self):
        backend = self._makeOne()
        payload = 'a rather boring payload'
        queue_name = uuid.uuid4().hex
        last = backend.push('weak', 'myapp', queue_name, payload)[0]
        last_uuid = uuid.UUID(hex=last)
        msg = backend.retrieve('weak', 'myapp', queue_name, last_uuid)
        eq_(msg['body'], payload)

    def test_message_retrieve_with_metadata(self):
        backend = self._makeOne()
        payload = 'a rather boring payload'
        queue_name = uuid.uuid4().hex
        last = backend.push('weak', 'myapp', queue_name, payload,
                            {'ContentType': 'application/json'})[0]
        last_uuid = uuid.UUID(hex=last)
        msg = backend.retrieve('weak', 'myapp', queue_name, last_uuid,
                               include_metadata=True)
        eq_(msg['body'], payload)
        eq_(msg['metadata']['ContentType'], 'application/json')

    def test_batch_message_with_metadata(self):
        backend = self._makeOne()
        payload = 'a rather boring payload'
        queue_name = uuid.uuid4().hex
        backend.push('weak', 'myapp', queue_name, payload,
                     {'ContentType': 'application/json'})
        msg = backend.retrieve_batch('weak', 'myapp', [queue_name],
                                     include_metadata=True)
        eq_(msg[0]['body'], payload)
        eq_(msg[0]['metadata']['ContentType'], 'application/json')

    def test_message_delete(self):
        backend = self._makeOne()
        payload = 'a rather boring payload'
        another = 'another payload'
        queue_name = uuid.uuid4().hex
        key1 = backend.push('weak', 'myapp', queue_name, payload)[0]
        key2 = backend.push('weak', 'myapp', queue_name, another)[0]
        existing = backend.retrieve_batch('weak', 'myapp', [queue_name])
        eq_(2, len(existing))

        backend.delete('weak', 'myapp', queue_name, key2)
        existing = backend.retrieve_batch('weak', 'myapp', [queue_name])
        eq_(1, len(existing))

        backend.delete('weak', 'myapp', queue_name, key1)
        existing = backend.retrieve_batch('weak', 'myapp', [queue_name])
        eq_(0, len(existing))

    def test_message_counting(self):
        backend = self._makeOne()
        payload = 'a rather boring payload'
        queue_name = uuid.uuid4().hex
        for x in range(4):
            backend.push('weak', 'myapp', queue_name, payload)
            eq_(x + 1, backend.count('weak', 'myapp', queue_name))

        # Test non-existing row
        eq_(backend.count('weak', 'myapp', 'no row'), 0)


class TestCassandraMetadata(unittest.TestCase):
    def _makeOne(self):
        from queuey.storage.cassandra import CassandraMetadata
        host = os.environ.get('TEST_CASSANDRA_HOST', 'localhost')
        return CassandraMetadata(host)

    def _makeQB(self):
        from queuey.storage.cassandra import CassandraQueueBackend
        host = os.environ.get('TEST_CASSANDRA_HOST', 'localhost')
        return CassandraQueueBackend(host)

    def setUp(self):
        backend = self._makeOne()
        backend.remove_queue('myapp', 'fredrick')
        backend.remove_queue('myapp', 'smith')
        backend.remove_queue('myapp', 'alpha')

    def test_register_queue(self):
        backend = self._makeOne()
        backend.register_queue('myapp', 'fredrick')
        eq_(1, len(backend.queue_list('myapp')))

    def test_update_queue_with_metadata(self):
        backend = self._makeOne()
        backend.register_queue('myapp', 'fredrick')
        eq_(1, len(backend.queue_list('myapp')))
        eq_({'application': 'myapp'},
            backend.queue_information('myapp', 'fredrick'))

        # Update metadata
        backend.register_queue('myapp', 'fredrick', partitions=5)
        eq_({'application': 'myapp', 'partitions': 5},
            backend.queue_information('myapp', 'fredrick'))

    def test_queue_paging(self):
        backend = self._makeOne()
        backend.register_queue('myapp', 'fredrick')
        backend.register_queue('myapp', 'smith')
        backend.register_queue('myapp', 'alpha')

        # See that we get it back in our list
        results = backend.queue_list('myapp')
        eq_(3, len(results))

        # Page 1 in
        res = backend.queue_list('myapp', offset=results[1])
        eq_(2, len(res))
        eq_(results[2], res[1])

    def test_remove_queue(self):
        backend = self._makeOne()
        backend.register_queue('myapp', 'fredrick')
        backend.remove_queue('myapp', 'fredrick')

        results = backend.remove_queue('myapp', 'fredrick')
        eq_(False, results)

    def test_queue_info(self):
        backend = self._makeOne()
        backend.register_queue('myapp', 'fredrick', partitions=3)

        info = backend.queue_information('myapp', 'fredrick')
        eq_(info['partitions'], 3)

        eq_({}, backend.queue_information('myapp', 'asdfasdf'))
