from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.s3_utils import S3Admin, S3Exception, S3ValidationResult


def run_module():
    module_args = {
        's3_endpoint': {'type': 'str', 'required': True},
        's3_access_key': {'type': 'str', 'required': True},
        's3_secret_key': {'type': 'str', 'required': True, 'no_log': True},
        's3_region': {'type': 'str', 'required': True},
        's3_ca_path': {'type': 'str', 'required': True},
    }
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    if module.check_mode:
        module.exit_json()

    try:
        s3_admin = S3Admin(
            s3_endpoint=module.params['s3_endpoint'],
            s3_access_key=module.params['s3_access_key'],
            s3_secret_key=module.params['s3_secret_key'],
            s3_region=module.params['s3_region'],
            s3_ca_path=module.params['s3_ca_path'],
        )
        result = s3_admin.validate()
        module.exit_json(**result.ansible_result())
    except S3Exception as e:
        # Keep the same shape as a successful S3ValidationResult (in
        # particular, 'validated') even on failure, in case this is ever
        # retried with `until: <result>.validated` the way idp_validate is.
        result = S3ValidationResult(changed=False, msg=e.msg, validated=False)
        module.fail_json(**result.ansible_result())


def main():
    run_module()


if __name__ == '__main__':
    main()
