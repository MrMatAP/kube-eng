from pydantic import BaseModel, Field


class StackPrometheusConfig(BaseModel):
    enabled: bool = Field(default=True)
    ns: str = Field(default="prometheus")
    hostname: str = Field(default="prometheus")


class StackAlloyConfig(BaseModel):
    enabled: bool = Field(default=True)
    ns: str = Field(default="alloy")
    hostname: str = Field(default="alloy")


class StackLokiConfig(BaseModel):
    enabled: bool = Field(default=True)
    ns: str = Field(default="loki")
    hostname: str = Field(default="loki")


class StackKeycloakConfig(BaseModel):
    enabled: bool = Field(default=True)
    ns: str = Field(default="keycloak")
    hostname: str = Field(default="keycloak")
    operator_version: str = Field(default="26.4.7")


class StackGrafanaConfig(BaseModel):
    enabled: bool = Field(default=True)
    ns: str = Field(default="grafana")
    hostname: str = Field(default="grafana")
    client_id: str = Field(default="grafana")
    admin_user: str = Field(default="admin")


class StackJaegerConfig(BaseModel):
    enabled: bool = Field(default=True)
    ns: str = Field(default="jaeger")
    hostname: str = Field(default="jaeger")


class StackJaegerV2Config(BaseModel):
    enabled: bool = Field(default=False)
    ns: str = Field(default="jaeger")
    hostname: str = Field(default="jaeger")


class StackKialiConfig(BaseModel):
    enabled: bool = Field(default=True)
    ns: str = Field(default="kiali")
    hostname: str = Field(default="kiali")
    version: str = Field(default="v2.18.0")


class StackConfig(BaseModel):
    prometheus: StackPrometheusConfig = Field(default_factory=StackPrometheusConfig)
    alloy: StackAlloyConfig = Field(default_factory=StackAlloyConfig)
    loki: StackLokiConfig = Field(default_factory=StackLokiConfig)
    keycloak: StackKeycloakConfig = Field(default_factory=StackKeycloakConfig)
    grafana: StackGrafanaConfig = Field(default_factory=StackGrafanaConfig)
    jaeger: StackJaegerConfig = Field(default_factory=StackJaegerConfig)
    jaeger_v2: StackJaegerV2Config = Field(default_factory=StackJaegerV2Config)
    kiali: StackKialiConfig = Field(default_factory=StackKialiConfig)
