"""
Things that make Jester frown.

This module defines the exceptions that Jester generates as
well as those that users can generate to control what the stack
does.

"""


class PlatformException(Exception):
    """Root of all Jester generated exceptions."""


class ProtocolParseException(PlatformException):
    """Failed to parse bytes as a valid HTTP request."""
    def __init__(self, lexeme):
        super(ProtocolParseException, self).__init__()
        self.lexeme = lexeme


class MalformedHttpVersion(ProtocolParseException):
    """The parsed HTTP version was malformed."""
