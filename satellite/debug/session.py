import uuid

from .larky_debugger import LarkyDebugger


class DebugSession:
    def __init__(self):
        self._id = str(uuid.uuid4())
        self._started = False
        self._debugger = LarkyDebugger()

    @property
    def id(self) -> str:
        return self._id

    @property
    def started(self):
        return self._started

    @property
    def debugger(self):
        return self._debugger

    def start(self):
        if self._started:
            return
        self._debugger.start("XXX", "YYY")  # POC
        self._started = True

    def stop(self):
        if not self._started:
            return
        self._debugger.stop()
        self._started = False
