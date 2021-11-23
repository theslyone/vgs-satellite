from dataclasses import dataclass
from enum import Enum
from typing import Dict, List
import logging
import socket

from google.protobuf.json_format import MessageToDict, ParseDict
from pylarky.eval.http_evaluator import HttpEvaluator
from pylarky.model.http_message import HttpMessage

from .starlark_debugging_pb2 import (
    Breakpoint,
    DebugEvent,
    DebugRequest,
    ListFramesRequest,
    Location,
    SetBreakpointsRequest,
)


logger = logging.getLogger(__file__)


class Stepping(str, Enum):
    NONE = "NONE"
    INTO = "INTO"
    OVER = "OVER"
    OUT = "OUT"


class LarkyDebuggerError(Exception):
    pass


class UnknownThreadError(LarkyDebuggerError):
    pass


class DataSizeOverflowError(LarkyDebuggerError):
    pass


class LarkyDebugger:
    @dataclass
    class State:
        debug_threads: Dict = None
        sock: socket = None

    def __init__(self, debug_server_port: int = 7300):
        self._debug_server_port = debug_server_port
        self._state = None

    @property
    def started(self):
        return self._state is not None

    def start(self, code: str, http_message: HttpMessage) -> dict:
        if self.started:
            return

        self._state = self.State(debug_threads={})
        self._connect()
        self._read_response(max_events=1)

    def stop(self):
        if not self.started:
            return
        self._state.sock.close()
        self._state = None

    def set_breakpoints(self, breakpoints: List[dict]):
        req = DebugRequest()
        ParseDict({"set_breakpoints": {"breakpoint": breakpoints}}, req)
        self._send_request(req)
        self._read_response()

    def get_threads(self) -> List[dict]:
        return list(self._state.debug_threads.values())

    def list_frames(self, thread_id: int) -> List[dict]:
        if thread_id not in self._state.debug_threads:
            raise UnknownThreadError()

        req = DebugRequest(list_frames=ListFramesRequest(thread_id=thread_id))
        self._send_request(req)
        event = self._read_response()
        return event["list_frames"]["frame"]

    def continue_execution(self, thread_id: int, stepping: Stepping):
        if thread_id not in self._state.debug_threads:
            raise UnknownThreadError()

        req = DebugRequest()
        ParseDict(
            {
                "continue_execution": {
                    "thread_id": thread_id,
                    "stepping": stepping.value,
                },
            },
            req,
        )
        self._send_request(req)

        self._read_response()

    def get_source(self, path: str) -> bytes:
        with open(path) as f:
            return f.read()

    def _send_request(self, request: DebugRequest):
        data = request.SerializeToString()
        self._put_size(len(data))
        self._state.sock.sendall(data)

    def _read_response(self, max_events: int = None) -> dict:
        total_events = 0
        while max_events is None or total_events < max_events:
            event = self._read_event()
            if "thread_paused" in event:
                thread = event["thread_paused"]["thread"]
                thread_id = int(thread["id"])
                self._state.debug_threads[thread_id] = {**thread, "id": thread_id}
            elif "thread_continued" in event:
                del self._state.debug_threads[
                    int(event["thread_continued"]["thread_id"])
                ]
            else:
                return event

            total_events += 1

    def _read_event(self) -> dict:
        rsp_size = self._read_size()
        rsp_data = self._state.sock.recv(rsp_size)
        event = DebugEvent()
        event.ParseFromString(rsp_data)
        event_dict = MessageToDict(event, preserving_proto_field_name=True)
        print(f"Got event from debug server: {event_dict}")  # TODO: remove after POC

        error = event_dict.get("error")
        if error:
            raise LarkyDebuggerError(
                f"Got error from the debug server: {error['message']}"
            )

        return event_dict

    def _connect(self):
        self._state.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._state.sock.connect(("localhost", self._debug_server_port))

    def _put_size(self, size: int):
        while size >= 0x80:
            self._state.sock.send(((size & 0xFF) | 0x80).to_bytes(1, "little"))
            size >>= 7
        self._state.sock.send((size & 0xFF).to_bytes(1, "little"))

    def _read_size(self) -> int:
        size = 0
        shift = 0

        for i in range(10):
            byte = int.from_bytes(self._state.sock.recv(1), "little")
            if byte < 0x80:
                if i == 9 and byte > 1:
                    raise DataSizeOverflowError()
                return size | (byte << shift)
            size |= (byte & 0x7f) << shift
            shift += 7

        raise DataSizeOverflowError()
