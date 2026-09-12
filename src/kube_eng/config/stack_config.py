import enum
import secrets

from pydantic import Field, computed_field

from .base import IdPClientRole, RootConfigAware

# Convention for every optional cross-component integration in this hierarchy
# (Prometheus -> Mimir, Alloy -> Mimir, Alloy -> Loki, ...): a stored
# `enabled: bool` plus a stored `uri: str` the user may override, and a
# `push_url` computed_field that resolves to `uri` if set, else the target
# component's own `push_url` if it is enabled locally, else raises. This
# keeps exactly one source of truth per integration and lets every consumer
# (Ansible playbooks, Helm chart values) read a single resolved field instead
# of re-deriving the target URL themselves. See docs/adr for the write-up.


class StackPrometheusMimirConfig(RootConfigAware):
    """Whether this Prometheus instance also remote_writes into Mimir."""

    # True by default: stack.mimir already defaults enabled, and prior to
    # this option existing, Prometheus always remote_wrote into Mimir
    # whenever stack.mimir.enabled was true (unconditionally, no separate
    # switch). An existing config with no stack.prometheus.mimir key must
    # keep doing that after upgrade, not silently stop.
    enabled: bool = Field(
        default=True, description='Also remote_write scraped metrics into Mimir'
    )
    uri: str = Field(
        default='',
        description=(
            'Mimir remote_write endpoint. Left blank, defaults to the local '
            'Mimir install if stack.mimir.enabled'
        ),
    )

    @computed_field(description='Resolved Mimir remote_write endpoint')
    @property
    def push_url(self) -> str:
        if not self.enabled:
            return ''
        if self.uri:
            return self.uri
        if self._root_config.stack.mimir.enabled:
            return self._root_config.stack.mimir.push_url
        raise ValueError(
            'stack.prometheus.mimir.enabled is set but stack.mimir is disabled '
            'and stack.prometheus.mimir.uri is empty. Enable stack.mimir or set '
            'stack.prometheus.mimir.uri explicitly.'
        )


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
    mimir: StackPrometheusMimirConfig = Field(
        default_factory=StackPrometheusMimirConfig
    )

    @computed_field(description='PromQL query endpoint used by Grafana')
    @property
    def query_url(self) -> str:
        return f'http://prometheus-operated.{self.ns}.svc.cluster.local:9090/'

    @computed_field(
        description=(
            'Whether the kube-eng-prometheus chart release should exist at '
            'all -- true if the Prometheus server itself is wanted, or if '
            'stack.alloy.metrics only wants the ServiceMonitor/PodMonitor '
            'CRDs and exporters (kube-state-metrics, node-exporter) that '
            'chart also installs, with the server itself switched off'
        )
    )
    @property
    def chart_enabled(self) -> bool:
        alloy = self._root_config.stack.alloy
        # alloy.metrics.enabled is meaningless when Alloy itself won't run
        # (stack_apply.yml's "Deploy Alloy" block is gated on alloy.enabled)
        # -- without this check, disabling Alloy entirely while its
        # metrics.enabled default (True) is left untouched would still pull
        # in the whole Prometheus chart for CRDs nothing consumes.
        return self.enabled or (alloy.enabled and alloy.metrics.enabled)


class StackMimirConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    ns: str = Field(default='mimir')
    hostname: str = Field(default='mimir')

    @computed_field(description='Remote-write ingestion endpoint')
    @property
    def push_url(self) -> str:
        return f'http://mimir-gateway.{self.ns}.svc.cluster.local/api/v1/push'

    @computed_field(description='PromQL query endpoint used by Grafana')
    @property
    def query_url(self) -> str:
        # Mimir's gateway serves the Prometheus-compatible query API under
        # /prometheus by default (see mimir.prometheusHttpPrefix in the
        # vendored mimir-distributed chart); this stack never overrides it.
        return f'http://mimir-gateway.{self.ns}.svc.cluster.local/prometheus'


class StackAlloyMetricsConfig(RootConfigAware):
    """Whether Alloy should scrape metrics and remote_write them into Mimir."""

    # True by default, matching stack.alloy.logs.enabled: when Alloy itself
    # is enabled it should collect both signals out of the box. This is a
    # static default rather than one derived from stack.alloy.enabled at
    # read time because the "Deploy Alloy" block in stack_apply.yml is
    # itself gated on stack.alloy.enabled -- if that's false this value is
    # never consulted, so a static default is equivalent and far simpler.
    enabled: bool = Field(
        default=True, description='Scrape metrics and remote_write them into Mimir'
    )
    uri: str = Field(
        default='',
        description=(
            'Mimir remote_write endpoint. Left blank, defaults to the local '
            'Mimir install if stack.mimir.enabled'
        ),
    )

    @computed_field(description='Resolved Mimir remote_write endpoint')
    @property
    def push_url(self) -> str:
        if not self.enabled:
            return ''
        if self.uri:
            return self.uri
        if self._root_config.stack.mimir.enabled:
            return self._root_config.stack.mimir.push_url
        raise ValueError(
            'stack.alloy.metrics.enabled is set but stack.mimir is disabled '
            'and stack.alloy.metrics.uri is empty. Enable stack.mimir or set '
            'stack.alloy.metrics.uri explicitly.'
        )


class StackAlloyLogsConfig(RootConfigAware):
    """Whether Alloy should tail pod logs and push them into Loki."""

    enabled: bool = Field(
        default=True, description='Tail pod logs and push them into Loki'
    )
    uri: str = Field(
        default='',
        description=(
            'Loki push endpoint. Left blank, defaults to the local Loki '
            'install if stack.loki.enabled'
        ),
    )

    @computed_field(description='Resolved Loki push endpoint')
    @property
    def push_url(self) -> str:
        if not self.enabled:
            return ''
        if self.uri:
            return self.uri
        if self._root_config.stack.loki.enabled:
            return self._root_config.stack.loki.push_url
        raise ValueError(
            'stack.alloy.logs.enabled is set but stack.loki is disabled '
            'and stack.alloy.logs.uri is empty. Enable stack.loki or set '
            'stack.alloy.logs.uri explicitly.'
        )


class StackAlloyConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    ns: str = Field(default='alloy')
    hostname: str = Field(default='alloy')
    metrics: StackAlloyMetricsConfig = Field(default_factory=StackAlloyMetricsConfig)
    logs: StackAlloyLogsConfig = Field(default_factory=StackAlloyLogsConfig)


class StackLokiConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    ns: str = Field(default='loki')
    hostname: str = Field(default='loki')

    @computed_field(description='Log push endpoint')
    @property
    def push_url(self) -> str:
        return f'http://loki.{self.ns}.svc.cluster.local:3100/loki/api/v1/push'

    @computed_field(description='LogQL query endpoint used by Grafana')
    @property
    def query_url(self) -> str:
        return f'http://loki.{self.ns}.svc.cluster.local:3100'


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

    @computed_field(description='Trace query endpoint used by Grafana')
    @property
    def query_url(self) -> str:
        return f'http://tempo.{self.ns}.svc.cluster.local:3200'


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
