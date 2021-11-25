import logging
import uuid
from concurrent.futures import Future
from enum import Enum
from threading import Thread

import grpc
from google.protobuf.json_format import MessageToJson
from pylarky.model.http_message import HttpMessage

from .larky_debugger import LarkyDebugger
from .larky_gateway.gateway_pb2_grpc import LarkyGatewayStub
from .larky_gateway.gateway_pb2 import (
    ClientEvent,
    NewSessionEvent,
    ResultReadyEvent,
    HttpMessage as HttpMessageProto,
)


logger = logging.getLogger(__file__)


class DebugSessionState(Enum):
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class DebugSession:
    def __init__(
        self,
        larky_gateway_host: str,
        larky_gateway_port: int,
        larky_debug_server_port: int,
        org_id: str,
        vault: str,
    ):
        self._id = str(uuid.uuid4())
        self._org_id = org_id
        self._vault = vault

        self._larky_gateway_host = larky_gateway_host
        self._larky_gateway_port = larky_gateway_port
        self._larky_debug_server_port = larky_debug_server_port

        self._result_future = Future()
        self._gateway_client_thread = Thread(
            target=self._gateway_client,
            daemon=True,  # This is a hack - should find a way to shutdown it gracefully
        )
        self._gateway_client_thread.start()

        self._error = None

        self._debugger = None

    @property
    def id(self) -> str:
        return self._id

    @property
    def state(self) -> DebugSessionState:
        if self._error is not None:
            return DebugSessionState.ERROR
        if self.debugger is None:
            return DebugSessionState.INITIALIZING
        if self.debugger.completed:
            return DebugSessionState.COMPLETED
        return DebugSessionState.RUNNING

    @property
    def error(self) -> str:
        return self._error

    @property
    def debugger(self):
        return self._debugger

    def start(self):
        if self.state == DebugSessionState.RUNNING:
            return
        self._debugger = LarkyDebugger(debug_server_port=self._larky_debug_server_port)

    def stop(self):
        if self.state == DebugSessionState.COMPLETED:
            return

        if self._debugger:
            self._debugger.stop()

    def _gateway_client_events(self):
        logger.debug("Sending NewSeesion event to Larky gateway")
        yield ClientEvent(new_session=NewSessionEvent(
            session_id=self.id,
            org_id=self._org_id,
            vault=self._vault,
        ))

        logger.debug("Waiting for the result before sending it to Larky gateway")
        message = self._result_future.result()

        logger.debug("Sending result to Larky gateway")
        message_proto = HttpMessageProto(
            url=message.url,
            data=message.data,
            headers=message.headers,
        )
        yield ClientEvent(result_ready=ResultReadyEvent(http_message=message_proto))

    def _gateway_client(self):
        try:
            endpoint = f"{self._larky_gateway_host}:{self._larky_gateway_port}"
            logger.debug(f"Connecting to Larky gateway at {endpoint}")
            channel = grpc.insecure_channel(endpoint)
            stub = LarkyGatewayStub(channel)

            for event in stub.DebugSession(self._gateway_client_events()):
                logger.debug(
                    f"Got event from LarkyGateway {MessageToJson(event)}"
                )

                event_type = event.WhichOneof("payload")
                if event_type != "proxy_request":
                    raise Exception(f"Unexpected LarkyGateway event type: {event_type}")

                request = event.proxy_request
                message = HttpMessage(
                    url=request.http_message.url,
                    data=request.http_message.data,
                    headers=request.http_message.headers,
                )
                self._debugger = LarkyDebugger(
                    larky_script=request.larky_script,
                    message=message,
                    result_future=self._result_future,
                    debug_server_port=self._larky_debug_server_port,
                )

        except Exception:
            self._error = "Larky gate way error"
            raise
