# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
"""MessageQueue Storage Interface

.. note::

    The MetadataBackend and MessageQueueBackend are separate in the event
    that the message queuing backend is suitable only for messages and
    not storing the additional application and queue metadata.

"""
from pyramid.util import DottedNameResolver
from zope.interface import Interface

dotted_resolver = DottedNameResolver(None)


def configure_from_settings(object_name, settings):
    """Given a settings dict, create the storage instance and return it"""
    config = {}
    prefix = object_name + '.'
    for name, value in settings.iteritems():
        name = config[name[len(prefix):]] if name.startswith(prefix) else name
        config[name] = value
    klass = dotted_resolver.resolve(config.pop('backend'))
    return klass(**config)


class StorageUnavailable(Exception):
    """Raised when the storage backend is unavailable"""


class MessageQueueBackend(Interface):
    """A MessageQueue Backend"""
    def __init__(username=None, password=None, database='MessageQueue',
                 host='localhost'):
        """Initialize the backend

        If any operation fails due to servers being unavailable, the
        :exc:`StorageUnavailable` exception should be raised.

        """

    def retrieve_batch(consistency, application_name, queue_names,
                       limit=None, include_metadata=False, start_at=None,
                       order="ascending"):
        """Retrieve a batch of messages from a queue

        :param consistency: Desired consistency of the read operation
        :param application_name: Name of the application
        :param queue_names: List of queue names to retrieve from
        :param limit: Amount of messages to retrieve
        :param include_metadata: Whether to include message metadata
        :param start_at: Either a timestamp or message id to start from
        :param order: Which order to traverse the messages. Defaults to
                      ascending order.
        :type order: `ascending` or `descending`

        :returns: A list of dicts, empty if no messages meet the criteria
        :rtype: list

        Example response::

            [
                {
                    'message_id': 'aebb663d1d4311e1a65f002500f0fa7c',
                    'timestamp': 1323973966282.637,
                    'body': 'jiawefjilawe',
                    'metadata': {},
                    'queue_name': 'a queue'
                },
                {
                    'message_id': 'ae45017a1d4311e19562002500f0fa7c',
                    'timestamp': 1323973966918.241,
                    'body': 'auwiofuweni3',
                    'metadata': {},
                    'queue_name': 'other queue'
                },
            ]

        The messages will be ordered based on the ``order`` param using
        the timestamp.

        .. note::

            The limit is applied per queue_name, so a limit of 10 with 3
            queue names supplied could return up to 30 messages.

        """

    def retrieve(consistency, application_name, queue_name, message_id,
                 include_metadata=False):
        """Retrieve a single message

        :param consistency: Desired consistency of the read operation
        :param application_name: Name of the application
        :param queue_name: Queue name
        :param message_id: Message id to retrieve
        :param include_metadata: Whether to include message metadata

        :returns: A dict
        :rtype: dict

        Example response::

        {
            'message_id': 'ae45017a1d4311e19562002500f0fa7c',
            'timestamp': 1323973966918.241,
            'body': 'auwiofuweni3',
            'metadata': {}
        }

        """

    def push(consistency, application_name, queue_name, message,
             metadata=None, ttl=3600 * 24 * 3, timestamp=None):
        """Push a message onto the given queue

        The queue is assumed to exist, and will be created if it does not
        exist.

        :param consistency: Desired consistency of the write operation
        :param application_name: Name of the application
        :param queue_name: Queue name
        :param message: Message to add to the queue
        :param metadata: Additional metadata to record for the message
        :type metadata: dict
        :param ttl: Time to Live in seconds for the message, after this
                    period the message should be unavilable
        :param timestamp: The timestamp to use for the message, should be
                          either a `uuid.uuid1` or a decimal/float of seconds
                          since the epoch as time.time() would return.
                          Defaults to the current time.

        :returns: The message id and timestamp as a tuple
        :rtype: tuple

        Example response::

            ('ae45017a1d4311e19562002500f0fa7c', 1323973966918.241)

        """

    def push_batch(consistency, application_name, message_data):
        """Push a batch of messages to queues

        The queue(s) are assumed to exist, and will be created if
        they do not exist.

        :param consistency: Desired consistency of the write operation
        :param application_name: Name of the application
        :param message_data: A list of messages to insert into queues
        :type message_data: List of tuples, where each tuple is the
                            queue_name, message body, TTL, and a dict of
                            message metadata.

        :returns: The message id's and timestamps as a list of tuples in the
                  order they were sent
        :rtype: list of tuples

        Example message_data content::

            [
                ('my_queue', 'some message body', 3600, {}),
                ('other_queue', 'other body', 7200, {})
            ]

        Example response::

            [
                ('ae45017a1d4311e19562002500f0fa7c', 1323973966282.637).
                ('aebb663d1d4311e1a65f002500f0fa7c', 1323973966918.241)
            ]

        """

    def truncate(consistency, application_name, queue_name):
        """Remove all contents of the queue

        :param consistency: Desired consistency of the truncate operation
        :param application_name: Name of the application
        :param queue_name: Queue name

        :returns: Whether the queue was truncated.
        :rtype: bool

        """

    def delete(consistency, application_name, queue_name, *ids):
        """Delete all the given message ids from the queue

        :param consistency: Desired consistency of the delete operation
        :param application_name: Name of the application
        :param queue_name: Queue name
        :param ids: Message ids that should be removed

        :returns: Whether the delete executed successfully
        :rtype: bool

        """

    def count(consistency, application_name, queue_name):
        """Returns the amount of messages in the queue

        :param consistency: Desired consistency of the read operation
        :param application_name: Name of the application
        :param queue_name: Queue name

        :returns: Message total
        :rtype: int

        """


class MetadataBackend(Interface):
    """A Metadata Backend

    Stores associated metadata for the message queue system, such as the
    active applications registered, and the queues that have been
    allocated for each application.

    """
    def __init__(username=None, password=None, database='MetaData',
                 host='localhost'):
        """Initialize the backend"""

    def register_queue(application_name, queue_name, **metadata):
        """Register a queue for the given application

        Registers a queue for the application and when it was
        created in seconds since the epoch, and additional metadata.

        This function should record all data needed to lookup queues
        by application name, along with the metadata.

        :param application_name: Name of the application
        :param queue_name: Queue name
        :param metadata: Queue metadata

        :returns: Whether the queue was registered
        :rtype: bool

        """

    def remove_queue(application_name, queue_name):
        """Remove a queue registration for the given application

        :param application_name: Name of the application
        :param queue_name: Queue name

        :returns: Whether the queue was removed.
        :rtype: bool

        """

    def queue_list(application_name, limit=100, offset=None):
        """Return a list of queues registered for the application

        :param application_name: Name of the application
        :param limit: How many queue names to return at once
        :param offset: Start at a specific queue_name offset

        :returns: List of queues registered for the application
        :rtype: list

        """

    def queue_information(application_name, queue_names):
        """Return information regarding the queue for the application

        This is a mix of basic queue information as well as the
        queue metadata.

        :param application_name: Name of the application
        :param queue_names: Queue names to retreive information from

        :returns: Queue information, an empty dict if the queue doesn't
                  exist
        :rtype: dict

        Example response::

            [
            {
                'created': 82989382,
                'partitions': 20,
                'application': 'your app name',
                'type': 'user',
                'consistency': 'strong',
                'principles': 'bid:fred@browserid.org,bid:george@home.com'
            }
            ]

        """
