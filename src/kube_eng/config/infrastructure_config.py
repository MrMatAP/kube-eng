import pathlib
import typing

from pydantic import Field, computed_field, field_validator

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


class LocalIdpConfig(RootConfigAware):
    """Keycloak IdP provisioned locally as a Docker container."""

    provider: typing.Literal['local'] = 'local'
    name: str = Field(default='idp', description='Name of the IdP container')
    image: str = Field(
        default='keycloak/keycloak:26.5.6', description='IdP container image'
    )
    host_ip: str = Field(
        default='127.0.0.1',
        description='IP address to expose the IdP on the host',
    )
    host_port: int = Field(
        default=8443, description='Port to expose the IdP on the host'
    )
    realm: str = Field(default='master', description='Realm to register clients in')
    admin_user: str = Field(default='admin', description='IdP administrative user')
    admin_password: str = Field(
        default='',
        description=(
            'IdP administrative password. If empty, defaults to the admin password'
        ),
    )
    db_name: str = Field(default='idp', description='Name of the IdP database')
    db_user: str = Field(default='idp', description='User for the IdP database')
    db_password: str = Field(
        default='',
        description=(
            'Password for the IdP database. If empty, defaults to the admin password'
        ),
    )

    @computed_field
    @property
    def config_path(self) -> pathlib.Path:
        """Directory to store IdP configuration in."""
        return self._root_config.config_path / 'idp'

    @computed_field
    @property
    def url(self) -> str:
        """Base URL of the IdP as reachable by consumers and this host."""
        return f'https://{self.name}.{self._root_config.host.dns.zone}:{self.host_port}'

    @computed_field
    @property
    def issuer_url(self) -> str:
        return f'{self.url}/realms/{self.realm}'


class RemoteIdpConfig(RootConfigAware):
    """Central IdP hosted elsewhere."""

    provider: typing.Literal['remote'] = 'remote'
    url: str = Field(
        description='Base URL of the IdP, e.g. https://idp.example.com:8443'
    )
    realm: str = Field(description='Realm to register clients in')
    admin_user: str = Field(description='IdP administrative user')
    admin_password: str = Field(description='IdP administrative password')

    @field_validator('url')
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip('/')

    @computed_field
    @property
    def issuer_url(self) -> str:
        return f'{self.url}/realms/{self.realm}'


class LocalS3Config(RootConfigAware):
    """S3-compatible storage provisioned locally as a Docker container."""

    provider: typing.Literal['local'] = 'local'
    name: str = Field(default='s3', description='Name of the S3 container')
    image: str = Field(default='rustfs/rustfs:latest', description='S3 container image')
    volume_name: str = Field(default='s3-volume', description='Name of the S3 volume')
    port: int = Field(
        default=9000, description='Port the S3 server listens on inside the container'
    )
    console_port: int = Field(
        default=9001, description='Port the S3 console listens on inside the container'
    )
    host_ip: str = Field(
        default='127.0.0.1',
        description='IP address to expose the S3 server on the host',
    )
    host_port: int = Field(
        default=9000, description='Port to expose the S3 server on the host'
    )
    host_console_port: int = Field(
        default=9001, description='Port to expose the S3 console on the host'
    )
    access_key: str = Field(default='admin', description='S3 access key')
    secret_key: str = Field(
        default='',
        description='S3 secret key. If empty, defaults to the admin password',
    )
    region: str = Field(default='us-east-1', description='S3 region name')

    @computed_field
    @property
    def config_path(self) -> pathlib.Path:
        """Directory to store S3 configuration in."""
        return self._root_config.config_path / 's3'

    @computed_field
    @property
    def endpoint(self) -> str:
        """Endpoint URL consumers (containers and cluster workloads) use."""
        return f'https://{self.name}.{self._root_config.host.dns.zone}:{self.port}'

    @computed_field
    @property
    def admin_endpoint(self) -> str:
        """Endpoint URL Ansible uses to administer S3 from this host."""
        return f'https://{self.name}.{self._root_config.host.dns.zone}:{self.host_port}'


class RemoteS3Config(RootConfigAware):
    """Central S3-compatible storage hosted elsewhere."""

    provider: typing.Literal['remote'] = 'remote'
    endpoint: str = Field(description='Endpoint URL of the S3 service')
    access_key: str = Field(description='S3 access key')
    secret_key: str = Field(description='S3 secret key')
    region: str = Field(default='us-east-1', description='S3 region name')

    @field_validator('endpoint')
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip('/')

    @computed_field
    @property
    def admin_endpoint(self) -> str:
        return self.endpoint


class LocalRegistryConfig(RootConfigAware):
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
    port: int = Field(
        default=5000, description='Port the registry listens on inside the container'
    )
    host_ip: str = Field(
        default='127.0.0.1',
        description='IP address to expose the registry on the host',
    )
    host_port: int = Field(
        default=5001, description='Port to expose the registry on the host'
    )

    @computed_field
    @property
    def config_path(self) -> pathlib.Path:
        """Directory to store registry configuration in."""
        return self._root_config.config_path / 'registry'

    @computed_field
    @property
    def url(self) -> str:
        """OCI URL for images and Helm charts."""
        return f'oci://{self.name}.{self._root_config.host.dns.zone}:{self.host_port}'

    @computed_field
    @property
    def https_url(self) -> str:
        return 'https://' + self.url.removeprefix('oci://')


class RemoteRegistryConfig(RootConfigAware):
    """Central OCI registry hosted elsewhere. Authenticate out of band (docker/helm login)."""

    provider: typing.Literal['remote'] = 'remote'
    url: str = Field(
        description='OCI URL of the registry, e.g. oci://harbor.example.com/kube-eng'
    )

    @field_validator('url')
    @classmethod
    def validate_oci_url(cls, value: str) -> str:
        if not value.startswith('oci://'):
            raise ValueError('registry url must start with oci://')
        return value.rstrip('/')

    @computed_field
    @property
    def https_url(self) -> str:
        return 'https://' + self.url.removeprefix('oci://')


InfraIdpConfig = typing.Annotated[
    LocalIdpConfig | RemoteIdpConfig,
    Field(discriminator='provider'),
]
InfraS3Config = typing.Annotated[
    LocalS3Config | RemoteS3Config,
    Field(discriminator='provider'),
]
InfraRegistryConfig = typing.Annotated[
    LocalRegistryConfig | RemoteRegistryConfig,
    Field(discriminator='provider'),
]


class InfrastructureConfig(RootConfigAware):
    """Core infrastructure the cluster and stack depend on."""

    postgresql: InfraPostgresqlConfig = Field(default_factory=LocalPostgresqlConfig)
    idp: InfraIdpConfig = Field(default_factory=LocalIdpConfig)
    s3: InfraS3Config = Field(default_factory=LocalS3Config)
    registry: InfraRegistryConfig = Field(default_factory=LocalRegistryConfig)
