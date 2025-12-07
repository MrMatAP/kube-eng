import pathlib
import socket

from pydantic import BaseModel, Field


class ClusterMeshConfig(BaseModel):
    kind: str = Field(default="istio")
    ns: str = Field(default="istio-system")


class ClusterPKIConfig(BaseModel):
    ns: str = Field(default="cert-manager")
    crd: str = Field(
        default="https://github.com/cert-manager/cert-manager/releases/download/v1.17.1/cert-manager.crds.yaml"
    )


class ClusterEdgeConfig(BaseModel):
    kind: str = Field(default="istio-gateway-api")
    name: str = Field(default="edge-ingress")
    ns: str = Field(default="edge")
    external_domain: str = Field(default="k8s")
    ingress_repository: str = Field(default="docker.io/traefik")
    ingress_tag: str = Field(default="v3.4.4")
    istio_gateway_api_crd: str = Field(
        default="https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.1/standard-install.yaml"
    )


class ClusterConfig(BaseModel):
    name: str = Field(description="Name of the cluster", default_factory=socket.gethostname)

    control_plane_nodes: int = Field(default=1)
    worker_nodes: int = Field(default=3)

    mesh: ClusterMeshConfig = Field(default_factory=ClusterMeshConfig)
    pki: ClusterPKIConfig = Field(default_factory=ClusterPKIConfig)
    edge: ClusterEdgeConfig = Field(default_factory=ClusterEdgeConfig)
