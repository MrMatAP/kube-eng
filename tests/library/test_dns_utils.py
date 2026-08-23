"""
Unit tests for kube_eng.ansible.project.module_utils.dns_utils that don't
require a live DNS server. Only the dnspython query call is mocked, so
DNSAdmin's own logic (SOA/update/verify sequencing, error wrapping) runs for
real.
"""

from unittest.mock import MagicMock

import dns.exception
import dns.flags
import dns.rcode
import pytest
from kube_eng.ansible.project.module_utils.dns_utils import DNSAdmin, DNSException

_KEY_SECRET = 'c2VjcmV0MTIzNA=='  # valid base64, arbitrary TSIG key material
_FIXED_TIMESTAMP = '2026-01-01T00:00:00+00:00'


class _FakeRdata:
    def __init__(self, text: str):
        self.strings = [text.encode()]


class _FakeResponse:
    def __init__(self, *, flags: int = 0, rcode: int | None = None, answer=None):
        self.flags = flags
        self._rcode = rcode
        self.answer = answer or []

    def rcode(self):
        return self._rcode


def _admin() -> DNSAdmin:
    admin = DNSAdmin.__new__(DNSAdmin)  # bypass __init__, no query-fn selection
    admin._dns_ip = '127.0.0.1'
    admin._admin_key_name = 'update-key'
    admin._admin_key_secret = _KEY_SECRET
    admin._query = MagicMock()
    return admin


@pytest.fixture(autouse=True)
def _fixed_timestamp(monkeypatch):
    """Freeze the timestamp validate() writes, so the fake TXT readback in
    the success test can match it without inspecting dnspython internals."""
    fake_now = MagicMock()
    fake_now.isoformat.return_value = _FIXED_TIMESTAMP
    fake_datetime_cls = MagicMock()
    fake_datetime_cls.now.return_value = fake_now
    monkeypatch.setattr(
        'kube_eng.ansible.project.module_utils.dns_utils.datetime.datetime',
        fake_datetime_cls,
    )


def test_validate_success_writes_and_verifies_a_txt_record():
    admin = _admin()
    admin._query.side_effect = [
        _FakeResponse(flags=dns.flags.AA),  # SOA: authoritative
        _FakeResponse(rcode=dns.rcode.NOERROR),  # update: accepted
        _FakeResponse(answer=[[_FakeRdata(_FIXED_TIMESTAMP)]]),  # readback matches
    ]

    result = admin.validate(dns_zone='k8s', dns_domain='testcluster.k8s')

    assert result.validated is True
    assert result.changed is False
    assert admin._query.call_count == 3


def test_validate_fails_when_server_is_not_authoritative():
    admin = _admin()
    admin._query.return_value = _FakeResponse(flags=0)

    with pytest.raises(DNSException) as exc_info:
        admin.validate(dns_zone='k8s', dns_domain='testcluster.k8s')

    assert 'not authoritative' in exc_info.value.msg
    admin._query.assert_called_once()


def test_validate_fails_when_the_update_is_rejected():
    admin = _admin()
    admin._query.side_effect = [
        _FakeResponse(flags=dns.flags.AA),
        _FakeResponse(rcode=dns.rcode.REFUSED),
    ]

    with pytest.raises(DNSException) as exc_info:
        admin.validate(dns_zone='k8s', dns_domain='testcluster.k8s')

    assert 'DNS update failed' in exc_info.value.msg


def test_validate_fails_when_the_readback_does_not_match():
    admin = _admin()
    admin._query.side_effect = [
        _FakeResponse(flags=dns.flags.AA),
        _FakeResponse(rcode=dns.rcode.NOERROR),
        _FakeResponse(answer=[[_FakeRdata('something-else')]]),
    ]

    with pytest.raises(DNSException) as exc_info:
        admin.validate(dns_zone='k8s', dns_domain='testcluster.k8s')

    assert 'could not be verified' in exc_info.value.msg


def test_validate_wraps_dnspython_exceptions():
    admin = _admin()
    admin._query.side_effect = dns.exception.Timeout()

    with pytest.raises(DNSException) as exc_info:
        admin.validate(dns_zone='k8s', dns_domain='testcluster.k8s')

    assert exc_info.value.code == 400
