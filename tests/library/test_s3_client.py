"""
Unit tests for the s3_client Ansible module wrapper. S3Admin is mocked out
entirely, so these tests only pin the relay between Ansible task args and
S3Admin calls -- no live S3, no network.
"""

from unittest.mock import MagicMock

import pytest
from _ansible_harness import AnsibleExitJson, AnsibleFailJson, set_module_args
from kube_eng.ansible.project.library import s3_client

BASE_ARGS = {
    's3_endpoint': 'https://s3.kube-eng.test:9001',
    's3_access_key': 'admin',
    's3_secret_key': 'admin-secret',
    's3_region': 'us-east-1',
    's3_ca_path': '/tmp/ca.pem',
    'access_key': 'loki-covenant',
}


def _fake_admin(*, ensure_result: dict, remove_result: dict) -> MagicMock:
    admin = MagicMock()
    admin.account_ensure.return_value = MagicMock(ansible_result=lambda: ensure_result)
    admin.account_remove.return_value = MagicMock(ansible_result=lambda: remove_result)
    return admin


def test_present_ensures_the_dedicated_account(monkeypatch):
    set_module_args(
        {
            **BASE_ARGS,
            'secret_key': 'loki-secret',
            'role': 'contributor',
            'state': 'present',
        }
    )
    fake_admin = _fake_admin(
        ensure_result={
            'changed': True,
            'msg': 'Account created',
            'access_key': 'loki-covenant',
            'role': 'contributor',
        },
        remove_result={},
    )
    monkeypatch.setattr(s3_client, 'S3Admin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleExitJson) as exc_info:
        s3_client.main()

    fake_admin.account_ensure.assert_called_once_with(
        access_key='loki-covenant', secret_key='loki-secret', role='contributor'
    )
    assert exc_info.value.kwargs == {
        'changed': True,
        'msg': 'Account created',
        'access_key': 'loki-covenant',
        'role': 'contributor',
    }


def test_present_requires_secret_key_and_role(monkeypatch):
    set_module_args({**BASE_ARGS, 'state': 'present'})
    monkeypatch.setattr(s3_client, 'S3Admin', MagicMock())

    with pytest.raises(AnsibleFailJson) as exc_info:
        s3_client.main()

    assert 'requires setting secret_key and role' in exc_info.value.kwargs['msg']


def test_present_rejects_an_unknown_role(monkeypatch):
    set_module_args(
        {
            **BASE_ARGS,
            'secret_key': 'loki-secret',
            'role': 'superuser',
            'state': 'present',
        }
    )
    monkeypatch.setattr(s3_client, 'S3Admin', MagicMock())

    with pytest.raises(AnsibleFailJson) as exc_info:
        s3_client.main()

    assert 'role must be one of' in exc_info.value.kwargs['msg']


@pytest.mark.parametrize('role', ['admin', 'contributor', 'viewer'])
def test_present_accepts_each_supported_role(monkeypatch, role):
    set_module_args(
        {**BASE_ARGS, 'secret_key': 'loki-secret', 'role': role, 'state': 'present'}
    )
    fake_admin = _fake_admin(
        ensure_result={
            'changed': True,
            'msg': 'Account created',
            'access_key': 'loki-covenant',
            'role': role,
        },
        remove_result={},
    )
    monkeypatch.setattr(s3_client, 'S3Admin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleExitJson):
        s3_client.main()

    fake_admin.account_ensure.assert_called_once_with(
        access_key='loki-covenant', secret_key='loki-secret', role=role
    )


def test_absent_removes_the_account(monkeypatch):
    set_module_args({**BASE_ARGS, 'state': 'absent'})
    fake_admin = _fake_admin(
        ensure_result={},
        remove_result={
            'changed': True,
            'msg': 'Account removed',
            'access_key': 'loki-covenant',
            'role': None,
        },
    )
    monkeypatch.setattr(s3_client, 'S3Admin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleExitJson) as exc_info:
        s3_client.main()

    fake_admin.account_remove.assert_called_once_with('loki-covenant')
    assert exc_info.value.kwargs['changed'] is True


def test_absent_does_not_require_secret_key_or_role(monkeypatch):
    """state=absent only needs the access_key -- no point demanding
    credentials/role just to tear something down."""
    set_module_args({**BASE_ARGS, 'state': 'absent'})
    fake_admin = _fake_admin(
        ensure_result={},
        remove_result={
            'changed': False,
            'msg': 'Account is absent',
            'access_key': 'loki-covenant',
            'role': None,
        },
    )
    monkeypatch.setattr(s3_client, 'S3Admin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleExitJson) as exc_info:
        s3_client.main()

    assert exc_info.value.kwargs['changed'] is False
