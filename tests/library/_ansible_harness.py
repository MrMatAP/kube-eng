"""
Shared harness for unit-testing Ansible modules under library/ in isolation,
without ansible-runner or a live target. Not a conftest.py on purpose: pytest
auto-loads conftest.py rather than treating it as an importable module, so
test files that need these helpers import them from here instead.
"""

import json

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes


def set_module_args(args: dict) -> None:
    """Simulate the Ansible task args a module would receive on module.params."""
    serialized = json.dumps({'ANSIBLE_MODULE_ARGS': args})
    basic._ANSIBLE_ARGS = to_bytes(serialized)
    # Standalone (non-collection) modules like ours run under the 'legacy'
    # serialization profile; ansible-core needs this set explicitly since we
    # bypass the normal AnsiballZ wrapper that would otherwise set it.
    basic._ANSIBLE_PROFILE = 'legacy'


class AnsibleExitJson(Exception):
    """Raised in place of AnsibleModule.exit_json(), carrying its kwargs and
    the module instance itself (e.g. to inspect module.no_log_values)."""

    def __init__(self, kwargs: dict, module: basic.AnsibleModule | None = None):
        super().__init__(kwargs)
        self.kwargs = kwargs
        self.module = module


class AnsibleFailJson(Exception):
    """Raised in place of AnsibleModule.fail_json(), carrying its kwargs and
    the module instance itself."""

    def __init__(self, kwargs: dict, module: basic.AnsibleModule | None = None):
        super().__init__(kwargs)
        self.kwargs = kwargs
        self.module = module
