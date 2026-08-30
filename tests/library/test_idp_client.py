"""
Unit tests for the idp_client Ansible module wrapper. IdPAdmin is mocked out
entirely, so these tests only pin the relay between Ansible task args and the
IdPAdmin/IdPClient calls -- no live IdP, no network.
"""

from unittest.mock import MagicMock

import pydantic
import pytest
from _ansible_harness import AnsibleExitJson, AnsibleFailJson, set_module_args
from kube_eng.ansible.project.library import idp_client

BASE_ARGS = {
    'idp_url': 'https://idp.kube-eng.test',
    'idp_admin_user': 'admin',
    'idp_admin_password': 'secret',
    'idp_realm': 'kube-eng',
    'idp_ca_path': '/tmp/ca.pem',
    'client_id': 's3-kube-eng',
}

PRESENT_ARGS = {
    **BASE_ARGS,
    'name': 'S3 :: kube-eng',
    'description': 'S3 instance on kube-eng',
    'root_url': 'https://s3.kube-eng.test',
    'state': 'present',
}


def _fake_admin(
    *, exists: bool = False, secret: pydantic.SecretStr | None = None
) -> MagicMock:
    admin = MagicMock()
    admin.client_exists.return_value = exists
    admin.client_create.return_value = MagicMock(
        client_id='s3-kube-eng', id='obj-1', secret=secret
    )
    return admin


