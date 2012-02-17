# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import unittest
import json

from paste.deploy import loadapp
from webtest import TestApp
from nose.tools import eq_

auth_header = {'Authorization': 'Application f25bfb8fe200475c8a0532a9cbe7651e'}


class TestQueueyApp(unittest.TestCase):
    def makeOne(self):
        ini_file = os.path.abspath(
            os.path.join(os.path.dirname(__file__), 'test.ini'))
        application = loadapp('config:%s' % ini_file)
        return application

    def test_app(self):
        app = TestApp(self.makeOne())
        resp = app.post('/queuey', status=403)
        assert "Access was denied" in resp.body

    def test_queue_list(self):
        app = TestApp(self.makeOne())
        resp = app.get('/queuey', headers=auth_header)
        result = json.loads(resp.body)
        eq_('ok', result['status'])
