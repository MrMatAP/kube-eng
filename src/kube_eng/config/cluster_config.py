import socket

from pydantic import Field

from kube_eng import __helm_chart_path__
from .root_config_aware import RootConfigAware


class ClusterMeshConfig(RootConfigAware):
    kind: str = Field(default="istio")
    ns: str = Field(default="istio-system")


class ClusterPKIConfig(RootConfigAware):
    ns: str = Field(default="cert-manager")
    crd: str = Field(
        default="https://github.com/cert-manager/cert-manager/releases/download/v1.17.1/cert-manager.crds.yaml"
    )
    chart_ref: str = Field(default=str(__helm_chart_path__ / "kube-eng-cert-manager"))


class ClusterEdgeConfig(RootConfigAware):
    kind: str = Field(default="istio-gateway-api")
    name: str = Field(default="edge-ingress")
    ns: str = Field(default="edge")
    external_domain: str = Field(default="k8s")
    ingress_repository: str = Field(default="docker.io/traefik")
    ingress_tag: str = Field(default="v3.4.4")
    istio_gateway_api_crd: str = Field(
        default="https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.1/standard-install.yaml"
    )
    chart_ref: str = Field(default=str(__helm_chart_path__ / "kube-eng-edge"))


class ClusterConfig(RootConfigAware):
    name: str = Field(description="Name of the cluster", default_factory=socket.gethostname)

    control_plane_nodes: int = Field(default=1)
    worker_nodes: int = Field(default=3)

    mesh: ClusterMeshConfig = Field(default_factory=ClusterMeshConfig)
    pki: ClusterPKIConfig = Field(default_factory=ClusterPKIConfig)
    edge: ClusterEdgeConfig = Field(default_factory=ClusterEdgeConfig)
