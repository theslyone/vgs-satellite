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
        self._sessions[session.id] = session
        session.start()  # TODO: start when a request is available

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

    def stop(self, session_id: Optional[str] = None):
        if session_id:
            self.delete_session(session_id)

        for session_id in list(self._sessions):
            self.delete_session(session_id)
