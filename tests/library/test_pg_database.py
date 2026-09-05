"""
Unit tests for the pg_database Ansible module wrapper. PGAdmin is mocked out
entirely, so these tests only pin the relay between Ansible task args and
PGAdmin.database_create()/database_remove() -- no live PostgreSQL, no
network.
"""

from unittest.mock import MagicMock

import pytest
from _ansible_harness import AnsibleExitJson, AnsibleFailJson, set_module_args
from kube_eng.ansible.project.library import pg_database

BASE_ARGS = {
    'admin_dsn': 'postgresql://postgres:secret@pg.kube-eng.test/postgres',
    'db_name': 'grafana',
    'db_user': 'grafana',
}

PRESENT_ARGS = {
    **BASE_ARGS,
    'db_password': 'grafana-secret',
    'state': 'present',
}


def test_create_relays_args_to_database_create(monkeypatch):
    set_module_args(PRESENT_ARGS)
    fake_admin = MagicMock()
    fake_admin.database_create.return_value = MagicMock(
        ansible_result=lambda: {
            'changed': True,
            'msg': 'Database created',
            'db_name': 'grafana',
            'db_user': 'grafana',
        }
    )
    mock_pg_admin_cls = MagicMock(return_value=fake_admin)
    monkeypatch.setattr(pg_database, 'PGAdmin', mock_pg_admin_cls)

    with pytest.raises(AnsibleExitJson) as exc_info:
        pg_database.main()

    assert exc_info.value.kwargs['changed'] is True
    assert exc_info.value.kwargs['db_name'] == 'grafana'
    mock_pg_admin_cls.assert_called_once_with(
        admin_dsn='postgresql://postgres:secret@pg.kube-eng.test/postgres'
    )
    fake_admin.database_create.assert_called_once_with(
        db_name='grafana', db_user='grafana', db_password='grafana-secret'
    )


def test_create_reports_unchanged_for_an_already_existing_database(monkeypatch):
    set_module_args(PRESENT_ARGS)
    fake_admin = MagicMock()
    fake_admin.database_create.return_value = MagicMock(
        ansible_result=lambda: {
            'changed': False,
            'msg': 'Database is present',
            'db_name': 'grafana',
            'db_user': 'grafana',
        }
    )
    monkeypatch.setattr(pg_database, 'PGAdmin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleExitJson) as exc_info:
        pg_database.main()

    assert exc_info.value.kwargs['changed'] is False
    assert exc_info.value.kwargs['msg'] == 'Database is present'


def test_state_present_defaults_to_present(monkeypatch):
    set_module_args(BASE_ARGS | {'db_password': 'grafana-secret'})
    fake_admin = MagicMock()
    fake_admin.database_create.return_value = MagicMock(
        ansible_result=lambda: {
            'changed': True,
            'msg': 'Database created',
            'db_name': 'grafana',
            'db_user': 'grafana',
        }
    )
    monkeypatch.setattr(pg_database, 'PGAdmin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleExitJson):
        pg_database.main()

    fake_admin.database_create.assert_called_once()


def test_create_requires_db_password(monkeypatch):
    set_module_args({**BASE_ARGS, 'state': 'present'})
    monkeypatch.setattr(pg_database, 'PGAdmin', MagicMock())

    with pytest.raises(AnsibleFailJson) as exc_info:
        pg_database.main()

    assert 'requires setting db_password' in exc_info.value.kwargs['msg']


def test_absent_removes_an_existing_database(monkeypatch):
    set_module_args({**BASE_ARGS, 'state': 'absent'})
    fake_admin = MagicMock()
    fake_admin.database_remove.return_value = MagicMock(
        ansible_result=lambda: {
            'changed': True,
            'msg': 'Database removed',
            'db_name': 'grafana',
            'db_user': 'grafana',
        }
    )
    monkeypatch.setattr(pg_database, 'PGAdmin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleExitJson) as exc_info:
        pg_database.main()

    fake_admin.database_remove.assert_called_once_with(
        db_name='grafana', db_user='grafana'
    )
    assert exc_info.value.kwargs['changed'] is True
    assert exc_info.value.kwargs['msg'] == 'Database removed'


def test_absent_reports_unchanged_when_already_absent(monkeypatch):
    set_module_args({**BASE_ARGS, 'state': 'absent'})
    fake_admin = MagicMock()
    fake_admin.database_remove.return_value = MagicMock(
        ansible_result=lambda: {
            'changed': False,
            'msg': 'Database is absent',
            'db_name': 'grafana',
            'db_user': 'grafana',
        }
    )
    monkeypatch.setattr(pg_database, 'PGAdmin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleExitJson) as exc_info:
        pg_database.main()

    assert exc_info.value.kwargs['changed'] is False
    assert exc_info.value.kwargs['msg'] == 'Database is absent'


def test_absent_does_not_require_db_password(monkeypatch):
    set_module_args({**BASE_ARGS, 'state': 'absent'})
    fake_admin = MagicMock()
    fake_admin.database_remove.return_value = MagicMock(
        ansible_result=lambda: {
            'changed': False,
            'msg': 'Database is absent',
            'db_name': 'grafana',
            'db_user': 'grafana',
        }
    )
    monkeypatch.setattr(pg_database, 'PGAdmin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleExitJson):
        pg_database.main()
