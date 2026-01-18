Role Name
=========

mrmat.kube_eng.kind_configuration

Requirements
------------

None

Role Variables
--------------

| Variable             | Type | Required | Default  | Description                         |
|----------------------|------|----------|----------|-------------------------------------|
| control_plane_nodes  | int  | false    | 1        | Number of control plane nodes       |
| worker_nodes         | int  | false    | 3        | Number of worker nodes              |
| cluster_name         | str  | false    | kube-eng | Name of the cluster                 |
| directory            | str  | true     | N/A      | Path to the configuration directory |
| airgap_registry_name | str  | true     | N/A      | Name of the airgap registry         |
| pod_subnet_cidr      | str  | true     | N/A      | Pod subnet CIDR                     |
| service_subnet_cidr  | str  | true     | N/A      | Service subnet CIDR                 |
| cni                  | str  | false    | kind     | CNI plugin to use                   |

Dependencies
------------

None

Example Playbook
----------------

```
---
- name: Create a cluster
  hosts: localhost
  tasks:
    - name: Template the cluster configuration
      ansible.builtin.import_role:
        name: kind_configuration
      vars:
      control_plane_nodes: "{{ cluster.control_plane_nodes | int }}"
      worker_nodes: "{{ cluster.worker_nodes | int }}"
      cluster_name: "{{ cluster.name }}"
      directory: "{{ host.tool.kind.config_path }}"
      ca_file_path: "{{ cluster.pki.config_path }}/ca.pem"
      airgap_registry_name: "{{ host.registry.name }}"
      pod_subnet_cidr: "{{ cluster.pod_subnet_cidr }}"
      service_subnet_cidr: "{{ cluster.service_subnet_cidr }}"
      cni: "{{ cluster.cni.kind }}"

    - name: Create the cluster
      kind_cluster:
          name: "{{ cluster.name }}"
          config_file: "{{ host.tool.kind.config_path }}/config.yaml"
          tool_kind: "{{ host.tool.kind.path }}"
          state: present
```

License
-------

MIT

Author Information
------------------

MrMatAP
