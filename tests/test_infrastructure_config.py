"""
Infrastructure configuration matrix tests
"""

import pathlib

import pytest
from kube_eng.config import RootConfig
from kube_eng.config.cluster_config import ClusterConfig
from kube_eng.config.infra_pg_config import LocalPGConfig
from pydantic import ValidationError


def make_config(tmp_path: pathlib.Path, **infrastructure) -> RootConfig:
    """Build a RootConfig with deterministic identity and the given infrastructure overrides."""
    return RootConfig(
        config_path=tmp_path,
        cluster=ClusterConfig(name='testcluster'),
        infra=infrastructure,
    )


def _url(value) -> str:
    """Compare pydantic Url objects/strings without tripping over pydantic's
    trailing-slash normalisation on URLs that have no explicit path."""
    return str(value).rstrip('/')


class TestPostgresql:
    def test_local_defaults(self, tmp_path: pathlib.Path):
        pg = make_config(tmp_path).infra.pg
        assert isinstance(pg, LocalPGConfig)
        assert pg.provider == 'local'
        assert pg.client_fqdn == 'pg.testcluster.k8s'
        assert pg.port == 5432
        assert str(pg.ip) == '127.0.0.1'
        assert pg.admin_db == 'postgres'
        assert pg.admin_user == 'postgres'
        assert pg.admin_password is not None

    def test_remote(self, tmp_path: pathlib.Path):
        pg = make_config(
            tmp_path,
            pg={
                'provider': 'remote',
                'fqdn': 'pg.central.example.com',
                'port': 5433,
                'admin_user': 'postgres',
                'admin_password': 'central-secret',
            },
        ).infra.pg
        assert pg.provider == 'remote'
        assert pg.client_fqdn == 'pg.central.example.com'
        assert pg.port == 5433
        assert pg.admin_user == 'postgres'
        assert pg.admin_password == 'central-secret'

    def test_remote_requires_fqdn(self, tmp_path: pathlib.Path):
        """fqdn is the only field a remote PostgreSQL has no default for --
        admin_user/admin_password/port/admin_db all fall back to the same
        defaults local uses."""
        with pytest.raises(ValidationError):
            make_config(tmp_path, pg={'provider': 'remote'})


class TestIdp:
    def test_local_defaults(self, tmp_path: pathlib.Path):
        idp = make_config(tmp_path).infra.idp
        assert idp.provider == 'local'
        assert _url(idp.client_base_url) == 'https://idp.testcluster.k8s:8443'
        assert _url(idp.issuer_url) == 'https://idp.testcluster.k8s:8443/realms/master'
        assert idp.admin_user == 'admin'
        assert idp.admin_password is not None
        assert idp.db_name == 'idp'
        assert idp.db_user == 'idp'
        assert idp.db_password is not None

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
        assert _url(idp.url) == 'https://idp.central.example.com'
        assert _url(idp.issuer_url) == 'https://idp.central.example.com/realms/kube-eng'

    def test_remote_requires_url(self, tmp_path: pathlib.Path):
        """url is the only field a remote IdP has no default for -- realm and
        admin credentials all fall back to the same defaults local uses."""
        with pytest.raises(ValidationError):
            make_config(tmp_path, idp={'provider': 'remote'})


class TestS3:
    def test_local_defaults(self, tmp_path: pathlib.Path):
        s3 = make_config(tmp_path).infra.s3
        assert s3.provider == 'local'
        assert _url(s3.endpoint) == 'https://s3.testcluster.k8s:9000'
        assert _url(s3.admin_endpoint) == 'https://s3.testcluster.k8s:9001'
        assert s3.access_key == 'admin'
        assert s3.secret_key is not None
        assert s3.region == 'us-east-1'

    def test_remote(self, tmp_path: pathlib.Path):
        s3 = make_config(
            tmp_path,
            s3={
                'provider': 'remote',
                'url': 'https://s3.central.example.com/',
                'access_key': 'ak',
                'secret_key': 'sk',
            },
        ).infra.s3
        assert _url(s3.endpoint) == 'https://s3.central.example.com'
        assert _url(s3.admin_endpoint) == 'https://s3.central.example.com'

    def test_remote_requires_url(self, tmp_path: pathlib.Path):
        """url is the only field a remote S3 has no default for --
        access_key/secret_key both fall back to the same defaults local uses."""
        with pytest.raises(ValidationError):
            make_config(tmp_path, s3={'provider': 'remote'})


class TestRegistry:
    def test_local_defaults(self, tmp_path: pathlib.Path):
        registry = make_config(tmp_path).infra.registry
        assert registry.provider == 'local'
        assert _url(registry.oci_endpoint) == 'oci://registry.testcluster.k8s:5001'
        assert _url(registry.http_endpoint) == 'https://registry.testcluster.k8s:5001'

    def test_local_push_account_is_generated(self, tmp_path: pathlib.Path):
        registry = make_config(tmp_path).infra.registry
        assert registry.admin_username == 'kube-eng'
        assert registry.admin_password  # generated

    def test_remote_push_account_is_supplied_not_generated(
        self, tmp_path: pathlib.Path
    ):
        registry = make_config(
            tmp_path,
            registry={
                'provider': 'remote',
                'url': 'oci://harbor.example.com/kube-eng',
                'admin_password': 'from-vault',
            },
        ).infra.registry
        assert registry.admin_username == 'kube-eng'
        assert registry.admin_password == 'from-vault'

    def test_remote(self, tmp_path: pathlib.Path):
        registry = make_config(
            tmp_path,
            registry={
                'provider': 'remote',
                'url': 'oci://harbor.example.com/kube-eng/',
            },
        ).infra.registry
        assert _url(registry.oci_endpoint) == 'oci://harbor.example.com/kube-eng'
        assert _url(registry.http_endpoint) == 'https://harbor.example.com/kube-eng'

    def test_remote_rejects_non_oci_url(self, tmp_path: pathlib.Path):
        with pytest.raises(ValidationError):
            make_config(
                tmp_path,
                registry={'provider': 'remote', 'url': 'https://harbor.example.com'},
            )
