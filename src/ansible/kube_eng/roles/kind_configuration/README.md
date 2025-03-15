Role Name
=========

mrmat.kube_eng.kind_configuration

Requirements
------------

None

Role Variables
--------------

| Variable            | Type | Required | Default | Description                                |
|---------------------|------|----------|---------|--------------------------------------------|
| control_plane_nodes | int  | false    | 1       | Number of control plane nodes              |
| worker_nodes        | int  | false    | 3       | Number of worker nodes                     |
| config_file         | str  | true     | N/A     | Path to the configuration file to generate |

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
        name: mrmat.kube_eng.kind_configuration
      vars:
      control_plane_nodes: "{{ cluster.control_plane_nodes | int }}"
      worker_nodes: "{{ cluster.worker_nodes | int }}"
      config_file: "{{ distdir }}/kind-config.yaml"

    - name: Create the cluster
      mrmat.kube_eng.kind_cluster:
      name: "{{ cluster_name }}"
      config_file: "{{ distdir }}/kind-config.yaml"
      tool_kind: "{{ tools.kind }}"
      state: present
```

License
-------

MIT

Author Information
------------------

MrMatAP
