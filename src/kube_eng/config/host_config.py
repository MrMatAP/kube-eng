import pathlib

from pydantic import BaseModel, Field


class HostToolDockerConfig(BaseModel):
    path: pathlib.Path = Field(default='/usr/local/bin/docker')

class HostToolKindConfig(BaseModel):
    path: pathlib.Path = Field(default='/opt/homebrew/bin/kind')

class HostToolKubectlConfig(BaseModel):
    path: pathlib.Path = Field(default='/opt/homebrew/bin/kubectl')

class HostToolCloudProviderKindConfig(BaseModel):
    path: pathlib.Path = Field(default='/opt/homebrew/bin/cloud-provider-kind')
    url: str = Field(default='https://github.com/kubernetes-sigs/cloud-provider-kind/releases/download/v0.10.0/cloud-provider-kind_0.10.0_darwin_arm64.tar.gz')
    enabled: bool = Field(default=True)

class HostToolCloudProviderMDNSConfig(BaseModel):
    path: pathlib.Path = Field(default='/opt/homebrew/sbin/cloud-provider-mdns')
    enabled: bool = Field(default=False)

class HostToolBindConfig(BaseModel):
    path: pathlib.Path = Field(default='/opt/homebrew/sbin/named')
    enabled: bool = Field(default=False)
    forwarders: str = Field(default='8.8.8.8; 4.4.4.4; 2001:4860:4860::8888; 2001:4860:4860::8844;')

class HostToolIstioCtlConfig(BaseModel):
    path: pathlib.Path = Field(default='/opt/homebrew/bin/istioctl')

class HostToolKustomizeConfig(BaseModel):
    path: pathlib.Path = Field(default='/opt/homebrew/bin/kustomize')

class HostToolConfig(BaseModel):
    docker: HostToolDockerConfig = Field(default_factory=HostToolDockerConfig)
    kind: HostToolKindConfig = Field(default_factory=HostToolKindConfig)
    kubectl: HostToolKubectlConfig = Field(default_factory=HostToolKubectlConfig)
    cloud_provider_kind: HostToolCloudProviderKindConfig = Field(default_factory=HostToolCloudProviderKindConfig)
    cloud_provider_mdns: HostToolCloudProviderMDNSConfig = Field(default_factory=HostToolCloudProviderMDNSConfig)
    bind: HostToolBindConfig = Field(default_factory=HostToolBindConfig)
    istioctl: HostToolIstioCtlConfig = Field(default_factory=HostToolIstioCtlConfig)
    kustomize: HostToolKustomizeConfig = Field(default_factory=HostToolKustomizeConfig)


class HostRegistryConfig(BaseModel):
    enabled: bool = Field(default=True)
    name: str = Field(default="registry")
    port: int = Field(default=5001)
    image: str = Field(default="ghcr.io/project-zot/zot-linux-arm64:v2.1.11")
    volume_name: str = Field(default="registry-volume")


class HostPostgresqlConfig(BaseModel):
    enabled: bool = Field(default=True)
    name: str = Field(default="pg")
    port: int = Field(default=5432)
    image: str = Field(default="postgres:16-alpine")
    volume_name: str = Field(default="pg-volume")


class HostMinioConfig(BaseModel):
    enabled: bool = Field(default=True)
    name: str = Field(default="minio")
    port: int = Field(default=9000)
    console_port: int = Field(default=9001)
    image: str = Field(default="minio/minio:latest")
    volume_name: str = Field(default="minio-volume")


class HostConfig(BaseModel):
    tool: HostToolConfig = Field(default_factory=HostToolConfig)
    registry: HostRegistryConfig = Field(default_factory=HostRegistryConfig)
    postgresql: HostPostgresqlConfig = Field(default_factory=HostPostgresqlConfig)
    minio: HostMinioConfig = Field(default_factory=HostMinioConfig)
