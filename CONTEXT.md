# kube-eng

`kube-eng` provisions and manages a local Kubernetes cluster for local engineering. It wraps Ansible playbooks that provision host-level infrastructure (Docker containers) and a `kind` Kubernetes cluster.

## Language

**Host**:
The tool binaries needed on the operator's machine to run kube-eng itself (docker, kind, kubectl, helm, cloud-provider-kind). Paths only — not a running service.

**Infra**:
The infrastructure services the Cluster and Stack depend on: DNS, PostgreSQL, IdP, S3, OCI Registry, Kafka — plus the Network and Root CA that support them. Each service is either Local or Remote via its Provider.

**Provider**:
Whether an Infra service is Local (provisioned by kube-eng as a Docker container on the host) or Remote (an existing service hosted elsewhere that kube-eng only configures a client for).

**Root CA** (`infra.pki`):
The general-purpose certificate authority kube-eng generates on the host. Its key/certificate live under `var/pki/` and are trusted by both the Local Docker infra services and the Cluster. Issues certificates for Infra services via the `issue_tls_certificate` role.
_Avoid_: PKI on its own (ambiguous with Cluster PKI), CA on its own

**Cluster PKI** (`cluster.pki`):
cert-manager deployed inside the Cluster. It mints and manages its own certificate authority, independent of the Root CA, and issues runtime certificates for the Stack.
_Avoid_: PKI on its own (ambiguous with Root CA)

**Cluster**:
The `kind` Kubernetes cluster itself and its platform-level concerns: CNI, service mesh (Istio), Cluster PKI (cert-manager), and the ingress/edge gateway.

**Stack**:
The observability and auth applications deployed onto the Cluster: Prometheus, Alloy, Loki, Grafana, Tempo, Kiali.

**IdP** (`infra.idp`):
The identity provider (Keycloak) that authenticates access to kube-eng's own Infra services (e.g. S3). Provisioned as Local infra (Docker container) or Remote, following the same Provider pattern as the other Infra services.
_Avoid_: `stack.keycloak` (legacy name, being retired — see ADR)

**Registry** (`infra.registry`):
The OCI registry (zot, locally) that stores the Helm charts kube-eng packages and publishes. Humans get an interactive OIDC login against `infra.idp` mapped to IdP Client Roles; automated chart pushes (`helm_publish`) use the Push Account instead, because zot can't run OIDC bearer auth and browser SSO together. Provisioned as Local infra (Docker container) or Remote, following the same Provider pattern as the other Infra services. See ADR-0004.

**IdP Client Role**:
One of `admin`, `contributor`, `viewer` — registered as Keycloak client roles on an `infra.idp` client (Cluster, Registry) and granted to a user via Keycloak group membership, carried into the client's `accessControl` policy via a group→role claim mapping. Distinct from Role (S3), which is RustFS-native IAM and doesn't involve the IdP.
_Avoid_: Role on its own (ambiguous with Role (S3))

**Service Account** (`infra.idp`):
The machine identity Keycloak issues for a `client_credentials` grant against a confidential `infra.idp` client, used for automated access in place of a human OIDC login. Distinct from Account (S3), which is RustFS-native and unrelated to the IdP.
_Note_: not used for Registry pushes — see Push Account.

**Push Account** (`infra.registry`):
The single htpasswd credential (`admin_username`, default `kube-eng`, + `admin_password`) `helm_publish` authenticates as to push charts to the Registry. A static credential rather than a Service Account token because zot can't run bearer auth and browser SSO at once (ADR-0004). For a Local registry the password is generated; for a Remote one it's supplied (typically an LDAP bind).

**Domain**:
The DNS suffix in which Infra service records are registered: `{cluster.name}.{dns.zone}`. Every Local Infra service's `client_fqdn` is `{service.name}.{domain}`.

**Account** (S3):
A dedicated access key/secret key pair in S3's own IAM system, created for one consuming service via `s3_client` — not shared credentials. Distinct from an IdP client (`infra.idp`), which is Keycloak's identity for a service; an S3 Account is RustFS-native and doesn't involve the IdP. See ADR-0003.

**Role** (S3):
One of `admin`, `contributor`, `viewer` — granted to an S3 Account at creation, mapped to RustFS's canned policies (`consoleAdmin`, `readwrite`, `readonly`). Not to be confused with an IdP Client Role, which is part of the OIDC design S3 still defers — see ADR-0003.