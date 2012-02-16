# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import re
import uuid

import colander
import simplejson

bid_match = re.compile(r'^(bid|app):\w+@\w+\.\w+$')


@colander.deferred
def default_queuename(node, kw):
    queue_name = kw.get('default_queue_name')
    if queue_name is None:
        queue_name = uuid.uuid4().hex
    return queue_name

_partition_node = colander.SchemaNode(colander.Int(), missing=1,
                                      validator=colander.Range(1, 200))
_queuename_node = colander.SchemaNode(
    colander.String(), missing=default_queuename)


# Custom JSON validator
class JSON(object):
    def deserialize(self, node, cstruct):
        if cstruct is colander.null:
            return colander.null
        try:
            data = simplejson.loads(cstruct)
        except simplejson.JSONDecodeError:
            raise colander.Invalid(node, '%r is not valid JSON data' % cstruct)
        return data


def permission_validator(node, value):
    if value is colander.null:
        return

    if ',' in value:
        results = [x.strip() for x in value.split(',')]
        valid_ids = filter(lambda x: bid_match.match(x), results)
        if len(results) != len(valid_ids):
            raise colander.Invalid(node, '%r is not a valid permission list.' %
                                   value)
    elif not bid_match.match(value):
        raise colander.Invalid(node, '%r is not a valid permission list.' %
                               value)


class NewQueue(colander.MappingSchema):
    queue_name = _queuename_node
    partitions = _partition_node
    type = colander.SchemaNode(colander.String(), missing='user',
                               validator=colander.OneOf(['public', 'user']))
    consistency = colander.SchemaNode(
        colander.String(), missing='strong', validator=colander.OneOf(
            ['weak', 'strong', 'very_strong']))
    permissions = colander.SchemaNode(colander.String(), missing=None,
                                      validator=permission_validator)


class QueueList(colander.MappingSchema):
    limit = colander.SchemaNode(colander.Int(), missing=None)
    offset = colander.SchemaNode(colander.String(), missing=None)


class Message(colander.MappingSchema):
    body = colander.SchemaNode(colander.String())
    partition = colander.SchemaNode(colander.Int(), missing=None,
                                    validator=colander.Range(1, 200))
    ttl = colander.SchemaNode(colander.Int(), missing=60 * 60 * 24 * 3,
                              validator=colander.Range(1, 60 * 60 * 24 * 3))


class MessageList(colander.SequenceSchema):
    message = Message()


class Messages(colander.MappingSchema):
    message = MessageList()
