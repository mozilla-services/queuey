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

You will then need to setup and install Cassandra and Zookeeper. To assist
with this you can run::

	make cassandra

Which will fetch the cassandra server and set up the configuration.

The default (Cassandra) stores its data and files inside the local cassandra
directory so as not to interfere with any existing Cassandra installations on
the system.

In addition, you'll need to start Cassandra (See: Running the Cassandra Server)
and create the schema:
* bin/cassandra/bin/cassandra-cli -host localhost --file etc/cassandra/schema.txt

Zookeeper
---------

To install Zookeeper, run::

	make zookeeper

This will fetch ZooKeeper, compile the C extension and Python extension. To
use it, you will need to install the C extension on your system if it hasn't
already been installed::
	
	cd bin/zookeeper/src/c
	sudo make install

You can test that the ZooKeeper extension is working properly by opening the
local Python with::
	
	./bin/python

And then importing zookeeper::
	
	import zookeeper


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

Running the Zookeeper Server:
-----------------------------

::
	
	./bin/zookeeper/bin/zkServer.sh start

To shut it down::
	
	./bin/zookeeper/bin/zkServer.sh stop


Running the Queuey Application:
-------------------------------

::

	bin/paster serve etc/queuey-dev.ini
