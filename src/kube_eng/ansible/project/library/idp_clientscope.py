# ruff: noqa: C408
#!/usr/bin/python

from keycloak import KeycloakAdmin

DOCUMENTATION = r"""
---
module: idp_clientscope_roles
short_description: Assert top-level roles in client scope
description:
- Create or update an IdP Client Scope
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
    idp_ca_path:
        description: Path to the truststore which has signed the IdP certificate
        required: true
        type: str
    name:
        description: Name of the roles client scope
        required: true
        type: str
    description:
        description: Description of the roles client scope
        required: true
        type: str
    client_id:
        description: Client-id for which this client scope applies
        required: true
        type: str
author:
- MrMat (@MrMatAP)
"""

EXAMPLES = r"""
- name: Validate IdP connectivity and entitlements
  idp_clientscope_roles:
    idp_url: https://idp.nostromo.k8s:8443
    idp_admin_user: admin
    idp_admin_password: secret
    idp_realm: master
    idp_ca_path: /path/to/truststore.pem
    name: client-rolescopes
    description: Add top-level roles to tokens issued for the client
"""

RETURN = r"""
changed:
  description: Whether a change was actually performed
  type: bool
msg:
  description: Output message
  type: str
"""

from ansible.module_utils.basic import AnsibleModule

def setup_module() -> AnsibleModule:
    module_args = dict(
        idp_url=dict(type='str', required=True),
        idp_admin_user=dict(type='str', required=True),
        idp_admin_password=dict(type='str', required=True, no_log=True),
        idp_realm=dict(type='str', required=True),
        idp_ca_path=dict(type='str', required=True),
        name=dict(type='str', required=True),
        description=dict(type='str', required=True),
        client_id=dict(type='str', required=True)
    )
    return AnsibleModule(argument_spec=module_args, supports_check_mode=True)

def execute(module: AnsibleModule) -> dict:
    idp_admin = KeycloakAdmin(
        server_url=module.params['idp_url'],
        username=module.params['idp_admin_user'],
        password=module.params['idp_admin_password'],
        realm_name=module.params['idp_realm'],
        verify=module.params['idp_ca_path']
    )
    client_scope = idp_admin.get_client_scope_by_name(client_scope_name=module.params['name'])
    if client_scope is None:
        idp_admin.create_client_scope()
    return dict(changed=True, msg='Done')

def run_module():
    result = dict(changed=False, msg='')
    module = setup_module()
    if module.check_mode:
        module.exit_json(**result)
    try:
        result = execute(module)
        module.exit_json(**result)
    except Exception as e:
        module.fail_json(msg='An exception occurred', exception=e)


def main():
    run_module()


if __name__ == '__main__':
    main()
