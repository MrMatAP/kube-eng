import typing

from pydantic import Field, computed_field

from .base import RootConfigAware


class LocalPostgresqlConfig(RootConfigAware):
    """PostgreSQL provisioned locally as a Docker container."""

    provider: typing.Literal['local'] = 'local'
    name: str = Field(default='pg', description='Name of the PostgreSQL container')
    image: str = Field(
        default='postgres:18-alpine', description='PostgreSQL container image'
    )
    volume_name: str = Field(
        default='pg-volume', description='Name of the PostgreSQL volume'
    )
    host_ip: str = Field(
        default='127.0.0.1',
        description='IP address to expose the PostgreSQL server on the host',
    )
    host_port: int = Field(
        default=5432,
        description='Port to expose the PostgreSQL server on the host',
    )
    admin_user: str = Field(default='postgres', description='PostgreSQL superuser')
    admin_password: str = Field(
        default='',
        description=(
            'PostgreSQL superuser password. If empty, defaults to the admin password'
        ),
    )

    @computed_field
    @property
    def client_host(self) -> str:
        """Hostname consumers (containers and cluster workloads) connect to."""
        return f'{self.name}.{self._root_config.host.dns.zone}'

    @computed_field
    @property
    def client_port(self) -> int:
        """Port consumers connect to (the in-network container port)."""
        return 5432

    @computed_field
    @property
    def admin_host(self) -> str:
        """Hostname Ansible uses to administer the server from this host."""
        return self.host_ip

    @computed_field
    @property
    def admin_port(self) -> int:
        """Port Ansible uses to administer the server from this host."""
        return self.host_port


class RemotePostgresqlConfig(RootConfigAware):
    """Central PostgreSQL hosted elsewhere."""

    provider: typing.Literal['remote'] = 'remote'
    host: str = Field(description='Hostname of the PostgreSQL server')
    port: int = Field(default=5432, description='Port of the PostgreSQL server')
    admin_user: str = Field(description='PostgreSQL administrative user')
    admin_password: str = Field(description='PostgreSQL administrative password')

    @computed_field
    @property
    def client_host(self) -> str:
        return self.host

    @computed_field
    @property
    def client_port(self) -> int:
        return self.port

    @computed_field
    @property
    def admin_host(self) -> str:
        return self.host

    @computed_field
    @property
    def admin_port(self) -> int:
        return self.port


InfraPostgresqlConfig = typing.Annotated[
    LocalPostgresqlConfig | RemotePostgresqlConfig,
    Field(discriminator='provider'),
]


class InfrastructureConfig(RootConfigAware):
    """Core infrastructure the cluster and stack depend on."""

    postgresql: InfraPostgresqlConfig = Field(default_factory=LocalPostgresqlConfig)
