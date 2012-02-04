======
Queuey
======

    Wat? Another message queue?

Given the proliferation of message queue's, one could be inclined to believe
that inventing more is not the answer. Using an existing solution was
attempted multiple times with most every existing message queue product.

The others failed (for our use-cases).

Queuey is meant to handle some unqiue conditions that most other message
queue solutions either don't handle, or handle very poorly. Many of them for
example are written for queues or pub/sub situations that don't require
possibly longer term (multiple days) storage of not just many messages but
huge quantities of queues.

Queuey Assumptions and Features:

- Messages may persist for upwards of 3 days
- Range scans with timestamps to rewind and re-read messages in a queue
- Millions of queues may be created
- Message delivery characteristics need to be tweakable based on the
  specific cost-benefit for a Queuey deployment
- RESTful HTTP API for easy access by a variety of clients, including AJAX
- Authentication system to support multiple 'Application' access to Queuey
  with optional Browser-ID client authentication

Queuey can be configured with varying message guarantees, such as:

- Deliver once, and exactly once
- Deliver at least once (and under rare conditions, maybe more)
- Deliver usually at least once

Changing the storage back-end and deployment strategies directly affects
the message guarantee's.

Reference Material
==================

Reference material includes documentation for every `queuey` API.

.. toctree::
   :maxdepth: 1

   api
   Changelog <changelog>

Source Code
===========

All source code is available on `github under queuey <https://github.com/mozilla-services/queuey>`_.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`glossary`

License
=======

``queuey`` is offered under the MPL 2.0 license.

Authors
=======

``queuey`` is made available by the `Mozilla Foundation`.
