import pathlib
import sys
import argparse

from textual.app import App, ComposeResult
from textual.widgets import (
    Footer,
    TabbedContent,
    TabPane
)

from kube_eng import __version__, __default_config_path__
from kube_eng.config import Config
from kube_eng.common import AnsibleEvent, AnsibleExecution
from kube_eng.tui.config_tab import ConfigTab

from .widgets import AppHeader, AppBody, TUILog


class KubeEngApp(App[None]):
    CSS_PATH = 'tui.tcss'
    BINDINGS = [('q', 'quit', 'Quit')]

    def __init__(self, config: Config) -> None:
        super().__init__()
        self._config = config
        self._kelog = TUILog(id='log')

    def on_mount(self) -> None:
        self.theme = 'tokyo-night'

    def on_config_tab_configured(self, message: ConfigTab.Configured) -> None:
        ex = AnsibleExecution(self._config, self.tui_ansible_callback).execute(playbook='apply_host.yml')

    def tui_ansible_callback(self, ev: AnsibleEvent):
        self._kelog.add_event(ev)

    def compose(self) -> ComposeResult:
        yield AppHeader()
        with AppBody():
            with TabbedContent(id='tabs'):
                yield ConfigTab('Configuration', config=self._config)
                yield TabPane('Status', id='status')
            yield self._kelog
        yield Footer(show_command_palette=False)


def run() -> int:
    parser = argparse.ArgumentParser(f'Kube-Eng {__version__}')
    parser.add_argument(
        '--config',
        type=pathlib.Path,
        required=False,
        dest='config_path',
        default=__default_config_path__,
        help=f'Path to the config file, defaults to {__default_config_path__}',
    )
    args = parser.parse_args()

    config = Config.load(config_path=args.config_path)
    app = KubeEngApp(config)
    app.run()
    return 0


if __name__ == '__main__':
    sys.exit(run())
