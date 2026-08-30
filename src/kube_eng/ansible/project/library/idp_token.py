from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.idp_utils import IdPAdmin, IdPException, IdPTokenResult


def run_module():
    module_args = {
        'idp_url': {'type': 'str', 'required': True},
        'idp_realm': {'type': 'str', 'required': True},
        'idp_ca_path': {'type': 'str', 'required': True},
        'client_id': {'type': 'str', 'required': True},
        'client_secret': {'type': 'str', 'required': True, 'no_log': True},
    }
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    if module.check_mode:
        module.exit_json()

    try:
        access_token = IdPAdmin.client_credentials_token(
            idp_url=module.params['idp_url'],
            idp_realm=module.params['idp_realm'],
            idp_ca_path=module.params['idp_ca_path'],
            client_id=module.params['client_id'],
            client_secret=module.params['client_secret'],
        )
        # access_token is returned for the playbook to consume (e.g. as the
        # password for `helm registry login`), so it must NOT be added to
        # module.no_log_values -- that scrubs matching values from this
        # module's own JSON result too, corrupting the very value the
        # caller registered this task to obtain. Mark the task itself
        # `no_log: true` in the playbook instead to keep it out of the
        # console/log.
        result = IdPTokenResult(
            changed=False,
            msg='Obtained access token',
            access_token=access_token,
        )
        module.exit_json(**result.ansible_result())
    except IdPException as e:
        module.fail_json(**e.ansible_result())


def main():
    run_module()


if __name__ == '__main__':
    main()
