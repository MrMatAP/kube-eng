"""
Unit tests for the pg_validate Ansible module wrapper. PGAdmin is mocked out
entirely, so these tests only pin the relay between Ansible task args and
PGAdmin.validate() -- no live PostgreSQL, no network.
"""

from unittest.mock import MagicMock

import pytest
from _ansible_harness import AnsibleExitJson, AnsibleFailJson, set_module_args
from kube_eng.ansible.project.library import pg_validate
from kube_eng.ansible.project.module_utils.pg_utils import PGException

BASE_ARGS = {'admin_dsn': 'postgresql://postgres:secret@pg.kube-eng.test:5432/postgres'}


def test_validate_success_returns_validated_true(monkeypatch):
    set_module_args(BASE_ARGS)
    fake_admin = MagicMock()
    fake_admin.validate.return_value = MagicMock(
        ansible_result=lambda: {
            'changed': False,
            'msg': 'Connectivity and entitlements are granted',
            'validated': True,
        }
    )
    monkeypatch.setattr(pg_validate, 'PGAdmin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleExitJson) as exc_info:
        pg_validate.main()

    assert exc_info.value.kwargs['validated'] is True


def test_validate_failure_still_returns_validated_false(monkeypatch):
    """Mirrors idp_validate: a failed validate() must still return
    'validated' (False), in case this is ever retried with
    `until: <result>.validated` the way idp_validate is."""
    set_module_args(BASE_ARGS)
    fake_admin = MagicMock()
    fake_admin.validate.side_effect = PGException(
        code=400, msg='Missing connectivity or entitlements'
    )
    monkeypatch.setattr(pg_validate, 'PGAdmin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleFailJson) as exc_info:
        pg_validate.main()

    assert exc_info.value.kwargs['validated'] is False
    assert exc_info.value.kwargs['changed'] is False
    assert exc_info.value.kwargs['msg'] == 'Missing connectivity or entitlements'
