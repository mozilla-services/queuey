.. note::

	This code is not yet stable. If you are interested in working with it,
	please contact the author directly (bbangert@mozilla.com)

======
Queuey
======

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
cd into the directory and run make.

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

In addition, you'll need to start Cassandra (See: Running the Cassandra
 Server)
and create the schema::

    bin/cassandra/bin/cassandra-cli -host localhost --file etc/cassandra/schema.txt

Running Queuey
==============

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
