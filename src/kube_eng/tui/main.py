import pathlib
import sys
import argparse

from textual.app import App, ComposeResult
from textual.widgets import (
    Footer,
    Tab,
    TabbedContent,
)
from textual.worker import Worker

from kube_eng import __version__, __default_config_path__
from kube_eng.config import RootConfig
from kube_eng.common import AnsibleEvent, AnsibleExecution
from kube_eng.common.ansible_execution import cmd_to_playbook
from kube_eng.tui.ansible_tab import AnsibleTab
from kube_eng.tui.config_tab import ConfigTab
from kube_eng.tui.status_tab import StatusTab
from kube_eng.tui.widgets import AppHeader, AppBody, ActionsModal

_NON_ANSIBLE_TABS = ('config-tab', 'status-tab')


class KubeEngApp(App[None]):
    CSS_PATH = 'tui.tcss'
    BINDINGS = [
        ('ctrl+q', 'quit', 'Quit'),
        ('ctrl+a', 'show_actions', 'Actions'),
        ('ctrl+r', 'helm_repackage', 'Repackage'),
        ('ctrl+d', 'dns_update', 'DNS Update'),
    ]

    def __init__(self, config: RootConfig) -> None:
        super().__init__()
        self._config = config
        self._executing: bool = False
        self._current_execution: AnsibleExecution | None = None
        self._current_worker: Worker | None = None

    def on_mount(self) -> None:
        self.theme = 'dracula'
        self.query_one('#tabs', TabbedContent).hide_tab('ansible-tab')

    def _set_nav_disabled(self, disabled: bool) -> None:
        """Enable or disable all tab buttons except the ansible tab."""
        for tab in self.query('Tab').results(Tab):
            if tab.id in _NON_ANSIBLE_TABS:
                tab.disabled = disabled

    async def execute_playbook(self, playbook_key: str) -> None:
        """
        Execute an Ansible playbook and display progress in the Ansible tab.

        Args:
            playbook_key: Key from cmd_to_playbook dict (e.g., 'host-apply')
        """
        playbook = cmd_to_playbook.get(playbook_key)
        if not playbook:
            return

        tabs = self.query_one('#tabs', TabbedContent)
        ansible_tab = self.query_one('#ansible-tab', AnsibleTab)
        ansible_tab.reset(playbook)
        tabs.show_tab('ansible-tab')
        tabs.active = 'ansible-tab'

        self._executing = True
        self._set_nav_disabled(True)

        def ansible_callback(event: AnsibleEvent) -> None:
            self.call_from_thread(ansible_tab.add_event, event)

        try:
            self._current_execution = AnsibleExecution(self._config, ansible_callback)
            await self._current_execution.execute(playbook=playbook)
            ansible_tab.on_execution_complete(True)
        except Exception:
            ansible_tab.on_execution_complete(False)
        finally:
            self._executing = False
            self._current_execution = None
            self._current_worker = None
            self._set_nav_disabled(False)

    def on_ansible_tab_cancel_requested(self, _: AnsibleTab.CancelRequested) -> None:
        """Cancel the running playbook when the cancel button is pressed."""
        if self._current_execution is not None:
            self._current_execution.cancel()

    def on_ansible_tab_navigate_to_status(self, _: AnsibleTab.NavigateToStatus) -> None:
        """Navigate to the Status tab when Ok is pressed after execution."""
        self.query_one('#tabs', TabbedContent).active = 'status-tab'

    async def action_quit(self) -> None:
        """Cancel any running execution and wait for it to finish before quitting."""
        if self._executing and self._current_execution is not None:
            self._current_execution.cancel()
            if self._current_worker is not None:
                await self._current_worker.wait()
        self.exit()

    def action_show_actions(self) -> None:
        if self._executing:
            return

        def on_action_selected(action_id: str | None) -> None:
            if action_id:
                self._current_worker = self.run_worker(self.execute_playbook(action_id))

        self.push_screen(ActionsModal(), on_action_selected)

    def action_helm_repackage(self) -> None:
        if self._executing:
            return
        self._current_worker = self.run_worker(self.execute_playbook('helm-repackage'))

    def action_dns_update(self) -> None:
        if self._executing:
            return
        self._current_worker = self.run_worker(self.execute_playbook('dns-update'))

    def compose(self) -> ComposeResult:
        yield AppHeader()
        with AppBody():
            with TabbedContent(id='tabs'):
                yield ConfigTab('Configuration', config=self._config, id='config-tab')
                yield StatusTab('Status', id='status-tab')
                yield AnsibleTab('Ansible', id='ansible-tab')
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

    config = RootConfig.load(config_path=args.config_path)
    app = KubeEngApp(config)
    app.run()
    return 0


if __name__ == '__main__':
    sys.exit(run())
