import pytest
from kube_eng import __default_config_path__
from kube_eng.config import RootConfig


@pytest.fixture(scope="session")
def config():
    yield RootConfig.load(config_path=__default_config_path__)
