# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import re

from pyramid.security import Allow
from pyramid.security import Everyone


FLOAT_REGEX = re.compile(r'^\d+(\.\d+)?')


class InvalidQueueName(Exception):
    """Raised when a queue name is invalid"""


class Root(object):
    __acl__ = []

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
        app_id = 'app:%s' % self.application_name

        # Applications can create queues and view existing queues
        self.__acl__ = [
            (Allow, app_id, 'create_queue'),
            (Allow, app_id, 'view_queues')
        ]

    def __getitem__(self, name):
        if len(name) > 50:
            raise InvalidQueueName("Queue name longer than 50 characters.")
        data = self.metadata.queue_information(self.application_name, name)
        if not data:
            raise InvalidQueueName("Queue of that name was not found.")
        return Queue(self.request, name, data)

    def register_queue(self, queue_name, **metadata):
        """Register a queue for this application"""
        if not metadata.get('principles'):
            del metadata['principles']
        return self.metadata.register_queue(
            self.application_name,
            queue_name,
            **metadata
        )

    def queue_list(self, limit=None, offset=None):
        return self.metadata.queue_list(self.application_name, limit=limit,
                                        offset=offset)


class Queue(object):
    """Queue Resource"""
    def __init__(self, request, queue_name, queue_data):
        self.request = request
        self.metadata = request.registry['backend_metadata']
        self.storage = request.registry['backend_storage']
        self.queue_name = queue_name
        principles = queue_data.pop('principles', '').split(',')
        self.principles = [x.strip() for x in principles if x]

        for name, value in queue_data.items():
            setattr(self, name, value)

        # Applications are always allowed to create message in queues
        # they made
        app_id = 'app:%s' % self.application
        self.__acl__ = acl = [
            (Allow, app_id, 'create'),
            (Allow, app_id, 'info'),
            (Allow, app_id, 'delete')
        ]

        # If there's additional principles, view/info/delete messages will
        # be granted to them
        if self.principles:
            for principle in self.principles:
                for permission in ['view', 'info', 'delete']:
                    acl.append((Allow, principle, permission))
        else:
            # If there are no additional principles, the application
            # may also view messages in the queue
            acl.append((Allow, app_id, 'view'))

        # Everyons is allowed to view public queues
        if queue_data['type'] == 'public':
            acl.append((Allow, Everyone, 'view'))

    def push_batch(self, messages):
        """Push a batch of messages to the storage"""
        msgs = [('%s:%s' % (self.queue_name, x['partition']), x['body'],
                 x['ttl'], {}) for x in messages]
        results = self.storage.push_batch(self.consistency, self.application,
                                          msgs)
        rl = []
        for i, msg in enumerate(results):
            rl.append({'key': msg[0], 'timestamp': repr(msg[1]),
                       'partition': messages[i]['partition']})
        return rl

    def get_messages(self, since=None, limit=None, order=None, partitions=None):
        queue_names = []
        for part in partitions:
            queue_names.append('%s:%s' % (self.queue_name, part))
        if since and FLOAT_REGEX.match(since):
            since = float(since)
        results = self.storage.retrieve_batch(
            self.consistency, self.application, queue_names, start_at=since,
            limit=limit, order=order)
        for res in results:
            del res['metadata']
            res['partition'] = int(res['queue_name'].split(':')[-1])
            del res['queue_name']
        return results

    def delete_messages(self, messages, partitions=None):
        partition = partitions[0] if partitions else 1
        qn = '%s:%s' % (self.queue_name, partition)
        return self.storage.delete(self.consistency, self.application, qn,
                                   *messages)

    def delete(self, delete_registration=False, partitions=None):
        partitions = partitions or [1]
        if delete_registration:
            partitions = range(1, self.partitions + 1)
        for partition in partitions:
            self.storage.truncate(self.consistency, self.application, '%s:%s' %
                                  (self.queue_name, partition))
        if delete_registration:
            self.metadata.remove_queue(self.application, self.queue_name)
        return True

    @property
    def count(self):
        total = 0
        for num in range(self.partitions):
            qn = '%s-%s' % (self.queue_name, num + 1)
            total += self.storage.count(self.consistency, self.application, qn)
        return total
