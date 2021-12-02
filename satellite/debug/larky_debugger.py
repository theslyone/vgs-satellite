import logging
import os
import os.path
import re
import socket
import time
from concurrent.futures import Future, TimeoutError
from enum import Enum
from functools import wraps
from queue import Queue
from threading import Event, Lock, Thread
from typing import Callable, List, Optional

from google.protobuf.json_format import MessageToDict, ParseDict
from pylarky.eval.http_evaluator import HttpEvaluator
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
        script: str,
        http_message: HttpMessage,
        result_future: Future,
        debug_server_port: int = 7300,
    ):
        self._completed: bool = False
        self._result_future = result_future
        self._debug_threads = {}
        self._stop_event = Event()
        self._response_queue = Queue()
<<<<<<< HEAD
        self._reader_thread = Thread(target=self._reader_thread_target)
=======
        self._lock = Lock()
>>>>>>> 228847e (Use pylarky.)

        self._evaluator_thread = Thread(
            target=self._evaluator_thread_target,
            kwargs={
                "script": script,
                "http_message": http_message,
                "debug_port": debug_server_port,
            },
            name="LakryEvaluatorThread",
            daemon=True,  # There is no way to interrupt the evaluator gracefully
        )
        self._evaluator_thread.start()

        self._sock = self._connect(debug_server_port)

        self._reader_thread = Thread(
            target=self._reader_thread_target,
            name="LarkyDebugServerEventsReaderThread",
        )
        self._reader_thread.start()

        # POC hack!!!
        self._skip()

    @property
    def completed(self) -> bool:
        return self._completed

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

        if self._sock is not None:
            self._sock.close()
            self._sock = None

        self._finalize()

        self._completed = True

    # POC hack!!!
    def _skip(self):
        latest_ts = 0
        script_path = None
        line_number = None
        for name in os.listdir("/tmp"):
            match = re.fullmatch(r"merge\d+.star", name)
            if match is not None:
                path = f"/tmp/{name}"
                ts = os.path.getmtime(path)
                if latest_ts < ts:
                    with open(path) as f:
                        for n, l in enumerate(f.readlines()):
                            if "start script" in l:
                                break
                    latest_ts = ts
                    script_path = path
                    line_number = n

        self.set_breakpoints([
            {"location": {"path": script_path, "line_number": line_number}}
        ])
        self._request({"start_debugging": {}})

    def _finalize(
        self,
        result: Optional[HttpMessage] = None,
        error: Optional[Exception] = None,
    ):
        logger.debug(f"Finallizing debugging with {result=} and {error=}")

        if self._result_future.done():
            return

        if result is None and error is None:
            # Before cancelling let's wait for a bit
            try:
                self._result_future.result(1)
            except TimeoutError:
                pass

            with self._lock:
                if not self._result_future.done():
                    self._result_future.cancel()

            return

        with self._lock:
            if not self._result_future.done():
                if result is not None:
                    self._result_future.set_result(result)
                else:
                    self._result_future.set_exception(error)

    def _request(self, request: dict) -> Optional[dict]:
        # Performing request
        request_proto = DebugRequest()
        ParseDict(request, request_proto)
        data = request_proto.SerializeToString()
        put_uint_to_sock(len(data), self._sock)
        self._sock.sendall(data)

        # Reading respone
        event = self._response_queue.get()
        if event is None:
            return None

        error = event.get("error")
        if error:
            raise LarkyDebuggerError(
                f"Got error from the debug server: {error['message']}"
            )

        return event

    def _read_event(self) -> Optional[dict]:
        size = read_uint_from_sock(self._sock)
        rsp_data = b''
        while size > 0:
            data = self._sock.recv(size)
            rsp_data += data
            size -= len(data)

        if not rsp_data:
            return None

        event = DebugEvent()
        try:
            event.ParseFromString(rsp_data)
        except Exception:
            logger.error(f"Unable to parse event data from debug server: {rsp_data}")
            raise

        return MessageToDict(event, preserving_proto_field_name=True)

    def _connect(self, debug_server_port: int) -> socket.socket:
        endpoint = ("localhost", debug_server_port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        attempts = 5

<<<<<<< HEAD
=======
        while attempts > 0:
            try:
                logger.debug(f"Connecting to the debug server {endpoint}")
                sock.connect(endpoint)
                logger.debug("Successfully connected to the larky debug server.")
                return sock
            except ConnectionError:
                attempts -= 1
                time.sleep(1)

        raise UnableToConnectToDebugServer(
            f"Unable to connect to the debug server {endpoint}"
        )

>>>>>>> 228847e (Use pylarky.)
    def _reader_thread_target(self):
        while not self._stop_event.is_set():
            event = None

            try:
                event = self._read_event()
            except OSError:
                pass
            except Exception as exc:
                logger.exception("Error during reading event from the debug server")
                self._finalize(error=exc)

            if event is None:
                break

            logging.debug(f"Got event from debug server: {event}")

            self._process_event(event)

        self._response_queue.put(None)

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

    def _evaluator_thread_target(
        self,
        script: str,
        http_message: HttpMessage,
        debug_port: int,
    ):
        try:
            evaluator = HttpEvaluator(script)
            result = evaluator.evaluate(
                http_message=http_message,
                debug=True,
                debug_port=debug_port,
            )
            self._finalize(result=result)
        except Exception as exc:
            logger.exception("Unable to execute larky script")
            self._finalize(error=exc)
