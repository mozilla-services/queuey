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
- A single deployment may support multiple Applications with varying
  message delivery characteristics, and authentication restricted queue
  access

Queuey can be configured with varying message guarantees, such as:

- Deliver once, and exactly once
- Deliver at least once (and under rare conditions, maybe more)
- Deliver no more than once (and under rare conditions, possibly not deliver)

Changing the storage back-end and deployment strategies directly affects
the message guarantee's. This enables the Queuey deployment to meet different
requirements and performance thresholds.

For more background on queuey, see `the Mozilla wiki section on queuey <https://wiki.mozilla.org/Services/Sagrada/Queuey>`_.

Requirements
============

Make sure you have the following software already
installed before proceeding:

- Java 1.6
- Ant
- Make
- Python 2.6 (with virtualenv installed)


Installation
============

After downloading the repository for the first time, 
cd into the directory and run::

    $ make

This will do the following:

- Create a virtual python environment 
- Install required python packages into this environment

Cassandra
---------

To run queuey, you need a storage back-end for the queues. The default
storage back-end is Cassandra. This installation has been automated in
queuey's Makefile, to install Cassandra in the same directory as
queuey::

	make cassandra

Which will fetch the cassandra server and set up the configuration.

The default (Cassandra) stores its data and files inside the local cassandra
directory so as not to interfere with any existing Cassandra installations on
the system.

In addition, you'll need to start Cassandra (See: Running the Cassandra Server)
and create the schema::

    bin/cassandra/bin/cassandra-cli -host localhost --file etc/cassandra/schema.txt

Running
=======

Running the Cassandra Server:
-----------------------------
The message store (used by the server to route messages)
and the HTTP server must be started separately. The steps
are (starting from the root project directory)

::

	./bin/cassandra/bin/cassandra -p cassandra.pid

To shut it down at any point in the future::

	kill -2 `cat cassandra.pid`

Running the Queuey Application:
-------------------------------

::

	bin/pserve etc/queuey-dev.ini
