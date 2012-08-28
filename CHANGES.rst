Changelog
=========

0.8 (2012-08-28)
----------------

Features
********

- Compatibility with Cassandra 1.1
- Add new API's to get, post and update messages by their message id
- Add new memory storage backend for testing purposes.
- Add metlog based metrics logging.
- Use pycassa's system manager support to programmatically create the
  Cassandra schema during startup.

Bug fixes
*********

- Fix precision errors in server side message id to timestamp conversion.
- Enforce message keys to be valid UUID1 instead of just any UUID.
