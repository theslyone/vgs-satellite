import asyncio
import logging
import signal
from functools import partial
from pathlib import Path

from tornado import autoreload
from tornado.ioloop import IOLoop
from tornado.web import Application, StaticFileHandler

from .config import SatelliteConfig
from .controller import (
    BaseHandler,
    alias_handlers,
    audit_logs_handler,
    debug_handlers,
    flow_handlers,
)
from .controller.exceptions import NotFoundError
from .controller.route_handlers import RouteHandler, RoutesHandler
from .controller.websocket_connection import ClientConnection
from .proxy.manager import ProxyManager
from .spec import build_openapi_spec
from .debug.debug_manager import DebugManager


logger = logging.getLogger()


class IndexHandler(BaseHandler):
    def head(self):
        self.finish_empty_ok()


class SpecJSONHandler(BaseHandler):
    def get(self):
        self.finish(self.application.spec.to_dict())


class SpecYAMLHandler(BaseHandler):
    def get(self):
        self.set_header('Content-Type', 'text/yaml')
        self.finish(self.application.spec.to_yaml())


class NotFoundHandler(BaseHandler):
    def prepare(self) -> None:
        raise NotFoundError(f'Unknown URI: {self.request.uri}')

    def check_xsrf_cookie(self) -> None:
        # POSTs to an ErrorHandler don't actually have side effects,
        # so we don't need to check the xsrf token.  This allows POSTs
        # to the wrong url to return a 404 instead of 403.
        pass


class WebApplication(Application):
    def __init__(self, config: SatelliteConfig = None):
        self.config = config or SatelliteConfig()

        api_handlers = [
            (r'/aliases', alias_handlers.AliasesHandler),
            (r'/aliases/(?P<public_alias>.+)', alias_handlers.AliasHandler),
            (r'/flows', flow_handlers.Flows),
            (r'/flows/(?P<flow_id>[^/]+)', flow_handlers.FlowHandler),
            (r'/flows/(?P<flow_id>[^/]+)/duplicate', flow_handlers.DuplicateFlow),
            (r'/flows/(?P<flow_id>[^/]+)/replay', flow_handlers.ReplayFlow),
            (r'/logs/(?P<flow_id>[^/]+)', audit_logs_handler.AuditLogsHandler),
            (r'/route', RoutesHandler),
            (r'/route/(?P<route_id>[^/]+)', RouteHandler),
            (r'/debug', debug_handlers.SessionsHandler),
            (r'/debug/(?P<session_id>[^/]+)', debug_handlers.SessionHandler),
            (
                r'/debug/(?P<session_id>[^/]+)/breakpoints',
                debug_handlers.BreakpointsHandler,
            ),
            (r'/debug/(?P<session_id>[^/]+)/threads', debug_handlers.ThreadsHandler),
            (
                r'/debug/(?P<session_id>[^/]+)/threads/(?P<thread_id>\d+)/frames',
                debug_handlers.FramesHandler,
            ),
            (
                r'/debug/(?P<session_id>[^/]+)/threads/(?P<thread_id>\d+)/continue',
                debug_handlers.ThreadContinueHandler,
            ),
            (
                r'/debug/(?P<session_id>[^/]+)/threads/(?P<thread_id>\d+)/pause',
                debug_handlers.ThreadPauseHandler,
            ),
            (r'/debug/source(?P<path>/.+)', debug_handlers.GetSourceHandler),
        ]

        self.spec = build_openapi_spec(api_handlers)

        super().__init__(
            handlers=[
                *api_handlers,
                (r'/', IndexHandler),
                (r'/flows.json', flow_handlers.Flows),
                (r'/spec.json', SpecJSONHandler),
                (r'/spec.yaml', SpecYAMLHandler),
                (r'/updates', ClientConnection),
                (
                    r'/apidocs/?(.*)',
                    StaticFileHandler,
                    {
                        'default_filename': 'index.html',
                        'path': Path(__file__).parent / 'static' / 'swagger',
                    },
                ),
            ],
            debug=self.config.debug,
            default_handler_class=NotFoundHandler,
        )

        self._should_exit = False

        self.proxy_manager = ProxyManager(
            forward_proxy_port=self.config.forward_proxy_port,
            reverse_proxy_port=self.config.reverse_proxy_port,
            event_handler=partial(
                self._proxy_event_handler,
                loop=asyncio.get_event_loop(),
            ),
        )

        self.debug_manager = DebugManager(
            larky_gateway_host=config.larky_gateway_host,
            larky_gateway_port=config.larky_gateway_port,
            larky_debug_server_port=config.larky_debug_server_port,
        )

    def _proxy_event_handler(self, event, loop):
        asyncio.run_coroutine_threadsafe(
            ClientConnection.process_proxy_event(event),
            loop,
        )

    def start(self):
        loop = asyncio.get_event_loop()
        for sig in [signal.SIGINT, signal.SIGTERM]:
            loop.add_signal_handler(sig, self.stop)

        if self.settings.get('autoreload'):
            autoreload.add_reload_hook(self.proxy_manager.stop)

        self.proxy_manager.start()

        self.listen(self.config.web_server_port)
        logger.info(f'Web server listening at {self.config.web_server_port} port.')
        IOLoop.current().start()

    def stop(self):
        if self._should_exit:
            return
        self._should_exit = True
        self.proxy_manager.stop()
        self.debug_manager.stop()
        IOLoop.current().stop()
