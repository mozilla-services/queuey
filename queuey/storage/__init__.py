# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Mozilla Message Queue
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
# Ben Bangert (bbangert@mozilla.com)
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
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
        if name.startswith(prefix):
            config[name[len(prefix):]] = value
        else:
            config[name] = value
    klass = dotted_resolver.resolve(config.pop('backend'))
    return klass(**config)


class MessageQueueBackend(Interface):
    """A MessageQueue Backend"""
    def __init__(self, username=None, password=None, database='MessageQueue',
                 host='localhost'):
        """Initialize the backend"""

    def retrieve(self, queue_name, limit=None, timestamp=None,
                 order="descending"):
        """Retrieve messages from a queue

        :param queue_name: Queue name
        :queue_name type: string
        :param limit: Amount of messages to retrieve
        :limit type: int
        :param timestamp: Retrieve messages starting with this timestamp
        :timestamp type: datetime
        :param order: Which order to traverse the messages. Defaults to
                      descending order.
        :order type: `ascending` or `descending`

        :returns: A list of (key, timestamp, message_body) tuples
        :rtype: list
        :raises: :exc:`~queuey.exceptions.QueueDoesNotExist` if the
                 queue does not exist

        Example response::

            [
                ('aebb663d1d4311e1a65f002500f0fa7c', 1323973966282.637,
                 'jiawefjilawe'),
                ('ae45017a1d4311e19562002500f0fa7c', 1323973966918.241,
                 'auwiofuweni3')
            ]

        The messages will be ordered based on the ``order`` param using
        the timestamp.

        .. note::

            The message body is considered raw string data and should
            have no encoding/decoding performed on it.

        """

    def push(self, queue_name, message, ttl=3600 * 24 * 3):
        """Push a message onto the given queue

        The queue is assumed to exist, and will be created if it does not
        exist.

        :param queue_name: Queue name
        :queue_name type: string
        :param message: Message to add to the queue
        :message type: string
        :param ttl: Time to Live in seconds for the message, after this
                    period the message should be unavilable
        :ttl type: int

        :returns: The message key and timestamp as a tuple
        :rtype: tuple

        """

    def exists(self, queue_name):
        """Check to see if a queue of a given name exists

        :param queue_name: Queue name
        :queue_name type: string

        :returns: Whether the queue exists.
        :rtype: bool

        """

    def truncate(self, queue_name):
        """Remove all contents of the queue

        :param queue_name: Queue name
        :queue_name type: string

        :returns: Whether the queue was truncated.
        :rtype: bool
        :raises: :exc:`~queuey.exceptions.QueueDoesNotExist` if the
                 queue does not exist

        """

    def count(self, queue_name):
        """Returns the amount of messages in the queue

        :param queue_name: Queue name
        :queue_name type: string

        :returns: Message total
        :rtype: int
        :raises: :exc:`~queuey.exceptions.QueueDoesNotExist` if the
                 queue does not exist

        """


class MetadataBackend(Interface):
    """A Metadata Backend

    Stores associated metadata for the message queue system, such as the
    active applications registered, and the queues that have been
    allocated for each application.

    """
    def __init__(self, username=None, password=None, database='MetaData',
                 host='localhost'):
        """Initialize the backend"""

    def register_application(self, application_name):
        """Register the application

        :param application_name: Name of the application
        :application_name type: string

        :returns: Whether the application was created
        :rtype: bool
        :raises: :exc:`~queuey.exceptions.ApplicationExists` if the
                 application is already registered

        """

    def register_queue(self, application_name, queue_name, partitions):
        """Register a queue for the given application

        Registers a queue for the application and when it was
        created in seconds since the epoch, and how many partitions
        should be allocated.

        :param application_name: Name of the application
        :application_name type: string
        :param queue_name: Queue name
        :queue_name type: string
        :param partitions: Amount of partitions for the queue
        :partitions type: int

        :returns: Whether the queue was registered
        :rtype: bool
        :raises: :exc:`~queuey.exceptions.ApplicationNotRegistered` if
                 the application is not registered.

        """

    def remove_queue(self, application_name, queue_name):
        """Remove a queue registration for the given application

        :param application_name: Name of the application
        :application_name type: string
        :param queue_name: Queue name
        :queue_name type: string

        :returns: Whether the queue was removed.
        :rtype: bool
        :raises: :exc:`~queuey.exceptions.ApplicationNotRegistered` if
                 the application is not registered.

        """

    def queue_information(self, application_name, queue_name):
        """Return information regarding the queue for the application

        :param application_name: Name of the application
        :application_name type: string
        :param queue_name: Queue name
        :queue_name type: string

        :returns: Queue information
        :rtype: dict
        :raises: :exc:`~queuey.exceptions.QueueDoesNotExist` if the
                 queue does not exist

        Example response::

            {
                'created': 82989382,
                'partitions': 20
            }

        """
