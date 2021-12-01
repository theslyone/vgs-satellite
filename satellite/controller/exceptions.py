from tornado.web import HTTPError


class APIError(HTTPError):
    def __init__(
        self,
        status_code: int,
        reason: str,
        message: str = None,
        details: dict = None,
    ):
        log_message = ': '.join(map(str, filter(None, [message, details]))) or None
        super().__init__(
            status_code=status_code,
            reason=reason,
            log_message=log_message,
        )
        self.message = message
        self.details = details


class InternalError(APIError):
    def __init__(self):
        super().__init__(500, 'Internal error')


class NotFoundError(APIError):
    def __init__(self, message: str):
        super().__init__(404, 'Not found', message)


class InvalidMethod(APIError):
    def __init__(self):
        super().__init__(405, 'Invalid method')


class ValidationError(APIError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(400, 'Invalid request', message, details)


class ConflictError(APIError):
    def __init__(self, message: str):
        super().__init__(409, 'Conflict', message)
