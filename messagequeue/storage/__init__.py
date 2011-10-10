# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Mozilla Message Queue
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
# Ben Bangert (bbangert@mozilla.com)
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
"""MessageQueue Storage Interface"""
from zope.interface import Interface

class MessageQueueBackend(Interface):
    """A MessageQueue Backend"""
    def __init__(self, username=None, password=None, database='MessageQueue', 
                 host='localhost'):
        """Initialize the backend"""

    def retrieve(self, queue_name, limit=None, timestamp=None,
                 order="ascending"):
        """Retrieve messages from a queue

        :param queue_name: Queue name
        :param type: string
        :param limit: Amount of messages to retrieve
        :param type: int
        :param timestamp: Retrieve messages starting with this timestamp
        :param type: datetime
        :param order: Which order to traverse the messages. Defaults to
                      ascending order.
        :type order: ascending/descending
        :param type: order

        """
    
    def push(self, queue_name, message, ttl=3600*24*3):
        """Push a message onto the given queue
        
        The queue is assumed to exist, and will be created if it does not
        exist.

        :param queue_name: Queue name
        :param type: string
        :param message: Message to add to the queue
        :param type: string
        :param ttl: Time to Live in seconds for the message, after this
                    period the message should be unavilable
        :param type: int

        """

    def exists(self, queue_name):
        """Check to see if a queue of a given name exists"""
