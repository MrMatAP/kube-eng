import enum
import pathlib
import socket
from typing import Any

from pydantic import Field, computed_field

from .root_config_aware import RootConfigAware


class ClusterMeshKind(str, enum.Enum):
    istio = "istio"

class ClusterMeshConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    kind: ClusterMeshKind = Field(default=ClusterMeshKind.istio)
    ns: str = Field(default="istio-system")
    istio_gateway_api_crd: str = Field(
        default="https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.4.0/experimental-install.yaml"
    )

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
    ingress = "ingress"


class ClusterEdgeConfig(RootConfigAware):
    kind: ClusterEdgeKindEnum = Field(default=ClusterEdgeKindEnum.ingress)
    name: str = Field(default="edge-ingress")
    ns: str = Field(default="edge")
    ingress_repository: str = Field(default="docker.io/traefik")
    ingress_tag: str = Field(default="v3.6")
    ingress_hostname: str = Field(default="edge")


class ClusterConfig(RootConfigAware):
    name: str = Field(description="Name of the cluster", default_factory=socket.gethostname)

    control_plane_nodes: int = Field(default=1)
    worker_nodes: int = Field(default=3)

    mesh: ClusterMeshConfig = Field(default_factory=ClusterMeshConfig)
    pki: ClusterPKIConfig = Field(default_factory=ClusterPKIConfig)
    edge: ClusterEdgeConfig = Field(default_factory=ClusterEdgeConfig)

    def model_post_init(self, context: Any, /) -> None:
        super().model_post_init(context)
        # We want to have an unqualified hostname
        if self.name == socket.gethostname() and self.name.endswith(".local"):
            self.name = self.name.replace(".local", "")
