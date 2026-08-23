"""
Status tab showing the current system status.
"""

from textual.app import ComposeResult
from textual.containers import Center, Middle
from textual.widgets import Static, TabPane


class StatusTab(TabPane):
    """
    Status tab - displays the current state of the infrastructure.
    """

    DEFAULT_CLASSES = 'status-tab'

    def compose(self) -> ComposeResult:
        with Center(), Middle():
            yield Static(
                'System Status\n\n[ Coming Soon ]', classes='status-placeholder'
            )
