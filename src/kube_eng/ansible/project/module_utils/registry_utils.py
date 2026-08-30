"""OCI registry-related tooling"""

import hashlib
import pathlib
import secrets
import typing
import urllib.parse

import pydantic
import requests

from .base import InfraException, InfraResult


class RegistryException(InfraException):
    pass


class RegistryResult(InfraResult):
    pass


class RegistryValidationResult(RegistryResult):
    validated: typing.Annotated[bool, pydantic.Field()]


class RegistryAdmin:
    def __init__(self, registry_endpoint: str, registry_ca_path: str):
        # The distribution spec's base endpoint lives at the registry root
        # (scheme://host:port/v2/), not under whatever path the endpoint
        # happens to carry -- infra.registry.http_endpoint is bare for a
        # local registry but RemoteRegistryConfig.http_endpoint can carry a
        # path (e.g. https://harbor.example.com/kube-eng), so any path
        # component is discarded rather than just trimming a trailing '/'.
        parsed = urllib.parse.urlsplit(registry_endpoint)
        self._registry_endpoint = urllib.parse.urlunsplit(
            (parsed.scheme, parsed.netloc, '', '', '')
        )
        self._registry_ca_path = registry_ca_path

    def validate(
        self, username: str | None = None, password: str | None = None
    ) -> RegistryValidationResult:
        """
        Validate connectivity to the OCI registry, and -- when a
        username/password pair is given -- that the registry actually
        accepts it. The distribution spec's base endpoint (GET /v2/) is
        answered with 200 by every conformant registry whether or not the
        caller authenticates, so an unauthenticated check here proves
        nothing beyond "the server is up". Passing the push account's
        credentials exercises the exact same htpasswd credential
        helm_publish uses to push charts (see ADR-0004): a registry that
        rejects it responds 401/403 rather than silently falling back to
        anonymous access, so this doubles as the entitlements check
        pg/idp/s3 validation do that a bare connectivity probe can't
        provide.
        Args:
            username: The push account name, or None for a bare
                connectivity check only.
            password: The push account password. A Remote registry that
                kube-eng holds no credential for passes an empty password
                (auth there is out of band) and gets the connectivity
                check only.

        Returns:
            A RegistryValidationResult
        Throws:
            RegistryException, when connectivity or authentication is missing
        """
        auth = (username, password) if username and password else None
        try:
            response = requests.get(
                f'{self._registry_endpoint}/v2/',
                auth=auth,
                verify=self._registry_ca_path,
                timeout=10,
            )
        except requests.RequestException as re:
            raise RegistryException(
                code=400, msg='Unable to connect to the registry'
            ) from re
        if not response.ok:
            if auth and response.status_code in (401, 403):
                raise RegistryException(
                    code=response.status_code,
                    msg='Registry rejected the push account credentials',
                )
            raise RegistryException(
                code=response.status_code, msg='Missing connectivity to the registry'
            )
        return RegistryValidationResult(
            changed=False,
            msg=(
                'Connectivity and authentication are validated'
                if auth
                else 'Connectivity is validated'
            ),
            validated=True,
        )


# --- htpasswd -------------------------------------------------------------
#
# The registry (zot) accepts bcrypt, $5$ and $6$ htpasswd hashes. We cannot
# lean on Ansible or the stdlib to produce one: Python 3.13 dropped the `crypt`
# module, `passlib` is unmaintained for 3.13+, and pulling in `bcrypt`
# re-introduces the pinned native dependency ADR-0004 set out to avoid. So the
# $6$ algorithm (https://www.akkadia.org/drepper/SHA-crypt.txt) is implemented
# here directly and verified against `openssl passwd -6` in the tests.

_SHA512_CRYPT_ROUNDS = 5000
# crypt's base64 alphabet -- note the leading './', not the standard '+/'.
_ITOA64 = './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

# Byte-triples of the final digest, in the order SHA-crypt emits them.
_SHA512_PERMUTATION = (
    (0, 21, 42),
    (22, 43, 1),
    (44, 2, 23),
    (3, 24, 45),
    (25, 46, 4),
    (47, 5, 26),
    (6, 27, 48),
    (28, 49, 7),
    (50, 8, 29),
    (9, 30, 51),
    (31, 52, 10),
    (53, 11, 32),
    (12, 33, 54),
    (34, 55, 13),
    (56, 14, 35),
    (15, 36, 57),
    (37, 58, 16),
    (59, 17, 38),
    (18, 39, 60),
    (40, 61, 19),
    (62, 20, 41),
)


