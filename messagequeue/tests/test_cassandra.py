import unittest
import uuid
import os

class TestCassandraStore(unittest.TestCase):
    def _makeOne(self):
        from messagequeue.storage.cassandra import CassandraQueueBackend
        host = os.environ.get('TEST_CASSANDRA_HOST', 'localhost')
        return CassandraQueueBackend(host)
    
    def test_parsehosts(self):
        from messagequeue.storage.cassandra import parse_hosts
        hosts = parse_hosts('localhost')
        self.assertEqual(hosts, ['localhost:9160'])
        
        hosts = parse_hosts('192.168.2.1,192.168.2.3:9180 , 192.168.2.19')
        self.assertEqual(hosts, 
            ['192.168.2.1:9160','192.168.2.3:9180','192.168.2.19:9160'])

    def test_noqueue(self):
        backend = self._makeOne()
        queue_name = uuid.uuid4().hex
        existing = backend.retrieve(queue_name)
        self.assertEqual([], existing)
    
    def test_onemessage(self):
        backend = self._makeOne()
        payload = 'a rather boring payload'
        queue_name = uuid.uuid4().hex
        backend.push(queue_name, payload)
        existing = backend.retrieve(queue_name)
        self.assertEqual(existing[0][1], payload)

    def test_message_ordering(self):
        backend = self._makeOne()
        payload = 'a rather boring payload'
        another = 'another payload'
        queue_name = uuid.uuid4().hex
        backend.push(queue_name, payload)
        backend.push(queue_name, another)
        existing = backend.retrieve(queue_name)
        self.assertEqual(2, len(existing))
        self.assertEqual(existing[0][1], payload)
        
        existing = backend.retrieve(queue_name, order='descending')
        self.assertEqual(existing[0][1], another)

    def test_noqueue(self):
        backend = self._makeOne()
        payload = 'a rather boring payload'
        queue_name = uuid.uuid4().hex
        backend.push(queue_name, payload)
        
        self.assertEqual(False, backend.exists(uuid.uuid4().hex))
        self.assertEqual(True, backend.exists(queue_name))
