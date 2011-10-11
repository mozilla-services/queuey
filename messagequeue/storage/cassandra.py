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

from messagequeue.exceptions import ApplicationExists
from messagequeue.exceptions import ApplicationNotRegistered
from messagequeue.exceptions import QueueAlreadyExists
from messagequeue.storage import MessageQueueBackend
from messagequeue.storage import MetadataBackend

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
                 host='localhost'):
        """Create a Cassandra backend for the Message Queue

        :param host: Hostname, accepts either an IP, hostname, hostname:port,
                     or a comma seperated list of 'hostname:port'

        """
        hosts = parse_hosts(host)
        self.pool = pool = pycassa.connect(database, hosts)
        self.store_fam = pycassa.ColumnFamily(pool, 'Stores')

    def retrieve(self, queue_name, limit=None, timestamp=None,
                 order="ascending"):
        """Retrieve a message off the queue"""
        kwargs = {}
        if order == 'descending':
            kwargs['column_reversed'] = True

        if limit:
            kwargs['column_count'] = limit

        if timestamp:
            kwargs['column_start'] = timestamp

        try:
            results = self.store_fam.get(queue_name, **kwargs)
        except pycassa.NotFoundException as exc:
            return []
        results = [(uuid.UUID(bytes=x), y) for x,y in results.items()]
        return results

    def push(self, queue_name, message, ttl=60*60*24*3):
        """Push a message onto the queue"""
        now = uuid.uuid1().bytes
        self.store_fam.insert(queue_name, {now: message}, ttl=ttl)

    def exists(self, queue_name):
        """Return whether the queue exists or not"""
        try:
            return bool(self.store_fam.get(queue_name, column_count=1))
        except pycassa.NotFoundException as exc:
            return False


class CassandraMetadta(object):
    implements(MetadataBackend)

    def __init__(self, username=None, password=None, database='MessageStore',
                 host='localhost'):
        """Create a Cassandra backend for the Message Queue

        :param host: Hostname, accepts either an IP, hostname, hostname:port,
                     or a comma seperated list of 'hostname:port'

        """
        hosts = parse_hosts(host)
        self.row_key = '__APPLICATIONS__'
        self.pool = pool = pycassa.connect(database, hosts)
        self.app_fam = pycassa.ColumnFamily(pool, 'Applications')

    def register_application(self, application_name):
        """Register the application
        
        Saves the time the application was registered as well as
        registering it.
        
        """
        now = str(time.time())
        try:
            results = self.app_fam.get(self.row_key,
                                       columns=[application_name],
                                       column_count=1)
            if len(results) > 0:
                raise ApplicationExists("An application with this name "
                                        "is already registered: %s" % 
                                        application_name)
        except pycassa.NotFoundException as exc:
            pass
        self.app_fam.insert(self.row_key, {application_name: now})

    def create_queue(self, application_name, queue_name):
        """Create a queue"""
        # Determine if its registered already
        try:
            results = self.app_fam.get(self.row_key,
                                       columns=[application_name],
                                       column_count=1)
        except pycassa.NotFoundException as exc:
            raise ApplicationNotRegistered("%s is not registered" %
                                           application_name)
        
        results = self.app_fam.get(application_name, columns=[queue_name])
        if len(results) > 0:
            # Already registered, and queue already exists
            raise QueueAlreadyExists("%s already exists" % queue_name)                                           
        self.app_fam.insert(application_name, {application_name: now})
