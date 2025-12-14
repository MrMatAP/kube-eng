Role Name
=========

mrmat.kube_eng.create_namespace

Requirements
------------

None

Role Variables
--------------

| Variable | Type | Required | Default | Description                                                          |
|----------|------|----------|---------|----------------------------------------------------------------------|
| name     | str  | true     | N/A     | Name of the namespace                                                |
| mesh     | str  | false    | istio   | The mesh currently in use. One of 'none', 'istio' or 'istio-ambient' |

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
      mesh: "{{ cluster.mesh.kind }}"
```

License
-------

MIT

Author Information
------------------

MrMatAP
