from marshmallow import Schema, fields


class NewSessionRequestSchema(Schema):
    org_id = fields.Str(required=True)
    vault = fields.Str(required=True)


class NewSessionResponseSchema(Schema):
    session_id = fields.Str(required=True)


class GetSessionResponseSchema(Schema):
    id = fields.Str(required=True)
    status = fields.Str(required=True)


class Location(Schema):
    path = fields.Str(required=True)
    line_number = fields.Int(required=True)
    column_number = fields.Int(required=True)


class GetThreadsResponseSchema(Schema):
    class Thread(Schema):
        id = fields.Str(required=True)
        name = fields.Str(required=True)
        pause_reason = fields.Str(required=True)
        location = fields.Nested(Location)

    threads = fields.List(fields.Nested(Thread))


class GetFramesResponseSchema(Schema):
    class Frame(Schema):
        class Scope(Schema):
            name = fields.Str(required=True)

        function_name = fields.Str(required=True)
        scope = fields.Nested(Scope)
        location = fields.Nested(Location)

    frames = fields.List(fields.Nested(Frame))
