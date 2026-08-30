# Automated chart pushes authenticate with a dedicated htpasswd account; humans use OpenID SSO

The local registry (zot) needs two kinds of access:

- **humans**, through the registry UI, authenticated by `infra.idp` (OpenID) so the same identities and roles the rest of kube-eng uses apply here too;
- **`helm_publish`**, unattended, from `infra_apply` and `helm_repackage`, to push the packaged charts.

zot's `http.auth.openid` covers the first. It does **not** cover the second: in OpenID mode zot's request auth path accepts only htpasswd, LDAP or an existing API key as a password — never an OpenID/OAuth2 access token — and its `POST /zot/auth/apikey` endpoint itself requires you to already be authenticated (browser session, htpasswd or LDAP). So there is no way for Ansible to obtain a push credential from `infra.idp` alone.

## Decision

- **Local registry:** template `http.auth.openid` (pointed at `infra.idp`) **and** `http.auth.htpasswd` into the zot config. `infra.registry.admin_username` (default `kube-eng`) with `infra.registry.admin_password` (generated with `secrets.token_urlsafe(16)`, like every other kube-eng-managed password) is the single htpasswd account, and the `accessControl` policy grants that user full RW on `**`. `helm_publish` does `helm registry login -u {{ admin_username }} -p {{ admin_password }}`.
- **Remote registry:** expected to be configured for OpenID **and** LDAP out of band. `infra.registry.admin_username`/`admin_password` are still the credentials `helm_publish` logs in with (an LDAP bind, typically); they are supplied, not generated, and an empty password makes `helm_publish` skip the login and assume the caller is already authenticated.
- The htpasswd file is written by a dedicated Ansible module, `registry_htpasswd`, called from the `registry_configuration` role with the push account's plaintext password. The `$6$` SHA-512 crypt lives in `module_utils/registry_utils.py` (pure Python, verified against `openssl passwd -6` in the tests) because Python 3.13 dropped `crypt`, `passlib` is unmaintained for 3.13+, and `community.general.htpasswd` needs one of those. The module is idempotent: it re-hashes only when the file has no matching `$6$` entry that verifies against the password, so re-running doesn't restart the registry container.

## Why not a shared IdP service account (the abandoned path)

Two earlier attempts were dropped:

1. **htpasswd with a `bcrypt`-hashed password** via `community.general.htpasswd` — rejected for needing a hand-pinned `bcrypt<4.2` native dependency in the execution environment. The current approach keeps the htpasswd account but sidesteps the dependency by hashing in pure Python with `$6$` instead of bcrypt.
2. **zot `http.auth.bearer.oidc`** (a v2.1.19 feature): `helm_publish` mints a `client_credentials` token from the registry's `infra.idp` client and passes it as the `helm registry login` password; zot validates the JWT and maps the `client_id` claim to the pushing identity. This works for the push (and needs `http.auth.bearer.realm` set to an absolute `<external_url>/zot/auth/token` URL — helm's oras client rejects the bare `"zot"` realm from zot's examples with `bearer realm "zot" uses unsupported scheme ""`). It was abandoned because of the limitation below.

## Limitation: zot cannot run bearer auth and browser SSO together

In zot (through v2.1.20 and `main` as of this writing) `http.auth.bearer` and `http.auth.openid` are mutually exclusive. `AuthHandler` returns early the moment bearer auth is enabled and never runs `tryAuthnHandlers`, which is what builds the OpenID relying parties (and wires up htpasswd/LDAP/API-key/session auth). The `/zot/auth/login` route is still registered from the openid config, so every login attempt then fails with `failed to authenticate due to unrecognized openid provider`.

Since kube-eng wants browser SSO for humans, the `bearer` path is off the table until a zot release lets the two coexist. Only the machine-push path is affected: humans still get full role-mapped access. The registry IdP client's `registry-admin`/`registry-contributor`/`registry-viewer` roles flow through the provider's `claimMapping` (`groups` <- `roles`) into the `accessControl` group policies, so a user in the `registry-admin` group has RW today via SSO. The htpasswd account exists only because Ansible has no way to obtain an equivalent credential unattended.
