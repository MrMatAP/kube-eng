from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.pg_utils import PGAdmin, PGException

_UNSET_ = '--UNSET--'


def run_module():
    module_args = {
        'admin_dsn': {'type': 'str', 'required': True, 'no_log': True},
        'db_name': {'type': 'str', 'required': True},
        'db_user': {'type': 'str', 'required': True},
        'db_password': {
            'type': 'str',
            'required': False,
            'default': _UNSET_,
            'no_log': True,
        },
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
        if (
            module.params['state'] == 'present'
            and module.params['db_password'] == _UNSET_
        ):
            module.fail_json(msg='Creating a database requires setting db_password')

        pg_admin = PGAdmin(admin_dsn=module.params['admin_dsn'])
        if module.params['state'] == 'present':
            result = pg_admin.database_create(
                db_name=module.params['db_name'],
                db_user=module.params['db_user'],
                db_password=module.params['db_password'],
            )
        else:
            result = pg_admin.database_remove(
                db_name=module.params['db_name'],
                db_user=module.params['db_user'],
            )
        module.exit_json(**result.ansible_result())
    except PGException as e:
        module.fail_json(**e.ansible_result())


def main():
    run_module()


if __name__ == '__main__':
    main()
