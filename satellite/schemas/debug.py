from marshmallow import Schema, fields
from marshmallow_enum import EnumField

from satellite.debug.larky_debugger import Stepping

class NewSessionRequestSchema(Schema):
    org_id = fields.Str(required=True, example="ACVf8AmMNcrqXi1r2igVQGZ")
    vault = fields.Str(required=True, example="tnt77ievpnu")


class GetSessionResponseSchema(Schema):
    id = fields.Str(required=True, example="005d0b98-412a-45e8-a77a-4f764c2d3d36")
    started = fields.Bool(required=True, example=True)


class Location(Schema):
    path = fields.Str(required=True, example="/Users/satellite/script.bzl")
    line_number = fields.Int(required=True, example=4)
    column_number = fields.Int(required=False, example=10)


class GetThreadsResponseSchema(Schema):
    class Thread(Schema):
        id = fields.Int(required=True, example=413)
        name = fields.Str(required=True, example="thread-413")
        pause_reason = fields.Str(required=True, example="INITIALIZING")
        location = fields.Nested(Location)

    threads = fields.List(fields.Nested(Thread))


class Value(Schema):
    label = fields.Str(required=False, example="i")
    description = fields.Str(required=False, example="3")
    type = fields.Str(required=False, example="string")
    has_children = fields.Bool(required=False, example=False)
    id = fields.Int(required=False)


class GetFramesResponseSchema(Schema):
    class Frame(Schema):
        class Scope(Schema):
            name = fields.Str(required=True, example="global")
            binding = fields.List(fields.Nested(Value))

        function_name = fields.Str(required=True, example="<toplevel>")
        scope = fields.Nested(Scope)
        location = fields.Nested(Location)

    frames = fields.List(fields.Nested(Frame))


class SetBreakpointsSchema(Schema):
    class Breakpoint(Schema):
        location = fields.Nested(Location)

    breakpoints = fields.List(fields.Nested(Breakpoint))


class ThreadContinueSchema(Schema):
    stepping = EnumField(
        Stepping,
        by_value=True,
        required=True,
        example=Stepping.OVER.value,
    )
