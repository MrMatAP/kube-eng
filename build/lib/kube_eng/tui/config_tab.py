import pathlib
from encodings import normalize_encoding

from textual import on
from textual.app import ComposeResult
from textual.containers import Grid, VerticalScroll
from textual.content import ContentType
from textual.message import Message
from textual.validation import Validator, ValidationResult
from textual.widget import Widget
from textual.widgets import (
    Static,
    TabPane,
    Input,
    Label,
    Checkbox,
    Button,
)

from kube_eng.config import RootConfig
from kube_eng.tui.widgets import FormGroup, FormLine, FormActions


class ConfigGrid(Grid):
    def __init__(self, border_title: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.border_title = border_title


class ExecutablePathValidator(Validator):
    def validate(self, value: str) -> ValidationResult:
        path = pathlib.Path(value)
        if not path.exists():
            return self.failure(f'{value} does not exist')
        if not path.is_file():
            return self.failure(f'{value} is not a file')
        return self.success()


class ExecutablePathInput(Input):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.validate_on = {'changed', 'submitted'}
        self.validators = [ExecutablePathValidator()]


class ConfigTab(TabPane):
    DEFAULT_CLASSES = 'form'

    def __init__(self, title: ContentType, *children: Widget, config: RootConfig, name: str | None = None,
                 id: str | None = None, classes: str | None = None, disabled: bool = False):
        super().__init__(title, *children, name=name, id=id, classes=classes, disabled=disabled)
        self._config = config

    class Configured(Message):
        pass

    def on_mount(self) -> None:
        self.query_one('#host_tool_docker_path').value = str(self._config.host.tool.docker.path)
        self.query_one('#host_tool_kind_path').value = str(self._config.host.tool.kind.path)
        self.query_one('#host_tool_kubectl_path').value = str(self._config.host.tool.kubectl.path)
        self.query_one('#host_tool_cloud_provider_kind_enabled').value = self._config.host.tool.cloud_provider_kind.enabled
        self.query_one('#host_tool_cloud_provider_kind_path').value = str(self._config.host.tool.cloud_provider_kind.path)
        self.query_one('#host_tool_cloud_provider_kind_path').disabled = not self._config.host.tool.cloud_provider_kind.enabled
        self.query_one('#host_tool_cloud_provider_mdns_enabled').value = self._config.host.tool.cloud_provider_mdns.enabled
        self.query_one('#host_tool_cloud_provider_mdns_path').value = str(self._config.host.tool.cloud_provider_mdns.path)
        self.query_one('#host_tool_cloud_provider_mdns_path').disabled = not self._config.host.tool.cloud_provider_mdns.enabled
        self.query_one('#host_tool_bind_enabled').value = self._config.host.tool.bind.enabled
        self.query_one('#host_tool_bind_path').value = str(self._config.host.tool.bind.path)
        self.query_one('#host_tool_bind_path').disabled = not self._config.host.tool.bind.enabled
        self.query_one('#host_tool_bind_forwarders').value = self._config.host.tool.bind.forwarders
        self.query_one('#host_tool_bind_forwarders').disabled = not self._config.host.tool.bind.enabled
        self.query_one('#host_tool_istioctl_path').value = str(self._config.host.tool.istioctl.path)
        self.query_one('#host_tool_kustomize_path').value = str(self._config.host.tool.kustomize.path)
        
        self.query_one('#host_registry_enabled').value = self._config.host.registry.enabled
        self.query_one('#host_registry_name').value = self._config.host.registry.name
        self.query_one('#host_registry_name').disabled = not self._config.host.registry.enabled
        self.query_one('#host_registry_port').value = str(self._config.host.registry.port)
        self.query_one('#host_registry_port').disabled = not self._config.host.registry.enabled
        self.query_one('#host_registry_image').value = self._config.host.registry.image
        self.query_one('#host_registry_image').disabled = not self._config.host.registry.enabled
        self.query_one('#host_registry_volume_name').value = self._config.host.registry.volume_name
        self.query_one('#host_registry_volume_name').disabled = not self._config.host.registry.enabled
        
        self.query_one('#host_postgresql_enabled').value = self._config.host.postgresql.enabled
        self.query_one('#host_postgresql_name').value = self._config.host.postgresql.name
        self.query_one('#host_postgresql_name').disabled = not self._config.host.postgresql.enabled
        self.query_one('#host_postgresql_port').value = str(self._config.host.postgresql.port)
        self.query_one('#host_postgresql_port').disabled = not self._config.host.postgresql.enabled
        self.query_one('#host_postgresql_image').value = self._config.host.postgresql.image
        self.query_one('#host_postgresql_image').disabled = not self._config.host.postgresql.enabled
        self.query_one('#host_postgresql_volume_name').value = self._config.host.postgresql.volume_name
        self.query_one('#host_postgresql_volume_name').disabled = not self._config.host.postgresql.enabled

        self.query_one('#host_minio_enabled').value = self._config.host.minio.enabled
        self.query_one('#host_minio_name').value = self._config.host.minio.name
        self.query_one('#host_minio_name').disabled = not self._config.host.minio.enabled
        self.query_one('#host_minio_port').value = str(self._config.host.minio.port)
        self.query_one('#host_minio_port').disabled = not self._config.host.minio.enabled
        self.query_one('#host_minio_console_port').value = str(self._config.host.minio.console_port)
        self.query_one('#host_minio_console_port').disabled = not self._config.host.minio.enabled
        self.query_one('#host_minio_image').value = self._config.host.minio.image
        self.query_one('#host_minio_image').disabled = not self._config.host.minio.enabled
        self.query_one('#host_minio_volume_name').value = self._config.host.minio.volume_name
        self.query_one('#host_minio_volume_name').disabled = not self._config.host.minio.enabled


    @on(Button.Pressed, '#apply_host_configuration')
    def apply_host_configuration(self, event: Button.Pressed) -> None:
        self._config.host.tool.docker.path = pathlib.Path(self.query_one('#host_tool_docker_path', Input).value)
        self._config.host.tool.kind.path = pathlib.Path(self.query_one('#host_tool_kind_path', Input).value)
        self._config.host.tool.kubectl.path = pathlib.Path(self.query_one('#host_tool_kubectl_path', Input).value)
        self._config.host.tool.cloud_provider_kind.enabled = self.query_one('#host_tool_cloud_provider_kind_enabled', Checkbox).value
        self._config.host.tool.cloud_provider_kind.path = pathlib.Path(self.query_one('#host_tool_cloud_provider_kind_path', Input).value)
        self._config.host.tool.cloud_provider_mdns.enabled = self.query_one('#host_tool_cloud_provider_mdns_enabled', Checkbox).value
        self._config.host.tool.cloud_provider_mdns.path = pathlib.Path(self.query_one('#host_tool_cloud_provider_mdns_path', Input).value)
        self._config.host.tool.bind.enabled = self.query_one('#host_tool_bind_enabled', Checkbox).value
        self._config.host.tool.bind.path = pathlib.Path(self.query_one('#host_tool_bind_path', Input).value)
        self._config.host.tool.bind.forwarders = self.query_one('#host_tool_bind_forwarders', Input).value
        self._config.host.tool.istioctl.path = pathlib.Path(self.query_one('#host_tool_istioctl_path', Input).value)
        self._config.host.tool.kustomize.path = pathlib.Path(self.query_one('#host_tool_kustomize_path', Input).value)

        self._config.host.registry.enabled = self.query_one('#host_registry_enabled', Checkbox).value
        self._config.host.registry.name = self.query_one('#host_registry_name', Input).value
        self._config.host.registry.port = int(self.query_one('#host_registry_port', Input).value)
        self._config.host.registry.image = self.query_one('#host_registry_image', Input).value
        self._config.host.registry.volume_name = self.query_one('#host_registry_volume_name', Input).value

        self._config.host.postgresql.enabled = self.query_one('#host_postgresql_enabled', Checkbox).value
        self._config.host.postgresql.name = self.query_one('#host_postgresql_name', Input).value
        self._config.host.postgresql.port = int(self.query_one('#host_postgresql_port', Input).value)
        self._config.host.postgresql.image = self.query_one('#host_postgresql_image', Input).value
        self._config.host.postgresql.volume_name = self.query_one('#host_postgresql_volume_name', Input).value

        self._config.host.minio.enabled = self.query_one('#host_minio_enabled', Checkbox).value
        self._config.host.minio.name = self.query_one('#host_minio_name', Input).value
        self._config.host.minio.port = int(self.query_one('#host_minio_port', Input).value)
        self._config.host.minio.console_port = int(self.query_one('#host_minio_console_port', Input).value)
        self._config.host.minio.image = self.query_one('#host_minio_image', Input).value
        self._config.host.minio.volume_name = self.query_one('#host_minio_volume_name', Input).value
        self._config.save()

        self.post_message(self.Configured())

    @on(Checkbox.Changed, '#host_tool_cloud_provider_kind_enabled')
    def on_cloud_provider_kind_enabled_changed(self, event: Checkbox.Changed) -> None:
        self.query_one('#host_tool_cloud_provider_kind_path').disabled = not event.value

    @on(Checkbox.Changed, '#host_tool_cloud_provider_mdns_enabled')
    def on_cloud_provider_mdns_enabled_changed(self, event: Checkbox.Changed) -> None:
        self.query_one('#host_tool_cloud_provider_mdns_path').disabled = not event.value

    @on(Checkbox.Changed, '#host_tool_bind_enabled')
    def on_bind_enabled(self, event: Checkbox.Changed):
        self.query_one('#host_tool_bind_path').disabled = not event.value
        self.query_one('#host_tool_bind_forwarders').disabled = not event.value

    @on(Checkbox.Changed, '#host_registry_enabled')
    def on_registry_enabled(self, event: Checkbox.Changed):
        self.query_one('#host_registry_name').disabled = not event.value
        self.query_one('#host_registry_port').disabled = not event.value
        self.query_one('#host_registry_image').disabled = not event.value
        self.query_one('#host_registry_volume_name').disabled = not event.value

    @on(Checkbox.Changed, '#host_postgresql_enabled')
    def on_postgresql_enabled(self, event: Checkbox.Changed):
        self.query_one('#host_postgresql_name').disabled = not event.value
        self.query_one('#host_postgresql_port').disabled = not event.value
        self.query_one('#host_postgresql_image').disabled = not event.value
        self.query_one('#host_postgresql_volume_name').disabled = not event.value

    @on(Checkbox.Changed, '#host_minio_enabled')
    def on_minio_enabled(self, event: Checkbox.Changed):
        self.query_one('#host_minio_name').disabled = not event.value
        self.query_one('#host_minio_port').disabled = not event.value
        self.query_one('#host_minio_console_port').disabled = not event.value
        self.query_one('#host_minio_image').disabled = not event.value
        self.query_one('#host_minio_volume_name').disabled = not event.value

    def compose(self) -> ComposeResult:
        with VerticalScroll(can_focus=True):
            with FormGroup(title='Host'):
                with FormLine():
                    yield Label('Docker:')
                    yield ExecutablePathInput(
                        id='host_tool_docker_path',
                        placeholder='Path to docker',
                        valid_empty=False,
                    )
                with FormLine():
                    yield Label('Kind:')
                    yield ExecutablePathInput(
                        id='host_tool_kind_path',
                        placeholder='Path to kind',
                        valid_empty=False,
                    )
                with FormLine():
                    yield Label('Kubectl:')
                    yield ExecutablePathInput(
                        id='host_tool_kubectl_path',
                        placeholder='Path to kubectl',
                        valid_empty=False,
                    )
                with FormGroup('cloud-provider-kind'):
                    with FormLine():
                        yield Checkbox('Enabled',
                                       id='host_tool_cloud_provider_kind_enabled')
                    with FormLine():
                        yield Label('Path:')
                        yield ExecutablePathInput(
                            id='host_tool_cloud_provider_kind_path',
                            placeholder='Path to cloud-provider-kind',
                            valid_empty=False,
                        )
                with FormGroup('cloud-provider-mdns'):
                    with FormLine():
                        yield Checkbox('Enabled',
                                       id='host_tool_cloud_provider_mdns_enabled')
                    with FormLine():
                        yield Label('Path:')
                        yield ExecutablePathInput(
                            id='host_tool_cloud_provider_mdns_path',
                            placeholder='Path to cloud-provider-mdns',
                            valid_empty=False,
                        )
                with FormGroup('BIND'):
                    with FormLine():
                        yield Checkbox('Enabled',
                                       id='host_tool_bind_enabled')
                    with FormLine():
                        yield Label('Path:')
                        yield ExecutablePathInput(
                            id='host_tool_bind_path',
                            placeholder='Path to bind',
                        )
                    with FormLine():
                        yield Label('Forwarders:')
                        yield Input(id='host_tool_bind_forwarders')
                with FormLine():
                    yield Label('Istioctl:')
                    yield ExecutablePathInput(
                        id='host_tool_istioctl_path',
                        placeholder='Path to istioctl',
                        valid_empty=False,
                    )
                with FormLine():
                    yield Label('Kustomize:')
                    yield ExecutablePathInput(
                        id='host_tool_kustomize_path',
                        placeholder='Path to kustomize',
                        valid_empty=False,
                    )
                with FormGroup('Registry'):
                    with FormLine():
                        yield Checkbox('Enabled', id='host_registry_enabled')
                    with FormLine():
                        yield Label('Name:')
                        yield Input(id='host_registry_name')
                    with FormLine():
                        yield Label('Port (Host):')
                        yield Input(id='host_registry_port', type='integer')
                    with FormLine():
                        yield Label('Image:')
                        yield Input(id='host_registry_image')
                    with FormLine():
                        yield Label('Volume Name:')
                        yield Input(id='host_registry_volume_name')
                with FormGroup('PostgreSQL'):
                    with FormLine():
                        yield Checkbox('Enabled', id='host_postgresql_enabled')
                    with FormLine():
                        yield Label('Name:')
                        yield Input(id='host_postgresql_name')
                    with FormLine():
                        yield Label('Port:')
                        yield Input(id='host_postgresql_port', type='integer')
                    with FormLine():
                        yield Label('Image:')
                        yield Input(id='host_postgresql_image')
                    with FormLine():
                        yield Label('Volume Name:')
                        yield Input(id='host_postgresql_volume_name')
                with FormGroup('Minio'):
                    with FormLine():
                        yield Checkbox('Enabled', id='host_minio_enabled')
                    with FormLine():
                        yield Label('Name:')
                        yield Input(id='host_minio_name')
                    with FormLine():
                        yield Label('Port:')
                        yield Input(id='host_minio_port', type='integer')
                    with FormLine():
                        yield Label('Console Port:')
                        yield Input(id='host_minio_console_port', type='integer')
                    with FormLine():
                        yield Label('Image:')
                        yield Input(id='host_minio_image')
                    with FormLine():
                        yield Label('Volume Name:')
                        yield Input(id='host_minio_volume_name')
                with FormActions():
                    yield Button('Apply', id='apply_host_configuration')
            with FormGroup(title='Cluster'):
                yield Static('Cluster Configuration')
            with FormGroup(title='Stack'):
                yield Static('Stack Configuration')
