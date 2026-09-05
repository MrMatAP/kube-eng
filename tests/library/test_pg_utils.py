"""
Unit tests for kube_eng.ansible.project.module_utils.pg_utils that don't
require a live PostgreSQL server. Only psycopg2.connect is mocked, so
PGAdmin's own logic (entitlement check, error wrapping) runs for real.
"""

from unittest.mock import MagicMock

import psycopg2
import pytest
from kube_eng.ansible.project.module_utils.pg_utils import PGAdmin, PGException


class _PGErrorWithPgerror(psycopg2.Error):
    """psycopg2.Error.pgerror is a read-only C attribute that can't be set
    on a plain instance; a subclass property can still shadow it."""

    def __init__(self, pgerror: str):
        super().__init__(pgerror)
        self._pgerror = pgerror

    @property
    def pgerror(self) -> str:
        return self._pgerror


def _mock_connect(monkeypatch, *, entitlements=None, connect_error=None):
    """Wire up psycopg2.connect(...) as PGAdmin.validate() uses it:
    `with psycopg2.connect(...) as conn, conn.cursor() as cur:`."""
    if connect_error is not None:
        monkeypatch.setattr(
            'kube_eng.ansible.project.module_utils.pg_utils.psycopg2.connect',
            MagicMock(side_effect=connect_error),
        )
        return None

    cursor = MagicMock()
    cursor.fetchone.return_value = entitlements
    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.cursor.return_value.__enter__.return_value = cursor
    monkeypatch.setattr(
        'kube_eng.ansible.project.module_utils.pg_utils.psycopg2.connect',
        MagicMock(return_value=conn),
    )
    return cursor


def test_validate_succeeds_when_entitlements_are_granted(monkeypatch):
    _mock_connect(monkeypatch, entitlements=(True, True))

    result = PGAdmin(admin_dsn='postgresql://x').validate()

    assert result.validated is True
    assert result.changed is False


def test_validate_fails_when_entitlements_are_partial(monkeypatch):
    _mock_connect(monkeypatch, entitlements=(True, False))

    with pytest.raises(PGException) as exc_info:
        PGAdmin(admin_dsn='postgresql://x').validate()

    assert 'Missing connectivity or entitlements' in exc_info.value.msg


def test_validate_fails_when_no_row_is_returned(monkeypatch):
    _mock_connect(monkeypatch, entitlements=None)

    with pytest.raises(PGException) as exc_info:
        PGAdmin(admin_dsn='postgresql://x').validate()

    assert 'Missing connectivity or entitlements' in exc_info.value.msg


def test_validate_wraps_connection_errors(monkeypatch):
    _mock_connect(
        monkeypatch, connect_error=psycopg2.OperationalError('connection refused')
    )

    with pytest.raises(PGException) as exc_info:
        PGAdmin(admin_dsn='postgresql://x').validate()

    assert exc_info.value.code == 400


def test_validate_uses_pgerror_when_available(monkeypatch):
    error = _PGErrorWithPgerror('permission denied for table pg_roles')
    _mock_connect(monkeypatch, connect_error=error)

    with pytest.raises(PGException) as exc_info:
        PGAdmin(admin_dsn='postgresql://x').validate()

    assert exc_info.value.msg == 'permission denied for table pg_roles'


def _mock_connect_sequence(monkeypatch, *, fetchone_side_effect):
    """Wire up psycopg2.connect(...) to always hand back the same conn/cursor
    mock, with 'fetchone' returning successive values across the several
    connections database_create()/database_remove() open (one per
    role_exists()/database_exists() check, plus one for the DDL itself)."""
    cursor = MagicMock()
    cursor.fetchone.side_effect = fetchone_side_effect
    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.cursor.return_value.__enter__.return_value = cursor
    monkeypatch.setattr(
        'kube_eng.ansible.project.module_utils.pg_utils.psycopg2.connect',
        MagicMock(return_value=conn),
    )
    return conn, cursor


def test_database_create_creates_role_and_database_when_both_are_absent(monkeypatch):
    conn, cursor = _mock_connect_sequence(
        monkeypatch, fetchone_side_effect=[None, None]
    )

    result = PGAdmin(admin_dsn='postgresql://x').database_create(
        db_name='grafana', db_user='grafana', db_password='secret'
    )

    assert result.changed is True
    assert result.msg == 'Database created'
    assert conn.autocommit is True
    # 2 existence checks (role, database) + 2 DDL statements (role, database)
    assert cursor.execute.call_count == 4


def test_database_create_is_unchanged_when_both_already_exist(monkeypatch):
    _, cursor = _mock_connect_sequence(monkeypatch, fetchone_side_effect=[(1,), (1,)])

    result = PGAdmin(admin_dsn='postgresql://x').database_create(
        db_name='grafana', db_user='grafana', db_password='secret'
    )

    assert result.changed is False
    assert result.msg == 'Database is present'
    # Only the 2 existence checks, no DDL.
    assert cursor.execute.call_count == 2


def test_database_create_only_creates_the_role_when_the_database_already_exists(
    monkeypatch,
):
    _, cursor = _mock_connect_sequence(monkeypatch, fetchone_side_effect=[None, (1,)])

    result = PGAdmin(admin_dsn='postgresql://x').database_create(
        db_name='grafana', db_user='grafana', db_password='secret'
    )

    assert result.changed is True
    # 2 existence checks + 1 DDL statement (role only).
    assert cursor.execute.call_count == 3


def test_database_create_never_rotates_an_existing_roles_password(monkeypatch):
    """Same rationale as idp_utils.client_create(): existing credentials are
    left alone."""
    _, cursor = _mock_connect_sequence(monkeypatch, fetchone_side_effect=[(1,), (1,)])

    PGAdmin(admin_dsn='postgresql://x').database_create(
        db_name='grafana', db_user='grafana', db_password='secret'
    )

    for call in cursor.execute.call_args_list:
        assert 'secret' not in call.args


def test_database_create_wraps_psycopg2_errors(monkeypatch):
    monkeypatch.setattr(
        'kube_eng.ansible.project.module_utils.pg_utils.psycopg2.connect',
        MagicMock(side_effect=psycopg2.OperationalError('connection refused')),
    )

    with pytest.raises(PGException) as exc_info:
        PGAdmin(admin_dsn='postgresql://x').database_create(
            db_name='grafana', db_user='grafana', db_password='secret'
        )

    assert exc_info.value.code == 400


def test_database_remove_removes_both_when_present(monkeypatch):
    _, cursor = _mock_connect_sequence(monkeypatch, fetchone_side_effect=[(1,), (1,)])

    result = PGAdmin(admin_dsn='postgresql://x').database_remove(
        db_name='grafana', db_user='grafana'
    )

    assert result.changed is True
    assert result.msg == 'Database removed'
    # 2 existence checks + 2 DDL statements (database, role).
    assert cursor.execute.call_count == 4


def test_database_remove_is_unchanged_when_already_absent(monkeypatch):
    _, cursor = _mock_connect_sequence(monkeypatch, fetchone_side_effect=[None, None])

    result = PGAdmin(admin_dsn='postgresql://x').database_remove(
        db_name='grafana', db_user='grafana'
    )

    assert result.changed is False
    assert result.msg == 'Database is absent'
    assert cursor.execute.call_count == 2
