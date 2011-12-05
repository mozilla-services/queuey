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

CL = {
    'any': pycassa.ConsistencyLevel.ANY,
    'one': pycassa.ConsistencyLevel.ONE,
    'local_quorum': pycassa.ConsistencyLevel.LOCAL_QUORUM,
}


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
                 host='localhost', delay=None, read_consistency=None,
                 write_consistency=None):
        """Create a Cassandra backend for the Message Queue

        :param host: Hostname, accepts either an IP, hostname, hostname:port,
                     or a comma seperated list of 'hostname:port'

        """
        hosts = parse_hosts(host)
        self.pool = pool = pycassa.connect(database, hosts)
        self.store_fam = sf = pycassa.ColumnFamily(pool, 'Stores')
        sf.read_consistency_level = CL.get(read_consistency) or CL['one']
        sf.write_consistency_level = CL.get(write_consistency) or CL['one']
        self.delay = int(delay) if delay else None

    def retrieve(self, queue_name, limit=None, timestamp=None,
                 order="descending"):
        """Retrieve a message off the queue"""
        kwargs = {}
        if order == 'descending':
            kwargs['column_reversed'] = True

        if limit:
            kwargs['column_count'] = limit

        if timestamp:
            kwargs['column_start'] = timestamp

        try:
            results = self.store_fam.get(key=queue_name, **kwargs)
        except pycassa.NotFoundException:
            return []
        results = results.items()
        return results

    def push(self, queue_name, message, ttl=60 * 60 * 24 * 3):
        """Push a message onto the queue"""
        now = uuid.uuid1()
        self.store_fam.insert(key=queue_name, columns={now: message}, ttl=ttl)

    def exists(self, queue_name):
        """Return whether the queue exists or not"""
        try:
            return bool(self.store_fam.get(key=queue_name, column_count=1))
        except pycassa.NotFoundException:
            return False

    def truncate(self, queue_name):
        """Remove all contents of the queue"""
        try:
            self.store_fam.remove(key=queue_name)
        except pycassa.NotFoundException:
            pass

    def count(self, queue_name):
        """Return a count of the items in this queue"""
        try:
            return self.store_fam.get_count(key=queue_name)
        except pycassa.NotFoundException:
            raise QueueDoesNotExist


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
        self.pool = pool = pycassa.connect(database, hosts)
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

    def register_queue(self, application_name, queue_name):
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

    def remove_queue(self, application_name, queue_name):
        """Remove a queue"""
        self._verify_app_exists(key=application_name)
        try:
            self.app_fam.remove(key=application_name, columns=[queue_name])
        except pycassa.NotFoundException:
            raise QueueDoesNotExist("%s is not registered" % queue_name)

    def queue_information(self, application_name, queue_name):
        """Return information on a registered queue"""
