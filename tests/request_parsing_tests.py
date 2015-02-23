import unittest

from jester import parsing


class WhenRequestLineIsParsed(unittest.TestCase):

    def setUp(self):
        super(WhenRequestLineIsParsed, self).setUp()
        self.parser = parsing.ProtocolParser()
        self.parser.add_callback(
            parsing.ProtocolParser.request_line_received, self.callback)
        self.last_call = None

    def callback(self, *args, **kwargs):
        self.last_call = (args, kwargs)

    def test_that_request_line_received_callback_is_called(self):
        self.parser.feed(b'GET / HTTP/1.1\r\n')
        self.assertIsNotNone(self.last_call)

    def test_that_callback_receives_request_line(self):
        self.parser.feed(b'GET / HTTP/1.1\r\n')
        self.assertEqual(self.last_call[0], ('GET', '/', 'HTTP/1.1'))

    def test_that_callback_is_not_called_until_crlf_received(self):
        self.parser.feed(b'GET / HTTP/1.1')
        self.assertIsNone(self.last_call)
        self.parser.feed(b'\r\n')
        self.assertIsNotNone(self.last_call)


class WhenHeadersAreParsed(unittest.TestCase):

    def setUp(self):
        super(WhenHeadersAreParsed, self).setUp()
        self.parser = parsing.ProtocolParser()
        self.parser.add_callback(
            parsing.ProtocolParser.header_parsed, self.header_parsed)
        self.parser.add_callback(
            parsing.ProtocolParser.headers_finished, self.headers_finished)

        self.headers = []
        self.headers_are_finished = False

        self.parser.feed(b'GET / HTTP/1.1\r\n')

    def header_parsed(self, *args, **kwargs):
        self.headers.append((args, kwargs))

    def headers_finished(self):
        self.headers_are_finished = True

    def test_that_header_callback_is_invoked(self):
        self.parser.feed(b'Header: first value\r\n')
        self.assertGreater(len(self.headers), 0)

    def test_that_callback_is_invoked_for_each_header(self):
        self.parser.feed(
            b'Header: first value\r\n'
            b'Another-Header: second value\r\n'
        )

        self.assertEqual(self.headers, [
            (('Header', b'first value'), {}),
            (('Another-Header', b'second value'), {}),
        ])

    def test_that_headers_finished_is_emitted(self):
        self.parser.feed(b'Header: first\r\n\r\n')
        self.assertEqual(self.headers_are_finished, True)

    def test_that_parsing_by_byte_succeeds(self):
        headers = (
            b'Header: first value\r\n'
            b'Another-Header: second value\r\n'
            b'\r\n'
        )
        for index in range(0, len(headers)):
            self.parser.feed(headers[index:index + 1])
        self.assertEqual(self.headers, [
            (('Header', b'first value'), {}),
            (('Another-Header', b'second value'), {}),
        ])
        self.assertEqual(self.headers_are_finished, True)
