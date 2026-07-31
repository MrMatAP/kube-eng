import abc
import base64
import pathlib
import secrets
import typing
from base64 import b64encode

from pydantic import IPvAnyAddress, Field, computed_field

from .base import RootConfigAware


class DNSConfig(RootConfigAware, abc.ABC):
    """Common DNS Configuration"""

    ip: IPvAnyAddress = Field(
        default_factory=lambda: IPvAnyAddress('127.0.0.1'),
        description='IP address of the DNS server',
    )
    port: int = Field(
        default=53, description='Port to expose the DNS server on the host'
    )
    control_port: int = Field(
        default=953,
        description='Port to expose the DNS server control port on the host',
    )
    admin_key_name: str = Field(
        default='update-key',
        description='Name of the DNS update key'
    )
    admin_key_secret: str = Field(
        default_factory=lambda: b64encode(secrets.token_bytes(16)).decode(encoding='utf-8'),
        description='DNS update key secret'
    )
    key_algorithm: str = Field(
        default='hmac-sha256',
        description='Algorithm used for signing dynamic DNS updates'
    )
    protocol: str = Field(
        default='tcp',
        description='Protocol used for dynamic DNS updates'
    )
    ttl: int = Field(
        default=1800,
        description='Time to live for DNS records'
    )
    zone: str = Field(
        default='k8s',
        description='Parent zone to serve'
    )

    @computed_field
    @property
    def domain(self) -> str:
        """
        Computed name of the DNS domain in which to register records for this cluster
        Returns:
            The domain to register records in for this cluster
        """
        return f'{self._root_config.cluster.name}.{self.zone}'


class LocalDNSConfig(DNSConfig):
    """DNS provisioned locally as a Docker container"""
    provider: typing.Literal['local'] = 'local'
    name: str = Field(default='dns', description='Name of the DNS container')
    image: str = Field(default='ubuntu/bind9:latest', description='DNS container image')
    cache_volume_name: str = Field(
        default='dns-volume-cache', description='Name of the DNS cache volume'
    )
    zones_volume_name: str = Field(
        default='dns-volume-zones', description='Name of the DNS volume for zones'
    )

    @computed_field
    @property
    def config_path(self) -> pathlib.Path:
        """
        Directory to store DNS configuration in.
        Returns:
            Path to the DNS configuration directory.
        """
        return self._root_config.config_path / 'dns'


class RemoteDNSConfig(DNSConfig):
    """DNS hosted remotely"""
    provider: typing.Literal['remote'] = 'remote'


InfraDNSConfig = typing.Annotated[
    LocalDNSConfig | RemoteDNSConfig,
    Field(discriminator='provider'),
]
