"""
Unit tests for the registry_htpasswd Ansible module wrapper. These pin the
relay between Ansible task args and RegistryHtpasswd.reconcile(), plus the
end-to-end file behaviour against a tmp path.
"""

import pathlib

import pytest
from _ansible_harness import AnsibleExitJson, AnsibleFailJson, set_module_args
from kube_eng.ansible.project.library import registry_htpasswd
from kube_eng.ansible.project.module_utils.registry_utils import verify_sha512_crypt


def test_writes_the_entry_and_reports_changed(tmp_path: pathlib.Path):
    path = tmp_path / 'htpasswd'
    set_module_args({'path': str(path), 'username': 'kube-eng', 'password': 's3cret'})

    with pytest.raises(AnsibleExitJson) as exc_info:
        registry_htpasswd.main()

    assert exc_info.value.kwargs['changed'] is True
    assert verify_sha512_crypt('s3cret', path.read_text().strip().partition(':')[2])


def test_second_run_is_idempotent(tmp_path: pathlib.Path):
    path = tmp_path / 'htpasswd'
    args = {'path': str(path), 'username': 'kube-eng', 'password': 's3cret'}

    set_module_args(args)
    with pytest.raises(AnsibleExitJson):
        registry_htpasswd.main()

    set_module_args(args)
    with pytest.raises(AnsibleExitJson) as exc_info:
        registry_htpasswd.main()

    assert exc_info.value.kwargs['changed'] is False


def test_empty_password_fails(tmp_path: pathlib.Path):
    set_module_args(
        {'path': str(tmp_path / 'htpasswd'), 'username': 'kube-eng', 'password': ''}
    )

    with pytest.raises(AnsibleFailJson) as exc_info:
        registry_htpasswd.main()

    assert 'empty password' in exc_info.value.kwargs['msg'].lower()
