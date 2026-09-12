"""
Sidebar navigation widget for configuration sections.
"""

from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.message import Message
from textual.widgets import OptionList
from textual.widgets.option_list import Option


class ConfigSidebar(Container):
    """
    Sidebar navigation for configuration sections.
    Displays a hierarchical list of configuration categories and sections.
    """

    class SectionSelected(Message):
        """Message sent when a navigation section is selected"""

        def __init__(self, section_id: str) -> None:
            self.section_id = section_id
            super().__init__()

    def compose(self) -> ComposeResult:
        yield OptionList(
            Option('Host', id='host-config'),
            Option('  Tools', id='host-tools'),
            Option('Infrastructure', id='infra-config'),
            Option('  Network', id='infra-net'),
            Option('  PKI', id='infra-pki'),
            Option('  DNS', id='infra-dns'),
            Option('  PostgreSQL', id='infra-pg'),
            Option('  Identity Provider', id='infra-idp'),
            Option('  S3', id='infra-s3'),
            Option('  Registry', id='infra-registry'),
            Option('  Kafka', id='infra-kafka'),
            Option('Cluster', id='cluster-config'),
            Option('  Basic', id='cluster-basic'),
            Option('  CNI', id='cluster-cni'),
            Option('  Mesh', id='cluster-mesh'),
            Option('  PKI', id='cluster-pki'),
            Option('  Edge', id='cluster-edge'),
            Option('Stack', id='stack-config'),
            Option('  Prometheus', id='stack-prometheus'),
            Option('  Mimir', id='stack-mimir'),
            Option('  Alloy', id='stack-alloy'),
            Option('  Loki', id='stack-loki'),
            Option('  Grafana', id='stack-grafana'),
            Option('  Tempo', id='stack-tempo'),
            Option('  Kiali', id='stack-kiali'),
            id='sidebar-nav',
        )

    @on(OptionList.OptionSelected)
    def on_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle navigation selection and post message to parent"""
        if event.option_id:
            self.post_message(self.SectionSelected(event.option_id))
