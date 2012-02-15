# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from pyramid.security import Allow
from pyramid.security import Everyone


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
        if not metadata.get('permissions'):
            del metadata['permissions']
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
        for name, value in queue_data.items():
            setattr(self, name, value)

        # Applications are always allowed to create message in queues
        # they made
        app_id = 'app:%s' % self.application
        self.__acl__ = acl = [
            (Allow, app_id, 'create'),
            (Allow, app_id, 'info')
        ]

        # If there's additional permissions, view/info/delete messages will
        # be granted to them
        if 'permissions' in queue_data:
            for permission in queue_data['permissions'].split(','):
                acl.extend([
                    (Allow, permission, 'view'),
                    (Allow, permission, 'info'),
                    (Allow, permission, 'delete')
                ])
        else:
            # If there are no additional permissions, the application
            # may also view messages in the queue
            acl.append((Allow, app_id, 'view'))

        # Everyons is allowed to view public queues
        if queue_data['type'] == 'public':
            acl.append((Allow, Everyone, 'view'))

    @property
    def count(self):
        total = 0
        for num in range(self.partitions):
            qn = '%s-%s' % (self.queue_name, num + 1)
            total += self.storage.count(self.consistency, self.application, qn)
        return total
