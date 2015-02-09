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
        self.parser.feed(b'GET / HTTP/1.1')
        self.assertIsNotNone(self.last_call)

    def test_that_callback_receives_request_line(self):
        self.parser.feed(b'GET / HTTP/1.1')
        self.assertEqual(self.last_call[0], ('GET', '/', 'HTTP/1.1'))
