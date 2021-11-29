import dataclasses
from pathlib import Path
from types import MappingProxyType

import pytest
from ruamel.yaml import YAML

from satellite.config import InvalidConfigError, configure


DEFAULT_CONFIG_VALUES = MappingProxyType(
    {
        'db_path': str(Path.home() / '.vgs-satellite' / 'db.sqlite'),
        'debug': False,
        'forward_proxy_port': 9099,
        'larky_debug_server_host': 'localhost',
        'larky_debug_server_port': 7300,
        'larky_gateway_host': 'localhost',
        'larky_gateway_port': 50051,
        'log_level': 'INFO',
        'log_path': None,
        'reverse_proxy_port': 9098,
        'routes_path': None,
        'silent': False,
        'volatile_aliases_ttl': 3600,
        'web_server_port': 8089,
    }
)


def _write_config(config_path: Path, raw_data: str = None, **kwargs):
    with open(config_path, 'w') as stream:
        if raw_data:
            stream.write(raw_data)
        else:
            YAML().dump(kwargs, stream)


def test_defaults(monkeypatch, tmp_path):
    monkeypatch.setattr(
        'satellite.config.DEFAULT_CONFIG_PATH',
        tmp_path / 'config.yml',
    )
    config = configure()
    assert dataclasses.asdict(config) == DEFAULT_CONFIG_VALUES


def test_from_default_config_file(monkeypatch, tmp_path):
    config_path = tmp_path / 'config.yml'
    _write_config(config_path, web_server_port=1)
    monkeypatch.setattr('satellite.config.DEFAULT_CONFIG_PATH', config_path)
    config = configure()
    assert dataclasses.asdict(config) == {
        **DEFAULT_CONFIG_VALUES,
        'web_server_port': 1,
    }


def test_from_custom_config_file(monkeypatch, tmp_path):
    default_config_path = tmp_path / 'config.yml'
    _write_config(default_config_path, web_server_port=1)
    monkeypatch.setattr(
        'satellite.config.DEFAULT_CONFIG_PATH',
        default_config_path,
    )

    custom_config_path = tmp_path / 'custom-config.yml'
    _write_config(custom_config_path, web_server_port=2)

    config = configure(config_path=custom_config_path)
    assert dataclasses.asdict(config) == {
        **DEFAULT_CONFIG_VALUES,
        'web_server_port': 2,
    }


def test_invalid_config_syntax(monkeypatch, tmp_path):
    config_path = tmp_path / 'config.yml'
    _write_config(config_path, raw_data='{invalid')
    monkeypatch.setattr('satellite.config.DEFAULT_CONFIG_PATH', config_path)
    with pytest.raises(InvalidConfigError):
        configure()


def test_invalid_config_data(monkeypatch, tmp_path):
    config_path = tmp_path / 'config.yml'
    _write_config(config_path, web_server_port='invalid')
    monkeypatch.setattr('satellite.config.DEFAULT_CONFIG_PATH', config_path)
    with pytest.raises(InvalidConfigError):
        configure()


def test_invalid_config_args(monkeypatch, tmp_path):
    config_path = tmp_path / 'config.yml'
    monkeypatch.setattr('satellite.config.DEFAULT_CONFIG_PATH', config_path)
    with pytest.raises(InvalidConfigError):
        configure(web_server_port='invalid')
