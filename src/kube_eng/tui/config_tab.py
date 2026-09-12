import typing
from dataclasses import dataclass

import pydantic
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.content import ContentType
from textual.message import Message
from textual.widget import Widget
from textual.widgets import (
    Button,
    Checkbox,
    Collapsible,
    Input,
    Label,
    Select,
    TabPane,
)

from kube_eng.config import RootConfig, RootConfigAware
from kube_eng.config.cluster_config import (
    ClusterCNIKindEnum,
    ClusterEdgeKindEnum,
    ClusterMeshKind,
)
from kube_eng.config.stack_config import StackGrafanaDBKind, StackGrafanaDBSSL
from kube_eng.tui.validators import ExecutablePathInput, PortValidator
from kube_eng.tui.widgets import ConfigSidebar, FormActions, FormLine

# Options for every infra.<resource>.provider discriminator Select.
_PROVIDER_OPTIONS = [('local', 'local'), ('remote', 'remote')]


@dataclass(frozen=True)
class FieldSpec:
    """One editable field on a discriminated infra resource's form."""

    name: str
    label: str
    kind: str = 'text'  # 'text' | 'int' | 'password' | 'checkbox'
    port: bool = False  # attach PortValidator (only meaningful for kind='int')


@dataclass(frozen=True)
class UnionResourceSpec:
    """
    Describes one infra.<key> discriminated union (Local<X>Config |
    Remote<X>Config) for the generic compose/mount/collect helpers below.

    `common` fields exist on both providers (declared on the shared abstract
    base); `local_only`/`remote_only` exist on just one variant. All three
    groups are always rendered -- the fields irrelevant to whichever
    provider is currently selected are simply disabled, not hidden, since
    Textual's compose() runs once and can't be re-entered when the
    provider Select changes.
    """

    key: str
    title: str
    common: tuple[FieldSpec, ...]
    local_only: tuple[FieldSpec, ...] = ()
    remote_only: tuple[FieldSpec, ...] = ()

    @property
    def all_fields(self) -> tuple[FieldSpec, ...]:
        return self.common + self.local_only + self.remote_only


# admin_password/secret_key/admin_key_secret are exposed (unlike e.g.
# stack.grafana.admin_password) because a remote provider needs the user to
# supply the *real* credential for a central resource -- there is no
# equivalent local/remote split for the stack components, so those stay
# auto-generated and unexposed.
#
# These are `common` fields, so they carry across a provider switch in this
# form as-is (whatever the field currently shows). That is a deliberate
# difference from `kube-eng config set infra.<x>.provider ...`, which drops
# them on an actual provider change (see cli/main.py's config_set): the CLI
# has no way to supply a replacement in the same command, so dropping is the
# only safe option there, whereas the TUI shows the user exactly what will
# be submitted and lets them edit or clear it before pressing Apply.
_DNS_SPEC = UnionResourceSpec(
    key='dns',
    title='DNS',
    common=(
        FieldSpec('ip', 'IP Address'),
        FieldSpec('port', 'Port', 'int', port=True),
        FieldSpec('control_port', 'Control Port', 'int', port=True),
        FieldSpec('admin_key_name', 'Key Name'),
        FieldSpec('admin_key_secret', 'Key Secret', 'password'),
        FieldSpec('key_algorithm', 'Key Algorithm'),
        FieldSpec('protocol', 'Protocol'),
        FieldSpec('ttl', 'TTL', 'int'),
        FieldSpec('zone', 'Zone'),
    ),
    local_only=(
        FieldSpec('name', 'Name'),
        FieldSpec('image', 'Image'),
        FieldSpec('cache_volume_name', 'Cache Volume Name'),
        FieldSpec('zones_volume_name', 'Zones Volume Name'),
    ),
)

_PG_SPEC = UnionResourceSpec(
    key='pg',
    title='PostgreSQL',
    common=(
        FieldSpec('port', 'Port', 'int', port=True),
        FieldSpec('admin_user', 'Admin User'),
        FieldSpec('admin_password', 'Admin Password', 'password'),
        FieldSpec('admin_db', 'Admin Database'),
    ),
    local_only=(
        FieldSpec('name', 'Name'),
        FieldSpec('image', 'Image'),
        FieldSpec('volume_name', 'Volume Name'),
        FieldSpec('ip', 'IP Address'),
    ),
    remote_only=(FieldSpec('fqdn', 'FQDN'),),
)

_IDP_SPEC = UnionResourceSpec(
    key='idp',
    title='Identity Provider',
    common=(
        FieldSpec('realm', 'Realm'),
        FieldSpec('admin_user', 'Admin User'),
        FieldSpec('admin_password', 'Admin Password', 'password'),
        FieldSpec('username_claim', 'Username Claim'),
        FieldSpec('groups_claim', 'Groups Claim'),
    ),
    local_only=(
        FieldSpec('name', 'Name'),
        FieldSpec('image', 'Image'),
        FieldSpec('ip', 'IP Address'),
        FieldSpec('port', 'Port', 'int', port=True),
        FieldSpec('db_host', 'DB Host'),
        FieldSpec('db_port', 'DB Port', 'int', port=True),
        FieldSpec('db_name', 'DB Name'),
        FieldSpec('db_user', 'DB User'),
        FieldSpec('db_password', 'DB Password', 'password'),
    ),
    remote_only=(FieldSpec('url', 'URL'),),
)

_S3_SPEC = UnionResourceSpec(
    key='s3',
    title='S3',
    common=(
        FieldSpec('port', 'Port', 'int', port=True),
        FieldSpec('console_port', 'Console Port', 'int', port=True),
        FieldSpec('region', 'Region'),
        FieldSpec('access_key', 'Access Key'),
        FieldSpec('secret_key', 'Secret Key', 'password'),
    ),
    local_only=(
        FieldSpec('name', 'Name'),
        FieldSpec('image', 'Image'),
        FieldSpec('volume_name', 'Volume Name'),
        FieldSpec('ip', 'IP Address'),
    ),
    remote_only=(FieldSpec('url', 'URL'),),
)

