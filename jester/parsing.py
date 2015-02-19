import collections
import functools
import logging

from . import errors

DIGITS = b'0123456789'
"""Bytes that are valid numerical digits"""

ALPHA = b'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
"""Bytes that are valid alphabetic characters"""

VCHARS = bytes(bytearray(range(0x21, 0x7E)))
"""Bytes that are 'visible characters' per :rfc:`5234`"""

HEADER_CHARS = VCHARS + b' \t'
"""Bytes that are valid in a header value"""

URI_CHARS = (b":/?#[]@!$&'()*+,;=0123456789-._~%"
             b'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
"""Bytes that are valid in the *request-target* production."""

TOKEN_CHARS = DIGITS + ALPHA + b"!#$%&'*+-.^_`|~"
"""Bytes that are valid in the *token* production."""

SENTINEL_TOKEN = object()


def _emit(parse_function, event_function):
    """Call `event_function` after `parse_function` runs."""
    @functools.wraps(parse_function)
    def wrapped(data_in):
        data_out = parse_function(data_in)
        if data_in != data_out:
            event_function()
        return data_out
    return wrapped


def _translate_parse_failure(parser, other_exception):
    """Wrap `parser` and translate jester exceptions to `other_exception`."""
    @functools.wraps(parser)
    def translated(data):
        try:
            return parser(data)
        except errors.ProtocolParseException as exc:
            raise other_exception(exc.lexeme)
    return translated


class ProtocolParser(object):

    """
    An iterative HTTP protocol parser.

    This class parses HTTP messages as a stream of bytes and emits
    events as portions of the protocol are recognized.  The events
    are sent to other objects by calling registered callbacks.  An
    event is sent by invoking the callback inline during the parse.

    Callbacks are registered by calling :meth:`.add_callback` with
    the method that you want to be notified by and the callable to
    invoke when the event occurs.  The following methods emit
    notifications and thus can be passed as the first parameter to
    :meth:`.add_callback`.

    - :meth:`.request_line_received` callback is invoked with the
      the method, resource, and HTTP version

    """

    def __init__(self):
        super(ProtocolParser, self).__init__()
        self.logger = logging.getLogger('jester.Protocol')
        self._callbacks = collections.defaultdict(list)
        self._tokens = [SENTINEL_TOKEN]
        self._working_buffer = bytearray()
        self._parse_stack = [
            self.parse_token,
            self._skip_single_character(b' '),
            self.parse_target,
            self._skip_single_character(b' '),
            self.parse_http_version,
            self._skip_single_character(b'\r'),
            _emit(self._skip_single_character(b'\n'),
                  self.request_line_received),
            self.parse_header,
        ]

    def feed(self, data):
        """
        Consumes `data` and generates a stream of events.

        :param bytes data: bytes received from the client.
        :return: any bytes that remain after parsing is complete

        """
        self.logger.debug('feeding %r into the parser', data)
        while data and self._parse_stack:
            parser = self._parse_stack[0]
            self.logger.debug('parsing %r with %s', data, parser.__name__)
            data = parser(data)
        return data

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
        remaining = data.lstrip(b'\t ')
        if remaining:
            self._pop_parser()
        return remaining

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

    def parse_number(self, data):
        """
        Parse a string of digits from `data`.

        :param bytes data: buffer to parse
        :return: the bytes remaining in ``data`` after parsing

        """
        remaining = data.lstrip(DIGITS)
        self._consume(data, len(data) - len(remaining))
        return remaining

    def parse_http_version(self, data):
        """
        Parse an HTTP version specifier from `data`.

        :param bytes data: buffer to parse
        :return: the bytes remaining in ``data`` after parsing
        :raises jester.errors.MalformedHttpVersion:
            when a malformed version is parsed.  This exception
            is raised when the accumulated stream could not possibly
            be an HTTP version specifier.

        """
        parse_stack = [
            self.parse_fixed_string(b'HTTP/'),
            self.parse_single_character_from(b'0123456789'),
            self.parse_fixed_string(b'.'),
            self.parse_single_character_from(b'0123456789'),
        ]
        for index, parser in enumerate(parse_stack):
            parse_stack[index] = _translate_parse_failure(
                parser, errors.MalformedHttpVersion)
        parse_stack.append(self._collapse_http_version)
        parse_stack.extend(self._parse_stack[1:])
        self._parse_stack = parse_stack
        return data

    def parse_header(self, data):
        """
        Parse a header.

        :param bytes data: buffer to parse
        :return: ``data`` unchanged

        This method checks if there is another header in the stream.  If
        there is, then the parse stack is set up to parse another header.

        """
        self._pop_parser()
        if data.startswith(b'\r'):
            return data
        self._unshift_parsers(
            self.parse_token,
            self._skip_single_character(b':'),
            self.skip_linear_whitespace,
            self.parse_header_value,
            self._skip_single_character(b'\r'),
            _emit(self._skip_single_character(b'\n'),
                  self.header_parsed),
            self.parse_header,
        )
        return data

    def parse_header_value(self, data):
        """
        Parse a header value.

        :param bytes data: buffer to parse
        :return: the bytes remaining in ``data`` after parsing

        """
        remaining = data.lstrip(HEADER_CHARS)
        if remaining == data:
            raise errors.ProtocolParseException(data)
        self._consume(data, len(data) - len(remaining))
        return remaining

    def _collapse_http_version(self, data):
        """Collapse HTTP version tokens into a single token."""
        self.logger.debug('collapsing HTTP version - %r', self._tokens[-4:])
        self._tokens.pop()  # SENTINEL_TOKEN
        version_token = b''.join(self._tokens[-4:])
        del self._tokens[-4:]
        self._tokens.append(version_token)
        self._pop_parser()
        return data

    @property
    def tokens(self):
        """Tokens that are currently being processed."""
        return [t for t in self._tokens if t != SENTINEL_TOKEN]

    def add_callback(self, event, callback):
        """
        Add a callable to invoke when `event` occurs.

        :param event: the event that callback should be called for
        :param callback: the callable to invoke

        """
        self._callbacks[event].append(callback)

    def request_line_received(self):
        """Event fired when the request line is parsed."""
        method, resource, version = self.tokens
        for callback in self._callbacks[ProtocolParser.request_line_received]:
            callback(method.decode('US-ASCII'),
                     resource.decode('US-ASCII'),
                     version.decode('US-ASCII'))
        self._clear_tokens()

    def header_parsed(self):
        """Event fired when a header is parsed."""
        header_name, header_value = self.tokens
        for callback in self._callbacks[ProtocolParser.header_parsed]:
            callback(header_name.decode('US-ASCII'), header_value)
        self._clear_tokens()

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
        remaining = data[num_bytes:]
        if remaining:
            self._pop_parser()
        return remaining

    def _append_to_token(self, data):
        if self._tokens:
            if self._tokens[-1] is SENTINEL_TOKEN:
                self._tokens[-1] = data
            else:
                self._tokens[-1] += data
        else:
            self._tokens.append(data)

    def _add_token(self, data):
        if self._tokens[-1] is SENTINEL_TOKEN:
            self._tokens[-1] = data
        else:
            self._tokens.append(data)
        self._terminate_current_token()

    def _terminate_current_token(self):
        """Append the sentinel token if it isn't already there."""
        if self._tokens[-1] != SENTINEL_TOKEN:
            self._tokens.append(SENTINEL_TOKEN)

    def _clear_tokens(self):
        del self._tokens[:]

    def _unshift_parsers(self, *parsers):
        self.logger.debug('inserting parsers at front - %r', parsers)
        for parser in reversed(parsers):
            self._parse_stack.insert(0, parser)

    def _pop_parser(self):
        self._working_buffer = bytearray()
        current_parser = self._parse_stack.pop(0)
        self.logger.debug(
            'finished with %s, remaining - [%r]', current_parser.__name__,
            ','.join(p.__name__ for p in self._parse_stack))

    def _skip_single_character(self, character):
        """Generate a parser that skips `character` or fails."""
        def parser(data):
            if data.startswith(character):
                self._terminate_current_token()
                self._pop_parser()
                return data[1:]
            raise errors.ProtocolParseException(data[0])
        parser.__name__ = 'skip({0!r})'.format(character.decode('utf-8'))
        return parser

    def parse_fixed_string(self, fixed_value):
        """Generate a parser that consumes `fixed_value` or fails."""
        def parser(data):
            self._working_buffer.extend(data)
            if self._working_buffer.startswith(fixed_value):
                remaining = self._working_buffer[len(fixed_value):]
                self._add_token(fixed_value)
                self._pop_parser()
                return remaining
            if not fixed_value.startswith(self._working_buffer):
                raise errors.ProtocolParseException(self._working_buffer)
        parser.__name__ = 'parse({0!r})'.format(fixed_value.decode('utf-8'))
        return parser

    def parse_single_character_from(self, characters):
        """Generate a parser that consumes a character from `characters`."""
        valid_chars = bytearray(characters)

        def parser(data):
            if data[0] in valid_chars:  # RHS is reqd to be bytearray in 2.7
                self._add_token(bytes(data[0:1]))  # need bytes() for 2.7
                self._pop_parser()
                return data[1:]
            raise errors.ProtocolParseException(data[0])
        parser.__name__ = 'parser(any({0!r}))'.format(
            characters.decode('utf-8'))
        return parser
