import asyncio
import os
import unittest


class AsyncioTestCase(unittest.TestCase):

    """
    Resembles Tornado's async test runner.

    .. code:: python

        class MyTestCase(AsyncioTestCase):
            def setUp(self):
                super(MyTestCase, self).setUp()
                self.start_server(coro_under_test)
                self.reader, self.writer = self.connect_to_server()

            def test_that_something_happens(self):
                self.writer.write(b'Hi there\r\n')
                response = self.run_async(self.reader.readline())
                self.assertEqual(response, b"What's up?\r\n")

    The :meth:`setUp` method creates a new event loop instance for
    the test run.  This also established/starts a timer that will
    abortively stop the event loop after a configurable number of
    seconds.

    .. attribute:: loop

       A handle to :class:`asyncio.events.AbstractEventLoop` instance
       created just for this test case.  This is created anew and
       assigned in :meth:`setUp`.

    .. attribute:: async_test_timeout

       The :class:`float` number of seconds to terminate the test after.
       You can set this explicitly before call :meth:`start_server` or
       set the :envvar:`ASYNC_TEST_TIMEOUT` environment variable.

    Test suites should include a ``setUp`` implementation that calls
    this class's :meth:`setUp` and then calls :meth:`start_server` with
    your connection handling callback.  Once the server is started, the
    following attributes are available to your test for communicating
    with the server instance.

    .. attribute:: server

       The cached result of calling :meth:`start_server`.  This is
       :data:`None` if ``start_server`` hasn't been called.

    .. attribute:: server_addr

       IP address that the started server was bound to.  This attribute
       is :data:`None` if :meth:`start_server` has not been called.

    .. attribute:: server_port

       Ephemeral TCP port number that the started server bound to.  This
       attribute is :data:`None` if :meth:`start_server` has not been
       called.

    """

    def setUp(self):
        """Creates the new event loop instance."""
        super(AsyncioTestCase, self).setUp()
        self.loop = asyncio.new_event_loop()
        self.loop.set_debug(True)
        self.async_test_timeout = float(
            os.environ.get('ASYNC_TEST_TIMEOUT', 0.5))

        self._timeout_handle = self.loop.call_later(self.async_test_timeout,
                                                    self.loop.stop)
        self.server = None
        self.server_addr, self.server_port = None, None

    def tearDown(self):
        """Close the server (if open) and event loop."""
        if self._timeout_handle:
            self._timeout_handle.cancel()
        if self.server:
            self.server.close()
            self.run_async(self.server.wait_closed())

        self.loop.stop()
        self.loop.close()
        super(AsyncioTestCase, self).tearDown()

    def start_server(self, client_connected_cb):
        """
        Create a running server to test against.

        :param client_connected_cb: function that is called when a
            new client connects.

        :return: the running server instance.  This is cached in the
            :attr:`server` attribute.
        :rtype: asyncio.events.AbstractServer

        This is a wrapped call to :func:`asyncio.start_server` run on
        the event loop.

        """
        coro = asyncio.start_server(client_connected_cb, '127.0.0.1', 0,
                                    loop=self.loop)
        self.server = self.run_async(coro)
        sock = self.server.sockets[0]
        info = sock.getsockname()
        self.server_addr, self.server_port = info[0], info[1]

        return self.server

    def connect_to_server(self):
        """
        Open a connect to the running server.

        :return: connected :class:`asyncio.streams.StreamReader`,
            :class:`asyncio.streams.StreamWriter` pair
        :rtype: tuple

        This is simply a call to :func:`asyncio.open_connection` run
        on the event loop.

        """
        coro = asyncio.open_connection(self.server_addr, self.server_port,
                                       loop=self.loop)
        return self.run_async(coro)

    def run_async(self, coro):
        """Run a co-routine on the event loop."""
        return self.loop.run_until_complete(coro)
