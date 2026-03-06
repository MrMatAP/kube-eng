Role Name
=========

dns_local_configuration

Requirements
------------

None

Role Variables
--------------

| Variable              | Type | Required | Default                                                       | Description                                                      |
|-----------------------|------|----------|---------------------------------------------------------------|------------------------------------------------------------------|
| dns_local_config_path | str  | true     | N/A                                                           | Directory in which to generate the configuration                 |
| dns_local_zone        | str  | true     | N/A                                                           | Name of the zone to authoritatively host                         |
| dns_local_update_key  | str  | true     | N/A                                                           | TSIG key to use for DDNS updates                                 |

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
      name: dns_local_configuration
    vars:
      dns_local_config_path: "{{ host.dns.config_path }}"
      dns_local_forwarders: "{{ host.dns.forwarders }}"
      dns_local_zone: "{{ host.dns.zone }}"
      dns_local_update_key: "{{ admin_password }}"
```

License
-------

MIT

Author Information
------------------

MrMatAP
