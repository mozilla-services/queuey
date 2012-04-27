# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from queuey.tests.storage import StorageTestMessageBase
from queuey.tests.storage import StorageTestMetadataBase


class TestMemoryStore(StorageTestMessageBase):
    def _makeOne(self, **kwargs):
        from queuey.storage.memory import MemoryQueueBackend
        return MemoryQueueBackend()


class TestMemoryMetadata(StorageTestMetadataBase):
    def _makeOne(self):
        from queuey.storage.memory import MemoryMetadata
        return MemoryMetadata()
