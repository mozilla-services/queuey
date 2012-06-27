# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import collections
from cdecimal import Decimal
import re

from pyramid.security import Allow
from pyramid.security import Everyone


DECIMAL_REGEX = re.compile(r'^\d+(\.\d+)?$')
MESSAGE_REGEX = re.compile(
    r'(?:\d\:)?[a-zA-Z0-9]{32}(?:\,(?:\d{1,3}\:)?[a-zA-Z0-9]{32}){0,}'
)


class InvalidQueueName(Exception):
    """Raised when a queue name is invalid"""
    status = 404


class InvalidUpdate(Exception):
    """Raised when an update to existing data fails"""
    status = 400


class InvalidMessageID(Exception):
    """Raised for invalid message ID's"""
    status = 400


def transform_stored_message(message):
    del message['metadata']
    message['partition'] = int(message['queue_name'].split(':')[-1])
    del message['queue_name']
    message['timestamp'] = str(message['timestamp'])


class Root(object):
    __acl__ = []

    def __init__(self, request):
        self.request = request

    def __getitem__(self, name):
        if name == 'v1':
            return QueueyVersion1API(self.request)
        else:
            raise KeyError("No key %s found" % name)


class QueueyVersion1API(object):
    def __init__(self, request):
        self.request = request

    def __getitem__(self, name):
        # See if the application name is valid
        if name in self.request.registry['app_names']:
            return Application(self.request, name)
        else:
            raise KeyError("No key %s found" % name)


class Application(object):
    """Application resource"""
    def __init__(self, request, application_name):
        self.request = request
        self.application_name = application_name
        self.metadata = request.registry['backend_metadata']
        self.storage = request.registry['backend_storage']
        app_id = 'app:%s' % self.application_name

        # Applications can create queues and view existing queues
        self.__acl__ = [
            (Allow, app_id, 'create_queue'),
            (Allow, app_id, 'view_queues')
        ]

    def __getitem__(self, name):
        if len(name) > 50:
            raise InvalidQueueName("Queue name longer than 50 characters.")
        data = self.metadata.queue_information(self.application_name, [name])
        if not data or not data[0]:
            raise InvalidQueueName("Queue of that name was not found.")
        return Queue(self.request, name, data[0])

    def register_queue(self, queue_name, **metadata):
        """Register a queue for this application"""
        if not metadata.get('principles'):
            del metadata['principles']
        return self.metadata.register_queue(
            self.application_name,
            queue_name,
            **metadata
        )

    def queue_list(self, details=False, include_count=False, limit=None,
                   offset=None):
        queues = self.metadata.queue_list(self.application_name, limit=limit,
                                          offset=offset)
        queue_list = []
        queue_data = []
        if details or include_count:
            queue_data = self.metadata.queue_information(self.application_name,
                                                         queues)
        for index, queue_name in enumerate(queues):
            qd = {
                'queue_name': queue_name,
            }
            if details or include_count:
                qd.update(queue_data[index])
            if include_count:
                total = 0
                for num in range(queue_data[index]['partitions']):
                    qn = '%s:%s' % (queue_name, num + 1)
                    total += self.storage.count('weak', self.application_name,
                                                qn)
                qd['count'] = total
            queue_list.append(qd)
        return queue_list


