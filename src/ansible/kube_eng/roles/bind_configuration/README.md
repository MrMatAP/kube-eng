Role Name
=========

mrmat.kube_eng.bind_configuration

Requirements
------------

None

Role Variables
--------------

| Variable     | Type | Required | Default | Description                                   |
|--------------|------|----------|---------|-----------------------------------------------|
| resolver_dir | str  | true     | N/A     | Directory in which the resolver operates      |
| forwarder    | str  | false    | 8.8.8.8 | IP address where DNS queries are forwarded to |
| domain       | str  | true     | N/A     | Name of the domain to authoritatively host    |

Dependencies
------------

None

Example Playbook
----------------

```
---
- name: Configure the local resolver
  hosts: localhost
  tasks:
  - name: Template the BIND configuration
    ansible.builtin.import_role:
      name: mrmat.kube_eng.resolver_configuration
    vars:
      resolver_dir: "{{ distdir }}/resolver"
      forwarder: "{{ host.forwarder }}"
      domain: "{{ host.domain }}"
```

License
-------

MIT

Author Information
------------------

MrMatAP
