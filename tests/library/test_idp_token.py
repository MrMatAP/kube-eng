"""
Unit tests for the idp_token Ansible module wrapper. IdPAdmin is mocked out
entirely, so these tests only pin the relay between Ansible task args and
IdPAdmin.client_credentials_token() -- no live IdP, no network.
"""

from unittest.mock import MagicMock

import pytest
from _ansible_harness import AnsibleExitJson, AnsibleFailJson, set_module_args
from kube_eng.ansible.project.library import idp_token
from kube_eng.ansible.project.module_utils.idp_utils import IdPException

BASE_ARGS = {
    'idp_url': 'https://idp.kube-eng.test',
    'idp_realm': 'kube-eng',
    'idp_ca_path': '/tmp/ca.pem',
    'client_id': 'registry-kube-eng',
    'client_secret': 'sup3r-secret',
}


def test_token_relays_args_and_returns_the_access_token(monkeypatch):
    set_module_args(BASE_ARGS)
    mock_token_fn = MagicMock(return_value='a-jwt')
    monkeypatch.setattr(idp_token.IdPAdmin, 'client_credentials_token', mock_token_fn)

    with pytest.raises(AnsibleExitJson) as exc_info:
        idp_token.main()

    mock_token_fn.assert_called_once_with(
        idp_url='https://idp.kube-eng.test',
        idp_realm='kube-eng',
        idp_ca_path='/tmp/ca.pem',
        client_id='registry-kube-eng',
        client_secret='sup3r-secret',
    )
    assert exc_info.value.kwargs['access_token'] == 'a-jwt'
    assert exc_info.value.kwargs['changed'] is False


def test_token_returns_the_real_access_token_unmangled(monkeypatch):
    """The token must come back verbatim -- it must NOT be registered in
    module.no_log_values, since that scrubs matching values from this same
    module's JSON result (replacing it with the literal string
    'VALUE_SPECIFIED_IN_NO_LOG_PARAMETER'), corrupting the very value the
    playbook registers this task to consume downstream (as the password for
    `helm registry login`)."""
    set_module_args(BASE_ARGS)
    monkeypatch.setattr(
        idp_token.IdPAdmin, 'client_credentials_token', MagicMock(return_value='a-jwt')
    )

    with pytest.raises(AnsibleExitJson) as exc_info:
        idp_token.main()

    assert exc_info.value.kwargs['access_token'] == 'a-jwt'
    assert 'a-jwt' not in exc_info.value.module.no_log_values


def test_token_fails_when_the_grant_fails(monkeypatch):
    set_module_args(BASE_ARGS)
    monkeypatch.setattr(
        idp_token.IdPAdmin,
        'client_credentials_token',
        MagicMock(
            side_effect=IdPException(
                code=400, msg='Unable to obtain a client credentials token'
            )
        ),
    )

    with pytest.raises(AnsibleFailJson) as exc_info:
        idp_token.main()

    assert exc_info.value.kwargs['msg'] == 'Unable to obtain a client credentials token'
