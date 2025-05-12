Role Name
=========

mrmat.kube_eng.create_namespace

Requirements
------------

None

Role Variables
--------------

| Variable      | Type | Required | Default | Description           |
|---------------|------|----------|---------|-----------------------|
| name          | str  | true     | N/A     | Name of the namespace |
| istio_profile | str  | false    | ambient | The Istio Profile     |

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
      name: mrmat.kube_eng.create_namespace
    vars:
      name: "{{ stack.cert_manager.ns }}
      istio_profile: "{{ cluster.istio_profile }}"
```

License
-------

MIT

Author Information
------------------

MrMatAP
