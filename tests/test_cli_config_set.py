"""
Unit tests for the `config set` CLI command, particularly its handling of
discriminated union fields (e.g. infra.dns.provider: local <-> remote).
"""

import argparse
import asyncio
import pathlib

from kube_eng.cli.main import config_set
from kube_eng.config import RootConfig
from kube_eng.config.infra_dns_config import LocalDNSConfig, RemoteDNSConfig
from kube_eng.config.infra_pg_config import RemotePGConfig


def make_config(tmp_path: pathlib.Path, **infrastructure) -> RootConfig:
    return RootConfig(
        config_path=tmp_path,
        admin_password='test-admin',
        cluster={'name': 'testcluster'},
        infra=infrastructure,
    )


def _set(config: RootConfig, key: str, value: str) -> int:
    return asyncio.run(config_set(config, argparse.Namespace(key=key, value=value)))


def test_switching_provider_revalidates_the_whole_union_member(
    tmp_path: pathlib.Path,
):
    config = make_config(tmp_path)
    assert isinstance(config.infra.dns, LocalDNSConfig)

    rc = _set(config, 'infra.dns.provider', 'remote')

    assert rc == 0
    assert isinstance(config.infra.dns, RemoteDNSConfig)
    assert config.infra.dns.provider == 'remote'
    # The new instance needs a working root-config back-reference, or a
    # computed field that depends on it (e.g. `domain`) blows up on the next
    # access or save.
    assert config.infra.dns._root_config is config


def test_switching_provider_defaults_fields_it_does_not_have_yet(
    tmp_path: pathlib.Path,
):
    config = make_config(tmp_path)

    rc = _set(config, 'infra.pg.provider', 'remote')

    assert rc == 0
    assert isinstance(config.infra.pg, RemotePGConfig)
    # fqdn only exists on RemotePGConfig; the switch must seed a placeholder
    # rather than fail, so the user can fix it up with a follow-up `set`.
    assert config.infra.pg.fqdn == 'change-me.example.com'
    # Fields the local config already had a real value for (not just a
    # default) are carried over rather than clobbered with a placeholder.
    assert config.infra.pg.admin_user == 'postgres'


def test_the_placeholder_can_be_overwritten_afterwards(tmp_path: pathlib.Path):
    config = make_config(tmp_path)
    _set(config, 'infra.pg.provider', 'remote')

    rc = _set(config, 'infra.pg.fqdn', 'pg.central.example.com')

    assert rc == 0
    assert config.infra.pg.fqdn == 'pg.central.example.com'


def test_switching_to_an_unknown_provider_still_fails_cleanly(
    tmp_path: pathlib.Path,
):
    config = make_config(tmp_path)

    rc = _set(config, 'infra.pg.provider', 'bogus')

    assert rc == 1
    assert config.infra.pg.provider == 'local'


def test_switching_provider_persists_across_a_reload(tmp_path: pathlib.Path):
    config = make_config(tmp_path)
    _set(config, 'infra.dns.provider', 'remote')

    reloaded = RootConfig.load(config_path=tmp_path)

    assert isinstance(reloaded.infra.dns, RemoteDNSConfig)


def test_setting_a_plain_field_still_works(tmp_path: pathlib.Path):
    config = make_config(tmp_path)

    rc = _set(config, 'infra.pg.admin_user', 'someone-else')

    assert rc == 0
    assert config.infra.pg.admin_user == 'someone-else'


def test_setting_a_whole_object_is_still_rejected(tmp_path: pathlib.Path):
    config = make_config(tmp_path)

    rc = _set(config, 'infra.pg', 'localhost')

    assert rc == 1
