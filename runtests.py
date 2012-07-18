# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys
import time
from contextlib import contextmanager

import pycassa

from queuey.storage.cassandra import parse_hosts
from queuey.testing import setup


@contextmanager
def supervisor():
    started_supervisor = False
    if not os.path.exists(os.path.join('var', 'supervisor.sock')):
        started_supervisor = True
        os.system('bin/supervisord')
    try:
        yield
    finally:
        if started_supervisor:
            os.system('bin/supervisorctl shutdown')


def main():
    ret = 1
    host = os.environ.get('TEST_CASSANDRA_HOST', '127.0.0.1')
    hosts = parse_hosts(host)
    with supervisor():
        setup(40)
        while 1:
            try:
                pycassa.ConnectionPool(
                    keyspace='MessageStore', server_list=hosts)
                break
            except pycassa.InvalidRequestException:
                # successful connection but missing schema
                break
            except pycassa.AllServersUnavailable:
                time.sleep(0.2)
                print(u'Waiting on connection pool for 0.2 seconds.')
        ret = os.system('make test-python')
    sys.exit(ret)

if __name__ == '__main__':
    main()
