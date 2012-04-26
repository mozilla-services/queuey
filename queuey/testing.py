# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import time
import xmlrpclib

processes = {}

here = os.path.dirname(__file__)
maindir = os.path.dirname(here)


def ensure_process(name, timeout=10):
    srpc = processes['supervisor']
    if srpc.getProcessInfo(name)['statename'] in ('STOPPED', 'EXITED'):
        print(u'Starting %s!\n' % name)
        srpc.startProcess(name)
    # wait for startup to succeed
    for i in range(1, timeout):
        state = srpc.getProcessInfo(name)['statename']
        if state == 'RUNNING':
            break
        elif state != 'RUNNING':
            print(u'Waiting on %s for %s seconds.' % (name, i * 0.1))
            time.sleep(i * 0.1)
    if srpc.getProcessInfo(name)['statename'] != 'RUNNING':
        vardir = os.path.join(maindir, 'var')
        for name in os.listdir(vardir):
            if name in ('README.txt', 'supervisor.sock'):
                continue
            print("\n\nFILE: %s" % name)
            with open(os.path.join(vardir, name)) as f:
                print(f.read())
        raise RuntimeError('%s not running' % name)


def setup_supervisor():
    processes['supervisor'] = xmlrpclib.ServerProxy(
        'http://127.0.0.1:4999').supervisor


def setup(timeout=10):
    """Shared one-time test setup, called from tests/__init__.py"""
    setup_supervisor()
    ensure_process('cassandra', timeout)
