import logging
from concurrent.futures import CancelledError, Future
from threading import Thread

import grpc
from google.protobuf.json_format import MessageToJson
from pylarky.model.http_message import HttpMessage

from .gateway_pb2_grpc import LarkyGatewayStub
from .gateway_pb2 import (
    ClientEvent,
    ErrorEvent,
    HttpMessage as HttpMessageProto,
    NewSessionEvent,
    ResultReadyEvent,
)


logger = logging.getLogger("satellite.debug.larky_gateway.client")


class LarkyGatewayClient:
    def __init__(self, gateway_host: str, gateway_port: int):
        self._endpoint = f"{gateway_host}:{gateway_port}"

    def new_session(
        self,
        session_id: str,
        org_id: str,
        vault: str,
        request_ready: Future,
        result_ready: Future,
    ):
        new_session_event = NewSessionEvent(
            session_id=session_id,
            org_id=org_id,
            vault=vault,
        )
        session_thread = Thread(
            target=self._session_thread,
            kwargs={
                "new_session_event": new_session_event,
                "request_ready": request_ready,
                "result_ready": result_ready,
            },
            daemon=True,  # This is a hack - should find a way to shutdown it gracefully
        )
        session_thread.start()

    def _session_thread(
        self,
        new_session_event: NewSessionEvent,
        request_ready: Future,
        result_ready: Future,
    ):
        try:
            logger.debug(f"Connecting to Larky gateway at {self._endpoint}")
            channel = grpc.insecure_channel(self._endpoint)
            stub = LarkyGatewayStub(channel)

            client_events = self._client_events_iterator(
                new_session_event=new_session_event,
                result_ready=result_ready,
            )

            for event in stub.DebugSession(client_events):
                logger.debug(f"Got event from LarkyGateway {MessageToJson(event)}")

                event_type = event.WhichOneof("payload")
                # Don't expect other events than proxy_request for now
                if event_type != "proxy_request":
                    raise Exception(f"Unexpected LarkyGateway event type: {event_type}")

                # Notifying that a request is ready
                request = event.proxy_request
                message = HttpMessage(
                    url=request.http_message.url,
                    data=request.http_message.data,
                    headers=request.http_message.headers,
                )
                request_ready.set_result(
                    {
                        "message": message,
                        "script": request.larky_script,
                    }
                )
        except Exception as exc:
            if not request_ready.done():
                request_ready.set_exception(exc)
            raise

    def _client_events_iterator(
        self,
        new_session_event: NewSessionEvent,
        result_ready: Future,
    ):
        logger.debug("Sending NewSeesion event to Larky gateway")
        yield ClientEvent(new_session=new_session_event)

        logger.debug("Waiting for the result before sending it to Larky gateway")
        try:
            message = result_ready.result()
        except CancelledError:
            logger.debug("Sending cancellation error to Larky gateway")
            yield ClientEvent(error=ErrorEvent(message="Cancelled debug session"))
        except Exception as exc:
            logger.debug("Sending error to Larky gateway")
            yield ClientEvent(error=ErrorEvent(message=str(exc)))
        else:
            logger.debug("Sending result to Larky gateway")
            message_proto = HttpMessageProto(
                url=message.url,
                data=message.data,
                headers=message.headers,
            )
            yield ClientEvent(result_ready=ResultReadyEvent(http_message=message_proto))
