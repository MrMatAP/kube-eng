"""
Shared harness for testing the Ansible modules under ``library/`` in isolation.

Ansible's runtime loader rewrites ``from ansible.module_utils.<name> import ...``
in a ``library/*.py`` module into an import of the sibling ``module_utils/<name>.py``
file. That rewrite only happens when Ansible actually executes the module (via
ansible-runner/ansible-playbook), so a plain ``import`` of a ``library`` module
fails outside of that machinery. We pre-register the real module_utils modules
under their ``ansible.module_utils.*`` names so a straight import works in
pytest too.
"""

import sys
import typing

import pytest
from _ansible_harness import AnsibleExitJson, AnsibleFailJson
from ansible.module_utils import basic
from kube_eng.ansible.project.module_utils import (
    dns_utils,
    idp_utils,
    pg_utils,
    registry_utils,
    s3_utils,
)

sys.modules.setdefault('ansible.module_utils.dns_utils', dns_utils)
sys.modules.setdefault('ansible.module_utils.idp_utils', idp_utils)
sys.modules.setdefault('ansible.module_utils.pg_utils', pg_utils)
sys.modules.setdefault('ansible.module_utils.registry_utils', registry_utils)
sys.modules.setdefault('ansible.module_utils.s3_utils', s3_utils)


@pytest.fixture(autouse=True)
def _patch_module_termination(
    monkeypatch: pytest.MonkeyPatch,
) -> typing.Generator[None]:
    """Make module.exit_json()/fail_json() raise instead of calling sys.exit()."""

    def exit_json(self, **kwargs):
        raise AnsibleExitJson(kwargs, module=self)

    def fail_json(self, **kwargs):
        raise AnsibleFailJson(kwargs, module=self)

    monkeypatch.setattr(basic.AnsibleModule, 'exit_json', exit_json)
    monkeypatch.setattr(basic.AnsibleModule, 'fail_json', fail_json)
    yield
