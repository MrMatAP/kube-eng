import enum
import socket
from typing import Any

from pydantic import AnyHttpUrl, Field, computed_field

from .base import IdPClientRole, RootConfigAware


class ClusterCNIKindEnum(str, enum.Enum):
    kind = 'kind'
    cilium = 'cilium'


class ClusterCNIConfig(RootConfigAware):
    kind: ClusterCNIKindEnum = Field(default=ClusterCNIKindEnum.cilium)
    exclusive: bool = Field(
        default=False,
        description='If true, only one CNI plugin can be active at a time',
    )
    ui: bool = Field(default=False, description='If true, deploy CNI UI')
    hostname: str = Field(default='cni', description='CNI UI hostname, if applicable')


class ClusterMeshKind(str, enum.Enum):
    none = 'none'
    istio_sidecar = 'istio-sidecar'
    istio_ambient = 'istio-ambient'


class ClusterMeshConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    kind: ClusterMeshKind = Field(default=ClusterMeshKind.istio_ambient)
    ns: str = Field(default='istio-system')


class ClusterPKIConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    ns: str = Field(default='cert-manager')
    crd: str = Field(
        default='https://github.com/cert-manager/cert-manager/releases/download/v1.17.1/cert-manager.crds.yaml'
    )
    hostname: str = Field(default='pki')


class ClusterEdgeKindEnum(str, enum.Enum):
    istio = 'istio'
    istio_gateway_api = 'istio-gateway-api'
    traefik = 'traefik'


class ClusterEdgeConfig(RootConfigAware):
    kind: ClusterEdgeKindEnum = Field(default=ClusterEdgeKindEnum.istio_gateway_api)
    name: str = Field(default='gw-edge')
    ns: str = Field(default='edge')
    gateway_api_crds: str = Field(
        default='https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.4.1/experimental-install.yaml'
    )

    @computed_field
    @property
    def gateway_class(self) -> str:
        match self.kind:
            case ClusterEdgeKindEnum.istio:
                return 'istio'
            case ClusterEdgeKindEnum.istio_gateway_api:
                return 'istio'
            case ClusterEdgeKindEnum.traefik:
                return 'traefik'
            case _:
                raise ValueError(f'Unknown edge kind: {self.kind}')


class ClusterConfig(RootConfigAware):
    name: str = Field(
        description='Name of the cluster', default_factory=socket.gethostname
    )
    image: str = Field(
        description='Image to use for the cluster',
        default='kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5',
    )
    pod_subnet_cidr: str = Field(default='10.244.0.0/16')
    service_subnet_cidr: str = Field(default='10.96.0.0/12')
    control_plane_nodes: int = Field(default=1)
    worker_nodes: int = Field(default=3)

    admin_port: int = Field(default=8000)

    cni: ClusterCNIConfig = Field(default_factory=ClusterCNIConfig)
    mesh: ClusterMeshConfig = Field(default_factory=ClusterMeshConfig)
    pki: ClusterPKIConfig = Field(default_factory=ClusterPKIConfig)
    edge: ClusterEdgeConfig = Field(default_factory=ClusterEdgeConfig)

    @computed_field(description='Cluster Client Id')
    @property
    def client_id(self) -> str:
        return f'kind-{self.name}'

    @computed_field(description='Cluster Client Name')
    @property
    def client_name(self) -> str:
        return f'Kind :: {self.name}'

    @computed_field(description='Cluster Client Description')
    @property
    def client_description(self) -> str:
        return f'Kind Cluster on {self.name}'

    @computed_field(description='Cluster Roles')
    @property
    def client_roles(self) -> list[IdPClientRole]:
        return [
            IdPClientRole(name='kind-admin', description='Kind :: Admin'),
            IdPClientRole(name='kind-contributor', description='Kind :: Contributor'),
            IdPClientRole(name='kind-viewer', description='Kind :: Viewer'),
        ]

    @computed_field(description='Cluster admin endpoint')
    @property
    def admin_endpoint(self) -> AnyHttpUrl:
        return AnyHttpUrl(f'https://{self.name}.{self._root_config.infra.dns.domain}:{self.admin_port}')

    @computed_field(description='Cluster Callback URLs')
    @property
    def callback_urls(self) -> list[AnyHttpUrl]:
        return [self.admin_endpoint]

    def model_post_init(self, context: Any, /) -> None:
        super().model_post_init(context)
        # We want to have an unqualified hostname
        if self.name == socket.gethostname() and self.name.endswith('.local'):
            self.name = self.name.replace('.local', '')
