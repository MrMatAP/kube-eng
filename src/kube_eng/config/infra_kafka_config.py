import abc
import pathlib
import secrets
import typing

from pydantic import AnyHttpUrl, Field, IPvAnyAddress, computed_field

from .base import RootConfigAware


class KafkaConfig(RootConfigAware, abc.ABC):
    """Common configuration for Kafka"""
    enabled: bool = Field(
        default=True, description='Whether to enable Kafka'
    )
    port: int = Field(
        default=9092, description='Port of the Kafka server'
    )
    admin_user: str = Field(description='Admin username of the Kafka server',
                            default='admin')
    admin_password: str = Field(description='Admin password of the Kafka server',
                                default_factory=lambda: secrets.token_urlsafe(16))

    @abc.abstractmethod
    @computed_field(description='The fully qualified domain name to connect to')
    @property
    def client_fqdn(self) -> str:
        """
        The fully qualified domain name to connect to
        Returns:
            A FQDN
        """

class LocalKafkaConfig(KafkaConfig):
    """Local Kafka server hosted in a container on this host"""

    provider: typing.Literal['local'] = 'local'
    name: str = Field(default='kafka', description='Name of the Kafka server container')
    image: str = Field(
        default='apache/kafka:latest', description='Kafka server container image'
    )
    volume_name: str = Field(
        default='kafka-volume', description='Name of the Kafka volume'
    )
    ip: IPvAnyAddress = Field(
        default_factory=lambda: IPvAnyAddress('127.0.0.1'),
        description='IP address of the Kafka server',
    )

    @computed_field
    @property
    def config_path(self) -> pathlib.Path:
        """
        Directory to store Kafka configuration in.
        Returns:
            Path to the Kafka configuration directory.
        """
        return self._root_config.config_path / 'kafka'

    @computed_field(description='The fully qualified domain name to connect to')
    @property
    def client_fqdn(self) -> str:
        return f'{self.name}.{self._root_config.infra.dns.domain}'


class RemoteKafkaConfig(KafkaConfig):
    """Remote Kafka server hosted on a remote host"""
    provider: typing.Literal['remote'] = 'remote'
    endpoint: AnyHttpUrl = Field(
        description='URL of the remote Kafka server'
    )

    @computed_field(description='The fully qualified domain name to connect to')
    @property
    def client_fqdn(self) -> str:
        if self.endpoint.host is None:
            raise ValueError('Missing Kafka endpoint')
        return self.endpoint.host or ''


InfraKafkaConfig = typing.Annotated[
    LocalKafkaConfig | RemoteKafkaConfig,
    Field(discriminator='provider'),
]
