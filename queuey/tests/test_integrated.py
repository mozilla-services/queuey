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

    def test_make_queue_post_get_messages(self):
        app = TestApp(self.makeOne())
        resp = app.post('/queuey', headers=auth_header)
        result = json.loads(resp.body)
        queue_name = str(result['queue_name'])

        # Post a message
        resp = app.post('/queuey/' + queue_name,
                        {'body': 'Hello there!'}, headers=auth_header)
        result = json.loads(resp.body)

        # Fetch the messages
        resp = app.get('/queuey/' + queue_name, headers=auth_header)
        result = json.loads(resp.body)
        eq_(1, len(result['messages']))
        msg = result['messages'][0]
        eq_('Hello there!', msg['body'])
        eq_(1, msg['partition'])

    def test_queue_permissions(self):
        app = TestApp(self.makeOne())
        resp = app.post('/queuey', {'permissions': 'app:queuey'},
                        headers=auth_header)
        result = json.loads(resp.body)
        queue_name = str(result['queue_name'])

        # Get the queue info
        resp = app.get('/queuey/%s/info' % queue_name, headers=auth_header)
        result = json.loads(resp.body)
        eq_(0, result['count'])
        assert 'app:queuey' in result['permissions']

    def test_make_queue_post_get_batches(self):
        app = TestApp(self.makeOne())
        resp = app.post('/queuey', headers=auth_header)
        result = json.loads(resp.body)
        queue_name = str(result['queue_name'])

        # Post several messages
        resp = app.post('/queuey/' + queue_name,
                        {'body': 'Hello there!'}, headers=auth_header)
        result = json.loads(resp.body)

        # Fetch the messages
        resp = app.get('/queuey/' + queue_name, headers=auth_header)
        result = json.loads(resp.body)
        eq_(1, len(result['messages']))
        msg = result['messages'][0]
        eq_('Hello there!', msg['body'])
        eq_(1, msg['partition'])
