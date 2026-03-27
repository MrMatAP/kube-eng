import enum
import pathlib

from pydantic import Field, computed_field

from kube_eng import __version__, __helm_chart_path__
from .base import RootConfigAware

class HostToolDockerConfig(RootConfigAware):
    path: pathlib.Path = Field(default=pathlib.Path('/usr/local/bin/docker'))

class HostToolKindConfig(RootConfigAware):
    path: pathlib.Path = Field(default=pathlib.Path('/opt/homebrew/bin/kind'))

    @computed_field
    @property
    def config_path(self) -> pathlib.Path:
        """
        Directory to store kind configuration in.
        Returns:
            Path to the kind directory.
        """
        return self._root_config.config_path / "kind"

class HostToolKubectlConfig(RootConfigAware):
    path: pathlib.Path = Field(default=pathlib.Path('/opt/homebrew/bin/kubectl'))

class HostToolHelmConfig(RootConfigAware):
    path: pathlib.Path = Field(default=pathlib.Path('/opt/homebrew/Cellar/helm@3/3.20.1/bin/helm'))

    @computed_field
    @property
    def chart_path(self) -> pathlib.Path:
        """
        Path to the included Helm charts
        Returns:
            Path to the included Helm charts
        """
        return __helm_chart_path__

    @computed_field
    @property
    def packaged_chart_path(self) -> pathlib.Path:
        """
        Path to the packaged Helm charts
        Returns:
            Path to the packaged Helm charts
        """
        return self._root_config.config_path / "helm"

    @computed_field
    @property
    def chart_version(self) -> str:
        """
        Adjust the kube_eng version to be acceptable for Helm chart versioning.
        Returns:
            The kube-chart version formatted for Helm
        """
        return __version__.replace('.dev', '-dev')

class HostToolCloudProviderKindConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    path: pathlib.Path = Field(default=pathlib.Path('/opt/homebrew/bin/cloud-provider-kind'))
    url: str = Field(default='https://github.com/kubernetes-sigs/cloud-provider-kind/releases/download/v0.10.0/cloud-provider-kind_0.10.0_darwin_arm64.tar.gz')

    @computed_field
    @property
    def config_path(self) -> pathlib.Path:
        """
        Directory to store cloud_provider_kind files in.
        Returns:
            Path to the cloud_provider_kind directory.
        """
        return self._root_config.config_path / "cloud_provider_kind"

class HostToolCloudProviderMDNSConfig(RootConfigAware):
    enabled: bool = Field(default=False)
    path: pathlib.Path = Field(default=pathlib.Path('/opt/homebrew/sbin/cloud-provider-mdns'))

    @computed_field
    @property
    def config_path(self) -> pathlib.Path:
        """
        Directory to store cloud_provider_mdns files in.
        Returns:
            Path to the cloud_provider_mdns directory.
        """
        return self._root_config.config_path / "cloud_provider_mdns"

class HostToolConfig(RootConfigAware):
    docker: HostToolDockerConfig = Field(default_factory=HostToolDockerConfig)
    kind: HostToolKindConfig = Field(default_factory=HostToolKindConfig)
    kubectl: HostToolKubectlConfig = Field(default_factory=HostToolKubectlConfig)
    helm: HostToolHelmConfig = Field(default_factory=HostToolHelmConfig)
    cloud_provider_kind: HostToolCloudProviderKindConfig = Field(default_factory=HostToolCloudProviderKindConfig)
    cloud_provider_mdns: HostToolCloudProviderMDNSConfig = Field(default_factory=HostToolCloudProviderMDNSConfig)

class HostPKIConfig(RootConfigAware):
    key_type: str = Field(default="ECC")
    key_curve: str = Field(default="secp384r1")
    key_size: int = Field(default=4096)
    crt_validity: str = Field(default="+825d")

    @computed_field
    @property
    def config_path(self) -> pathlib.Path:
        """
        Directory to store PKI files in.
        Returns:
            Path to the PKI directory.
        """
        return self._root_config.config_path / "pki"

    @computed_field
    @property
    def ca_key_path(self) -> pathlib.Path:
        """
        Constructed path to the CA key file on the host
        Returns:
            Path to the CA key file on the host
        """
        return self.config_path / "ca.key"

    @computed_field
    @property
    def ca_path(self) -> pathlib.Path:
        """
        Constructed path to the CA certificate file on the host
        Returns:
            Path the CA certificate file on the host
        """
        return self.config_path / "ca.pem"

    @computed_field
    @property
    def ca_truststore_path(self) -> pathlib.Path:
        """
        Computed path to the CA truststore file on the host
        Returns:
            Path to the CA truststore file on the host
        """
        return self.config_path / "truststore.pem"

class HostDNSKindEnum(str, enum.Enum):
    local = "local"
    remote = "remote"

