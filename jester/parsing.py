from . import errors


URI_CHARS = (b":/?#[]@!$&'()*+,;=0123456789-._~%"
             b'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
"""Bytes that are valid in the *request-target* production."""

TOKEN_CHARS = URI_CHARS + b'^`|'
"""Bytes that are valid in the *token* production."""

SENTINEL_TOKEN = object()


class ProtocolParser(object):

    """
    An iterative HTTP protocol parser.

    This class parses HTTP messages as a stream of bytes and emits
    events as portions of the protocol are recognized.  The events
    are sent to an object that implements a simple event handling
    protocol::

    - ``request_line_received``
    - ``header_parsed``
    - ``body_parsed``

    The events are sent by calling the appropriate method inline
    during the parse.  The event handler can reject a message from
    any callback by raising a :exc:`jester.errors.RejectMessage`
    instance.

    """

    def __init__(self):
        super().__init__()
        self._tokens = [SENTINEL_TOKEN]
        self.version = None

    def parse_token(self, data):
        """
        Parse a `token`_ from ``data``.

        :param bytes data: the byte stream to parse
        :return: the bytes remaining in ``data`` after parsing

        .. _token: http://tools.ietf.org/html/rfc7230#appendix-B

        """
        remaining = data.lstrip(TOKEN_CHARS)
        return self._consume(data, len(data) - len(remaining))

    def skip_linear_whitespace(self, data):
        """
        Skip leading linear whitespace from `data`.

        :param bytes data: buffer to strip whitespace from
        :return: the portion of ``data`` following the LWSP

        This method will terminate the current token if necessary.

        """
        self._terminate_current_token()
        return data.lstrip(b'\t ')

    def parse_target(self, data):
        """
        Parse the `target`_ from a request line.

        :param bytes data: buffer to parse
        :return: the bytes remaining in ``data`` after parsing

        Note that this method **DOES NOT** validate that the target
        is a URL.  It simply parses the token containing characters
        that are valid within a URL.

        .. _target: http://tools.ietf.org/html/rfc7230#appendix-B

        """
        remaining = data.lstrip(URI_CHARS)
        self._consume(data, len(data) - len(remaining))
        return remaining

    def parse_version(self, data):
        """
        Parse an HTTP version specifier from `data`.

        :param bytes data: buffer to parse
        :return: the bytes remaining in ``data`` after parsing
        :raises jester.errors.MalformedHttpVersion:
            when a malformed version is parsed.  This exception
            is raised when the accumulated stream could not possibly
            be an HTTP version specifier.

        """
        if self._tokens[-1] == SENTINEL_TOKEN:
            self._tokens[-1] = b''
        current = self._tokens[-1] + data
        if len(current) >= 8:
            if current.startswith(b'HTTP/'):
                major, dot, minor = current[5:8].decode('us-ascii')
                if dot == '.':
                    self.version = int(major), int(minor)
                    self._tokens[-1] = current[:8]
                    return current[8:]
                else:
                    raise errors.MalformedHttpVersion(current)
            else:
                raise errors.MalformedHttpVersion(current)
        self._consume(data, len(data))

    @property
    def tokens(self):
        return [t for t in self._tokens if t != SENTINEL_TOKEN]

    def _consume(self, data, num_bytes):
        """
        Consume `num_bytes` from `data`.

        :param bytes data: buffer to consume the left-most bytes from
        :param int num_bytes: the number of bytes to copy
        :return: the remaining portion of ``data``

        The consumed data is appended to the last token adjusting the
        sentinel token usage as necessary.

        """
        self._append_to_token(data[:num_bytes])
        return data[num_bytes:]

    def _append_to_token(self, data):
        if self._tokens[-1] is SENTINEL_TOKEN:
            self._tokens[-1] = data
        else:
            self._tokens[-1] += data

    def _terminate_current_token(self):
        """Append the sentinel token if it isn't already there."""
        if self._tokens[-1] != SENTINEL_TOKEN:
            self._tokens.append(SENTINEL_TOKEN)