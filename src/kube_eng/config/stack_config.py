from pydantic import Field

from kube_eng import __helm_chart_path__
from .root_config_aware import RootConfigAware


class StackPrometheusConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    ns: str = Field(default="prometheus")
    hostname: str = Field(default="prometheus")
    chart_ref: str = Field(default=str(__helm_chart_path__ / "kube-eng-prometheus"))


class StackAlloyConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    ns: str = Field(default="alloy")
    hostname: str = Field(default="alloy")
    chart_ref: str = Field(default=str(__helm_chart_path__ / "kube-eng-alloy"))


class StackLokiConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    ns: str = Field(default="loki")
    hostname: str = Field(default="loki")
    chart_ref: str = Field(default=str(__helm_chart_path__ / "kube-eng-loki"))


class StackKeycloakConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    ns: str = Field(default="keycloak")
    hostname: str = Field(default="keycloak")
    operator_version: str = Field(default="26.4.7")
    operator_chart_ref: str = Field(default=str(__helm_chart_path__ / "kube-eng-keycloak-operator"))
    chart_ref: str = Field(default=str(__helm_chart_path__ / "kube-eng-operator"))


class StackGrafanaConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    ns: str = Field(default="grafana")
    hostname: str = Field(default="grafana")
    client_id: str = Field(default="grafana")
    admin_user: str = Field(default="admin")
    chart_ref: str = Field(default=str(__helm_chart_path__ / "kube-eng-grafana"))


class StackJaegerConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    ns: str = Field(default="jaeger")
    hostname: str = Field(default="jaeger")
    chart_ref: str = Field(default=str(__helm_chart_path__ / "kube-eng-jaeger"))


class StackJaegerV2Config(RootConfigAware):
    enabled: bool = Field(default=False)
    ns: str = Field(default="jaeger")
    hostname: str = Field(default="jaeger")
    chart_ref: str = Field(default=str(__helm_chart_path__ / "kube-eng-jaeger-v2"))


class StackKialiConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    ns: str = Field(default="kiali")
    hostname: str = Field(default="kiali")
    version: str = Field(default="v2.18.0")
    chart_ref: str = Field(default=str(__helm_chart_path__ / "kube-eng-kiali"))


class StackConfig(RootConfigAware):
    prometheus: StackPrometheusConfig = Field(default_factory=StackPrometheusConfig)
    alloy: StackAlloyConfig = Field(default_factory=StackAlloyConfig)
    loki: StackLokiConfig = Field(default_factory=StackLokiConfig)
    keycloak: StackKeycloakConfig = Field(default_factory=StackKeycloakConfig)
    grafana: StackGrafanaConfig = Field(default_factory=StackGrafanaConfig)
    jaeger: StackJaegerConfig = Field(default_factory=StackJaegerConfig)
    jaeger_v2: StackJaegerV2Config = Field(default_factory=StackJaegerV2Config)
    kiali: StackKialiConfig = Field(default_factory=StackKialiConfig)
