Role Name
=========

mrmat.kube_eng.edge

Requirements
------------

None

Role Variables
--------------

| Variable    | Type | Required | Default     | Description                                                                                                 |
|-------------|------|----------|-------------|-------------------------------------------------------------------------------------------------------------|
| kind        | str  | false    | gateway-api | What kind of edge to create. One of 'istio', 'istio-gateway-api', 'istio-gateway-api-experimental', 'nginx' |
| ns          | str  | false    | edge        | What namespace to create the edge in                                                                        |
| config_file | str  | true     | N/A         | Config file to create the edge kube yaml in (for potential later manual application)                        |

Dependencies
------------

None

Example Playbook
----------------

```yaml
---
- name: Create a cluster
  hosts: localhost
  tasks:
    - name: Template the cluster configuration
      ansible.builtin.import_role:
        name: mrmat.kube_eng.cluster_configuration
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

    - name: Install Edge
      ansible.builtin.import_role:
        name: mrmat.kube_eng.edge
      vars:
        kind: "{{ cluster.edge }}"
        ns: "{{ cluster.edge_ns }}"
        config_file: "{{ distdir }}/edge.yaml"
```

License
-------

MIT

Author Information
------------------

MrMatAP
