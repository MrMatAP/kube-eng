# Infrastructure Configuration Section Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a top-level `infrastructure` config section so the four core services (PostgreSQL, IdP, S3, registry) can each be either local (Docker container) or remote (given endpoint + admin credentials), specified once and referenced everywhere, backed by a regression test suite covering all supported configuration.

**Architecture:** Each core service becomes a Pydantic discriminated union (`provider: local | remote`). Local variants keep the container provisioning fields and *compute* the connectivity view; remote variants require connectivity + admin credentials and expose the same computed view. Consumers (IdP DB, Grafana DB, OIDC issuer, chart refs) resolve through the existing `_root_config` back-reference instead of duplicating values. Ansible playbooks branch provisioning on `provider == 'local'` and read only the computed connectivity/credential fields. Helm charts keep receiving fully-resolved values.

**Tech Stack:** Python 3.14, Pydantic v2, pytest, ansible (playbook syntax-check), helm (template render tests).

## Global Constraints

- Python 3.14; format with `uv run ruff format src/`, lint with `uv run ruff check src/` (single quotes, 88-char lines, 4-space indent)
- Type check with `uv run pyrefly check` (NOT mypy)
- Run tests with `uv run pytest`
- All config sub-models MUST extend `RootConfigAware` (from `kube_eng.config.base`)
- Import order: stdlib, blank line, third-party, blank line, local package (`from .x import Y` allowed within the package)
- Pydantic v2 idioms: `Field()`, `computed_field`, `model_post_init`
- Commit messages end with: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`

## Preconditions

- The working tree currently has uncommitted changes (`stack_apply.yml`, `stack_config.py`, `kube-eng-grafana` chart). **Commit or stash them before Task 1.** The "old code" quotes in this plan reflect the working tree as of 2026-07-19.
- Out of scope (explicitly): TUI (`src/kube_eng/tui/`) — it references removed fields and will need a separate migration; Kafka and DNS stay under `host` unchanged (they follow this pattern later); remote-registry auth (helm/docker credential store handles login out of band); CA injection into Loki/Tempo (tracked TODO).
- Migration note for existing user config files (`~/.kube-eng/config.yaml`): Pydantic ignores unknown keys, so old files load with defaults for the new section. Users who customized `host.postgresql/idp/s3/registry` or `cluster.registry.url` must re-enter those values under `infrastructure`. Behavior for an all-defaults local setup is unchanged.

## File Structure

| File | Responsibility |
|---|---|
| `src/kube_eng/config/infrastructure_config.py` (create) | All four service unions + `InfrastructureConfig` |
| `src/kube_eng/config/root_config.py` (modify) | `infrastructure` field, credential defaulting in `model_post_init` |
| `src/kube_eng/config/host_config.py` (modify) | Remove PostgreSQL/IdP/S3/registry classes |
| `src/kube_eng/config/cluster_config.py` (modify) | `ClusterOIDCConfig` delegates to infra IdP; remove `ClusterRegistryConfig` |
| `src/kube_eng/config/stack_config.py` (modify) | Grafana DB references infra PostgreSQL; per-consumer client secrets |
| `src/kube_eng/config/__init__.py` (modify) | Export `InfrastructureConfig` |
| `tests/test_infrastructure_config.py` (create) | Config matrix tests (local/remote × service) |
| `tests/test_extravars_contract.py` + `tests/golden/*.json` (create) | Golden-file contract for the shape Ansible consumes |
| `tests/test_ansible_playbooks.py` (create) | Playbook syntax-check + stale-reference guard |
| `tests/test_helm_charts.py` + `tests/helm_values/*.yaml` (create) | `helm template` render tests per scenario |
| `src/kube_eng/ansible/project/{host,cluster,stack}_apply.yml`, `helm_repackage.yml` (modify) | Consume `infrastructure.*`, provider gating, bug fixes |
| `src/kube_eng/helm/kube-eng-{loki,tempo}/values.yaml` (modify) | Neutralize local-infra default endpoints |
| `CLAUDE.md` (modify) | Document the new section |

---

### Task 1: PostgreSQL infrastructure union, wired into RootConfig

**Files:**
- Create: `src/kube_eng/config/infrastructure_config.py`
- Modify: `src/kube_eng/config/root_config.py`
- Modify: `src/kube_eng/config/__init__.py`
- Test: `tests/test_infrastructure_config.py`

**Interfaces:**
- Consumes: `RootConfigAware` from `src/kube_eng/config/base.py`; `host.dns.zone` (existing computed field, `f'{cluster.name}.k8s'`).
- Produces: `RootConfig.infrastructure.postgresql` with the uniform connectivity view used by every later task: `provider: str` (`'local'`/`'remote'`), `client_host: str`, `client_port: int`, `admin_host: str`, `admin_port: int`, `admin_user: str`, `admin_password: str`. Local-only: `name`, `image`, `volume_name`, `host_ip`, `host_port`. `InfrastructureConfig` class with field `postgresql`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_infrastructure_config.py`:

```python
"""
Infrastructure configuration matrix tests
"""

import pathlib

import pytest
from pydantic import ValidationError

from kube_eng.config import RootConfig


def make_config(tmp_path: pathlib.Path, **infrastructure) -> RootConfig:
    """Build a RootConfig with deterministic identity and the given infrastructure overrides."""
    return RootConfig(
        config_path=tmp_path,
        admin_password='test-admin',
        cluster={'name': 'testcluster'},
        infra=infrastructure,
    )


class TestPostgresql:
    def test_local_defaults(self, tmp_path: pathlib.Path):
        pg = make_config(tmp_path).infra.pg
        assert pg.provider == 'local'
        assert pg.client_host == 'pg.testcluster.k8s'
        assert pg.client_port == 5432
        assert pg.admin_host == '127.0.0.1'
        assert pg.admin_port == 5432
        assert pg.admin_user == 'postgres'
        assert pg.admin_password == 'test-admin'

    def test_local_explicit_admin_password_is_kept(self, tmp_path: pathlib.Path):
        pg = make_config(
            tmp_path, postgresql={'provider': 'local', 'admin_password': 'pg-secret'}
        ).infra.pg
        assert pg.admin_password == 'pg-secret'

    def test_remote(self, tmp_path: pathlib.Path):
        pg = make_config(
            tmp_path,
            postgresql={
                'provider': 'remote',
                'host': 'pg.central.example.com',
                'port': 5433,
                'admin_user': 'postgres',
                'admin_password': 'central-secret',
            },
        ).infra.pg
        assert pg.provider == 'remote'
        assert pg.client_host == 'pg.central.example.com'
        assert pg.client_port == 5433
        assert pg.admin_host == 'pg.central.example.com'
        assert pg.admin_port == 5433
        assert pg.admin_password == 'central-secret'

    def test_remote_requires_host_and_credentials(self, tmp_path: pathlib.Path):
        with pytest.raises(ValidationError):
            make_config(tmp_path, postgresql={'provider': 'remote'})
        with pytest.raises(ValidationError):
            make_config(
                tmp_path, postgresql={'provider': 'remote', 'host': 'pg.example.com'}
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_infrastructure_config.py -v`
Expected: FAIL/ERROR — `RootConfig` has no field `infrastructure` (unexpected keyword argument).

- [ ] **Step 3: Create the infrastructure module**

Create `src/kube_eng/config/infrastructure_config.py`:

```python
import typing

from pydantic import Field, computed_field

from .base import RootConfigAware


class LocalPostgresqlConfig(RootConfigAware):
    """PostgreSQL provisioned locally as a Docker container."""
    provider: typing.Literal['local'] = 'local'
    name: str = Field(default='pg', description='Name of the PostgreSQL container')
    image: str = Field(default='postgres:18-alpine', description='PostgreSQL container image')
    volume_name: str = Field(default='pg-volume', description='Name of the PostgreSQL volume')
    host_ip: str = Field(default='127.0.0.1', description='IP address to expose the PostgreSQL server on the host')
    host_port: int = Field(default=5432, description='Port to expose the PostgreSQL server on the host')
    admin_user: str = Field(default='postgres', description='PostgreSQL superuser')
    admin_password: str = Field(default='', description='PostgreSQL superuser password. If empty, defaults to the admin password')

    @computed_field
    @property
    def client_host(self) -> str:
        """Hostname consumers (containers and cluster workloads) connect to."""
        return f'{self.name}.{self._root_config.host.dns.zone}'

    @computed_field
    @property
    def client_port(self) -> int:
        """Port consumers connect to (the in-network container port)."""
        return 5432

    @computed_field
    @property
    def admin_host(self) -> str:
        """Hostname Ansible uses to administer the server from this host."""
        return self.host_ip

    @computed_field
    @property
    def admin_port(self) -> int:
        """Port Ansible uses to administer the server from this host."""
        return self.host_port


class RemotePostgresqlConfig(RootConfigAware):
    """Central PostgreSQL hosted elsewhere."""
    provider: typing.Literal['remote'] = 'remote'
    host: str = Field(description='Hostname of the PostgreSQL server')
    port: int = Field(default=5432, description='Port of the PostgreSQL server')
    admin_user: str = Field(description='PostgreSQL administrative user')
    admin_password: str = Field(description='PostgreSQL administrative password')

    @computed_field
    @property
    def client_host(self) -> str:
        return self.host

    @computed_field
    @property
    def client_port(self) -> int:
        return self.port

    @computed_field
    @property
    def admin_host(self) -> str:
        return self.host

    @computed_field
    @property
    def admin_port(self) -> int:
        return self.port


InfraPostgresqlConfig = typing.Annotated[
    LocalPostgresqlConfig | RemotePostgresqlConfig,
    Field(discriminator='provider'),
]


class InfrastructureConfig(RootConfigAware):
    """Core infrastructure the cluster and stack depend on."""
    postgresql: InfraPostgresqlConfig = Field(default_factory=LocalPostgresqlConfig)
```

In `src/kube_eng/config/root_config.py`:

Add the import (after the existing `.host_config` import):

```python
from .infrastructure_config import InfrastructureConfig
```

Add the field (after the `stack` field, line 29):

```python
    infrastructure: InfrastructureConfig = Field(default_factory=InfrastructureConfig, description="Infrastructure configuration")
```

In `model_post_init`, after the existing IdP-db-password block, add:

```python
        # Local infrastructure credentials default to the admin password
if (
        self.infra.pg.provider == 'local'
        and self.infra.pg.admin_password == ''
):
    self.infra.pg.admin_password = self.admin_password
```

In `src/kube_eng/config/__init__.py`, add:

```python
from .infrastructure_config import InfrastructureConfig as InfrastructureConfig
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_infrastructure_config.py tests/test_config.py -v`
Expected: all PASS (including the two pre-existing propagation tests — the union members are `RootConfigAware`, so propagation reaches them).

- [ ] **Step 5: Lint, type check, commit**

```bash
uv run ruff format src/ tests/ && uv run ruff check src/ && uv run pyrefly check
git add src/kube_eng/config/ tests/test_infrastructure_config.py
git commit -m "feat(config): infrastructure section with local/remote PostgreSQL union"
```

---

### Task 2: IdP, S3, and registry unions

**Files:**
- Modify: `src/kube_eng/config/infrastructure_config.py`
- Modify: `src/kube_eng/config/root_config.py` (`model_post_init` defaulting)
- Test: `tests/test_infrastructure_config.py`

**Interfaces:**
- Consumes: Task 1's module and `make_config` test helper.
- Produces on `RootConfig.infrastructure`:
  - `idp`: `provider`, `url: str` (base URL, no trailing slash), `realm: str`, `admin_user: str`, `admin_password: str`, `issuer_url: str` (computed `f'{url}/realms/{realm}'`). Local-only: `name`, `image`, `host_ip`, `host_port`, `config_path`, `db_name`, `db_user`, `db_password`.
  - `s3`: `provider`, `endpoint: str` (URL consumers use), `admin_endpoint: str` (URL Ansible uses), `access_key: str`, `secret_key: str`, `region: str`. Local-only: `name`, `image`, `volume_name`, `port`, `console_port`, `host_ip`, `host_port`, `host_console_port`, `config_path`.
  - `registry`: `provider`, `url: str` (`oci://…`, no trailing slash), `https_url: str` (computed). Local-only: `name`, `image`, `volume_name`, `port`, `host_ip`, `host_port`, `config_path`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_infrastructure_config.py`:

```python
class TestIdp:
    def test_local_defaults(self, tmp_path: pathlib.Path):
        idp = make_config(tmp_path).infra.idp
        assert idp.provider == 'local'
        assert idp.url == 'https://idp.testcluster.k8s:8443'
        assert idp.issuer_url == 'https://idp.testcluster.k8s:8443/realms/master'
        assert idp.admin_user == 'admin'
        assert idp.admin_password == 'test-admin'
        assert idp.db_name == 'idp'
        assert idp.db_user == 'idp'
        assert idp.db_password == 'test-admin'

    def test_remote(self, tmp_path: pathlib.Path):
        idp = make_config(
            tmp_path,
            idp={
                'provider': 'remote',
                'url': 'https://idp.central.example.com/',
                'realm': 'kube-eng',
                'admin_user': 'kc-admin',
                'admin_password': 'kc-secret',
            },
        ).infra.idp
        assert idp.url == 'https://idp.central.example.com'
        assert idp.issuer_url == 'https://idp.central.example.com/realms/kube-eng'

    def test_remote_requires_realm_and_credentials(self, tmp_path: pathlib.Path):
        with pytest.raises(ValidationError):
            make_config(
                tmp_path, idp={'provider': 'remote', 'url': 'https://idp.example.com'}
            )


class TestS3:
    def test_local_defaults(self, tmp_path: pathlib.Path):
        s3 = make_config(tmp_path).infra.s3
        assert s3.provider == 'local'
        assert s3.endpoint == 'https://s3.testcluster.k8s:9000'
        assert s3.admin_endpoint == 'https://s3.testcluster.k8s:9000'
        assert s3.access_key == 'admin'
        assert s3.secret_key == 'test-admin'
        assert s3.region == 'us-east-1'

    def test_remote(self, tmp_path: pathlib.Path):
        s3 = make_config(
            tmp_path,
            s3={
                'provider': 'remote',
                'endpoint': 'https://s3.central.example.com/',
                'access_key': 'ak',
                'secret_key': 'sk',
            },
        ).infra.s3
        assert s3.endpoint == 'https://s3.central.example.com'
        assert s3.admin_endpoint == 'https://s3.central.example.com'

    def test_remote_requires_credentials(self, tmp_path: pathlib.Path):
        with pytest.raises(ValidationError):
            make_config(
                tmp_path, s3={'provider': 'remote', 'endpoint': 'https://s3.example.com'}
            )


class TestRegistry:
    def test_local_defaults(self, tmp_path: pathlib.Path):
        registry = make_config(tmp_path).infra.registry
        assert registry.provider == 'local'
        assert registry.url == 'oci://registry.testcluster.k8s:5001'
        assert registry.https_url == 'https://registry.testcluster.k8s:5001'

    def test_remote(self, tmp_path: pathlib.Path):
        registry = make_config(
            tmp_path,
            registry={'provider': 'remote', 'url': 'oci://harbor.example.com/kube-eng/'},
        ).infra.registry
        assert registry.url == 'oci://harbor.example.com/kube-eng'
        assert registry.https_url == 'https://harbor.example.com/kube-eng'

    def test_remote_rejects_non_oci_url(self, tmp_path: pathlib.Path):
        with pytest.raises(ValidationError):
            make_config(
                tmp_path,
                registry={'provider': 'remote', 'url': 'https://harbor.example.com'},
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_infrastructure_config.py -v`
Expected: new tests FAIL/ERROR — `InfrastructureConfig` has no fields `idp`/`s3`/`registry`.

- [ ] **Step 3: Implement the three unions**

In `src/kube_eng/config/infrastructure_config.py`, extend the pydantic import to include `field_validator`, add `import pathlib` to the stdlib imports, and add before `InfrastructureConfig`:

```python
class LocalIdpConfig(RootConfigAware):
    """Keycloak IdP provisioned locally as a Docker container."""
    provider: typing.Literal['local'] = 'local'
    name: str = Field(default='idp', description='Name of the IdP container')
    image: str = Field(default='keycloak/keycloak:26.5.6', description='IdP container image')
    host_ip: str = Field(default='127.0.0.1', description='IP address to expose the IdP on the host')
    host_port: int = Field(default=8443, description='Port to expose the IdP on the host')
    realm: str = Field(default='master', description='Realm to register clients in')
    admin_user: str = Field(default='admin', description='IdP administrative user')
    admin_password: str = Field(default='', description='IdP administrative password. If empty, defaults to the admin password')
    db_name: str = Field(default='idp', description='Name of the IdP database')
    db_user: str = Field(default='idp', description='User for the IdP database')
    db_password: str = Field(default='', description='Password for the IdP database. If empty, defaults to the admin password')

    @computed_field
    @property
    def config_path(self) -> pathlib.Path:
        """Directory to store IdP configuration in."""
        return self._root_config.config_path / 'idp'

    @computed_field
    @property
    def url(self) -> str:
        """Base URL of the IdP as reachable by consumers and this host."""
        return f'https://{self.name}.{self._root_config.host.dns.zone}:{self.host_port}'

    @computed_field
    @property
    def issuer_url(self) -> str:
        return f'{self.url}/realms/{self.realm}'


class RemoteIdpConfig(RootConfigAware):
    """Central IdP hosted elsewhere."""
    provider: typing.Literal['remote'] = 'remote'
    url: str = Field(description='Base URL of the IdP, e.g. https://idp.example.com:8443')
    realm: str = Field(description='Realm to register clients in')
    admin_user: str = Field(description='IdP administrative user')
    admin_password: str = Field(description='IdP administrative password')

    @field_validator('url')
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip('/')

    @computed_field
    @property
    def issuer_url(self) -> str:
        return f'{self.url}/realms/{self.realm}'


class LocalS3Config(RootConfigAware):
    """S3-compatible storage provisioned locally as a Docker container."""
    provider: typing.Literal['local'] = 'local'
    name: str = Field(default='s3', description='Name of the S3 container')
    image: str = Field(default='rustfs/rustfs:latest', description='S3 container image')
    volume_name: str = Field(default='s3-volume', description='Name of the S3 volume')
    port: int = Field(default=9000, description='Port the S3 server listens on inside the container')
    console_port: int = Field(default=9001, description='Port the S3 console listens on inside the container')
    host_ip: str = Field(default='127.0.0.1', description='IP address to expose the S3 server on the host')
    host_port: int = Field(default=9000, description='Port to expose the S3 server on the host')
    host_console_port: int = Field(default=9001, description='Port to expose the S3 console on the host')
    access_key: str = Field(default='admin', description='S3 access key')
    secret_key: str = Field(default='', description='S3 secret key. If empty, defaults to the admin password')
    region: str = Field(default='us-east-1', description='S3 region name')

    @computed_field
    @property
    def config_path(self) -> pathlib.Path:
        """Directory to store S3 configuration in."""
        return self._root_config.config_path / 's3'

    @computed_field
    @property
    def endpoint(self) -> str:
        """Endpoint URL consumers (containers and cluster workloads) use."""
        return f'https://{self.name}.{self._root_config.host.dns.zone}:{self.port}'

    @computed_field
    @property
    def admin_endpoint(self) -> str:
        """Endpoint URL Ansible uses to administer S3 from this host."""
        return f'https://{self.name}.{self._root_config.host.dns.zone}:{self.host_port}'


class RemoteS3Config(RootConfigAware):
    """Central S3-compatible storage hosted elsewhere."""
    provider: typing.Literal['remote'] = 'remote'
    endpoint: str = Field(description='Endpoint URL of the S3 service')
    access_key: str = Field(description='S3 access key')
    secret_key: str = Field(description='S3 secret key')
    region: str = Field(default='us-east-1', description='S3 region name')

    @field_validator('endpoint')
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip('/')

    @computed_field
    @property
    def admin_endpoint(self) -> str:
        return self.endpoint


class LocalRegistryConfig(RootConfigAware):
    """OCI registry provisioned locally as a Docker container."""
    provider: typing.Literal['local'] = 'local'
    name: str = Field(default='registry', description='Name of the OCI registry container')
    image: str = Field(default='ghcr.io/project-zot/zot-linux-arm64:v2.1.15', description='OCI registry container image')
    volume_name: str = Field(default='registry-volume', description='Name of the OCI registry volume')
    port: int = Field(default=5000, description='Port the registry listens on inside the container')
    host_ip: str = Field(default='127.0.0.1', description='IP address to expose the registry on the host')
    host_port: int = Field(default=5001, description='Port to expose the registry on the host')

    @computed_field
    @property
    def config_path(self) -> pathlib.Path:
        """Directory to store registry configuration in."""
        return self._root_config.config_path / 'registry'

    @computed_field
    @property
    def url(self) -> str:
        """OCI URL for images and Helm charts."""
        return f'oci://{self.name}.{self._root_config.host.dns.zone}:{self.host_port}'

    @computed_field
    @property
    def https_url(self) -> str:
        return 'https://' + self.url.removeprefix('oci://')


class RemoteRegistryConfig(RootConfigAware):
    """Central OCI registry hosted elsewhere. Authenticate out of band (docker/helm login)."""
    provider: typing.Literal['remote'] = 'remote'
    url: str = Field(description='OCI URL of the registry, e.g. oci://harbor.example.com/kube-eng')

    @field_validator('url')
    @classmethod
    def validate_oci_url(cls, value: str) -> str:
        if not value.startswith('oci://'):
            raise ValueError('registry url must start with oci://')
        return value.rstrip('/')

    @computed_field
    @property
    def https_url(self) -> str:
        return 'https://' + self.url.removeprefix('oci://')


InfraIdpConfig = typing.Annotated[
    LocalIdpConfig | RemoteIdpConfig,
    Field(discriminator='provider'),
]
InfraS3Config = typing.Annotated[
    LocalS3Config | RemoteS3Config,
    Field(discriminator='provider'),
]
InfraRegistryConfig = typing.Annotated[
    LocalRegistryConfig | RemoteRegistryConfig,
    Field(discriminator='provider'),
]
```

Extend `InfrastructureConfig`:

```python
class InfrastructureConfig(RootConfigAware):
    """Core infrastructure the cluster and stack depend on."""
    postgresql: InfraPostgresqlConfig = Field(default_factory=LocalPostgresqlConfig)
    idp: InfraIdpConfig = Field(default_factory=LocalIdpConfig)
    s3: InfraS3Config = Field(default_factory=LocalS3Config)
    registry: InfraRegistryConfig = Field(default_factory=LocalRegistryConfig)
```

In `root_config.py` `model_post_init`, extend the credential-defaulting block added in Task 1:

```python
        # Local infrastructure credentials default to the admin password
infra = self.infra
if infra.pg.provider == 'local' and infra.pg.admin_password == '':
    infra.pg.admin_password = self.admin_password
if infra.idp.provider == 'local':
    if infra.idp.admin_password == '':
        infra.idp.admin_password = self.admin_password
    if infra.idp.db_password == '':
        infra.idp.db_password = self.admin_password
if infra.s3.provider == 'local' and infra.s3.secret_key == '':
    infra.s3.secret_key = self.admin_password
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 5: Lint, type check, commit**

```bash
uv run ruff format src/ tests/ && uv run ruff check src/ && uv run pyrefly check
git add src/kube_eng/config/ tests/test_infrastructure_config.py
git commit -m "feat(config): IdP, S3 and registry infrastructure unions"
```

---

### Task 3: Cut consumers over, delete the old fields

**Files:**
- Modify: `src/kube_eng/config/host_config.py` (delete `HostPostgresqlConfig`, `HostIDPConfig`, `HostS3Config`, `HostRegistryConfig` and their fields on `HostConfig`)
- Modify: `src/kube_eng/config/cluster_config.py` (rewrite `ClusterOIDCConfig.issuer_url`; delete `ClusterRegistryConfig` and the `registry` field)
- Modify: `src/kube_eng/config/stack_config.py` (Grafana DB + client secrets)
- Modify: `src/kube_eng/config/root_config.py` (remove obsolete `model_post_init` blocks; add consumer-secret defaulting)
- Test: `tests/test_infrastructure_config.py`

**Interfaces:**
- Consumes: `infrastructure.postgresql.client_host/client_port`, `infrastructure.idp.issuer_url`, `infrastructure.registry.url` from Tasks 1–2.
- Produces: `stack.grafana.db_host: str` / `db_port: int` (computed), `stack.grafana.client_secret: str`, `stack.kiali.client_secret: str`, `cluster.oidc.issuer_url` (delegating). **Removed:** `host.postgresql`, `host.idp`, `host.s3`, `host.registry`, `cluster.registry`, `stack.grafana.db_host/db_port` as stored fields.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_infrastructure_config.py`:

```python
class TestConsumerReferences:
    def test_grafana_db_references_infrastructure_postgresql(self, tmp_path: pathlib.Path):
        config = make_config(
            tmp_path,
            postgresql={
                'provider': 'remote',
                'host': 'pg.central.example.com',
                'admin_user': 'postgres',
                'admin_password': 'central-secret',
            },
        )
        assert config.stack.grafana.db_host == 'pg.central.example.com'
        assert config.stack.grafana.db_port == 5432
        assert config.stack.grafana.db_password == 'test-admin'

    def test_cluster_oidc_issuer_references_infrastructure_idp(self, tmp_path: pathlib.Path):
        config = make_config(
            tmp_path,
            idp={
                'provider': 'remote',
                'url': 'https://idp.central.example.com',
                'realm': 'kube-eng',
                'admin_user': 'kc-admin',
                'admin_password': 'kc-secret',
            },
        )
        assert config.cluster.oidc.issuer_url == 'https://idp.central.example.com/realms/kube-eng'

    def test_client_secrets_default_to_admin_password(self, tmp_path: pathlib.Path):
        config = make_config(tmp_path)
        assert config.stack.grafana.client_secret == 'test-admin'
        assert config.stack.kiali.client_secret == 'test-admin'

    def test_old_sections_are_gone(self, tmp_path: pathlib.Path):
        config = make_config(tmp_path)
        assert not hasattr(config.host, 'postgresql')
        assert not hasattr(config.host, 'idp')
        assert not hasattr(config.host, 's3')
        assert not hasattr(config.host, 'registry')
        assert not hasattr(config.cluster, 'registry')


class TestRoundTrip:
    def test_yaml_round_trip_remote(self, tmp_path: pathlib.Path):
        config = make_config(
            tmp_path,
            postgresql={
                'provider': 'remote',
                'host': 'pg.central.example.com',
                'admin_user': 'postgres',
                'admin_password': 'central-secret',
            },
            idp={
                'provider': 'remote',
                'url': 'https://idp.central.example.com',
                'realm': 'kube-eng',
                'admin_user': 'kc-admin',
                'admin_password': 'kc-secret',
            },
        )
        config.save()
        reloaded = RootConfig.load(config_path=tmp_path)
        assert reloaded.infra.pg.provider == 'remote'
        assert reloaded.infra.idp.provider == 'remote'
        assert reloaded.model_dump(mode='json') == config.model_dump(mode='json')

    def test_yaml_round_trip_local(self, tmp_path: pathlib.Path):
        config = make_config(tmp_path)
        config.save()
        reloaded = RootConfig.load(config_path=tmp_path)
        assert reloaded.model_dump(mode='json') == config.model_dump(mode='json')
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_infrastructure_config.py -v`
Expected: `TestConsumerReferences` and `test_old_sections_are_gone` FAIL (old fields still exist, `db_host` is `'pg'`, `client_secret` missing).

- [ ] **Step 3: Implement the cut-over**

`host_config.py`: delete the classes `HostPostgresqlConfig`, `HostIDPConfig`, `HostS3Config`, `HostRegistryConfig` entirely, and reduce `HostConfig` to:

```python
class HostConfig(RootConfigAware):
    tool: HostToolConfig = Field(default_factory=HostToolConfig)
    pki: HostPKIConfig = Field(default_factory=HostPKIConfig)
    dns: HostDNSConfig = Field(default_factory=HostDNSConfig)
    kafka: HostKafkaConfig = Field(default_factory=HostKafkaConfig)
```

`cluster_config.py`: delete `ClusterRegistryConfig` and the `registry: ClusterRegistryConfig` field on `ClusterConfig`; replace `ClusterOIDCConfig.issuer_url` with:

```python
    @computed_field
@property
def issuer_url(self) -> str:
    """
    Computed IDP issuer URL for the cluster
    Returns:
        Computed IDP issuer URL for the cluster
    """
    return self._root_config.infra.idp.issuer_url
```

`stack_config.py`: import `computed_field` from pydantic and change `StackGrafanaConfig` / `StackKialiConfig`:

```python
class StackGrafanaConfig(RootConfigAware):
    enabled: bool = Field(default=True)
    ns: str = Field(default='grafana')
    hostname: str = Field(default='grafana')
    client_id: str = Field(default='kube-eng-grafana')
    client_secret: str = Field(default='', description='OIDC client secret. If empty, defaults to the admin password')
    admin_user: str = Field(default='admin')
    db_kind: StackGrafanaDBKind = Field(default=StackGrafanaDBKind.sqlite3)
    db_name: str = Field(default='grafana')
    db_user: str = Field(default='grafana')
    db_password: str = Field(default='',
                             description='Grafana database password. If empty, defaults to the admin password')
    db_ssl_mode: StackGrafanaDBSSL = Field(default=StackGrafanaDBSSL.require)

    @computed_field
    @property
    def db_host(self) -> str:
        return self._root_config.infra.pg.client_host

    @computed_field
    @property
    def db_port(self) -> int:
        return self._root_config.infra.pg.client_port
```

(Preserve any additional fields the pre-plan working tree already added to `StackGrafanaConfig`; only `db_host`/`db_port` move to computed and `db_password` changes default.) Add to `StackKialiConfig`:

```python
    client_secret: str = Field(default='', description='OIDC client secret. If empty, defaults to the admin password')
```

`root_config.py` `model_post_init`: **delete** the old blocks that populate `cluster.registry.url` and `host.idp.db_password` (lines 122–128 of the pre-plan file), and append to the Task 2 defaulting block:

```python
        if self.stack.grafana.db_password == '':
            self.stack.grafana.db_password = self.admin_password
        if self.stack.grafana.client_secret == '':
            self.stack.grafana.client_secret = self.admin_password
        if self.stack.kiali.client_secret == '':
            self.stack.kiali.client_secret = self.admin_password
```

- [ ] **Step 4: Run all tests**

Run: `uv run pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 5: Lint, type check, commit**

```bash
uv run ruff format src/ tests/ && uv run ruff check src/ && uv run pyrefly check
git add src/kube_eng/config/ tests/
git commit -m "feat(config): consumers reference infrastructure; remove duplicated host sections"
```

Note: the TUI (`src/kube_eng/tui/config_tab.py`) may now reference removed fields — that is expected and out of scope; do not fix it in this task.

---

### Task 4: Extravars golden contract tests

**Files:**
- Create: `tests/test_extravars_contract.py`
- Create: `tests/golden/extravars_local.json`, `tests/golden/extravars_remote.json` (generated)

**Interfaces:**
- Consumes: the full `RootConfig` from Tasks 1–3; `AnsibleExecution` passes `model_dump(mode='json')` as extravars — this test freezes that shape.
- Produces: golden JSON files that later Ansible tasks (5–7) treat as the authoritative variable tree.

- [ ] **Step 1: Write the test (it doubles as the generator)**

Create `tests/test_extravars_contract.py`:

```python
"""
Golden-file contract for the extravars shape consumed by the Ansible playbooks.
Regenerate after intentional model changes with:  UPDATE_GOLDEN=1 uv run pytest tests/test_extravars_contract.py
"""

import json
import os
import pathlib
from typing import Any

import pytest

from kube_eng.config import RootConfig

GOLDEN_DIR = pathlib.Path(__file__).parent / 'golden'


def _local_config() -> RootConfig:
    return RootConfig(
        config_path=pathlib.Path('/kube-eng-test'),
        admin_password='test-admin',
        user_id='test-user',
        cluster={'name': 'testcluster'},
    )


def _remote_config() -> RootConfig:
    return RootConfig(
        config_path=pathlib.Path('/kube-eng-test'),
        admin_password='test-admin',
        user_id='test-user',
        cluster={'name': 'testcluster'},
        infra={
            'postgresql': {
                'provider': 'remote',
                'host': 'pg.central.example.com',
                'admin_user': 'postgres',
                'admin_password': 'pg-secret',
            },
            'idp': {
                'provider': 'remote',
                'url': 'https://idp.central.example.com',
                'realm': 'kube-eng',
                'admin_user': 'kc-admin',
                'admin_password': 'kc-secret',
            },
            's3': {
                'provider': 'remote',
                'endpoint': 'https://s3.central.example.com',
                'access_key': 'ak',
                'secret_key': 'sk',
            },
            'registry': {
                'provider': 'remote',
                'url': 'oci://harbor.example.com/kube-eng',
            },
        },
    )


def _normalize(dumped: dict[str, Any]) -> dict[str, Any]:
    """Blank out machine- and version-dependent values."""
    dumped['version'] = 'VERSION'
    dumped['host']['tool']['helm']['chart_version'] = 'VERSION'
    dumped['host']['tool']['helm']['chart_path'] = 'CHART_PATH'
    return dumped


@pytest.mark.parametrize(
    'name,factory',
    [('extravars_local', _local_config), ('extravars_remote', _remote_config)],
)
def test_extravars_contract(name: str, factory):
    dumped = _normalize(factory().model_dump(mode='json'))
    golden_path = GOLDEN_DIR / f'{name}.json'
    if os.environ.get('UPDATE_GOLDEN'):
        GOLDEN_DIR.mkdir(exist_ok=True)
        golden_path.write_text(json.dumps(dumped, indent=2, sort_keys=True) + '\n')
    assert golden_path.exists(), 'golden file missing — run with UPDATE_GOLDEN=1'
    assert dumped == json.loads(golden_path.read_text())
```

- [ ] **Step 2: Run to verify it fails (no golden files yet)**

Run: `uv run pytest tests/test_extravars_contract.py -v`
Expected: FAIL with "golden file missing".

- [ ] **Step 3: Generate the golden files and inspect them**

```bash
UPDATE_GOLDEN=1 uv run pytest tests/test_extravars_contract.py -v
git diff --no-index /dev/null tests/golden/extravars_local.json | head -80
```

Manually verify: `infrastructure.postgresql.client_host` is `pg.testcluster.k8s` in local, `pg.central.example.com` in remote; no `host.postgresql`/`cluster.registry` keys anywhere; secrets are the test placeholders.

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_extravars_contract.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_extravars_contract.py tests/golden/
git commit -m "test: extravars golden contract for the Ansible variable tree"
```

---

### Task 5: Migrate host_apply.yml + playbook test harness

**Files:**
- Modify: `src/kube_eng/ansible/project/host_apply.yml`
- Create: `tests/test_ansible_playbooks.py`

**Interfaces:**
- Consumes: extravars tree per `tests/golden/extravars_local.json`: `infrastructure.postgresql.*`, `infrastructure.idp.*`, `infrastructure.s3.*`, `infrastructure.registry.*` (fields listed in Tasks 1–2 Produces blocks).
- Produces: `host_apply.yml` that provisions containers only when `provider == 'local'`; the syntax-check + stale-reference test harness used by Tasks 6–7.

- [ ] **Step 1: Write the test harness**

Create `tests/test_ansible_playbooks.py`:

```python
"""
Playbook-level regression tests: syntax and stale config references.
"""

import pathlib
import shutil
import subprocess

import pytest

PROJECT_DIR = (
    pathlib.Path(__file__).parent.parent / 'src' / 'kube_eng' / 'ansible' / 'project'
)
PLAYBOOKS = sorted(PROJECT_DIR.glob('*.yml'))
STALE_PATTERNS = [
    'host.postgresql',
    'host.idp',
    'host.s3',
    'host.registry',
    'cluster.registry',
]


@pytest.mark.skipif(
    shutil.which('ansible-playbook') is None, reason='ansible-playbook not available'
)
@pytest.mark.parametrize('playbook', PLAYBOOKS, ids=lambda p: p.name)
def test_playbook_syntax(playbook: pathlib.Path):
    result = subprocess.run(
        ['ansible-playbook', '--syntax-check', '-i', 'localhost,', str(playbook)],
        capture_output=True,
        text=True,
        cwd=PROJECT_DIR,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('playbook', PLAYBOOKS, ids=lambda p: p.name)
def test_no_stale_config_references(playbook: pathlib.Path):
    content = playbook.read_text()
    stale = [p for p in STALE_PATTERNS if p in content]
    assert stale == [], f'{playbook.name} still references removed config: {stale}'
```

- [ ] **Step 2: Run to verify the reference guard fails**

Run: `uv run pytest tests/test_ansible_playbooks.py -v`
Expected: `test_no_stale_config_references` FAILS for `host_apply.yml`, `cluster_apply.yml`, `stack_apply.yml`, `helm_repackage.yml`; syntax checks PASS.

- [ ] **Step 3: Edit host_apply.yml**

Apply this mapping mechanically throughout the file, then the specific fixes below.

| Old expression | New expression |
|---|---|
| `host.postgresql.enabled` (when) | `infrastructure.postgresql.provider == 'local'` |
| `host.postgresql.<field>` | `infrastructure.postgresql.<field>` (same field names) |
| `host.postgresql.name }}.{{ host.dns.zone` (FQDN concatenations) | `infrastructure.postgresql.client_host` |
| `host.idp.enabled` (when) | `infrastructure.idp.provider == 'local'` |
| `host.idp.<field>` | `infrastructure.idp.<field>` |
| `host.idp.name }}.{{ host.dns.zone` | the literal `{{ infrastructure.idp.name }}.{{ host.dns.zone }}` stays only inside cert SANs/aliases; for URLs use `infrastructure.idp.url` |
| `host.s3.enabled` / `host.s3.<field>` | `infrastructure.s3.provider == 'local'` / `infrastructure.s3.<field>` |
| `host.registry.enabled` / `host.registry.<field>` | `infrastructure.registry.provider == 'local'` / `infrastructure.registry.<field>` |

Specific edits (line numbers from the pre-plan file):

1. Line 63–64 (extra CA bug fix):
```yaml
    - name: Append any extra CA certificates to the trust store
      when: host.pki.extra_ca_path
```

2. Line 154 — give the PostgreSQL container both aliases:
```yaml
        networks:
        - name: kind
          aliases:
          - "{{ infrastructure.postgresql.name }}"
          - "{{ infrastructure.postgresql.client_host }}"
```

3. Lines 155–157 — superuser from config:
```yaml
        env:
          POSTGRES_USER: "{{ infrastructure.postgresql.admin_user }}"
          POSTGRES_PASSWORD: "{{ infrastructure.postgresql.admin_password }}"
          PGDATA: /var/lib/postgresql/data
```

4. PostgreSQL DNS record (171–172): `dns_record: "{{ infrastructure.postgresql.client_host }}."`, `dns_value: "{{ infrastructure.postgresql.host_ip }}"`.

5. IdP DB user/database creation (183–206) — admin connection from infra, **db_password bug fix**:
```yaml
    - name: Create a user for the IdP in PostgreSQL
      community.postgresql.postgresql_user:
        login_host: "{{ infrastructure.postgresql.admin_host }}"
        login_port: "{{ infrastructure.postgresql.admin_port | int }}"
        login_user: "{{ infrastructure.postgresql.admin_user }}"
        login_password: "{{ infrastructure.postgresql.admin_password }}"
        login_db: postgres
        name: "{{ infrastructure.idp.db_user }}"
        password: "{{ infrastructure.idp.db_password }}"
        comment: "IDP DB User"
        state: present
      environment:
        PGOPTIONS: "-c password_encryption=scram-sha-256"
```
(the `postgresql_db` task analogously: `login_*` from `infrastructure.postgresql.admin_*`, `name`/`owner` from `infrastructure.idp.db_name`/`db_user`)

6. IdP container env (252–288) — **KC_DB_URL_HOST hardcode fix** and credential/URL wiring:
```yaml
          KC_BOOTSTRAP_ADMIN_USERNAME: "{{ infrastructure.idp.admin_user }}"
          KC_BOOTSTRAP_ADMIN_PASSWORD: "{{ infrastructure.idp.admin_password }}"
          KC_DB_URL_HOST: "{{ infrastructure.postgresql.client_host }}"
          KC_DB_URL_PORT: "{{ infrastructure.postgresql.client_port }}"
          KC_HOSTNAME: "{{ infrastructure.idp.url }}/"
```
(all other `KC_*` lines keep their current values with the mechanical `host.idp.*` → `infrastructure.idp.*` rename)

7. S3 container env (362–366):
```yaml
        env:
          RUSTFS_ACCESS_KEY: "{{ infrastructure.s3.access_key }}"
          RUSTFS_SECRET_KEY: "{{ infrastructure.s3.secret_key }}"
          RUSTFS_CONSOLE_ENABLE: "true"
          RUSTFS_TLS_PATH: "/opt/tls/"
```

8. "Stop … if now disabled" blocks (174, 306, 384, 441, 526): change `when: host.<svc>.enabled == false` to `when: infrastructure.<svc>.provider != 'local'` (for kafka keep `host.kafka.enabled == false`). Also fix the copy-paste name at line 441: `- name: Stop the local Kafka instance, if now disabled`.

9. Infra DNS-record tasks (PostgreSQL/IdP/S3/registry) stay inside their `provider == 'local'` blocks — remote infrastructure manages its own DNS.

- [ ] **Step 4: Run the harness**

Run: `uv run pytest tests/test_ansible_playbooks.py -v -k 'host_apply'`
Expected: syntax PASS; stale-reference PASS for host_apply.yml (other playbooks still fail — expected until Tasks 6–7).

Also run: `grep -n 'host\.postgresql\|host\.idp\|host\.s3\|host\.registry' src/kube_eng/ansible/project/host_apply.yml`
Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add src/kube_eng/ansible/project/host_apply.yml tests/test_ansible_playbooks.py
git commit -m "refactor(ansible): host_apply consumes infrastructure section; fix IdP DB password and extra-CA bugs"
```

---

### Task 6: Migrate cluster_apply.yml and helm_repackage.yml

**Files:**
- Modify: `src/kube_eng/ansible/project/cluster_apply.yml`
- Modify: `src/kube_eng/ansible/project/helm_repackage.yml`

**Interfaces:**
- Consumes: `infrastructure.idp.url/realm/admin_user/admin_password/issuer_url`, `infrastructure.registry.url/https_url`, `infrastructure.postgresql.client_host/client_port`, `infrastructure.s3.endpoint`.
- Produces: keycloak `module_defaults` pattern reused verbatim in Task 7.

- [ ] **Step 1: Add keycloak module_defaults to the play**

In `cluster_apply.yml`, the second play header (line 6–8) becomes:

```yaml
- name: (Re-)package and publish the Helm charts
  hosts: localhost
  module_defaults:
    community.general.keycloak_clientscope: &keycloak_auth
      auth_keycloak_url: "{{ infrastructure.idp.url }}"
      auth_realm: "{{ infrastructure.idp.realm }}"
      auth_username: "{{ infrastructure.idp.admin_user }}"
      auth_password: "{{ infrastructure.idp.admin_password }}"
      validate_certs: true
    community.general.keycloak_client: *keycloak_auth
    community.general.keycloak_role: *keycloak_auth
    community.general.keycloak_user: *keycloak_auth
    community.general.keycloak_user_rolemapping: *keycloak_auth
  tasks:
```

Then delete the five lines `auth_keycloak_url:`, `auth_realm: master`, `auth_username: admin`, `auth_password: …`, `validate_certs: true` from every `community.general.keycloak_*` task in this file. In `keycloak_user` and `keycloak_user_rolemapping` tasks, change the separate `realm: master` parameter to `realm: "{{ infrastructure.idp.realm }}"`.

- [ ] **Step 2: Registry, OIDC, and ServiceEntry references**

1. All `{{ cluster.registry.url }}` → `{{ infrastructure.registry.url }}` (lines 292, 319, 437, 476, 520); line 18: `chart_registry_url: "{{ infrastructure.registry.url }}/kube-eng"` (no trailing slash). Line 159: `airgap_registry_url: "{{ infrastructure.registry.https_url }}"`.
2. Line 163: `oidc_discovery_url: "{{ infrastructure.idp.issuer_url }}/.well-known/openid-configuration"`.
3. ServiceEntries (331–399): remove the `when: host.<svc>.enabled` conditions on the PostgreSQL/IdP/S3 blocks (core infra is always present) and reference the connectivity view; keep the Kafka block gated on `host.kafka.enabled`:
   - PG: `hosts: ["{{ infrastructure.postgresql.client_host }}"]`, port `number: "{{ infrastructure.postgresql.client_port | int }}"`
   - IdP: `hosts: ["{{ infrastructure.idp.url | urlsplit('hostname') }}"]`, port `number: "{{ infrastructure.idp.url | urlsplit('port') | default(443, true) | int }}"`
   - S3: `hosts: ["{{ infrastructure.s3.endpoint | urlsplit('hostname') }}"]`, port `number: "{{ infrastructure.s3.endpoint | urlsplit('port') | default(443, true) | int }}"`

- [ ] **Step 3: Run the harness**

Run: `uv run pytest tests/test_ansible_playbooks.py -v -k 'cluster_apply or helm_repackage'`
Expected: PASS (both tests, both files).

- [ ] **Step 4: Commit**

```bash
git add src/kube_eng/ansible/project/cluster_apply.yml src/kube_eng/ansible/project/helm_repackage.yml
git commit -m "refactor(ansible): cluster_apply/helm_repackage consume infrastructure; keycloak module_defaults"
```

---

### Task 7: Migrate stack_apply.yml

**Files:**
- Modify: `src/kube_eng/ansible/project/stack_apply.yml`

**Interfaces:**
- Consumes: same infrastructure views as Task 6, plus `stack.grafana.db_host/db_port/db_password/client_secret`, `stack.kiali.client_secret`, `infrastructure.s3.admin_endpoint/access_key/secret_key/region`.
- Produces: Grafana chart values keyed the way the chart actually reads them (`integration.database.kind/host/port`).

- [ ] **Step 1: Keycloak module_defaults**

Add the same `module_defaults` block as Task 6 Step 1 to the play header (modules used here: `keycloak_clientscope`, `keycloak_client`, `keycloak_role`), and strip the per-task `auth_*`/`validate_certs` lines.

- [ ] **Step 2: Apply the reference migration**

1. All `{{ cluster.registry.url }}` → `{{ infrastructure.registry.url }}` (lines 40, 198, 258, 265, 323, 330, 386, 529).
2. Grafana OIDC values (216–220):
```yaml
            oauth:
              clientId: "{{ stack.grafana.client_id }}"
              clientSecret: "{{ stack.grafana.client_secret }}"
              authUrl: "{{ infrastructure.idp.issuer_url }}/protocol/openid-connect/auth"
              tokenUrl: "{{ infrastructure.idp.issuer_url }}/protocol/openid-connect/token"
              apiUrl: "{{ infrastructure.idp.issuer_url }}/protocol/openid-connect/userinfo"
```
Also `secret: "{{ stack.grafana.client_secret }}"` in the `Register Grafana in Keycloak` task (line 119).
3. Grafana DB provisioning (167–192) — admin connection from infra, **owner bug fix**:
```yaml
    - when: stack.grafana.db_kind == "postgres"
      block:
      - name: Create a user for Grafana in PostgreSQL
        community.postgresql.postgresql_user:
          login_host: "{{ infrastructure.postgresql.admin_host }}"
          login_port: "{{ infrastructure.postgresql.admin_port | int }}"
          login_user: "{{ infrastructure.postgresql.admin_user }}"
          login_password: "{{ infrastructure.postgresql.admin_password }}"
          login_db: postgres
          name: "{{ stack.grafana.db_user }}"
          password: "{{ stack.grafana.db_password }}"
          comment: "Grafana DB User"
          state: present
        environment:
          PGOPTIONS: "-c password_encryption=scram-sha-256"
      - name: Create a database for Grafana in PostgreSQL
        community.postgresql.postgresql_db:
          login_host: "{{ infrastructure.postgresql.admin_host }}"
          login_port: "{{ infrastructure.postgresql.admin_port | int }}"
          login_user: "{{ infrastructure.postgresql.admin_user }}"
          login_password: "{{ infrastructure.postgresql.admin_password }}"
          name: "{{ stack.grafana.db_name }}"
          owner: "{{ stack.grafana.db_user }}"
          comment: "Grafana Database"
          encoding: UTF-8
          state: present
```
4. Grafana chart database values (221–227) — **align to the keys the template reads** (`grafana.yaml` uses `integration.database.kind`, `host`, `port` separately; the current playbook passes `type` and a combined `host:port`, which the template ignores):
```yaml
            database:
              kind: "{{ stack.grafana.db_kind }}"
              host: "{{ stack.grafana.db_host }}"
              port: "{{ stack.grafana.db_port | int }}"
              name: "{{ stack.grafana.db_name }}"
              user: "{{ stack.grafana.db_user }}"
              password: "{{ stack.grafana.db_password }}"
              ssl_mode: "{{ stack.grafana.db_ssl_mode }}"
```
5. S3 buckets (Loki 299–306, Tempo 367–374):
```yaml
      s3_bucket:
        admin_access_key: "{{ infrastructure.s3.access_key }}"
        admin_secret_key: "{{ infrastructure.s3.secret_key }}"
        s3_endpoint: "{{ infrastructure.s3.admin_endpoint }}"
        truststore_path: "{{ host.pki.ca_truststore_path }}"
```
6. Loki chart storage values (342–346):
```yaml
              storage:
                s3:
                  endpoint: "{{ infrastructure.s3.endpoint }}"
                  accessKeyId: "{{ infrastructure.s3.access_key }}"
                  secretAccessKey: "{{ infrastructure.s3.secret_key }}"
```
7. Tempo chart storage values (401–410):
```yaml
                trace:
                  backend: s3
                  s3:
                    endpoint: "{{ infrastructure.s3.endpoint | regex_replace('^https?://', '') }}"
                    access_key: "{{ infrastructure.s3.access_key }}"
                    secret_key: "{{ infrastructure.s3.secret_key }}"
                    region: "{{ infrastructure.s3.region }}"
                    insecure: false
                    tls_insecure_skip_verify: true
```
8. Kiali: `secret: "{{ stack.kiali.client_secret }}"` (line 465), `oidc-secret: "{{ stack.kiali.client_secret }}"` (line 511), `issuer_uri: "{{ infrastructure.idp.issuer_url }}"` (line 545), Grafana `external_url: "https://{{ stack.grafana.hostname }}.{{ host.dns.zone }}/"` (line 552, drops the stray `{{ cluster.name }}` segment).
9. Alloy DNS record fix (line 293): `dns_record: "{{ stack.alloy.hostname }}.{{ host.dns.zone }}."`.

- [ ] **Step 3: Run the full harness and test suite**

Run: `uv run pytest tests/ -v`
Expected: all PASS, including `test_no_stale_config_references` for every playbook.

- [ ] **Step 4: Commit**

```bash
git add src/kube_eng/ansible/project/stack_apply.yml
git commit -m "refactor(ansible): stack_apply consumes infrastructure; fix Grafana DB owner and chart value keys"
```

---

### Task 8: Helm render tests, chart default cleanup, docs

**Files:**
- Create: `tests/test_helm_charts.py`
- Create: `tests/helm_values/kube-eng-grafana.postgres.yaml`, `tests/helm_values/kube-eng-loki.s3.yaml`, `tests/helm_values/kube-eng-tempo.s3.yaml`
- Modify: `src/kube_eng/helm/kube-eng-loki/values.yaml`, `src/kube_eng/helm/kube-eng-tempo/values.yaml`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: chart value keys as passed by the migrated playbooks (Task 7).
- Produces: render regression coverage for every chart plus the two remote-relevant scenarios.

- [ ] **Step 1: Write the render tests**

Create `tests/test_helm_charts.py`:

```python
"""
Helm chart render regression tests. Requires the helm binary; skipped otherwise.
"""

import pathlib
import shutil
import subprocess

import pytest

HELM = shutil.which('helm')
CHART_ROOT = pathlib.Path(__file__).parent.parent / 'src' / 'kube_eng' / 'helm'
CHARTS = sorted(p for p in CHART_ROOT.iterdir() if (p / 'Chart.yaml').exists())
VALUES_ROOT = pathlib.Path(__file__).parent / 'helm_values'
SCENARIOS = sorted(VALUES_ROOT.glob('*.yaml'))

pytestmark = pytest.mark.skipif(HELM is None, reason='helm binary not available')


def _ensure_dependencies(chart: pathlib.Path) -> None:
    if (chart / 'Chart.lock').exists() and not (chart / 'charts').exists():
        result = subprocess.run(
            [HELM, 'dependency', 'build', str(chart)], capture_output=True, text=True
        )
        if result.returncode != 0:
            pytest.skip(f'cannot build dependencies for {chart.name}: {result.stderr}')


def _template(chart: pathlib.Path, *values_files: pathlib.Path) -> str:
    _ensure_dependencies(chart)
    cmd = [HELM, 'template', 'test', str(chart)]
    for values_file in values_files:
        cmd += ['-f', str(values_file)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout


@pytest.mark.parametrize('chart', CHARTS, ids=lambda p: p.name)
def test_chart_renders_with_defaults(chart: pathlib.Path):
    _template(chart)


@pytest.mark.parametrize('values_file', SCENARIOS, ids=lambda p: p.name)
def test_chart_renders_scenario(values_file: pathlib.Path):
    chart = CHART_ROOT / values_file.name.split('.')[0]
    _template(chart, values_file)


def test_grafana_postgres_scenario_reaches_config():
    rendered = _template(
        CHART_ROOT / 'kube-eng-grafana',
        VALUES_ROOT / 'kube-eng-grafana.postgres.yaml',
    )
    assert 'type: postgres' in rendered
    assert 'pg.central.example.com:5432' in rendered
```

Create `tests/helm_values/kube-eng-grafana.postgres.yaml` (mirrors what `stack_apply.yml` passes for a remote PostgreSQL):

```yaml
integration:
  adminUser: admin
  adminPassword: test-admin
  rootUrl: https://grafana.testcluster.k8s/
  oauth:
    clientId: kube-eng-grafana
    clientSecret: test-secret
    authUrl: https://idp.central.example.com/realms/kube-eng/protocol/openid-connect/auth
    tokenUrl: https://idp.central.example.com/realms/kube-eng/protocol/openid-connect/token
    apiUrl: https://idp.central.example.com/realms/kube-eng/protocol/openid-connect/userinfo
  database:
    kind: postgres
    host: pg.central.example.com
    port: 5432
    name: grafana
    user: grafana
    password: test-db-secret
    ssl_mode: require
```

Create `tests/helm_values/kube-eng-loki.s3.yaml`:

```yaml
loki:
  loki:
    storage:
      s3:
        endpoint: https://s3.central.example.com
        accessKeyId: ak
        secretAccessKey: sk
```

Create `tests/helm_values/kube-eng-tempo.s3.yaml`:

```yaml
tempo:
  tempo:
    storage:
      trace:
        backend: s3
        s3:
          endpoint: s3.central.example.com
          access_key: ak
          secret_key: sk
          region: us-east-1
```

- [ ] **Step 2: Run and fix what falls out**

Run: `uv run pytest tests/test_helm_charts.py -v`
Expected: scenario tests PASS. If a default-render test fails, the failure output names the broken template — fix the chart default (not the test) and re-run. Known cleanups to apply regardless:
- `src/kube_eng/helm/kube-eng-loki/values.yaml`: `endpoint: https://s3:9000` → `endpoint: https://s3.invalid:9000`
- `src/kube_eng/helm/kube-eng-tempo/values.yaml` line 33: `endpoint: "https://s3.kind:9000"` → `endpoint: "s3.invalid:9000"`

(`.invalid` is an RFC 2606 reserved TLD: defaults render but can never silently connect anywhere if the playbook forgets to override them.)

- [ ] **Step 3: Update CLAUDE.md**

In the Architecture → Configuration Model section, update the `RootConfig` bullet list: remove registry/postgres/minio mentions from `host`, and add:

```markdown
  - `infrastructure: InfrastructureConfig` — core services the cluster depends on (PostgreSQL, IdP, S3, OCI registry). Each is a discriminated union on `provider`: `local` provisions a Docker container and computes its connectivity; `remote` requires endpoint + admin credentials for centrally hosted infrastructure. Consumers (IdP DB, Grafana DB, OIDC issuer, chart refs) read the computed `client_*`/`admin_*`/`url` views via `_root_config` — never duplicate endpoints or credentials in consumer configs.
```

Also add to the Development Commands section:

```markdown
# Regenerate the extravars golden files after intentional config-model changes
UPDATE_GOLDEN=1 uv run pytest tests/test_extravars_contract.py
```

- [ ] **Step 4: Full suite, lint, commit**

```bash
uv run pytest tests/ -v
uv run ruff format src/ tests/ && uv run ruff check src/ && uv run pyrefly check
git add tests/test_helm_charts.py tests/helm_values/ src/kube_eng/helm/kube-eng-loki/values.yaml src/kube_eng/helm/kube-eng-tempo/values.yaml CLAUDE.md
git commit -m "test(helm): render regression tests per scenario; neutralize local-infra chart defaults"
```

---

## Follow-ups (explicitly not in this plan)

- TUI migration to the `infrastructure` section (`config_tab.py` forms).
- Kafka and DNS as `local | remote` unions (same pattern).
- Inject the cluster CA into Loki/Tempo S3 clients and drop `insecure_skip_verify` / `tls_insecure_skip_verify`.
- Remote-registry credential fields if out-of-band `helm registry login` proves insufficient.
- `argument_specs` for the Ansible roles (use the `mrmat-ansible-role` skill) and a check-mode playbook tier.
- One slow end-to-end smoke: provision containers outside kube-eng, configure kube-eng in remote mode against them.
