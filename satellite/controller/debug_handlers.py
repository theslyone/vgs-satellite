from satellite.debug.session import DebugSession, DebugSessionState
from ..debug.debug_manager import DebugSessionLimitExceeded, DebugSessionNotFound
from ..debug.larky_debugger import UnknownThreadError
from ..schemas.debug import (
    GetFramesResponseSchema,
    GetSessionResponseSchema,
    GetThreadsResponseSchema,
    NewSessionRequestSchema,
    SetBreakpointsSchema,
    ThreadContinueSchema,
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
    def get_session(
        self,
        session_id: str,
        session_state: DebugSessionState = None,
    ) -> DebugSession:
        try:
            session = self.application.debug_manager.get_session(session_id)
        except DebugSessionNotFound:
            raise NotFoundError(f"Unknown session ID: {session_id}")

        if session_state is not None and session.state != session_state:
            raise ValidationError(
                "Requested operation is not allowed for the current session state "
                f"({session.state.value})."
            )

        return session


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

    def delete(self, session_id: str):
        """
        ---
        description: Delete debug session
        parameters:
            - name: session_id
              in: path
              description: Debug session ID
              required: true
              schema:
                type: string
        responses:
            204:
                description: Session was successfully deleted
            404:
                content:
                    application/json:
                        schema: ErrorResponseSchema
        """
        try:
            self.application.debug_manager.delete_session(session_id)
        except DebugSessionNotFound:
            raise NotFoundError(f"Unknown session ID: {session_id}")

        self.finish_empty_ok()


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
            400:
                content:
                    application/json:
                        schema: ErrorResponseSchema
        """
        session = self.get_session(session_id, DebugSessionState.RUNNING)
        return {"threads": session.debugger.get_threads()}


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
                        schema: GetFramesResponseSchema
            404:
                content:
                    application/json:
                        schema: ErrorResponseSchema
            400:
                content:
                    application/json:
                        schema: ErrorResponseSchema
        """
        session = self.get_session(session_id, DebugSessionState.RUNNING)
        try:
            return {"frames": session.debugger.list_frames(int(thread_id))}
        except UnknownThreadError:
            raise NotFoundError(f"Unknown thread ID {thread_id}")


class ThreadContinueHandler(BaseDebugSessionHander):
    @apply_request_schema(ThreadContinueSchema)
    def put(self, session_id: str, thread_id: int, validated_data: str):
        """
        ---
        description: Continue thread
        requestBody:
            content:
                application/json:
                    schema: ThreadContinueSchema
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
            204:
                description: Thread successfully proceeded
            404:
                content:
                    application/json:
                        schema: ErrorResponseSchema
            400:
                content:
                    application/json:
                        schema: ErrorResponseSchema
        """
        session = self.get_session(session_id, DebugSessionState.RUNNING)
        try:
            session.debugger.continue_execution(
                int(thread_id),
                validated_data.get("stepping"),
            )
        except UnknownThreadError:
            raise NotFoundError(f"Unknown thread ID {thread_id}")
        self.finish_empty_ok()


class ThreadPauseHandler(BaseDebugSessionHander):
    def put(self, session_id: str, thread_id: int):
        """
        ---
        description: Pause thread
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
            204:
                description: Thread successfully proceeded
            404:
                content:
                    application/json:
                        schema: ErrorResponseSchema
            400:
                content:
                    application/json:
                        schema: ErrorResponseSchema
        """
        session = self.get_session(session_id, DebugSessionState.RUNNING)
        try:
            session.debugger.pause_thread(int(thread_id))
        except UnknownThreadError:
            raise NotFoundError(f"Unknown thread ID {thread_id}")
        self.finish_empty_ok()


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
                    schema: SetBreakpointsSchema
        responses:
            204:
                description: Breakpoints were successfully set
            404:
                content:
                    application/json:
                        schema: ErrorResponseSchema
            400:
                content:
                    application/json:
                        schema: ErrorResponseSchema
        """
        session = self.get_session(session_id, DebugSessionState.RUNNING)
        session.debugger.set_breakpoints(validated_data["breakpoints"])
        self.finish_empty_ok()


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
