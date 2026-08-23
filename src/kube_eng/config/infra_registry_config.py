import abc
import pathlib
import typing

from pydantic import (
    AnyHttpUrl,
    AnyUrl,
    Field,
    IPvAnyAddress,
    UrlConstraints,
    computed_field,
)

from .base import RootConfigAware

OciUrl = typing.Annotated[AnyUrl, UrlConstraints(allowed_schemes=['oci'])]


class RegistryConfig(RootConfigAware, abc.ABC):
    """Common registry configuration"""

    @computed_field(description='The fully qualified domain name of the registry')
    @property
    def client_fqdn(self) -> str:
        if not self.oci_endpoint.host:
            raise ValueError('Missing OCI URL')
        return self.oci_endpoint.host or ''

    @computed_field(description='OCI endpoint of the registry')
    @property
    @abc.abstractmethod
    def oci_endpoint(self) -> AnyUrl:
        """
        Computed client OCI URL for the registry
        Returns:
            An OCI URL
        """

    @computed_field(description='HTTP endpoint of the registry')
    @property
    @abc.abstractmethod
    def http_endpoint(self) -> AnyHttpUrl:
        """
        Computed client HTTP URL for the registry
        Returns:
            An HTTP URL
        """


class LocalRegistryConfig(RegistryConfig):
    """OCI registry provisioned locally as a Docker container."""

    provider: typing.Literal['local'] = 'local'
    name: str = Field(
        default='registry', description='Name of the OCI registry container'
    )
    image: str = Field(
        default='ghcr.io/project-zot/zot-linux-arm64:v2.1.15',
        description='OCI registry container image',
    )
    volume_name: str = Field(
        default='registry-volume', description='Name of the OCI registry volume'
    )
    ip: IPvAnyAddress = Field(
        default_factory=lambda: IPvAnyAddress('127.0.0.1'),
        description='IP address to expose the registry on the host',
    )
    port: int = Field(
        default=5001, description='Port to expose the registry on the host'
    )

    @computed_field(
        description='Local directory path to store registry configuration in'
    )
    @property
    def config_path(self) -> pathlib.Path:
        """Directory to store registry configuration in."""
        return self._root_config.config_path / 'registry'

    @computed_field(description='OCI endpoint of the registry')
    @property
    def oci_endpoint(self) -> AnyUrl:
        return AnyUrl(
            f'oci://{self.name}.{self._root_config.infra.dns.domain}:{self.port}'
        )

    @computed_field(description='HTTP endpoint of the registry')
    @property
    def http_endpoint(self) -> AnyHttpUrl:
        return AnyHttpUrl(
            f'https://{self.name}.{self._root_config.infra.dns.domain}:{self.port}'
        )


class RemoteRegistryConfig(RegistryConfig):
    """Central OCI registry hosted elsewhere.

    Authenticate out of band (docker/helm login).
    """

    provider: typing.Literal['remote'] = 'remote'
    url: OciUrl = Field(
        description='URL of the registry, e.g. oci://harbor.example.com/kube-eng'
    )

    @computed_field(description='OCI endpoint of the registry')
    @property
    def oci_endpoint(self) -> AnyUrl:
        if self.url.host is None:
            raise ValueError('Missing host in URL')
        # AnyUrl.build() inserts its own separator before path, so a path
        # that already carries its own leading slash (as .path always does)
        # would otherwise produce a double slash after the host.
        return AnyUrl.build(
            scheme='oci',
            host=self.url.host or '',
            port=self.url.port,
            path=(self.url.path or '').lstrip('/'),
            query=self.url.query,
            fragment=self.url.fragment,
        )

    @computed_field(description='HTTP endpoint of the registry')
    @property
    def http_endpoint(self) -> AnyHttpUrl:
        if self.url.host is None:
            raise ValueError('Missing host in URL')
        return AnyHttpUrl.build(
            scheme='http',
            host=self.url.host or '',
            port=self.url.port,
            path=(self.url.path or '').lstrip('/'),
            query=self.url.query,
            fragment=self.url.fragment,
        )


InfraRegistryConfig = typing.Annotated[
    LocalRegistryConfig | RemoteRegistryConfig,
    Field(discriminator='provider'),
]
