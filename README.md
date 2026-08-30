# kube-eng

Tooling for a local Kubernetes cluster, suitable for local engineering. Also airgapped, on a plane.

> **Note:** This project is perpetually under construction.

## How to use this

kube-eng provides both a command-line interface (CLI) and a text-based user interface (TUI) for managing your local Kubernetes cluster. 

```shell
$ uv run kube-eng <cmd> <parameters>
```

There are four major stages to create your cluster:

* `config` - Review configuration of the cluster. The defaults will set up local infrastructure.
* `infra-apply` - will configure any host infrastructure you may need, such as DNS, a local PKI and the registry
* `cluster-apply` - will deploy the cluster and core supporting services 
* `stack-apply` - will deploy the remaining stack

## config

Use `uv run kube-eng config get` and `uv run kube-eng config set` commands to review and configure the kube-eng 
cluster.

```shell
# See all configuration
$ uv run kube-eng config list 

# Get the host, cluster and stack configuration roots
$ uv run kube-eng config get host
$ uv run kube-eng config get host
$ uv run kube-eng config get stack

# Get just the host DNS configuration
$ uv run kube-eng config get host.dns

# Disable the local DNS server
$ uv run kube-eng config set host.dns.enabled false
```

## infra-apply

`uv run kube-eng infra-apply` will create the local host infrastructure you configured.

> **IMPORTANT (DNS):**<br/>
> kube-eng cluster expect DNS and creating them will register tooling in the configured DNS server. Enabling the 
> local DNS server will configure it accordingly so kube-eng can make these updates. If you disable the local DNS 
> server then you must configure the cluster to point to a DNS server that supports updates and provide a key with 
> the necessary permissions to make that update. 
> If you configure a local DNS server then you must point your host towards it. 

> **IMPORTANT (PKI):**<br/>
> kube-eng will create a local PKI for you and protect all endpoints using certificates created with it. You must 
> configure your host and any clients of these endpoints to trust CA kube-eng creates. The CA is re-used if it 
> remains present, so you only need to re-establish trust on the host when you re-create it.
> Doubleclick `~/.kube-eng/pki/ca.pem` to import it or run `security add-certificates ~/.kube-eng/pki/ca.pem`, 
> followed by marking the imported CA certificate as 'Always Trust' in the Keychain Utility.

### Container registry

