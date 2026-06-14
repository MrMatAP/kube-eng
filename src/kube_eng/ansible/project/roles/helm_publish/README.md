Role Name
=========

helm_publish

Requirements
------------

None

Role Variables
--------------

| Variable           | Type | Required | Default                | Description                         |
|--------------------|------|----------|------------------------|-------------------------------------|
| helm_tool_path     | str  | false    | /opt/homebrew/bin/helm | Path to the Helm binary             |
| chart_version      | str  | false    | 0.0.0-dev0             | Version of the Helm chart           |
| chart_name         | str  | true     | N/A                    | Name of the Helm chart              |
| chart_src_path     | str  | true     | N/A                    | Path to the chart source directory  |
| chart_pkg_path     | str  | true     | N/A                    | Path to the chart package directory |
| chart_registry_url | str  | true     | N/A                    | URL of the Helm chart registry      |

Dependencies
------------

None

Example Playbook
----------------

```
---
- name: (Re-)publish the Helm charts
  hosts: localhost
  tasks:
  - name: Publish the Helm charts
    ansible.builtin.include_role:
      name: helm_publish
    vars:
      helm_tool_path: "{{ host.tool.helm.path }}"
      chart_version: "{{ host.tool.helm.chart_version }}"
      chart_name: "kube-eng-istio"
      chart_src_path: "{{ host.tool.helm.chart_path }}/kube-eng-istio"
      chart_pkg_path: "{{ host.tool.helm.packaged_chart_path }}"
      chart_registry_url: "oci://reg.mrmat.org:5000/kube-eng"
```

License
-------

MIT

Author Information
------------------

MrMatAP
