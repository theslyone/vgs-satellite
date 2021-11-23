from threading import Thread, Event
from queue import Queue
from enum import Enum
from typing import List, Optional
import logging
import socket

from google.protobuf.json_format import MessageToDict, ParseDict

from .starlark_debugging_pb2 import (
    DebugEvent,
    DebugRequest,
    ListFramesRequest,
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


class UnableToConnectToDebugServer(LarkyDebuggerError):
    pass


class UsingStoppedDebugger(LarkyDebuggerError):
    pass


class LarkyDebugger:
    def __init__(self, debug_server_port: int = 7300):
        self._debug_server_port = debug_server_port
        self._completed = False
        self._debug_threads = {}

        self._sock = self._connect()
        self._stop_event: Event = Event()
        self._response_queue = Queue()
        self._reader_thread = Thread(target=self._reader_thread)
        self._reader_thread.start()

    @property
    def completed(self):
        return self._completed

    def stop(self):
        if self._completed:
            return

        if not self._stop_event.is_set():
            self._stop_event.set()

        if self._sock:
            self._sock.close()
            self._sock = None

        self._completed = True

    def set_breakpoints(self, breakpoints: List[dict]):
        if self.completed:
            raise UsingStoppedDebugger()

        req = DebugRequest()
        ParseDict({"set_breakpoints": {"breakpoint": breakpoints}}, req)
        self._send_request(req)
        self._response_queue.get()

    def get_threads(self) -> List[dict]:
        if self.completed:
            raise UsingStoppedDebugger()

        return list(self._debug_threads.values())

    def list_frames(self, thread_id: int) -> List[dict]:
        if self.completed:
            raise UsingStoppedDebugger()

        if thread_id not in self._debug_threads:
            raise UnknownThreadError()

        req = DebugRequest(list_frames=ListFramesRequest(thread_id=thread_id))
        self._send_request(req)
        event = self._response_queue.get()
        return event["list_frames"]["frame"]

    def continue_execution(self, thread_id: int, stepping: Stepping):
        if self.completed:
            raise UsingStoppedDebugger()

        if thread_id not in self._debug_threads:
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

        self._response_queue.get()

    def get_source(self, path: str) -> bytes:
        with open(path) as f:
            return f.read()

    def _send_request(self, request: DebugRequest):
        data = request.SerializeToString()
        self._put_size(len(data))
        self._sock.sendall(data)

    def _read_event(self) -> Optional[dict]:
        rsp_size = self._read_size()
        rsp_data = self._sock.recv(rsp_size)
        if not rsp_data:
            return None

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

    def _connect(self) -> socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(("localhost", self._debug_server_port))
        except ConnectionRefusedError:
            raise UnableToConnectToDebugServer()
        return sock

    def _put_size(self, size: int):
        while size >= 0x80:
            self._sock.send(((size & 0xFF) | 0x80).to_bytes(1, "little"))
            size >>= 7
        self._sock.send((size & 0xFF).to_bytes(1, "little"))

    def _read_size(self) -> int:
        size = 0
        shift = 0

        for i in range(10):
            byte = int.from_bytes(self._sock.recv(1), "little")
            if byte < 0x80:
                if i == 9 and byte > 1:
                    raise DataSizeOverflowError()
                return size | (byte << shift)
            size |= (byte & 0x7f) << shift
            shift += 7

        raise DataSizeOverflowError()

    def _reader_thread(self):
        while not self._stop_event.is_set():
            event = None

            try:
                event = self._read_event()
            except OSError:
                pass

            if event is None:
                break

            self._process_event(event)

        if not self._stop_event.is_set():
            self.stop()

    def _process_event(self, event: dict):
        if "thread_paused" in event:
            thread = event["thread_paused"]["thread"]
            thread_id = int(thread["id"])
            self._debug_threads[thread_id] = {**thread, "id": thread_id}
            return

        if "thread_continued" in event:
            del self._debug_threads[int(event["thread_continued"]["thread_id"])]
            return

        self._response_queue.put(event)
