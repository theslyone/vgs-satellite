from typing import Dict, Optional

from .session import DebugSession


class DebugManagerError(Exception):
    pass


class DebugSessionLimitExceeded(DebugManagerError):
    pass


class DebugSessionNotFound(DebugManagerError):
    pass


class DebugManager:
    def __init__(self) -> None:
        self._sessions: Dict[str, DebugSession] = {}

    def new_session(self, org_id: str, vault: str) -> DebugSession:
        if self._sessions:
            raise DebugSessionLimitExceeded()

        session = DebugSession()
        session.start()  # TODO: start when a request is available
        self._sessions[session.id] = session

        return session

    def get_session(self, session_id: str) -> DebugSession:
        session = self._sessions.get(session_id)
        if session:
            return session
        raise DebugSessionNotFound()

    def stop(self, session_id: Optional[str] = None):
        if session_id:
            session = self.get_session(session_id)
            session.stop()
            del self._sessions[session_id]
            return

        for session in self._sessions.values():
            session.stop()

        self._sessions = {}
