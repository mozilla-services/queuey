# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import datetime
from datetime import timedelta
import uuid
import time

import pycassa
from zope.interface import implements

from queuey.exceptions import ApplicationExists
from queuey.exceptions import ApplicationNotRegistered
from queuey.exceptions import QueueAlreadyExists
from queuey.exceptions import QueueDoesNotExist
from queuey.storage import MessageQueueBackend
from queuey.storage import MetadataBackend

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
        self.delay = int(base_delay) if base_delay else None
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
        cl = self.cl or self._get_cl(consistency)
        delay = self._get_delay(consistency)

        if isinstance(start_at, str):
            # Assume its a hex
            start_at = uuid.UUID(hex=start_at)

        kwargs = {'read_consistency_level': cl}
        if order == 'descending':
            kwargs['column_reversed'] = True
        elif start_at:
            # Impose our upper bound
            kwargs['column_finish'] = datetime.today() - timedelta(seconds=delay)

        if limit:
            kwargs['column_count'] = limit

        if start_at:
            kwargs['column_start'] = start_at

        queue_names = ['%s:%s' % (application_name, x) for x in queue_names]
        try:
            results = self.message_fam.multiget(keys=queue_names, **kwargs)
        except pycassa.NotFoundException:
            return []

        results = results.items()
        if delay:
            cut_off = time.time() - self.delay
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
                    'queue_name': queue_name.split(':')[1]
                }
                result_list.append(obj)
                msg_hash[msg_id] = obj

        # Get metadata?
        if include_metadata:
            try:
                results = self.meta_fam.multiget(keys=msg_hash.keys())
            except pycassa.NotFoundException:
                results = []
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
            'queue_name': queue_name.split(':')[1]
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
        now = uuid.uuid1()
        queue_name = '%s:%s' % (application_name, queue_name)
        if metadata:
            batch = pycassa.batch.Mutator(self.pool)
            batch.insert(self.message_fam, key=queue_name,
                         columns={now: message}, ttl=ttl)
            batch.insert(self.meta_fam, key=now, columns=metadata, ttl=ttl)
            batch.send()
        else:
            self.message_fam.insert(key=queue_name, columns={now: message}, ttl=ttl)
        timestamp = (now.time - 0x01b21dd213814000L) / 1e7
        return now.hex, timestamp

    def exists(self, queue_name):
        """Return whether the queue exists or not"""
        try:
            return bool(self.store_fam.get(key=queue_name, column_count=1))
        except pycassa.NotFoundException:
            return False

    def truncate(self, queue_name):
        """Remove all contents of the queue"""
        self.store_fam.remove(key=queue_name)
        return True

    def delete(self, queue_name, *keys):
        """Delete a batch of keys"""
        self.store_fam.remove(key=queue_name,
                              columns=[uuid.UUID(hex=x) for x in keys])
        return True

    def count(self, queue_name):
        """Return a count of the items in this queue"""
        return self.store_fam.get_count(key=queue_name)


class CassandraMetadata(object):
    implements(MetadataBackend)

    def __init__(self, username=None, password=None, database='MessageStore',
                 host='localhost', read_consistency=None,
                 write_consistency=None):
        """Create a Cassandra backend for the Message Queue

        :param host: Hostname, accepts either an IP, hostname, hostname:port,
                     or a comma seperated list of 'hostname:port'

        """
        hosts = parse_hosts(host)
        self.row_key = '__APPLICATIONS__'
        self.pool = pool = pycassa.ConnectionPool(
            keyspace=database,
            server_list=hosts,
        )
        self.app_fam = af = pycassa.ColumnFamily(pool, 'Applications')
        af.read_consistency_level = CL.get(read_consistency) or CL['one']
        af.write_consistency_level = CL.get(write_consistency) or CL['one']

    def _verify_app_exists(self, application_name):
        try:
            self.app_fam.get(key=self.row_key, columns=[application_name],
                             column_count=1)
        except pycassa.NotFoundException:
            raise ApplicationNotRegistered("%s is not registered" %
                                           application_name)

    def register_application(self, application_name):
        """Register the application

        Saves the time the application was registered as well as
        registering it.

        """
        try:
            results = self.app_fam.get(key=self.row_key,
                                       columns=[application_name],
                                       column_count=1)
            if len(results) > 0:
                raise ApplicationExists("An application with this name "
                                        "is already registered: %s" %
                                        application_name)
        except pycassa.NotFoundException:
            pass
        now = str(time.time())
        self.app_fam.insert(key=self.row_key, columns={application_name: now})

    def register_queue(self, application_name, queue_name, partitions):
        """Register a queue"""
        # Determine if its registered already
        self._verify_app_exists(application_name)
        try:
            results = self.app_fam.get(key=application_name,
                                       columns=[queue_name])
            if len(results) > 0:
                # Already registered, and queue already exists
                raise QueueAlreadyExists("%s already exists" % queue_name)
        except pycassa.NotFoundException:
            pass
        now = str(time.time())
        self.app_fam.insert(key=application_name, columns={queue_name: now})
        self.app_fam.insert(key=queue_name + '_meta',
                            columns={'partitions': str(partitions),
                                     'created': now})

    def remove_queue(self, application_name, queue_name):
        """Remove a queue"""
        self._verify_app_exists(application_name)
        try:
            self.app_fam.get(key=application_name, columns=[queue_name])
        except pycassa.NotFoundException:
            raise QueueDoesNotExist("%s is not registered" % queue_name)
        self.app_fam.remove(key=application_name, columns=[queue_name])

    def queue_information(self, application_name, queue_name):
        """Return information on a registered queue"""
        # Determine if its registered already
        self._verify_app_exists(application_name)
        try:
            results = self.app_fam.get(key=queue_name + '_meta')
            results['partitions'] = int(results['partitions'])
            return results
        except pycassa.NotFoundException:
            raise QueueDoesNotExist("%s is not registered" % queue_name)
