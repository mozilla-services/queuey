from pyramid.security import Allow
from pyramid.security import Authenticated

class Root(object):
    __acl__ = [
            (Allow, Authenticated, 'create_queue'),
            (Allow, Authenticated, 'delete_queue'),
            (Allow, Authenticated, 'new_message'),
        ]

    def __init__(self, request):
        self.request = request
