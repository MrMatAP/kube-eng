Role Name
=========

mrmat.kube_eng.issue_tls_certificate

Requirements
------------

None

Role Variables
--------------

| Variable              | Type | Required | Default | Description                                                                        |
|-----------------------|------|----------|---------|------------------------------------------------------------------------------------|
| pki_config_path       | str  | true     | N/A     | Directory in which the key, CSR and certificate files will be written              |
| pki_key_filename      | str  | true     | N/A     | Filename (not path) of the generated private key                                   |
| pki_csr_filename      | str  | true     | N/A     | Filename (not path) of the intermediate CSR                                        |
| pki_cert_filename     | str  | true     | N/A     | Filename (not path) of the signed certificate                                      |
| pki_common_name       | str  | true     | N/A     | Common name (CN) for the certificate subject                                       |
| pki_subject_alt_names | list | true     | N/A     | List of Subject Alternative Names (e.g. ["DNS:host.example.com", "DNS:localhost"]) |
| pki_key_type          | str  | true     | N/A     | Key algorithm to use (RSA, ECC, etc.)                                              |
| pki_key_curve         | str  | true     | N/A     | Elliptic curve to use when pki_key_type is ECC (e.g. secp256r1)                    |
| pki_key_size          | int  | true     | N/A     | Key size in bits when pki_key_type is RSA                                          |
| pki_ca_path           | str  | true     | N/A     | Path to the CA certificate used to sign the new certificate                        |
| pki_ca_key_path       | str  | true     | N/A     | Path to the CA private key used to sign the new certificate                        |
| pki_cert_validity     | str  | true     | N/A     | Expiry date for the signed certificate (e.g. +3650d)                               |

Dependencies
------------

None

Example Playbook
----------------

```yaml
- name: Example invocation of issue_tls_certificate
  hosts: localhost
  tasks:
  - name: Issue a TLS certificate
    ansible.builtin.import_role:
      name: mrmat.kube_eng.issue_tls_certificate
    vars:
      pki_config_path: "{{ infra.idp.config_path }}"
      pki_key_filename: idp_key.pem
      pki_csr_filename: idp_cert.csr
      pki_cert_filename: idp_cert.pem
      pki_common_name: "{{ infra.idp.client_fqdn }}"
      pki_subject_alt_names:
      - "DNS:{{ infra.idp.client_fqdn }}"
      - "DNS:{{ infra.idp.name }}.{{ infra.net.name }}"
      - "DNS:{{ infra.idp.name }}"
      - "DNS:localhost"
      pki_key_type: "{{ infra.pki.key_type }}"
      pki_key_curve: "{{ infra.pki.key_curve }}"
      pki_key_size: "{{ infra.pki.key_size }}"
      pki_ca_path: "{{ infra.pki.ca_path }}"
      pki_ca_key_path: "{{ infra.pki.ca_key_path }}"
      pki_cert_validity: "{{ infra.pki.crt_validity }}"
```

License
-------

MIT

Author Information
------------------

MrMatAP
