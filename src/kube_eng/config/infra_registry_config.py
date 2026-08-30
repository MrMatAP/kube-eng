import abc
import pathlib
import secrets
import typing

from pydantic import (
    AnyHttpUrl,
    AnyUrl,
    Field,
    IPvAnyAddress,
    UrlConstraints,
    computed_field,
)

from .base import IdPClientRole, RootConfigAware

OciUrl = typing.Annotated[AnyUrl, UrlConstraints(allowed_schemes=['oci'])]


class RegistryConfig(RootConfigAware, abc.ABC):
    """Common registry configuration"""

    admin_username: str = Field(
        default='kube-eng',
        description='Registry account helm_publish authenticates as to push charts',
    )
    admin_password: str = Field(
        default='',
        description=(
            'Password for admin_username. Generated for a local registry; supplied '
            'out of band for a remote one (which authenticates it via LDAP).'
        ),
    )

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

    @computed_field(
        description='HTTP endpoint used by containers on the shared Docker '
        'network (the kind nodes)'
    )
    @property
    @abc.abstractmethod
    def cluster_endpoint(self) -> AnyHttpUrl:
        """
        HTTP URL the kind nodes' containerd uses for the registry mirror.
        For a local registry this reaches the container directly on the
        shared network -- a different port from the host-published one.
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
        default='ghcr.io/project-zot/zot-linux-arm64:v2.1.20',
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
    container_port: int = Field(
        default=5000,
        description='Port the registry listens on inside its container '
        '(what other containers on the shared network connect to)',
    )
    admin_password: str = Field(
        default_factory=lambda: secrets.token_urlsafe(16),
        description='Password for admin_username, generated if not set',
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

    @computed_field(
        description='HTTP endpoint used by containers on the shared Docker '
        'network (the kind nodes)'
    )
    @property
    def cluster_endpoint(self) -> AnyHttpUrl:
        # The kind nodes share the Docker network with this container and
        # resolve its FQDN alias to the container IP, so they reach it on the
        # in-container port, not the host-published one.
        domain = self._root_config.infra.dns.domain
        return AnyHttpUrl(f'https://{self.name}.{domain}:{self.container_port}')

    @computed_field(description='Registry client Id')
    @property
    def client_id(self) -> str:
        return f'registry-{self._root_config.cluster.name}'

    @computed_field(description='Registry client Name')
    @property
    def client_name(self) -> str:
        return f'Registry :: {self._root_config.cluster.name}'

    @computed_field(description='Registry client description')
    @property
    def client_description(self) -> str:
        return f'Registry instance on {self._root_config.cluster.name}'

    @computed_field(description='Registry roles')
    @property
    def client_roles(self) -> list[IdPClientRole]:
        return [
            IdPClientRole(name='registry-admin', description='Registry :: Admin'),
            IdPClientRole(
                name='registry-contributor', description='Registry :: Contributor'
            ),
            IdPClientRole(name='registry-viewer', description='Registry :: Viewer'),
        ]

    @computed_field(description='Registry callback URL')
    @property
    def callback_url(self) -> AnyHttpUrl:
        return AnyHttpUrl(
            f'https://{self.name}.{self._root_config.infra.dns.domain}:{self.port}/zot/auth/callback/oidc'
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
            scheme='https',
            host=self.url.host or '',
            port=self.url.port,
            path=(self.url.path or '').lstrip('/'),
            query=self.url.query,
            fragment=self.url.fragment,
        )

    @computed_field(
        description='HTTP endpoint used by containers on the shared Docker '
        'network (the kind nodes)'
    )
    @property
    def cluster_endpoint(self) -> AnyHttpUrl:
        # A remote registry is off-host; everyone reaches it the same way.
        return self.http_endpoint


InfraRegistryConfig = typing.Annotated[
    LocalRegistryConfig | RemoteRegistryConfig,
    Field(discriminator='provider'),
]
