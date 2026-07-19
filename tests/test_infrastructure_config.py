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
        infrastructure=infrastructure,
    )


class TestPostgresql:
    def test_local_defaults(self, tmp_path: pathlib.Path):
        pg = make_config(tmp_path).infrastructure.postgresql
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
        ).infrastructure.postgresql
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
        ).infrastructure.postgresql
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


class TestIdp:
    def test_local_defaults(self, tmp_path: pathlib.Path):
        idp = make_config(tmp_path).infrastructure.idp
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
        ).infrastructure.idp
        assert idp.url == 'https://idp.central.example.com'
        assert idp.issuer_url == 'https://idp.central.example.com/realms/kube-eng'

    def test_remote_requires_realm_and_credentials(self, tmp_path: pathlib.Path):
        with pytest.raises(ValidationError):
            make_config(
                tmp_path, idp={'provider': 'remote', 'url': 'https://idp.example.com'}
            )


class TestS3:
    def test_local_defaults(self, tmp_path: pathlib.Path):
        s3 = make_config(tmp_path).infrastructure.s3
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
        ).infrastructure.s3
        assert s3.endpoint == 'https://s3.central.example.com'
        assert s3.admin_endpoint == 'https://s3.central.example.com'

    def test_remote_requires_credentials(self, tmp_path: pathlib.Path):
        with pytest.raises(ValidationError):
            make_config(
                tmp_path,
                s3={'provider': 'remote', 'endpoint': 'https://s3.example.com'},
            )


class TestRegistry:
    def test_local_defaults(self, tmp_path: pathlib.Path):
        registry = make_config(tmp_path).infrastructure.registry
        assert registry.provider == 'local'
        assert registry.url == 'oci://registry.testcluster.k8s:5001'
        assert registry.https_url == 'https://registry.testcluster.k8s:5001'

    def test_remote(self, tmp_path: pathlib.Path):
        registry = make_config(
            tmp_path,
            registry={
                'provider': 'remote',
                'url': 'oci://harbor.example.com/kube-eng/',
            },
        ).infrastructure.registry
        assert registry.url == 'oci://harbor.example.com/kube-eng'
        assert registry.https_url == 'https://harbor.example.com/kube-eng'

    def test_remote_rejects_non_oci_url(self, tmp_path: pathlib.Path):
        with pytest.raises(ValidationError):
            make_config(
                tmp_path,
                registry={'provider': 'remote', 'url': 'https://harbor.example.com'},
            )
