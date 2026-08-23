from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.dns_utils import DNSAdmin, DNSException, DNSValidationResult


def run_module():
    module_args = {
        'dns_ip': {'type': 'str', 'required': True},
        'dns_admin_key_name': {'type': 'str', 'required': True},
        'dns_admin_key_secret': {'type': 'str', 'required': True, 'no_log': True},
        'dns_protocol': {
            'type': 'str',
            'required': False,
            'default': 'tcp',
            'choices': ['tcp', 'udp'],
        },
        'dns_zone': {'type': 'str', 'required': True},
        'dns_domain': {'type': 'str', 'required': True},
    }
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    if module.check_mode:
        module.exit_json()

    try:
        dns_admin = DNSAdmin(
            dns_ip=module.params['dns_ip'],
            dns_admin_key_name=module.params['dns_admin_key_name'],
            dns_admin_key_secret=module.params['dns_admin_key_secret'],
            dns_protocol=module.params['dns_protocol'],
        )
        result = dns_admin.validate(
            dns_zone=module.params['dns_zone'],
            dns_domain=module.params['dns_domain'],
        )
        module.exit_json(**result.ansible_result())
    except DNSException as e:
        # Keep the same shape as a successful DNSValidationResult (in
        # particular, 'validated') even on failure, in case this is ever
        # retried with `until: <result>.validated` the way idp_validate is.
        result = DNSValidationResult(changed=False, msg=e.msg, validated=False)
        module.fail_json(**result.ansible_result())


def main():
    run_module()


if __name__ == '__main__':
    main()
