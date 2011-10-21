from pyramid.security import Allow
from pyramid.security import Authenticated

class Root(object):
    def __init__(self, request):
        self.request = request
        self.__acl__ = [
            (Allow, Authenticated, 'create_queue'),
            (Allow, Authenticated, 'delete_queue'),
            (Allow, Authenticated, 'new_message'),
        ]
