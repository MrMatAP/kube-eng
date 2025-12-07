#!/usr/bin/python

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

DOCUMENTATION = r'''
---
module: kind_cluster
short_description: Manage kind clusters
description:
- Manage kind clusters
options:
    name:
        description: The name of the cluster
        required: true
        type: str
    image:
        description: The node image to use
        required: false
        default: ""
        type: str
    config_file:
        description: Path to the cluster configuration file
        required: false
        type: str
    state:
        description: The desired state of the cluster
        required: false
        type: str
        choices: ['present', 'absent']
        default: present
    tool_kind:
        description: Path to the 'kind' tool
        required: false
        type: str
        default: /opt/homebrew/bin/kind

author:
- MrMat (@MrMatAP)
'''

EXAMPLES = r'''
- name: Create a cluster
  mrmat.kube_eng.kind_cluster:
    name: sample-cluster
    config_file: /path/to/config.yaml
    tool_kind: /path/to/kind
    state: present
  
- name: Destroy a cluster
  mrmat.kube_eng.kind_cluster:
    name: sample-cluster
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
        name=dict(type='str', required=True),
        image=dict(type='str', required=False, default=''),
        config_file=dict(type='str', required=False),
        state=dict(type='str', required=False, default='present', choices=['present', 'absent']),
        tool_kind=dict(type='str', required=False, default='/opt/homebrew/bin/kind'),
    )
    result = dict(
        changed=False,
        msg='',
    )
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    if module.check_mode:
        module.exit_json(**result)

    rc, out, err = module.run_command(check_rc=True,
                                      args=[module.params['tool_kind'],
                                       'get', 'clusters'])
    if rc != 0:
        result['msg'] = 'Failed to get clusters'
        result['msg'] = err
        module.fail_json(**result)
    clusters = out.splitlines()
    cluster_state = 'present' if module.params['name'] in clusters else 'absent'
    if cluster_state == module.params['state']:
        result['state'] = module.params['state']
        result['msg'] = 'Cluster is in desired state'
        module.exit_json(**result)
    match module.params['state']:
        case 'absent':
            rc, out, err = module.run_command(check_rc=True,
                                              args=[module.params['tool_kind'],
                                                    'delete', 'cluster', '-n',
                                                    module.params['name']])
        case 'present':
            kind_command = [
                module.params['tool_kind'],
                'create', 'cluster',
                '--name', module.params['name'],
                '--config', module.params['config_file']]
            if module.params['image'] != '':
                kind_command.extend(['--image', module.params['image']])
            rc, out, err = module.run_command(check_rc=True,args=kind_command)
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
