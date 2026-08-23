"""
Unit tests for the idp_validate Ansible module wrapper. IdPAdmin is mocked
out entirely, so these tests only pin the relay between Ansible task args
and IdPAdmin.validate() -- no live IdP, no network.
"""

from unittest.mock import MagicMock

import pytest
from _ansible_harness import AnsibleExitJson, AnsibleFailJson, set_module_args
from kube_eng.ansible.project.library import idp_validate
from kube_eng.ansible.project.module_utils.idp_utils import IdPException

BASE_ARGS = {
    'idp_url': 'https://idp.kube-eng.test:8443',
    'idp_admin_user': 'admin',
    'idp_admin_password': 'secret',
    'idp_realm': 'master',
    'idp_ca_path': '/tmp/ca.pem',
}


def test_validate_success_returns_validated_true(monkeypatch):
    set_module_args(BASE_ARGS)
    fake_admin = MagicMock()
    fake_admin.validate.return_value = MagicMock(
        ansible_result=lambda: {
            'changed': False,
            'msg': 'Connectivity and entitlements are validated',
            'validated': True,
        }
    )
    monkeypatch.setattr(idp_validate, 'IdPAdmin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleExitJson) as exc_info:
        idp_validate.main()

    assert exc_info.value.kwargs['validated'] is True
    fake_admin.validate.assert_called_once_with('admin')


def test_validate_failure_still_returns_validated_false(monkeypatch):
    """The IdP container (Keycloak) commonly reports healthy before its
    admin API is actually queryable, so this is the expected shape of the
    very first attempt right after the container comes up. The playbook
    retries this task with `until: idp_validation.validated`, which needs
    that key present on every attempt -- not just successful ones."""
    set_module_args(BASE_ARGS)
    fake_admin = MagicMock()
    fake_admin.validate.side_effect = IdPException(
        code=400, msg='Unable to connect to IdP'
    )
    monkeypatch.setattr(idp_validate, 'IdPAdmin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleFailJson) as exc_info:
        idp_validate.main()

    assert exc_info.value.kwargs['validated'] is False
    assert exc_info.value.kwargs['changed'] is False
    assert exc_info.value.kwargs['msg'] == 'Unable to connect to IdP'
