from typing import Dict

from .larky_gateway.client import LarkyGatewayClient
from .session import DebugSession


class DebugManagerError(Exception):
    pass


class DebugSessionLimitExceeded(DebugManagerError):
    pass


class DebugSessionNotFound(DebugManagerError):
    pass


class DebugManager:
    def __init__(
        self,
        larky_gateway_host: str,
        larky_gateway_port: int,
        larky_debug_server_host: str,
        larky_debug_server_port: int,
    ) -> None:
        self._larky_gateway_client = LarkyGatewayClient(
            gateway_host=larky_gateway_host,
            gateway_port=larky_gateway_port,
        )
        self._larky_debug_server_host = larky_debug_server_host
        self._larky_debug_server_port = larky_debug_server_port
        self._sessions: Dict[str, DebugSession] = {}

    def new_session(self, org_id: str, vault: str) -> DebugSession:
        if self._sessions:
            raise DebugSessionLimitExceeded()

        session = DebugSession(
            larky_debug_server_host=self._larky_debug_server_host,
            larky_debug_server_port=self._larky_debug_server_port,
            larky_gateway_client=self._larky_gateway_client,
            org_id=org_id,
            vault=vault,
        )
        self._sessions[session.id] = session

        return session

    def get_session(self, session_id: str) -> DebugSession:
        session = self._sessions.get(session_id)
        if session:
            return session
        raise DebugSessionNotFound()

    def delete_session(self, session_id: str):
        session = self._sessions.get(session_id)
        if not session:
            raise DebugSessionNotFound()

        session.stop()

        del self._sessions[session.id]

    def delete_all_sessions(self):
        for session_id in list(self._sessions):
            self.delete_session(session_id)

    def stop(self):
        self.delete_all_sessions()
