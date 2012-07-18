# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys
from contextlib import contextmanager

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
    ret = 0
    with supervisor():
        setup(40)
        ret = os.system('make test-python')
    sys.exit(ret)

if __name__ == '__main__':
    main()