def test_create_client_relays_roles_to_idp_admin(monkeypatch):
    set_module_args(
        {
            **PRESENT_ARGS,
            'roles': [
                {'name': 'kube-eng-s3-admin', 'description': 'Kube Eng :: S3 :: Admin'},
                {
                    'name': 'kube-eng-s3-viewer',
                    'description': 'Kube Eng :: S3 :: Viewer',
                },
            ],
        }
    )

    fake_admin = _fake_admin()
    monkeypatch.setattr(idp_client, 'IdPAdmin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleExitJson) as exc_info:
        idp_client.main()

    assert exc_info.value.kwargs['changed'] is True
    assert exc_info.value.kwargs['client_id'] == 's3-kube-eng'
    assert fake_admin.client_role_create.call_count == 2
    fake_admin.client_role_create.assert_any_call(
        fake_admin.client_create.return_value,
        role='kube-eng-s3-admin',
        description='Kube Eng :: S3 :: Admin',
    )
    fake_admin.client_role_create.assert_any_call(
        fake_admin.client_create.return_value,
        role='kube-eng-s3-viewer',
        description='Kube Eng :: S3 :: Viewer',
    )


def test_create_client_relays_callback_url_to_client_template(monkeypatch):
    set_module_args(
        {
            **PRESENT_ARGS,
            'callback_url': (
                'https://s3.kube-eng.test/rustfs/admin/v3/oidc/callback/default'
            ),
        }
    )

    fake_admin = _fake_admin()
    mock_idp_admin_cls = MagicMock(return_value=fake_admin)
    monkeypatch.setattr(idp_client, 'IdPAdmin', mock_idp_admin_cls)

    with pytest.raises(AnsibleExitJson):
        idp_client.main()

    mock_idp_admin_cls.client_template.assert_called_once_with(
        client_id='s3-kube-eng',
        name='S3 :: kube-eng',
        root_url='https://s3.kube-eng.test',
        description='S3 instance on kube-eng',
        callback_url='https://s3.kube-eng.test/rustfs/admin/v3/oidc/callback/default',
        redirect_uris=None,
        public_client=False,
        pkce_enabled=True,
        flows=[],
        audience=None,
    )


def test_create_client_defaults_callback_url_to_none(monkeypatch):
    set_module_args(PRESENT_ARGS)

    fake_admin = _fake_admin()
    mock_idp_admin_cls = MagicMock(return_value=fake_admin)
    monkeypatch.setattr(idp_client, 'IdPAdmin', mock_idp_admin_cls)

    with pytest.raises(AnsibleExitJson):
        idp_client.main()

    assert mock_idp_admin_cls.client_template.call_args.kwargs['callback_url'] is None


def test_create_client_relays_redirect_uris_and_public_client_to_client_template(
    monkeypatch,
):
    set_module_args(
        {
            **PRESENT_ARGS,
            'redirect_uris': ['http://localhost:8000', 'http://localhost:18000'],
            'public_client': True,
        }
    )

    fake_admin = _fake_admin()
    mock_idp_admin_cls = MagicMock(return_value=fake_admin)
    monkeypatch.setattr(idp_client, 'IdPAdmin', mock_idp_admin_cls)

    with pytest.raises(AnsibleExitJson):
        idp_client.main()

    mock_idp_admin_cls.client_template.assert_called_once_with(
        client_id='s3-kube-eng',
        name='S3 :: kube-eng',
        root_url='https://s3.kube-eng.test',
        description='S3 instance on kube-eng',
        callback_url=None,
        redirect_uris=['http://localhost:8000', 'http://localhost:18000'],
        public_client=True,
        pkce_enabled=True,
        flows=[],
        audience=None,
    )


def test_create_client_defaults_public_client_to_false(monkeypatch):
    set_module_args(PRESENT_ARGS)

    fake_admin = _fake_admin()
    mock_idp_admin_cls = MagicMock(return_value=fake_admin)
    monkeypatch.setattr(idp_client, 'IdPAdmin', mock_idp_admin_cls)

    with pytest.raises(AnsibleExitJson):
        idp_client.main()

    assert mock_idp_admin_cls.client_template.call_args.kwargs['public_client'] is False


def test_create_client_defaults_pkce_enabled_to_true(monkeypatch):
    set_module_args(PRESENT_ARGS)

    fake_admin = _fake_admin()
    mock_idp_admin_cls = MagicMock(return_value=fake_admin)
    monkeypatch.setattr(idp_client, 'IdPAdmin', mock_idp_admin_cls)

    with pytest.raises(AnsibleExitJson):
        idp_client.main()

    assert mock_idp_admin_cls.client_template.call_args.kwargs['pkce_enabled'] is True


def test_create_client_relays_pkce_enabled_false_to_client_template(monkeypatch):
    set_module_args({**PRESENT_ARGS, 'pkce_enabled': False})

    fake_admin = _fake_admin()
    mock_idp_admin_cls = MagicMock(return_value=fake_admin)
    monkeypatch.setattr(idp_client, 'IdPAdmin', mock_idp_admin_cls)

    with pytest.raises(AnsibleExitJson):
        idp_client.main()

    assert mock_idp_admin_cls.client_template.call_args.kwargs['pkce_enabled'] is False


def test_create_client_defaults_flows_to_empty(monkeypatch):
    """Standard flow is always on inside client_template and isn't a
    choice here -- a plain client gets an empty flows list, i.e. nothing
    beyond standard flow."""
    set_module_args(PRESENT_ARGS)

    fake_admin = _fake_admin()
    mock_idp_admin_cls = MagicMock(return_value=fake_admin)
    monkeypatch.setattr(idp_client, 'IdPAdmin', mock_idp_admin_cls)

    with pytest.raises(AnsibleExitJson):
        idp_client.main()

    assert mock_idp_admin_cls.client_template.call_args.kwargs['flows'] == []


def test_create_client_relays_flows_to_client_template(monkeypatch):
    set_module_args({**PRESENT_ARGS, 'flows': ['direct_access_grants']})

    fake_admin = _fake_admin()
    mock_idp_admin_cls = MagicMock(return_value=fake_admin)
    monkeypatch.setattr(idp_client, 'IdPAdmin', mock_idp_admin_cls)

    with pytest.raises(AnsibleExitJson):
        idp_client.main()

    assert mock_idp_admin_cls.client_template.call_args.kwargs['flows'] == [
        'direct_access_grants'
    ]


def test_create_client_defaults_audience_to_none(monkeypatch):
    set_module_args(PRESENT_ARGS)

    fake_admin = _fake_admin()
    mock_idp_admin_cls = MagicMock(return_value=fake_admin)
    monkeypatch.setattr(idp_client, 'IdPAdmin', mock_idp_admin_cls)

    with pytest.raises(AnsibleExitJson):
        idp_client.main()

    assert mock_idp_admin_cls.client_template.call_args.kwargs['audience'] is None


def test_create_client_relays_audience_to_client_template(monkeypatch):
    set_module_args({**PRESENT_ARGS, 'audience': 'registry-kube-eng'})

    fake_admin = _fake_admin()
    mock_idp_admin_cls = MagicMock(return_value=fake_admin)
    monkeypatch.setattr(idp_client, 'IdPAdmin', mock_idp_admin_cls)

    with pytest.raises(AnsibleExitJson):
        idp_client.main()

    assert (
        mock_idp_admin_cls.client_template.call_args.kwargs['audience']
        == 'registry-kube-eng'
    )


def test_create_client_rejects_an_unknown_flow(monkeypatch):
    """Ansible's own choices validation on the 'flows' arg_spec should
    reject this before client_template ever runs."""
    set_module_args({**PRESENT_ARGS, 'flows': ['bogus']})
    monkeypatch.setattr(idp_client, 'IdPAdmin', MagicMock())

    with pytest.raises(AnsibleFailJson):
        idp_client.main()


def test_create_client_reports_unchanged_for_an_already_existing_client(monkeypatch):
    """This is the crux of idempotency: re-running against a client that's
    already there must report changed=False, not silently claim it created
    something it didn't."""
    set_module_args(PRESENT_ARGS)

    fake_admin = _fake_admin(exists=True)
    monkeypatch.setattr(idp_client, 'IdPAdmin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleExitJson) as exc_info:
        idp_client.main()

    assert exc_info.value.kwargs['changed'] is False
    assert exc_info.value.kwargs['msg'] == 'Client already exists'


def test_create_client_reports_changed_for_a_new_client(monkeypatch):
    set_module_args(PRESENT_ARGS)

    fake_admin = _fake_admin(exists=False)
    monkeypatch.setattr(idp_client, 'IdPAdmin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleExitJson) as exc_info:
        idp_client.main()

    assert exc_info.value.kwargs['changed'] is True
    assert exc_info.value.kwargs['msg'] == 'Created client'


def test_create_client_returns_the_real_client_secret_unmangled(monkeypatch):
    """The secret must come back verbatim -- it must NOT be registered in
    module.no_log_values, since that scrubs matching values from this same
    module's JSON result (replacing it with the literal string
    'VALUE_SPECIFIED_IN_NO_LOG_PARAMETER'), corrupting the very value the
    playbook registers this task to consume downstream."""
    set_module_args(PRESENT_ARGS)

    fake_admin = _fake_admin(secret=pydantic.SecretStr('generated-secret'))
    monkeypatch.setattr(idp_client, 'IdPAdmin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleExitJson) as exc_info:
        idp_client.main()

    assert exc_info.value.kwargs['client_secret'] == 'generated-secret'
    assert 'generated-secret' not in exc_info.value.module.no_log_values


def test_create_client_without_a_secret_returns_none(monkeypatch):
    set_module_args(PRESENT_ARGS)

    fake_admin = _fake_admin()
    monkeypatch.setattr(idp_client, 'IdPAdmin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleExitJson) as exc_info:
        idp_client.main()

    assert exc_info.value.kwargs['client_secret'] is None


def test_create_client_without_roles_creates_none(monkeypatch):
    set_module_args(PRESENT_ARGS)

    fake_admin = _fake_admin()
    monkeypatch.setattr(idp_client, 'IdPAdmin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleExitJson):
        idp_client.main()

    fake_admin.client_role_create.assert_not_called()


def test_create_client_requires_name_description_and_root_url(monkeypatch):
    set_module_args({**BASE_ARGS, 'state': 'present'})
    monkeypatch.setattr(idp_client, 'IdPAdmin', MagicMock())

    with pytest.raises(AnsibleFailJson) as exc_info:
        idp_client.main()

    assert (
        'requires setting name, description and root_url'
        in exc_info.value.kwargs['msg']
    )


def test_absent_removes_an_existing_client(monkeypatch):
    set_module_args({**BASE_ARGS, 'state': 'absent'})
    fake_admin = MagicMock()
    fake_admin.client_exists.return_value = True
    monkeypatch.setattr(idp_client, 'IdPAdmin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleExitJson) as exc_info:
        idp_client.main()

    fake_admin.client_remove.assert_called_once_with('s3-kube-eng')
    assert exc_info.value.kwargs['client_id'] == 's3-kube-eng'
    assert exc_info.value.kwargs['changed'] is True
    assert exc_info.value.kwargs['msg'] == 'Removed client'


def test_absent_reports_unchanged_when_already_absent(monkeypatch):
    set_module_args({**BASE_ARGS, 'state': 'absent'})
    fake_admin = MagicMock()
    fake_admin.client_exists.return_value = False
    monkeypatch.setattr(idp_client, 'IdPAdmin', MagicMock(return_value=fake_admin))

    with pytest.raises(AnsibleExitJson) as exc_info:
        idp_client.main()

    assert exc_info.value.kwargs['changed'] is False
    assert exc_info.value.kwargs['msg'] == 'Client already absent'
