Role Name
=========

mrmat.kube_eng.registry_configuration

Templates the local registry (zot) configuration: `config.json` (OpenID SSO for
humans + an htpasswd push account), the `oidc.json` credentials file, and the
htpasswd file itself (via the `registry_htpasswd` module). See
`docs/adr/0004-registry-push-auth-htpasswd-account.md`.

Requirements
------------

None

Role Variables
--------------

| Variable            | Type | Required | Default | Description                                                          |
|---------------------|------|----------|---------|--------------------------------------------------------------------|
| directory           | str  | true     | N/A     | Directory holding the registry configuration                        |
| external_endpoint   | str  | true     | N/A     | External endpoint of the registry (`http.externalUrl`)              |
| oidc_issuer         | str  | true     | N/A     | OIDC issuer URL for the registry's browser SSO login                |
| oidc_client_id      | str  | true     | N/A     | IdP client id for the registry                                      |
| oidc_client_secret  | str  | true     | N/A     | IdP client secret for the registry (no_log)                         |
| oidc_callback_url   | str  | true     | N/A     | OIDC callback URL, allow-listed as a login redirect origin          |
| htpasswd_username   | str  | true     | N/A     | Username of the htpasswd push account (referenced by the policy)    |
| htpasswd_password   | str  | true     | N/A     | Password for the htpasswd push account, hashed into the file (no_log)|

Dependencies
------------

None

Example Playbook
----------------

```
- name: Configure the registry
  ansible.builtin.import_role:
    name: mrmat.kube_eng.registry_configuration
  vars:
    directory: "{{ infra.registry.config_path }}"
    external_endpoint: "{{ infra.registry.http_endpoint }}"
    oidc_issuer: "{{ infra.idp.issuer_url }}"
    oidc_client_id: "{{ infra.registry.client_id }}"
    oidc_client_secret: "{{ registry_idp_client.client_secret }}"
    oidc_callback_url: "{{ infra.registry.callback_url }}"
    htpasswd_username: "{{ infra.registry.admin_username }}"
    htpasswd_password: "{{ infra.registry.admin_password }}"
```

License
-------

MIT

Author Information
------------------

MrMatAP
