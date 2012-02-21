# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
import os
import unittest
import urllib
import json

from paste.deploy import loadapp
from webtest import TestApp
from nose.tools import eq_

auth_header = {'Authorization': 'Application f25bfb8fe200475c8a0532a9cbe7651e'}


class TestQueueyApp(unittest.TestCase):
    def makeOne(self):
        try:
            return self.application
        except AttributeError:
            ini_file = os.path.abspath(
                os.path.join(os.path.dirname(__file__), 'test.ini'))
            self.application = application = TestApp(loadapp('config:%s' % ini_file))
            return application

    def test_app(self):
        app = self.makeOne()
        resp = app.post('/queuey', status=403)
        assert "Access was denied" in resp.body

    def test_queue_list(self):
        app = self.makeOne()
        resp = app.get('/queuey', headers=auth_header)
        result = json.loads(resp.body)
        eq_('ok', result['status'])

    def test_make_queue_post_get_messages(self):
        app = self.makeOne()
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

    def test_queue_and_get_since_ts(self):
        app = self.makeOne()
        resp = app.post('/queuey', headers=auth_header)
        result = json.loads(resp.body)
        queue_name = str(result['queue_name'])

        # Post a message
        resp = app.post('/queuey/' + queue_name,
                        {'body': 'Hello there!'}, headers=auth_header)
        resp = app.post('/queuey/' + queue_name,
                        {'body': 'Hello there 2!'}, headers=auth_header)
        result = json.loads(resp.body)
        resp = app.post('/queuey/' + queue_name,
                        {'body': 'Hello there! 3'}, headers=auth_header)
        msg_ts = result['messages'][0]['timestamp']

        # Fetch the messages
        resp = app.get('/queuey/' + queue_name, {'since': msg_ts},
                       headers=auth_header)
        result = json.loads(resp.body)
        eq_(2, len(result['messages']))
        msg = result['messages'][0]
        eq_('Hello there 2!', msg['body'])
        eq_(1, msg['partition'])

    def test_queue_principles(self):
        app = self.makeOne()
        resp = app.post('/queuey', {'principles': 'app:queuey'},
                        headers=auth_header)
        result = json.loads(resp.body)
        queue_name = str(result['queue_name'])

        # Get the queue info
        resp = app.get('/queuey/%s/info' % queue_name, headers=auth_header)
        result = json.loads(resp.body)
        eq_(0, result['count'])
        assert 'app:queuey' in result['principles']

        # Test multiplate queue principles
        resp = app.post('/queuey', {'principles': 'app:queuey,app:george'},
                headers=auth_header)
        result = json.loads(resp.body)
        queue_name = str(result['queue_name'])

        # Get the queue info
        resp = app.get('/queuey/%s/info' % queue_name, headers=auth_header)
        result = json.loads(resp.body)
        eq_(0, result['count'])
        assert 'app:queuey' in result['principles']
        assert 'app:george' in result['principles']

    def test_queue_update(self):
        app = self.makeOne()
        resp = app.post('/queuey', {'principles': 'app:queuey'},
                        headers=auth_header)
        result = json.loads(resp.body)
        queue_name = str(result['queue_name'])

        # Get the queue info
        resp = app.get('/queuey/%s/info' % queue_name, headers=auth_header)
        result = json.loads(resp.body)
        eq_(0, result['count'])
        assert 'app:queuey' in result['principles']
        eq_(1, result['partitions'])

        # Update the partitions
        resp = app.put('/queuey/%s' % queue_name, {'partitions': 2},
                       headers=auth_header)
        result = json.loads(resp.body)
        eq_(0, result['count'])
        assert 'app:queuey' in result['principles']
        eq_(2, result['partitions'])

        # Add principles
        resp = app.put('/queuey/%s' % queue_name,
                       {'principles': 'app:queuey,app:notifications'},
                       headers=auth_header)
        result = json.loads(resp.body)
        eq_(0, result['count'])
        assert 'app:queuey' in result['principles']
        assert 'app:notifications' in result['principles']

        # Bad partition update
        resp = app.put('/queuey/%s' % queue_name, {'partitions': 1},
                       headers=auth_header, status=400)
        result = json.loads(resp.body)
        eq_('error', result['status'])

    def test_public_queue(self):
        app = self.makeOne()
        resp = app.post('/queuey', {'type': 'public'},
                        headers=auth_header)
        result = json.loads(resp.body)
        queue_name = str(result['queue_name'])

        # Get the queue info
        resp = app.get('/queuey/%s/info' % queue_name, headers=auth_header)
        result = json.loads(resp.body)
        eq_('public', result['type'])

    def test_make_queue_post_get_batches(self):
        app = self.makeOne()
        resp = app.post('/queuey', {'partitions': 3}, headers=auth_header)
        result = json.loads(resp.body)
        queue_name = str(result['queue_name'])

        # Post several messages
        msgs = {
            'message.0.body': 'Hello msg 1',
            'message.0.partition': '2',
            'message.1.body': 'Hello msg 2',
            'message.1.partition': '2',
            'message.2.body': 'Hello msg 3',
            'message.2.ttl': '3600',
            'message.2.partition': '1'
        }
        resp = app.post('/queuey/' + queue_name, msgs, headers=auth_header)
        result = json.loads(resp.body)

        # Fetch the messages
        resp = app.get('/queuey/' + queue_name, {'partitions': '1,2,3'},
                       headers=auth_header)
        result = json.loads(resp.body)
        eq_(3, len(result['messages']))
        msg = result['messages'][0]
        eq_('Hello msg 3', msg['body'])
        eq_(1, msg['partition'])
        eq_(2, result['messages'][1]['partition'])

        # From a single partition
        resp = app.get('/queuey/' + queue_name, {'partitions': '2'},
               headers=auth_header)
        result = json.loads(resp.body)
        eq_(2, len(result['messages']))
        msg = result['messages'][0]
        eq_('Hello msg 1', msg['body'])

    def test_delete_queue(self):
        app = self.makeOne()
        resp = app.post('/queuey', {'partitions': 3}, headers=auth_header)
        result = json.loads(resp.body)
        queue_name = str(result['queue_name'])

        resp = app.get('/queuey/%s/info' % queue_name, headers=auth_header)
        result = json.loads(resp.body)
        eq_('user', result['type'])

        resp = app.delete('/queuey/%s?delete_registration=true' % queue_name,
                          headers=auth_header)
        result = json.loads(resp.body)
        eq_('ok', result['status'])

        resp = app.get('/queuey/%s/info' % queue_name, headers=auth_header,
                       status=404)
        result = json.loads(resp.body)
        eq_('error', result['status'])

    def test_delete_queue_messages(self):
        app = self.makeOne()
        resp = app.post('/queuey', {'partitions': 3}, headers=auth_header)
        result = json.loads(resp.body)
        queue_name = str(result['queue_name'])

        # Post a few messages
        resp = app.post('/queuey/' + queue_name,
                {'body': 'Hello there!', 'partition': 2}, headers=auth_header)
        resp2 = app.post('/queuey/' + queue_name,
                {'body': 'Hello there!', 'partition': 2}, headers=auth_header)
        msg = json.loads(resp2.body)['messages'][0]
        msg2 = json.loads(resp.body)['messages'][0]
        resp = app.post('/queuey/' + queue_name,
                {'body': 'Hello there!', 'partition': 1}, headers=auth_header)
        resp = app.post('/queuey/' + queue_name,
                {'body': 'Hello there!', 'partition': 3}, headers=auth_header)

        # Fetch the messages
        resp = app.get('/queuey/' + queue_name, {'partitions': '1,2,3'},
                       headers=auth_header)
        result = json.loads(resp.body)
        eq_(4, len(result['messages']))

        # Delete 2 messages
        q = urllib.urlencode(
            {'messages': msg['key'] + ',' + msg2['key'],
             'partitions': '2'})
        resp = app.delete('/queuey/%s?%s' % (queue_name, q), headers=auth_header)

        resp = app.get('/queuey/' + queue_name, {'partitions': '1,2,3'},
                       headers=auth_header)
        result = json.loads(resp.body)
        eq_(2, len(result['messages']))

    def test_invalid_inputs(self):
        app = self.makeOne()
        resp = app.post('/queuey', {'partitions': 3}, headers=auth_header)
        result = json.loads(resp.body)
        queue_name = str(result['queue_name'])

        # Test a bad message
        resp = app.post('/queuey/' + queue_name,
                {'body': 'Hello there!', 'ttl': 'fred'}, headers=auth_header,
                status=400)
        result = json.loads(resp.body)

        eq_('error', result['status'])
        eq_('"fred" is not a number', result['error_msg']['ttl'])

        # Test a bad unflatten
        resp = app.post('/queuey/' + queue_name,
            {'.body': 'Hello there!'}, headers=auth_header, status=400)
        result = json.loads(resp.body)
        eq_('error', result['status'])

        # Test no queue name
        resp = app.post('/queuey/' + queue_name + 'blip',
            {'.body': 'Hello there!'}, headers=auth_header, status=404)
        eq_(404, resp.status_int)

        # Test queue name too long
        resp = app.post('/queuey/' + 'blip' * 30,
            {'.body': 'Hello there!'}, headers=auth_header, status=404)
        eq_(404, resp.status_int)

        # Test invalid partition type
        resp = app.get('/queuey/' + queue_name, {'partitions': '1,fred'},
                       headers=auth_header, status=400)
        result = json.loads(resp.body)
        eq_('error', result['status'])

        # Test bad principle name
        resp = app.post('/queuey', {'principles': 'app:queuey,apple:oranges'},
                        headers=auth_header, status=400)
        eq_(400, resp.status_int)
        resp = app.post('/queuey', {'principles': 'apple:oranges'},
                        headers=auth_header, status=400)
        eq_(400, resp.status_int)

        # Test bad hex
        q = urllib.urlencode(
            {'messages': 'asdfasdfasdfadsfasdf',
             'partitions': '2'})
        resp = app.delete('/queuey/%s?%s' % (queue_name, q), headers=auth_header,
                          status=400)
        result = json.loads(resp.body)
        eq_('error', result['status'])

        # Test 2 bad args
        q = urllib.urlencode(
            {'messages': '227208545c1611e19f857cc3a171be4b',
             'partitions': '1,2'})
        resp = app.delete('/queuey/%s?%s' % (queue_name, q), headers=auth_header,
                          status=400)
        result = json.loads(resp.body)
        eq_('error', result['status'])

    def test_bad_appkey(self):
        app = self.makeOne()
        resp = app.post('/queuey', headers={'Authorization': 'Application OOPS'},
                        status=401)
        result = json.loads(resp.body)

        eq_('error', result['status'])
        eq_('InvalidApplicationKey', result['error_msg'].keys()[0])

    def test_no_path(self):
        app = self.makeOne()
        resp = app.post('/blah', status=404)
        eq_(404, resp.status_int)
