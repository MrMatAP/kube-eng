"""
TUI ConfigTab smoke tests.

Textual's compose()/on_mount()/apply_configuration() only execute inside a
running App -- a plain `import` never reaches the query_one() calls that
reference widget ids or config attributes, so an import passing proves
nothing about this file. run_test() mounts the real app and drives it with
a Pilot, which is the only way to catch a stale widget id or a config
attribute that moved (e.g. host.registry -> infra.registry).
"""

import pathlib

import pytest
from kube_eng.config import RootConfig
from kube_eng.tui.main import KubeEngApp
from textual.widgets import Button


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.mark.anyio
async def test_mount_and_apply_round_trips_defaults(tmp_path: pathlib.Path):
    """Mounting populates every field; applying without changing anything
    must save a config that RootConfig.load() accepts back."""
    config = RootConfig(config_path=tmp_path)
    app = KubeEngApp(config)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one('#apply_configuration', Button).press()
        await pilot.pause()

    # Re-load from disk: proves apply_configuration() produced a valid,
    # persisted config rather than raising or writing something broken.
    reloaded = RootConfig.load(config_path=tmp_path)
    assert reloaded.cluster.name == config.cluster.name
    assert reloaded.infra.dns.provider == 'local'


@pytest.mark.anyio
async def test_switch_registry_provider_to_remote(tmp_path: pathlib.Path):
    """Flipping a provider Select to 'remote' and filling in the
    newly-required field must produce a config that round-trips."""
    from textual.widgets import Select

    config = RootConfig(config_path=tmp_path)
    app = KubeEngApp(config)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one('#infra_registry_provider', Select).value = 'remote'
        await pilot.pause()
        app.query_one('#infra_registry_url').value = 'oci://harbor.example.com/kube-eng'
        app.query_one('#apply_configuration', Button).press()
        await pilot.pause()

    reloaded = RootConfig.load(config_path=tmp_path)
    assert reloaded.infra.registry.provider == 'remote'
    assert str(reloaded.infra.registry.url) == 'oci://harbor.example.com/kube-eng'


@pytest.mark.anyio
@pytest.mark.parametrize(
    ('key', 'remote_field', 'remote_value'),
    [
        ('dns', None, None),
        ('pg', 'fqdn', 'pg.central.example.com'),
        ('idp', 'url', 'https://idp.central.example.com/'),
        ('s3', 'url', 'https://s3.central.example.com/'),
        ('kafka', 'endpoint', 'https://kafka.central.example.com/'),
    ],
)
async def test_switch_infra_provider_to_remote(
    tmp_path: pathlib.Path, key: str, remote_field: str | None, remote_value: str | None
):
    """Every infra.<key> discriminated union must switch cleanly, not just
    registry -- this is the exact family of bug the rewrite targets."""
    from textual.widgets import Select

    config = RootConfig(config_path=tmp_path)
    app = KubeEngApp(config)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one(f'#infra_{key}_provider', Select).value = 'remote'
        await pilot.pause()
        if remote_field is not None:
            app.query_one(f'#infra_{key}_{remote_field}').value = remote_value
        app.query_one('#apply_configuration', Button).press()
        await pilot.pause()

    reloaded = RootConfig.load(config_path=tmp_path)
    assert getattr(reloaded.infra, key).provider == 'remote'


@pytest.mark.anyio
async def test_sidebar_navigation_reveals_section(tmp_path: pathlib.Path):
    """Selecting a sidebar entry must expand its Collapsible without error."""
    from textual.widgets import Collapsible

    config = RootConfig(config_path=tmp_path)
    app = KubeEngApp(config)
    async with app.run_test() as pilot:
        await pilot.pause()
        collapsible = app.query_one('#section-infra-registry', Collapsible)
        assert collapsible.collapsed
        app.query_one('#sidebar-nav').post_message(
            app.query_one('ConfigSidebar').SectionSelected('infra-registry')
        )
        await pilot.pause()
        assert not collapsible.collapsed


@pytest.mark.anyio
async def test_apply_with_invalid_value_leaves_config_untouched(
    tmp_path: pathlib.Path,
):
    """A bad value must notify, not crash, and must not corrupt the saved
    config -- validate_assignment turned this from a silent write into a
    raise, so Apply must catch it."""
    config = RootConfig(config_path=tmp_path)
    app = KubeEngApp(config)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one('#cluster_worker_nodes').value = 'not-a-number'
        app.query_one('#apply_configuration', Button).press()
        await pilot.pause()

    # No config.yaml should have been written by the failed apply.
    assert not (tmp_path / 'config.yaml').exists()
