# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
from pyramid.security import Allow
from pyramid.security import Authenticated


class Root(object):
    __acl__ = [
            (Allow, Authenticated, 'create_queue'),
            (Allow, Authenticated, 'delete_queue'),
            (Allow, Authenticated, 'new_message'),
            (Allow, Authenticated, 'view_queue'),
            (Allow, Authenticated, 'view_message'),
        ]

    def __init__(self, request):
        self.request = request
