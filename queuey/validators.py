# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import re
import uuid

import colander

BID_REGEX = re.compile(r'^(bid:\w+@\w+\.\w+|app:\w+)$')
INT_REGEX = re.compile(r'^\d+$')


@colander.deferred
def default_queuename(node, kw):
    queue_name = kw.get('default_queue_name')
    if queue_name is None:
        queue_name = uuid.uuid4().hex
    return queue_name


@colander.deferred
def max_queue_partition(node, kw):
    max_partition = kw['max_partition']
    return colander.Range(1, max_partition)


class CommaList(object):
    def deserialize(self, node, cstruct):
        if cstruct is colander.null:
            return colander.null
        return [x.strip() for x in cstruct.split(',') if x]


def principle_validator(node, value):
    for value in [x.strip() for x in value.split(',') if x]:
        if not BID_REGEX.match(value):
            raise colander.Invalid(node, '%r is not a valid permission list.' %
                                   value)


def comma_int_list(node, value):
    msg = ('%r is not a valid comma separated list of integers or a single '
           'integer.' % value)
    for val in value:
        if not INT_REGEX.match(val):
            raise colander.Invalid(node, msg)


class GetMessages(colander.MappingSchema):
    since = colander.SchemaNode(colander.String(), missing=None)
    limit = colander.SchemaNode(colander.Int(), missing=None,
                                validator=colander.Range(1, 1000))
    order = colander.SchemaNode(colander.String(), missing="ascending",
                                validator=colander.OneOf(['descending',
                                                          'ascending']))
    partitions = colander.SchemaNode(CommaList(), missing=[1],
                                    validator=comma_int_list)


class UpdateQueue(colander.MappingSchema):
    partitions = colander.SchemaNode(colander.Int(), missing=None,
                                     validator=colander.Range(1, 200))
    type = colander.SchemaNode(colander.String(), missing='user',
                               validator=colander.OneOf(['public', 'user']))
    consistency = colander.SchemaNode(
        colander.String(), missing='strong', validator=colander.OneOf(
            ['weak', 'strong', 'very_strong']))
    principles = colander.SchemaNode(colander.String(), missing=None,
                                      validator=principle_validator)


class NewQueue(colander.MappingSchema):
    partitions = colander.SchemaNode(colander.Int(), missing=1,
                                     validator=colander.Range(1, 200))
    queue_name = colander.SchemaNode(colander.String(),
                                     missing=default_queuename)
    type = colander.SchemaNode(colander.String(), missing='user',
                               validator=colander.OneOf(['public', 'user']))
    consistency = colander.SchemaNode(
        colander.String(), missing='strong', validator=colander.OneOf(
            ['weak', 'strong', 'very_strong']))
    principles = colander.SchemaNode(colander.String(), missing=None,
                                      validator=principle_validator)


class QueueList(colander.MappingSchema):
    limit = colander.SchemaNode(colander.Int(), missing=None)
    offset = colander.SchemaNode(colander.String(), missing=None)
    details = colander.SchemaNode(colander.Bool(), missing=False)
    include_count = colander.SchemaNode(colander.Bool(), missing=False)


class Message(colander.MappingSchema):
    body = colander.SchemaNode(colander.String(),
                               validator=colander.Length(min=1))
    partition = colander.SchemaNode(colander.Int(), missing=None,
                                    validator=max_queue_partition)
    ttl = colander.SchemaNode(colander.Int(), missing=60 * 60 * 24 * 3,
                              validator=colander.Range(1, 2 ** 25))


class MessageList(colander.SequenceSchema):
    message = Message()
