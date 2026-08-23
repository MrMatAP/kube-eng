"""
Unit tests for the s3_validate Ansible module wrapper. S3Admin is mocked
out entirely, so these tests only pin the relay between Ansible task args
and S3Admin.validate() -- no live S3, no network.
"""

from unittest.mock import MagicMock

import pytest
from _ansible_harness import AnsibleExitJson, AnsibleFailJson, set_module_args
from kube_eng.ansible.project.library import s3_validate
from kube_eng.ansible.project.module_utils.s3_utils import S3Exception

BASE_ARGS = {
    's3_endpoint': 'https://s3.kube-eng.test:9000',
    's3_access_key': 'admin',
    's3_secret_key': 'secret',
    's3_region': 'us-east-1',
    's3_ca_path': '/tmp/ca.pem',
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
    monkeypatch.setattr(s3_validate, 'S3Admin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleExitJson) as exc_info:
        s3_validate.main()

    assert exc_info.value.kwargs['validated'] is True


def test_validate_failure_still_returns_validated_false(monkeypatch):
    """Mirrors idp_validate: a failed validate() must still return
    'validated' (False), in case this is ever retried with
    `until: <result>.validated` the way idp_validate is."""
    set_module_args(BASE_ARGS)
    fake_admin = MagicMock()
    fake_admin.validate.side_effect = S3Exception(
        code=400, msg='Missing connectivity or entitlements'
    )
    monkeypatch.setattr(s3_validate, 'S3Admin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleFailJson) as exc_info:
        s3_validate.main()

    assert exc_info.value.kwargs['validated'] is False
    assert exc_info.value.kwargs['changed'] is False
    assert exc_info.value.kwargs['msg'] == 'Missing connectivity or entitlements'
