import enum
import socket
from typing import Any

from pydantic import Field, computed_field

from .base import RootConfigAware


class ClusterCNIKindEnum(str, enum.Enum):
    kind = "kind"
    cilium = "cilium"

class ClusterCNIConfig(RootConfigAware):
    kind: ClusterCNIKindEnum = Field(default=ClusterCNIKindEnum.cilium)
    exclusive: bool = Field(default=False, description="If true, only one CNI plugin can be active at a time")
    ui: bool = Field(default=False, description="If true, deploy CNI UI")
    hostname: str = Field(default="cni", description="CNI UI hostname, if applicable")

class ClusterMeshKind(str, enum.Enum):
    none = "none"
    istio_sidecar = "istio-sidecar"
    istio_ambient = "istio-ambient"

class ClusterMeshConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    kind: ClusterMeshKind = Field(default=ClusterMeshKind.istio_ambient)
    ns: str = Field(default="istio-system")

class ClusterPKIConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    ns: str = Field(default="cert-manager")
    crd: str = Field(
        default="https://github.com/cert-manager/cert-manager/releases/download/v1.17.1/cert-manager.crds.yaml"
    )
    hostname: str = Field(default="pki")

class ClusterEdgeKindEnum(str, enum.Enum):
    istio = "istio"
    istio_gateway_api = "istio-gateway-api"
    traefik = "traefik"

class ClusterEdgeConfig(RootConfigAware):
    kind: ClusterEdgeKindEnum = Field(default=ClusterEdgeKindEnum.istio_gateway_api)
    name: str = Field(default="gw-edge")
    ns: str = Field(default="edge")
    gateway_api_crds: str = Field(
        default="https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.4.1/experimental-install.yaml"
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
                raise ValueError(f"Unknown edge kind: {self.kind}")

class ClusterOIDCConfig(RootConfigAware):
    username_claim: str = Field(default="preferred_username")
    groups_claim: str = Field(default="groups")

    @computed_field
    @property
    def issuer_url(self) -> str:
        """
        Computed IDP issuer URL for the cluster
        Returns:
            Computed IDP issuer URL for the cluster
        """
        return f"https://{self._root_config.host.idp.name}.{self._root_config.host.dns.zone}:{self._root_config.host.idp.host_port }/realms/master"

class ClusterDNSConfig(RootConfigAware):
    server: str = Field(default="127.0.0.1", description="DNS server IP address. This should be 127.0.0.1 for local DNS")
    key_name: str = Field(default="update-key", description='Name of the key to sign dynamic DNS updates with')
    key_algorithm: str = Field(default="hmac-sha256", description='Algorithm to use for signing dynamic DNS updates')
    key_secret: str = Field(default="", description='Secret containing the key to sign dynamic DNS updates with. If empty, defaults to the admin password')
    protocol: str = Field(default="tcp", description="DNS server protocol for DNS updates")
    ttl: int = Field(default=1800, description="Time to live (TTL) for DNS records")

class ClusterRegistryConfig(RootConfigAware):
    url: str = Field(default="", description="URL of the registry to use for images and Helm charts")

class ClusterConfig(RootConfigAware):
    name: str = Field(description="Name of the cluster", default_factory=socket.gethostname)
    pod_subnet_cidr: str = Field(default="10.244.0.0/16")
    service_subnet_cidr: str = Field(default="10.96.0.0/12")
    control_plane_nodes: int = Field(default=1)
    worker_nodes: int = Field(default=3)

    dns: ClusterDNSConfig = Field(default_factory=ClusterDNSConfig)
    registry: ClusterRegistryConfig = Field(default_factory=ClusterRegistryConfig)
    cni: ClusterCNIConfig = Field(default_factory=ClusterCNIConfig)
    mesh: ClusterMeshConfig = Field(default_factory=ClusterMeshConfig)
    pki: ClusterPKIConfig = Field(default_factory=ClusterPKIConfig)
    oidc: ClusterOIDCConfig = Field(default_factory=ClusterOIDCConfig)
    edge: ClusterEdgeConfig = Field(default_factory=ClusterEdgeConfig)

    def model_post_init(self, context: Any, /) -> None:
        super().model_post_init(context)
        # We want to have an unqualified hostname
        if self.name == socket.gethostname() and self.name.endswith(".local"):
            self.name = self.name.replace(".local", "")
