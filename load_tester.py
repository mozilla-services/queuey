import os
import base64
import time
from optparse import OptionParser

from gevent import monkey
from gevent.pool import Pool
monkey.patch_all(thread=False)

import requests

auth = {}
qurl = []


def files(filedir):
    files = os.listdir(filedir)
    file_map = []
    for filename in files:
        if filename.endswith('dump'):
            continue
        with open(os.path.join(filedir, filename)) as f:
            data = f.read()

        dumpname = filename.rstrip('.json') + '.dump'
        with open(os.path.join(filedir, dumpname)) as f:
            data += f.read()
        file_map.append(base64.b64encode(data.encode('zlib')))
    return file_map


def send_msg(msg):
    requests.post(qurl[0], msg, headers=auth, config={'safe_mode': True})


if __name__ == '__main__':
    usage = "usage: %prog url_to_queue application_key"
    parser = OptionParser(usage=usage)
    parser.add_option("--concurrency", dest="concurrency", type="int",
                      default=10, help="Concurrent requests")
    parser.add_option("--messages", dest="messages", type="int",
                      default=10000, help="Amount of messages to send")
    parser.add_option("--message_size", dest="message_size", type="int",
                      default=140, help="Message size (in bytes)")
    (options, args) = parser.parse_args()

    # Setup globals
    auth['Authorization'] = 'Application %s' % args[1]
    qurl.append(args[0])

    print "Constructing %s messages of size %s..." % (options.messages,
                                                      options.message_size)
    messages = [base64.b64encode(os.urandom(options.message_size)) for x in
                range(options.messages)]

    p = Pool(options.concurrency)
    start = time.time()
    p.map(send_msg, messages)
    total = time.time() - start
    print "Completed in %s seconds" % total
    print "Requests per seconds: %s" % (len(messages) / total)
