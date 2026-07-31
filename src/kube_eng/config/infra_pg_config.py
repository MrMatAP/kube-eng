import abc
import typing
import secrets

from pydantic import IPvAnyAddress, Field, computed_field, PostgresDsn

from .base import RootConfigAware


class PGConfig(RootConfigAware, abc.ABC):
    """Common PostgreSQL configuration"""

    port: int = Field(
        default=5432,
        description='Port to expose the PostgreSQL server on the host',
    )
    admin_user: str = Field(description='PostgreSQL administrative user',
                            default='postgres')
    admin_password: str = Field(description='PostgreSQL administrative password',
                                default_factory=lambda: secrets.token_urlsafe(16))
    admin_db: str = Field(description='PostgreSQL administrative database',
                          default='postgres')

    @computed_field(description='The fully qualified domain name to connect to')
    @property
    @abc.abstractmethod
    def client_fqdn(self) -> str:
        """
        Compute the fully qualified domain name for PostgreSQL
        Returns:
            A fully qualified domain name
        """
        pass

    @computed_field(description='A PostgreSQL DSN')
    @property
    def admin_dsn(self) -> PostgresDsn:
        """
        Compute the DSN for connecting to PostgreSQL in administrative context
        Returns:
            A DSN
        """
        return PostgresDsn.build(scheme='postgres',
                                 host=self.client_fqdn,
                                 port=self.port,
                                 username=self.admin_user,
                                 password=self.admin_password,
                                 path=self.admin_db)


class LocalPGConfig(PGConfig):
    """PostgreSQL provisioned locally as a Docker container."""

    provider: typing.Literal['local'] = 'local'
    name: str = Field(default='pg', description='Name of the PostgreSQL container')
    image: str = Field(
        default='postgres:18-alpine', description='PostgreSQL container image'
    )
    volume_name: str = Field(
        default='pg-volume', description='Name of the PostgreSQL volume'
    )
    ip: IPvAnyAddress = Field(
        default_factory=lambda: IPvAnyAddress('127.0.0.1'),
        description='IP address to expose the PostgreSQL server on the host',
    )

    @computed_field(description='The fully qualified domain name to connect to')
    @property
    def client_fqdn(self) -> str:
        return f'{self.name}.{self._root_config.infra.dns.domain}'


class RemotePGConfig(PGConfig):
    """Central PostgreSQL hosted elsewhere."""

    provider: typing.Literal['remote'] = 'remote'
    fqdn: str = Field(description='Fully qualified domain name of the PostgreSQL server')

    @computed_field(description='The fully qualified domain name to connect to')
    @property
    def client_fqdn(self) -> str:
        return self.fqdn


InfraPGConfig = typing.Annotated[
    LocalPGConfig | RemotePGConfig,
    Field(discriminator='provider'),
]
