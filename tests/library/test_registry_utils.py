"""
Unit tests for kube_eng.ansible.project.module_utils.registry_utils. The
transport (requests.get) is mocked, so these run without a live registry.
"""

import pathlib
import shutil
import subprocess
from unittest.mock import MagicMock

import pytest
from kube_eng.ansible.project.module_utils.registry_utils import (
    RegistryAdmin,
    RegistryException,
    RegistryHtpasswd,
    random_salt,
    sha512_crypt,
    verify_sha512_crypt,
)


def _admin() -> RegistryAdmin:
    return RegistryAdmin(
        registry_endpoint='https://registry.kube-eng.test:5001/',
        registry_ca_path='/tmp/ca.pem',
    )


class _FakeResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code
        self.ok = status_code < 400


def test_validate_strips_the_trailing_slash_and_calls_the_v2_endpoint(monkeypatch):
    captured = {}

    def fake_get(url, auth=None, verify=None, timeout=None):
        captured.update(url=url, auth=auth, verify=verify, timeout=timeout)
        return _FakeResponse(status_code=200)

    monkeypatch.setattr(
        'kube_eng.ansible.project.module_utils.registry_utils.requests.get', fake_get
    )

    result = _admin().validate()

    assert result.validated is True
    assert result.msg == 'Connectivity is validated'
    assert captured['url'] == 'https://registry.kube-eng.test:5001/v2/'
    assert captured['verify'] == '/tmp/ca.pem'
    assert captured['auth'] is None


def test_validate_discards_a_path_on_the_endpoint(monkeypatch):
    """RemoteRegistryConfig.http_endpoint can carry a path (e.g.
    https://harbor.example.com/kube-eng) -- the distribution spec's base
    endpoint lives at the registry root, not under that path."""
    captured = {}

    def fake_get(url, auth=None, verify=None, timeout=None):
        captured.update(url=url)
        return _FakeResponse(status_code=200)

    monkeypatch.setattr(
        'kube_eng.ansible.project.module_utils.registry_utils.requests.get', fake_get
    )

    admin = RegistryAdmin(
        registry_endpoint='https://harbor.example.com/kube-eng',
        registry_ca_path='/tmp/ca.pem',
    )
    admin.validate()

    assert captured['url'] == 'https://harbor.example.com/v2/'


def test_validate_raises_when_the_registry_is_unreachable(monkeypatch):
    import requests

    monkeypatch.setattr(
        'kube_eng.ansible.project.module_utils.registry_utils.requests.get',
        MagicMock(side_effect=requests.ConnectionError('boom')),
    )

    with pytest.raises(RegistryException) as exc_info:
        _admin().validate()

    assert exc_info.value.code == 400


def test_validate_raises_on_a_non_ok_response(monkeypatch):
    monkeypatch.setattr(
        'kube_eng.ansible.project.module_utils.registry_utils.requests.get',
        lambda *a, **kw: _FakeResponse(status_code=503),
    )

    with pytest.raises(RegistryException) as exc_info:
        _admin().validate()

    assert exc_info.value.code == 503


def test_validate_sends_the_push_credentials_as_basic_auth(monkeypatch):
    """The push account exercises the same htpasswd credential
    helm_publish uses to push charts (ADR-0004), not just plain
    connectivity."""
    captured = {}

    def fake_get(url, auth=None, verify=None, timeout=None):
        captured.update(auth=auth)
        return _FakeResponse(status_code=200)

    monkeypatch.setattr(
        'kube_eng.ansible.project.module_utils.registry_utils.requests.get', fake_get
    )

    result = _admin().validate(username='kube-eng', password='s3cret')

    assert result.validated is True
    assert result.msg == 'Connectivity and authentication are validated'
    assert captured['auth'] == ('kube-eng', 's3cret')


def test_validate_raises_a_specific_error_when_the_credentials_are_rejected(
    monkeypatch,
):
    """A 401/403 with credentials presented means the credential itself is
    bad -- distinct from a registry that's merely unreachable or
    misconfigured, which the generic 'Missing connectivity' message from
    an unauthenticated check still covers."""
    monkeypatch.setattr(
        'kube_eng.ansible.project.module_utils.registry_utils.requests.get',
        lambda *a, **kw: _FakeResponse(status_code=401),
    )

    with pytest.raises(RegistryException) as exc_info:
        _admin().validate(username='kube-eng', password='wrong')

    assert exc_info.value.code == 401
    assert exc_info.value.msg == 'Registry rejected the push account credentials'


