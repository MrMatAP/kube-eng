from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.registry_utils import RegistryException, RegistryHtpasswd


def run_module():
    module_args = {
        'path': {'type': 'str', 'required': True},
        'username': {'type': 'str', 'required': True},
        'password': {'type': 'str', 'required': True, 'no_log': True},
    }
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    try:
        result = RegistryHtpasswd(module.params['path']).reconcile(
            username=module.params['username'],
            password=module.params['password'],
            check_mode=module.check_mode,
        )
        module.exit_json(**result.ansible_result())
    except RegistryException as e:
        module.fail_json(**e.ansible_result())


def main():
    run_module()


if __name__ == '__main__':
    main()
