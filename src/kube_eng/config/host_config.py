import pathlib

from pydantic import Field, computed_field

from kube_eng import __version__, __helm_chart_path__
from .base import RootConfigAware
from .infra_pki_config import InfraPKIConfig


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
        return self._root_config.config_path / 'kind'


class HostToolKubectlConfig(RootConfigAware):
    path: pathlib.Path = Field(default=pathlib.Path('/opt/homebrew/bin/kubectl'))


class HostToolHelmConfig(RootConfigAware):
    path: pathlib.Path = Field(default=pathlib.Path('/opt/homebrew/bin/helm'))

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
        return self._root_config.config_path / 'helm'

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
    path: pathlib.Path = Field(
        default=pathlib.Path('/opt/homebrew/bin/cloud-provider-kind')
    )
    arch: str = Field(default='arm64')
    version: str = Field(default='0.11.1')

    @computed_field
    @property
    def url(self) -> str:
        """
        Construct the download URL for the cloud-provider-kind binary using the provided version and system architecture
        Returns:
            The download URL for the cloud-provider-kind binary
        """
        return f'https://github.com/kubernetes-sigs/cloud-provider-kind/releases/download/v{self.version}/cloud-provider-kind_{self.version}_darwin_{self.arch}.tar.gz'

    @computed_field
    @property
    def config_path(self) -> pathlib.Path:
        """
        Directory to store cloud_provider_kind files in.
        Returns:
            Path to the cloud_provider_kind directory.
        """
        return self._root_config.config_path / 'cloud_provider_kind'


class HostToolConfig(RootConfigAware):
    docker: HostToolDockerConfig = Field(default_factory=HostToolDockerConfig)
    kind: HostToolKindConfig = Field(default_factory=HostToolKindConfig)
    kubectl: HostToolKubectlConfig = Field(default_factory=HostToolKubectlConfig)
    helm: HostToolHelmConfig = Field(default_factory=HostToolHelmConfig)
    cloud_provider_kind: HostToolCloudProviderKindConfig = Field(
        default_factory=HostToolCloudProviderKindConfig
    )


class HostConfig(RootConfigAware):
    tool: HostToolConfig = Field(default_factory=HostToolConfig)
