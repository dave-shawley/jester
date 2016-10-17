import collections
import logging
import urllib.parse

from jester import exceptions, syntax


_logger = logging.getLogger(__name__)


def _normalize_header_name(key):
    return str(key).lower().title()


class Headers(collections.UserDict):
    """
    Dictionary of HTTP headers.

    This IS NOT a standard case insensitive dictionary that most
    HTTP libraries provide.  The header names (keys) are normalized
    to title case during both lookup and storage.  This means that
    the values returned by :meth:`.keys` may differ from the values
    that were used to store the value.

    >>> h = Headers()
    >>> h['header-name'] = 'value'
    >>> list(h.keys())
    ['Header-Name']

    The same normalization is performed when values are retrieved
    so you do not have to be so careful when looking up values.
    You SHOULD be consistent in your code of course.

    >>> h = Headers()
    >>> h['header-name'] = 'value'
    >>> h['Header-Name'], h['header-name'], h['HEADER-NAME']
    ('value', 'value', 'value')

    Unlike :meth:`email.message.Message.__setitem__`, this class
    retains the standard dictionary behavior and always overwrites
    what is there.  If you want to append a new value to a header,
    then use the :meth:`.add_header` method instead of treating
    the instance like a dictionary.

    >>> h = Headers()
    >>> h['header'] = 'first'
    >>> h['header'] = 'second'
    >>> h['header']
    'second'
    >>> h.add_header('header', 2)
    >>> h['header']
    'second,2'

    """

    def __getitem__(self, item):
        return super(Headers, self).__getitem__(_normalize_header_name(item))

    def __setitem__(self, key, value):
        super(Headers, self).__setitem__(_normalize_header_name(key),
                                         str(value))

    def add_header(self, name, value):
        """
        Appends `value` to an existing header.

        :param name: name of the header to assign/append to
        :param value: value to append to the header

        The header name is normalized before retrieving the existing
        value.  If a value exists, then `value` is appended to the
        current value after appending a comma.  This opperation is
        described in :rfc:`7230#section-3.2.2`:

           "a recipient MAY combine multiple header values with the
           same field name into one "field-name: field-value" pair,
           without changing the semantics of the message, by appending
           each subsequent field value to the combined field value in
           order, separated by a comma."

        """
        try:
            self[name] = self[name] + ',' + str(value)
        except KeyError:
            self[name] = value


class HTTPRequest(object):
    """
    Request as it is being processed.

    :param str method: the incoming HTTP method
    :param str resource: the request_target portion of the HTTP request line
    :param str http_version: the version portion of the HTTP request line

    A ``HTTPRequest`` instance captures all of the details about the
    incoming request as well as having methods to read the request from
    the input stream.

    .. attribute:: method

       The requested HTTP method.  This value is not restricted to the
       well-known set of HTTP methods so you must be prepared to handle
       custom method names.

    .. attribute:: request_target

       The resource portion of the request line.  This value is not
       restricted in any way.

    .. attribute:: http_version

       The HTTP version that governs the request.  This value is not
       restricted in any way.

    .. attribute:: headers

       :class:`~jester.datastructures.Headers` instance containing
       the incoming headers.  This attribute is initially empty and
       populated by the :meth:`read_headers` method.

    """

    def __init__(self, method, resource, http_version):
        super(HTTPRequest, self).__init__()
        self.logger = _logger.getChild('HTTPRequest')
        self.method = method
        self.request_target = resource
        self.http_version = http_version
        self.headers = Headers()
        self.url = urllib.parse.urlsplit(resource)
        self.body = None

    async def read_headers(self, reader):
        """
        Read HTTP headers from `reader`.

        :param asyncio.streams.StreamReader reader: stream to read
            the header segment from

        This method repeatedly reads lines from `reader`, parses them
        into name and value, and adds them to the :attr:`headers`
        collection.  If a line cannot be processed as a header, then
        a :exc:`~jester.exceptions.ProtocolViolation` exception is
        raised.

        :raises jester.exceptions.ProtocolViolation: if a request line
            cannot be parsed as a HTTP header.

        """
        while True:
            # TODO need to handle timeouts in some sensible way.
            # StreamReader.readline will block until a LF is received.
            line = await reader.readline()
            line = line.rstrip(b'\r\n')
            if not line:  # headers done
                break

            name, sep, value = line.partition(b':')
            self.logger.debug('parsed: %r %r %r', name, sep, value)
            if sep != b':':  # missing separator
                raise exceptions.ProtocolViolation(400, 'Malformed header')
            if name.endswith((b' ', b'\t')):  # illegal whitespace
                # RFC7230 3.2.4 - No whitespace is allowed between the
                # header field-name and colon. ... A server MUST reject
                # any received request message that contains whitespace
                # between a header field-name and colon with a response
                # code of 400 (Bad Request)
                raise exceptions.ProtocolViolation(
                    400, 'Illegal header syntax')

            # RFC7230 3.2.4 - A field value may be preceded and/or
            # followed by optional whitespace ... OWS occurring before the
            # first non-whitespace octet of the field value or after the
            # last non-whitespace octet of the field value ought to be
            # excluded by parsers when extracting the field value
            value = value.strip()

            try:
                name = name.decode('ASCII')
                value = value.decode('ASCII')
            except Exception:
                # RFC7230 uses <token> as <field-name> which is limited
                # to a strict subset of ASCII characters.  <field-value>
                # is also limited to visual ASCII characters.
                self.logger.exception('Non-ASCII header "%r: %r"',
                                      name, value)
                raise exceptions.ProtocolViolation(400, 'Non-ASCII Header')

            if any(c not in syntax.TCHARS for c in name):
                raise exceptions.ProtocolViolation(
                    400, 'Illegal token characters')
            self.headers[name] = value

    async def read_content_body(self, reader):
        """

        :param asyncio.streams.StreamReader reader: stream to read
            the body from

        :raises: jester.exceptions.ProtocolViolation

        """
        try:

            content_len = self.headers.get('Content-Length', None)
            if content_len is not None:
                self.body = await reader.readexactly(int(content_len))
                return

            transfer_encoding = self.headers.get('Transfer-Encoding', None)
            if transfer_encoding == 'chunked':
                chunks = []
                while True:
                    chunk_size = await reader.readline()
                    chunk_size = int(chunk_size.decode('ascii'), base=16)
                    if chunk_size == 0:
                        break
                    buf = await reader.readexactly(chunk_size)
                    chunks.append(buf)
                self.body = b''.join(chunks)
                return

            self.body = await reader.read()

        except EOFError as error:
            raise exceptions.ProtocolViolation from error


