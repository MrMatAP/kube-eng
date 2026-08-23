"""
Unit tests for the dns_validate Ansible module wrapper. DNSAdmin is mocked
out entirely, so these tests only pin the relay between Ansible task args
and DNSAdmin.validate() -- no live DNS, no network.
"""

from unittest.mock import MagicMock

import pytest
from _ansible_harness import AnsibleExitJson, AnsibleFailJson, set_module_args
from kube_eng.ansible.project.library import dns_validate
from kube_eng.ansible.project.module_utils.dns_utils import DNSException

BASE_ARGS = {
    'dns_ip': '127.0.0.1',
    'dns_admin_key_name': 'update-key',
    'dns_admin_key_secret': 'secret',
    'dns_zone': 'k8s',
    'dns_domain': 'testcluster.k8s',
}


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
    monkeypatch.setattr(dns_validate, 'DNSAdmin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleExitJson) as exc_info:
        dns_validate.main()

    assert exc_info.value.kwargs['validated'] is True
    fake_admin.validate.assert_called_once_with(
        dns_zone='k8s', dns_domain='testcluster.k8s'
    )


def test_validate_failure_still_returns_validated_false(monkeypatch):
    """Mirrors idp_validate: a failed validate() must still return
    'validated' (False), in case this is ever retried with
    `until: <result>.validated` the way idp_validate is."""
    set_module_args(BASE_ARGS)
    fake_admin = MagicMock()
    fake_admin.validate.side_effect = DNSException(
        code=400, msg='DNS server is not authoritative for k8s'
    )
    monkeypatch.setattr(dns_validate, 'DNSAdmin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleFailJson) as exc_info:
        dns_validate.main()

    assert exc_info.value.kwargs['validated'] is False
    assert exc_info.value.kwargs['changed'] is False
    assert exc_info.value.kwargs['msg'] == 'DNS server is not authoritative for k8s'


def test_default_protocol_is_tcp(monkeypatch):
    set_module_args(BASE_ARGS)
    fake_admin = MagicMock()
    fake_admin.validate.return_value = MagicMock(
        ansible_result=lambda: {'changed': False, 'msg': 'ok', 'validated': True}
    )
    mock_dns_admin_cls = MagicMock(return_value=fake_admin)
    monkeypatch.setattr(dns_validate, 'DNSAdmin', mock_dns_admin_cls)

    with pytest.raises(AnsibleExitJson):
        dns_validate.main()

    assert mock_dns_admin_cls.call_args.kwargs['dns_protocol'] == 'tcp'
