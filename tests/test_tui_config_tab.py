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
from kube_eng.tui.config_tab import _SECTION_TARGETS, ConfigTab
from kube_eng.tui.main import KubeEngApp
from textual.widgets import Button, Collapsible, Select


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
        assert app.theme == 'kube-eng'
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
    ('key', 'remote_seed', 'local_default_name'),
    [
        ('dns', {}, 'dns'),
        ('pg', {'fqdn': 'pg.central.example.com'}, 'pg'),
        ('idp', {'url': 'https://idp.central.example.com/'}, 'idp'),
        ('s3', {'url': 'https://s3.central.example.com/'}, 's3'),
        ('registry', {'url': 'oci://harbor.example.com/kube-eng'}, 'registry'),
        ('kafka', {'endpoint': 'https://kafka.central.example.com/'}, 'kafka'),
    ],
)
async def test_switch_infra_provider_back_to_local(
    tmp_path: pathlib.Path, key: str, remote_seed: dict, local_default_name: str
):
    """The reverse switch (remote -> local) must also work for every
    resource: the remote variant has no ip/port/name/etc to show, so
    mounting fills those fields with '' -- collecting them anyway (without
    filling anything in) would send an empty string into IPvAnyAddress/int
    fields on the local variant and fail. _fill_provider_defaults exists
    to prefill those with the local class's own defaults instead."""
    config = RootConfig(
        config_path=tmp_path,
        infra={key: {'provider': 'remote', **remote_seed}},
    )
    config.save()

    app = KubeEngApp(RootConfig.load(config_path=tmp_path))
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one(f'#infra_{key}_provider', Select).value = 'local'
        await pilot.pause()
        app.query_one('#apply_configuration', Button).press()
        await pilot.pause()

    reloaded = RootConfig.load(config_path=tmp_path)
    switched = getattr(reloaded.infra, key)
    assert switched.provider == 'local'
    assert switched.name == local_default_name


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
@pytest.mark.parametrize('section_id', sorted(_SECTION_TARGETS))
async def test_sidebar_navigation_reveals_section(
    tmp_path: pathlib.Path, section_id: str
):
    """Every sidebar entry must resolve to a real widget id and, for a
    Collapsible target, expand it -- on_section_selected no longer
    swallows a bad id into a silent print(), so a typo in _SECTION_TARGETS
    now crashes the app instead."""
    from kube_eng.tui.widgets import ConfigSidebar

    config = RootConfig(config_path=tmp_path)
    app = KubeEngApp(config)
    async with app.run_test() as pilot:
        await pilot.pause()
        target_id = _SECTION_TARGETS[section_id]
        target = app.query_one(f'#{target_id}')
        was_collapsed = isinstance(target, Collapsible) and target.collapsed

        app.query_one('#sidebar-nav').post_message(
            ConfigSidebar.SectionSelected(section_id)
        )
        await pilot.pause()

        if was_collapsed:
            assert not target.collapsed


@pytest.mark.anyio
async def test_apply_with_invalid_value_leaves_config_untouched(
    tmp_path: pathlib.Path,
):
    """A bad value must notify, not crash, and must leave self._config
    exactly as it was -- validate_assignment turned this from a silent
    write into a raise, so Apply must catch it before committing anything,
    including sections that validated fine before the bad one."""
    config = RootConfig(config_path=tmp_path)
    app = KubeEngApp(config)
    async with app.run_test() as pilot:
        await pilot.pause()
        tab = app.query_one(ConfigTab)
        app.query_one('#cluster_worker_nodes').value = 'not-a-number'
        app.query_one('#apply_configuration', Button).press()
        await pilot.pause()

        # Not just "no file was written" (true even if Apply did nothing) --
        # the in-memory config, including sections validated before the bad
        # one, must be untouched by the failed, aborted commit.
        assert tab._config.cluster.worker_nodes == 3
        assert tab._config.infra.net.name == 'kind'

    assert not (tmp_path / 'config.yaml').exists()


@pytest.mark.anyio
async def test_apply_commits_top_level_and_nested_cluster_edits_together(
    tmp_path: pathlib.Path,
):
    """cluster (top-level scalars) is committed before cluster.cni/mesh/
    pki/edge specifically so a nested edit in the same Apply isn't
    clobbered by the stale cni/mesh/pki/edge snapshot carried inside the
    top-level rebuild. Edit one of each in a single Apply and check both
    land."""
    config = RootConfig(config_path=tmp_path)
    app = KubeEngApp(config)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one('#cluster_name').value = 'renamed-cluster'
        app.query_one('#cluster_cni_hostname').value = 'renamed-cni'
        app.query_one('#apply_configuration', Button).press()
        await pilot.pause()

    reloaded = RootConfig.load(config_path=tmp_path)
    assert reloaded.cluster.name == 'renamed-cluster'
    assert reloaded.cluster.cni.hostname == 'renamed-cni'
