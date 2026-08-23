from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.idp_utils import IdPAdmin, IdPClientCreateResult, IdPException

_UNSET_ = '--UNSET--'


def run_module():
    module_args = {
        'idp_url': {'type': 'str', 'required': True},
        'idp_admin_user': {'type': 'str', 'required': True},
        'idp_admin_password': {'type': 'str', 'required': True, 'no_log': True},
        'idp_realm': {'type': 'str', 'required': True},
        'idp_ca_path': {'type': 'str', 'required': True},
        'client_id': {'type': 'str', 'required': True},
        'name': {'type': 'str', 'required': False, 'default': _UNSET_},
        'description': {'type': 'str', 'required': False, 'default': _UNSET_},
        'root_url': {'type': 'str', 'required': False, 'default': _UNSET_},
        'callback_url': {'type': 'str', 'required': False, 'default': None},
        'roles': {'type': 'list', 'elements': 'dict', 'required': False},
        'state': {
            'type': 'str',
            'required': False,
            'default': 'present',
            'choices': ['present', 'absent'],
        },
    }
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    if module.check_mode:
        module.exit_json()

    try:
        if module.params['state'] == 'present' and any(
            [
                module.params['name'] == _UNSET_,
                module.params['description'] == _UNSET_,
                module.params['root_url'] == _UNSET_,
            ]
        ):
            module.fail_json(
                msg='Creating an IdP client requires setting name, description and root_url'
            )

        idp_admin = IdPAdmin(
            idp_url=module.params['idp_url'],
            idp_admin_user=module.params['idp_admin_user'],
            idp_admin_password=module.params['idp_admin_password'],
            idp_realm=module.params['idp_realm'],
            idp_ca_path=module.params['idp_ca_path'],
        )
        if module.params['state'] == 'present':
            already_existed = idp_admin.client_exists(module.params['client_id'])
            client = IdPAdmin.client_template(
                client_id=module.params['client_id'],
                name=module.params['name'],
                root_url=module.params['root_url'],
                description=module.params['description'],
                callback_url=module.params['callback_url'],
            )
            created_client = idp_admin.client_create(client)
            for role in module.params['roles'] or []:
                idp_admin.client_role_create(
                    created_client, role=role['name'], description=role['description']
                )
            client_secret = (
                created_client.secret.get_secret_value()
                if created_client.secret is not None
                else None
            )
            # client_secret is returned for the playbook to consume (e.g. to
            # configure a downstream service), so it must NOT be added to
            # module.no_log_values -- that scrubs matching values from this
            # module's own JSON result too, corrupting the very value the
            # caller registered this task to obtain. Mark the task itself
            # `no_log: true` in the playbook instead to keep it out of the
            # console/log.
            result = IdPClientCreateResult(
                changed=not already_existed,
                msg='Client already exists' if already_existed else 'Created client',
                client_id=created_client.client_id,
                client_secret=client_secret,
            )
            module.exit_json(**result.ansible_result())
        else:
            already_existed = idp_admin.client_exists(module.params['client_id'])
            idp_admin.client_remove(module.params['client_id'])
            result = IdPClientCreateResult(
                changed=already_existed,
                msg='Removed client' if already_existed else 'Client already absent',
                client_id=module.params['client_id'],
            )
            module.exit_json(**result.ansible_result())
    except IdPException as e:
        module.fail_json(**e.ansible_result())


def main():
    run_module()


if __name__ == '__main__':
    main()
