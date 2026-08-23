from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.s3_utils import S3Admin, S3Exception


def run_module():
    module_args = {
        's3_endpoint': {'type': 'str', 'required': True},
        's3_access_key': {'type': 'str', 'required': True},
        's3_secret_key': {'type': 'str', 'required': True, 'no_log': True},
        's3_region': {'type': 'str', 'required': True},
        's3_ca_path': {'type': 'str', 'required': True},

        'bucket_name': {'type': 'str', 'required': True},

        'state': {'type': 'str', 'required': False, 'default': 'present', 'choices': ['present', 'absent']}
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
        if module.params['state'] == 'present':
            result = s3_admin.bucket_create(module.params['bucket_name'])
        else:
            result = s3_admin.bucket_remove(module.params['bucket_name'])
        module.exit_json(**result.ansible_result())
    except S3Exception as e:
        module.fail_json(**e.ansible_result())


def main():
    run_module()


if __name__ == '__main__':
    main()
