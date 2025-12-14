Role Name
=========

mrmat.kube_eng.bind_configuration

Requirements
------------

None

Role Variables
--------------

| Variable        | Type | Required | Default                                                       | Description                                       |
|-----------------|------|----------|---------------------------------------------------------------|---------------------------------------------------|
| bind_executable | str  | true     | N/A                                                           | Path to the `named` executable                    |
| bind_config_path        | str  | true     | N/A                                                           | Directory in which the BIND resolver operates     |
| forwarders      | str  | false    | 8.8.8.8; 4.4.4.4; 2001:4860:4860::8888; 2001:4860:4860::8844; | IP address(es) where DNS queries are forwarded to |
| cluster_domain          | str  | true     | N/A                                                           | Name of the cluster_domain to authoritatively host        |
| bind_key        | str  | true     | N/A                                                           | TSIG key to use                                   |

Dependencies
------------

None

Example Playbook
----------------

```
---
- name: Create and configure the host infrastructure
  hosts: localhost
  tasks:
  - name: Template the BIND resolver configuration
    ansible.builtin.import_role:
      name: mrmat.kube_eng.bind_configuration
    vars:
      bind_executable: "{{ host.tools.named }}"
      bind_config_path: "{{ dist_dir }}/bind"
      forwarders: "{{ host.bind.forwarders }}"
      cluster_domain: "{{ cluster_name }}.k8s"
      bind_key: "{{ admin_password }}"
```

License
-------

MIT

Author Information
------------------

MrMatAP
