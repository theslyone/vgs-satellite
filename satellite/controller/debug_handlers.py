from . import (
    BaseHandler,
    apply_request_schema,
    apply_response_schema,
)

from ..schemas.debug import (
    GetFramesResponseSchema,
    GetSessionResponseSchema,
    GetThreadsResponseSchema,
    NewSessionRequestSchema,
    NewSessionResponseSchema,
)
from .exceptions import NotFoundError


class SessionsHandler(BaseHandler):
    @apply_request_schema(NewSessionRequestSchema)
    @apply_response_schema(NewSessionResponseSchema)
    def post(self, validated_data: dict):
        """
        ---
        description: Start new debug session
        requestBody:
            content:
                application/json:
                    schema: NewSessionRequestSchema
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
        session_id = self.application.debug_manager.start(
            org_id=validated_data["org_id"],
            vault=validated_data["vault"],
        )
        return {"session_id": session_id}


class SessionHandler(BaseHandler):
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
        return {
            "id": session_id,
            "status": self.application.debug_manager.status(session_id),
        }


class ThreadsHandler(BaseHandler):
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
        debugger = self.application.debug_manager.get_debugger(session_id)
        return {"threads": [debugger.get_current_thread()]}


class FramesHandler(BaseHandler):
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
        debugger = self.application.debug_manager.get_debugger(session_id)
        return {"frames": debugger.list_frames(int(thread_id))}


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