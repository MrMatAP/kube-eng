"""
Tab for displaying Ansible playbook execution progress.
Hidden until a playbook is executed.
"""

from textual import on
from textual.app import ComposeResult
from textual.message import Message
from textual.widgets import TabPane, Static, RichLog, Button
from rich.text import Text

from kube_eng.common import AnsibleEvent, AnsibleStatusEnum


class AnsibleTab(TabPane):
    """
    Tab that displays Ansible playbook execution events in real-time.
    Hidden from the tab bar until a playbook is executed.
    """

    DEFAULT_CLASSES = 'ansible-tab'

    class CancelRequested(Message):
        """Posted when the user presses the cancel button during execution."""

    class NavigateToStatus(Message):
        """Posted when the user presses Ok after execution completes."""

    _status_colors: dict[AnsibleStatusEnum, str] = {
        AnsibleStatusEnum.ok: 'green',
        AnsibleStatusEnum.empty: 'dim green',
        AnsibleStatusEnum.running: 'orange',
        AnsibleStatusEnum.failed: 'red',
    }

    def __init__(self, title: str, **kwargs) -> None:
        super().__init__(title, **kwargs)
        self._playbook_name = ''
        self._complete = False

    def compose(self) -> ComposeResult:
        yield Static('', id='ansible-title')
        yield RichLog(id='ansible-log', auto_scroll=True)
        yield Button('Cancel', variant='error', id='ansible-cancel-button')

    def reset(self, playbook_name: str) -> None:
        """Clear previous events and update the title for a new playbook run."""
        self._playbook_name = playbook_name
        title = self.query_one('#ansible-title', Static)
        title.update(f'Executing: {playbook_name}')
        title.remove_class('ansible-title--success', 'ansible-title--failure')
        title.add_class('ansible-title--running')
        self._complete = False
        self.query_one('#ansible-log', RichLog).clear()
        button = self.query_one('#ansible-cancel-button', Button)
        button.label = 'Cancel'
        button.variant = 'error'
        button.disabled = False

    def add_event(self, event: AnsibleEvent) -> None:
        """Append an Ansible event to the log, mirroring CLIAnsibleEventLog."""
        log = self.query_one('#ansible-log', RichLog)
        color = self._status_colors.get(event.status, 'white')

        log.write(Text(f'* {event.task}', style='white'))
        log.write(Text(f'  {event.msg}', style=color))
        if event.stdout:
            log.write(Text('  Stdout:', style='dim white'))
            log.write(Text(f'    {event.stdout}', style='dim white'))
        if event.stderr:
            log.write(Text('  Stderr:', style='dim yellow'))
            log.write(Text(f'    {event.stderr}', style='dim yellow'))
        for warning in event.warnings:
            log.write(Text('  Warnings:', style='yellow'))
            log.write(Text(f'    {warning}', style='yellow'))

    def on_execution_complete(self, success: bool) -> None:
        """Update the title bar and button to reflect the final execution state."""
        title = self.query_one('#ansible-title', Static)
        title.remove_class('ansible-title--running')
        if success:
            title.update(f'✓ Completed: {self._playbook_name}')
            title.add_class('ansible-title--success')
        else:
            title.update(f'✗ Failed: {self._playbook_name}')
            title.add_class('ansible-title--failure')
        self._complete = True
        button = self.query_one('#ansible-cancel-button', Button)
        button.label = 'Ok'
        button.variant = 'success'
        button.disabled = False

    @on(Button.Pressed, '#ansible-cancel-button')
    def _on_cancel_pressed(self) -> None:
        if self._complete:
            self.post_message(self.NavigateToStatus())
        else:
            self.query_one('#ansible-cancel-button', Button).disabled = True
            self.post_message(self.CancelRequested())
