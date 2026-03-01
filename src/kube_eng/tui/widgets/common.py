"""
Common TUI widgets for headers, body, and logging.
"""

from typing_extensions import Literal

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.events import Resize
from textual.widgets import Label, DataTable
from textual.widgets._data_table import CursorType

from kube_eng import __version__
from kube_eng.common import AnsibleEvent


class AppHeader(Horizontal):
    """
    Application header widget with branding
    """

    def compose(self) -> ComposeResult:
        yield Label('kube-eng', id='app-title-left')
        yield Label(__version__, id='app-title-right')


class AppBody(Vertical):
    """
    Main application body container
    """
    pass


class TUILog(DataTable):
    """
    Log table widget for displaying Ansible execution events
    """

    def __init__(self, *, show_header: bool = True, show_row_labels: bool = True,
                 fixed_rows: int = 0, fixed_columns: int = 0, zebra_stripes: bool = False,
                 header_height: int = 1, show_cursor: bool = True,
                 cursor_foreground_priority: Literal["renderable", "css"] = "css",
                 cursor_background_priority: Literal["renderable", "css"] = "renderable",
                 cursor_type: CursorType = "cell", cell_padding: int = 1, name: str | None = None,
                 id: str | None = None, classes: str | None = None, disabled: bool = False) -> None:
        super().__init__(show_header=show_header, show_row_labels=show_row_labels,
                         fixed_rows=fixed_rows, fixed_columns=fixed_columns,
                         zebra_stripes=zebra_stripes, header_height=header_height,
                         show_cursor=show_cursor,
                         cursor_foreground_priority=cursor_foreground_priority,
                         cursor_background_priority=cursor_background_priority,
                         cursor_type=cursor_type, cell_padding=cell_padding, name=name, id=id,
                         classes=classes, disabled=disabled)
        self._ansible_events: dict[str, AnsibleEvent] = {}

    def on_mount(self):
        super().on_mount()
        self.show_header = True
        self.show_row_labels = False
        self.zebra_stripes = True
        self.cursor_type = 'row'
        self.add_column(label='Log', key='log', width=10)
        self.add_column(label='', key='status', width=2)

    @on(Resize)
    def resize(self, event: Resize):
        log_column = list(self.columns.values())[0]
        log_column.auto_width = False
        log_column.width = event.size.width - 6 - 6
        self.refresh()

    async def add_event(self, event: AnsibleEvent):
        if event.uuid in self._ansible_events:
            self.update_cell(event.uuid,
                             'status',
                             Text(event.status, justify='right'))
        else:
            self.add_row(Text(event.task, overflow='ellipsis'),
                         Text(event.status, justify='right'),
                         height=None,
                         key=event.uuid,
                         label=event.uuid)
        self._ansible_events[event.uuid] = event

    def add_log(self, msg: str, status: str = ''):
        self.add_row(Text(msg, overflow='ellipsis'),
                     Text(status),
                     height=None)
