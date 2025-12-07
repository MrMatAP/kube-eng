#!/usr/bin/python

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

DOCUMENTATION = r'''
---
module: mesh
short_description: Manage the cluster mesh
description:
- Manage the cluster mesh
options:
    mesh:
        description: The cluster mesh to deploy
        required: false
        type: str
        choices: ['none', 'istio', 'istio-ambient']
        default: istio-ambient
    namespace:
        description: The namespace in which to install Istio
        required: false
        type: str
        default: istio-system
    edge_kind:
        description: We configure istio depending on the edge we intend to deploy
        type: str
        required: false
        choices: ['none', 'ingress', 'istio', 'istio-gateway-api', 'istio-gateway-api-experimental']
        default: none
    tracing:
        description: Enable support for tracing
        type: bool
        required: false
        default: false
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
- name: Install the cluster mesh
  mrmat.kube_eng.mesh:
    tool_kubectl: /path/to/kubectl
    tool_istioctl: /path/to/istioctl
    state: present
  
- name: Uninstall Istio
  mrmat.kube_eng.kind_cluster:
    state: absent
'''

RETURN = r'''
changed:
  description: Whether a change was actually performed
  type: bool
msg:
  description: Output message
  type: str
'''

from ansible.module_utils.basic import AnsibleModule


def run_module():
    module_args = dict(
        mesh=dict(type='str', required=False, choices=['none', 'istio', 'istio-ambient'], default='istio'),
        namespace=dict(type='str', required=False, default='istio-system'),
        edge_kind=dict(type='str', required=False, choices=['none', 'ingress', 'istio', 'istio-gateway-api', 'istio-gateway-api-experimental'], default='none'),
        tracing=dict(type='bool', required=False, default=False),
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
    if module.params['mesh'] == 'none':
        module.exit_json(**result)
    if module.params['mesh'] not in ['istio', 'istio-ambient']:
        result['changed'] = False
        result['msg'] = 'Unknown mesh type'
        return module.exit_json(**result)

    rc, out, err = module.run_command(check_rc=False,
                                      args=[module.params['tool_kubectl'],
                                       'get', 'svc', 'istiod',
                                       '-n',  module.params['namespace']])
    if (rc == 1 and module.params['state'] == 'absent') or \
       (rc == 0 and module.params['state'] == 'present'):
        result['changed'] = False
        result['msg'] = 'Mesh is in desired state'
        return module.exit_json(**result)

    if rc == 1 and module.params['state'] == 'present':
        profile = 'ambient' if module.params['mesh'] == 'istio-ambient' else 'minimal'
        args = [module.params['tool_istioctl'], 'install', '-y',
                '--set', f'profile={profile}']
        if module.params['edge_kind'] == 'istio-gateway-api-experimental':
            args.extend(['--set', 'values.pilot.env.PILOT_ENABLE_ALPHA_GATEWAY_API=true'])
        if module.params['tracing']:
            args.extend(['--set', 'meshConfig.enableTracing=true'])
        rc, out, err = module.run_command(check_rc=True, args=args)

    if rc == 0 and module.params['state'] == 'absent':
        rc, out, err = module.run_command(check_rc=True,
                                          args=[module.params['tool_istioctl'],
                                                'uninstall', '-y', '--purge'])
    result['msg'] = err
    result['changed'] = True
    if rc != 0:
        result['state'] = module.params['state']
        return module.fail_json(**result)
    return module.exit_json(**result)

def main():
    run_module()


if __name__ == '__main__':
    main()