def test_validate_without_credentials_does_not_send_an_auth_tuple(monkeypatch):
    captured = {}

    def fake_get(url, auth=None, verify=None, timeout=None):
        captured.update(auth=auth)
        return _FakeResponse(status_code=200)

    monkeypatch.setattr(
        'kube_eng.ansible.project.module_utils.registry_utils.requests.get', fake_get
    )

    _admin().validate(username='kube-eng', password='')

    assert captured['auth'] is None


# --- htpasswd -----------------------------------------------------------

_openssl = shutil.which('openssl')
requires_openssl = pytest.mark.skipif(_openssl is None, reason='openssl not on PATH')


def _openssl_sha512(password: str, salt: str) -> str:
    return subprocess.run(
        [_openssl, 'passwd', '-6', '-salt', salt, '-stdin'],
        input=password,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


@requires_openssl
@pytest.mark.parametrize(
    ('password', 'salt'),
    [
        ('secret123', 'Xy9kLm2p'),
        ('a-generated-token_urlsafe-ish', 'abcdEFGH12345678'),
        ('x', 'a'),
        ('p@ss w/$pecial \t chars', 'SALTsalt'),
    ],
)
def test_sha512_crypt_matches_openssl(password: str, salt: str):
    assert sha512_crypt(password, salt) == _openssl_sha512(password, salt)


def test_sha512_crypt_rejects_an_empty_password():
    with pytest.raises(RegistryException):
        sha512_crypt('', 'somesalt')


def test_verify_sha512_crypt_round_trips():
    encoded = sha512_crypt('hunter2', random_salt())
    assert verify_sha512_crypt('hunter2', encoded)
    assert not verify_sha512_crypt('hunter3', encoded)
    assert not verify_sha512_crypt('hunter2', '')
    assert not verify_sha512_crypt('hunter2', '$2y$05$notsha512')


def test_random_salt_stays_within_the_crypt_alphabet():
    salt = random_salt()
    assert len(salt) == 16
    assert set(salt) <= set(
        './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    )


def test_htpasswd_reconcile_writes_then_is_idempotent(tmp_path: pathlib.Path):
    path = tmp_path / 'htpasswd'
    store = RegistryHtpasswd(str(path))

    first = store.reconcile('kube-eng', 's3cret')
    assert first.changed is True
    user, _, hashed = path.read_text().strip().partition(':')
    assert user == 'kube-eng'
    assert hashed.startswith('$6$')
    assert path.stat().st_mode & 0o777 == 0o600

    second = store.reconcile('kube-eng', 's3cret')
    assert second.changed is False
    assert path.read_text().partition(':')[2] == hashed + '\n'


def test_htpasswd_reconcile_rewrites_on_password_change(tmp_path: pathlib.Path):
    path = tmp_path / 'htpasswd'
    store = RegistryHtpasswd(str(path))
    store.reconcile('kube-eng', 'old')
    result = store.reconcile('kube-eng', 'new')
    assert result.changed is True
    assert verify_sha512_crypt('new', path.read_text().strip().partition(':')[2])


def test_htpasswd_reconcile_owns_the_file_and_discards_other_entries(
    tmp_path: pathlib.Path,
):
    """kube-eng is the only writer -- a leftover entry from an earlier auth
    approach must not survive as a valid push credential."""
    path = tmp_path / 'htpasswd'
    path.write_text('legacy:$2y$05$somebcrypthash\n')
    result = RegistryHtpasswd(str(path)).reconcile('kube-eng', 's3cret')
    assert result.changed is True
    lines = path.read_text().splitlines()
    assert len(lines) == 1
    user, _, hashed = lines[0].partition(':')
    assert user == 'kube-eng'
    assert verify_sha512_crypt('s3cret', hashed)


def test_htpasswd_reconcile_check_mode_does_not_write(tmp_path: pathlib.Path):
    path = tmp_path / 'htpasswd'
    result = RegistryHtpasswd(str(path)).reconcile(
        'kube-eng', 's3cret', check_mode=True
    )
    assert result.changed is True
    assert not path.exists()
