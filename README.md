# kube-eng

Create a local Kubernetes cluster suitable for local engineering.

## How to run this

Start docker. Consider making customisations in `cluster.yaml`. All services
are preconfigured with an admin password stored in `.admin-password`. If not
pre-specified then that admin password will be generated. The pre-heat target will cache all
required images locally so you don't have to download them again on the road.

```shell
$ make host-infra
$ make cluster
```

At this stage, you will find `var/pki/ca.pem`, which you should import into your login keystore and trust. Continue with the commands below. The host-infra-start target will ask you for your password
so it can start some services on the host. The stack target will run unprivileged again.

```shell
$ make host-infra-start
$ make stack
```

You can stop the host infra services if you mind keeping them running permanently in the background by running `make host-infra-stop`.

## Features

### PKI

A local CA certificate is created when host.pki.enabled is set to true in `cluster.yaml`. The CA and its private key
are stored in `var/pki` rather than in `.dist` to avoid accidentally deleting it. Add the local CA to the trust configuration
of your host before you deploy the stack.

The CA and its private key are registered in the clusters cert-manager configuration for issuing certificates.

### Air gapped registry

An air gapped OCI registry is created when host.registry.enabled is set to true in `cluster.yaml`. The cluster uses this
registry as a pass-through mirror for any image it attempts to pull, with the benefit of avoiding rate limits in the 
upstream registries as you hack on your cluster. 

Your hosts knows the registry as localhost on port 5001. The Kubernetes cluster knows it as 'registry' on the default 
port 443 because the registry container is attached to the same 'kind' docker network the cluster itself is connected to. 
Docker ensures that container names are known within that network.
A web UI is available at [https://localhost:5001](https://localhost:5001). The TLS certificate for this site is created using the same PKI that
`make host-infra` establishes so once you trust the CA generated there you're good to go for the registry as well.

```shell
# Pushing an image locally
$ docker push localhost:5001/some/path/awesome-app:v1.0.0

# Pulling an image from the Kubernetes cluster
... some deployment.yaml
image: registry/some/path/awesome-app:v1.0.0

# Pass-through pulling of an image through the mirror registry
$ docker pull localhost:5001/postgres:15
```

> There is no need to adjust the image configuration of the included or any extra deployments. The cluster's containerd
> configuration is preconfigured to mirror them through the air gapped registry.

## Limitations

* On ARM-based MacOS, there is a kernel panic when issuing a query to current BIND 9.20.7
  * The reason for the kernel panic is the [use of private APIs within libuv](https://github.com/libuv/libuv/issues/4594). Mitigation for this is to revert [back and pin to libuv 1.48.0](https://delaat.net/setup/#mozTocId756945)
* Ansible doesn't immediately trust the CA certificate we generate. The playbook currently ignores TLS validation when communicating with newly-spawned services
* Kiali isn't integrated into Keycloak
* Kiali can't authenticate to Grafana
* Kiali is unable to pull traces from Jaeger
* We currently have no way to synchronise stack.kiali.version with the AppVersion in the Kiali Helm chart
* cloud-provider-mdns still requires to be restarted too frequently when the cluster gets recreated. It is best to `make host-infra-stop` and `make host-infra-start`
* make stack should wait for keycloak to fully start up before continuing
* Istio Ambient mode (mesh.kind=istio-ambient, edge.kind=istio-gateway-api) does not play well with Keycloak
* `make stack` often needs to be run twice, as keycloak takes a bit longer to come up. We don't wait properly
