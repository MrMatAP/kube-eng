Role Name
=========

mrmat.kube_eng.kind_configuration

Requirements
------------

None

Role Variables
--------------

| Variable              | Type | Required | Default            | Description                                                              |
|-----------------------|------|----------|--------------------|--------------------------------------------------------------------------|
| control_plane_nodes   | int  | false    | 1                  | Number of control plane nodes                                            |
| worker_nodes          | int  | false    | 3                  | Number of worker nodes                                                   |
| cluster_name          | str  | false    | kube-eng           | Name of the cluster                                                      |
| directory             | str  | true     | N/A                | Path to the directory to hold kind configuration                         |
| ca_file_path          | str  | true     | N/A                | Path to the CA trust file which has signed the air gapped registry certificate |
| airgap_registry_name  | str  | true     | N/A                | Name of the airgap registry                                              |
| pod_subnet_cidr       | str  | true     | N/A                | Pod subnet CIDR                                                          |
| service_subnet_cidr   | str  | true     | N/A                | Service subnet CIDR                                                      |
| cni                   | str  | false    | kind               | CNI plugin to use for the cluster                                        |
| oidc_discovery_url    | str  | true     | N/A                | OIDC discovery URL for the API server (e.g. https://idp.example.com/realms/master) |
| oidc_issuer_url       | str  | true     | N/A                | OIDC issuer URL for the API server (e.g. https://idp.example.com/realms/master)    |
| oidc_client_id        | str  | true     | N/A                | OIDC client ID registered in the IDP for the Kubernetes cluster          |
| oidc_username_claim   | str  | false    | preferred_username | JWT claim to use as the username                                         |
| oidc_groups_claim     | str  | false    | groups             | JWT claim to use as the user's groups                                    |

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
      oidc_discovery_url: "{{ cluster.oidc.discovery_url }}"
      oidc_issuer_url: "{{ cluster.oidc.issuer_url }}"
      oidc_client_id: "{{ cluster.oidc.client_id }}"
      oidc_username_claim: "{{ cluster.oidc.username_claim }}"
      oidc_groups_claim: "{{ cluster.oidc.groups_claim }}"

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
