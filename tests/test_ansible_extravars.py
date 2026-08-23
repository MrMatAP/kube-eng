"""
Contract tests for the RootConfig -> Ansible extravars boundary.

AnsibleExecution serializes RootConfig with model_dump(mode='json') and hands
it to ansible-runner as extravars (see common/ansible_execution.py). Playbooks
then relay nested values straight into Ansible module args (e.g.
infra_apply.yml passes infra.s3.client_roles to the idp_client module's
`roles` argument, a list of dicts). These tests pin that shape so a change to
a config model (e.g. adding a serialization alias) can't silently break what
an Ansible module receives.
"""

import pathlib

from kube_eng.config import RootConfig


def make_config(tmp_path: pathlib.Path, **infrastructure) -> RootConfig:
    return RootConfig(
        config_path=tmp_path,
        admin_password='test-admin',
        cluster={'name': 'testcluster'},
        infra=infrastructure,
    )


def test_s3_client_roles_serialize_as_plain_name_description_dicts(
    tmp_path: pathlib.Path,
):
    dumped = make_config(tmp_path).model_dump(mode='json')

    roles = dumped['infra']['s3']['client_roles']
    assert roles, 'There should be at least one S3 client role'
    for role in roles:
        assert set(role) == {'name', 'description'}, (
            "idp_client's 'roles' argument_spec expects dicts with exactly "
            "'name' and 'description' keys"
        )
