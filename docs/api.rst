.. _queuey_api:

==========
Queuey API
==========

The Queuey API is documented by URL and valid HTTP methods for each Queuey
resource. Arrows around the name indicate variables in the URL.

All calls return JSON, and unless otherwise indicated methods that take
input in the body expect form-encoded variables.

Application Resources
=====================

Access application information, and register queues. All calls to this resource
must include an Authorization header with the application key::

    Authorization: Application <key here>

Calls missing a valid Authorization header or valid Application key will be
rejected.

.. http:method:: GET /{application}

    :arg application: Application name
    :optparam integer limit: Amount of queues to list.
    :optparam string offset: A queue name to start with for paginating through the
                             result

    Returns a list of queues for the application. No sorting or ordering for
    this operation is available, and queues are not in any specific ordering.

    Example response::

        {
            'status': 'ok',
            'queues': ['a queue', 'another queue']
        }

.. http:method:: POST /{application}

    :arg application: Application name
    :optparam queue_name: Name of the queue to create
    :optparam integer partitions: How many partitions the queue should have.
                                  Defaults to 1.
    :optparam type: Type of queue to create, defaults to ``user`` which
                    requires authentication to access messages.
    :optparam consistency: Level of consistency for the queue, defaults to
                           ``strong``.
    :optparam principles: List of App or Browser ID's separated
                  with a comma if there's more than one

    Create a new queue for the application. Returns a JSON response indicating
    the status, the UUID4 hex string of the queue name (if not supplied), and
    the partitions created.

    Example response::

        {
            'status': 'ok',
            'application_name': 'notifications',
            'queue_name': 'ea2f39c0de9a4b9db6463123641631de',
            'partitions': 1,
            'type': 'user',
            'consistency': 'strong'
        }

Queue Resources
===============

Create messages on a queue, get messages, and delete messages or an entire
queue. Access varies depending on the queue, queues with a type of ``public`` 
may have messages viewed without any authentication. All other queue's require
an Application key to create messages, and viewing messages varies depending
on queue principles. By default an Application may create/view messages it
creates unless a set of principles was registered for the queue.

.. http:method:: GET /{application}/{queue_name}

    :arg application: Application name
    :arg queue_name: Queue name to access
    :optparam since: All messages newer than this timestamp *or* message id.
                     Should be formatted as seconds since epoch in GMT, or the
                     hexadecimal message ID.
    :optparam limit: Only return N amount of messages.
    :optparam order: Order of messages, can be set to either `ascending` or
                     `descending`. Defaults to `descending`.
    :optparam partitions: A specific partition number to retrieve messages from
                          or a comma separated list of partitions. Defaults to
                          retrieving messages from partition 1.

    Get messages from a queue. Messages are returned in order of newest to
    oldest.

    Example response::

        {
            'status': 'ok',
            'messages': [
                {
                    'message_id': '3a6592301e0911e190b1002500f0fa7c',
                    'timestamp': 1323973966282.637,
                    'body': 'jlaijwiel2432532jilj',
                    'partition': 1
                },
                {
                    'message_id': '3a8553d71e0911e19262002500f0fa7c',
                    'timestamp': 1323973966918.241,
                    'body': 'ion12oibasdfjioawneilnf',
                    'partition': 2
                }
            ]
        }

.. http:method:: POST /{application}/{queue_name}

    :arg application: Application name
    :arg queue_name: Queue name to access

    A form body containing a single message and optional partition
    value, or a set of message and partition pairs by number.

    Example single message POST (shown as dict)::

        {
            'body': 'this is a message',
            'partition': '1'
        }

    Example multiple message POST (shown as dict)::

        {
            'message.0.body': 'this is message 1',
            'message.0.ttl': '3600',
            'message.1.body': 'this is message 2',
            'message.1.partition': '3'
        }

    The second example lets the first message go to the default
    partition (1), while the second message is sent to partition
    3.

    Example success response::

        {
            'status': 'ok',
            'messages' [
                {
                    'key': '3a6592301e0911e190b1002500f0fa7c',
                    'timestamp': 1323976306.988889,
                    'partition': 1
                },
            ]
        }

.. http:method:: DELETE /{application}/{queue_name}

    :arg application: Application name
    :arg queue_name: Queue name to access
    :optparam messages: A comma separated list of message keys to delete. If
                        set, this implies that the registration will not be
                        deleted.
    :optparam delete_registration: Set to true to delete the queue registration
                                   as well as the messages. Defaults to false.
    :optparam partitions: If `delete_registration` is set to false, individual
                          partitions may be emptied. If messages are supplied,
                          only the partition they are from may be specified. If
                          delete_registration is True, partitions will be
                          ignored and all partitions will be removed.

    Delete a queues messages (and optionally the entire queue). If individual
    messages are specified and are not in the default partition (1), the
    partition must be provided as the ``partitions`` parameter.

    Example success response::

        {'status': 'ok'}

.. http:method:: GET /{application}/{queue_name}/info

    :arg application: Application name
    :arg queue_name: Queue name to access

    Get queue information. Returns a response indicating the status, and the
    information about the queue.

    Example response::

        {
            'status': 'ok',
            'application_name': 'notifications',
            'queue_name': 'ea2f39c0de9a4b9db6463123641631de',
            'partitions': 1,
            'created': 1322521547,
            'type': 'user',
            'count': 932
        }
