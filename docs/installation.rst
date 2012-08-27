.. _installation:

============
Installation
============

Queuey is composed of two main parts, the Queuey Python web application and
the back-end storage layer used by the web application which defaults to
Cassandra_.

Cassandra_ can be setup either as a single node, or preferably as a cluster
for higher throughput, availability, and durability. The Queuey web application
should ideally be installed on separate web nodes to avoid sharing resources
with Cassandra_ but in smaller setups should be fine on the same node.

Installing the Queuey web application
=====================================

Using the source
----------------

Pre-requisites:

- Python >=2.6
- Make

Checkout the source and build using git from Github:

.. code-block:: bash

    git clone git://github.com/mozilla-services/queuey.git
    make

This will setup a new virtualenv in this directory with all the other tools
installed that Queuey needs to run.

Installing Cassandra
====================

It's recommended that Cassandra be installed using the Datastax_ 
`Cassandra Community Edition`_ as it goes through more testing then the latest
open-source version and provides a smooth upgrade path for the Enterprise
Edition should one wish to upgrade later. It also comes with support for the
Datastax_ Opscenter_ to help manage the Cassandra_ cluster.

There is complete documentation on the Datastax_ site that explains the
installation in more detail, a quick-start is provided here based on those
docs.

Before continuing to install Cassandra_, you should make sure the machine
you're installing to has the necessary pre-requisites::

    Sun Java Runtime Environment 1.6.0_19 or later

You can check to see what version of Java is available by running:

.. code-block:: bash

    java -version

Which should print something like:

.. code-block:: bash

    Java(TM) SE Runtime Environment (build 1.6.0_29-b11-402-11D50b)

If you're using an OpenJDK Java version, see the Datastax_ site for
`Installing Sun JRE on Redhat Systems <http://www.datastax.com/docs/1.0/install/install_package#installing-sun-jre-on-redhat-systems>`_ or
`Installing Sun JRE on Ubuntu systems <http://www.datastax.com/docs/1.0/install/install_package#install-jre-deb>`_.

These directions include installing the opscenter agent, which reports cluster
and node information for the opscenter dashboard.

Using the source
----------------

If you installed Queuey using ``make`` above and Cassandra_ is being installed
on the Queuey node, the Makefile includes Cassandra_ setup:

.. code-block:: bash

    make cassandra

If setting up a cluster, or not installing Cassandra_ on the same node as the
Queuey webapp the following directions should be used. Also note that this
step does not install opscenter, which also requires the following.

Download the source tarball to the desired directory (first check for newer
versions):

.. code-block:: bash

    cd $HOME
    mkdir datastax
    cd datastax

    wget http://downloads.datastax.com/community/dsc-cassandra-1.1.2-bin.tar.gz

    # On your first node *only*, get opscenter
    wget http://downloads.datastax.com/community/opscenter-2.1.2-free.tar.gz

    # Untar the distributions
    tar -xzvf dsc-cassandra-1.1.2-bin.tar.gz
    tar -xzvf opscenter-2.1.2-free.tar.gz

    # Remove the tarballs
    rm *.tar.gz

    # Create a data/logging directory
    mkdir $HOME/datastax/cassandra-data

The opscenter package only needs to be installed on a single node, as the
opscenter agent for the other nodes will be configured and tar'd up after
the setup is run on the main node. This is because the agent.tar.gz that will
be created contains SSL authentication information to protect the agents
communication.

For more efficient performance, its recommended that JNA be installed to
improve memory performance.

1. Download jna.jar from the `JNA project site <http://java.net/projects/jna/sources/svn/show/trunk/jnalib/dist/>`_.
2. Add jna.jar to $CASSANDRA_HOME/lib/ or otherwise place it on the CLASSPATH.
3. Edit the file /etc/security/limits.conf, adding the following entries for
   the user or group that runs Cassandra::

        $USER soft memlock unlimited
        $USER hard memlock unlimited

Via RPM's
---------

See the `Datastax RPM installation instructions <http://www.datastax.com/docs/1.0/install/install_package#installing-cassandra-rpm-packages>`_.


.. _Cassandra: http://cassandra.apache.org/
.. _Cassandra Community Edition: http://www.datastax.com/products/community
.. _Opscenter: http://www.datastax.com/products/opscenter
.. _Datastax: http://www.datastax.com/
