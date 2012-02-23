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

    def _get_queue_info(self, app, queue_name, include_count=False):
        resp = app.get('/v1/queuey',
                       {'details': 'true',
                        'offset': queue_name,
                        'include_count': include_count,
                        'limit': 1}, headers=auth_header)
        return json.loads(resp.body)['queues'][0]

    def _make_app_queue(self, params=None):
        params = params or {}
        app = self.makeOne()
        resp = app.post('/v1/queuey', params, headers=auth_header)
        result = json.loads(resp.body)
        queue_name = str(result['queue_name'])
        return app, queue_name

    def test_app(self):
        app = self.makeOne()
        resp = app.post('/v1/queuey', status=403)
        assert "Access was denied" in resp.body

        # Must have a valid queue name
        app.get('/v1/fredrick', status=404)

    def test_queue_list(self):
        app = self.makeOne()
        resp = app.get('/v1/queuey', headers=auth_header)
        result = json.loads(resp.body)
        eq_('ok', result['status'])

    def test_queue_and_get_since_ts(self):
        app, queue_name = self._make_app_queue()

        # Post a message
        resp = app.post('/v1/queuey/' + queue_name,
                        'Hello there!', headers=auth_header)
        resp = app.post('/v1/queuey/' + queue_name,
                        'Hello there 2!', headers=auth_header)
        result = json.loads(resp.body)
        resp = app.post('/v1/queuey/' + queue_name,
                        'Hello there! 3', headers=auth_header)
        msg_ts = result['messages'][0]['timestamp']

        # Fetch the messages
        resp = app.get('/v1/queuey/' + queue_name, {'since': msg_ts},
                       headers=auth_header)
        result = json.loads(resp.body)
        eq_(2, len(result['messages']))
        msg = result['messages'][0]
        eq_('Hello there 2!', msg['body'])
        eq_(1, msg['partition'])

    def test_queue_update(self):
        app, queue_name = self._make_app_queue({'principles': 'app:queuey'})

        # Get the queue info
        queue = self._get_queue_info(app, queue_name, include_count=True)
        eq_(0, queue['count'])
        assert 'app:queuey' in queue['principles']
        eq_(1, queue['partitions'])

        # Update the partitions
        resp = app.put('/v1/queuey/%s' % queue_name, {'partitions': 2},
                       headers=auth_header)
        result = json.loads(resp.body)
        assert 'app:queuey' in result['principles']
        eq_(2, result['partitions'])

        # Add principles
        resp = app.put('/v1/queuey/%s' % queue_name,
                       {'principles': 'app:queuey,app:notifications'},
                       headers=auth_header)
        result = json.loads(resp.body)
        assert 'app:queuey' in result['principles']
        assert 'app:notifications' in result['principles']

        # Bad partition update
        resp = app.put('/v1/queuey/%s' % queue_name, {'partitions': 1},
                       headers=auth_header, status=400)
        result = json.loads(resp.body)
        eq_('error', result['status'])

    def test_public_queue(self):
        app, queue_name = self._make_app_queue({'type': 'public'})

        # Get the queue info
        queue = self._get_queue_info(app, queue_name)
        eq_('public', queue['type'])
        result = app.get('/v1/queuey/%s' % queue_name)
        result = json.loads(result.body)
        eq_('ok', result['status'])

    def test_make_queue_post_get_batches(self):
        app, queue_name = self._make_app_queue({'partitions': 3})

        # Post several messages
        msgs = {
            'messages': [
                {'body': 'Hello msg 1', 'partition': 2},
                {'body': 'Hello msg 2', 'partition': 2},
                {'body': 'Hello msg 3', 'partition': 1, 'ttl': 3600}
            ]
        }
        msgs = json.dumps(msgs)
        json_header = {'Content-Type': 'application/json'}
        json_header.update(auth_header)
        resp = app.post('/v1/queuey/' + queue_name, msgs, headers=json_header)
        result = json.loads(resp.body)

        # Fetch the messages
        resp = app.get('/v1/queuey/' + queue_name, {'partitions': '1,2,3'},
                       headers=auth_header)
        result = json.loads(resp.body)
        eq_(3, len(result['messages']))
        msg = result['messages'][0]
        eq_('Hello msg 3', msg['body'])
        eq_(1, msg['partition'])
        eq_(2, result['messages'][1]['partition'])

        # From a single partition
        resp = app.get('/v1/queuey/' + queue_name, {'partitions': '2'},
               headers=auth_header)
        result = json.loads(resp.body)
        eq_(2, len(result['messages']))
        msg = result['messages'][0]
        eq_('Hello msg 1', msg['body'])

        # Dump a message in a cluster without a partition
        msgs = {
            'messages': [
                {'body': 'Hello msg 1'},
            ]
        }
        msgs = json.dumps(msgs)
        json_header = {'Content-Type': 'application/json'}
        json_header.update(auth_header)
        resp = app.post('/v1/queuey/' + queue_name, msgs, headers=json_header)
        result = json.loads(resp.body)
        eq_('ok', result['status'])

    def test_delete_queue(self):
        app, queue_name = self._make_app_queue({'partitions': 3})

        queue = self._get_queue_info(app, queue_name)
        eq_('user', queue['type'])
        eq_(queue_name, queue['queue_name'])
        eq_(3, queue['partitions'])

        resp = app.delete('/v1/queuey/%s' % queue_name,
                          headers=auth_header)
        result = json.loads(resp.body)
        eq_('ok', result['status'])

        resp = app.get('/v1/queuey/%s' % queue_name, headers=auth_header,
                       status=404)
        result = json.loads(resp.body)
        eq_('error', result['status'])

    def test_delete_queue_messages(self):
        app, queue_name = self._make_app_queue({'partitions': 3})

        # Post a few messages
        p2 = auth_header.copy()
        p2['X-Partition'] = '2'
        resp = app.post('/v1/queuey/' + queue_name,
                'Hello there!', headers=p2)
        resp2 = app.post('/v1/queuey/' + queue_name,
                'Hello there!', headers=p2)
        msg = json.loads(resp2.body)['messages'][0]
        msg2 = json.loads(resp.body)['messages'][0]
        p2['X-Partition'] = '1'
        resp = app.post('/v1/queuey/' + queue_name,
                'Hello there!', headers=p2)
        msg3 = json.loads(resp.body)['messages'][0]
        resp = app.post('/v1/queuey/' + queue_name,
                'Hello there!', headers=auth_header)

        # Fetch the messages
        resp = app.get('/v1/queuey/' + queue_name, {'partitions': '1,2,3'},
                       headers=auth_header)
        result = json.loads(resp.body)
        eq_(4, len(result['messages']))

        # Delete 2 messages
        q = urllib.quote_plus('2:%s,2:%s' % (msg['key'], msg2['key']))
        resp = app.delete('/v1/queuey/%s/%s' % (queue_name, q), headers=auth_header)

        resp = app.get('/v1/queuey/' + queue_name, {'partitions': '1,2,3'},
                       headers=auth_header)
        result = json.loads(resp.body)
        eq_(2, len(result['messages']))

        # Delete 1 message
        q = urllib.quote_plus('%s' % msg3['key'])
        resp = app.delete('/v1/queuey/%s/%s' % (queue_name, q), headers=auth_header)

        resp = app.get('/v1/queuey/' + queue_name, {'partitions': '1,2,3'},
                       headers=auth_header)
        result = json.loads(resp.body)
        eq_(1, len(result['messages']))

    def test_bad_ttl(self):
        app, queue_name = self._make_app_queue()
        h = auth_header.copy()
        h['X-TTL'] = 'fred'
        resp = app.post('/v1/queuey/' + queue_name,
                'Hello there!', headers=h,
                status=400)
        result = json.loads(resp.body)
        eq_('error', result['status'])
        eq_(u'Invalid X-TTL header.', result['error_msg']['InvalidParameter'])

    def test_bad_partition(self):
        app, queue_name = self._make_app_queue()
        h = auth_header.copy()
        h['X-Partition'] = 'fred'
        resp = app.post('/v1/queuey/' + queue_name,
                'Hello there!', headers=h,
                status=400)
        result = json.loads(resp.body)
        eq_('error', result['status'])
        eq_(u'Invalid X-Partition header.', result['error_msg']['InvalidParameter'])

    def test_no_body(self):
        app, queue_name = self._make_app_queue()
        resp = app.post('/v1/queuey/' + queue_name,
                '', headers=auth_header,
                status=400)
        result = json.loads(resp.body)
        eq_('error', result['status'])
        eq_(u'No request body found.', result['error_msg']['InvalidParameter'])

    def test_no_queuename(self):
        app, queue_name = self._make_app_queue()
        resp = app.post('/v1/queuey/' + queue_name + 'blip',
            'Hello there!', headers=auth_header, status=404)
        eq_(404, resp.status_int)

    def test_queuename_too_long(self):
        app, queue_name = self._make_app_queue()
        resp = app.post('/v1/queuey/' + 'blip' * 30,
            {'.body': 'Hello there!'}, headers=auth_header, status=404)
        eq_(404, resp.status_int)

    def test_invalid_partition_type(self):
        app, queue_name = self._make_app_queue()
        resp = app.get('/v1/queuey/' + queue_name, {'partitions': '1,fred'},
                       headers=auth_header, status=400)
        result = json.loads(resp.body)
        eq_('error', result['status'])

    def test_bad_principle_name(self):
        app, queue_name = self._make_app_queue()
        resp = app.post('/v1/queuey', {'principles': 'app:queuey,apple:oranges'},
                        headers=auth_header, status=400)
        eq_(400, resp.status_int)
        resp = app.post('/v1/queuey', {'principles': 'apple:oranges'},
                        headers=auth_header, status=400)
        eq_(400, resp.status_int)

    def test_bad_hex(self):
        app, queue_name = self._make_app_queue()
        q = urllib.quote_plus('2:asdfasdfasdfadsfasdf')
        resp = app.delete('/v1/queuey/%s/%s' % (queue_name, q), headers=auth_header,
                          status=400)
        result = json.loads(resp.body)
        eq_('error', result['status'])

    def test_bad_json(self):
        app, queue_name = self._make_app_queue()
        q = '[this isnt good}'
        h = auth_header.copy()
        h['Content-Type'] = 'application/json'
        resp = app.post('/v1/queuey/%s' % queue_name, q, headers=h, status=400)
        result = json.loads(resp.body)
        eq_('error', result['status'])

    def test_bad_appkey(self):
        app = self.makeOne()
        resp = app.post('/v1/queuey', headers={'Authorization': 'Application OOPS'},
                        status=401)
        result = json.loads(resp.body)

        eq_('error', result['status'])
        eq_('InvalidApplicationKey', result['error_msg'].keys()[0])

    def test_no_path(self):
        app = self.makeOne()
        resp = app.post('/blah', status=404)
        eq_(404, resp.status_int)
