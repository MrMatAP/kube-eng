Role Name
=========

mrmat.kube_eng.cloud_provider_kind_configuration

Requirements
------------

None

Role Variables
--------------

| Variable                | Type | Required | Default                                                                                                                       | Description                                                     |
|-------------------------|------|----------|-------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------|
| cloud_provider_kind_url | str  | false    | https://github.com/kubernetes-sigs/cloud-provider-kind/releases/download/v0.6.0/cloud-provider-kind_0.6.0_darwin_arm64.tar.gz | URL from where to obtain cloud-provider-kind                    |
| cloud_provider_kind_dir | str  | true     | N/A                                                                                                                           | Path to the the directory in which cloud-provider-kind operates |

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
  - name: Template the cloud-provider-kind configuration
  ansible.builtin.import_role:
    name: mrmat.kube_eng.cloud_provider_kind_configuration
  vars:
    cloud_provider_kind_url: "{{ host.cloud_provider_kind.url }}"
    cloud_provider_kind_dir: "{{ dist_dir }}/cloud-provider-kind"
```

License
-------

MIT

Author Information
------------------

MrMatAP
