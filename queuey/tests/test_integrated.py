# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import unittest

from paste.deploy import loadapp
from webtest import TestApp


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
