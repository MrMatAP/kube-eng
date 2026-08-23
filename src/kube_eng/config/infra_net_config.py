
from pydantic import Field

from .base import RootConfigAware


class InfraNetConfig(RootConfigAware):
    """Network Configuration"""
    name: str = Field(description='Name of the docker network',
                      default='kind')
