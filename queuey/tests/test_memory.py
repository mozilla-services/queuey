# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import unittest
import uuid
import time

from nose.tools import eq_

from queuey.tests.storage import StorageTestMessageBase
from queuey.tests.storage import StorageTestMetadataBase


class TestMessage(unittest.TestCase):

    def _makeOne(self):
        from queuey.storage.memory import Message
        return Message(uuid.uuid1(), 'body', 300)

    def test_create(self):
        msg = self._makeOne()
        eq_('body', msg.body)

    def test_compare(self):
        msg1 = self._makeOne()
        msg2 = self._makeOne()
        eq_(msg1, msg1)
        eq_(msg2, msg2)
        self.assertNotEqual(msg1, msg2)
        self.assertNotEqual(msg1, object())


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
