class Finish(Exception):
    pass


class JesterException(Exception):
    pass


class HTTPError(JesterException):
    """Stop processing a request with ``status_code``."""

    def __init__(self, status_code, reason):
        super(HTTPError, self).__init__()
        self.status_code = status_code
        self.reason = reason


class ProtocolViolation(JesterException):
    """
    Stop processing a request and terminate the connection.

    :param int|NoneType status_code: optional status code to respond
        to the client with.
    :param str|NoneType reason: optional reason to include in the
        response.

    This is used when a constraint of the HTTP protocol is violated
    before the request is received.  For example, if a HTTP header is
    syntactically incorrect.

    .. note::

       If the `status_code` is not supplied, then no response is sent
       to the client and the connection is abortively closed.

    """

    def __init__(self, status_code=None, reason=None):
        super(ProtocolViolation, self).__init__()
        self.status_code = status_code
        self.reason = reason
