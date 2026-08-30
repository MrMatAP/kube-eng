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


def test_client_template_merges_redirect_uris_and_callback_url():
    client = IdPAdmin.client_template(
        client_id='kube-eng-cluster',
        name='Cluster',
        description='Cluster OIDC client',
        root_url='http://localhost:8000',
        callback_url='http://localhost:18000',
        redirect_uris=['http://localhost:8000'],
    )

    assert [str(uri) for uri in client.redirect_uris] == [
        'http://localhost:8000/',
        'http://localhost:18000/',
    ]


def test_client_template_enables_pkce_by_default():
    client = IdPAdmin.client_template(
        client_id='s3-kube-eng',
        name='S3',
        description='S3 instance',
        root_url='https://s3.kube-eng.test',
    )

    assert client.attributes['pkce.code.challenge.method'] == 'S256'


def test_client_template_omits_pkce_attribute_when_disabled():
    """pkce_enabled=False is an escape hatch for relying parties that can't
    do PKCE at all -- currently only the registry (zot), whose OIDC
    implementation has no PKCE support. Keycloak treats a missing
    pkce.code.challenge.method attribute as PKCE-not-enforced, so the key
    must be absent entirely rather than set to an empty/falsy value."""
    client = IdPAdmin.client_template(
        client_id='registry-kube-eng',
        name='Registry',
        description='Registry instance',
        root_url='https://registry.kube-eng.test',
        pkce_enabled=False,
    )

    assert 'pkce.code.challenge.method' not in client.attributes


def test_client_template_public_client_has_no_service_account_and_no_implicit_flow():
    client = IdPAdmin.client_template(
        client_id='kube-eng-cluster',
        name='Cluster',
        description='Cluster OIDC client',
        root_url='http://localhost:8000',
        public_client=True,
    )

    assert client.public_client is True
    assert client.service_accounts_enabled is False
    assert client.implicit_flow_enabled is False


def test_client_template_standard_flow_is_always_on():
    client = IdPAdmin.client_template(
        client_id='s3-kube-eng',
        name='S3',
        description='S3 instance',
        root_url='https://s3.kube-eng.test',
    )

    assert client.standard_flow_enabled is True


def test_client_template_defaults_to_standard_flow_only():
    """A confidential client with no flows requested gets exactly the
    standard flow -- service_accounts is no longer implied by
    public_client=False, it must be requested explicitly."""
    client = IdPAdmin.client_template(
        client_id='s3-kube-eng',
        name='S3',
        description='S3 instance',
        root_url='https://s3.kube-eng.test',
    )

    assert client.standard_flow_enabled is True
    assert client.implicit_flow_enabled is False
    assert client.direct_access_grants_enabled is False
    assert client.service_accounts_enabled is False


@pytest.mark.parametrize(
    ('flow', 'attribute'),
    [
        ('implicit', 'implicit_flow_enabled'),
        ('direct_access_grants', 'direct_access_grants_enabled'),
        ('service_accounts', 'service_accounts_enabled'),
    ],
)
def test_client_template_enables_the_requested_optional_flow(flow, attribute):
    client = IdPAdmin.client_template(
        client_id='s3-kube-eng',
        name='S3',
        description='S3 instance',
        root_url='https://s3.kube-eng.test',
        flows=[flow],
    )

    assert getattr(client, attribute) is True
    assert client.standard_flow_enabled is True
    other_flow_attributes = {
        'implicit_flow_enabled',
        'direct_access_grants_enabled',
        'service_accounts_enabled',
    } - {attribute}
    for other in other_flow_attributes:
        assert getattr(client, other) is False


def test_client_template_rejects_an_unknown_flow():
    with pytest.raises(IdPException) as exc_info:
        IdPAdmin.client_template(
            client_id='s3-kube-eng',
            name='S3',
            description='S3 instance',
            root_url='https://s3.kube-eng.test',
            flows=['bogus'],
        )

    assert exc_info.value.code == 400


def test_client_template_rejects_service_accounts_on_a_public_client():
    """Keycloak has no notion of a service account on a public client, so
    this combination is rejected rather than silently ignored."""
    with pytest.raises(IdPException) as exc_info:
        IdPAdmin.client_template(
            client_id='kube-eng-cluster',
            name='Cluster',
            description='Cluster OIDC client',
            root_url='http://localhost:8000',
            public_client=True,
            flows=['service_accounts'],
        )

    assert exc_info.value.code == 400


def test_client_template_omits_audience_mapper_by_default():
    client = IdPAdmin.client_template(
        client_id='registry-kube-eng',
        name='Registry',
        description='Registry instance',
        root_url='https://registry.kube-eng.test',
    )

    assert all(
        mapper.protocol_mapper != 'oidc-audience-mapper'
        for mapper in client.protocol_mappers
    )


def test_client_template_adds_an_audience_mapper_when_requested():
    """audience backs zot's bearer.oidc workload-identity auth (ADR-0004),
    which checks a minted token's 'aud' claim against a configured value."""
    client = IdPAdmin.client_template(
        client_id='registry-kube-eng',
        name='Registry',
        description='Registry instance',
        root_url='https://registry.kube-eng.test',
        audience='registry-kube-eng',
    )

    audience_mappers = [
        mapper
        for mapper in client.protocol_mappers
        if mapper.protocol_mapper == 'oidc-audience-mapper'
    ]
    assert len(audience_mappers) == 1
    assert audience_mappers[0].config['included.custom.audience'] == 'registry-kube-eng'


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


