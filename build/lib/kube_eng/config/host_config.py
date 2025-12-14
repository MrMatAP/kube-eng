import pathlib

from pydantic import Field, computed_field

from .root_config_aware import RootConfigAware

class HostToolDockerConfig(RootConfigAware):
    path: pathlib.Path = Field(default='/usr/local/bin/docker')

class HostToolKindConfig(RootConfigAware):
    path: pathlib.Path = Field(default='/opt/homebrew/bin/kind')

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
    path: pathlib.Path = Field(default='/opt/homebrew/bin/kubectl')

class HostToolCloudProviderKindConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    path: pathlib.Path = Field(default='/opt/homebrew/bin/cloud-provider-kind')
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
    path: pathlib.Path = Field(default='/opt/homebrew/sbin/cloud-provider-mdns')

    @computed_field
    @property
    def config_path(self) -> pathlib.Path:
        """
        Directory to store cloud_provider_mdns files in.
        Returns:
            Path to the cloud_provider_mdns directory.
        """
        return self._root_config.config_path / "cloud_provider_mdns"

class HostToolBindConfig(RootConfigAware):
    enabled: bool = Field(default=False)
    path: pathlib.Path = Field(default='/opt/homebrew/sbin/named')
    forwarders: str = Field(default='8.8.8.8; 4.4.4.4; 2001:4860:4860::8888; 2001:4860:4860::8844;')

    @computed_field
    @property
    def config_path(self) -> pathlib.Path:
        """
        Directory to store BIND files in.
        Returns:
            Path to the BIND directory.
        """
        return self._root_config.config_path / "bind"

class HostToolIstioCtlConfig(RootConfigAware):
    path: pathlib.Path = Field(default='/opt/homebrew/bin/istioctl')

class HostToolKustomizeConfig(RootConfigAware):
    path: pathlib.Path = Field(default='/opt/homebrew/bin/kustomize')

class HostToolConfig(RootConfigAware):
    docker: HostToolDockerConfig = Field(default_factory=HostToolDockerConfig)
    kind: HostToolKindConfig = Field(default_factory=HostToolKindConfig)
    kubectl: HostToolKubectlConfig = Field(default_factory=HostToolKubectlConfig)
    cloud_provider_kind: HostToolCloudProviderKindConfig = Field(default_factory=HostToolCloudProviderKindConfig)
    cloud_provider_mdns: HostToolCloudProviderMDNSConfig = Field(default_factory=HostToolCloudProviderMDNSConfig)
    bind: HostToolBindConfig = Field(default_factory=HostToolBindConfig)
    istioctl: HostToolIstioCtlConfig = Field(default_factory=HostToolIstioCtlConfig)
    kustomize: HostToolKustomizeConfig = Field(default_factory=HostToolKustomizeConfig)


class HostRegistryConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    name: str = Field(default="registry")
    port: int = Field(default=5001)
    image: str = Field(default="ghcr.io/project-zot/zot-linux-arm64:v2.1.11")
    volume_name: str = Field(default="registry-volume")


class HostPostgresqlConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    name: str = Field(default="pg")
    port: int = Field(default=5432)
    image: str = Field(default="postgres:16-alpine")
    volume_name: str = Field(default="pg-volume")


class HostMinioConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    name: str = Field(default="minio")
    port: int = Field(default=9000)
    console_port: int = Field(default=9001)
    image: str = Field(default="minio/minio:latest")
    volume_name: str = Field(default="minio-volume")

class HostConfig(RootConfigAware):
    tool: HostToolConfig = Field(default_factory=HostToolConfig)
    registry: HostRegistryConfig = Field(default_factory=HostRegistryConfig)
    postgresql: HostPostgresqlConfig = Field(default_factory=HostPostgresqlConfig)
    minio: HostMinioConfig = Field(default_factory=HostMinioConfig)
