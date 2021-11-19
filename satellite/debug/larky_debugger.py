import logging
import socket
from json import loads
from threading import Thread
from typing import List

from google.protobuf.json_format import MessageToDict
from pylarky.eval.http_evaluator import HttpEvaluator
from pylarky.model.http_message import HttpMessage

from .starlark_debugging_pb2 import (
    DebugEvent,
    DebugRequest,
    ListFramesRequest,
    ListFramesResponse,
    StartDebuggingRequest,
    PauseThreadRequest,
)


logger = logging.getLogger(__file__)


class LarkyDebuggerError(Exception):
    pass


class DataSizeOverflowError(LarkyDebuggerError):
    pass


class LarkyDebugger:
    def __init__(self, debug_server_port: int = 7300):
        self._debug_server_port = debug_server_port
        self._larky_thread: Thread = None
        self._result: HttpMessage = None
        self._current_debug_thread = None
        self._sock = None

    def start(self, code: str, http_message: HttpMessage) -> dict:
        # self._larky_thread = Thread(
        #     target=self._larky_thread,
        #     kwargs={"code": code, "http_message": http_message},
        # )
        # self._larky_thread.start()

        self._connect()
        self._current_debug_thread = self._get_paused_thread()

    def get_current_thread(self) -> dict:
        return self._current_debug_thread

    def list_frames(self, thread_id: int) -> List[dict]:
        req = DebugRequest(list_frames=ListFramesRequest(thread_id=thread_id))
        self._send_request(req)
        event = self._read_event()
        return event["list_frames"]["frame"]

    def get_source(self, path: str) -> bytes:
        with open(path) as f:
            return f.read()

    def _get_paused_thread(self):
        event = self._read_event()
        thread = event["thread_paused"]["thread"]
        return {**thread, "id": int(thread["id"])}

    def _send_request(self, request: DebugRequest):
        data = request.SerializeToString()
        self._put_size(len(data))
        self._sock.sendall(data)

    def _read_event(self) -> dict:
        rsp_size = self._read_size()
        rsp_data = self._sock.recv(rsp_size)
        event = DebugEvent()
        event.ParseFromString(rsp_data)
        event_dict = MessageToDict(event, preserving_proto_field_name=True)
        print(f"Got event from debug server: {event_dict}")
        return event_dict

    def _connect(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect(("localhost", self._debug_server_port))

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

    def _larky_thread(self, code: str, http_message: HttpMessage):
        evaluator = HttpEvaluator(code, debug_server_port=self._debug_server_port)
        self._result = evaluator.evaluate(http_message, debug=True)
