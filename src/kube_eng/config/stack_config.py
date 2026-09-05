import enum
import secrets

from pydantic import Field, computed_field

from .base import IdPClientRole, RootConfigAware


class StackPrometheusConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    ns: str = Field(default='prometheus')
    hostname: str = Field(default='prometheus')
    service_monitor_crd: str = Field(
        default='https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/main/example/prometheus-operator-crd/monitoring.coreos.com_servicemonitors.yaml'
    )
    pod_monitor_crd: str = Field(
        default='https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/main/example/prometheus-operator-crd/monitoring.coreos.com_podmonitors.yaml'
    )

class StackMimirConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    ns: str = Field(default='mimir')
    hostname: str = Field(default='mimir')

class StackAlloyConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    ns: str = Field(default='alloy')
    hostname: str = Field(default='alloy')


class StackLokiConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    ns: str = Field(default='loki')
    hostname: str = Field(default='loki')


class StackGrafanaDBKind(str, enum.Enum):
    postgres = 'postgres'
    sqlite3 = 'sqlite3'


class StackGrafanaDBSSL(str, enum.Enum):
    disable = 'disable'
    require = 'require'
    verify_ca = 'verify-ca'
    verify_full = 'verify-full'


class StackGrafanaConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    ns: str = Field(default='grafana')
    hostname: str = Field(default='grafana')
    client_id: str = Field(default='kube-eng-grafana')
    admin_user: str = Field(default='admin')
    admin_password: str = Field(default_factory=lambda: secrets.token_urlsafe(16),
                                description='Grafana admin password')
    db_kind: StackGrafanaDBKind = Field(default=StackGrafanaDBKind.sqlite3)
    db_host: str = Field(default='pg')
    db_port: int = Field(default=5432)
    db_name: str = Field(default='grafana')
    db_user: str = Field(default='grafana')
    db_password: str = Field(default='grafana')
    db_ssl_mode: StackGrafanaDBSSL = Field(default=StackGrafanaDBSSL.require)

    @computed_field(description='Grafana roles')
    @property
    def client_roles(self) -> list[IdPClientRole]:
        return [
            IdPClientRole(
                name='grafana-viewer', description='Kube-Eng :: Grafana :: Viewers'
            ),
            IdPClientRole(
                name='grafana-editor', description='Kube-Eng :: Grafana :: Editors'
            ),
            IdPClientRole(
                name='grafana-admin', description='Kube-Eng :: Grafana :: Admins'
            ),
        ]


class StackTempoConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    ns: str = Field(default='tempo')
    hostname: str = Field(default='tempo')


class StackKialiConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    ns: str = Field(default='kiali')
    hostname: str = Field(default='kiali')
    version: str = Field(default='v2.18.0')
    client_id: str = Field(default='kube-eng-kiali')


class StackConfig(RootConfigAware):
    prometheus: StackPrometheusConfig = Field(default_factory=StackPrometheusConfig)
    mimir: StackMimirConfig = Field(default_factory=StackMimirConfig)
    alloy: StackAlloyConfig = Field(default_factory=StackAlloyConfig)
    loki: StackLokiConfig = Field(default_factory=StackLokiConfig)
    grafana: StackGrafanaConfig = Field(default_factory=StackGrafanaConfig)
    tempo: StackTempoConfig = Field(default_factory=StackTempoConfig)
    kiali: StackKialiConfig = Field(default_factory=StackKialiConfig)
