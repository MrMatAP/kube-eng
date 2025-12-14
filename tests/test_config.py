"""
Configuration tests
"""

import pathlib

from pydantic import BaseModel

from kube_eng.config import RootConfig, RootConfigAware

def recursive_config_assertion(config: RootConfig, base: RootConfigAware)-> bool:
    """
    A little utility function to recurse down the entire configuration hierarchy
    and assert that _root_config as a reference back to the root configuration instance is set.
    Args:
        config (RootConfig): The root configuration instance
        base (RootConfigAware): The current instance to be checked within the hierarchy

    Returns:
        True if all attributes of the base that are subclasses of BaseModel have a reference to the root config

    Raises:
        AssertionError: If there is an attribute that is a subclass of BaseModel without a reference to the root config
    """
    for attr in dict(base).values():
        if issubclass(type(attr), BaseModel):
            assert attr._root_config == config, f'{base.__class__.__name__}.{attr.__class__.__name__} is not configured'
    return True

def test_root_config_propagates_when_loaded(tmp_path: pathlib.Path):
    """
    We expect that the root_config propagates down the entire configuration hierarchy
    when the configuration is instantiated with its load class method
    Args:
        tmp_path (pathlib.Path): A temporary path
    """
    config = RootConfig.load(config_path=tmp_path)

    assert config.config_path == tmp_path
    for attr in dict(config).values():
        if issubclass(type(attr), BaseModel):
            assert recursive_config_assertion(config, attr)

def test_root_config_propagates_when_initialized(tmp_path: pathlib.Path):
    """
    We expect that the root_config propagates down the entire configuration hierarchy
    when we simply instantiate the root configuration class.
    Args:
        tmp_path (pathlib.Path): A temporary path
    """
    config = RootConfig(config_path=tmp_path)

    assert config.config_path == tmp_path
    for attr in dict(config).values():
        if issubclass(type(attr), BaseModel):
            assert recursive_config_assertion(config, attr)
