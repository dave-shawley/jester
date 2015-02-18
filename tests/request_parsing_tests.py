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
            parsing.ProtocolParser.header_parsed, self.callback)
        self.callback_calls = []

        self.parser.feed(b'GET / HTTP/1.1\r\n')

    def callback(self, *args, **kwargs):
        self.callback_calls.append((args, kwargs))

    def test_that_header_callback_is_invoked(self):
        self.parser.feed(b'Header: first value\r\n')
        self.assertEqual(self.callback_calls, [
            (('Header', b'first value'), {}),
        ])
