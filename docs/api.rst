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

.. http:method:: GET /v1/{application}

    :arg application: Application name
    :optparam integer limit: Amount of queues to list.
    :optparam string offset: A queue name to start with for paginating through the
                             result
    :optparam boolean details: Whether additional queue details such as the
                               consistency, type, partitions, and principles
                               for the queue should also be returned. Defaults
                               to false.
    :optparam boolean include_count: When including details, should the total
                                     message count be included? Defaults to
                                     false.

    Returns a list of queues for the application. No sorting or ordering for
    this operation is available, queues are not in any specific ordering but
    their order is consistent for proper pagination.

    Example response::

        {
            'status': 'ok',
            'queues': [
                {'queue_name': 'a queue'},
                {'queue_name': 'another queue'}
            ]
        }

    Example response with details::

        {
            'status': 'ok',
            'queues': [
                {
                    'queue_name': 'ea2f39c0de9a4b9db6463123641631de',
                    'partitions': 1,
                    'created': 1322521547,
                    'type': 'user',
                    'count': 932                
                },
                {
                    'queue_name': 'another queue',
                    'partitions': 4,
                    'created': 1325243233,
                    'type': 'user',
                    'count': 232                
                },
            ]
        }

.. http:method:: POST /v1/{application}

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
    the status, the UUID4 hex string of the queue name (if a queue_name was not
    supplied), and the partitions created.

    Calling this method with no parameters at all will yield a response like
    the one below.

    Example response::

        {
            'status': 'ok',
            'queue_name': 'ea2f39c0de9a4b9db6463123641631de',
            'partitions': 1,
            'type': 'user',
            'consistency': 'strong'
        }

.. http:method:: PUT /v1/{application}/{queue_name}

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
            'queue_name': 'ea2f39c0de9a4b9db6463123641631de',
            'partitions': 1,
            'type': 'user',
            'consistency': 'strong'
        }

.. http:method:: DELETE /v1/{application}/{queue_name}

    :arg application: Application name
    :arg queue_name: Queue name to access

    Delete a queue and all its partitions and messages.

    Example success response::

        {'status': 'ok'}

Message Management
==================

Create messages on a queue, get messages, and delete messages. Access varies
depending on the queue, queues with a type of ``public`` 
may have messages viewed without any authentication. All other queue's require
an Application key to create messages, and viewing messages varies depending
on queue principles. By default an Application may create/view messages it
creates unless a set of principles was registered for the queue.

.. http:method:: GET /v1/{application}/{queue_name}

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

.. http:method:: POST /v1/{application}/{queue_name}

    :arg application: Application name
    :arg queue_name: Queue name to access

    A body containing a single message and optional partition
    value, or a set of message and partition pairs by number.

    When the partition is not specified, the message will be randomly
    assigned to one of the partitions for a queue (or just the first
    one if the queue has only one partition).

    A TTL can be specified per message, in seconds till it should expire
    and be unavailable.

    **Posting a batch of messages (Using JSON)**

    Include a ``Content-Type`` HTTP header set to ``application/json`` with
    a body like the following::

        {'messages': [
            {
                'body': 'this is message 1',
                'ttl': 3600,
            },
            {
                'body': 'this is message 2',
                'partition': 3
            }
        ]}

    **Post an individual message**

    Any ``Content-Type`` header will be recorded with the message. The body
    is assumed to be the entirety of the POST body. The TTL or Partition can
    be set by including the appropriate value with either ``X-TTL`` or 
    ``X-Partition`` HTTP headers in the request.

    Example POST as seen by server including both *optional* HTTP headers::

        POST /notifications/ea2f39c0de9a4b9db6463123641631de HTTP/1.1
        Host: site.running.queuey
        User-Agent: AwesomeClient
        Content-Length: 36
        Content-Type: application/text
        X-TTL: 3600
        X-Partition: 2

        A really cool message body to store.

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

.. http:method:: DELETE /v1/{application}/{queue_name}/{messages}

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
