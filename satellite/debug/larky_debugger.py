import logging
import socket
from concurrent.futures import Future
from enum import Enum
from functools import wraps
from queue import Queue
from threading import Thread, Event
from typing import Callable, List, Optional

from google.protobuf.json_format import MessageToDict, ParseDict
from pylarky.model.http_message import HttpMessage

from .starlark_debugging_pb2 import DebugEvent, DebugRequest
from .utils import read_uint_from_sock, put_uint_to_sock


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


def requires_running_debugger(debugger_method: Callable):
    @wraps(debugger_method)
    def wrapper(debugger, *args, **kwargs):
        if debugger.completed:
            raise UsingStoppedDebugger()

        return debugger_method(debugger, *args, **kwargs)

    return wrapper


class LarkyDebugger:
    def __init__(
        self,
        larky_script: str,
        message: HttpMessage,
        result_future: Optional[Future] = None,
        debug_server_port: int = 7300,
        debug_server_host: str = "localhost",
    ):
        self._completed = False
        self._result = None
        self._result_future = result_future

        self._larky_script = larky_script
        self._request_message = message

        self._debug_server_host = debug_server_host
        self._debug_server_port = debug_server_port
        self._debug_threads = {}

        self._sock = None

        self._stop_event = Event()
        self._response_queue = Queue()
        self._reader_thread = Thread(target=self._reader_thread)

        self._connect()
        self._reader_thread.start()

    @property
    def completed(self):
        return self._completed

    @property
    def result(self):
        return self._result

    @requires_running_debugger
    def set_breakpoints(self, breakpoints: List[dict]):
        self._request({"set_breakpoints": {"breakpoint": breakpoints}})

    @requires_running_debugger
    def get_threads(self) -> List[dict]:
        return list(self._debug_threads.values())

    @requires_running_debugger
    def list_frames(self, thread_id: int) -> List[dict]:
        if thread_id not in self._debug_threads:
            raise UnknownThreadError()

        event = self._request({"list_frames": {"thread_id": thread_id}})
        return event["list_frames"]["frame"]

    @requires_running_debugger
    def pause_thread(self, thread_id: Optional[int] = 0):
        if thread_id in self._debug_threads:
            return

        self._request({"pause_thread": {"thread_id": thread_id}})

    @requires_running_debugger
    def continue_execution(
        self,
        thread_id: Optional[int] = 0,
        stepping: Optional[Stepping] = None,
    ):
        if thread_id != 0 and thread_id not in self._debug_threads:
            raise UnknownThreadError()

        self._request(
            {
                "continue_execution": {
                    "thread_id": thread_id,
                    "stepping": stepping.value,
                },
            }
        )

    def stop(self):
        if self._completed:
            return

        if not self._stop_event.is_set():
            self._stop_event.set()

        if self._sock:
            self._sock.close()
            self._sock = None

        if self._result_future is not None and not self._result_future.done():
            self._result_future.cancel()

        self._completed = True

    def _request(self, request: dict) -> dict:
        # Performing request
        request_proto = DebugRequest()
        ParseDict(request, request_proto)
        data = request_proto.SerializeToString()
        put_uint_to_sock(len(data), self._sock)
        self._sock.sendall(data)

        # Reading respone
        event = self._response_queue.get()

        error = event.get("error")
        if error:
            raise LarkyDebuggerError(
                f"Got error from the debug server: {error['message']}"
            )

        return event

    def _read_event(self) -> Optional[dict]:
        rsp_size = read_uint_from_sock(self._sock)
        rsp_data = self._sock.recv(rsp_size)
        if not rsp_data:
            return None

        event = DebugEvent()
        try:
            event.ParseFromString(rsp_data)
        except Exception:
            logger.error(f"Unable to parse event data from debug server: {rsp_data}")
            raise

        return MessageToDict(event, preserving_proto_field_name=True)

    def _connect(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            endpoint = (self._debug_server_host, self._debug_server_port)
            logger.debug(f"Connecting to the debug server {endpoint}")
            self._sock.connect(endpoint)
        except ConnectionRefusedError:
            raise UnableToConnectToDebugServer()

    def _reader_thread(self):
        while not self._stop_event.is_set():
            event = None

            try:
                event = self._read_event()
            except OSError:
                pass
            except Exception:
                logger.exception("Error during reading event from the debug server")

            if event is None:
                self._set_result(self._request_message)  # Remove after larky is ready
                break

            logging.debug(f"Got event from debug server: {event}")

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

    def _set_result(self, result: HttpMessage):
        if self._result is not None:
            return
        self._result = result
        if self._result_future is not None:
            self._result_future.set_result(result)
