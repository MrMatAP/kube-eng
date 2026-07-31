#!/usr/bin/python

__metaclass__ = type

DOCUMENTATION = r"""
---
module: idp_validate
short_description: Validate S3 connectivity and entitlements
description:
- Validate S3 connectivity
options:
    idp_url:
        description: The IdP URL
        required: true
        type: str
    idp_admin_user:
        description: The IdP admin user
        required: true
        type: str
    idp_admin_password:
        description: The IdP admin password
        required: true
        type: str
    idp_realm:
        description: The IdP realm
        required: true
        type: str
author:
- MrMat (@MrMatAP)
"""

EXAMPLES = r"""
- name: Validate IdP connectivity and entitlements
  idp_validate:
    idp_url: https://idp.nostromo.k8s:8443
    idp_admin_user: admin
    idp_admin_password: secret
    idp_realm: master
"""

RETURN = r"""
status:
  description: All required entitlements are granted
  type: bool
msg:
  description: Output message
  type: str
"""

from ansible.module_utils.basic import AnsibleModule  # noqa: E402


def run_module():
    module_args = dict(
        idp_url=dict(type='str', required=True),
        idp_admin_user=dict(type='str', required=True),
        idp_admin_password=dict(type='str', required=True, no_log=True),
        idp_realm=dict(type='str', required=True),
        idp_ca_path=dict(type='str', required=True)
    )
    result = dict(status=False, msg='')
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    if module.check_mode:
        module.exit_json(**result)

    try:
        idp_admin = KeycloakAdmin(
            server_url=module.params['idp_url'],
            username=module.params['idp_admin_user'],
            password=module.params['idp_admin_password'],
            realm_name=module.params['idp_realm'],
            verify=module.params['idp_ca_path']
        )
        user_id = idp_admin.get_user_id(module.params['idp_admin_user'])
        if user_id is None:
            result['status'] = False
            result['msg'] = 'Admin user id cannot be found in the realm'
            module.fail_json(**result)
        roles = idp_admin.get_realm_roles_of_user(user_id)
        if any(filter(lambda r: r['name'] == 'admin', roles)):
            result['status'] = True
            result['msg'] = 'Connectivity and entitlements are granted'
        else:
            result['status'] = False
            result['msg'] = 'Admin user lacks sufficient permissions'
        module.exit_json(**result)
    except Exception as e:
        result['status'] = False
        result['msg'] = str(e) or 'Unknown Error'
        module.fail_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
