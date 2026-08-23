import abc
import pathlib
import secrets
import typing

from pydantic import AnyHttpUrl, Field, IPvAnyAddress, computed_field

from .base import IdPClientRole, RootConfigAware


class S3Config(RootConfigAware, abc.ABC):
    """Common S3 Configuration"""
    port: int = Field(
        default=9000, description='Port of the S3 server'
    )
    console_port: int = Field(
        default=9001, description='Console port of the S3 server'
    )
    region: str = Field(default='us-east-1', description='S3 region name')
    access_key: str = Field(default='admin', description='S3 access key')
    secret_key: str = Field(
        default_factory=lambda: secrets.token_urlsafe(16),
        description='S3 secret key. If empty, defaults to the admin password',
    )

    @computed_field(description='S3 Client Id')
    @property
    def client_id(self) -> str:
        return f's3-{self._root_config.cluster.name}'

    @computed_field(description='S3 Client Name')
    @property
    def client_name(self) -> str:
        return f'S3 :: {self._root_config.cluster.name }'

    @computed_field(description='S3 Client description')
    @property
    def client_description(self) -> str:
        return f'S3 instance on {self._root_config.cluster.name}'

    @computed_field(description='S3 Roles')
    @property
    def client_roles(self) -> list[IdPClientRole]:
        return [
            IdPClientRole(name='kube-eng-s3-admin', description='Kube Eng :: S3 :: Admin'),
            IdPClientRole(name='kube-eng-s3-contributor', description='Kube Eng :: S3 :: Contributor'),
            IdPClientRole(name='kube-eng-s3-viewer', description='Kube Eng :: S3 :: Viewer')
        ]

    @computed_field(description='Client FQDN of the S3 service')
    @property
    def client_fqdn(self) -> str:
        if self.endpoint.host is None:
            raise ValueError('Missing host in endpoint')
        return self.endpoint.host or ''

    @abc.abstractmethod
    @computed_field(description='Client endpoint of the S3 service')
    @property
    def endpoint(self) -> AnyHttpUrl:
        """
        Client endpoint of the S3 service
        Returns:
            A HTTP URL
        """
    
    @abc.abstractmethod
    @computed_field(description='Admin endpoint of the S3 service')
    @property
    def admin_endpoint(self) -> AnyHttpUrl:
        """
        Admin endpoint of the S3 service
        Returns:
            A HTTP URL
        """

class LocalS3Config(S3Config):
    """S3-compatible storage provisioned locally as a Docker container."""

    provider: typing.Literal['local'] = 'local'
    name: str = Field(default='s3', description='Name of the S3 container')
    image: str = Field(default='rustfs/rustfs:latest', description='S3 container image')
    volume_name: str = Field(default='s3-volume', description='Name of the S3 volume')
    ip: IPvAnyAddress = Field(
        default_factory=lambda: IPvAnyAddress('127.0.0.1'),
        description='IP address to expose the PostgreSQL server on the host',
    )

    @computed_field(description='Local directory path to store S3 configuration in')
    @property
    def config_path(self) -> pathlib.Path:
        """Directory to store S3 configuration in."""
        return self._root_config.config_path / 's3'

    @computed_field(description='Client endpoint of the S3 service')
    @property
    def endpoint(self) -> AnyHttpUrl:
        return AnyHttpUrl(
            f'https://{self.name}.{self._root_config.infra.dns.domain}:{self.port}'
        )

    @computed_field(description='Admin endpoint of the S3 service')
    @property
    def admin_endpoint(self) -> AnyHttpUrl:
        return AnyHttpUrl(
            f'https://{self.name}.{self._root_config.infra.dns.domain}:{self.console_port}'
        )

    @computed_field(description='Client endpoint of the S3 service')
    @property
    def client_endpoint(self) -> AnyHttpUrl:
        return self.endpoint

    @computed_field(description='Callback URL for OIDC')
    @property
    def callback_url(self) -> AnyHttpUrl:
        return AnyHttpUrl(f'https://{self.name}.{self._root_config.infra.dns.domain}:{self.console_port}/rustfs/admin/v3/oidc/callback/default')

class RemoteS3Config(S3Config):
    """Central S3-compatible storage hosted elsewhere."""

    provider: typing.Literal['remote'] = 'remote'
    url: AnyHttpUrl = Field(description='URL of the S3 service')

    @computed_field(description='Client endpoint of the S3 service')
    @property
    def endpoint(self) -> AnyHttpUrl:
        return self.url

    @computed_field(description='Admin endpoint of the S3 service')
    @property
    def admin_endpoint(self) -> AnyHttpUrl:
        return self.url


InfraS3Config = typing.Annotated[
    LocalS3Config | RemoteS3Config,
    Field(discriminator='provider'),
]
