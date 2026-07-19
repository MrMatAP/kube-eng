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
