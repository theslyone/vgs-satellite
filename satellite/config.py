import dataclasses
import os
from pathlib import Path
from typing import Optional

import marshmallow_dataclass
from ruamel.yaml import YAML


SATELLITE_DIR = Path(
    os.getenv(
        'SATELLITE_DIR',
        Path.home() / '.vgs-satellite',
    )
)
DEFAULT_CONFIG_PATH = SATELLITE_DIR / 'config.yml'
DEFAULT_DB_PATH = SATELLITE_DIR / 'db.sqlite'


@dataclasses.dataclass(frozen=True)
class SatelliteConfig:
    db_path: str = str(DEFAULT_DB_PATH)
    debug: bool = False
    forward_proxy_port: int = 9099
    log_path: Optional[str] = None
    log_level: str = "INFO"
    reverse_proxy_port: int = 9098
    routes_path: Optional[str] = None
    silent: bool = False
    volatile_aliases_ttl: int = 3600
    web_server_port: int = 8089


SatelliteConfigSchema = marshmallow_dataclass.class_schema(SatelliteConfig)


class InvalidConfigError(Exception):
    pass


def init_satellite_dir():
    SATELLITE_DIR.mkdir(exist_ok=True)


def configure(config_path: str = None, **kwargs):
    params_from_file = _get_params_from_config_file(config_path)
    params = {**params_from_file, **kwargs}

    schema = SatelliteConfigSchema(unknown='EXCLUDE')
    errors = schema.validate(params)
    if errors:
        raise InvalidConfigError(errors)

    global __config
    __config = SatelliteConfig(**schema.dump(params))
    return __config


def get_config() -> SatelliteConfig:
    return __config


def _get_params_from_config_file(config_path: str = None) -> dict:
    for path in filter(None, [config_path, DEFAULT_CONFIG_PATH]):
        path = Path(path).expanduser().resolve()
        if path.exists():
            try:
                with open(path) as stream:
                    config = YAML().load(stream) or {}
                if not isinstance(config, dict):
                    raise TypeError(
                        f'Expecting mapping, but got {type(config).__name__}.'
                    )
            except Exception as exc:
                raise InvalidConfigError(str(exc)) from exc

            return config

    return {}


__config: SatelliteConfig = None
