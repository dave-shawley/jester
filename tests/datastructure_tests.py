import unittest
import unittest.mock

from jester import datastructures


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
