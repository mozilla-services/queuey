# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from cdecimal import Decimal
import inspect
import uuid
import time

import pycassa
from pycassa.index import create_index_expression
from pycassa.index import create_index_clause
from pycassa import system_manager
from thrift.Thrift import TException
from zope.interface import implements

from queuey.storage import MessageQueueBackend
from queuey.storage import MetadataBackend
from queuey.storage import StorageUnavailable
from queuey.storage.util import convert_time_to_uuid

ONE = pycassa.ConsistencyLevel.ONE
QUORUM = pycassa.ConsistencyLevel.QUORUM
LOCAL_QUORUM = pycassa.ConsistencyLevel.LOCAL_QUORUM
EACH_QUORUM = pycassa.ConsistencyLevel.EACH_QUORUM
DECIMAL_1E7 = Decimal('1e7')


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
        except (pycassa.UnavailableException, pycassa.TimedOutException,
                pycassa.MaximumRetryException):
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
                 host='localhost', base_delay=None, multi_dc=False,
                 create_schema=True):
        """Create a Cassandra backend for the Message Queue

        :param host: Hostname, accepts either an IP, hostname, hostname:port,
                     or a comma seperated list of 'hostname:port'

        """
        hosts = parse_hosts(host)
        if create_schema:
            self._create_schema(hosts[0], database)
        credentials = None
        if username and password is not None:
            credentials = dict(username=username, password=password)
        self.pool = pool = pycassa.ConnectionPool(
            keyspace=database,
            server_list=hosts,
            credentials=credentials,
        )
        self.message_fam = pycassa.ColumnFamily(pool, 'Messages')
        self.meta_fam = pycassa.ColumnFamily(pool, 'MessageMetadata')
        self.delay = int(base_delay) if base_delay else 0
        self.cl = ONE if len(hosts) < 2 else None
        self.multi_dc = multi_dc

    def _create_schema(self, host, database):
        try:
            sm = Schema(host)
            sm.install_message(database)
            sm.close()
        except TException:
            pass

    def _get_cl(self, consistency):
        """Return the consistency operation to use"""
        if consistency == 'weak':
            return ONE
        elif self.multi_dc == False:
            return QUORUM
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
            if isinstance(start_at, basestring):
                # Assume its a hex, transform to a datetime
                start_at = uuid.UUID(hex=start_at)
            else:
                # Assume its a float/decimal, convert to UUID
                start_at = convert_time_to_uuid(start_at)

            kwargs['column_start'] = start_at

        queue_names = ['%s:%s' % (application_name, x) for x in queue_names]
        results = self.message_fam.multiget(keys=queue_names, **kwargs)
        results = results.items()
        if delay:
            cut_off = time.time() - delay
            # Turn it into time in ns, for efficient comparison
            cut_off = int(cut_off * 1e7) + 0x01b21dd213814000L

        result_list = []
        msg_hash = {}
        for queue_name, messages in results:
            for msg_id, body in messages.items():
                if delay and msg_id.time >= cut_off:
                    continue
                obj = {
                    'message_id': msg_id.hex,
                    'timestamp': (Decimal(msg_id.time - 0x01b21dd213814000L) /
                        DECIMAL_1E7),
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
        if isinstance(message_id, basestring):
            # Convert to uuid for lookup
            message_id = uuid.UUID(hex=message_id)
        else:
            # Assume its a float/decimal, convert to UUID
            message_id = convert_time_to_uuid(message_id)

        kwargs = {
            'read_consistency_level': cl,
            'columns': [message_id]}
        queue_name = '%s:%s' % (application_name, queue_name)
        try:
            results = self.message_fam.get(key=queue_name, **kwargs)
        except (pycassa.NotFoundException, pycassa.InvalidRequestException):
            return {}
        msg_id, body = results.items()[0]

        obj = {
            'message_id': msg_id.hex,
            'timestamp': (Decimal(msg_id.time - 0x01b21dd213814000L) /
                DECIMAL_1E7),
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
             metadata=None, ttl=60 * 60 * 24 * 3, timestamp=None):
        """Push a message onto the queue"""
        cl = self.cl or self._get_cl(consistency)
        if not timestamp:
            now = uuid.uuid1()
        elif isinstance(timestamp, (float, Decimal)):
            now = convert_time_to_uuid(timestamp, randomize=True)
        else:
            now = uuid.UUID(hex=timestamp)
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
        timestamp = Decimal(now.time - 0x01b21dd213814000L) / DECIMAL_1E7
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
            timestamp = (Decimal(now.time - 0x01b21dd213814000L) / DECIMAL_1E7)
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
                 host='localhost', multi_dc=False, create_schema=True):
        """Create a Cassandra backend for the Message Queue

        :param host: Hostname, accepts either an IP, hostname, hostname:port,
                     or a comma seperated list of 'hostname:port'

        """
        hosts = parse_hosts(host)
        if create_schema:
            self._create_schema(hosts[0], database)
        credentials = None
        if username and password is not None:
            credentials = dict(username=username, password=password)
        self.pool = pool = pycassa.ConnectionPool(
            keyspace=database,
            server_list=hosts,
            credentials=credentials,
        )
        self.metric_fam = pycassa.ColumnFamily(pool, 'ApplicationQueueData')
        self.queue_fam = pycassa.ColumnFamily(pool, 'Queues')
        self.cl = ONE if len(hosts) < 2 else None
        self.multi_dc = multi_dc

    def _create_schema(self, host, database):
        try:
            sm = Schema(host)
            sm.install_metadata(database)
            sm.close()
        except TException:
            pass

    def register_queue(self, application_name, queue_name, **metadata):
        """Register a queue, optionally with metadata"""
        # Determine if its registered already
        cl = self.cl or LOCAL_QUORUM if self.multi_dc else QUORUM
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
        cl = self.cl or LOCAL_QUORUM if self.multi_dc else QUORUM
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
        cl = self.cl or LOCAL_QUORUM if self.multi_dc else QUORUM
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
        if not isinstance(queue_names, list):
            raise Exception("Queue names must be a list.")
        queue_names = ['%s:%s' % (application_name, queue_name) for
                       queue_name in queue_names]
        queues = self.queue_fam.multiget(keys=queue_names,
                                          read_consistency_level=ONE)
        results = []
        for queue in queue_names:
            results.append(queues.get(queue, {}))
        return results