_REGISTRY_SPEC = UnionResourceSpec(
    key='registry',
    title='Registry',
    common=(
        FieldSpec('admin_username', 'Admin Username'),
        FieldSpec('admin_password', 'Admin Password', 'password'),
    ),
    local_only=(
        FieldSpec('name', 'Name'),
        FieldSpec('image', 'Image'),
        FieldSpec('volume_name', 'Volume Name'),
        FieldSpec('ip', 'IP Address'),
        FieldSpec('port', 'Port', 'int', port=True),
        FieldSpec('container_port', 'Container Port', 'int', port=True),
    ),
    remote_only=(FieldSpec('url', 'URL'),),
)

_KAFKA_SPEC = UnionResourceSpec(
    key='kafka',
    title='Kafka',
    common=(
        FieldSpec('enabled', 'Enabled', 'checkbox'),
        FieldSpec('port', 'Port', 'int', port=True),
        FieldSpec('admin_user', 'Admin User'),
        FieldSpec('admin_password', 'Admin Password', 'password'),
    ),
    local_only=(
        FieldSpec('name', 'Name'),
        FieldSpec('image', 'Image'),
        FieldSpec('volume_name', 'Volume Name'),
        FieldSpec('ip', 'IP Address'),
    ),
    remote_only=(FieldSpec('endpoint', 'Endpoint'),),
)

_UNION_SPECS = (_DNS_SPEC, _PG_SPEC, _IDP_SPEC, _S3_SPEC, _REGISTRY_SPEC, _KAFKA_SPEC)

# checkbox_id -> field_ids it enables/disables. Reused for the initial
# on_mount state and for every Checkbox.Changed event, so the two can never
# drift apart the way on_mount()/apply_configuration() did in the past.
_CHECKBOX_TOGGLES: dict[str, list[str]] = {
    'host_tool_cloud_provider_kind_enabled': [
        'host_tool_cloud_provider_kind_path',
        'host_tool_cloud_provider_kind_arch',
        'host_tool_cloud_provider_kind_version',
    ],
    'cluster_cni_ui': ['cluster_cni_hostname'],
    'cluster_mesh_enabled': ['cluster_mesh_kind', 'cluster_mesh_ns'],
    'cluster_pki_enabled': [
        'cluster_pki_ns',
        'cluster_pki_crd',
        'cluster_pki_hostname',
    ],
    'stack_prometheus_enabled': [
        'stack_prometheus_ns',
        'stack_prometheus_hostname',
        'stack_prometheus_service_monitor_crd',
        'stack_prometheus_pod_monitor_crd',
        'stack_prometheus_mimir_enabled',
        'stack_prometheus_mimir_uri',
    ],
    'stack_prometheus_mimir_enabled': ['stack_prometheus_mimir_uri'],
    'stack_mimir_enabled': ['stack_mimir_ns', 'stack_mimir_hostname'],
    'stack_alloy_enabled': [
        'stack_alloy_ns',
        'stack_alloy_hostname',
        'stack_alloy_metrics_enabled',
        'stack_alloy_metrics_uri',
        'stack_alloy_logs_enabled',
        'stack_alloy_logs_uri',
    ],
    'stack_alloy_metrics_enabled': ['stack_alloy_metrics_uri'],
    'stack_alloy_logs_enabled': ['stack_alloy_logs_uri'],
    'stack_loki_enabled': ['stack_loki_ns', 'stack_loki_hostname'],
    'stack_grafana_enabled': [
        'stack_grafana_ns',
        'stack_grafana_hostname',
        'stack_grafana_admin_user',
        'stack_grafana_db_kind',
        'stack_grafana_db_host',
        'stack_grafana_db_port',
        'stack_grafana_db_name',
        'stack_grafana_db_user',
        'stack_grafana_db_password',
        'stack_grafana_db_ssl_mode',
    ],
    'stack_tempo_enabled': ['stack_tempo_ns', 'stack_tempo_hostname'],
    'stack_kiali_enabled': [
        'stack_kiali_ns',
        'stack_kiali_hostname',
        'stack_kiali_version',
    ],
}

# Sidebar option id -> the header/Collapsible id it should reveal. A typo
# here used to fail silently (on_section_selected swallowed exceptions);
# it now crashes the app instead, so this is covered by a test that walks
# every entry rather than spot-checking one.
_SECTION_TARGETS: dict[str, str] = {
    'host-config': 'header-host-config',
    'host-tools': 'section-host-tools',
    'infra-config': 'header-infra-config',
    'infra-net': 'section-infra-net',
    'infra-pki': 'section-infra-pki',
    'infra-dns': 'section-infra-dns',
    'infra-pg': 'section-infra-pg',
    'infra-idp': 'section-infra-idp',
    'infra-s3': 'section-infra-s3',
    'infra-registry': 'section-infra-registry',
    'infra-kafka': 'section-infra-kafka',
    'cluster-config': 'header-cluster-config',
    'cluster-basic': 'section-cluster-basic',
    'cluster-cni': 'section-cluster-cni',
    'cluster-mesh': 'section-cluster-mesh',
    'cluster-pki': 'section-cluster-pki',
    'cluster-edge': 'section-cluster-edge',
    'stack-config': 'header-stack-config',
    'stack-prometheus': 'section-stack-prometheus',
    'stack-mimir': 'section-stack-mimir',
    'stack-alloy': 'section-stack-alloy',
    'stack-loki': 'section-stack-loki',
    'stack-grafana': 'section-stack-grafana',
    'stack-tempo': 'section-stack-tempo',
    'stack-kiali': 'section-stack-kiali',
}


