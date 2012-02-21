.. _queuey_api:

==========
Queuey API
==========

The Queuey API is documented by URL and valid HTTP methods for each Queuey
resource. Arrows around the name indicate variables in the URL.

All calls return JSON, and unless otherwise indicated methods that take
input in the body expect form-encoded variables.

Queue Management
================

Access queue information, create, update, and delete queues. All calls to these
methods must include an Authorization header with the application key::

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

.. http:method:: PUT /{application}/{queue_name}

    :arg application: Application name
    :arg queue_name: Queue name to access

    :optparam integer partitions: How many partitions the queue should have.
    :optparam type: Type of queue to create, 'user' or 'public'.
    :optparam consistency: Level of consistency for the queue.
    :optparam principles: List of App or Browser ID's separated
                          with a comma if there's more than one

    Update queue parameters. Partitions may only be increased, not decreased.
    Other settings overwrite existing parameters for the queue, to modify the
    principles one should first fetch the existing ones, change them as
    appropriate and PUT the new ones.

    Example response::

        {
            'status': 'ok',
            'application_name': 'notifications',
            'queue_name': 'ea2f39c0de9a4b9db6463123641631de',
            'partitions': 1,
            'type': 'user',
            'consistency': 'strong'
        }

.. http:method:: DELETE /{application}/{queue_name}

    :arg application: Application name
    :arg queue_name: Queue name to access

    Delete a queue and all its messages.

    Example success response::

        {'status': 'ok'}

Multiple Messages
=================

Create messages on a queue, get messages, and delete messages. Access varies
depending on the queue, queues with a type of ``public`` 
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
                     `descending`. Defaults to `ascending`.
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

    When the partition is not specified, the message will be randomly
    assigned to one of the partitions for a queue (or just the first
    one if the queue has only one partition).

    A TTL can be specified per message, in seconds till it should expire
    and be unavailable.

    Example single message POST with all optional params (shown as dict)::

        {
            'body': 'this is a message',
            'partition': '1',
            'ttl': '3600'
        }

    Example single message POST with minimum params::

        {
            'body': 'this is a message'
        }

    Example multiple message POST (shown as dict)::

        {
            'message.0.body': 'this is message 1',
            'message.0.ttl': '3600',
            'message.1.body': 'this is message 2',
            'message.1.partition': '3'
        }

    The second example lets the first message go to a random partition,
    while the second message is sent specifically to partition 3.

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

.. http:method:: GET /{application}/{queue_name}/info

    :arg application: Application name
    :arg queue_name: Queue name to access
    :optparam include_count: Include the message count, use carefully as the
                             counting could take awhile on larger and/or
                             heavily partitioned queues.

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

.. http:method:: DELETE /{application}/{queue_name}/{messages}

    :arg application: Application name
    :arg queue_name: Queue name to access
    :arg messages: A single hex message id, or comma separated list of hex
                   message id's. To indicate partitions for the messages,
                   prefix the hex message with the partition number and a
                   colon.

    Delete a message, or multiple messages from a queue. The message ID must
    be prefixed with the partition number and a colon if the queue has multiple
    partitions to indicate which one contains the message.

    Example of deleting a message from partition 2::

        # The %3 is a URL encoded colon
        DELETE /my_application/somequeuename/2%38cc967e0cf1e45e3b0d4926c90057caf

    Example success response::

        {'status': 'ok'}

Individual Messages
===================

.. http:method:: GET /{application}/{queue_name}/{message_id}

    :arg application: Application name
    :arg queue_name: Queue name to access
    :arg message_id: A message ID to access

    Returns an individual message from queuey. If the message has a
    Content-Type recorded for it, the response will include it as an
    HTTP header.

.. http:method:: PUT /{application}/{queue_name}/{message_id}

    :arg application: Application name
    :arg queue_name: Queue name to access
    :arg message_id: A message ID to access

    Update the message stored at this id. The body and metadata associated
    with the message may be changed.

.. http:method:: DELETE /{application}/{queue_name}/{message_id}

    :arg application: Application name
    :arg queue_name: Queue name to access
    :arg message_id: A message ID to access

    Delete the message id at this URI.
