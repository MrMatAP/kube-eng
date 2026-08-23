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
