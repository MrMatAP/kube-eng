from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.pg_utils import PGAdmin, PGException, PGValidationResult


def run_module():
    module_args = {
        'admin_dsn': {'type': 'str', 'required': True, 'no_log': True},
    }
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    if module.check_mode:
        module.exit_json()

    try:
        pg_admin = PGAdmin(admin_dsn=module.params['admin_dsn'])
        result = pg_admin.validate()
        module.exit_json(**result.ansible_result())
    except PGException as e:
        # Keep the same shape as a successful PGValidationResult (in
        # particular, 'validated') even on failure, in case this is ever
        # retried with `until: <result>.validated` the way idp_validate is.
        result = PGValidationResult(changed=False, msg=e.msg, validated=False)
        module.fail_json(**result.ansible_result())


def main():
    run_module()


if __name__ == '__main__':
    main()
