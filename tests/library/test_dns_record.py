"""
Unit tests for the dns_record Ansible module wrapper. DNSAdmin is mocked out
entirely, so these tests only pin the relay between Ansible task args and
DNSAdmin.record_set() -- no live DNS, no network.
"""

from unittest.mock import MagicMock

import pytest
from _ansible_harness import AnsibleExitJson, AnsibleFailJson, set_module_args
from kube_eng.ansible.project.library import dns_record
from kube_eng.ansible.project.module_utils.dns_utils import DNSException

BASE_ARGS = {
    'dns_ip': '127.0.0.1',
    'dns_admin_key_name': 'update-key',
    'dns_admin_key_secret': 'secret',
    'dns_zone': 'k8s',
    'dns_record': 'grafana.testcluster.k8s.',
    'dns_value': '192.168.1.10',
    'dns_ttl': 1800,
}


def test_record_set_success_returns_changed(monkeypatch):
    set_module_args(BASE_ARGS)
    fake_admin = MagicMock()
    fake_admin.record_set.return_value = MagicMock(
        ansible_result=lambda: {'changed': True, 'msg': 'Record updated'}
    )
    monkeypatch.setattr(dns_record, 'DNSAdmin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleExitJson) as exc_info:
        dns_record.main()

    assert exc_info.value.kwargs['changed'] is True
    fake_admin.record_set.assert_called_once_with(
        dns_zone='k8s',
        dns_record='grafana.testcluster.k8s.',
        dns_value='192.168.1.10',
        dns_ttl=1800,
    )


def test_record_set_already_up_to_date_returns_unchanged(monkeypatch):
    set_module_args(BASE_ARGS)
    fake_admin = MagicMock()
    fake_admin.record_set.return_value = MagicMock(
        ansible_result=lambda: {'changed': False, 'msg': 'Record is up to date'}
    )
    monkeypatch.setattr(dns_record, 'DNSAdmin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleExitJson) as exc_info:
        dns_record.main()

    assert exc_info.value.kwargs['changed'] is False


def test_record_set_failure_calls_fail_json(monkeypatch):
    set_module_args(BASE_ARGS)
    fake_admin = MagicMock()
    fake_admin.record_set.side_effect = DNSException(
        code=400, msg='DNS update failed: REFUSED'
    )
    monkeypatch.setattr(dns_record, 'DNSAdmin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleFailJson) as exc_info:
        dns_record.main()

    assert exc_info.value.kwargs['msg'] == 'DNS update failed: REFUSED'


def test_default_protocol_is_tcp(monkeypatch):
    set_module_args(BASE_ARGS)
    fake_admin = MagicMock()
    fake_admin.record_set.return_value = MagicMock(
        ansible_result=lambda: {'changed': False, 'msg': 'ok'}
    )
    mock_dns_admin_cls = MagicMock(return_value=fake_admin)
    monkeypatch.setattr(dns_record, 'DNSAdmin', mock_dns_admin_cls)

    with pytest.raises(AnsibleExitJson):
        dns_record.main()

    assert mock_dns_admin_cls.call_args.kwargs['dns_protocol'] == 'tcp'
