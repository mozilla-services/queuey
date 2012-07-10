# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from collections import defaultdict
from cdecimal import Decimal
import uuid
import time

from zope.interface import implements

from queuey.storage import MessageQueueBackend
from queuey.storage import MetadataBackend
from queuey.storage.util import convert_time_to_uuid

DECIMAL_1E7 = Decimal('1e7')

# Queue's keyed by applciation_name + queue_name
# Queues are just a list of Message objects
message_store = defaultdict(list)

# Applcation's keyed by application name
metadata_store = {}


class Message(object):
    def __init__(self, id, body, ttl, **metadata):
        self.id = id
        self.body = body
        self.metadata = metadata
        self.ttl = None
        self.expiration = None
        if ttl:
            now = Decimal(self.id.time - 0x01b21dd213814000L) / DECIMAL_1E7
            self.expiration = now + ttl

    def __eq__(self, other):
        if isinstance(other, Message):
            return self.id == other.id
        return id(self) == id(other)


class Application(object):
    def __init__(self, application_name):
        self.application_name = application_name
        self.queues = {}


class QueueMetadata(object):
    def __init__(self, queue_name, **metadata):
        self.queue_name = queue_name
        self.metadata = metadata


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
            if isinstance(start_at, basestring):
                # Assume its a hex, transform to a UUID
                start_at = uuid.UUID(hex=start_at)
            else:
                # Assume its a float/decimal, convert to UUID
                start_at = convert_time_to_uuid(start_at)

        queue_names = ['%s:%s' % (application_name, x) for x in queue_names]
        results = []
        now = Decimal(repr(time.time()))
        for queue_name in queue_names:
            msgs = message_store[queue_name]
            if not msgs:
                continue
            msgs.sort(key=lambda k: (k.id.time, k.id.bytes))
            if start_at:
                # Locate the index given the start_at
                point = (start_at.time, start_at.bytes)
                beg = msgs[0].id
                end = msgs[-1].id
                if point <= (beg.time, beg.bytes):
                    # Is the start_at less than the beginning? Start at beginning
                    start = 0
                elif point >= (end.time, end.bytes):
                    # Is the start_at larger than the end? Start at the end
                    start = len(msgs) - 1
                else:
                    # The start point is somewhere inside, skim through until
                    # we hit a value a value equal to or greater than
                    start = 0
                    msg_comp = (msgs[start].id.time, msgs[start].id.bytes)
                    while point > msg_comp:
                        start += 1
                        msg_comp = (msgs[start].id.time, msgs[start].id.bytes)
            else:
                if order == -1:
                    start = len(msgs) - 1
                else:
                    start = 0
            count = 0

            for msg in msgs[start::order]:
                if msg.expiration and now > msg.expiration:
                    msgs.remove(msg)
                    continue
                count += 1
                if limit and count > limit:
                    break
                obj = {
                    'message_id': msg.id.hex,
                    'timestamp': (Decimal(msg.id.time - 0x01b21dd213814000L) /
                        DECIMAL_1E7),
                    'body': msg.body,
                    'metadata': {},
                    'queue_name': queue_name[queue_name.find(':'):]
                }
                if include_metadata:
                    obj['metadata'] = msg.metadata
                results.append(obj)
        return results

    def retrieve(self, consistency, application_name, queue_name, message_id,
                 include_metadata=False):
        """Retrieve a single message"""
        if isinstance(message_id, basestring):
            # Convert to uuid for lookup
            message_id = uuid.UUID(hex=message_id)
        else:
            # Assume its a float/decimal, convert to UUID
            message_id = convert_time_to_uuid(message_id)

        queue_name = '%s:%s' % (application_name, queue_name)
        queue = message_store[queue_name]
        found = None
        for msg in queue:
            if msg.id == message_id:
                found = msg
                break

        if not found:
            return {}

        now = Decimal(repr(time.time()))
        if found.expiration and now > found.expiration:
            queue.remove(found)
            return {}

        obj = {
            'message_id': found.id.hex,
            'timestamp': (Decimal(found.id.time - 0x01b21dd213814000L) /
                DECIMAL_1E7),
            'body': found.body,
            'metadata': {},
            'queue_name': queue_name[queue_name.find(':'):]
        }
        if include_metadata:
            obj['metadata'] = found.metadata
        return obj

    def push(self, consistency, application_name, queue_name, message,
             metadata=None, ttl=60 * 60 * 24 * 3, timestamp=None):
        """Push a message onto the queue"""
        if not timestamp:
            now = uuid.uuid1()
        elif isinstance(timestamp, (float, Decimal)):
            now = convert_time_to_uuid(timestamp, randomize=True)
        else:
            now = uuid.UUID(hex=timestamp)
        msg = Message(id=now, body=message, ttl=ttl)
        if metadata:
            msg.metadata = metadata
        timestamp = Decimal(msg.id.time - 0x01b21dd213814000L) / DECIMAL_1E7
        queue_name = '%s:%s' % (application_name, queue_name)
        if msg in message_store[queue_name]:
            message_store[queue_name].remove(msg)
        message_store[queue_name].append(msg)
        return msg.id.hex, timestamp

    def push_batch(self, consistency, application_name, message_data):
        """Push a batch of messages"""
        msgs = []
        for queue_name, body, ttl, metadata in message_data:
            qn = '%s:%s' % (application_name, queue_name)
            msg = Message(id=uuid.uuid1(), body=body, ttl=ttl)
            if metadata:
                msg.metadata = metadata
            message_store[qn].append(msg)
            timestamp = (Decimal(msg.id.time - 0x01b21dd213814000L) /
                DECIMAL_1E7)
            msgs.append((msg.id.hex, timestamp))
        return msgs

    def truncate(self, consistency, application_name, queue_name):
        """Remove all contents of the queue"""
        queue_name = '%s:%s' % (application_name, queue_name)
        message_store[queue_name] = []
        return True

    def delete(self, consistency, application_name, queue_name, *keys):
        """Delete a batch of keys"""
        queue_name = '%s:%s' % (application_name, queue_name)
        queue = message_store.get(queue_name)
        del_items = []
        for index, msg in enumerate(queue):
            if msg.id.hex in keys:
                del_items.append(index)
        for index in sorted(del_items)[::-1]:
            del queue[index]
        return True

    def count(self, consistency, application_name, queue_name):
        """Return a count of the items in this queue"""
        queue_name = '%s:%s' % (application_name, queue_name)
        queue = message_store.get(queue_name)
        if not queue:
            return 0
        else:
            return len(queue)


class MemoryMetadata(object):
    implements(MetadataBackend)

    def __init__(self):
        pass

    def register_queue(self, application_name, queue_name, **metadata):
        """Register a queue, optionally with metadata"""
        if application_name not in metadata_store:
            metadata_store[application_name] = app = Application(application_name)
        else:
            app = metadata_store[application_name]
        if queue_name in app.queues:
            app.queues[queue_name].metadata.update(metadata)
        else:
            metadata['application'] = application_name
            if 'created' not in metadata:
                metadata['created'] = time.time()
            app.queues[queue_name] = QueueMetadata(queue_name, **metadata)
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
        app = metadata_store.get(application_name, None)
        if app is None:
            return []
        if offset:
            queues = filter(lambda x: x >= offset,
                            sorted(app.queues.keys()))
        else:
            queues = sorted(app.queues.keys())

        return queues[:limit]

    def queue_information(self, application_name, queue_names):
        """Return information on a registered queue"""
        if not isinstance(queue_names, list):
            raise Exception("Queue names must be a list.")
        app = metadata_store.get(application_name,
                                 Application(application_name))
        results = []
        for qn in queue_names:
            queue = app.queues.get(qn)
            if not queue:
                results.append({})
                continue
            results.append(queue.metadata)
        return results
