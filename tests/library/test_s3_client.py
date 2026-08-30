"""
Unit tests for the s3_client Ansible module wrapper. S3Admin is mocked out
entirely, so these tests only pin the relay between Ansible task args and
S3Admin calls -- no live S3, no network.
"""

from types import SimpleNamespace
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
    'access_key': 'svc-loki',
}

_DOC = {
    'Version': '2012-10-17',
    'Statement': [
        {
            'Effect': 'Allow',
            'Action': ['s3:GetObject', 's3:PutObject'],
            'Resource': ['arn:aws:s3:::loki-*/*'],
        }
    ],
}


def _fake_admin() -> MagicMock:
    admin = MagicMock()
    admin.policy_ensure.return_value = SimpleNamespace(
        changed=True, msg='Policy created', policy_name='svc-loki'
    )
    admin.account_ensure.return_value = SimpleNamespace(
        changed=True,
        msg='Account created',
        access_key='svc-loki',
        policies=['svc-loki'],
    )
    admin.account_remove.return_value = SimpleNamespace(
        changed=True, msg='Account removed', access_key='svc-loki', policies=[]
    )
    admin.policy_remove.return_value = SimpleNamespace(
        changed=True, msg='Policy removed', policy_name='svc-loki'
    )
    return admin


def _patch(monkeypatch, admin):
    monkeypatch.setattr(s3_client, 'S3Admin', MagicMock(return_value=admin))


def test_present_authors_the_policy_and_the_account(monkeypatch):
    set_module_args(
        {**BASE_ARGS, 'secret_key': 'loki-secret', 'policy': _DOC, 'state': 'present'}
    )
    admin = _fake_admin()
    _patch(monkeypatch, admin)

    with pytest.raises(AnsibleExitJson) as exc_info:
        s3_client.main()

    admin.policy_ensure.assert_called_once_with('svc-loki', _DOC)
    admin.account_ensure.assert_called_once_with(
        'svc-loki', 'loki-secret', ['svc-loki']
    )
    assert exc_info.value.kwargs['changed'] is True
    assert exc_info.value.kwargs['policies'] == ['svc-loki']


def test_present_with_extra_pre_existing_policies(monkeypatch):
    set_module_args(
        {
            **BASE_ARGS,
            'secret_key': 'loki-secret',
            'policy': _DOC,
            'policies': ['readonly'],
            'state': 'present',
        }
    )
    admin = _fake_admin()
    _patch(monkeypatch, admin)

    with pytest.raises(AnsibleExitJson):
        s3_client.main()

    admin.account_ensure.assert_called_once_with(
        'svc-loki', 'loki-secret', ['svc-loki', 'readonly']
    )


def test_present_policy_only_does_not_touch_an_account(monkeypatch):
    set_module_args(
        {**BASE_ARGS, 'access_key': 's3-admin', 'policy': _DOC, 'state': 'present'}
    )
    admin = _fake_admin()
    admin.policy_ensure.return_value = SimpleNamespace(
        changed=True, msg='Policy created', policy_name='s3-admin'
    )
    _patch(monkeypatch, admin)

    with pytest.raises(AnsibleExitJson) as exc_info:
        s3_client.main()

    admin.policy_ensure.assert_called_once_with('s3-admin', _DOC)
    admin.account_ensure.assert_not_called()
    assert 'policies' not in exc_info.value.kwargs


def test_present_account_only_attaches_named_policies(monkeypatch):
    set_module_args(
        {
            **BASE_ARGS,
            'secret_key': 'loki-secret',
            'policies': ['readonly'],
            'state': 'present',
        }
    )
    admin = _fake_admin()
    _patch(monkeypatch, admin)

    with pytest.raises(AnsibleExitJson):
        s3_client.main()

    admin.policy_ensure.assert_not_called()
    admin.account_ensure.assert_called_once_with(
        'svc-loki', 'loki-secret', ['readonly']
    )


def test_present_requires_a_secret_key_or_a_policy(monkeypatch):
    set_module_args({**BASE_ARGS, 'state': 'present'})
    _patch(monkeypatch, _fake_admin())

    with pytest.raises(AnsibleFailJson) as exc_info:
        s3_client.main()

    assert 'secret_key' in exc_info.value.kwargs['msg']


def test_absent_removes_the_account_and_its_policy(monkeypatch):
    set_module_args({**BASE_ARGS, 'policy': _DOC, 'state': 'absent'})
    admin = _fake_admin()
    _patch(monkeypatch, admin)

    with pytest.raises(AnsibleExitJson) as exc_info:
        s3_client.main()

    admin.account_remove.assert_called_once_with('svc-loki')
    admin.policy_remove.assert_called_once_with('svc-loki')
    assert exc_info.value.kwargs['changed'] is True


def test_absent_without_policy_removes_only_the_account(monkeypatch):
    set_module_args({**BASE_ARGS, 'state': 'absent'})
    admin = _fake_admin()
    _patch(monkeypatch, admin)

    with pytest.raises(AnsibleExitJson) as exc_info:
        s3_client.main()

    admin.account_remove.assert_called_once_with('svc-loki')
    admin.policy_remove.assert_not_called()
    assert exc_info.value.kwargs['changed'] is True


def test_absent_is_a_no_op_when_nothing_exists(monkeypatch):
    set_module_args({**BASE_ARGS, 'policy': _DOC, 'state': 'absent'})
    admin = _fake_admin()
    admin.account_remove.return_value = SimpleNamespace(
        changed=False, msg='Account is absent', access_key='svc-loki', policies=[]
    )
    admin.policy_remove.return_value = SimpleNamespace(
        changed=False, msg='Policy is absent', policy_name='svc-loki'
    )
    _patch(monkeypatch, admin)

    with pytest.raises(AnsibleExitJson) as exc_info:
        s3_client.main()

    assert exc_info.value.kwargs['changed'] is False
