import random
import unittest

from jester import errors, parsing


class WhenParsingTokens(unittest.TestCase):

    def setUp(self):
        super(WhenParsingTokens, self).setUp()
        self.parser = parsing.ProtocolParser()

    def test_that_tokens_are_parsed(self):
        buffer = self.parser.parse_token(b'one tw')
        buffer = self.parser.skip_linear_whitespace(buffer)
        buffer += b'o three '
        while buffer:
            buffer = self.parser.parse_token(buffer)
            buffer = self.parser.skip_linear_whitespace(buffer)
        self.assertEqual(self.parser.tokens, [b'one', b'two', b'three'])

    def test_that_final_token_is_available(self):
        buffer = b'onetwo three'
        buffer = self.parser.parse_token(buffer)
        buffer = self.parser.skip_linear_whitespace(buffer)
        buffer = self.parser.parse_token(buffer)
        self.assertEqual(buffer, b'')
        self.assertEqual(self.parser.tokens, [b'onetwo', b'three'])


class WhenParsingRequestTarget(unittest.TestCase):

    def setUp(self):
        super(WhenParsingRequestTarget, self).setUp()
        self.parser = parsing.ProtocolParser()

    def test_that_parsing_terminates_at_space(self):
        buffer = b'whatever-you%C2%ABwant%C2%BB left-over'
        buffer = self.parser.parse_target(buffer)
        self.assertEqual(buffer, b' left-over')
        self.assertEqual(self.parser.tokens, [b'whatever-you%C2%ABwant%C2%BB'])

    def test_that_parsing_terminates_at_nonascii_character(self):
        buffer = b'valid-target\xC2\xABnext token'
        buffer = self.parser.parse_target(buffer)
        self.assertEqual(buffer, b'\xC2\xABnext token')


class WhenParsingHttpVersion(unittest.TestCase):

    def setUp(self):
        super(WhenParsingHttpVersion, self).setUp()
        self.parser = parsing.ProtocolParser()
        self.parser._parse_stack = [self.parser.parse_http_version]

    def test_that_parsing_version_succeeds(self):
        buffer = b'HTTP/1.1\r\n'
        buffer = self.parser.feed(buffer)
        self.assertEqual(buffer, b'\r\n')
        self.assertEqual(self.parser.tokens, [b'HTTP/1.1'])

    def test_that_parsing_by_byte_succeeds(self):
        buffer = b'HTTP/0.9\r\n'
        for idx in range(0, len(buffer)):
            self.parser.feed(buffer[idx:idx+1])
        self.assertEqual(self.parser.tokens, [b'HTTP/0.9'])

    def test_that_missing_dot_fails(self):
        with self.assertRaises(errors.MalformedHttpVersion):
            self.parser.feed(b'HTTP/1-1')

    def test_that_parse_fails_when_start_token_is_missing(self):
        with self.assertRaises(errors.MalformedHttpVersion):
            self.parser.feed(b'http/1.1')

    def test_that_parse_fails_with_non_digit_version(self):
        with self.assertRaises(errors.MalformedHttpVersion):
            self.parser.feed(b'HTTP/1.X')


class WhenSkippingSingleCharacter(unittest.TestCase):

    def setUp(self):
        super(WhenSkippingSingleCharacter, self).setUp()
        self.parser = parsing.ProtocolParser()

    def test_that_parsing_fails_when_character_is_missing(self):
        with self.assertRaises(errors.ProtocolParseException):
            method = self.parser._skip_single_character(b'1')
            method(b'2')

    def test_that_parsing_skips_matching_character(self):
        method = self.parser._skip_single_character(b'1')
        data = method(b'12')
        self.assertEqual(data, b'2')


class WhenParsingFixedString(unittest.TestCase):

    def setUp(self):
        super(WhenParsingFixedString, self).setUp()
        self.parser = parsing.ProtocolParser()
        self.parser._parse_stack = [self.parser.parse_fixed_string(b'fixed')]

    def test_that_parsing_consumes_matching_string(self):
        self.parser.feed(b'fix')
        self.assertEqual(self.parser.tokens, [])
        self.parser.feed(b'e')
        self.assertEqual(self.parser.tokens, [])
        remaining = self.parser.feed(b'd\n')
        self.assertEqual(self.parser.tokens, [b'fixed'])
        self.assertEqual(remaining, b'\n')

    def test_that_parsing_fails_with_mismatched_string(self):
        with self.assertRaises(errors.ProtocolParseException):
            self.parser.feed(b'mismatch')


class WhenParsingNumber(unittest.TestCase):

    def setUp(self):
        super(WhenParsingNumber, self).setUp()
        self.parser = parsing.ProtocolParser()

    def test_that_simple_number_is_parsed(self):
        remaining = self.parser.parse_number(b'1234')
        self.assertEqual(self.parser.tokens, [b'1234'])
        self.assertEqual(remaining, b'')

    def test_that_only_digits_are_parsed(self):
        remaining = self.parser.parse_number(b'1234abcd')
        self.assertEqual(self.parser.tokens, [b'1234'])
        self.assertEqual(remaining, b'abcd')


class WhenParsingHeaderValue(unittest.TestCase):

    def setUp(self):
        super(WhenParsingHeaderValue, self).setUp()
        self.parser = parsing.ProtocolParser()

    def test_that_leading_valid_characters_are_consumed(self):
        valid_characters = bytearray(range(0x21, 0x7E))
        valid_characters.extend(b' \t')
        random.shuffle(valid_characters)
        data = bytes(valid_characters)
        data += b'\x7F'

        remaining = self.parser.parse_header_value(data)
        self.assertEqual(remaining, b'\x7F')

    def test_that_missing_value_is_rejected(self):
        with self.assertRaises(errors.ProtocolParseException):
            self.parser.parse_header_value(b'\x7F')
