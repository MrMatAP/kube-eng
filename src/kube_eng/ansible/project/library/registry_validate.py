from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.registry_utils import (
    RegistryAdmin,
    RegistryException,
    RegistryValidationResult,
)


def run_module():
    module_args = {
        'registry_endpoint': {'type': 'str', 'required': True},
        'registry_ca_path': {'type': 'str', 'required': True},
        # The push account (see infra_apply.yml). A Remote registry that
        # kube-eng holds no credential for passes an empty password and
        # gets a bare connectivity check.
        'username': {'type': 'str', 'required': False, 'default': None},
        'password': {
            'type': 'str',
            'required': False,
            'default': None,
            'no_log': True,
        },
    }
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    if module.check_mode:
        module.exit_json()

    try:
        registry_admin = RegistryAdmin(
            registry_endpoint=module.params['registry_endpoint'],
            registry_ca_path=module.params['registry_ca_path'],
        )
        result = registry_admin.validate(
            username=module.params['username'],
            password=module.params['password'],
        )
        module.exit_json(**result.ansible_result())
    except RegistryException as e:
        # Keep the same shape as a successful RegistryValidationResult (in
        # particular, 'validated') even on failure, in case this is ever
        # retried with `until: <result>.validated` the way idp_validate is.
        result = RegistryValidationResult(changed=False, msg=e.msg, validated=False)
        module.fail_json(**result.ansible_result())


def main():
    run_module()


if __name__ == '__main__':
    main()
