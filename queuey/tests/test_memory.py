# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import uuid
import time

from nose.tools import eq_

from queuey.tests.storage import StorageTestMessageBase
from queuey.tests.storage import StorageTestMetadataBase


class TestMemoryStore(StorageTestMessageBase):
    def _makeOne(self, **kwargs):
        from queuey.storage.memory import MemoryQueueBackend
        return MemoryQueueBackend()

    def test_ttl_in_batch(self):
        backend = self._makeOne()
        payload = 'a rather boring payload'
        queue_name = uuid.uuid4().hex
        past = time.time() - 10
        backend.push('weak', 'myapp', queue_name, payload, ttl=5,
                     timestamp=past)[0]
        existing = backend.retrieve_batch('weak', 'myapp', [queue_name])
        eq_([], existing)

    def test_ttl_in_retrieve(self):
        backend = self._makeOne()
        payload = 'a rather boring payload'
        queue_name = uuid.uuid4().hex
        past = time.time() - 10
        msg = backend.push('weak', 'myapp', queue_name, payload, ttl=5,
                      timestamp=past)[0]
        existing = backend.retrieve('weak', 'myapp', queue_name, msg)
        eq_({}, existing)


class TestMemoryMetadata(StorageTestMetadataBase):
    def _makeOne(self):
        from queuey.storage.memory import MemoryMetadata
        return MemoryMetadata()

del StorageTestMessageBase
del StorageTestMetadataBase
