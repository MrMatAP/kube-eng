Role Name
=========

mrmat.kube_eng.cloud_provider_mdns_configuration

Requirements
------------

None

Role Variables
--------------

| Variable                 | Type | Required | Default | Description                                                     |
|--------------------------|------|----------|---------|-----------------------------------------------------------------|
| tool_cloud_provider_mdns | str  | false    | N/A     | Path to the cloud-provider-mdns executable                      |
| directory                | str  | true     | N/A     | Path to the the directory in which cloud-provider-mdns operates |
| user                     | str  | true     | N/A     | User to run cloud-provider-mdns with                            |


Dependencies
------------

None

Example Playbook
----------------

```yaml
---
- name: Create the host infrastructure
  hosts: localhost
  tasks:
  - name: Template the cloud-provider-mdns configuration
  ansible.builtin.import_role:
    name: mrmat.kube_eng.cloud_provider_mdns_configuration
  vars:
    cloud_provider_mdns_executable: "{{ cloud_provider_mdns }}"
    directory: "{{ dist_dir }}/cloud-provider-mdns"
    user: "{{ user_id }}"
```

License
-------

MIT

Author Information
------------------

MrMatAP
