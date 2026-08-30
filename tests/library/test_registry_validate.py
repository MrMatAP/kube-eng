"""
Unit tests for the registry_validate Ansible module wrapper. RegistryAdmin is
mocked out entirely, so these tests only pin the relay between Ansible task
args and RegistryAdmin.validate() -- no live registry, no network.
"""

from unittest.mock import MagicMock

import pytest
from _ansible_harness import AnsibleExitJson, AnsibleFailJson, set_module_args
from kube_eng.ansible.project.library import registry_validate
from kube_eng.ansible.project.module_utils.registry_utils import RegistryException

BASE_ARGS = {
    'registry_endpoint': 'https://registry.kube-eng.test:5001',
    'registry_ca_path': '/tmp/ca.pem',
}


def test_validate_success_returns_validated_true(monkeypatch):
    set_module_args(BASE_ARGS)
    fake_admin = MagicMock()
    fake_admin.validate.return_value = MagicMock(
        ansible_result=lambda: {
            'changed': False,
            'msg': 'Connectivity is validated',
            'validated': True,
        }
    )
    monkeypatch.setattr(
        registry_validate, 'RegistryAdmin', MagicMock(return_value=fake_admin)
    )

    with pytest.raises(AnsibleExitJson) as exc_info:
        registry_validate.main()

    assert exc_info.value.kwargs['validated'] is True


def test_validate_defaults_credentials_to_none(monkeypatch):
    set_module_args(BASE_ARGS)
    fake_admin = MagicMock()
    fake_admin.validate.return_value = MagicMock(
        ansible_result=lambda: {
            'changed': False,
            'msg': 'Connectivity is validated',
            'validated': True,
        }
    )
    mock_registry_admin_cls = MagicMock(return_value=fake_admin)
    monkeypatch.setattr(registry_validate, 'RegistryAdmin', mock_registry_admin_cls)

    with pytest.raises(AnsibleExitJson):
        registry_validate.main()

    fake_admin.validate.assert_called_once_with(username=None, password=None)


def test_validate_relays_the_push_credentials(monkeypatch):
    """The push account exercises the same htpasswd credential
    helm_publish uses to push charts (ADR-0004)."""
    set_module_args({**BASE_ARGS, 'username': 'kube-eng', 'password': 's3cret'})
    fake_admin = MagicMock()
    fake_admin.validate.return_value = MagicMock(
        ansible_result=lambda: {
            'changed': False,
            'msg': 'Connectivity and authentication are validated',
            'validated': True,
        }
    )
    mock_registry_admin_cls = MagicMock(return_value=fake_admin)
    monkeypatch.setattr(registry_validate, 'RegistryAdmin', mock_registry_admin_cls)

    with pytest.raises(AnsibleExitJson):
        registry_validate.main()

    fake_admin.validate.assert_called_once_with(username='kube-eng', password='s3cret')


def test_validate_failure_still_returns_validated_false(monkeypatch):
    """Mirrors idp_validate/s3_validate: a failed validate() must still
    return 'validated' (False), in case this is ever retried with
    `until: <result>.validated` the way idp_validate is."""
    set_module_args(BASE_ARGS)
    fake_admin = MagicMock()
    fake_admin.validate.side_effect = RegistryException(
        code=400, msg='Missing connectivity to the registry'
    )
    monkeypatch.setattr(
        registry_validate, 'RegistryAdmin', MagicMock(return_value=fake_admin)
    )

    with pytest.raises(AnsibleFailJson) as exc_info:
        registry_validate.main()

    assert exc_info.value.kwargs['validated'] is False
    assert exc_info.value.kwargs['changed'] is False
    assert exc_info.value.kwargs['msg'] == 'Missing connectivity to the registry'
