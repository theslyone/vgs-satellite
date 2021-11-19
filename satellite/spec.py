import logging
from typing import Callable, List, Tuple

from apispec import APISpec
from apispec.exceptions import APISpecError
from apispec.ext.marshmallow import (
    MarshmallowPlugin as BaseMarshmallowPlugin,
    OpenAPIConverter,
)
from apispec.ext.marshmallow.common import resolve_schema_instance
from apispec_webframeworks.tornado import TornadoPlugin
from marshmallow.fields import Field
from marshmallow_enum import EnumField
from marshmallow_oneofschema import OneOfSchema


class Converter(OpenAPIConverter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_attribute_function(self._convert_non_standard_fields)

    def resolve_nested_schema(self, schema):
        try:
            instance = resolve_schema_instance(schema)
        except Exception:
            # Let base class handle it
            instance = None

        if not instance or not isinstance(instance, OneOfSchema):
            return super().resolve_nested_schema(schema)

        mapping = {}
        refs = []
        for type_name, schema_cls in instance.type_schemas.items():
            ref = self.resolve_nested_schema(schema_cls)
            refs.append(ref)
            mapping[type_name] = ref['$ref']

        return {
            'discriminator': {
                'mapping': mapping,
                'propertyName': instance.type_field,
            },
            'oneOf': refs,
        }

    def _convert_non_standard_fields(self, field: Field, ret: dict) -> dict:
        if isinstance(field, EnumField):
            return {
                **ret,
                'enum': [member.value for member in field.enum],
                'type': 'string',
            }
        return ret


class MarshmallowPlugin(BaseMarshmallowPlugin):
    Converter = Converter


def build_openapi_spec(handlers: List[Tuple[str, Callable]]) -> APISpec:
    spec = APISpec(
        title='VGS Satellite management API',
        version='1.0.0',
        openapi_version='3.0.2',
        info={'description': 'The management API for VGS Satellite app'},
        plugins=[TornadoPlugin(), MarshmallowPlugin()],
    )

    for urlspec in handlers:
        try:
            spec.path(urlspec=urlspec)
        except APISpecError as exc:
            logging.error(f"Error during loading spec: {exc}")

    return spec
