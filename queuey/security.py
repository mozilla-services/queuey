from pyramid.security import Authenticated
from pyramid.security import Everyone


class InvalidApplicationKey(Exception):
    """Raised when an application key is invalid"""


class InvalidBrowserID(Exception):
    """Raised when a browser id assertion is invalid"""


class QueueyAuthenticationPolicy(object):
    def effective_principals(self, request):
        effective_principals = [Everyone]
        auth_header = request.headers.get('Authorization', [])
        if auth_header:
            auth_header = [x.strip() for x in auth_header.split(';')]
        for auth_line in auth_header:
            if auth_line.startswith('Application '):
                app_key = auth_line.strip('Application ').strip()
                app_name = request.registry['app_keys'].get(app_key)
                if app_name:
                    effective_principals.append('app:%s' % app_name)
                    request.application_name = app_name
                    if 'application' not in effective_principals:
                        effective_principals.append('application')
                else:
                    raise InvalidApplicationKey("Invalid application key")
            # TODO: Whenever the MAC/BID stuff is determined, pull it out here
            # elif auth_line.startswith('BrowserID '):
            #     assertion = auth_line.strip('BrowserID ').strip()
            #     try:
            #         data = vep.verify(assertion, request.host)
            #     except Exception:
            #         raise InvalidBrowserID("Invalid browser ID assertion")
            #     effective_principals.append('bid:%s' % data['email'])
        if len(effective_principals) > 1:
            effective_principals.append(Authenticated)
        return effective_principals
