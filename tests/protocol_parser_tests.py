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

    def test_that_parsing_version_succeeds(self):
        buffer = b'HTTP/1.1\r\n'
        buffer = self.parser.parse_version(buffer)
        self.assertEqual(buffer, b'\r\n')
        self.assertEqual(self.parser.tokens, [b'HTTP/1.1'])

    def test_that_parsing_by_byte_succeeds(self):
        remaining = None
        buffer = b'HTTP/0.9'
        for ch in buffer.decode():
            remaining = self.parser.parse_version(ch.encode())
        self.assertEqual(remaining, b'')
        self.assertEqual(self.parser.tokens, [b'HTTP/0.9'])

    def test_that_missing_dot_fails(self):
        with self.assertRaises(errors.MalformedHttpVersion):
            self.parser.parse_version(b'HTTP/1-1')

    def test_that_parse_fails_when_start_token_is_missing(self):
        with self.assertRaises(errors.MalformedHttpVersion):
            self.parser.parse_version(b'http/1.1')


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
        self.parser._parse_stack = [self.parser._parse_fixed_string(b'fixed')]

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
