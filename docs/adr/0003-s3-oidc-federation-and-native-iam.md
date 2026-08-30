# S3 uses OIDC federation for the console and native IAM accounts for services

The local S3 (RustFS) needs two kinds of access, and they use different mechanisms:

- **Humans**, through the RustFS console, authenticate via **OIDC federation** with `infra.idp` — the same identities and `s3-admin` / `s3-contributor` / `s3-viewer` roles the rest of kube-eng uses.
- **Services** (Loki, Tempo, and any future S3 consumer) authenticate with a **RustFS-native IAM account** — a dedicated access key / secret key pair per service, scoped by a per-service policy.

## OIDC federation (console access)

`infra_apply.yml`'s "Create an IdP client for S3" task registers a confidential `infra.idp` client (`idp_client` → `s3_idp_client`) and feeds its id/secret into RustFS's `RUSTFS_IDENTITY_OPENID_*` container env. `infra_s3_config` supplies the client identity (`client_id`, `client_name`, `client_roles`) and the `callback_url` (`…:{console_port}/rustfs/admin/v3/oidc/callback/default`). Roles arrive on the token as a top-level `roles` claim (the default client scope `idp_client` attaches — see ADR-0002), which RustFS reads via `RUSTFS_IDENTITY_OPENID_ROLES_CLAIM: roles`.

This was deferred once — RustFS's OIDC login didn't work end to end — and is now enabled. The wiring that matters: the redirect/browser URLs are derived from `infra.s3.console_endpoint`, and `RUSTFS_OUTBOUND_ALLOW_ORIGINS` is `infra.idp.client_base_url` (no hard-coded container IPs). The mTLS-trust experiments (`RUSTFS_TRUST_SYSTEM_CA`, `RUSTFS_TRUST_LEAF_CERT_AS_CA`, `RUSTFS_SERVER_MTLS_ENABLE`) are gone; RustFS trusts the local CA through the mounted `SSL_CERT_FILE` truststore like the other services.

`idp_client` / `idp_utils` stay generic (any client, not S3-specific). Note the `module.no_log_values` pitfall around the returned `client_secret` — see `library/idp_client.py`.

## Authorization model

RustFS attaches session policies at OIDC login by **name-matching the claim to existing RustFS policies** — the `roles` claim values must be the names of policies that already exist. So every grant kube-eng makes is a named RustFS policy, provisioned by Ansible, and identities are bound to policies rather than carrying inline permissions.

### Human tiers (three, broad)

Three custom policies, named to match the `s3-*` Keycloak client roles so the `roles` claim resolves. Bucket-fine-grained human roles are explicitly out of scope — a human is admin, read/write, or read-only across all buckets:

| Policy | Grants |
|---|---|
| `s3-admin` | `admin:*`, `kms:*`, `s3:*` on `arn:aws:s3:::*`, `sts:AssumeRole` — mirrors the built-in `consoleAdmin` |
| `s3-contributor` | `s3:*` on `arn:aws:s3:::*`, `sts:AssumeRole` — mirrors the built-in `readwrite`; full data plane, no admin actions |
| `s3-viewer` | an explicit read-only `s3:Get*`/`s3:List*` action list on `arn:aws:s3:::*`, `sts:AssumeRole` |

Created at `infra-apply` alongside the OIDC client wiring (`infra_apply.yml` → `s3_client` in policy-only mode, looped over the three documents), since they are the console-access half. RustFS rejects wildcard action names (`s3:Get*`), so the viewer tier enumerates its actions.

### Per-service policies (one each, least-privilege)

Every S3-consuming service gets exactly one IAM user `svc-<service>` bound to one policy `svc-<service>`, scoped to that service's buckets with an **explicit verb list** (not `s3:*`):

```json
// policy "svc-loki"
{"Version":"2012-10-17","Statement":[{
  "Effect":"Allow",
  "Action":["s3:ListBucket","s3:GetObject","s3:PutObject","s3:DeleteObject",
            "s3:AbortMultipartUpload","s3:ListMultipartUploadParts"],
  "Resource":["arn:aws:s3:::loki-*","arn:aws:s3:::loki-*/*"]
}]}
```

The prefix works because **buckets are named `<service>-<purpose>`** (`loki-chunks`, `loki-ruler`, `loki-admin`, `tempo-traces`, …) — this convention is now a rule, so a service's policy is always `arn:aws:s3:::<service>-*`.

### Identity → policy

| Principal | Identity | Policy | Bound by |
|---|---|---|---|
| Human | Keycloak group → `s3-{admin,contributor,viewer}` client role → `roles` claim | matching `s3-*` policy | RustFS at login |
| Loki / Tempo / … | IAM user `svc-<service>` | `svc-<service>` | `s3_client` at `stack-apply` |

Bucket *provisioning* (`s3_bucket`) stays on the RustFS root key — that is infra-admin work, not a service grant.

### Service credential lifecycle

Each service's access key is `svc-<service>`; its secret is **generated once and persisted** (a `default_factory` field per stack service, same pattern as `infra.registry.admin_password`), then injected into the workload's Helm values. Not minted fresh per `stack-apply`.

## Implementation status

The console OIDC path is wired, and the module layer for the authorization model is built. What remains is the **playbook wiring**:

- `s3_utils.S3Admin` authors custom policies (`policy_ensure` / `policy_remove` via `add-canned-policy`) and reconciles an arbitrary attached-policy set (`account_policy_set(access_key, [names])`). RustFS reports a missing policy as `500 'InternalError: policy does not exist'`, which `policy_get` treats as absent.
- `library/s3_client.py` takes a `policy` arg (inline document, authored under `access_key` — the `svc-<service>` 1:1 name) plus `policies` (pre-existing names to also attach); the old `role: admin|contributor|viewer` is gone. `state: absent` removes the `access_key`-named policy only when `policy` is passed.
- The `s3-*` human policies are created in `infra_apply.yml` (the "Provision the human-tier S3 console policies" task, local S3 only). ✔
- `stack_apply.yml` provisions each service's policy + IAM user and stops passing the root key to Loki/Tempo. *(pending — that file is still largely pre-`infra.*`-refactor: `host.s3`, `cluster.registry.url`, bare `admin_password`, and needs that rewrite first.)*

Until then, Loki and Tempo authenticate with the RustFS root credentials.

## Naming

`infra_s3_config` exposes `api_endpoint` (the S3 API, `:{port}`) and `console_endpoint` (the web console, `:{console_port}`), renamed from the earlier `endpoint` / `admin_endpoint` now that the console is a real OIDC relying party and "admin" was ambiguous with the native-IAM admin API.