class ConfigTab(TabPane):
    DEFAULT_CLASSES = 'form'

    def __init__(
        self,
        title: ContentType,
        *children: Widget,
        config: RootConfig,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ):
        super().__init__(
            title, *children, name=name, id=id, classes=classes, disabled=disabled
        )
        self._config = config

    class Configured(Message):
        pass

    # ── generic helpers ──────────────────────────────────────────────

    def _toggle_fields(self, checkbox_id: str, field_ids: list[str]) -> None:
        """Enable/disable field_ids based on a checkbox's current value."""
        checkbox = self.query_one(f'#{checkbox_id}', Checkbox)
        for field_id in field_ids:
            self.query_one(f'#{field_id}').disabled = not checkbox.value

    def _toggle_by_select(
        self, select_id: str, target_value: str, field_ids: list[str]
    ) -> None:
        """Enable field_ids only when select_id's value equals target_value."""
        select = self.query_one(f'#{select_id}', Select)
        for field_id in field_ids:
            self.query_one(f'#{field_id}').disabled = select.value != target_value

    def _toggle_union_fields(self, spec: UnionResourceSpec) -> None:
        select_id = f'infra_{spec.key}_provider'
        self._toggle_by_select(
            select_id, 'local', [f'infra_{spec.key}_{f.name}' for f in spec.local_only]
        )
        self._toggle_by_select(
            select_id,
            'remote',
            [f'infra_{spec.key}_{f.name}' for f in spec.remote_only],
        )

    def _resolve_provider_class(
        self, key: str, provider: str
    ) -> type[RootConfigAware] | None:
        field_info = type(self._config.infra).model_fields[key]
        for cls in typing.get_args(field_info.annotation):
            if cls.model_fields['provider'].default == provider:
                return cls
        return None

    def _fill_provider_defaults(self, spec: UnionResourceSpec, provider: str) -> None:
        """
        When the provider Select changes, the fields exclusive to the
        newly-selected provider go from disabled to editable. A field that
        has never had a value to show (e.g. a local-only `ip` on what was
        previously a remote config, or vice versa) is blank -- prefill it
        with that class's own default rather than leaving '' for the user
        to hit as a validation error on Apply (IPvAnyAddress/int reject an
        empty string). A required field with no default (a remote's
        url/fqdn/endpoint) is left blank -- that one must be genuinely
        supplied, there is no sensible default to guess.
        """
        target_cls = self._resolve_provider_class(spec.key, provider)
        if target_cls is None:
            return
        fields = spec.local_only if provider == 'local' else spec.remote_only
        for f in fields:
            widget = self.query_one(f'#infra_{spec.key}_{f.name}')
            if f.kind == 'checkbox' or widget.value:
                continue
            field_info = target_cls.model_fields.get(f.name)
            if field_info is None or field_info.is_required():
                continue
            widget.value = str(field_info.get_default(call_default_factory=True))

    def _rebuild(self, model: RootConfigAware, edits: dict) -> RootConfigAware:
        """Validate `model`'s current values merged with `edits` as a fresh
        instance of the same class -- raises before anything is mutated."""
        merged = {
            **model.model_dump(mode='json', exclude_computed_fields=True),
            **edits,
        }
        return type(model).model_validate(merged)

    def _rebuild_union(
        self, key: str, current: RootConfigAware, edits: dict
    ) -> RootConfigAware:
        """Like _rebuild, but for a discriminated infra.<key> field, where
        `edits['provider']` may select a different class than `current`."""
        field_info = type(self._config.infra).model_fields[key]
        adapter = pydantic.TypeAdapter(field_info.rebuild_annotation())
        merged = {
            **current.model_dump(mode='json', exclude_computed_fields=True),
            **edits,
        }
        return adapter.validate_python(merged)

    def _commit(self, parent: object, attr: str, new_value: object) -> None:
        setattr(parent, attr, new_value)
        if isinstance(new_value, RootConfigAware):
            new_value.propagate_root_config(self._config)

    # ── discriminated infra resource: compose/mount/collect ─────────

    def _compose_union_field(self, spec: UnionResourceSpec, f: FieldSpec):
        widget_id = f'infra_{spec.key}_{f.name}'
        if f.kind == 'checkbox':
            with FormLine():
                yield Checkbox(f.label, id=widget_id)
            return
        with FormLine():
            yield Label(f'{f.label}:')
            if f.kind == 'int':
                yield Input(
                    id=widget_id,
                    type='integer',
                    validators=[PortValidator()] if f.port else [],
                )
            elif f.kind == 'password':
                yield Input(id=widget_id, password=True)
            else:
                yield Input(id=widget_id)

    def _compose_union_section(self, spec: UnionResourceSpec) -> ComposeResult:
        with Collapsible(title=spec.title, id=f'section-infra-{spec.key}'):
            with FormLine():
                yield Label('Provider:')
                yield Select(
                    options=list(_PROVIDER_OPTIONS),
                    id=f'infra_{spec.key}_provider',
                    allow_blank=False,
                )
            for f in spec.all_fields:
                yield from self._compose_union_field(spec, f)

    def _mount_union_section(self, spec: UnionResourceSpec) -> None:
        current = getattr(self._config.infra, spec.key)
        self.query_one(f'#infra_{spec.key}_provider', Select).value = current.provider
        for f in spec.all_fields:
            widget = self.query_one(f'#infra_{spec.key}_{f.name}')
            # A field only present on the *other* provider has no current
            # value to show -- fall back to an empty/False placeholder.
            value = getattr(current, f.name, False if f.kind == 'checkbox' else '')
            if f.kind == 'checkbox':
                widget.value = bool(value)
            else:
                widget.value = str(value)
        self._toggle_union_fields(spec)

    def _collect_union_section(self, spec: UnionResourceSpec) -> dict:
        provider = self.query_one(f'#infra_{spec.key}_provider', Select).value
        # Only ever collect the fields that belong to the *selected*
        # provider. The other provider's fields are shown disabled with
        # whatever placeholder _mount_union_section gave them (often '' --
        # e.g. a remote config has no local `ip`/`port` to display) and
        # sending those through would fail validation on the target class
        # (IPvAnyAddress/int rejecting '') instead of letting it fall back
        # to its own defaults, which is what should happen for fields the
        # user was never shown as editable.
        fields = spec.common + (
            spec.local_only if provider == 'local' else spec.remote_only
        )
        values: dict = {'provider': provider}
        for f in fields:
            widget = self.query_one(f'#infra_{spec.key}_{f.name}')
            values[f.name] = widget.value
        return values

    # ── mount ─────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        """Load configuration values into the UI"""
        # Host Tool Configuration
        self.query_one('#host_tool_docker_path').value = str(
            self._config.host.tool.docker.path
        )
        self.query_one('#host_tool_kind_path').value = str(
            self._config.host.tool.kind.path
        )
        self.query_one('#host_tool_kubectl_path').value = str(
            self._config.host.tool.kubectl.path
        )
        self.query_one('#host_tool_helm_path').value = str(
            self._config.host.tool.helm.path
        )

        cpk = self._config.host.tool.cloud_provider_kind
        self.query_one('#host_tool_cloud_provider_kind_enabled').value = cpk.enabled
        self.query_one('#host_tool_cloud_provider_kind_path').value = str(cpk.path)
        self.query_one('#host_tool_cloud_provider_kind_arch').value = cpk.arch
        self.query_one('#host_tool_cloud_provider_kind_version').value = cpk.version

        # Infrastructure: Network / PKI
        self.query_one('#infra_net_name').value = self._config.infra.net.name

        pki = self._config.infra.pki
        self.query_one('#infra_pki_key_type').value = pki.key_type
        self.query_one('#infra_pki_key_curve').value = pki.key_curve
        self.query_one('#infra_pki_key_size').value = str(pki.key_size)
        self.query_one('#infra_pki_crt_validity').value = pki.crt_validity

        # Infrastructure: discriminated (local/remote) resources
        for spec in _UNION_SPECS:
            self._mount_union_section(spec)

        # Cluster Configuration
        self.query_one('#cluster_name').value = self._config.cluster.name
        self.query_one('#cluster_image').value = self._config.cluster.image
        self.query_one(
            '#cluster_pod_subnet_cidr'
        ).value = self._config.cluster.pod_subnet_cidr
        self.query_one(
            '#cluster_service_subnet_cidr'
        ).value = self._config.cluster.service_subnet_cidr
        self.query_one('#cluster_control_plane_nodes').value = str(
            self._config.cluster.control_plane_nodes
        )
        self.query_one('#cluster_worker_nodes').value = str(
            self._config.cluster.worker_nodes
        )
        self.query_one('#cluster_admin_port').value = str(
            self._config.cluster.admin_port
        )

        # Cluster CNI Configuration
        self.query_one(
            '#cluster_cni_kind', Select
        ).value = self._config.cluster.cni.kind.value
        self.query_one(
            '#cluster_cni_exclusive'
        ).value = self._config.cluster.cni.exclusive
        self.query_one('#cluster_cni_ui').value = self._config.cluster.cni.ui
        self.query_one(
            '#cluster_cni_hostname'
        ).value = self._config.cluster.cni.hostname

        # Cluster Mesh Configuration
        self.query_one(
            '#cluster_mesh_enabled'
        ).value = self._config.cluster.mesh.enabled
        self.query_one(
            '#cluster_mesh_kind', Select
        ).value = self._config.cluster.mesh.kind.value
        self.query_one('#cluster_mesh_ns').value = self._config.cluster.mesh.ns

        # Cluster PKI Configuration
        self.query_one('#cluster_pki_enabled').value = self._config.cluster.pki.enabled
        self.query_one('#cluster_pki_ns').value = self._config.cluster.pki.ns
        self.query_one('#cluster_pki_crd').value = self._config.cluster.pki.crd
        self.query_one(
            '#cluster_pki_hostname'
        ).value = self._config.cluster.pki.hostname

        # Cluster Edge Configuration
        self.query_one(
            '#cluster_edge_kind', Select
        ).value = self._config.cluster.edge.kind.value
        self.query_one('#cluster_edge_name').value = self._config.cluster.edge.name
        self.query_one('#cluster_edge_ns').value = self._config.cluster.edge.ns
        self.query_one(
            '#cluster_edge_gateway_api_crds'
        ).value = self._config.cluster.edge.gateway_api_crds

        # Stack Prometheus Configuration
        prometheus = self._config.stack.prometheus
        self.query_one('#stack_prometheus_enabled').value = prometheus.enabled
        self.query_one('#stack_prometheus_ns').value = prometheus.ns
        self.query_one('#stack_prometheus_hostname').value = prometheus.hostname
        self.query_one(
            '#stack_prometheus_service_monitor_crd'
        ).value = prometheus.service_monitor_crd
        self.query_one(
            '#stack_prometheus_pod_monitor_crd'
        ).value = prometheus.pod_monitor_crd
        self.query_one(
            '#stack_prometheus_mimir_enabled'
        ).value = prometheus.mimir.enabled
        self.query_one('#stack_prometheus_mimir_uri').value = prometheus.mimir.uri

        # Stack Mimir Configuration
        mimir = self._config.stack.mimir
        self.query_one('#stack_mimir_enabled').value = mimir.enabled
        self.query_one('#stack_mimir_ns').value = mimir.ns
        self.query_one('#stack_mimir_hostname').value = mimir.hostname

        # Stack Alloy Configuration
        alloy = self._config.stack.alloy
        self.query_one('#stack_alloy_enabled').value = alloy.enabled
        self.query_one('#stack_alloy_ns').value = alloy.ns
        self.query_one('#stack_alloy_hostname').value = alloy.hostname
        self.query_one('#stack_alloy_metrics_enabled').value = alloy.metrics.enabled
        self.query_one('#stack_alloy_metrics_uri').value = alloy.metrics.uri
        self.query_one('#stack_alloy_logs_enabled').value = alloy.logs.enabled
        self.query_one('#stack_alloy_logs_uri').value = alloy.logs.uri

        # Stack Loki Configuration
        self.query_one('#stack_loki_enabled').value = self._config.stack.loki.enabled
        self.query_one('#stack_loki_ns').value = self._config.stack.loki.ns
        self.query_one('#stack_loki_hostname').value = self._config.stack.loki.hostname

        # Stack Grafana Configuration
        grafana = self._config.stack.grafana
        self.query_one('#stack_grafana_enabled').value = grafana.enabled
        self.query_one('#stack_grafana_ns').value = grafana.ns
        self.query_one('#stack_grafana_hostname').value = grafana.hostname
        self.query_one('#stack_grafana_admin_user').value = grafana.admin_user
        self.query_one('#stack_grafana_db_kind', Select).value = grafana.db_kind.value
        self.query_one('#stack_grafana_db_host').value = grafana.db_host
        self.query_one('#stack_grafana_db_port').value = str(grafana.db_port)
        self.query_one('#stack_grafana_db_name').value = grafana.db_name
        self.query_one('#stack_grafana_db_user').value = grafana.db_user
        self.query_one('#stack_grafana_db_password').value = grafana.db_password
        self.query_one(
            '#stack_grafana_db_ssl_mode', Select
        ).value = grafana.db_ssl_mode.value

        # Stack Tempo Configuration
        self.query_one('#stack_tempo_enabled').value = self._config.stack.tempo.enabled
        self.query_one('#stack_tempo_ns').value = self._config.stack.tempo.ns
        self.query_one(
            '#stack_tempo_hostname'
        ).value = self._config.stack.tempo.hostname

        # Stack Kiali Configuration
        self.query_one('#stack_kiali_enabled').value = self._config.stack.kiali.enabled
        self.query_one('#stack_kiali_ns').value = self._config.stack.kiali.ns
        self.query_one(
            '#stack_kiali_hostname'
        ).value = self._config.stack.kiali.hostname
        self.query_one('#stack_kiali_version').value = self._config.stack.kiali.version

        # Initial enabled/disabled state for every checkbox-gated group.
        for checkbox_id, field_ids in _CHECKBOX_TOGGLES.items():
            self._toggle_fields(checkbox_id, field_ids)

    # ── apply ─────────────────────────────────────────────────────────

    @on(Button.Pressed, '#apply_configuration')
    def apply_configuration(self, event: Button.Pressed) -> None:
        """
        Validate every section first, then commit atomically. Nothing is
        written to self._config (or disk) unless every section validates --
        a single bad field (e.g. flipping a provider to 'remote' without
        filling in its now-required URL) must not leave self._config
        partially updated and out of sync with what's on disk.
        """
        try:
            new_docker = self._rebuild(
                self._config.host.tool.docker,
                {'path': self.query_one('#host_tool_docker_path', Input).value},
            )
            new_kind = self._rebuild(
                self._config.host.tool.kind,
                {'path': self.query_one('#host_tool_kind_path', Input).value},
            )
            new_kubectl = self._rebuild(
                self._config.host.tool.kubectl,
                {'path': self.query_one('#host_tool_kubectl_path', Input).value},
            )
            new_helm = self._rebuild(
                self._config.host.tool.helm,
                {'path': self.query_one('#host_tool_helm_path', Input).value},
            )
            new_cpk = self._rebuild(
                self._config.host.tool.cloud_provider_kind,
                {
                    'enabled': self.query_one(
                        '#host_tool_cloud_provider_kind_enabled', Checkbox
                    ).value,
                    'path': self.query_one(
                        '#host_tool_cloud_provider_kind_path', Input
                    ).value,
                    'arch': self.query_one(
                        '#host_tool_cloud_provider_kind_arch', Input
                    ).value,
                    'version': self.query_one(
                        '#host_tool_cloud_provider_kind_version', Input
                    ).value,
                },
            )

            new_net = self._rebuild(
                self._config.infra.net,
                {'name': self.query_one('#infra_net_name', Input).value},
            )
            new_pki = self._rebuild(
                self._config.infra.pki,
                {
                    'key_type': self.query_one('#infra_pki_key_type', Input).value,
                    'key_curve': self.query_one('#infra_pki_key_curve', Input).value,
                    'key_size': self.query_one('#infra_pki_key_size', Input).value,
                    'crt_validity': self.query_one(
                        '#infra_pki_crt_validity', Input
                    ).value,
                },
            )

            new_unions = {
                spec.key: self._rebuild_union(
                    spec.key,
                    getattr(self._config.infra, spec.key),
                    self._collect_union_section(spec),
                )
                for spec in _UNION_SPECS
            }

            new_cluster_top = self._rebuild(
                self._config.cluster,
                {
                    'name': self.query_one('#cluster_name', Input).value,
                    'image': self.query_one('#cluster_image', Input).value,
                    'pod_subnet_cidr': self.query_one(
                        '#cluster_pod_subnet_cidr', Input
                    ).value,
                    'service_subnet_cidr': self.query_one(
                        '#cluster_service_subnet_cidr', Input
                    ).value,
                    'control_plane_nodes': self.query_one(
                        '#cluster_control_plane_nodes', Input
                    ).value,
                    'worker_nodes': self.query_one(
                        '#cluster_worker_nodes', Input
                    ).value,
                    'admin_port': self.query_one('#cluster_admin_port', Input).value,
                },
            )
            new_cni = self._rebuild(
                self._config.cluster.cni,
                {
                    'kind': self.query_one('#cluster_cni_kind', Select).value,
                    'exclusive': self.query_one(
                        '#cluster_cni_exclusive', Checkbox
                    ).value,
                    'ui': self.query_one('#cluster_cni_ui', Checkbox).value,
                    'hostname': self.query_one('#cluster_cni_hostname', Input).value,
                },
            )
            new_mesh = self._rebuild(
                self._config.cluster.mesh,
                {
                    'enabled': self.query_one('#cluster_mesh_enabled', Checkbox).value,
                    'kind': self.query_one('#cluster_mesh_kind', Select).value,
                    'ns': self.query_one('#cluster_mesh_ns', Input).value,
                },
            )
            new_cluster_pki = self._rebuild(
                self._config.cluster.pki,
                {
                    'enabled': self.query_one('#cluster_pki_enabled', Checkbox).value,
                    'ns': self.query_one('#cluster_pki_ns', Input).value,
                    'crd': self.query_one('#cluster_pki_crd', Input).value,
                    'hostname': self.query_one('#cluster_pki_hostname', Input).value,
                },
            )
            new_edge = self._rebuild(
                self._config.cluster.edge,
                {
                    'kind': self.query_one('#cluster_edge_kind', Select).value,
                    'name': self.query_one('#cluster_edge_name', Input).value,
                    'ns': self.query_one('#cluster_edge_ns', Input).value,
                    'gateway_api_crds': self.query_one(
                        '#cluster_edge_gateway_api_crds', Input
                    ).value,
                },
            )

            new_prometheus = self._rebuild(
                self._config.stack.prometheus,
                {
                    'enabled': self.query_one(
                        '#stack_prometheus_enabled', Checkbox
                    ).value,
                    'ns': self.query_one('#stack_prometheus_ns', Input).value,
                    'hostname': self.query_one(
                        '#stack_prometheus_hostname', Input
                    ).value,
                    'service_monitor_crd': self.query_one(
                        '#stack_prometheus_service_monitor_crd', Input
                    ).value,
                    'pod_monitor_crd': self.query_one(
                        '#stack_prometheus_pod_monitor_crd', Input
                    ).value,
                },
            )
            new_prometheus_mimir = self._rebuild(
                self._config.stack.prometheus.mimir,
                {
                    'enabled': self.query_one(
                        '#stack_prometheus_mimir_enabled', Checkbox
                    ).value,
                    'uri': self.query_one('#stack_prometheus_mimir_uri', Input).value,
                },
            )
            new_mimir = self._rebuild(
                self._config.stack.mimir,
                {
                    'enabled': self.query_one('#stack_mimir_enabled', Checkbox).value,
                    'ns': self.query_one('#stack_mimir_ns', Input).value,
                    'hostname': self.query_one('#stack_mimir_hostname', Input).value,
                },
            )
            new_alloy = self._rebuild(
                self._config.stack.alloy,
                {
                    'enabled': self.query_one('#stack_alloy_enabled', Checkbox).value,
                    'ns': self.query_one('#stack_alloy_ns', Input).value,
                    'hostname': self.query_one('#stack_alloy_hostname', Input).value,
                },
            )
            new_alloy_metrics = self._rebuild(
                self._config.stack.alloy.metrics,
                {
                    'enabled': self.query_one(
                        '#stack_alloy_metrics_enabled', Checkbox
                    ).value,
                    'uri': self.query_one('#stack_alloy_metrics_uri', Input).value,
                },
            )
            new_alloy_logs = self._rebuild(
                self._config.stack.alloy.logs,
                {
                    'enabled': self.query_one(
                        '#stack_alloy_logs_enabled', Checkbox
                    ).value,
                    'uri': self.query_one('#stack_alloy_logs_uri', Input).value,
                },
            )
            new_loki = self._rebuild(
                self._config.stack.loki,
                {
                    'enabled': self.query_one('#stack_loki_enabled', Checkbox).value,
                    'ns': self.query_one('#stack_loki_ns', Input).value,
                    'hostname': self.query_one('#stack_loki_hostname', Input).value,
                },
            )
            new_grafana = self._rebuild(
                self._config.stack.grafana,
                {
                    'enabled': self.query_one('#stack_grafana_enabled', Checkbox).value,
                    'ns': self.query_one('#stack_grafana_ns', Input).value,
                    'hostname': self.query_one('#stack_grafana_hostname', Input).value,
                    'admin_user': self.query_one(
                        '#stack_grafana_admin_user', Input
                    ).value,
                    'db_kind': self.query_one('#stack_grafana_db_kind', Select).value,
                    'db_host': self.query_one('#stack_grafana_db_host', Input).value,
                    'db_port': self.query_one('#stack_grafana_db_port', Input).value,
                    'db_name': self.query_one('#stack_grafana_db_name', Input).value,
                    'db_user': self.query_one('#stack_grafana_db_user', Input).value,
                    'db_password': self.query_one(
                        '#stack_grafana_db_password', Input
                    ).value,
                    'db_ssl_mode': self.query_one(
                        '#stack_grafana_db_ssl_mode', Select
                    ).value,
                },
            )
            new_tempo = self._rebuild(
                self._config.stack.tempo,
                {
                    'enabled': self.query_one('#stack_tempo_enabled', Checkbox).value,
                    'ns': self.query_one('#stack_tempo_ns', Input).value,
                    'hostname': self.query_one('#stack_tempo_hostname', Input).value,
                },
            )
            new_kiali = self._rebuild(
                self._config.stack.kiali,
                {
                    'enabled': self.query_one('#stack_kiali_enabled', Checkbox).value,
                    'ns': self.query_one('#stack_kiali_ns', Input).value,
                    'hostname': self.query_one('#stack_kiali_hostname', Input).value,
                    'version': self.query_one('#stack_kiali_version', Input).value,
                },
            )
        except (pydantic.ValidationError, ValueError) as e:
            self.notify(
                str(e), title='Configuration not applied', severity='error', timeout=10
            )
            return

        # Nothing above touched self._config -- everything validated first.
        # Commit parents before the children nested inside them (cluster
        # before cluster.cni/mesh/pki/edge, etc.) so a wholesale parent
        # replacement can't clobber a child assigned just before it.
        self._commit(self._config.host.tool, 'docker', new_docker)
        self._commit(self._config.host.tool, 'kind', new_kind)
        self._commit(self._config.host.tool, 'kubectl', new_kubectl)
        self._commit(self._config.host.tool, 'helm', new_helm)
        self._commit(self._config.host.tool, 'cloud_provider_kind', new_cpk)

        self._commit(self._config.infra, 'net', new_net)
        self._commit(self._config.infra, 'pki', new_pki)
        for key, new_value in new_unions.items():
            self._commit(self._config.infra, key, new_value)

        self._commit(self._config, 'cluster', new_cluster_top)
        self._commit(self._config.cluster, 'cni', new_cni)
        self._commit(self._config.cluster, 'mesh', new_mesh)
        self._commit(self._config.cluster, 'pki', new_cluster_pki)
        self._commit(self._config.cluster, 'edge', new_edge)

        self._commit(self._config.stack, 'prometheus', new_prometheus)
        self._commit(self._config.stack.prometheus, 'mimir', new_prometheus_mimir)
        self._commit(self._config.stack, 'mimir', new_mimir)
        self._commit(self._config.stack, 'alloy', new_alloy)
        self._commit(self._config.stack.alloy, 'metrics', new_alloy_metrics)
        self._commit(self._config.stack.alloy, 'logs', new_alloy_logs)
        self._commit(self._config.stack, 'loki', new_loki)
        self._commit(self._config.stack, 'grafana', new_grafana)
        self._commit(self._config.stack, 'tempo', new_tempo)
        self._commit(self._config.stack, 'kiali', new_kiali)

        self._config.save()
        self.post_message(self.Configured())

    # ── event handlers ───────────────────────────────────────────────

    @on(Checkbox.Changed)
    def _on_toggle_checkbox_changed(self, event: Checkbox.Changed) -> None:
        field_ids = _CHECKBOX_TOGGLES.get(event.checkbox.id or '')
        if field_ids is not None:
            self._toggle_fields(event.checkbox.id or '', field_ids)

    @on(Select.Changed)
    def _on_provider_select_changed(self, event: Select.Changed) -> None:
        select_id = event.select.id or ''
        if not select_id.startswith('infra_') or not select_id.endswith('_provider'):
            return
        key = select_id.removeprefix('infra_').removesuffix('_provider')
        spec = next((s for s in _UNION_SPECS if s.key == key), None)
        if spec is not None:
            self._toggle_union_fields(spec)
            self._fill_provider_defaults(spec, event.value)

    @on(ConfigSidebar.SectionSelected)
    async def on_section_selected(self, event: ConfigSidebar.SectionSelected) -> None:
        """Handle sidebar navigation to specific subsections"""
        target_id = _SECTION_TARGETS.get(event.section_id)
        if not target_id:
            return

        target_widget = self.query_one(f'#{target_id}')
        if isinstance(target_widget, Collapsible):
            target_widget.collapsed = False

        self.query_one('#config-scroll', VerticalScroll).scroll_to_widget(
            target_widget, animate=True
        )

    # ── compose ───────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        """Build the complete configuration UI"""
        with Horizontal():
            yield ConfigSidebar()
            with VerticalScroll(can_focus=True, id='config-scroll'):
                # Host Configuration Section
                yield Label(
                    'HOST CONFIGURATION',
                    id='header-host-config',
                    classes='section-header',
                )
                with Collapsible(title='Tools', id='section-host-tools'):
                    with FormLine():
                        yield Label('Docker:')
                        yield ExecutablePathInput(
                            id='host_tool_docker_path',
                            placeholder='Path to docker',
                        )
                    with FormLine():
                        yield Label('Kind:')
                        yield ExecutablePathInput(
                            id='host_tool_kind_path',
                            placeholder='Path to kind',
                        )
                    with FormLine():
                        yield Label('Kubectl:')
                        yield ExecutablePathInput(
                            id='host_tool_kubectl_path',
                            placeholder='Path to kubectl',
                        )
                    with FormLine():
                        yield Label('Helm:')
                        yield ExecutablePathInput(
                            id='host_tool_helm_path',
                            placeholder='Path to helm',
                        )

                with Collapsible(
                    title='Cloud Provider: Kind', id='section-host-cloud-kind'
                ):
                    with FormLine():
                        yield Checkbox(
                            'Enabled', id='host_tool_cloud_provider_kind_enabled'
                        )
                    with FormLine():
                        yield Label('Path:')
                        yield ExecutablePathInput(
                            id='host_tool_cloud_provider_kind_path',
                            placeholder='Path to cloud-provider-kind',
                        )
                    with FormLine():
                        yield Label('Architecture:')
                        yield Input(id='host_tool_cloud_provider_kind_arch')
                    with FormLine():
                        yield Label('Version:')
                        yield Input(id='host_tool_cloud_provider_kind_version')

                # Infrastructure Configuration Section
                yield Label(
                    'INFRASTRUCTURE CONFIGURATION',
                    id='header-infra-config',
                    classes='section-header',
                )
                with Collapsible(title='Network', id='section-infra-net'), FormLine():
                    yield Label('Docker Network Name:')
                    yield Input(id='infra_net_name')

                # infra.pki.extra_ca_path (a list of extra CA paths) has no
                # form field -- editing a list in this form layout isn't
                # worth the complexity for a rarely-touched setting.
                with Collapsible(title='PKI', id='section-infra-pki'):
                    with FormLine():
                        yield Label('Key Type:')
                        yield Input(id='infra_pki_key_type')
                    with FormLine():
                        yield Label('Key Curve:')
                        yield Input(id='infra_pki_key_curve')
                    with FormLine():
                        yield Label('Key Size:')
                        yield Input(id='infra_pki_key_size', type='integer')
                    with FormLine():
                        yield Label('Cert Validity:')
                        yield Input(id='infra_pki_crt_validity')

                for spec in _UNION_SPECS:
                    yield from self._compose_union_section(spec)

                # Cluster Configuration Section
                yield Label(
                    'CLUSTER CONFIGURATION',
                    id='header-cluster-config',
                    classes='section-header',
                )
                with Collapsible(title='Basic', id='section-cluster-basic'):
                    with FormLine():
                        yield Label('Name:')
                        yield Input(id='cluster_name')
                    with FormLine():
                        yield Label('Node Image:')
                        yield Input(id='cluster_image')
                    with FormLine():
                        yield Label('Pod Subnet CIDR:')
                        yield Input(id='cluster_pod_subnet_cidr')
                    with FormLine():
                        yield Label('Service Subnet CIDR:')
                        yield Input(id='cluster_service_subnet_cidr')
                    with FormLine():
                        yield Label('Control Plane Nodes:')
                        yield Input(id='cluster_control_plane_nodes', type='integer')
                    with FormLine():
                        yield Label('Worker Nodes:')
                        yield Input(id='cluster_worker_nodes', type='integer')
                    with FormLine():
                        yield Label('Admin Port:')
                        yield Input(
                            id='cluster_admin_port',
                            type='integer',
                            validators=[PortValidator()],
                        )

                with Collapsible(title='CNI', id='section-cluster-cni'):
                    with FormLine():
                        yield Label('Kind:')
                        yield Select(
                            options=[(e.value, e.value) for e in ClusterCNIKindEnum],
                            id='cluster_cni_kind',
                            allow_blank=False,
                        )
                    with FormLine():
                        yield Checkbox('Exclusive', id='cluster_cni_exclusive')
                    with FormLine():
                        yield Checkbox('UI', id='cluster_cni_ui')
                    with FormLine():
                        yield Label('Hostname:')
                        yield Input(id='cluster_cni_hostname')

                with Collapsible(title='Service Mesh', id='section-cluster-mesh'):
                    with FormLine():
                        yield Checkbox('Enabled', id='cluster_mesh_enabled')
                    with FormLine():
                        yield Label('Kind:')
                        yield Select(
                            options=[(e.value, e.value) for e in ClusterMeshKind],
                            id='cluster_mesh_kind',
                            allow_blank=False,
                        )
                    with FormLine():
                        yield Label('Namespace:')
                        yield Input(id='cluster_mesh_ns')

                with Collapsible(title='PKI', id='section-cluster-pki'):
                    with FormLine():
                        yield Checkbox('Enabled', id='cluster_pki_enabled')
                    with FormLine():
                        yield Label('Namespace:')
                        yield Input(id='cluster_pki_ns')
                    with FormLine():
                        yield Label('CRD URL:')
                        yield Input(id='cluster_pki_crd')
                    with FormLine():
                        yield Label('Hostname:')
                        yield Input(id='cluster_pki_hostname')

                with Collapsible(title='Edge', id='section-cluster-edge'):
                    with FormLine():
                        yield Label('Kind:')
                        yield Select(
                            options=[(e.value, e.value) for e in ClusterEdgeKindEnum],
                            id='cluster_edge_kind',
                            allow_blank=False,
                        )
                    with FormLine():
                        yield Label('Name:')
                        yield Input(id='cluster_edge_name')
                    with FormLine():
                        yield Label('Namespace:')
                        yield Input(id='cluster_edge_ns')
                    with FormLine():
                        yield Label('Gateway API CRDs:')
                        yield Input(id='cluster_edge_gateway_api_crds')

                # Stack Configuration Section
                yield Label(
                    'STACK CONFIGURATION',
                    id='header-stack-config',
                    classes='section-header',
                )
                with Collapsible(title='Prometheus', id='section-stack-prometheus'):
                    with FormLine():
                        yield Checkbox('Enabled', id='stack_prometheus_enabled')
                    with FormLine():
                        yield Label('Namespace:')
                        yield Input(id='stack_prometheus_ns')
                    with FormLine():
                        yield Label('Hostname:')
                        yield Input(id='stack_prometheus_hostname')
                    with FormLine():
                        yield Label('ServiceMonitor CRD:')
                        yield Input(id='stack_prometheus_service_monitor_crd')
                    with FormLine():
                        yield Label('PodMonitor CRD:')
                        yield Input(id='stack_prometheus_pod_monitor_crd')
                    with FormLine():
                        yield Checkbox(
                            'Remote-write into Mimir',
                            id='stack_prometheus_mimir_enabled',
                        )
                    with FormLine():
                        yield Label('Mimir URI (blank = local):')
                        yield Input(id='stack_prometheus_mimir_uri')

                with Collapsible(title='Mimir', id='section-stack-mimir'):
                    with FormLine():
                        yield Checkbox('Enabled', id='stack_mimir_enabled')
                    with FormLine():
                        yield Label('Namespace:')
                        yield Input(id='stack_mimir_ns')
                    with FormLine():
                        yield Label('Hostname:')
                        yield Input(id='stack_mimir_hostname')

                with Collapsible(title='Alloy', id='section-stack-alloy'):
                    with FormLine():
                        yield Checkbox('Enabled', id='stack_alloy_enabled')
                    with FormLine():
                        yield Label('Namespace:')
                        yield Input(id='stack_alloy_ns')
                    with FormLine():
                        yield Label('Hostname:')
                        yield Input(id='stack_alloy_hostname')
                    with FormLine():
                        yield Checkbox(
                            'Scrape metrics into Mimir',
                            id='stack_alloy_metrics_enabled',
                        )
                    with FormLine():
                        yield Label('Metrics URI (blank = local Mimir):')
                        yield Input(id='stack_alloy_metrics_uri')
                    with FormLine():
                        yield Checkbox(
                            'Tail logs into Loki', id='stack_alloy_logs_enabled'
                        )
                    with FormLine():
                        yield Label('Logs URI (blank = local Loki):')
                        yield Input(id='stack_alloy_logs_uri')

                with Collapsible(title='Loki', id='section-stack-loki'):
                    with FormLine():
                        yield Checkbox('Enabled', id='stack_loki_enabled')
                    with FormLine():
                        yield Label('Namespace:')
                        yield Input(id='stack_loki_ns')
                    with FormLine():
                        yield Label('Hostname:')
                        yield Input(id='stack_loki_hostname')

                with Collapsible(title='Grafana', id='section-stack-grafana'):
                    with FormLine():
                        yield Checkbox('Enabled', id='stack_grafana_enabled')
                    with FormLine():
                        yield Label('Namespace:')
                        yield Input(id='stack_grafana_ns')
                    with FormLine():
                        yield Label('Hostname:')
                        yield Input(id='stack_grafana_hostname')
                    with FormLine():
                        yield Label('Admin User:')
                        yield Input(id='stack_grafana_admin_user')
                    with FormLine():
                        yield Label('Database Kind:')
                        yield Select(
                            options=[(e.value, e.value) for e in StackGrafanaDBKind],
                            id='stack_grafana_db_kind',
                            allow_blank=False,
                        )
                    with FormLine():
                        yield Label('DB Host:')
                        yield Input(id='stack_grafana_db_host')
                    with FormLine():
                        yield Label('DB Port:')
                        yield Input(
                            id='stack_grafana_db_port',
                            type='integer',
                            validators=[PortValidator()],
                        )
                    with FormLine():
                        yield Label('DB Name:')
                        yield Input(id='stack_grafana_db_name')
                    with FormLine():
                        yield Label('DB User:')
                        yield Input(id='stack_grafana_db_user')
                    with FormLine():
                        yield Label('DB Password:')
                        yield Input(id='stack_grafana_db_password', password=True)
                    with FormLine():
                        yield Label('DB SSL Mode:')
                        yield Select(
                            options=[(e.value, e.value) for e in StackGrafanaDBSSL],
                            id='stack_grafana_db_ssl_mode',
                            allow_blank=False,
                        )

                with Collapsible(title='Tempo', id='section-stack-tempo'):
                    with FormLine():
                        yield Checkbox('Enabled', id='stack_tempo_enabled')
                    with FormLine():
                        yield Label('Namespace:')
                        yield Input(id='stack_tempo_ns')
                    with FormLine():
                        yield Label('Hostname:')
                        yield Input(id='stack_tempo_hostname')

                with Collapsible(title='Kiali', id='section-stack-kiali'):
                    with FormLine():
                        yield Checkbox('Enabled', id='stack_kiali_enabled')
                    with FormLine():
                        yield Label('Namespace:')
                        yield Input(id='stack_kiali_ns')
                    with FormLine():
                        yield Label('Hostname:')
                        yield Input(id='stack_kiali_hostname')
                    with FormLine():
                        yield Label('Version:')
                        yield Input(id='stack_kiali_version')

                # Action Buttons
                with FormActions():
                    yield Button(
                        'Apply Configuration',
                        id='apply_configuration',
                        variant='primary',
                    )
