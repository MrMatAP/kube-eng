Role Name
=========

mrmat.kube_eng.registry_configuration

Requirements
------------

None

Role Variables
--------------

| Variable  | Type | Required | Default | Description                                                     |
|-----------|------|----------|---------|-----------------------------------------------------------------|
| directory | str  | true     | 1       | Path to the directory to hold air gapped registry configuration |

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
    - name: Configure the air gapped registry
      ansible.builtin.import_role:
        name: mrmat.kube_eng.registry_configuration
      vars:
        directory: "{{ dist_dir }}/registry"
```

License
-------

MIT

Author Information
------------------

MrMatAP
