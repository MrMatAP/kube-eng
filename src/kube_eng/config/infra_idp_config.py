import abc
import pathlib
import secrets
import typing

from pydantic import AnyHttpUrl, Field, IPvAnyAddress, computed_field

from .base import RootConfigAware


class IdPConfig(RootConfigAware, abc.ABC):
    """Common IdP Configuration"""

    realm: str = Field(default='master', description='Realm to register clients in')
    admin_user: str = Field(default='admin', description='IdP administrative user')
    admin_password: str = Field(
        default_factory=lambda: secrets.token_urlsafe(16),
        description=(
            'IdP administrative password. If empty, defaults to the admin password'
        ),
    )

    username_claim: str = Field(default='preferred_username')
    groups_claim: str = Field(default='groups')

    @computed_field(description='The fully qualified domain name of the IdP')
    @property
    @abc.abstractmethod
    def client_fqdn(self) -> str:
        """
        Compute the fully qualified domain name for the identity provider
        Returns:
            A fully qualified domain name
        """

    @computed_field(description='The base URL of the IdP')
    @property
    @abc.abstractmethod
    def client_base_url(self) -> AnyHttpUrl:
        """
        Compute the URL of the identity provider
        Returns:
            A URL
        """

    @computed_field(description='The IdP issuer URL')
    @property
    @abc.abstractmethod
    def issuer_url(self) -> AnyHttpUrl:
        """
        The IdP issuer URL
        Returns:
            A URL
        """


class LocalIdPConfig(IdPConfig):
    """IdP provisioned locally as a Docker container."""

    provider: typing.Literal['local'] = 'local'
    name: str = Field(default='idp', description='Name of the IdP container')
    image: str = Field(
        default='keycloak/keycloak:26.5.6', description='IdP container image'
    )
    ip: IPvAnyAddress = Field(
        default_factory=lambda: IPvAnyAddress('127.0.0.1'),
        description='Exposed IP address of the local IdP',
    )
    port: int = Field(default=8443, description='Exposed port of the local IdP')
    db_host: str = Field(default='pg', description='Host of the IdP database')
    db_port: int = Field(default=5432, description='Port of the IdP database')
    db_name: str = Field(default='idp', description='Name of the IdP database')
    db_user: str = Field(default='idp', description='User for the IdP database')
    db_password: str = Field(
        default_factory=lambda: secrets.token_urlsafe(16),
        description=(
            'Password for the IdP database. If empty, defaults to the admin password'
        ),
    )

    @computed_field(description='Local directory path to store IdP configuration in')
    @property
    def config_path(self) -> pathlib.Path:
        """Local directory path to store IdP configuration in."""
        return self._root_config.config_path / 'idp'

    @computed_field(description='The fully qualified domain name of the IdP')
    @property
    def client_fqdn(self) -> str:
        return f'{self.name}.{self._root_config.infra.dns.domain}'

    @computed_field(description='The base URL of the IdP')
    @property
    def client_base_url(self) -> AnyHttpUrl:
        """Base URL of the IdP as reachable by consumers and this host."""
        return AnyHttpUrl(
            f'https://{self.name}.{self._root_config.infra.dns.domain}:{self.port}'
        )

    @computed_field(description='The IdP issuer URL')
    @property
    def issuer_url(self) -> AnyHttpUrl:
        base = str(self.client_base_url).rstrip('/')
        return AnyHttpUrl(f'{base}/realms/{self.realm}')


class RemoteIdPConfig(IdPConfig):
    """Central IdP hosted elsewhere."""

    provider: typing.Literal['remote'] = 'remote'
    url: AnyHttpUrl = Field(
        description='Base URL of the IdP, e.g. https://idp.example.com:8443'
    )

    @computed_field(description='The fully qualified domain name of the IdP')
    @property
    def client_fqdn(self) -> str:
        if not self.url or not self.url.host:
            raise ValueError('Missing URL')
        return self.url.host or ''

    @computed_field(description='The base URL of the IdP')
    @property
    def client_base_url(self) -> AnyHttpUrl:
        return self.url

    @computed_field(description='The IdP issuer URL')
    @property
    def issuer_url(self) -> AnyHttpUrl:
        base = str(self.url).rstrip('/')
        return AnyHttpUrl(f'{base}/realms/{self.realm}')

    @computed_field(description='The port the IdP is reachable on')
    @property
    def port(self) -> int:
        return self.url.port or 443


InfraIdPConfig = typing.Annotated[
    LocalIdPConfig | RemoteIdPConfig,
    Field(discriminator='provider'),
]
