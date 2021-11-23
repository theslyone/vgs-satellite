import uuid
from enum import Enum

from .larky_debugger import LarkyDebugger


class DebugSessionState(Enum):
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"


class DebugSession:
    def __init__(self):
        self._id = str(uuid.uuid4())
        self._debugger = None

    @property
    def id(self) -> str:
        return self._id

    @property
    def state(self) -> DebugSessionState:
        if self.debugger is None:
            return DebugSessionState.INITIALIZING
        if self.debugger.completed:
            return DebugSessionState.COMPLETED
        return DebugSessionState.RUNNING

    @property
    def debugger(self):
        return self._debugger

    def start(self):
        if self.state == DebugSessionState.RUNNING:
            return
        self._debugger = LarkyDebugger()

    def stop(self):
        if self.state == DebugSessionState.COMPLETED:
            return

        if self._debugger:
            self._debugger.stop()
