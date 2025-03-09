#!/usr/bin/python

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

DOCUMENTATION = r'''
---
module: istio
short_description: Manage Istio
description:
- Manage Istio
options:
    profile:
        description: The Istio profile to install
        required: false
        type: str
        choices: ['default', 'demo', 'minimal', 'remote', 'ambient', 'empty', 'preview']
        default: minimal
    alpha_gateway_api:
        description: Enable support for the alpha gateway api
        type: bool
        required: false
        default: false
    namespace:
        description: The namespace in which to install Istio
        required: false
        type: str
        default: istio-system
    state:
        description: The desired state of the installation
        required: false
        type: str
        choices: ['present', 'absent']
        default: present
    tool_kubectl:
        description: Path to the 'kubectl' tool
        required: false
        type: str
        default: /opt/homebrew/bin/kubectl
    tool_istioctl:
        description: Path to the 'istioctl' tool
        required: false
        type: str
        default: /opt/homebrew/bin/istioctl

author:
- MrMat (@MrMatAP)
'''

EXAMPLES = r'''
- name: Install Istio
  mrmat.kube_eng.istio:
    tool_kubectl: /path/to/kubectl
    tool_istioctl: /path/to/istioctl
    alpha_gateway_api: true
    profile: demo
    state: present
  
- name: Uninstall Istio
  mrmat.kube_eng.kind_cluster:
    state: absent
'''

RETURN = r'''
changed:
  description: Wether a change was actually performed
  type: bool
msg:
  description: Output message
  type: str
'''

from ansible.module_utils.basic import AnsibleModule


def run_module():
    module_args = dict(
        profile=dict(type='str', required=False, choices=['default', 'minimal', 'remote', 'ambient', 'empty', 'preview'], default='minimal'),
        namespace=dict(type='str', required=False, default='istio-system'),
        alpha_gateway_api=dict(type='bool', required=False, default=False),
        state=dict(type='str', required=False, default='present', choices=['present', 'absent']),
        tool_kubectl=dict(type='str', required=False, default='/opt/homebrew/bin/kubectl'),
        tool_istioctl=dict(type='str', required=False, default='/opt/homebrew/bin/istioctl'),
    )
    result = dict(
        changed=False,
        msg='',
    )
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    if module.check_mode:
        module.exit_json(**result)

    rc, out, err = module.run_command(check_rc=False,
                                      args=[module.params['tool_kubectl'],
                                       'get', 'svc', 'istiod',
                                       '-n',  module.params['namespace']])
    if rc == 1 and module.params['state'] == 'absent' or rc == 0 and module.params['state'] == 'present':
        result['changed'] = False
        result['msg'] = 'Istio is in desired state'
        return module.exit_json(**result)

    if rc == 1 and module.params['state'] == 'present':
        args = [module.params['tool_istioctl'], 'install', '-y',
                '--set', f'profile={module.params["profile"]}']
        if module.params['alpha_gateway_api']:
            args.extend(['--set', f'values.pilot.env.PILOT_ENABLE_ALPHA_GATEWAY_API=true'])
        rc, out, err = module.run_command(check_rc=True, args=args)
    elif rc == 0 and module.params['state'] == 'absent':
        rc, out, err = module.run_command(check_rc=True,
                                          args=[module.params['tool_istioctl'],
                                                'uninstall', '-y', '--purge'])
    result['msg'] = err
    result['changed'] = True
    if rc != 0:
        result['state'] = module.params['state']
        module.fail_json(**result)
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
