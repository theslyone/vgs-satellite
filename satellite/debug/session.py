import logging
import uuid
from concurrent.futures import Future
from enum import Enum

from .larky_debugger import LarkyDebugger
from .larky_gateway.client import LarkyGatewayClient

logger = logging.getLogger(__file__)


class DebugSessionState(Enum):
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class DebugSession:
    def __init__(
        self,
        larky_debug_server_port: int,
        larky_gateway_client: LarkyGatewayClient,
        org_id: str,
        vault: str,
    ):
        self._id = str(uuid.uuid4())
        self._org_id = org_id
        self._vault = vault

        self._larky_gateway_client = larky_gateway_client
        self._larky_debug_server_port = larky_debug_server_port

        self._request_ready_future = Future()
        self._request_ready_future.add_done_callback(self._request_ready_callback)

        self._result_ready_future = Future()

        self._larky_gateway_client.new_session(
            session_id=self._id,
            org_id=self._org_id,
            vault=self._vault,
            request_ready=self._request_ready_future,
            result_ready=self._result_ready_future,
        )

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

    def _request_ready_callback(self, future: Future):
        request = future.result()
        self._debugger = LarkyDebugger(
            larky_script=request["script"],
            message=request["message"],
            result_future=self._result_ready_future,
            debug_server_port=self._larky_debug_server_port,
        )
