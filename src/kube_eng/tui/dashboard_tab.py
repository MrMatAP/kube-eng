from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Header, Static, Footer

from kube_eng import __version__


class DashboardScreen(Screen):
    BINDINGS = [('ctrl+q', 'quit', 'Quit')]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield Static('Host', classes='box')
            yield Static('Cluster', classes='box')
            yield Static('Stack', classes='box')
        yield Footer(show_command_palette=False)

    def on_mount(self) -> None:
        self.title = f'kube-eng {__version__}'
        self.sub_title = 'Dashboard'
