Jester Internals
================

Protocol Parsing
----------------
Jester uses a rather simple string-based iterative parser to parse HTTP
messages.  Instead of implementing a full lexer/parser combination or
using regular expressions, most of the parsing is done by consuming
bytes that are valid for the current production until an inappropriate
byte is encountered or the production is complete.  Then it moves on to
the next production.  The primary implementation class is the
:class:`jester.parsing.ProtocolParser` which contains methods that take
the stream of bytes and return the remaining (rightmost) bytes.  If the
production has terminated, then it returns bytes.  Otherwise, the method
returns a *falsy* value.

.. autoclass:: jester.parsing.ProtocolParser
   :members:
   :private-members:
