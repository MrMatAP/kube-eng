"""
Unit tests for the account/policy facilities added to
kube_eng.ansible.project.module_utils.s3_utils. Verified once against a live
RustFS instance (its admin API isn't published/versioned); these tests mock
the transport so they run without one.
"""

import json
from unittest.mock import MagicMock

import botocore.credentials
import pytest
from kube_eng.ansible.project.module_utils.s3_utils import S3Admin, S3Exception


def _admin() -> S3Admin:
    admin = S3Admin.__new__(S3Admin)  # bypass __init__, no boto3 client / network
    admin._admin_endpoint = 'https://s3.kube-eng.test:9001'
    admin._admin_region = 'us-east-1'
    admin._admin_ca_path = '/tmp/ca.pem'
    admin._admin_credentials = botocore.credentials.Credentials('root', 'root-secret')
    return admin


def _admin_with_mocked_transport(monkeypatch) -> tuple[S3Admin, MagicMock]:
    admin = _admin()
    mock_request = MagicMock()
    monkeypatch.setattr(admin, '_admin_request', mock_request)
    return admin, mock_request


class _FakeResponse:
    def __init__(self, status_code=200, json_body=None, text=None):
        self.status_code = status_code
        self.ok = status_code < 400
        self.text = (
            text
            if text is not None
            else (json.dumps(json_body) if json_body is not None else '')
        )
        self._json = json_body

    def json(self):
        if self._json is None:
            raise ValueError('invalid json')
        return self._json


# -- _admin_request: the actual HTTP/signing mechanics -----------------


def test_admin_request_signs_and_calls_the_right_url(monkeypatch):
    admin = _admin()
    captured = {}

    def fake_request(method, url, headers=None, data=None, verify=None, timeout=None):
        captured.update(
            method=method, url=url, headers=headers, data=data, verify=verify
        )
        return _FakeResponse(json_body={'ok': True})

    monkeypatch.setattr(
        'kube_eng.ansible.project.module_utils.s3_utils.requests.request', fake_request
    )

    result = admin._admin_request('GET', 'user-info', params={'accessKey': 'a'})

    assert result == {'ok': True}
    assert captured['method'] == 'GET'
    assert captured['url'].startswith(
        'https://s3.kube-eng.test:9001/rustfs/admin/v3/user-info'
    )
    assert 'accessKey=a' in captured['url']
    assert 'Authorization' in captured['headers']
    assert captured['verify'] == '/tmp/ca.pem'


def test_admin_request_raises_with_the_xml_error_message(monkeypatch):
    admin = _admin()
    xml = (
        '<?xml version="1.0"?><Error><Code>NoSuchResource</Code>'
        '<Message>user does not exist</Message></Error>'
    )
    monkeypatch.setattr(
        'kube_eng.ansible.project.module_utils.s3_utils.requests.request',
        lambda *a, **kw: _FakeResponse(status_code=404, text=xml),
    )

    with pytest.raises(S3Exception) as exc_info:
        admin._admin_request('GET', 'user-info', params={'accessKey': 'missing'})

    assert exc_info.value.code == 404
    assert 'user does not exist' in exc_info.value.msg


def test_admin_request_returns_empty_dict_for_an_empty_body(monkeypatch):
    admin = _admin()
    monkeypatch.setattr(
        'kube_eng.ansible.project.module_utils.s3_utils.requests.request',
        lambda *a, **kw: _FakeResponse(status_code=200, text=''),
    )

    assert admin._admin_request('PUT', 'add-user') == {}


# -- account_exists ------------------------------------------------------


def test_account_exists_true(monkeypatch):
    admin, mock_request = _admin_with_mocked_transport(monkeypatch)
    mock_request.return_value = {'status': 'enabled'}

    assert admin.account_exists('svc-a') is True
    mock_request.assert_called_once_with(
        'GET', 'user-info', params={'accessKey': 'svc-a'}
    )


def test_account_exists_false_on_404(monkeypatch):
    admin, mock_request = _admin_with_mocked_transport(monkeypatch)
    mock_request.side_effect = S3Exception(code=404, msg='not found')

    assert admin.account_exists('svc-a') is False


def test_account_exists_reraises_other_errors(monkeypatch):
    admin, mock_request = _admin_with_mocked_transport(monkeypatch)
    mock_request.side_effect = S3Exception(code=500, msg='boom')

    with pytest.raises(S3Exception) as exc_info:
        admin.account_exists('svc-a')

    assert exc_info.value.code == 500


# -- account_policy_get ---------------------------------------------------


def test_account_policy_get_parses_comma_separated_names(monkeypatch):
    admin, mock_request = _admin_with_mocked_transport(monkeypatch)
    mock_request.return_value = {'policyName': 'readonly,readwrite'}

    assert admin.account_policy_get('svc-a') == {'readonly', 'readwrite'}


def test_account_policy_get_empty_when_no_policy_attached(monkeypatch):
    admin, mock_request = _admin_with_mocked_transport(monkeypatch)
    mock_request.return_value = {'status': 'enabled'}

    assert admin.account_policy_get('svc-a') == set()


# -- account_create --------------------------------------------------------


def test_account_create_reports_created_for_a_new_account(monkeypatch):
    admin, mock_request = _admin_with_mocked_transport(monkeypatch)
    mock_request.side_effect = [S3Exception(code=404, msg='missing'), {}]

    created = admin.account_create('svc-a', 'secret-1')

    assert created is True
    last_call = mock_request.call_args_list[-1]
    assert last_call.args == ('PUT', 'add-user')
    assert last_call.kwargs == {
        'params': {'accessKey': 'svc-a'},
        'json_body': {'secretKey': 'secret-1', 'status': 'enabled'},
    }


def test_account_create_reports_not_created_for_an_existing_account(monkeypatch):
    admin, mock_request = _admin_with_mocked_transport(monkeypatch)
    mock_request.side_effect = [{'status': 'enabled'}, {}]

    created = admin.account_create('svc-a', 'secret-1')

    assert created is False


# -- account_role_set -------------------------------------------------------


def test_account_role_set_attaches_when_no_policy_present(monkeypatch):
    admin, mock_request = _admin_with_mocked_transport(monkeypatch)
    mock_request.side_effect = [{'status': 'enabled'}, {}]

    changed = admin.account_role_set('svc-a', 'viewer')

    assert changed is True
    attach_call = mock_request.call_args_list[-1]
    assert attach_call.args == ('POST', 'idp/builtin/policy/attach')
    assert attach_call.kwargs == {
        'json_body': {'policies': ['readonly'], 'user': 'svc-a'}
    }


def test_account_role_set_is_a_no_op_when_the_role_already_matches(monkeypatch):
    admin, mock_request = _admin_with_mocked_transport(monkeypatch)
    mock_request.return_value = {'policyName': 'readonly'}

    changed = admin.account_role_set('svc-a', 'viewer')

    assert changed is False
    mock_request.assert_called_once()


def test_account_role_set_detaches_extra_and_attaches_target(monkeypatch):
    admin, mock_request = _admin_with_mocked_transport(monkeypatch)
    mock_request.side_effect = [{'policyName': 'readwrite'}, {}, {}]

    changed = admin.account_role_set('svc-a', 'viewer')

    assert changed is True
    detach_call, attach_call = (
        mock_request.call_args_list[1],
        mock_request.call_args_list[2],
    )
    assert detach_call.args == ('POST', 'idp/builtin/policy/detach')
    assert detach_call.kwargs == {
        'json_body': {'policies': ['readwrite'], 'user': 'svc-a'}
    }
    assert attach_call.args == ('POST', 'idp/builtin/policy/attach')
    assert attach_call.kwargs == {
        'json_body': {'policies': ['readonly'], 'user': 'svc-a'}
    }


# -- account_ensure ---------------------------------------------------------


def test_account_ensure_reports_created(monkeypatch):
    admin = _admin()
    monkeypatch.setattr(admin, 'account_create', lambda *a, **kw: True)
    monkeypatch.setattr(admin, 'account_role_set', lambda *a, **kw: True)

    result = admin.account_ensure('svc-a', 'secret-1', 'admin')

    assert result.changed is True
    assert result.msg == 'Account created'
    assert result.access_key == 'svc-a'
    assert result.role == 'admin'


def test_account_ensure_reports_role_updated_when_only_the_role_changes(monkeypatch):
    admin = _admin()
    monkeypatch.setattr(admin, 'account_create', lambda *a, **kw: False)
    monkeypatch.setattr(admin, 'account_role_set', lambda *a, **kw: True)

    result = admin.account_ensure('svc-a', 'secret-1', 'contributor')

    assert result.changed is True
    assert result.msg == 'Account role updated'


def test_account_ensure_reports_unchanged_when_nothing_changed(monkeypatch):
    admin = _admin()
    monkeypatch.setattr(admin, 'account_create', lambda *a, **kw: False)
    monkeypatch.setattr(admin, 'account_role_set', lambda *a, **kw: False)

    result = admin.account_ensure('svc-a', 'secret-1', 'viewer')

    assert result.changed is False
    assert result.msg == 'Account is present'


# -- account_remove ----------------------------------------------------------


def test_account_remove_removes_an_existing_account(monkeypatch):
    admin = _admin()
    monkeypatch.setattr(admin, 'account_exists', lambda *_: True)
    mock_request = MagicMock(return_value={})
    monkeypatch.setattr(admin, '_admin_request', mock_request)

    result = admin.account_remove('svc-a')

    assert result.changed is True
    assert result.msg == 'Account removed'
    mock_request.assert_called_once_with(
        'DELETE', 'remove-user', params={'accessKey': 'svc-a'}
    )


def test_account_remove_is_a_no_op_when_already_absent(monkeypatch):
    admin = _admin()
    monkeypatch.setattr(admin, 'account_exists', lambda *_: False)
    mock_request = MagicMock()
    monkeypatch.setattr(admin, '_admin_request', mock_request)

    result = admin.account_remove('svc-a')

    assert result.changed is False
    assert result.msg == 'Account is absent'
    mock_request.assert_not_called()