class Schema(object):

    COUNTER_COLUMN_TYPE = system_manager.COUNTER_COLUMN_TYPE
    INT_TYPE = system_manager.INT_TYPE
    FLOAT_TYPE = system_manager.FLOAT_TYPE
    KEYS_INDEX = system_manager.KEYS_INDEX
    LONG_TYPE = system_manager.LONG_TYPE
    UTF8_TYPE = system_manager.UTF8_TYPE
    TIME_UUID_TYPE = system_manager.TIME_UUID_TYPE

    def __init__(self, host='localhost:9160'):
        self.host = host
        self.sm = system_manager.SystemManager(self.host)

    def install(self):
        self.install_message()
        self.install_metadata()
        self.close()

    def install_message(self, database='MessageStore'):
        sm = self.sm
        keyspaces = sm.list_keyspaces()
        if database not in keyspaces:
            sm.create_keyspace(database,
                system_manager.SIMPLE_STRATEGY, {'replication_factor': '1'})

        cfs = sm.get_keyspace_column_families(database)
        if 'Messages' not in cfs:
            sm.create_column_family(database, 'Messages',
                comparator_type=self.TIME_UUID_TYPE,
                default_validation_class=self.UTF8_TYPE,
                key_validation_class=self.UTF8_TYPE,
            )

        if 'MessageMetadata' not in cfs:
            sm.create_column_family(database, 'MessageMetadata',
                comparator_type=self.UTF8_TYPE,
                default_validation_class=self.UTF8_TYPE,
                key_validation_class=self.TIME_UUID_TYPE,
                column_validation_classes={
                    'ContentType': self.UTF8_TYPE,
                    'ContentLength': self.LONG_TYPE,
                    }
            )

    def install_metadata(self, database='MetadataStore'):
        sm = self.sm
        keyspaces = sm.list_keyspaces()
        if database not in keyspaces:
            sm.create_keyspace(database,
                system_manager.SIMPLE_STRATEGY, {'replication_factor': '1'})

        cfs = sm.get_keyspace_column_families(database)
        if 'ApplicationQueueData' not in cfs:
            sm.create_column_family(database, 'ApplicationQueueData',
                comparator_type=self.UTF8_TYPE,
                default_validation_class=self.COUNTER_COLUMN_TYPE,
                key_validation_class=self.UTF8_TYPE,
                caching='all',
                column_validation_classes={
                    'queue_count': self.COUNTER_COLUMN_TYPE,
                    }
            )

        if 'Queues' not in cfs:
            sm.create_column_family(database, 'Queues',
                comparator_type=self.UTF8_TYPE,
                key_validation_class=self.UTF8_TYPE,
                caching='all',
                column_validation_classes={
                    'partitions': self.INT_TYPE,
                    'application': self.UTF8_TYPE,
                    'created': self.FLOAT_TYPE,
                    'type': self.UTF8_TYPE,
                    'consistency': self.UTF8_TYPE,
                    }
            )
            sm.create_index(database, 'Queues', 'application',
                self.UTF8_TYPE, index_type=self.KEYS_INDEX)
            sm.create_index(database, 'Queues', 'type',
                self.UTF8_TYPE, index_type=self.KEYS_INDEX)

    def close(self):
        self.sm.close()
