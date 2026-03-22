"""
Modal dialog for selecting and triggering Ansible actions.
"""

from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Button, Static, OptionList
from textual.widgets.option_list import Option


class ActionsModal(ModalScreen[str]):
    """
    Modal dialog that displays a list of available actions.
    """

    DEFAULT_CSS = """
    $primary: #a78bfa;

    ActionsModal {
        align: center middle;
    }

    #actions-container {
        width: 40;
        height: auto;
        max-height: 20;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }

    #actions-title {
        dock: top;
        height: 3;
        content-align: center middle;
        text-style: bold;
        background: $primary;
        color: white;
        margin-bottom: 1;
    }

    #actions-list {
        height: auto;
        border: none;
    }

    #actions-cancel {
        margin-top: 1;
        width: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id='actions-container'):
            yield Static("Available Actions", id='actions-title')
            yield OptionList(
                Option("Host Apply", id="host-apply"),
                Option("Cluster Apply", id="cluster-apply"),
                Option("Cluster Destroy", id="cluster-destroy"),
                Option("Stack Apply", id="stack-apply"),
                id="actions-list"
            )
            yield Button("Cancel", id="actions-cancel", variant="error")

    @on(OptionList.OptionSelected, "#actions-list")
    def on_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle action selection"""
        if event.option_id:
            self.dismiss(event.option_id)

    @on(Button.Pressed, "#actions-cancel")
    def on_cancel_pressed(self) -> None:
        """Handle cancel button press"""
        self.dismiss()

    def on_mount(self) -> None:
        self.query_one("#actions-list").focus()

    def action_close(self) -> None:
        self.dismiss()
