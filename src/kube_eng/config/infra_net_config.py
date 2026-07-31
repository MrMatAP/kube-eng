import typing

from pydantic import Field, IPvAnyNetwork

from .base import RootConfigAware

class InfraNetConfig(RootConfigAware):
    """Network Configuration"""
    name: str = Field(description='Name of the docker network',
                      default='kind')
