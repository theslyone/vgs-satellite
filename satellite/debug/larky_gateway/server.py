import logging
from concurrent.futures import ThreadPoolExecutor

import click
from google.protobuf.json_format import MessageToJson
from grpc import server

from . import gateway_pb2_grpc
from .gateway_pb2 import HttpMessage, ProxyRequestEvent, ServerEvent


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s][%(levelname)s] %(message)s",
)


MOCK_REQUEST = ProxyRequestEvent(
    http_message=HttpMessage(
        url="http://example.com",
        data='{"some": "data"}',
        headers={"Content-type": "application/json"},
    ),
    larky_script="""
def process(input_message):
    print("start script")
"""
)


class LarkyGatewayServicer(gateway_pb2_grpc.LarkyGatewayServicer):
    def DebugSession(self, request_iterator, context):
        for event in request_iterator:
            logging.info(f"Processing client event: {MessageToJson(event)}")
            event_type = event.WhichOneof("payload")
            if event_type == "new_session":
                logging.info(f"Sending mock request {MOCK_REQUEST}")
                yield ServerEvent(proxy_request=MOCK_REQUEST)
            elif event_type == "result_ready":
                logging.info("Result is ready")
            else:
                raise Exception(f"Unknown event type: {event_type}")


@click.command()
@click.option("--port", type=int, default=50051)
def serve(port: int):
    logging.info(f"Starting LarkyGateway server. Will listen on port {port}")
    with ThreadPoolExecutor(1) as thread_pool:
        srv = server(thread_pool=thread_pool)
        gateway_pb2_grpc.add_LarkyGatewayServicer_to_server(LarkyGatewayServicer(), srv)
        srv.add_insecure_port(f"[::]:{port}")
        srv.start()
        try:
            srv.wait_for_termination()
        except KeyboardInterrupt:
            logging.info("Shutting down the service")
            srv.stop(grace=False)


if __name__ == "__main__":
    serve()
