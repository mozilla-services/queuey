.. _configuration:

=============
Configuration
=============

Cassandra
=========

Cassandra is configured via `cassandra.yaml` and `log4j-server.properties`
files. Queuey doesn't have any specific configuration requirements for
Cassandra, though availability and durability guarantees depend on
appropriate Cassandra settings.

Please refer to the `Datastax community edition documentation <http://www.datastax.com/docs/1.1/configuration/index>`_
for further details.

Pyramid
=======

Queuey is implemented on top of the `Pyramid web framework <http://www.pylonsproject.org/projects/pyramid/about>`_.
Documentation for configuring WSGI servers and general deployment techniques
therefor also apply to Queuey. The
`Pyramid cookbook <http://docs.pylonsproject.org/projects/pyramid_cookbook/en/latest/deployment/index.html>`_
contains some advice on a variety of web servers.

The simplest example of a Pyramid pipeline contains of the following::

    [app:pyramidapp]
    use = egg:queuey

    [filter:catcherror]
    paste.filter_app_factory = mozsvc.middlewares:make_err_mdw

    [pipeline:main]
    pipeline = catcherror
               pyramidapp

Queuey
======

Queuey is configured via an ini-style file, which is also used to configure
general Pyramid settings. This ini file contains a number of sections. The
following sections contain Queuey specific settings.

[application_keys]
------------------

Contains a mapping of application name to application key. The application
key acts as a shared secret between server and client. For example::

    [application_keys]
    app_1 = f25bfb8fe200475c8a0532a9cbe7651e

[storage]
---------

Configures the storage for message data.

backend
    The type of storage, for Cassandra use:
    `queuey.storage.cassandra.CassandraQueueBackend`

Further settings are dependent on the storage.

[metadata]
----------

Configures the storage for message metadata.

backend
    The type of storage, for Cassandra use:
    `queuey.storage.cassandra.CassandraMetadata`

Further settings are dependent on the storage.

Cassandra storage options
-------------------------

The Cassandra storages support the following additional settings:

host
    A comma separated list of either `host` or `host:port` values specifying
    the Cassandra servers. Defaults to `localhost:9160`.

username
    A username used for connecting to Cassandra's Thrift interface.
    Currently this value is ignored.

password
    A password used for connecting to Cassandra's Thrift interface.
    Currently this value is ignored.

multi_dc
    A boolean indicating whether or not Cassandra runs in a multi-datacenter
    environment, defaults to `False`. If enabled, read and write operations
    default to `LOCAL_QUORUM` instead of `QUORUM`.

create_schema
    A boolean value indicating if the required Cassandra schema should be
    automatically created during startup. Defaults to `True`. If enabled the
    first server in the host list is used and the keyspace names are
    hard-coded to their defaults.

database
    The name of the keyspace, defaults to `MessageStore` for the storage and
    `MetadataStore` for the metadata section.

[metlog]
--------

Queuey uses metlog for logging metrics. For detailed information see the
`metlog docs <http://metlog-py.readthedocs.org/en/latest/config.html>`_.
