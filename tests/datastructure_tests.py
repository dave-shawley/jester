import asyncio.streams
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
        self.response = datastructures.HTTPResponse(self.writer.write)

    def test_that_headers_are_sent_with_status(self):
        self.response.set_header('one', '1')
        self.response.set_header('2', 'two')
        self.response.set_header('tres', '3')
        self.assertEqual(self.writer.write.call_count, 0)

        self.response.send_status(200, 'what ev')
        self.assertEqual(self.writer.write.call_count, 4)

        self.assertEqual(self.writer.write.mock_calls[0],
                         unittest.mock.call(b'HTTP/1.1 200 what ev\r\n'))
        self.assertIn(unittest.mock.call(b'One: 1\r\n'),
                      self.writer.write.mock_calls)
        self.assertIn(unittest.mock.call(b'2: two\r\n'),
                      self.writer.write.mock_calls)
        self.assertIn(unittest.mock.call(b'Tres: 3\r\n'),
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
        self.writer.write.assert_called_once_with(b'One: two\r\n')

    def test_that_set_header_writes_after_status_is_sent(self):
        self.response.send_status(200, 'ok')
        self.writer.write.reset_mock()

        self.response.set_header('One', 'two')
        self.writer.write.assert_called_once_with(b'One: two\r\n')

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
        self.writer.write.assert_called_once_with(b'HTTP/1.1 200 Reason\r\n')

    def test_that_okay_status_sent_with_body(self):
        self.response.send_body_content('foo')
        self.response.send_body_content('bar')
        self.assertEqual(self.writer.write.mock_calls,
                         [unittest.mock.call(b'HTTP/1.1 200 OK\r\n'),
                          unittest.mock.call(b'\r\n'),
                          unittest.mock.call(b'foo'),
                          unittest.mock.call(b'bar')])


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


class HTTPRequestBodyTests(helpers.AsyncioTestCase):

    def test_that_content_length_body_bytes_are_read(self):
        reader = asyncio.StreamReader()
        reader.feed_data(b'Content-Length: 11\r\n'
                         b'Content-Type: text/plain\r\n'
                         b'\r\nhello worldGET /next/request HTTP/1.1\r\n')
        reader.feed_eof()

        request = datastructures.HTTPRequest('POST', '/', 'HTTP/1.1')
        self.run_async(request.read_headers(reader))
        self.run_async(request.read_content_body(reader))
        self.assertEqual(request.body, b'hello world')

        rest = self.run_async(reader.read())
        self.assertEqual(rest, b'GET /next/request HTTP/1.1\r\n')

    def test_that_chunked_transfer_encoding_is_supported(self):
        msg = (b'Throwup on your pillow. Eat prawns daintily with a claw '
               b'then lick paws clean wash down prawns with a lap of '
               b'carnation milk then retire to the warmest spot on the couch '
               b'to claw at the fabric before taking a catnap. So if it '
               b'fits, I sits yet stare at wall turn and meow stare at wall '
               b'some more meow again continue staring. '
               b'Make muffins peer out window, chatter at birds, lure them '
               b'to mouth. Where is my slave? I\'m getting hungry. Purr '
               b'while eating destroy the blinds so cat snacks, or sweet '
               b'beast, for go into a room to decide you didn\'t want to be '
               b'in there anyway eat owner\'s food.')
        reader = asyncio.StreamReader()
        reader.feed_data(b'Transfer-Encoding: chunked\r\n'
                         b'Content-Type: text/plain\r\n'
                         b'\r\n')
        offset = 0
        for chunk_size in (20, 90, 42, 290):
            reader.feed_data('{:x}\r\n'.format(chunk_size).encode('ascii'))
            reader.feed_data(msg[offset:offset+chunk_size])
            offset += chunk_size
        reader.feed_data('{:x}\r\n'.format(len(msg) - offset).encode('ascii'))
        reader.feed_data(msg[offset:])
        reader.feed_data(b'0\r\n')

        request = datastructures.HTTPRequest('POST', '/catipsum', 'HTTP/1.1')
        self.run_async(request.read_headers(reader))
        self.run_async(request.read_content_body(reader))
        self.assertEqual(request.body, msg)

    def test_that_zero_length_body_supported(self):
        reader = asyncio.StreamReader()
        reader.feed_data(b'Content-Length: 0\r\n\r\n'
                         b'GET /next/request HTTP/1.1\r\n')
        reader.feed_eof()

        request = datastructures.HTTPRequest('POST', '/doit', 'HTTP/1.1')
        self.run_async(request.read_headers(reader))
        self.run_async(request.read_content_body(reader))

        self.assertEqual(request.body, b'')
        self.assertEqual(self.run_async(reader.read()),
                         b'GET /next/request HTTP/1.1\r\n')

    def test_that_unspecified_length_reads_until_eof(self):
        reader = asyncio.StreamReader()
        reader.feed_data(b'Content-Type: text/plain\r\n'
                         b'\r\n'
                         b'content body')
        reader.feed_eof()

        request = datastructures.HTTPRequest('POST', '/', 'HTTP/1.1')
        self.run_async(request.read_headers(reader))
        self.run_async(request.read_content_body(reader))
        self.assertEqual(request.body, b'content body')

    def test_that_incomplete_read_with_content_length_fails(self):
        reader = asyncio.StreamReader()
        reader.feed_data(b'Content-Length: 100\r\n'
                         b'\r\n'
                         b'not anywhere near 100 bytes')
        reader.feed_eof()

        request = datastructures.HTTPRequest('POST', '/', 'HTTP/1.1')
        self.run_async(request.read_headers(reader))
        with self.assertRaises(exceptions.ProtocolViolation) as context:
            self.run_async(request.read_content_body(reader))
        self.assertIsNone(context.exception.status_code)
        self.assertIsInstance(context.exception.__cause__, EOFError)

    def test_that_incomplete_chunked_read_fails(self):
        reader = asyncio.StreamReader()
        reader.feed_data(b'Content-Type: text/plain\r\n'
                         b'Transfer-Encoding: chunked\r\n'
                         b'\r\n'
                         b'10\r\n'
                         b'sixteen    bytes'
                         b'30\r\n'
                         b'fewer than 48 bytes without trailing zero')
        reader.feed_eof()

        request = datastructures.HTTPRequest('POST', '/', 'HTTP/1.1')
        self.run_async(request.read_headers(reader))
        with self.assertRaises(exceptions.ProtocolViolation) as context:
            self.run_async(request.read_content_body(reader))
        self.assertIsNone(context.exception.status_code)
        self.assertIsInstance(context.exception.__cause__, EOFError)
