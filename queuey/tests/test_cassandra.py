# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import unittest
import uuid
import os

from nose.tools import eq_
from nose.tools import raises
from pycassa import ConsistencyLevel
import pycassa

import mock


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

    def test_cl(self):
        backend = self._makeOne()
        backend.cl = None
        eq_(ConsistencyLevel.ONE, backend._get_cl('weak'))
        eq_(ConsistencyLevel.EACH_QUORUM, backend._get_cl('very_strong'))
        eq_(ConsistencyLevel.LOCAL_QUORUM, backend._get_cl('medium'))

    def test_delay(self):
        backend = self._makeOne()
        eq_(0, backend._get_delay('weak'))
        backend.cl = None
        eq_(1, backend._get_delay('weak'))
        eq_(600, backend._get_delay('very_strong'))
        eq_(5, backend._get_delay('medium'))

    def test_delayed_messages(self):
        backend = self._makeOne()
        payload = 'a rather boring payload'
        queue_name = uuid.uuid4().hex
        backend.push('weak', 'myapp', queue_name, payload)
        backend._get_delay = lambda x: 5
        existing = backend.retrieve_batch('very_strong', 'myapp', [queue_name])
        eq_(0, len(existing))

    def test_noqueue(self):
        backend = self._makeOne()
        queue_name = uuid.uuid4().hex
        existing = backend.retrieve_batch('weak', 'myapp', [queue_name])
        eq_([], existing)

    def test_onemessage(self):
        backend = self._makeOne()
        payload = 'a rather boring payload'
        queue_name = uuid.uuid4().hex
        msg_id = backend.push('weak', 'myapp', queue_name, payload)[0]
        existing = backend.retrieve_batch('weak', 'myapp', [queue_name])
        eq_(existing[0]['body'], payload)

        # Retrieve just one message
        one = backend.retrieve('weak', 'myapp', queue_name, msg_id)
        eq_(one['body'], payload)

        # Empty metadata
        one = backend.retrieve('weak', 'myapp', queue_name, msg_id,
                               include_metadata=True)
        eq_(one['metadata'], {})

    def test_push_batch(self):
        backend = self._makeOne()
        queue_name = uuid.uuid4().hex
        queue_name2 = uuid.uuid4().hex
        backend.push_batch('weak', 'myapp', [
            (queue_name, 'first message', 3600, {}),
            (queue_name, 'second message', 3600, {'ContentType': 'application/json'}),
            (queue_name2, 'another first', 3600, {}),
        ])
        batch = backend.retrieve_batch('weak', 'myapp', [queue_name],
                                       include_metadata=True)
        eq_(batch[0]['body'], 'first message')
        eq_(batch[1]['metadata'], {'ContentType': 'application/json'})

    def test_must_use_list(self):
        @raises(Exception)
        def testit():
            backend = self._makeOne()
            queue_name = uuid.uuid4().hex
            backend.retrieve_batch('weak', 'myapp', queue_name)
        testit()

    def test_no_message(self):
        backend = self._makeOne()
        queue_name = uuid.uuid4().hex
        existing = backend.retrieve('weak', 'myapp', queue_name, queue_name)
        eq_({}, existing)

    def test_unavailable(self):
        from queuey.storage import StorageUnavailable
        mock_pool = mock.Mock(spec=pycassa.ColumnFamily)
        mock_cf = mock.Mock()
        mock_pool.return_value = mock_cf

        def explode(*args, **kwargs):
            raise pycassa.UnavailableException()

        mock_cf.get.side_effect = explode

        with mock.patch('pycassa.ColumnFamily', mock_pool):
            backend = self._makeOne()

            @raises(StorageUnavailable)
            def testit():
                queue_name = uuid.uuid4().hex
                backend.retrieve('strong', 'myapp', queue_name, queue_name)
            testit()

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

        # Update metadata
        backend.register_queue('myapp', 'fredrick', partitions=5)
        info = backend.queue_information('myapp', ['fredrick'])
        eq_(5, info[0]['partitions'])

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

        info = backend.queue_information('myapp', ['fredrick'])
        eq_(info[0]['partitions'], 3)

        eq_([], backend.queue_information('myapp', ['asdfasdf']))

    def test_must_use_list(self):
        @raises(Exception)
        def testit():
            backend = self._makeOne()
            backend.register_queue('myapp', 'fredrick', partitions=3)
            queue_name = uuid.uuid4().hex
            backend.queue_information('myapp', queue_name)
        testit()
