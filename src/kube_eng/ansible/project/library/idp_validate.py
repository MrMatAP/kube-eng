from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.idp_utils import IdPAdmin, IdPException, IdPValidationResult


def run_module():
    module_args = {
        'idp_url': {'type': 'str', 'required': True},
        'idp_admin_user': {'type': 'str', 'required': True},
        'idp_admin_password': {'type': 'str', 'required': True, 'no_log': True},
        'idp_realm': {'type': 'str', 'required': True},
        'idp_ca_path': {'type': 'str', 'required': True}
    }
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    if module.check_mode:
        module.exit_json()

    try:
        idp_admin = IdPAdmin(
            idp_url=module.params['idp_url'],
            idp_admin_user=module.params['idp_admin_user'],
            idp_admin_password=module.params['idp_admin_password'],
            idp_realm=module.params['idp_realm'],
            idp_ca_path=module.params['idp_ca_path'],
        )
        result = idp_admin.validate(module.params['idp_admin_user'])
        module.exit_json(**result.ansible_result())
    except IdPException as e:
        # Keep the same shape as a successful IdPValidationResult (in
        # particular, 'validated') even on failure -- this is retried with
        # `until: idp_validation.validated`, which needs that key present on
        # every attempt, not just successful ones. The IdP container (Keycloak)
        # commonly reports healthy before its admin API is actually queryable,
        # so the first attempt failing here is the expected, common case.
        result = IdPValidationResult(changed=False, msg=e.msg, validated=False)
        module.fail_json(**result.ansible_result())


def main():
    run_module()


if __name__ == '__main__':
    main()
