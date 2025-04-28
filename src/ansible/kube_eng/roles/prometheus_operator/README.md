prometheus_operator
=========

Deploy the Prometheus operator

Requirements
------------

None

Role Variables
--------------

| Variable | Type | Required | Default | Description                        |
|----------|------|----------|---------|------------------------------------|
| kubectl  | str  | true     | N/A     | Path to kubectl                    |
| ns       | str  | false    | stack   | Desired namespace for the operator |
| registry | str  | false    | quay.io | Registry to pull the images from   |
| version  | str  | false    | v0.82.0 | Version of the operator to install |

Dependencies
------------

None

Example Playbook
----------------

```yaml
---
- name: Deploy the stack
  hosts: localhost
  tasks:
  - name: Deploy Prometheus
    when: "stack.prometheus.enabled | bool == true"
    ansible.builtin.include_role:
      name: mrmat.kube_eng.preheat_image
    vars:
      kubectl: "{{ host.tools.kubectl }}"
      ns: prometheus
      registry: "registry:5000"
      version: v0.81.0
```

License
-------

MIT

Author Information
------------------

MrMatAP
