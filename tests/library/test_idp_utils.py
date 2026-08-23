"""
Unit tests for kube_eng.ansible.project.module_utils.idp_utils that don't require a
live IdP. Only the KeycloakAdmin instance is mocked, so IdPAdmin's own logic
(building the payload, error wrapping) runs for real.
"""

from unittest.mock import MagicMock

import pytest
from kube_eng.ansible.project.module_utils.idp_utils import (
    IdPAdmin,
    IdPClient,
    IdPClientScope,
    IdPException,
)


def _fake_admin() -> IdPAdmin:
    admin = IdPAdmin.__new__(IdPAdmin)  # bypass __init__, no network call
    admin._idp_admin = MagicMock()
    return admin


def _client(object_id: str | None = 'obj-1') -> IdPClient:
    client = IdPClient(client_id='s3-kube-eng', name='S3', protocol_mappers=[])
    client.id = object_id
    return client


def test_client_template_sets_redirect_uris_from_callback_url():
    client = IdPAdmin.client_template(
        client_id='s3-kube-eng',
        name='S3',
        description='S3 instance',
        root_url='https://s3.kube-eng.test',
        callback_url='https://s3.kube-eng.test/rustfs/admin/v3/oidc/callback/default',
    )

    assert [str(uri) for uri in client.redirect_uris] == [
        'https://s3.kube-eng.test/rustfs/admin/v3/oidc/callback/default'
    ]


def test_client_template_without_callback_url_has_no_redirect_uris():
    client = IdPAdmin.client_template(
        client_id='s3-kube-eng',
        name='S3',
        description='S3 instance',
        root_url='https://s3.kube-eng.test',
    )

    assert client.redirect_uris is None


def test_client_role_create_sends_a_name_key():
    admin = _fake_admin()
    client = _client()

    admin.client_role_create(
        client, role='kube-eng-s3-admin', description='Kube Eng :: S3 :: Admin'
    )

    admin._idp_admin.create_client_role.assert_called_once_with(
        client_role_id='obj-1',
        payload={'name': 'kube-eng-s3-admin', 'description': 'Kube Eng :: S3 :: Admin'},
        skip_exists=True,
    )


def test_client_role_create_requires_an_object_id():
    admin = _fake_admin()
    client = _client(object_id=None)

    with pytest.raises(IdPException) as exc_info:
        admin.client_role_create(client, role='kube-eng-s3-admin', description='Admin')

    assert exc_info.value.code == 400
    admin._idp_admin.create_client_role.assert_not_called()


def test_client_default_scope_add_attaches_the_scope_to_the_client():
    admin = _fake_admin()
    client = _client(object_id='client-obj-1')
    scope = IdPClientScope(id='scope-obj-1', name='s3-kube-eng-roles')

    admin.client_default_scope_add(client, scope)

    admin._idp_admin.add_client_default_client_scope.assert_called_once_with(
        client_id='client-obj-1', client_scope_id='scope-obj-1', payload={}
    )


def test_client_default_scope_add_requires_both_object_ids():
    admin = _fake_admin()
    client = _client(object_id=None)
    scope = IdPClientScope(id='scope-obj-1', name='s3-kube-eng-roles')

    with pytest.raises(IdPException) as exc_info:
        admin.client_default_scope_add(client, scope)

    assert exc_info.value.code == 400
    admin._idp_admin.add_client_default_client_scope.assert_not_called()


def _admin_with_create_client_mocked() -> IdPAdmin:
    admin = _fake_admin()
    admin._idp_admin.get_client_id.return_value = 'client-obj-1'
    admin._idp_admin.get_client.return_value = {
        'id': 'client-obj-1',
        'clientId': 's3-kube-eng',
        'name': 'S3',
        'protocolMappers': [],
    }
    admin._idp_admin.get_client_secrets.return_value = {
        'type': 'secret',
        'value': 'sup3r-secret',
    }
    return admin


def test_client_exists_true_when_the_client_id_resolves():
    admin = _fake_admin()
    admin._idp_admin.get_client_id.return_value = 'client-obj-1'

    assert admin.client_exists('s3-kube-eng') is True
    admin._idp_admin.get_client_id.assert_called_once_with('s3-kube-eng')


def test_client_exists_false_when_the_client_id_does_not_resolve():
    admin = _fake_admin()
    admin._idp_admin.get_client_id.return_value = None

    assert admin.client_exists('s3-kube-eng') is False


def test_client_remove_deletes_by_object_id_not_client_id():
    """delete_client takes Keycloak's internal object id, not the OAuth
    client_id -- passing the client_id straight through 404s."""
    admin = _fake_admin()
    admin._idp_admin.get_client_id.return_value = 'client-obj-1'

    admin.client_remove('s3-kube-eng')

    admin._idp_admin.get_client_id.assert_called_once_with('s3-kube-eng')
    admin._idp_admin.delete_client.assert_called_once_with('client-obj-1')


def test_client_remove_is_a_no_op_when_the_client_is_already_absent():
    admin = _fake_admin()
    admin._idp_admin.get_client_id.return_value = None

    admin.client_remove('s3-kube-eng')

    admin._idp_admin.delete_client.assert_not_called()


def test_client_create_returns_the_clients_secret():
    admin = _admin_with_create_client_mocked()
    client = IdPAdmin.client_template(
        client_id='s3-kube-eng',
        name='S3',
        description='S3 instance',
        root_url='https://s3.kube-eng.test',
    )

    created = admin.client_create(client)

    assert created.secret is not None
    assert created.secret.get_secret_value() == 'sup3r-secret'
    admin._idp_admin.get_client_secrets.assert_called_once_with(
        client_id='client-obj-1'
    )


def test_client_create_never_regenerates_the_secret():
    """Re-running against an already-existing client must fetch the same
    secret, not rotate it -- consumers configured with the old secret would
    otherwise break on every idempotent re-run."""
    admin = _admin_with_create_client_mocked()
    client = IdPAdmin.client_template(
        client_id='s3-kube-eng',
        name='S3',
        description='S3 instance',
        root_url='https://s3.kube-eng.test',
    )

    first = admin.client_create(client)
    second = admin.client_create(client)

    assert first.secret.get_secret_value() == second.secret.get_secret_value()
    admin._idp_admin.generate_client_secrets.assert_not_called()


def test_client_secret_get_returns_the_stored_secret():
    admin = _fake_admin()
    admin._idp_admin.get_client_secrets.return_value = {
        'type': 'secret',
        'value': 'sup3r-secret',
    }
    client = _client(object_id='client-obj-1')

    secret = admin.client_secret_get(client)

    assert secret.get_secret_value() == 'sup3r-secret'
    admin._idp_admin.get_client_secrets.assert_called_once_with(
        client_id='client-obj-1'
    )


def test_client_secret_get_requires_an_object_id():
    admin = _fake_admin()
    client = _client(object_id=None)

    with pytest.raises(IdPException) as exc_info:
        admin.client_secret_get(client)

    assert exc_info.value.code == 400
    admin._idp_admin.get_client_secrets.assert_not_called()
