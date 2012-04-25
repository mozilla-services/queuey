# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import uuid
import time

from zope.interface import implements

from queuey.storage import MessageQueueBackend
from queuey.storage import MetadataBackend

# Queue's keyed by applciation_name + queue_name
message_store = {}

# Applcation's keyed by application name
metadata_store = {}


class Message(object):
    def __init__(self, id, body, metadata):
        self.id = id
        self.body = body
        self.metadata = {}


class Application(object):
    def __init__(self, application_name):
        self.application_name = application_name
        self.queues = {}


class QueueMetadata(object):
    def __init__(self, queue_name, **metadata):
        self.queue_name = queue_name
        self.metadata = {}


class MemoryQueueBackend(object):
    implements(MessageQueueBackend)

    def __init__(self):
        pass

    def retrieve_batch(self, consistency, application_name, queue_names,
                       limit=None, include_metadata=False, start_at=None,
                       order="ascending"):
        """Retrieve a batch of messages off the queue"""
        if not isinstance(queue_names, list):
            raise Exception("queue_names must be a list")

        order = -1 if order == 'descending' else 1

        if start_at:
            if isinstance(start_at, str):
                # Assume its a hex, transform to a UUID
                start_at = uuid.UUID(hex=start_at)

        queue_names = ['%s:%s' % (application_name, x) for x in queue_names]
        results = self.message_fam.multiget(keys=queue_names, **kwargs)
        results = results.items()
        if delay:
            cut_off = time.time() - delay
            # Turn it into time in ns, for efficient comparison
            cut_off = cut_off * 1e9 / 100 + 0x01b21dd213814000L

        result_list = []
        msg_hash = {}
        for queue_name, messages in results:
            for msg_id, body in messages.items():
                if delay and msg_id.time >= cut_off:
                    continue
                obj = {
                    'message_id': msg_id.hex,
                    'timestamp': (msg_id.time - 0x01b21dd213814000L) / 1e7,
                    'body': body,
                    'metadata': {},
                    'queue_name': queue_name[queue_name.find(':'):]
                }
                result_list.append(obj)
                msg_hash[msg_id] = obj

        # Get metadata?
        if include_metadata:
            results = self.meta_fam.multiget(keys=msg_hash.keys())
            for msg_id, metadata in results.items():
                msg_hash[msg_id]['metadata'] = metadata
        return result_list

    def retrieve(self, consistency, application_name, queue_name, message_id,
                 include_metadata=False):
        """Retrieve a single message"""
        cl = self.cl or self._get_cl(consistency)
        if isinstance(message_id, str):
            # Convert to uuid for lookup
            message_id = uuid.UUID(hex=message_id)

        kwargs = {
            'read_consistency_level': cl,
            'columns': [message_id]}
        queue_name = '%s:%s' % (application_name, queue_name)
        try:
            results = self.message_fam.get(key=queue_name, **kwargs)
        except pycassa.NotFoundException:
            return {}
        msg_id, body = results.items()[0]

        obj = {
            'message_id': msg_id.hex,
            'timestamp': (msg_id.time - 0x01b21dd213814000L) / 1e7,
            'body': body,
            'metadata': {},
            'queue_name': queue_name[queue_name.find(':'):]
        }

        # Get metadata?
        if include_metadata:
            try:
                results = self.meta_fam.get(key=msg_id)
                obj['metadata'] = results
            except pycassa.NotFoundException:
                pass
        return obj

    def push(self, consistency, application_name, queue_name, message,
             metadata=None, ttl=60 * 60 * 24 * 3):
        """Push a message onto the queue"""
        cl = self.cl or self._get_cl(consistency)
        now = uuid.uuid1()
        queue_name = '%s:%s' % (application_name, queue_name)
        if metadata:
            batch = pycassa.batch.Mutator(self.pool,
                                          write_consistency_level=cl)
            batch.insert(self.message_fam, key=queue_name,
                         columns={now: message}, ttl=ttl)
            batch.insert(self.meta_fam, key=now, columns=metadata, ttl=ttl)
            batch.send()
        else:
            self.message_fam.insert(key=queue_name, columns={now: message},
                                    ttl=ttl, write_consistency_level=cl)
        timestamp = (now.time - 0x01b21dd213814000L) / 1e7
        return now.hex, timestamp

    def push_batch(self, consistency, application_name, message_data):
        """Push a batch of messages"""
        cl = self.cl or self._get_cl(consistency)
        batch = pycassa.batch.Mutator(self.pool, write_consistency_level=cl)
        msgs = []
        for queue_name, body, ttl, metadata in message_data:
            qn = '%s:%s' % (application_name, queue_name)
            now = uuid.uuid1()
            batch.insert(self.message_fam, key=qn, columns={now: body},
                         ttl=ttl)
            if metadata:
                batch.insert(self.meta_fam, key=now, columns=metadata, ttl=ttl)
            timestamp = (now.time - 0x01b21dd213814000L) / 1e7
            msgs.append((now.hex, timestamp))
        batch.send()
        return msgs

    def truncate(self, consistency, application_name, queue_name):
        """Remove all contents of the queue"""
        cl = self.cl or self._get_cl(consistency)
        queue_name = '%s:%s' % (application_name, queue_name)
        self.message_fam.remove(key=queue_name, write_consistency_level=cl)
        return True

    def delete(self, consistency, application_name, queue_name, *keys):
        """Delete a batch of keys"""
        cl = self.cl or self._get_cl(consistency)
        queue_name = '%s:%s' % (application_name, queue_name)
        self.message_fam.remove(key=queue_name,
                                columns=[uuid.UUID(hex=x) for x in keys],
                                write_consistency_level=cl)
        return True

    def count(self, consistency, application_name, queue_name):
        """Return a count of the items in this queue"""
        cl = self.cl or self._get_cl(consistency)
        queue_name = '%s:%s' % (application_name, queue_name)
        return self.message_fam.get_count(key=queue_name,
                                          read_consistency_level=cl)


class MemoryMetadata(object):
    implements(MetadataBackend)

    def __init__(self):
        pass

    def register_queue(self, application_name, queue_name, **metadata):
        """Register a queue, optionally with metadata"""
        if application_name not in metadata_store:
            metadata_store[application_name] = Application(application_name)
        app = metadata_store[application_name]
        if queue_name in app.queues:
            queue = app.queues[queue_name]
        else:
            app.queues[queue_name] = queue = QueueMetadata(queue_name)

        if 'created' not in metadata:
            metadata['created'] = time.time()

        queue.metadata.update(metadata)
        return True

    def remove_queue(self, application_name, queue_name):
        """Remove a queue"""
        app = metadata_store.get(application_name)
        if not app or queue_name not in app.queues:
            return False

        del app.queues[queue_name]
        return True

    def queue_list(self, application_name, limit=100, offset=None):
        """Return list of queues"""
        app = metadata_store.get(application_name)
        if offset:
            queues = filter(lambda x: x.queue_name >= offset,
                            sorted(app.queues.keys()))
        else:
            queues = sorted(app.queues.keys())

        return queues[:limit]

    def queue_information(self, application_name, queue_names):
        """Return information on a registered queue"""
        if not isinstance(queue_names, list):
            raise Exception("Queue names must be a list.")
        app = metadata_store.get(application_name)
        if not app:
            return []
        data = []
        for name in queue_names:
            data.append(app.queues.get(queue_names))
        queue_names = ['%s:%s' % (application_name, queue_name) for
                       queue_name in queue_names]
        return [metadata_store.get(x, {}) for x in queue_names]
