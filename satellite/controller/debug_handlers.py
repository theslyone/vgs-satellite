from satellite.debug.session import DebugSession
from ..debug.debug_manager import DebugSessionLimitExceeded, DebugSessionNotFound
from ..schemas.debug import (
    GetFramesResponseSchema,
    GetSessionResponseSchema,
    GetThreadsResponseSchema,
    NewSessionRequestSchema,
    SetBreakpointsSchema,
)
from . import (
    BaseHandler,
    apply_request_schema,
    apply_response_schema,
)
from .exceptions import NotFoundError, ValidationError


class SessionsHandler(BaseHandler):
    @apply_request_schema(NewSessionRequestSchema)
    @apply_response_schema(GetSessionResponseSchema)
    def post(self, validated_data: dict):
        """
        ---
        description: Start new debug session
        requestBody:
            content:
                application/json:
                    schema: GetSessionResponseSchema
        responses:
            200:
                content:
                    application/json:
                        schema: NewSessionResponseSchema
            400:
                content:
                    application/json:
                        schema: ErrorResponseSchema
        """
        try:
            return self.application.debug_manager.new_session(
                org_id=validated_data["org_id"],
                vault=validated_data["vault"],
            )
        except DebugSessionLimitExceeded:
            raise ValidationError("Debug sessions limit has been excceded")


class BaseDebugSessionHander(BaseHandler):
    def get_session(self, session_id: str) -> DebugSession:
        try:
            return self.application.debug_manager.get_session(session_id)
        except DebugSessionNotFound:
            raise NotFoundError(f"Unknown session ID: {session_id}")


class SessionHandler(BaseDebugSessionHander):
    @apply_response_schema(GetSessionResponseSchema)
    def get(self, session_id: str):
        """
        ---
        description: Retrieve debug session
        parameters:
            - name: session_id
              in: path
              description: Debug session ID
              required: true
              schema:
                type: string
        responses:
            200:
                content:
                    application/json:
                        schema: GetSessionResponseSchema
            404:
                content:
                    application/json:
                        schema: ErrorResponseSchema
        """
        return self.get_session(session_id)


class ThreadsHandler(BaseDebugSessionHander):
    @apply_response_schema(GetThreadsResponseSchema)
    def get(self, session_id: str):
        """
        ---
        description: Retrieve threads
        parameters:
            - name: session_id
              in: path
              description: Debug session ID
              required: true
              schema:
                type: string
        responses:
            200:
                content:
                    application/json:
                        schema: GetThreadsResponseSchema
            404:
                content:
                    application/json:
                        schema: ErrorResponseSchema
        """
        session = self.get_session(session_id)
        return {"threads": [session.debugger.get_current_thread()]}


class FramesHandler(BaseDebugSessionHander):
    @apply_response_schema(GetFramesResponseSchema)
    def get(self, session_id: str, thread_id: int):
        """
        ---
        description: Retrieve threads
        parameters:
            - name: session_id
              in: path
              description: Debug session ID
              required: true
              schema:
                type: string
            - name: thread_id
              in: path
              description: Thread ID
              required: true
              schema:
                type: integer
        responses:
            200:
                content:
                    application/json:
                        schema: GetThreadsResponseSchema
            404:
                content:
                    application/json:
                        schema: ErrorResponseSchema
        """
        session = self.get_session(session_id)
        return {"frames": session.debugger.list_frames(int(thread_id))}


class BreakpointsHandler(BaseDebugSessionHander):
    @apply_request_schema(SetBreakpointsSchema)
    def put(self, session_id: str, validated_data: dict):
        """
        ---
        description: Set breakpoints
        parameters:
            - name: session_id
              in: path
              description: Debug session ID
              required: true
              schema:
                type: string
        requestBody:
            content:
                application/json:
                    schema: NewSessionRequestSchema
        responses:
            204:
                description: Breakpoints were successfully set
            400:
                content:
                    application/json:
                        schema: ErrorResponseSchema
        """
        session = self.get_session(session_id)
        session.debugger.set_breakpoints(validated_data["breakpoints"])


class GetSourceHandler(BaseHandler):
    def get(self, path: int):
        """
        ---
        description: Get source code
        parameters:
            - name: path
              in: path
              description: Source code path
              required: true
              schema:
                type: string
        responses:
            200:
                description: Source code
            404:
                content:
                    application/json:
                        schema: ErrorResponseSchema
        """
        try:
            with open(path) as f:
                content = f.read()
        except FileNotFoundError:
            raise NotFoundError(f"Unknown path: {path}")

        self.set_status(200, "Success")
        self.finish(content)
