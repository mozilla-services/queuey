# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
"""Message Queue Exceptions"""


class MessageQueueException(BaseException):
    """Base MessageQueue Exception"""


class StorageException(MessageQueueException):
    """All exceptions from storage backends"""


class ApplicationExists(StorageException):
    """Raised when an application of a given name already exists"""


class ApplicationNotRegistered(StorageException):
    """Raised when an application is not registered for an action
    requiring registration"""


class QueueAlreadyExists(StorageException):
    """Raised when a queue already exists and an action tries to
    create it"""


class QueueDoesNotExist(StorageException):
    """Raised when a queue does not exist and an action tries to
    act on it"""
