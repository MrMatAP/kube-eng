import pathlib

from textual import on
from textual.app import ComposeResult
from textual.containers import VerticalScroll, Horizontal
from textual.content import ContentType
from textual.message import Message
from textual.widget import Widget
from textual.widgets import (
    TabPane,
    Input,
    Label,
    Checkbox,
    Button,
    Select,
    Collapsible,
    TabbedContent,
)

from kube_eng.config import RootConfig
from kube_eng.config.cluster_config import ClusterCNIKindEnum, ClusterMeshKind, ClusterEdgeKindEnum
from kube_eng.config.host_config import HostDNSKindEnum
from kube_eng.tui.widgets import FormGroup, FormLine, FormActions, EnumSelect, ConfigSidebar
from kube_eng.tui.validators import ExecutablePathInput, PortValidator


class ConfigTab(TabPane):
    DEFAULT_CLASSES = 'form'

    def __init__(self, title: ContentType, *children: Widget, config: RootConfig, name: str | None = None,
                 id: str | None = None, classes: str | None = None, disabled: bool = False):
        super().__init__(title, *children, name=name, id=id, classes=classes, disabled=disabled)
        self._config = config

    class Configured(Message):
        pass

    def on_mount(self) -> None:
        """Load configuration values into the UI"""
        # Host Tool Configuration
        self.query_one('#host_tool_docker_path').value = str(self._config.host.tool.docker.path)
        self.query_one('#host_tool_kind_path').value = str(self._config.host.tool.kind.path)
        self.query_one('#host_tool_kubectl_path').value = str(self._config.host.tool.kubectl.path)
        self.query_one('#host_tool_helm_path').value = str(self._config.host.tool.helm.path)

        self.query_one('#host_tool_cloud_provider_kind_enabled').value = self._config.host.tool.cloud_provider_kind.enabled
        self.query_one('#host_tool_cloud_provider_kind_path').value = str(self._config.host.tool.cloud_provider_kind.path)
        self.query_one('#host_tool_cloud_provider_kind_url').value = self._config.host.tool.cloud_provider_kind.url
        self._toggle_fields('#host_tool_cloud_provider_kind_enabled', ['#host_tool_cloud_provider_kind_path', '#host_tool_cloud_provider_kind_url'])

        self.query_one('#host_tool_cloud_provider_mdns_enabled').value = self._config.host.tool.cloud_provider_mdns.enabled
        self.query_one('#host_tool_cloud_provider_mdns_path').value = str(self._config.host.tool.cloud_provider_mdns.path)
        self._toggle_fields('#host_tool_cloud_provider_mdns_enabled', ['#host_tool_cloud_provider_mdns_path'])

        # Host DNS Configuration
        self.query_one('#host_dns_kind', Select).value = self._config.host.dns.kind.value
        self.query_one('#host_dns_name').value = self._config.host.dns.name
        self.query_one('#host_dns_image').value = self._config.host.dns.image
        self.query_one('#host_dns_volume_name').value = self._config.host.dns.volume_name
        self.query_one('#host_dns_forwarders').value = self._config.host.dns.forwarders
        self.query_one('#host_dns_server').value = self._config.host.dns.server
        self.query_one('#host_dns_port').value = str(self._config.host.dns.port)
        self.query_one('#host_dns_control_port').value = str(self._config.host.dns.control_port)
        self.query_one('#host_dns_key_name').value = self._config.host.dns.key_name
        self.query_one('#host_dns_key_algorithm').value = self._config.host.dns.key_algorithm
        self.query_one('#host_dns_key_secret').value = self._config.host.dns.key_secret
        self.query_one('#host_dns_protocol').value = self._config.host.dns.protocol
        self.query_one('#host_dns_zone').value = self._config.host.dns.zone
        self.query_one('#host_dns_ttl').value = str(self._config.host.dns.ttl)

        # Host Registry Configuration
        self.query_one('#host_registry_enabled').value = self._config.host.registry.enabled
        self.query_one('#host_registry_name').value = self._config.host.registry.name
        self.query_one('#host_registry_port').value = str(self._config.host.registry.port)
        self.query_one('#host_registry_image').value = self._config.host.registry.image
        self.query_one('#host_registry_volume_name').value = self._config.host.registry.volume_name
        self._toggle_fields('#host_registry_enabled', [
            '#host_registry_name', '#host_registry_port', '#host_registry_image', '#host_registry_volume_name'
        ])

        # Host PostgreSQL Configuration
        self.query_one('#host_postgresql_enabled').value = self._config.host.postgresql.enabled
        self.query_one('#host_postgresql_name').value = self._config.host.postgresql.name
        self.query_one('#host_postgresql_port').value = str(self._config.host.postgresql.port)
        self.query_one('#host_postgresql_image').value = self._config.host.postgresql.image
        self.query_one('#host_postgresql_volume_name').value = self._config.host.postgresql.volume_name
        self._toggle_fields('#host_postgresql_enabled', [
            '#host_postgresql_name', '#host_postgresql_port', '#host_postgresql_image', '#host_postgresql_volume_name'
        ])

        # Host Minio Configuration
        self.query_one('#host_minio_enabled').value = self._config.host.minio.enabled
        self.query_one('#host_minio_name').value = self._config.host.minio.name
        self.query_one('#host_minio_port').value = str(self._config.host.minio.port)
        self.query_one('#host_minio_console_port').value = str(self._config.host.minio.console_port)
        self.query_one('#host_minio_image').value = self._config.host.minio.image
        self.query_one('#host_minio_volume_name').value = self._config.host.minio.volume_name
        self._toggle_fields('#host_minio_enabled', [
            '#host_minio_name', '#host_minio_port', '#host_minio_console_port',
            '#host_minio_image', '#host_minio_volume_name'
        ])

        # Host Kafka Configuration
        self.query_one('#host_kafka_enabled').value = self._config.host.kafka.enabled
        self.query_one('#host_kafka_name').value = self._config.host.kafka.name
        self.query_one('#host_kafka_port').value = str(self._config.host.kafka.port)
        self.query_one('#host_kafka_image').value = self._config.host.kafka.image
        self.query_one('#host_kafka_volume_name').value = self._config.host.kafka.volume_name
        self._toggle_fields('#host_kafka_enabled', [
            '#host_kafka_name', '#host_kafka_port', '#host_kafka_image', '#host_kafka_volume_name'
        ])

        # Cluster Configuration
        self.query_one('#cluster_name').value = self._config.cluster.name
        self.query_one('#cluster_pod_subnet_cidr').value = self._config.cluster.pod_subnet_cidr
        self.query_one('#cluster_service_subnet_cidr').value = self._config.cluster.service_subnet_cidr
        self.query_one('#cluster_control_plane_nodes').value = str(self._config.cluster.control_plane_nodes)
        self.query_one('#cluster_worker_nodes').value = str(self._config.cluster.worker_nodes)

        # Cluster CNI Configuration
        self.query_one('#cluster_cni_kind', Select).value = self._config.cluster.cni.kind.value
        self.query_one('#cluster_cni_exclusive').value = self._config.cluster.cni.exclusive
        self.query_one('#cluster_cni_ui').value = self._config.cluster.cni.ui
        self.query_one('#cluster_cni_hostname').value = self._config.cluster.cni.hostname
        self._toggle_fields('#cluster_cni_ui', ['#cluster_cni_hostname'])

        # Cluster Mesh Configuration
        self.query_one('#cluster_mesh_enabled').value = self._config.cluster.mesh.enabled
        self.query_one('#cluster_mesh_kind', Select).value = self._config.cluster.mesh.kind.value
        self.query_one('#cluster_mesh_ns').value = self._config.cluster.mesh.ns
        self._toggle_fields('#cluster_mesh_enabled', ['#cluster_mesh_kind', '#cluster_mesh_ns'])

        # Cluster PKI Configuration
        self.query_one('#cluster_pki_ns').value = self._config.cluster.pki.ns
        self.query_one('#cluster_pki_crd').value = self._config.cluster.pki.crd
        self.query_one('#cluster_pki_key_type').value = self._config.cluster.pki.key_type
        self.query_one('#cluster_pki_key_curve').value = self._config.cluster.pki.key_curve
        self.query_one('#cluster_pki_key_size').value = str(self._config.cluster.pki.key_size)
        self.query_one('#cluster_pki_crt_validity').value = self._config.cluster.pki.crt_validity

        # Cluster Edge Configuration
        self.query_one('#cluster_edge_kind', Select).value = self._config.cluster.edge.kind.value
        self.query_one('#cluster_edge_name').value = self._config.cluster.edge.name
        self.query_one('#cluster_edge_ns').value = self._config.cluster.edge.ns
        self.query_one('#cluster_edge_gateway_api_crds').value = self._config.cluster.edge.gateway_api_crds
        self.query_one('#cluster_edge_traefik_repository').value = self._config.cluster.edge.traefik_repository
        self.query_one('#cluster_edge_traefik_tag').value = self._config.cluster.edge.traefik_tag
        self.query_one('#cluster_edge_traefik_hostname').value = self._config.cluster.edge.traefik_hostname
        self.query_one('#cluster_edge_traefik_dashboard_hostname').value = self._config.cluster.edge.traefik_dashboard_hostname

        # Stack Prometheus Configuration
        self.query_one('#stack_prometheus_enabled').value = self._config.stack.prometheus.enabled
        self.query_one('#stack_prometheus_ns').value = self._config.stack.prometheus.ns
        self.query_one('#stack_prometheus_hostname').value = self._config.stack.prometheus.hostname
        self.query_one('#stack_prometheus_service_monitor_crd').value = self._config.stack.prometheus.service_monitor_crd
        self.query_one('#stack_prometheus_pod_monitor_crd').value = self._config.stack.prometheus.pod_monitor_crd
        self._toggle_fields('#stack_prometheus_enabled', [
            '#stack_prometheus_ns', '#stack_prometheus_hostname',
            '#stack_prometheus_service_monitor_crd', '#stack_prometheus_pod_monitor_crd'
        ])

        # Stack Alloy Configuration
        self.query_one('#stack_alloy_enabled').value = self._config.stack.alloy.enabled
        self.query_one('#stack_alloy_ns').value = self._config.stack.alloy.ns
        self.query_one('#stack_alloy_hostname').value = self._config.stack.alloy.hostname
        self._toggle_fields('#stack_alloy_enabled', ['#stack_alloy_ns', '#stack_alloy_hostname'])

        # Stack Loki Configuration
        self.query_one('#stack_loki_enabled').value = self._config.stack.loki.enabled
        self.query_one('#stack_loki_ns').value = self._config.stack.loki.ns
        self.query_one('#stack_loki_hostname').value = self._config.stack.loki.hostname
        self._toggle_fields('#stack_loki_enabled', ['#stack_loki_ns', '#stack_loki_hostname'])

        # Stack Keycloak Configuration
        self.query_one('#stack_keycloak_enabled').value = self._config.stack.keycloak.enabled
        self.query_one('#stack_keycloak_ns').value = self._config.stack.keycloak.ns
        self.query_one('#stack_keycloak_hostname').value = self._config.stack.keycloak.hostname
        self.query_one('#stack_keycloak_operator_version').value = self._config.stack.keycloak.operator_version
        self._toggle_fields('#stack_keycloak_enabled', [
            '#stack_keycloak_ns', '#stack_keycloak_hostname', '#stack_keycloak_operator_version'
        ])

        # Stack Grafana Configuration
        self.query_one('#stack_grafana_enabled').value = self._config.stack.grafana.enabled
        self.query_one('#stack_grafana_ns').value = self._config.stack.grafana.ns
        self.query_one('#stack_grafana_hostname').value = self._config.stack.grafana.hostname
        self.query_one('#stack_grafana_client_id').value = self._config.stack.grafana.client_id
        self.query_one('#stack_grafana_admin_user').value = self._config.stack.grafana.admin_user
        self._toggle_fields('#stack_grafana_enabled', [
            '#stack_grafana_ns', '#stack_grafana_hostname',
            '#stack_grafana_client_id', '#stack_grafana_admin_user'
        ])

        # Stack Jaeger Configuration
        self.query_one('#stack_jaeger_enabled').value = self._config.stack.jaeger.enabled
        self.query_one('#stack_jaeger_ns').value = self._config.stack.jaeger.ns
        self.query_one('#stack_jaeger_hostname').value = self._config.stack.jaeger.hostname
        self._toggle_fields('#stack_jaeger_enabled', ['#stack_jaeger_ns', '#stack_jaeger_hostname'])

        # Stack Kiali Configuration
        self.query_one('#stack_kiali_enabled').value = self._config.stack.kiali.enabled
        self.query_one('#stack_kiali_ns').value = self._config.stack.kiali.ns
        self.query_one('#stack_kiali_hostname').value = self._config.stack.kiali.hostname
        self.query_one('#stack_kiali_version').value = self._config.stack.kiali.version
        self._toggle_fields('#stack_kiali_enabled', [
            '#stack_kiali_ns', '#stack_kiali_hostname', '#stack_kiali_version'
        ])

    def _toggle_fields(self, checkbox_id: str, field_ids: list[str]) -> None:
        """Helper to enable/disable fields based on checkbox state"""
        try:
            checkbox = self.query_one(checkbox_id, Checkbox)
            for field_id in field_ids:
                try:
                    field = self.query_one(field_id)
                    field.disabled = not checkbox.value
                except Exception:
                    pass
        except Exception:
            pass

    @on(Button.Pressed, '#apply_configuration')
    def apply_configuration(self, event: Button.Pressed) -> None:
        """Save all configuration changes"""
        # Host Tool Configuration
        self._config.host.tool.docker.path = pathlib.Path(self.query_one('#host_tool_docker_path', Input).value)
        self._config.host.tool.kind.path = pathlib.Path(self.query_one('#host_tool_kind_path', Input).value)
        self._config.host.tool.kubectl.path = pathlib.Path(self.query_one('#host_tool_kubectl_path', Input).value)
        self._config.host.tool.helm.path = pathlib.Path(self.query_one('#host_tool_helm_path', Input).value)

        self._config.host.tool.cloud_provider_kind.enabled = self.query_one('#host_tool_cloud_provider_kind_enabled', Checkbox).value
        self._config.host.tool.cloud_provider_kind.path = pathlib.Path(self.query_one('#host_tool_cloud_provider_kind_path', Input).value)
        self._config.host.tool.cloud_provider_kind.url = self.query_one('#host_tool_cloud_provider_kind_url', Input).value

        self._config.host.tool.cloud_provider_mdns.enabled = self.query_one('#host_tool_cloud_provider_mdns_enabled', Checkbox).value
        self._config.host.tool.cloud_provider_mdns.path = pathlib.Path(self.query_one('#host_tool_cloud_provider_mdns_path', Input).value)

        # Host DNS Configuration
        self._config.host.dns.kind = HostDNSKindEnum(self.query_one('#host_dns_kind', Select).value)
        self._config.host.dns.name = self.query_one('#host_dns_name', Input).value
        self._config.host.dns.image = self.query_one('#host_dns_image', Input).value
        self._config.host.dns.volume_name = self.query_one('#host_dns_volume_name', Input).value
        self._config.host.dns.forwarders = self.query_one('#host_dns_forwarders', Input).value
        self._config.host.dns.server = self.query_one('#host_dns_server', Input).value
        self._config.host.dns.port = int(self.query_one('#host_dns_port', Input).value)
        self._config.host.dns.control_port = int(self.query_one('#host_dns_control_port', Input).value)
        self._config.host.dns.key_name = self.query_one('#host_dns_key_name', Input).value
        self._config.host.dns.key_algorithm = self.query_one('#host_dns_key_algorithm', Input).value
        self._config.host.dns.key_secret = self.query_one('#host_dns_key_secret', Input).value
        self._config.host.dns.protocol = self.query_one('#host_dns_protocol', Input).value
        self._config.host.dns.zone = self.query_one('#host_dns_zone', Input).value
        self._config.host.dns.ttl = int(self.query_one('#host_dns_ttl', Input).value)

        # Host Registry Configuration
        self._config.host.registry.enabled = self.query_one('#host_registry_enabled', Checkbox).value
        self._config.host.registry.name = self.query_one('#host_registry_name', Input).value
        self._config.host.registry.port = int(self.query_one('#host_registry_port', Input).value)
        self._config.host.registry.image = self.query_one('#host_registry_image', Input).value
        self._config.host.registry.volume_name = self.query_one('#host_registry_volume_name', Input).value

        # Host PostgreSQL Configuration
        self._config.host.postgresql.enabled = self.query_one('#host_postgresql_enabled', Checkbox).value
        self._config.host.postgresql.name = self.query_one('#host_postgresql_name', Input).value
        self._config.host.postgresql.port = int(self.query_one('#host_postgresql_port', Input).value)
        self._config.host.postgresql.image = self.query_one('#host_postgresql_image', Input).value
        self._config.host.postgresql.volume_name = self.query_one('#host_postgresql_volume_name', Input).value

        # Host Minio Configuration
        self._config.host.minio.enabled = self.query_one('#host_minio_enabled', Checkbox).value
        self._config.host.minio.name = self.query_one('#host_minio_name', Input).value
        self._config.host.minio.port = int(self.query_one('#host_minio_port', Input).value)
        self._config.host.minio.console_port = int(self.query_one('#host_minio_console_port', Input).value)
        self._config.host.minio.image = self.query_one('#host_minio_image', Input).value
        self._config.host.minio.volume_name = self.query_one('#host_minio_volume_name', Input).value

        # Host Kafka Configuration
        self._config.host.kafka.enabled = self.query_one('#host_kafka_enabled', Checkbox).value
        self._config.host.kafka.name = self.query_one('#host_kafka_name', Input).value
        self._config.host.kafka.port = int(self.query_one('#host_kafka_port', Input).value)
        self._config.host.kafka.image = self.query_one('#host_kafka_image', Input).value
        self._config.host.kafka.volume_name = self.query_one('#host_kafka_volume_name', Input).value

        # Cluster Configuration
        self._config.cluster.name = self.query_one('#cluster_name', Input).value
        self._config.cluster.pod_subnet_cidr = self.query_one('#cluster_pod_subnet_cidr', Input).value
        self._config.cluster.service_subnet_cidr = self.query_one('#cluster_service_subnet_cidr', Input).value
        self._config.cluster.control_plane_nodes = int(self.query_one('#cluster_control_plane_nodes', Input).value)
        self._config.cluster.worker_nodes = int(self.query_one('#cluster_worker_nodes', Input).value)

        # Cluster CNI Configuration
        self._config.cluster.cni.kind = ClusterCNIKindEnum(self.query_one('#cluster_cni_kind', Select).value)
        self._config.cluster.cni.exclusive = self.query_one('#cluster_cni_exclusive', Checkbox).value
        self._config.cluster.cni.ui = self.query_one('#cluster_cni_ui', Checkbox).value
        self._config.cluster.cni.hostname = self.query_one('#cluster_cni_hostname', Input).value

        # Cluster Mesh Configuration
        self._config.cluster.mesh.enabled = self.query_one('#cluster_mesh_enabled', Checkbox).value
        self._config.cluster.mesh.kind = ClusterMeshKind(self.query_one('#cluster_mesh_kind', Select).value)
        self._config.cluster.mesh.ns = self.query_one('#cluster_mesh_ns', Input).value

        # Cluster PKI Configuration
        self._config.cluster.pki.ns = self.query_one('#cluster_pki_ns', Input).value
        self._config.cluster.pki.crd = self.query_one('#cluster_pki_crd', Input).value
        self._config.cluster.pki.key_type = self.query_one('#cluster_pki_key_type', Input).value
        self._config.cluster.pki.key_curve = self.query_one('#cluster_pki_key_curve', Input).value
        self._config.cluster.pki.key_size = int(self.query_one('#cluster_pki_key_size', Input).value)
        self._config.cluster.pki.crt_validity = self.query_one('#cluster_pki_crt_validity', Input).value

        # Cluster Edge Configuration
        self._config.cluster.edge.kind = ClusterEdgeKindEnum(self.query_one('#cluster_edge_kind', Select).value)
        self._config.cluster.edge.name = self.query_one('#cluster_edge_name', Input).value
        self._config.cluster.edge.ns = self.query_one('#cluster_edge_ns', Input).value
        self._config.cluster.edge.gateway_api_crds = self.query_one('#cluster_edge_gateway_api_crds', Input).value
        self._config.cluster.edge.traefik_repository = self.query_one('#cluster_edge_traefik_repository', Input).value
        self._config.cluster.edge.traefik_tag = self.query_one('#cluster_edge_traefik_tag', Input).value
        self._config.cluster.edge.traefik_hostname = self.query_one('#cluster_edge_traefik_hostname', Input).value
        self._config.cluster.edge.traefik_dashboard_hostname = self.query_one('#cluster_edge_traefik_dashboard_hostname', Input).value

        # Stack Prometheus Configuration
        self._config.stack.prometheus.enabled = self.query_one('#stack_prometheus_enabled', Checkbox).value
        self._config.stack.prometheus.ns = self.query_one('#stack_prometheus_ns', Input).value
        self._config.stack.prometheus.hostname = self.query_one('#stack_prometheus_hostname', Input).value
        self._config.stack.prometheus.service_monitor_crd = self.query_one('#stack_prometheus_service_monitor_crd', Input).value
        self._config.stack.prometheus.pod_monitor_crd = self.query_one('#stack_prometheus_pod_monitor_crd', Input).value

        # Stack Alloy Configuration
        self._config.stack.alloy.enabled = self.query_one('#stack_alloy_enabled', Checkbox).value
        self._config.stack.alloy.ns = self.query_one('#stack_alloy_ns', Input).value
        self._config.stack.alloy.hostname = self.query_one('#stack_alloy_hostname', Input).value

        # Stack Loki Configuration
        self._config.stack.loki.enabled = self.query_one('#stack_loki_enabled', Checkbox).value
        self._config.stack.loki.ns = self.query_one('#stack_loki_ns', Input).value
        self._config.stack.loki.hostname = self.query_one('#stack_loki_hostname', Input).value

        # Stack Keycloak Configuration
        self._config.stack.keycloak.enabled = self.query_one('#stack_keycloak_enabled', Checkbox).value
        self._config.stack.keycloak.ns = self.query_one('#stack_keycloak_ns', Input).value
        self._config.stack.keycloak.hostname = self.query_one('#stack_keycloak_hostname', Input).value
        self._config.stack.keycloak.operator_version = self.query_one('#stack_keycloak_operator_version', Input).value

        # Stack Grafana Configuration
        self._config.stack.grafana.enabled = self.query_one('#stack_grafana_enabled', Checkbox).value
        self._config.stack.grafana.ns = self.query_one('#stack_grafana_ns', Input).value
        self._config.stack.grafana.hostname = self.query_one('#stack_grafana_hostname', Input).value
        self._config.stack.grafana.client_id = self.query_one('#stack_grafana_client_id', Input).value
        self._config.stack.grafana.admin_user = self.query_one('#stack_grafana_admin_user', Input).value

        # Stack Jaeger Configuration
        self._config.stack.jaeger.enabled = self.query_one('#stack_jaeger_enabled', Checkbox).value
        self._config.stack.jaeger.ns = self.query_one('#stack_jaeger_ns', Input).value
        self._config.stack.jaeger.hostname = self.query_one('#stack_jaeger_hostname', Input).value

        # Stack Kiali Configuration
        self._config.stack.kiali.enabled = self.query_one('#stack_kiali_enabled', Checkbox).value
        self._config.stack.kiali.ns = self.query_one('#stack_kiali_ns', Input).value
        self._config.stack.kiali.hostname = self.query_one('#stack_kiali_hostname', Input).value
        self._config.stack.kiali.version = self.query_one('#stack_kiali_version', Input).value

        # Save configuration
        self._config.save()
        self.post_message(self.Configured())

    # Event handlers for checkbox changes
    @on(Checkbox.Changed, '#host_tool_cloud_provider_kind_enabled')
    def on_cloud_provider_kind_enabled_changed(self, event: Checkbox.Changed) -> None:
        self._toggle_fields('#host_tool_cloud_provider_kind_enabled',
                          ['#host_tool_cloud_provider_kind_path', '#host_tool_cloud_provider_kind_url'])

    @on(Checkbox.Changed, '#host_tool_cloud_provider_mdns_enabled')
    def on_cloud_provider_mdns_enabled_changed(self, event: Checkbox.Changed) -> None:
        self._toggle_fields('#host_tool_cloud_provider_mdns_enabled', ['#host_tool_cloud_provider_mdns_path'])

    @on(Checkbox.Changed, '#host_registry_enabled')
    def on_registry_enabled(self, event: Checkbox.Changed):
        self._toggle_fields('#host_registry_enabled', [
            '#host_registry_name', '#host_registry_port', '#host_registry_image', '#host_registry_volume_name'
        ])

    @on(Checkbox.Changed, '#host_postgresql_enabled')
    def on_postgresql_enabled(self, event: Checkbox.Changed):
        self._toggle_fields('#host_postgresql_enabled', [
            '#host_postgresql_name', '#host_postgresql_port', '#host_postgresql_image', '#host_postgresql_volume_name'
        ])

    @on(Checkbox.Changed, '#host_minio_enabled')
    def on_minio_enabled(self, event: Checkbox.Changed):
        self._toggle_fields('#host_minio_enabled', [
            '#host_minio_name', '#host_minio_port', '#host_minio_console_port',
            '#host_minio_image', '#host_minio_volume_name'
        ])

    @on(Checkbox.Changed, '#host_kafka_enabled')
    def on_kafka_enabled(self, event: Checkbox.Changed):
        self._toggle_fields('#host_kafka_enabled', [
            '#host_kafka_name', '#host_kafka_port', '#host_kafka_image', '#host_kafka_volume_name'
        ])

    @on(Checkbox.Changed, '#cluster_cni_ui')
    def on_cni_ui_changed(self, event: Checkbox.Changed):
        self._toggle_fields('#cluster_cni_ui', ['#cluster_cni_hostname'])

    @on(Checkbox.Changed, '#cluster_mesh_enabled')
    def on_mesh_enabled_changed(self, event: Checkbox.Changed):
        self._toggle_fields('#cluster_mesh_enabled', ['#cluster_mesh_kind', '#cluster_mesh_ns'])

    @on(Checkbox.Changed, '#stack_prometheus_enabled')
    def on_prometheus_enabled_changed(self, event: Checkbox.Changed):
        self._toggle_fields('#stack_prometheus_enabled', [
            '#stack_prometheus_ns', '#stack_prometheus_hostname',
            '#stack_prometheus_service_monitor_crd', '#stack_prometheus_pod_monitor_crd'
        ])

    @on(Checkbox.Changed, '#stack_alloy_enabled')
    def on_alloy_enabled_changed(self, event: Checkbox.Changed):
        self._toggle_fields('#stack_alloy_enabled', ['#stack_alloy_ns', '#stack_alloy_hostname'])

    @on(Checkbox.Changed, '#stack_loki_enabled')
    def on_loki_enabled_changed(self, event: Checkbox.Changed):
        self._toggle_fields('#stack_loki_enabled', ['#stack_loki_ns', '#stack_loki_hostname'])

    @on(Checkbox.Changed, '#stack_keycloak_enabled')
    def on_keycloak_enabled_changed(self, event: Checkbox.Changed):
        self._toggle_fields('#stack_keycloak_enabled', [
            '#stack_keycloak_ns', '#stack_keycloak_hostname', '#stack_keycloak_operator_version'
        ])

    @on(Checkbox.Changed, '#stack_grafana_enabled')
    def on_grafana_enabled_changed(self, event: Checkbox.Changed):
        self._toggle_fields('#stack_grafana_enabled', [
            '#stack_grafana_ns', '#stack_grafana_hostname',
            '#stack_grafana_client_id', '#stack_grafana_admin_user'
        ])

    @on(Checkbox.Changed, '#stack_jaeger_enabled')
    def on_jaeger_enabled_changed(self, event: Checkbox.Changed):
        self._toggle_fields('#stack_jaeger_enabled', ['#stack_jaeger_ns', '#stack_jaeger_hostname'])

    @on(Checkbox.Changed, '#stack_kiali_enabled')
    def on_kiali_enabled_changed(self, event: Checkbox.Changed):
        self._toggle_fields('#stack_kiali_enabled', [
            '#stack_kiali_ns', '#stack_kiali_hostname', '#stack_kiali_version'
        ])

    @on(ConfigSidebar.SectionSelected)
    async def on_section_selected(self, event: ConfigSidebar.SectionSelected) -> None:
        """Handle sidebar navigation to specific subsections"""
        # Map sidebar IDs to their corresponding collapsible widget IDs
        section_targets = {
            'host-config': 'header-host-config',
            'cluster-config': 'header-cluster-config',
            'stack-config': 'header-stack-config',
            'host-tools': 'section-host-tools',
            'host-dns': 'section-host-dns',
            'host-registry': 'section-host-registry',
            'host-postgresql': 'section-host-postgresql',
            'host-minio': 'section-host-minio',
            'host-kafka': 'section-host-kafka',
            'cluster-basic': 'section-cluster-basic',
            'cluster-cni': 'section-cluster-cni',
            'cluster-mesh': 'section-cluster-mesh',
            'cluster-pki': 'section-cluster-pki',
            'cluster-edge': 'section-cluster-edge',
            'stack-prometheus': 'section-stack-prometheus',
            'stack-alloy': 'section-stack-alloy',
            'stack-loki': 'section-stack-loki',
            'stack-keycloak': 'section-stack-keycloak',
            'stack-grafana': 'section-stack-grafana',
            'stack-jaeger': 'section-stack-jaeger',
            'stack-kiali': 'section-stack-kiali',
        }

        target_id = section_targets.get(event.section_id)
        if not target_id:
            return

        try:
            target_widget = self.query_one(f'#{target_id}')
            if isinstance(target_widget, Collapsible):
                target_widget.collapsed = False
            
            self.query_one('#config-scroll', VerticalScroll).scroll_to_widget(target_widget, animate=True)
        except Exception:
            pass

    def compose(self) -> ComposeResult:
        """Build the complete configuration UI"""
        with Horizontal():
            yield ConfigSidebar()
            with VerticalScroll(can_focus=True, id='config-scroll'):
                # Host Configuration Section
                yield Label("HOST CONFIGURATION", id="header-host-config", classes="section-header")
                with Collapsible(title="Tools", id="section-host-tools"):
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

                with Collapsible(title="Cloud Provider: Kind", id="section-host-cloud-kind"):
                    with FormLine():
                        yield Checkbox('Enabled', id='host_tool_cloud_provider_kind_enabled')
                    with FormLine():
                        yield Label('Path:')
                        yield ExecutablePathInput(
                            id='host_tool_cloud_provider_kind_path',
                            placeholder='Path to cloud-provider-kind',
                        )
                    with FormLine():
                        yield Label('URL:')
                        yield Input(id='host_tool_cloud_provider_kind_url')

                with Collapsible(title="Cloud Provider: MDNS", id="section-host-cloud-mdns"):
                    with FormLine():
                        yield Checkbox('Enabled', id='host_tool_cloud_provider_mdns_enabled')
                    with FormLine():
                        yield Label('Path:')
                        yield ExecutablePathInput(
                        id='host_tool_cloud_provider_mdns_path',
                        placeholder='Path to cloud-provider-mdns',
                    )

                with Collapsible(title="DNS", id="section-host-dns"):
                    with FormLine():
                        yield Label('Kind:')
                        yield Select(
                        options=[(e.value, e.value) for e in HostDNSKindEnum],
                        id='host_dns_kind',
                    )
                    with FormLine():
                        yield Label('Name:')
                        yield Input(id='host_dns_name')
                    with FormLine():
                        yield Label('Image:')
                        yield Input(id='host_dns_image')
                    with FormLine():
                        yield Label('Volume Name:')
                        yield Input(id='host_dns_volume_name')
                    with FormLine():
                        yield Label('Forwarders:')
                        yield Input(id='host_dns_forwarders')
                    with FormLine():
                        yield Label('Server:')
                        yield Input(id='host_dns_server')
                    with FormLine():
                        yield Label('Port:')
                        yield Input(id='host_dns_port', type='integer', validators=[PortValidator()])
                    with FormLine():
                        yield Label('Control Port:')
                        yield Input(id='host_dns_control_port', type='integer', validators=[PortValidator()])
                    with FormLine():
                        yield Label('Key Name:')
                        yield Input(id='host_dns_key_name')
                    with FormLine():
                        yield Label('Key Algorithm:')
                        yield Input(id='host_dns_key_algorithm')
                    with FormLine():
                        yield Label('Key Secret:')
                        yield Input(id='host_dns_key_secret', password=True)
                    with FormLine():
                        yield Label('Protocol:')
                        yield Input(id='host_dns_protocol')
                    with FormLine():
                        yield Label('Zone:')
                        yield Input(id='host_dns_zone')
                    with FormLine():
                        yield Label('TTL:')
                        yield Input(id='host_dns_ttl', type='integer')

                with Collapsible(title="Registry", id="section-host-registry"):
                    with FormLine():
                        yield Checkbox('Enabled', id='host_registry_enabled')
                    with FormLine():
                        yield Label('Name:')
                        yield Input(id='host_registry_name')
                    with FormLine():
                        yield Label('Port:')
                        yield Input(id='host_registry_port', type='integer', validators=[PortValidator()])
                    with FormLine():
                        yield Label('Image:')
                        yield Input(id='host_registry_image')
                    with FormLine():
                        yield Label('Volume Name:')
                        yield Input(id='host_registry_volume_name')

                with Collapsible(title="PostgreSQL", id="section-host-postgresql"):
                    with FormLine():
                        yield Checkbox('Enabled', id='host_postgresql_enabled')
                    with FormLine():
                        yield Label('Name:')
                        yield Input(id='host_postgresql_name')
                    with FormLine():
                        yield Label('Port:')
                        yield Input(id='host_postgresql_port', type='integer', validators=[PortValidator()])
                    with FormLine():
                        yield Label('Image:')
                        yield Input(id='host_postgresql_image')
                    with FormLine():
                        yield Label('Volume Name:')
                        yield Input(id='host_postgresql_volume_name')

                with Collapsible(title="MinIO", id="section-host-minio"):
                    with FormLine():
                        yield Checkbox('Enabled', id='host_minio_enabled')
                    with FormLine():
                        yield Label('Name:')
                        yield Input(id='host_minio_name')
                    with FormLine():
                        yield Label('Port:')
                        yield Input(id='host_minio_port', type='integer', validators=[PortValidator()])
                    with FormLine():
                        yield Label('Console Port:')
                        yield Input(id='host_minio_console_port', type='integer', validators=[PortValidator()])
                    with FormLine():
                        yield Label('Image:')
                        yield Input(id='host_minio_image')
                    with FormLine():
                        yield Label('Volume Name:')
                        yield Input(id='host_minio_volume_name')

                with Collapsible(title="Kafka", id="section-host-kafka"):
                    with FormLine():
                        yield Checkbox('Enabled', id='host_kafka_enabled')
                    with FormLine():
                        yield Label('Name:')
                        yield Input(id='host_kafka_name')
                    with FormLine():
                        yield Label('Port:')
                        yield Input(id='host_kafka_port', type='integer', validators=[PortValidator()])
                    with FormLine():
                        yield Label('Image:')
                        yield Input(id='host_kafka_image')
                    with FormLine():
                        yield Label('Volume Name:')
                        yield Input(id='host_kafka_volume_name')

                # Cluster Configuration Section
                yield Label("CLUSTER CONFIGURATION", id="header-cluster-config", classes="section-header")
                with Collapsible(title="Basic", id="section-cluster-basic"):
                    with FormLine():
                        yield Label('Name:')
                        yield Input(id='cluster_name')
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

                with Collapsible(title="CNI", id="section-cluster-cni"):
                    with FormLine():
                        yield Label('Kind:')
                        yield Select(
                        options=[(e.value, e.value) for e in ClusterCNIKindEnum],
                        id='cluster_cni_kind',
                    )
                    with FormLine():
                        yield Checkbox('Exclusive', id='cluster_cni_exclusive')
                    with FormLine():
                        yield Checkbox('UI', id='cluster_cni_ui')
                    with FormLine():
                        yield Label('Hostname:')
                        yield Input(id='cluster_cni_hostname')

                with Collapsible(title="Service Mesh", id="section-cluster-mesh"):
                    with FormLine():
                        yield Checkbox('Enabled', id='cluster_mesh_enabled')
                    with FormLine():
                        yield Label('Kind:')
                        yield Select(
                        options=[(e.value, e.value) for e in ClusterMeshKind],
                        id='cluster_mesh_kind',
                    )
                    with FormLine():
                        yield Label('Namespace:')
                        yield Input(id='cluster_mesh_ns')

                with Collapsible(title="PKI", id="section-cluster-pki"):
                    with FormLine():
                        yield Label('Namespace:')
                        yield Input(id='cluster_pki_ns')
                    with FormLine():
                        yield Label('CRD URL:')
                        yield Input(id='cluster_pki_crd')
                    with FormLine():
                        yield Label('Key Type:')
                        yield Input(id='cluster_pki_key_type')
                    with FormLine():
                        yield Label('Key Curve:')
                        yield Input(id='cluster_pki_key_curve')
                    with FormLine():
                        yield Label('Key Size:')
                        yield Input(id='cluster_pki_key_size', type='integer')
                    with FormLine():
                        yield Label('Cert Validity:')
                        yield Input(id='cluster_pki_crt_validity')

                with Collapsible(title="Edge", id="section-cluster-edge"):
                    with FormLine():
                        yield Label('Kind:')
                        yield Select(
                        options=[(e.value, e.value) for e in ClusterEdgeKindEnum],
                        id='cluster_edge_kind',
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
                    with FormLine():
                        yield Label('Traefik Repository:')
                        yield Input(id='cluster_edge_traefik_repository')
                    with FormLine():
                        yield Label('Traefik Tag:')
                        yield Input(id='cluster_edge_traefik_tag')
                    with FormLine():
                        yield Label('Traefik Hostname:')
                        yield Input(id='cluster_edge_traefik_hostname')
                    with FormLine():
                        yield Label('Traefik Dashboard:')
                        yield Input(id='cluster_edge_traefik_dashboard_hostname')

                # Stack Configuration Section
                yield Label("STACK CONFIGURATION", id="header-stack-config", classes="section-header")
                with Collapsible(title="Prometheus", id="section-stack-prometheus"):
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

                with Collapsible(title="Alloy", id="section-stack-alloy"):
                    with FormLine():
                        yield Checkbox('Enabled', id='stack_alloy_enabled')
                    with FormLine():
                        yield Label('Namespace:')
                        yield Input(id='stack_alloy_ns')
                    with FormLine():
                        yield Label('Hostname:')
                        yield Input(id='stack_alloy_hostname')

                with Collapsible(title="Loki", id="section-stack-loki"):
                    with FormLine():
                        yield Checkbox('Enabled', id='stack_loki_enabled')
                    with FormLine():
                        yield Label('Namespace:')
                        yield Input(id='stack_loki_ns')
                    with FormLine():
                        yield Label('Hostname:')
                        yield Input(id='stack_loki_hostname')

                with Collapsible(title="Keycloak", id="section-stack-keycloak"):
                    with FormLine():
                        yield Checkbox('Enabled', id='stack_keycloak_enabled')
                    with FormLine():
                        yield Label('Namespace:')
                        yield Input(id='stack_keycloak_ns')
                    with FormLine():
                        yield Label('Hostname:')
                        yield Input(id='stack_keycloak_hostname')
                    with FormLine():
                        yield Label('Operator Version:')
                        yield Input(id='stack_keycloak_operator_version')

                with Collapsible(title="Grafana", id="section-stack-grafana"):
                    with FormLine():
                        yield Checkbox('Enabled', id='stack_grafana_enabled')
                    with FormLine():
                        yield Label('Namespace:')
                        yield Input(id='stack_grafana_ns')
                    with FormLine():
                        yield Label('Hostname:')
                        yield Input(id='stack_grafana_hostname')
                    with FormLine():
                        yield Label('Client ID:')
                        yield Input(id='stack_grafana_client_id')
                    with FormLine():
                        yield Label('Admin User:')
                        yield Input(id='stack_grafana_admin_user')

                with Collapsible(title="Jaeger", id="section-stack-jaeger"):
                    with FormLine():
                        yield Checkbox('Enabled', id='stack_jaeger_enabled')
                    with FormLine():
                        yield Label('Namespace:')
                        yield Input(id='stack_jaeger_ns')
                    with FormLine():
                        yield Label('Hostname:')
                        yield Input(id='stack_jaeger_hostname')

                with Collapsible(title="Kiali", id="section-stack-kiali"):
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
                    yield Button('Apply Configuration', id='apply_configuration', variant='primary')