def _b64(b2: int, b1: int, b0: int, count: int) -> str:
    word = (b2 << 16) | (b1 << 8) | b0
    chars = []
    for _ in range(count):
        chars.append(_ITOA64[word & 0x3F])
        word >>= 6
    return ''.join(chars)


def random_salt(length: int = 16) -> str:
    """A fresh crypt-alphabet salt of ``length`` characters (max 16 used)."""
    return ''.join(secrets.choice(_ITOA64) for _ in range(length))


def sha512_crypt(password: str, salt: str) -> str:
    """Return the ``$6$<salt>$<hash>`` crypt string for ``password``."""
    if not password:
        raise RegistryException(code=400, msg='Cannot hash an empty password')
    pw = password.encode()
    salt = salt[:16]
    sb = salt.encode()
    plen = len(pw)

    alt = hashlib.sha512(pw + sb + pw).digest()

    ctx = hashlib.sha512()
    ctx.update(pw + sb)
    for _ in range(plen // 64):
        ctx.update(alt)
    ctx.update(alt[: plen % 64])
    bits = plen
    while bits:
        ctx.update(alt if bits & 1 else pw)
        bits >>= 1
    digest = ctx.digest()

    dp = hashlib.sha512(pw * plen).digest()
    p_seq = dp * (plen // 64) + dp[: plen % 64]

    ds = hashlib.sha512(sb * (16 + digest[0])).digest()
    s_seq = ds * (len(sb) // 64) + ds[: len(sb) % 64]

    for i in range(_SHA512_CRYPT_ROUNDS):
        ctx = hashlib.sha512()
        ctx.update(p_seq if i & 1 else digest)
        if i % 3:
            ctx.update(s_seq)
        if i % 7:
            ctx.update(p_seq)
        ctx.update(digest if i & 1 else p_seq)
        digest = ctx.digest()

    encoded = ''.join(
        _b64(digest[x], digest[y], digest[z], 4) for x, y, z in _SHA512_PERMUTATION
    )
    encoded += _b64(0, 0, digest[63], 2)
    return f'$6${salt}${encoded}'


def verify_sha512_crypt(password: str, encoded: str) -> bool:
    """Whether ``password`` produces ``encoded`` (a ``$6$<salt>$<hash>`` string)."""
    parts = encoded.split('$')
    if len(parts) != 4 or parts[1] != '6' or not password:
        return False
    return secrets.compare_digest(sha512_crypt(password, parts[2]), encoded)


class RegistryHtpasswd:
    """Owns the registry's htpasswd file: exactly one push-account entry.

    kube-eng is the only writer of this file, so it is managed exclusively --
    any other entries found (e.g. left over from an earlier auth approach) are
    discarded rather than merged.
    """

    def __init__(self, path: str):
        self._path = pathlib.Path(path)

    def _is_current(self, username: str, password: str) -> bool:
        """Whether the file is already exactly ``username``'s ``$6$`` entry."""
        if not self._path.exists():
            return False
        lines = self._path.read_text().splitlines()
        if len(lines) != 1:
            return False
        user, sep, hashed = lines[0].partition(':')
        return bool(sep) and user == username and verify_sha512_crypt(password, hashed)

    def reconcile(
        self, username: str, password: str, check_mode: bool = False
    ) -> RegistryResult:
        """
        Ensure the htpasswd file is exactly one ``$6$`` entry for ``username``
        matching ``password``. Only rewrites when it isn't already, so
        re-running does not needlessly restart the registry container.
        Throws:
            RegistryException, when the password is empty
        """
        if self._is_current(username, password):
            return RegistryResult(changed=False, msg='htpasswd file is up to date')

        entry = f'{username}:{sha512_crypt(password, random_salt())}\n'
        if not check_mode:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(entry)
            self._path.chmod(0o600)
        return RegistryResult(changed=True, msg=f'wrote htpasswd entry for {username}')
