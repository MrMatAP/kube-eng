from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.dns_utils import DNSAdmin, DNSException


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
        'dns_record': {'type': 'str', 'required': True},
        'dns_value': {'type': 'str', 'required': True},
        'dns_ttl': {'type': 'int', 'required': True},
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
        result = dns_admin.record_set(
            dns_zone=module.params['dns_zone'],
            dns_record=module.params['dns_record'],
            dns_value=module.params['dns_value'],
            dns_ttl=module.params['dns_ttl'],
        )
        module.exit_json(**result.ansible_result())
    except DNSException as e:
        module.fail_json(**e.ansible_result())


def main():
    run_module()


if __name__ == '__main__':
    main()
