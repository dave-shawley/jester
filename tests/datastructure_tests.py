import asyncio
import unittest
import unittest.mock

from jester import datastructures, exceptions
from tests import helpers


class HeaderTests(unittest.TestCase):

    def test_header_case_is_normalized(self):
        headers = datastructures.Headers()
        headers['UPPER'] = 'message'
        self.assertEqual(list(headers.keys()), ['Upper'])

    def test_header_lookup_is_case_insensitive(self):
        headers = datastructures.Headers()
        headers['One'] = 'one'
        self.assertEqual(headers['one'], 'one')

    def test_header_storage_is_coerced_to_strings(self):
        headers = datastructures.Headers()
        headers['One'] = 1
        self.assertEqual(headers['One'], '1')

    def test_duplicated_headers_overwrite(self):
        headers = datastructures.Headers()
        headers['one'] = 1
        headers['one'] = 'two'
        self.assertEqual(headers['one'], 'two')

    def test_that_add_header_sets_new_header(self):
        headers = datastructures.Headers()
        headers.add_header('one', 1)
        self.assertEqual(headers['one'], '1')


class HTTPResponseTests(unittest.TestCase):

    def setUp(self):
        super(HTTPResponseTests, self).setUp()
        self.writer = unittest.mock.Mock()
        self.response = datastructures.HTTPResponse(self.writer)

    def test_that_headers_are_sent_with_status(self):
        self.response.set_header('one', '1')
        self.response.set_header('2', 'two')
        self.response.set_header('tres', '3')
        self.assertEqual(self.writer.write.call_count, 0)

        self.response.send_status(200, 'what ev')
        self.assertEqual(self.writer.write.call_count, 4)

        self.assertEqual(self.writer.write.mock_calls[0],
                         unittest.mock.call('HTTP/1.1 200 what ev\r\n'))
        self.assertIn(unittest.mock.call('One: 1\r\n'),
                      self.writer.write.mock_calls)
        self.assertIn(unittest.mock.call('2: two\r\n'),
                      self.writer.write.mock_calls)
        self.assertIn(unittest.mock.call('Tres: 3\r\n'),
                      self.writer.write.mock_calls)

    def test_that_add_header_appends_values(self):
        self.response.add_header('Header', 'first')
        self.response.add_header('Header', 'second')
        self.assertEqual(self.response.headers['Header'], 'first, second')

    def test_that_set_header_overwrites_header(self):
        self.response.add_header('Header', 'first')
        self.response.add_header('Header', 'second')
        self.response.set_header('Header', 'final')
        self.assertEqual(self.response.headers['Header'], 'final')

    def test_that_add_header_writes_after_status_is_sent(self):
        self.response.send_status(200, 'ok')
        self.writer.write.reset_mock()

        self.response.add_header('One', 'two')
        self.writer.write.assert_called_once_with('One: two\r\n')

    def test_that_set_header_writes_after_status_is_sent(self):
        self.response.send_status(200, 'ok')
        self.writer.write.reset_mock()

        self.response.set_header('One', 'two')
        self.writer.write.assert_called_once_with('One: two\r\n')

    def test_that_headers_cannot_be_added_after_starting_body(self):
        self.response.send_status(200, 'Bah')
        self.response.send_body_content('body')
        self.writer.write.reset_mock()

        self.response.add_header('Foo', 'Bar')
        self.response.set_header('Bah', 'Boo')
        self.assertEqual(self.writer.write.call_count, 0)

    def test_that_status_can_only_be_sent_once(self):
        self.response.send_status(200, 'Reason')
        self.response.send_status(500, 'Fail')
        self.writer.write.assert_called_once_with('HTTP/1.1 200 Reason\r\n')

    def test_that_okay_status_sent_with_body(self):
        self.response.send_body_content('foo')
        self.response.send_body_content('bar')
        self.assertEqual(self.writer.write.mock_calls,
                         [unittest.mock.call('HTTP/1.1 200 OK\r\n'),
                          unittest.mock.call('\r\n'),
                          unittest.mock.call('foo'),
                          unittest.mock.call('bar')])


class HTTPRequestTests(helpers.AsyncioTestCase):

    def setUp(self):
        super(HTTPRequestTests, self).setUp()
        self.reader = asyncio.StreamReader(loop=self.loop)
        self.request = datastructures.HTTPRequest('GET', '/', 'HTTP/1.1')

    def test_that_headers_are_read(self):
        self.reader.feed_data(b'Header: value\r\n'
                              b'\r\n')
        self.run_async(self.request.read_headers(self.reader))
        self.assertEqual(self.request.headers['Header'], 'value')

    def test_that_whitespace_before_colon_fails(self):
        self.reader.feed_data(b'Header : value\r\n')
        with self.assertRaises(exceptions.ProtocolViolation) as context:
            self.run_async(self.request.read_headers(self.reader))
        self.assertEqual(context.exception.status_code, 400)

    def test_that_non_ascii_header_name_fails(self):
        self.reader.feed_data(
            ('\u0443\u0434\u0430\u0440-\u0433\u043e\u043b\u043e\u0432'
             '\u043e\u0439: Value\r\n').encode('utf-8'))
        with self.assertRaises(exceptions.ProtocolViolation) as context:
            self.run_async(self.request.read_headers(self.reader))
        self.assertEqual(context.exception.status_code, 400)

    def test_that_cr_is_optional(self):
        self.reader.feed_data(b'One: 1\nTwo: 2\n\n')
        self.run_async(self.request.read_headers(self.reader))
        self.assertEqual(self.request.headers['One'], '1')
        self.assertEqual(self.request.headers['Two'], '2')

    def test_that_missing_colon_fails(self):
        self.reader.feed_data(b'Header value\r\n\r\n')
        with self.assertRaises(exceptions.ProtocolViolation) as context:
            self.run_async(self.request.read_headers(self.reader))
        self.assertEqual(context.exception.status_code, 400)

    def test_that_invalid_header_name_characters_are_rejected(self):
        self.reader.feed_data(b'<Name>: value\r\n\r\n')
        with self.assertRaises(exceptions.ProtocolViolation) as context:
            self.run_async(self.request.read_headers(self.reader))
        self.assertEqual(context.exception.status_code, 400)
