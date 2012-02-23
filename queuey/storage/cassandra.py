# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import inspect
import uuid
import time

import pycassa
from pycassa.index import create_index_expression
from pycassa.index import create_index_clause
from zope.interface import implements

from queuey.storage import MessageQueueBackend
from queuey.storage import MetadataBackend
from queuey.storage import StorageUnavailable

ONE = pycassa.ConsistencyLevel.ONE
LOCAL_QUORUM = pycassa.ConsistencyLevel.LOCAL_QUORUM
EACH_QUORUM = pycassa.ConsistencyLevel.EACH_QUORUM


def parse_hosts(raw_hosts):
    """Parses out hosts into a list"""
    hosts = []
    if ',' in raw_hosts:
        names = [x.strip() for x in raw_hosts.split(',')]
    else:
        names = [raw_hosts]
    for name in names:
        if ':' not in name:
            name += ':9160'
        hosts.append(name)
    return hosts


def wrap_func(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (pycassa.UnavailableException, pycassa.TimedOutException):
            raise StorageUnavailable("Unable to contact storage pool")
    for attr in "__module__", "__name__", "__doc__":
        setattr(wrapper, attr, getattr(func, attr))
    return wrapper


def raise_unavailable(cls):
    """Wrap public method calls to return appropriate exception in the
    event the cluster is unavailable or has insufficient nodes available
    for the operation"""
    for name, meth in inspect.getmembers(cls, inspect.ismethod):
        if name.startswith('_'):
            continue
        setattr(cls, name, wrap_func(meth))
    return cls


@raise_unavailable
class CassandraQueueBackend(object):
    implements(MessageQueueBackend)

    def __init__(self, username=None, password=None, database='MessageStore',
                 host='localhost', base_delay=None):
        """Create a Cassandra backend for the Message Queue

        :param host: Hostname, accepts either an IP, hostname, hostname:port,
                     or a comma seperated list of 'hostname:port'

        """
        hosts = parse_hosts(host)
        self.pool = pool = pycassa.ConnectionPool(
            keyspace=database,
            server_list=hosts,
        )
        self.message_fam = pycassa.ColumnFamily(pool, 'Messages')
        self.meta_fam = pycassa.ColumnFamily(pool, 'MessageMetadata')
        self.delay = int(base_delay) if base_delay else 0
        self.cl = ONE if len(hosts) < 2 else None

    def _get_cl(self, consistency):
        """Return the consistency operation to use"""
        if consistency == 'weak':
            return ONE
        elif consistency == 'very_strong':
            return EACH_QUORUM
        else:
            return LOCAL_QUORUM

    def _get_delay(self, consistency):
        """Return the delay value to use for the results"""
        if self.cl:
            return 0
        elif consistency == 'weak':
            return 1 + self.delay
        elif consistency == 'very_strong':
            return 600 + self.delay
        else:
            return 5 + self.delay

    def retrieve_batch(self, consistency, application_name, queue_names,
                       limit=None, include_metadata=False, start_at=None,
                       order="ascending"):
        """Retrieve a batch of messages off the queue"""
        if not isinstance(queue_names, list):
            raise Exception("queue_names must be a list")

        cl = self.cl or self._get_cl(consistency)
        delay = self._get_delay(consistency)

        kwargs = {'read_consistency_level': cl}
        if order == 'descending':
            kwargs['column_reversed'] = True

        if limit:
            kwargs['column_count'] = limit

        if start_at:
            if isinstance(start_at, str):
                # Assume its a hex, transform to a datetime
                start_at = uuid.UUID(hex=start_at)

            kwargs['column_start'] = start_at

        queue_names = ['%s:%s' % (application_name, x) for x in queue_names]
        results = self.message_fam.multiget(keys=queue_names, **kwargs)
        results = results.items()
        if delay:
            cut_off = time.time() - delay
            # Turn it into time in ns, for efficient comparison
            cut_off = cut_off * 1e9 / 100 + 0x01b21dd213814000L

        result_list = []
        msg_hash = {}
        for queue_name, messages in results:
            for msg_id, body in messages.items():
                if delay and msg_id.time >= cut_off:
                    continue
                obj = {
                    'message_id': msg_id.hex,
                    'timestamp': (msg_id.time - 0x01b21dd213814000L) / 1e7,
                    'body': body,
                    'metadata': {},
                    'queue_name': queue_name[queue_name.find(':'):]
                }
                result_list.append(obj)
                msg_hash[msg_id] = obj

        # Get metadata?
        if include_metadata:
            results = self.meta_fam.multiget(keys=msg_hash.keys())
            for msg_id, metadata in results.items():
                msg_hash[msg_id]['metadata'] = metadata
        return result_list

    def retrieve(self, consistency, application_name, queue_name, message_id,
                 include_metadata=False):
        """Retrieve a single message"""
        cl = self.cl or self._get_cl(consistency)
        if isinstance(message_id, str):
            # Convert to uuid for lookup
            message_id = uuid.UUID(hex=message_id)

        kwargs = {
            'read_consistency_level': cl,
            'columns': [message_id]}
        queue_name = '%s:%s' % (application_name, queue_name)
        try:
            results = self.message_fam.get(key=queue_name, **kwargs)
        except pycassa.NotFoundException:
            return {}
        msg_id, body = results.items()[0]

        obj = {
            'message_id': msg_id.hex,
            'timestamp': (msg_id.time - 0x01b21dd213814000L) / 1e7,
            'body': body,
            'metadata': {},
            'queue_name': queue_name[queue_name.find(':'):]
        }

        # Get metadata?
        if include_metadata:
            try:
                results = self.meta_fam.get(key=msg_id)
                obj['metadata'] = results
            except pycassa.NotFoundException:
                pass
        return obj

    def push(self, consistency, application_name, queue_name, message,
             metadata=None, ttl=60 * 60 * 24 * 3):
        """Push a message onto the queue"""
        cl = self.cl or self._get_cl(consistency)
        now = uuid.uuid1()
        queue_name = '%s:%s' % (application_name, queue_name)
        if metadata:
            batch = pycassa.batch.Mutator(self.pool,
                                          write_consistency_level=cl)
            batch.insert(self.message_fam, key=queue_name,
                         columns={now: message}, ttl=ttl)
            batch.insert(self.meta_fam, key=now, columns=metadata, ttl=ttl)
            batch.send()
        else:
            self.message_fam.insert(key=queue_name, columns={now: message},
                                    ttl=ttl, write_consistency_level=cl)
        timestamp = (now.time - 0x01b21dd213814000L) / 1e7
        return now.hex, timestamp

    def push_batch(self, consistency, application_name, message_data):
        """Push a batch of messages"""
        cl = self.cl or self._get_cl(consistency)
        batch = pycassa.batch.Mutator(self.pool, write_consistency_level=cl)
        msgs = []
        for queue_name, body, ttl, metadata in message_data:
            qn = '%s:%s' % (application_name, queue_name)
            now = uuid.uuid1()
            batch.insert(self.message_fam, key=qn, columns={now: body},
                         ttl=ttl)
            if metadata:
                batch.insert(self.meta_fam, key=now, columns=metadata, ttl=ttl)
            timestamp = (now.time - 0x01b21dd213814000L) / 1e7
            msgs.append((now.hex, timestamp))
        batch.send()
        return msgs

    def truncate(self, consistency, application_name, queue_name):
        """Remove all contents of the queue"""
        cl = self.cl or self._get_cl(consistency)
        queue_name = '%s:%s' % (application_name, queue_name)
        self.message_fam.remove(key=queue_name, write_consistency_level=cl)
        return True

    def delete(self, consistency, application_name, queue_name, *keys):
        """Delete a batch of keys"""
        cl = self.cl or self._get_cl(consistency)
        queue_name = '%s:%s' % (application_name, queue_name)
        self.message_fam.remove(key=queue_name,
                                columns=[uuid.UUID(hex=x) for x in keys],
                                write_consistency_level=cl)
        return True

    def count(self, consistency, application_name, queue_name):
        """Return a count of the items in this queue"""
        cl = self.cl or self._get_cl(consistency)
        queue_name = '%s:%s' % (application_name, queue_name)
        return self.message_fam.get_count(key=queue_name,
                                          read_consistency_level=cl)


@raise_unavailable
class CassandraMetadata(object):
    implements(MetadataBackend)

    def __init__(self, username=None, password=None, database='MetadataStore',
                 host='localhost'):
        """Create a Cassandra backend for the Message Queue

        :param host: Hostname, accepts either an IP, hostname, hostname:port,
                     or a comma seperated list of 'hostname:port'

        """
        hosts = parse_hosts(host)
        self.pool = pool = pycassa.ConnectionPool(
            keyspace=database,
            server_list=hosts,
        )
        self.metric_fam = pycassa.ColumnFamily(pool, 'ApplicationQueueData')
        self.queue_fam = pycassa.ColumnFamily(pool, 'Queues')
        self.cl = ONE if len(hosts) < 2 else None

    def register_queue(self, application_name, queue_name, **metadata):
        """Register a queue, optionally with metadata"""
        # Determine if its registered already
        cl = self.cl or LOCAL_QUORUM
        queue_name = '%s:%s' % (application_name, queue_name)
        try:
            self.queue_fam.get(queue_name)
            if metadata:
                # Only update metadata
                self.queue_fam.insert(queue_name, columns=metadata)
            return
        except pycassa.NotFoundException:
            pass

        metadata['application'] = application_name
        if 'created' not in metadata:
            metadata['created'] = time.time()
        self.queue_fam.insert(queue_name, columns=metadata,
                              write_consistency_level=cl)
        self.metric_fam.add(application_name, column='queue_count', value=1,
                            write_consistency_level=cl)
        return True

    def remove_queue(self, application_name, queue_name):
        """Remove a queue"""
        cl = self.cl or LOCAL_QUORUM
        queue_name = '%s:%s' % (application_name, queue_name)
        try:
            self.queue_fam.get(key=queue_name,
                               read_consistency_level=cl)
        except pycassa.NotFoundException:
            return False
        self.queue_fam.remove(key=queue_name,
                            write_consistency_level=cl)
        self.metric_fam.add(application_name, column='queue_count', value=-1,
                            write_consistency_level=cl)
        return True

    def queue_list(self, application_name, limit=100, offset=None):
        """Return list of queues"""
        cl = self.cl or LOCAL_QUORUM
        app_expr = create_index_expression('application', application_name)
        if offset:
            offset = '%s:%s' % (application_name, offset)
            clause = create_index_clause([app_expr], start_key=offset,
                                         count=limit)
        else:
            clause = create_index_clause([app_expr], count=limit)
        results = self.queue_fam.get_indexed_slices(
            clause, columns=['application'], read_consistency_level=cl)
        # Pull off the application name in front
        app_len = len(application_name) + 1
        return [key[app_len:] for key, _ in results]

    def queue_information(self, application_name, queue_names):
        """Return information on a registered queue"""
        cl = self.cl or LOCAL_QUORUM
        if not isinstance(queue_names, list):
            raise Exception("Queue names must be a list.")
        queue_names = ['%s:%s' % (application_name, queue_name) for
                       queue_name in queue_names]
        results = self.queue_fam.multiget(keys=queue_names,
                                          read_consistency_level=cl)
        return [x[1] for x in results.items()]