class HostDNSConfig(RootConfigAware):
    kind: HostDNSKindEnum = Field(default=HostDNSKindEnum.local, description='Whether to run a local DNS server in a container image or use a remote one')
    name: str = Field(default="dns", description='Name of the DNS container')
    image: str = Field(default="ubuntu/bind9:latest", description="DNS container image")
    cache_volume_name: str = Field(default="dns-volume-cache", description='Name of the DNS cache volume')
    zones_volume_name: str = Field(default="dns-volume-zones", description='Name of the DNS volume for zones')
    server: str = Field(default="127.0.0.1", description="DNS server IP address. This should be 127.0.0.1 for local DNS")
    port: int = Field(default=53, description="DNS server port to bind, used for local DNS server only")
    control_port: int = Field(default=953, description="DNS server control port, used for local DNS server only")
    key_name: str = Field(default="update-key", description='Name of the key to sign dynamic DNS updates with')
    key_algorithm: str = Field(default="hmac-sha256", description='Algorithm to use for signing dynamic DNS updates')
    key_secret: str = Field(default="", description='Secret containing the key to sign dynamic DNS updates with. If empty, defaults to the admin password')
    protocol: str = Field(default="tcp", description="DNS server protocol for DNS updates")
    ttl: int = Field(default=1800, description="Time to live (TTL) for DNS records")
    host_ip: str = Field(default="127.0.0.1", description="IP address to expose the DNS server on the host")
    host_port: int = Field(default=53, description="Port to expose the DNS server on the host")
    host_control_port: int = Field(default=953, description="Port to expose the DNS server control port on the host")

    @computed_field
    @property
    def config_path(self) -> pathlib.Path:
        """
        Directory to store DNS configuration in.
        Returns:
            Path to the DNS configuration directory.
        """
        return self._root_config.config_path / "dns"

    @computed_field
    @property
    def zone(self) -> str:
        """
        Computed name of the DNS zone to serve
        Returns:
            The authoritative zone to serve
        """
        return f'{self._root_config.cluster.name}.k8s'

class HostRegistryConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    name: str = Field(default="registry")
    port: int = Field(default=5000)
    image: str = Field(default="ghcr.io/project-zot/zot-linux-arm64:v2.1.15")
    volume_name: str = Field(default="registry-volume")
    host_ip: str = Field(default="127.0.0.1", description="IP address to expose the registry on the host")
    host_port: int = Field(default=5001, description="Port to expose the registry on the host")

    @computed_field
    @property
    def config_path(self) -> pathlib.Path:
        """
        Directory to store registry configuration in.
        Returns:
            Path to the registry configuration directory.
        """
        return self._root_config.config_path / "registry"

class HostPostgresqlConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    name: str = Field(default="pg")
    port: int = Field(default=5432)
    image: str = Field(default="postgres:16-alpine")
    volume_name: str = Field(default="pg-volume")
    host_ip: str = Field(default="127.0.0.1", description="IP address to expose the PostgreSQL server on the host")
    host_port: int = Field(default=5432, description="Port to expose the PostgreSQL server on the host")

class HostIDPConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    name: str = Field(default="idp")
    image: str = Field(default="keycloak/keycloak:26.5.6")
    port: int = Field(default=8443)
    db_user: str = Field(default="idp")
    db_name: str = Field(default="idp")
    host_ip: str = Field(default="127.0.0.1", description="IP address to expose the IDP server on the host")
    host_port: int = Field(default=8443, description="Port to expose the IDP server on the host")

    @computed_field
    @property
    def config_path(self) -> pathlib.Path:
        """
        Directory to store IDP configuration in.
        Returns:
            Path to the IDP configuration directory.
        """
        return self._root_config.config_path / "idp"

class HostS3Config(RootConfigAware):
    enabled: bool = Field(default=True)
    name: str = Field(default="s3")
    port: int = Field(default=9000)
    console_port: int = Field(default=9001)
    image: str = Field(default="rustfs/rustfs:latest")
    volume_name: str = Field(default="s3-volume")
    host_ip: str = Field(default="127.0.0.1", description="IP address to expose the S3 server on the host")
    host_port: int = Field(default=9000, description="Port to expose the S3 server on the host")
    host_console_port: int = Field(default=9001, description="Port to expose the S3 console on the host")

    @computed_field
    @property
    def config_path(self) -> pathlib.Path:
        """
        Directory to store Kafka configuration in.
        Returns:
            Path to the S3 configuration directory.
        """
        return self._root_config.config_path / "s3"

class HostKafkaConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    name: str = Field(default="kafka")
    port: int = Field(default=9092)
    image: str = Field(default="apache/kafka:latest")
    volume_name: str = Field(default="kafka-volume")
    host_ip: str = Field(default="127.0.0.1", description="IP address to expose the Kafka server on the host")
    host_port: int = Field(default=9092, description="Port to expose the Kafka server on the host")

    @computed_field
    @property
    def config_path(self) -> pathlib.Path:
        """
        Directory to store Kafka configuration in.
        Returns:
            Path to the Kafka configuration directory.
        """
        return self._root_config.config_path / "kafka"

class HostConfig(RootConfigAware):
    tool: HostToolConfig = Field(default_factory=HostToolConfig)
    pki: HostPKIConfig = Field(default_factory=HostPKIConfig)
    dns: HostDNSConfig = Field(default_factory=HostDNSConfig)
    registry: HostRegistryConfig = Field(default_factory=HostRegistryConfig)
    postgresql: HostPostgresqlConfig = Field(default_factory=HostPostgresqlConfig)
    idp: HostIDPConfig = Field(default_factory=HostIDPConfig)
    s3: HostS3Config = Field(default_factory=HostS3Config)
    kafka: HostKafkaConfig = Field(default_factory=HostKafkaConfig)
