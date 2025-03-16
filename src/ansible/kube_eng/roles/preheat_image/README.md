Role Name
=========

Preheat an image into the local airgapped registry

Requirements
------------

None

Role Variables
--------------

| Variable        | Type | Required | Default        | Description                                             |
|-----------------|------|----------|----------------|---------------------------------------------------------|
| airgap_registry | str  | false    | localhost:5001 | Name of the airgapped registry accessible from the host |
| registry        | str  | true     | N/A            | Remote registry of the image to preheat                 |
| repository      | str  | true     | N/A            | Remote repository of the image to preheat               |
| image           | str  | true     | N/A            | Unqualified image name to preheat                       |
| tag             | str  | true     | N/A            | Tag of the image to preheat                             |

Dependencies
------------

None

Example Playbook
----------------

```yaml
# Create and configure all the host infrastructure
---
- name: Create the host infrastructure
  hosts: localhost
  tasks:
  - name: Preheat the Prometheus image(s)
    when: "stack.prometheus.preheat | bool == true"
    ansible.builtin.include_role:
      name: mrmat.kube_eng.preheat_image
    vars:
      airgap_registry: "localhost:{{ host.registry.port }}"
      registry: "{{ item.registry }}"
      repository: "{{ item.repository }}"
      image: "{{ item.image }}"
      tag: "{{ item.tag }}"
    loop: "{{ stack.prometheus.preheat_images }}"
```

License
-------

MIT

Author Information
------------------

MrMatAP