def test_client_get_tolerates_keycloaks_blank_url_fields():
    """Keycloak represents an unset URL field as '' on GET, not null --
    client_template() never sets base_url, so every existing client comes
    back this way and must not fail to parse."""
    admin = _fake_admin()
    admin._idp_admin.get_client_id.return_value = 'client-obj-1'
    admin._idp_admin.get_client.return_value = {
        'id': 'client-obj-1',
        'clientId': 's3-kube-eng',
        'name': 'S3',
        'baseUrl': '',
        'adminUrl': '',
        'rootUrl': '',
        'protocolMappers': [],
    }

    client = admin.client_get('s3-kube-eng')

    assert client.base_url is None
    assert client.admin_url is None
    assert client.root_url is None


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


def test_client_create_creates_a_new_client_when_absent():
    admin = _fake_admin()
    # First lookup (does this client exist yet?) finds nothing; the second,
    # after creation, resolves it -- client_get() calls get_client_id again
    # to fetch back what it just created.
    admin._idp_admin.get_client_id.side_effect = [None, 'client-obj-1']
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
    client = IdPAdmin.client_template(
        client_id='s3-kube-eng',
        name='S3',
        description='S3 instance',
        root_url='https://s3.kube-eng.test',
    )

    admin.client_create(client)

    admin._idp_admin.create_client.assert_called_once()
    admin._idp_admin.update_client.assert_not_called()


def test_client_create_reconciles_an_existing_client_instead_of_skipping_it():
    """A client created by an earlier run, before its desired shape
    changed (e.g. gaining 'service_accounts' or an audience mapper), must
    converge to the new shape here rather than being left stale forever."""
    admin = _admin_with_create_client_mocked()
    client = IdPAdmin.client_template(
        client_id='s3-kube-eng',
        name='S3',
        description='S3 instance',
        root_url='https://s3.kube-eng.test',
    )

    admin.client_create(client)

    admin._idp_admin.update_client.assert_called_once_with(
        'client-obj-1', client.model_dump(mode='json')
    )
    admin._idp_admin.create_client.assert_not_called()


def test_client_create_skips_the_secret_fetch_for_a_public_client():
    """Keycloak has no credential secret for a public client -- fetching one
    would either fail or hand back a meaningless value, so public clients
    must come back with secret=None without ever calling get_client_secrets."""
    admin = _fake_admin()
    admin._idp_admin.get_client_id.return_value = 'client-obj-1'
    admin._idp_admin.get_client.return_value = {
        'id': 'client-obj-1',
        'clientId': 'kube-eng-cluster',
        'name': 'Cluster',
        'publicClient': True,
        'protocolMappers': [],
    }
    client = IdPAdmin.client_template(
        client_id='kube-eng-cluster',
        name='Cluster',
        description='Cluster OIDC client',
        root_url='http://localhost:8000',
        public_client=True,
    )

    created = admin.client_create(client)

    assert created.secret is None
    admin._idp_admin.get_client_secrets.assert_not_called()


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


def test_client_credentials_token_returns_the_access_token(monkeypatch):
    fake_openid = MagicMock()
    fake_openid.token.return_value = {'access_token': 'a-jwt', 'expires_in': 60}
    mock_openid_cls = MagicMock(return_value=fake_openid)
    monkeypatch.setattr(
        'kube_eng.ansible.project.module_utils.idp_utils.KeycloakOpenID',
        mock_openid_cls,
    )

    token = IdPAdmin.client_credentials_token(
        idp_url='https://idp.kube-eng.test',
        idp_realm='kube-eng',
        idp_ca_path='/tmp/ca.pem',
        client_id='registry-kube-eng',
        client_secret='sup3r-secret',
    )

    assert token == 'a-jwt'
    mock_openid_cls.assert_called_once_with(
        server_url='https://idp.kube-eng.test',
        client_id='registry-kube-eng',
        realm_name='kube-eng',
        client_secret_key='sup3r-secret',
        verify='/tmp/ca.pem',
    )
    fake_openid.token.assert_called_once_with(grant_type='client_credentials')


def test_client_credentials_token_wraps_keycloak_errors(monkeypatch):
    import keycloak.exceptions

    fake_openid = MagicMock()
    fake_openid.token.side_effect = keycloak.exceptions.KeycloakError('nope')
    monkeypatch.setattr(
        'kube_eng.ansible.project.module_utils.idp_utils.KeycloakOpenID',
        MagicMock(return_value=fake_openid),
    )

    with pytest.raises(IdPException) as exc_info:
        IdPAdmin.client_credentials_token(
            idp_url='https://idp.kube-eng.test',
            idp_realm='kube-eng',
            idp_ca_path='/tmp/ca.pem',
            client_id='registry-kube-eng',
            client_secret='sup3r-secret',
        )

    assert exc_info.value.code == 400