class Queue(object):
    """Queue Resource"""
    def __init__(self, request, queue_name, queue_data):
        self.request = request
        self.metadata = request.registry['backend_metadata']
        self.storage = request.registry['backend_storage']
        self.queue_name = queue_name
        self.metlog = request.registry['metlog_client']
        principles = queue_data.pop('principles', '').split(',')
        self.principles = [x.strip() for x in principles if x]

        for name, value in queue_data.items():
            setattr(self, name, value)

        # Applications are always allowed to create message in queues
        # they made
        app_id = 'app:%s' % self.application
        self.__acl__ = acl = [
            (Allow, app_id, 'create'),
            (Allow, app_id, 'create_queue'),
            (Allow, app_id, 'delete_queue')
        ]

        # If there's additional principles, view/info/delete messages will
        # be granted to them
        if self.principles:
            for principle in self.principles:
                for permission in ['view', 'delete']:
                    acl.append((Allow, principle, permission))
        else:
            # If there are no additional principles, the application
            # may also view and delete messages in the queue
            acl.append((Allow, app_id, 'view'))
            acl.append((Allow, app_id, 'delete'))

        # Everyons is allowed to view public queues
        if queue_data['type'] == 'public':
            acl.append((Allow, Everyone, 'view'))

    def __getitem__(self, name):
        """Determine if this is a multiple message context"""
        if not MESSAGE_REGEX.match(name):
            raise InvalidMessageID("Invalid message id's.")
        return MessageBatch(self.request, self, name)

    def update_metadata(self, **metadata):
        # Strip out data not being updated
        metadata = dict((k, v) for k, v in metadata.items() if v)
        if 'partitions' in metadata:
            if metadata['partitions'] < self.partitions:
                raise InvalidUpdate("Partitions can only be increased.")

        self.metadata.register_queue(self.application, self.queue_name,
                                     **metadata)
        for k, v in metadata.items():
            setattr(self, k, v)
        if 'principles' in metadata:
            self.principles = [x.strip() for x in
                               metadata['principles'].split(',') if x]

    def push_batch(self, messages):
        """Push a batch of messages to the storage"""
        msgs = [('%s:%s' % (self.queue_name, x['partition']), x['body'],
                 x['ttl'], x.get('metadata', {})) for x in messages]
        results = self.storage.push_batch(self.consistency, self.application,
                                          msgs)
        rl = []
        for i, msg in enumerate(results):
            rl.append({'key': msg[0], 'timestamp': str(msg[1]),
                       'partition': messages[i]['partition']})
        self.metlog.incr('%s.new_message' % self.application,
                         count=len(results))
        return rl

    def get_messages(self, since=None, limit=None, order=None, partitions=None):
        queue_names = []
        for part in partitions:
            queue_names.append('%s:%s' % (self.queue_name, part))
        if since and DECIMAL_REGEX.match(since):
            since = Decimal(since)
        results = self.storage.retrieve_batch(
            self.consistency, self.application, queue_names, start_at=since,
            limit=limit, order=order)
        for res in results:
            transform_stored_message(res)
        self.metlog.incr('%s.get_message' % self.application,
                         count=len(results))
        return results

    def delete(self):
        partitions = range(1, self.partitions + 1)
        for partition in partitions:
            self.storage.truncate(self.consistency, self.application, '%s:%s' %
                                  (self.queue_name, partition))
        self.metadata.remove_queue(self.application, self.queue_name)
        return True


class MessageBatch(object):
    def __init__(self, request, queue, message_ids):
        self.request, self.queue = request, queue
        self.message_ids = [x.strip() for x in message_ids.split(',')]

        # Copy parent ACL
        self.__acl__ = queue.__acl__[:]

    def _messages(self):
        partition_hash = collections.defaultdict(lambda: [])
        for msg_id in self.message_ids:
            if ':' in msg_id:
                partition, msg_id = msg_id.split(':')
            else:
                partition = 1
            qn = '%s:%s' % (self.queue.queue_name, partition)
            partition_hash[qn].append(msg_id)
        return partition_hash

    def delete(self):
        for queue, msgs in self._messages().iteritems():
            self.queue.storage.delete(
                    self.queue.consistency,
                    self.queue.application,
                    queue, *msgs)
        return

    def get(self):
        results = []
        for queue, msgs in self._messages().iteritems():
            for msg_id in msgs:
                res = self.queue.storage.retrieve(self.queue.consistency,
                    self.queue.application, queue, str(msg_id))
                if res:
                    transform_stored_message(res)
                    results.append(res)
        self.queue.metlog.incr('%s.get_message' % self.queue.application,
            count=len(results))
        return results

    def update(self, params):
        for queue, msgs in self._messages().iteritems():
            for msg in msgs:
                self.queue.storage.push(self.queue.consistency,
                    self.queue.application, queue,
                    params['body'], ttl=params['ttl'], timestamp=msg)
        return
