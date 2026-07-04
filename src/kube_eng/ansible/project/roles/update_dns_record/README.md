Role Name
=========

mrmat.kube_eng.update_dns_record

Requirements
------------

None

Role Variables
--------------

| Variable          | Type | Required | Default | Description                                                       |
|-------------------|------|----------|---------|-------------------------------------------------------------------|
| dns_key_name      | str  | true     | N/A     | TSIG key name used to authenticate the DDNS update                |
| dns_key_secret    | str  | true     | N/A     | TSIG key secret used to authenticate the DDNS update              |
| dns_key_algorithm | str  | true     | N/A     | TSIG key algorithm (e.g. hmac-sha256)                             |
| dns_server        | str  | true     | N/A     | Address of the authoritative DNS server to send the update to     |
| dns_port          | int  | false    | 53      | UDP/TCP port on the DNS server                                    |
| dns_protocol      | str  | true     | N/A     | Transport protocol to use (tcp or udp)                            |
| dns_record        | str  | true     | N/A     | Fully-qualified domain name to update, including the trailing dot |
| dns_ttl           | int  | true     | N/A     | Time-to-live for the DNS record in seconds                        |
| dns_value         | str  | true     | N/A     | IP address to set for the A record                                |

Dependencies
------------

None

Example Playbook
----------------

```yaml
- name: Example invocation of update_dns_record
  hosts: localhost
  tasks:
  - name: Update DNS A record
    ansible.builtin.import_role:
      name: mrmat.kube_eng.update_dns_record
    vars:
      dns_key_name: "{{ host.dns.key_name }}"
      dns_key_secret: "{{ host.dns.key_secret }}"
      dns_key_algorithm: "{{ host.dns.key_algorithm }}"
      dns_server: "{{ host.dns.server }}"
      dns_protocol: "{{ host.dns.protocol }}"
      dns_record: "myservice.example.com."
      dns_ttl: "{{ host.dns.ttl | int }}"
      dns_value: "192.168.1.10"
```

License
-------

MIT

Author Information
------------------

MrMatAP
