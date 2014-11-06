jester
======

|Version| |Downloads| |Status| |License|

Another HTTP handler over the Python `asyncio`_ module.

Wait... Why? What??
-------------------
This isn't `Tornado`_ or an attempt to re-implement it.  I've been
pining for a simple async HTTP handler.  Tornado is close to what
I want, but I don't want the other baggage that it brings to the
table.  I usually work in JSON-backed APIs so I don't need or want
anything that resembles HTML, CSRF protection, or templating.  If
you do want that, then certainly check out `Tornado`_.  It excels
at what it does.  I just don't need all of it.

I also don't care for support SSL directly in Python.  You really
should be terminating SSL using something like Apache httpd or
nginx.  Let compiled code do the really heavy lifting and let
Python work where it shines -- in the request handling.

Mainly, I just want something that implements HTTP/1.1 in a way
that caters to API developers.  That means making it easy to get
at all of the nice and shiny bits that the protocol gives us and
not stepping in the way in every inopportune moment.  I also value
your thoughts and creativity so I'm going to try hard and not be
overly opinionated.  If you want to write your request handlers
as bare functions, go for it.  If you like writing OOP based code,
then I'm game.

Ok... Where?
------------

+---------------+-------------------------------------------------+
| Source        | https://github.com/dave-shawley/jester          |
+---------------+-------------------------------------------------+
| Status        | https://travis-ci.org/dave-shawley/jester       |
+---------------+-------------------------------------------------+
| Download      | https://pypi.python.org/pypi/jester             |
+---------------+-------------------------------------------------+
| Documentation | http://jester.readthedocs.org/en/latest         |
+---------------+-------------------------------------------------+
| Issues        | https://github.com/dave-shawley/jester          |
+---------------+-------------------------------------------------+

.. _asyncio: https://docs.python.org/3.4/library/asyncio.html
.. _tornado: https://tornadoweb.org

.. |Version| image:: https://pypip.in/version/jester/badge.svg
   :target: https://pypi.python.org/pypi/jester
.. |Downloads| image:: https://pypip.in/d/jester/badge.svg
   :target: https://pypi.python.org/pypi/jester
.. |Status| image:: https://travis-ci.org/dave-shawley/jester.svg
   :target: https://travis-ci.org/dave-shawley/jester
.. |License| image:: https://pypip.in/license/jester/badge.svg
   :target: https://jester.readthedocs.org/