class HTTPResponse(object):
    """
    Response to the current request.

    :param write_callback: function that writes bytes to the output

    """

    def __init__(self, write_callback):
        super(HTTPResponse, self).__init__()
        self.logger = _logger.getChild('HTTPResponse')
        self.headers = Headers()
        self.status_line_sent = False
        self._body_started = False
        self.write_callback = write_callback

    def add_header(self, name, value):
        """
        Add a header to the response.

        :param str name:
        :param str value:

        """
        if not self.status_line_sent:
            try:
                self.headers[name] = self.headers[name] + ', ' + value
            except KeyError:
                self.headers[name] = value
        elif not self._body_started:
            self._send_header(name, value)
        else:
            self.logger.warning('failed to add header %s value %s, header '
                                'values cannot be sent after body is started',
                                name, value)

    def set_header(self, name, value):
        """
        Overwrite a header value.

        :param str name:
        :param str value:

        """
        if not self.status_line_sent:
            self.headers[name] = value
        elif not self._body_started:
            self._send_header(name, value)
        else:
            self.logger.warning('failed to set header %s to %s, header '
                                'values cannot be sent after body is started',
                                name, value)

    def send_status(self, status, reason):
        """
        Send the status line.

        :param int status:
        :param str reason:

        """
        if self.status_line_sent:
            self.logger.error('status line already sent in send_status(%s,%s)',
                              status, reason)
            return

        self._write('HTTP/1.1 {} {}\r\n', status, reason)
        self.status_line_sent = True
        for name, value in self.headers.items():
            self._send_header(name, value)

    def send_body_content(self, chunk):
        """
        Send response body.

        :param str chunk:

        """
        if not self.status_line_sent:
            self.send_status(200, 'OK')
        if not self._body_started:
            self._write('\r\n')
            self._body_started = True
        self._write('{}', chunk)

    def _write(self, datafmt, *args, **kwargs):
        encoding = kwargs.pop('_encoding', 'ASCII')
        payload = datafmt.format(*args, **kwargs)
        if not isinstance(payload, (bytes, bytearray, memoryview)):
            payload = payload.encode(encoding)

        if self.write_callback is not None:
            self.write_callback(payload)
        else:
            self.logger.warning('not writing %d bytes, write callback '
                                'is not set', len(payload))

    def _send_header(self, name, value):
        self._write('{}: {}\r\n', name, value)
