from marshmallow import Schema, fields


class NewSessionRequestSchema(Schema):
    org_id = fields.Str(required=True)
    vault = fields.Str(required=True)


class GetSessionResponseSchema(Schema):
    id = fields.Str(required=True)
    started = fields.Bool(required=True)


class Location(Schema):
    path = fields.Str(required=True)
    line_number = fields.Int(required=True)
    column_number = fields.Int(required=False)


class GetThreadsResponseSchema(Schema):
    class Thread(Schema):
        id = fields.Str(required=True)
        name = fields.Str(required=True)
        pause_reason = fields.Str(required=True)
        location = fields.Nested(Location)

    threads = fields.List(fields.Nested(Thread))


class Value(Schema):
    label = fields.Str(required=False)
    description = fields.Str(required=False)
    type = fields.Str(required=False)
    has_children = fields.Bool(required=False)
    id = fields.Int(required=False)


class GetFramesResponseSchema(Schema):
    class Frame(Schema):
        class Scope(Schema):
            name = fields.Str(required=True)
            binding = fields.List(fields.Nested(Value))

        function_name = fields.Str(required=True)
        scope = fields.Nested(Scope)
        location = fields.Nested(Location)

    frames = fields.List(fields.Nested(Frame))


class SetBreakpointsSchema(Schema):
    class Breakpoint(Schema):
        location = fields.Nested(Location)

    breakpoints = fields.List(fields.Nested(Breakpoint))
