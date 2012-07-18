# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys
import time
from contextlib import contextmanager

from thrift.transport.TTransport import TTransportException

from queuey.testing import setup
from queuey.storage.cassandra import parse_hosts
from queuey.storage.cassandra import Schema


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
    ret = 0
    # Check that keyspaces necessary are there, create otherwise
    host = os.environ.get('TEST_CASSANDRA_HOST', '127.0.0.1')
    hosts = parse_hosts(host)
    with supervisor():
        setup(40)
        while 1:
            try:
                Schema(hosts[0]).install()
                time.sleep(0.2)
                break
            except TTransportException:
                print(u'Waiting on system manager for 0.1 seconds.')
                time.sleep(0.1)
        ret = os.system('make test-python')
    sys.exit(ret)

if __name__ == '__main__':
    main()
