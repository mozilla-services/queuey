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

Queuey
======

Queuey is configured via an ini-style file, which is also used to configure
general Pyramid settings. This ini file contains a number of sections. The
following sections contain Queuey specific settings.


[metlog]
--------

Queuey uses metlog for logging metrics. For detailed information see the
`metlog docs <http://metlog-py.readthedocs.org/en/latest/config.html>`_.
