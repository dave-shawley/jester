import unittest

from jester import parsing


class WhenParsingTokens(unittest.TestCase):

    def setUp(self):
        super().setUp()
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
        super().setUp()
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
