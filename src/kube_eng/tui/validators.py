"""
Input validators for TUI forms.
"""

import pathlib

from textual.validation import Validator, ValidationResult
from textual.widgets import Input


class ExecutablePathValidator(Validator):
    """
    Validates that a path exists and points to an executable file.
    """

    def validate(self, value: str) -> ValidationResult:
        if not value:
            return self.failure('Path cannot be empty')
        path = pathlib.Path(value)
        if not path.exists():
            return self.failure(f'{value} does not exist')
        if not path.is_file():
            return self.failure(f'{value} is not a file')
        return self.success()


class ExecutablePathInput(Input):
    """
    Input widget with built-in executable path validation.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.validate_on = {'changed', 'submitted'}
        self.validators = [ExecutablePathValidator()]


class PortValidator(Validator):
    """
    Validates that a value is a valid network port number (1-65535).
    """

    def validate(self, value: str) -> ValidationResult:
        try:
            port = int(value)
            if port < 1 or port > 65535:
                return self.failure('Port must be between 1 and 65535')
            return self.success()
        except ValueError:
            return self.failure('Port must be a number')
