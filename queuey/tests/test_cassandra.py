# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import uuid
import os

from nose.tools import eq_
from nose.tools import raises
from pycassa import ConsistencyLevel
import pycassa

import mock

from queuey.tests.storage import StorageTestMessageBase
from queuey.tests.storage import StorageTestMetadataBase


class TestCassandraStore(StorageTestMessageBase):
    def _makeOne(self, **kwargs):
        from queuey.storage.cassandra import CassandraQueueBackend
        host = os.environ.get('TEST_CASSANDRA_HOST', 'localhost')
        return CassandraQueueBackend(host=host, **kwargs)

    def test_parsehosts(self):
        from queuey.storage.cassandra import parse_hosts
        hosts = parse_hosts('localhost')
        eq_(hosts, ['localhost:9160'])

        hosts = parse_hosts('192.168.2.1,192.168.2.3:9180 , 192.168.2.19')
        eq_(hosts,
            ['192.168.2.1:9160', '192.168.2.3:9180', '192.168.2.19:9160'])

    def test_credentials(self):
        creds = dict(username='foo', password='foo')
        backend = self._makeOne(**creds)
        eq_(backend.pool.credentials, creds)

    def test_cl(self):
        backend = self._makeOne()
        backend.cl = None
        eq_(ConsistencyLevel.ONE, backend._get_cl('weak'))
        eq_(ConsistencyLevel.QUORUM, backend._get_cl('very_strong'))
        eq_(ConsistencyLevel.QUORUM, backend._get_cl('medium'))

    def test_multidc_cl(self):
        backend = self._makeOne()
        backend.cl = None
        backend.multi_dc = True
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


class TestCassandraMetadata(StorageTestMetadataBase):
    def _makeOne(self, **kwargs):
        from queuey.storage.cassandra import CassandraMetadata
        host = os.environ.get('TEST_CASSANDRA_HOST', 'localhost')
        return CassandraMetadata(host=host, **kwargs)

    def test_credentials(self):
        creds = dict(username='foo', password='foo')
        backend = self._makeOne(**creds)
        eq_(backend.pool.credentials, creds)


del StorageTestMessageBase
del StorageTestMetadataBase
