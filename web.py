import asyncio
import collections
import re

from jester import parsing


class HTTPStatus(Exception):

    def __init__(self, status_code, reason):
        super(HTTPStatus, self).__init__(status_code, reason)
        self.status_code = status_code
        self.reason = reason


class Request(object):

    def __init__(self):
        self.method = None
        self.target = None
        self.http_version = None
        self.headers = {}
        self.body = None


class HTTPProtocol11(asyncio.Protocol):
    # probably destined for jester.protocol

    def __init__(self, *args, **kwargs):
        super(HTTPProtocol11, self).__init__(*args, **kwargs)
        self.transport = None
        self.parser = None
        self.request = None

    def connection_made(self, transport):
        self.transport = transport
        self.parser = parsing.ProtocolParser()
        self.parser.add_callback(
            parsing.ProtocolParser.request_line_received,
            self._create_request)
        self.parser.add_callback(
            parsing.ProtocolParser.header_parsed,
            self._add_header)

    def data_received(self, data):
        try:
            self.feed(data)
        except Exception as exc:
            self.transport.close()

    def eof_received(self):
        pass

    def connection_lost(self, exc):
        pass

    def _create_request(self, method, resource, version):
        self.request = Request()
        self.request.method = method
        self.request.url = resource
        self.request.http_version = version

    def _add_header(self, name, value):
        self.request.add_header(name, value)


class Application(object):
    # this will be implemented in jester.application

    def __init__(self):
        super(Application, self).__init__()
        self._routes = []

    def protocol_factory(self):
        protocol_handler = HTTPProtocol11()
        protocol_handler.add_callback(HTTPProtocol.request_line_received,
                                      self.start_request)
        return protocol_handler

    def start_request(self, method, target, http_version):
        for path_expr, method_list, handler in self._routes:
            match = path_expr.match(target)
            if match:
                if method in method_list:
                    return
                raise HTTPStatus(405, 'Method Not Allowed')
        else:
            raise HTTPStatus(404, 'Not Found')

    def add_request_handler(self, path_expr, methods=None):
        def wrapped(handler):
            self._routes.append(
                (re.compile(path_expr), methods or ['GET'], handler))
            return handler
        return wrapped


######
# This is what application code should resemble

application = Application()


@application.add_request_handler('/status')
def status_handler(request):
    pass


loop = asyncio.get_event_loop()
coro = loop.create_server(application.protocol_factory,
                          host='127.0.0.1', port=0)
server = loop.run_until_complete(coro)
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()
