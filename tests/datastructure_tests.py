import unittest

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
