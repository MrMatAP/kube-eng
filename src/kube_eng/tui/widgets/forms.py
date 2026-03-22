"""
Form-related widgets for building configuration forms.
"""

from enum import Enum

from textual.containers import VerticalGroup, HorizontalGroup
from textual.widgets import Select


class FormGroup(VerticalGroup):
    """
    Container for grouping related form fields with a border and title.
    """

    def __init__(self, title: str, *args, **kwargs) -> None:
        super().__init__(*args)
        self.classes = 'form-group'
        self.border_title = title


class FormLine(HorizontalGroup):
    """
    Horizontal container for a single form field with its label.
    """
    DEFAULT_CLASSES = 'form-line'


class FormActions(HorizontalGroup):
    """
    Container for form action buttons (e.g., Submit, Cancel).
    """
    DEFAULT_CLASSES = 'form-actions'


class EnumSelect(Select):
    """
    A Select widget specialized for Enum types.
    Automatically generates options from enum values.
    """

    def __init__(self, enum_class: type[Enum], initial_value=None, **kwargs):
        options = [(str(e.value), e.value) for e in enum_class]
        super().__init__(options=options, **kwargs)
        if initial_value:
            self.value = initial_value
