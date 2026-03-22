import enum
import pathlib
import socket
from typing import Any

from pydantic import Field, computed_field

from .base import RootConfigAware


class ClusterCNIKindEnum(str, enum.Enum):
    kind = "kind"
    cilium = "cilium"

class ClusterCNIConfig(RootConfigAware):
    kind: ClusterCNIKindEnum = Field(default=ClusterCNIKindEnum.kind)
    exclusive: bool = Field(default=False, description="If true, only one CNI plugin can be active at a time")
    ui: bool = Field(default=False, description="If true, deploy CNI UI")
    hostname: str = Field(default="cni", description="CNI UI hostname, if applicable")

class ClusterMeshKind(str, enum.Enum):
    none = "none"
    istio_sidecar = "istio-sidecar"
    istio_ambient = "istio-ambient"

class ClusterMeshConfig(RootConfigAware):
    enabled: bool = Field(default=False)
    kind: ClusterMeshKind = Field(default=ClusterMeshKind.istio_sidecar)
    ns: str = Field(default="istio-system")

class ClusterPKIConfig(RootConfigAware):
    ns: str = Field(default="cert-manager")
    crd: str = Field(
        default="https://github.com/cert-manager/cert-manager/releases/download/v1.17.1/cert-manager.crds.yaml"
    )
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


class ClusterEdgeKindEnum(str, enum.Enum):
    istio = "istio"
    istio_gateway_api = "istio-gateway-api"
    traefik = "traefik"

class ClusterEdgeConfig(RootConfigAware):
    kind: ClusterEdgeKindEnum = Field(default=ClusterEdgeKindEnum.istio_gateway_api)
    name: str = Field(default="edge")
    ns: str = Field(default="edge")
    gateway_api_crds: str = Field(
        default="https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.4.1/experimental-install.yaml"
    )
    traefik_repository: str = Field(default="docker.io/traefik")
    traefik_tag: str = Field(default="v3.6")
    traefik_hostname: str = Field(default="edge")
    traefik_dashboard_hostname: str = Field(default="dashboard")

class ClusterConfig(RootConfigAware):
    name: str = Field(description="Name of the cluster", default_factory=socket.gethostname)

    pod_subnet_cidr: str = Field(default="10.244.0.0/16")
    service_subnet_cidr: str = Field(default="10.96.0.0/12")

    control_plane_nodes: int = Field(default=1)
    worker_nodes: int = Field(default=3)

    cni: ClusterCNIConfig = Field(default_factory=ClusterCNIConfig)
    mesh: ClusterMeshConfig = Field(default_factory=ClusterMeshConfig)
    pki: ClusterPKIConfig = Field(default_factory=ClusterPKIConfig)
    edge: ClusterEdgeConfig = Field(default_factory=ClusterEdgeConfig)

    def model_post_init(self, context: Any, /) -> None:
        super().model_post_init(context)
        # We want to have an unqualified hostname
        if self.name == socket.gethostname() and self.name.endswith(".local"):
            self.name = self.name.replace(".local", "")