`infra-apply` runs a local OCI registry ([zot](https://zotregistry.dev/)) and publishes the kube-eng Helm charts
into it. Humans log into its UI through the IdP (`infra.idp`). Automated chart pushes (`infra-apply`,
`helm-repackage`) use a dedicated htpasswd account instead: `infra.registry.admin_username` (default `kube-eng`)
with `infra.registry.admin_password` (generated, readable via `uv run kube-eng config get infra.registry.admin_password`).

> **LIMITATION (registry auth):**<br/>
> This split is a workaround. zot (through v2.1.20) cannot run OIDC bearer auth and browser OpenID SSO at the same
> time — enabling `http.auth.bearer` makes zot skip its whole session/OpenID/htpasswd setup, so `/zot/auth/login`
> then fails with `unrecognized openid provider`. Because kube-eng needs the browser SSO, chart pushes fall back to
> a static htpasswd credential rather than an IdP-issued token. See
> `docs/adr/0004-registry-push-auth-htpasswd-account.md`.

> **LIMITATION (anonymous pull):**<br/>
> zot also sends a `WWW-Authenticate: Basic` header on the `/v2/` ping even when it returns `200` and anonymous
> read is allowed (not RFC 7235 compliant). Standard clients — `docker`, containerd — then refuse to proceed
> without credentials, so anonymous pull can't be relied on. kube-eng works around this by authenticating every
> path as the htpasswd account: `infra-apply` runs `docker login` on the host, and the kind nodes carry it as a
> static header in each containerd `hosts.toml`. zot's `anonymousPolicy: ["read"]` is kept only as a fallback.

## cluster-apply

`uv run kube-eng cluster-apply` will create the cluster. You can monitor this via `kubectl get po -Aw`. This will 
register the PKI and also deploy it's 'edge'. By default, that edge is using the Kubernetes Gateway API via Istio.

> **IMPORTANT:**<br/>
> Once cluster-apply successfully concludes, you must start `sudo cloud-provider-kind` in a separate terminal window 
> and keep it running. cloud-provider-kind will discover the edge gateway and inject a local IP address to your 
> localhost interface. All communication with endpoints exposed by the cluster occur via that local IP address.

Note that kind will update your kubectl configuration with an mTLS context for administrative use. kube-eng 
registers the cluster in the configured IdP as well. The IdP responds by default on `https://<host.idp.name>.<cluster.
name>.<host.dns.zone>:<host.idp.port>`. On a host called 'covenant', this will be 'https://idp.covenant.k8s:8443' by 
default. The default username for the IdP is 'admin'. It's password can be obtained via `uv run kube-eng config.get 
admin_password`. You can declare a user in the IdP and grant it one of the three preconfigured client roles:

* kube-eng-admin - has the `cluster-admin` cluster-role
* kube-eng-viewer - has the `view` cluster-role
* kube-eng-user - has the `edit` cluster-role

These roles are assigned to users within the IdP and prefixed with `oidc:` for the Kubernetes API server (see 
`src/kube_eng/ansible/project/roles/kind_configuration/templates/kube-eng-auth.yaml.j2`).

kind switches the kubectl context to the admin context it generates by default. `cluster-apply` will create two new 
'users' and contexts in your kubeconfig, one called `kube-eng-<cluster.name>-console` and another 
`kube-eng-<cluster.name>-idp`. The console variant is for when no local browser is available. Switch to these to perform 
IdP authenticated logins. It is a prerequisite to have krew and oidc-login installed for these.

```shell
# Pre-requisites
$ brew install krew
$ kubectl krew install oidc-login

# Switch context
$ k config use-context kube-eng-<cluster.name>-idp

# This will open a browser to authenticate
$ k get po -A
```

> **Note:**<br/
> Caches are re-used when logging via browser. Be sure to log out of the IdP when you just came in as admin to 
> define your user. It is useful to clear caches with `kubectl oidc-login clean`.

## stack-apply

`uv run kube-eng stack-apply` will deploy the chosen infrastructural stack onto your cluster. This will fail early when 
`cloud-provider-kind` has not yet injected the local IP address. You can verify whether it has via `kubectl get svc 
-n edge`. If the 'EXTERNAL-IP' is set then `cloud-provider-kind` has done what is needed.

### How to build this

At this stage of development, you are bound to operate within the sources, clone the repository, then

```shell
$ uv sync
$ . .venv/bin/activate
```

## Debugging

### Debugging OIDC

You can use the `oidc-login` CLI to debug OIDC issues:

```shell
$ kubectl oidc-login setup --oidc-issuer-url=https://idp.nostromo.k8s:8443/realms/master 
--oidc-client-id=kube-eng-nostromo --grant-type=authcode --oidc-redirect-url=http://localhost:8000
```

### Debug pod

`var/debug/debug-pod.yaml` provides a minimal pod with `curl` available, useful for testing connectivity and HTTP endpoints from within the cluster.

```shell
# Deploy
$ kubectl apply -f var/debug/debug-pod.yaml

# Wait for it to be running
$ kubectl wait --for=condition=Ready pod/debug

# Exec into it
$ kubectl exec -it debug -- sh

# Clean up when done
$ kubectl delete -f var/debug/debug-pod.yaml
```

To target a specific namespace, pass `-n <namespace>` to each command. For example, to test a service from within the `prometheus` namespace:

```shell
$ kubectl apply -n prometheus -f var/debug/debug-pod.yaml
$ kubectl exec -n prometheus -it debug -- sh
```
