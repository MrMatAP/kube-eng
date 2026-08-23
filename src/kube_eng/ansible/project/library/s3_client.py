from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.s3_utils import S3Admin, S3Exception

_UNSET_ = '--UNSET--'
_ROLES_ = ('admin', 'contributor', 'viewer')


def run_module():
    module_args = {
        's3_endpoint': {'type': 'str', 'required': True},
        's3_access_key': {'type': 'str', 'required': True},
        's3_secret_key': {'type': 'str', 'required': True, 'no_log': True},
        's3_region': {'type': 'str', 'required': True},
        's3_ca_path': {'type': 'str', 'required': True},
        'access_key': {'type': 'str', 'required': True},
        'secret_key': {
            'type': 'str',
            'required': False,
            'default': _UNSET_,
            'no_log': True,
        },
        'role': {'type': 'str', 'required': False, 'default': _UNSET_},
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
        if module.params['state'] == 'present':
            if (
                module.params['secret_key'] == _UNSET_
                or module.params['role'] == _UNSET_
            ):
                module.fail_json(
                    msg='Creating an S3 account requires setting secret_key and role'
                )
            if module.params['role'] not in _ROLES_:
                module.fail_json(
                    msg=f'role must be one of {", ".join(_ROLES_)}, got {module.params["role"]!r}'
                )

        s3_admin = S3Admin(
            s3_endpoint=module.params['s3_endpoint'],
            s3_access_key=module.params['s3_access_key'],
            s3_secret_key=module.params['s3_secret_key'],
            s3_region=module.params['s3_region'],
            s3_ca_path=module.params['s3_ca_path'],
        )
        if module.params['state'] == 'present':
            # secret_key is returned unchanged as part of this module's own
            # inputs (never regenerated), so nothing here needs no_log_values
            # -- unlike a freshly-generated secret, it doesn't need scrubbing
            # from a JSON result the caller relies on.
            result = s3_admin.account_ensure(
                access_key=module.params['access_key'],
                secret_key=module.params['secret_key'],
                role=module.params['role'],
            )
        else:
            result = s3_admin.account_remove(module.params['access_key'])
        module.exit_json(**result.ansible_result())
    except S3Exception as e:
        module.fail_json(**e.ansible_result())


def main():
    run_module()


if __name__ == '__main__':
    main()
