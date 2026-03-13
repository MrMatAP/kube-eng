Role Name
=========

create_namespace

Requirements
------------

None

Role Variables
--------------

| Variable | Type | Required | Default | Description                                                                  |
|----------|------|----------|---------|------------------------------------------------------------------------------|
| name     | str  | true     | N/A     | Name of the namespace                                                        |
| mesh     | str  | false    | istio   | The mesh currently in use. One of 'none', 'istio-sidecar' or 'istio-ambient' |
| waypoint | bool | false    | false   | Enroll this namespace to use an Istio waypoint                               |

Dependencies
------------

None

Example Playbook
----------------

```
---
- name: Create and configure the cluster
  hosts: localhost
  tasks:
  - name: Create a namespace
    ansible.builtin.import_role:
      name: create_namespace
    vars:
      name: "{{ stack.cert_manager.ns }}
      mesh: "{{ cluster.mesh.kind }}"
      waypoint: true
```

License
-------

MIT

Author Information
------------------

MrMatAP
