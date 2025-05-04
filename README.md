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
$ make preheat
```

At this stage, you will find `.dist/pki/ca.pem`, which you should import into your login keystore and trust. Continue with the commands below. The host-infra-start target will ask you for your password
so it can start some services on the host. The stack target will run unprivileged again.

```shell
$ make host-infra-start
$ make stack
```

You can stop the host infra services if you mind keeping them running permanently in the background by running `make host-infra-stop`.

## Limitations

* On ARM-based MacOS, there is a kernel panic when issuing a query to current BIND 9.20.7
  * The reason for the kernel panic is the [use of private APIs within libuv](https://github.com/libuv/libuv/issues/4594). Mitigation for this is to revert [back and pin to libuv 1.48.0](https://delaat.net/setup/#mozTocId756945)
* It would be useful if the airgap registry was a pull-through so we do not have to declare the
  container images to preheat. But the bare registry:2 from dockerhub can only have one upstream and the harbor registry uses a lot of resources.
* Ansible doesn't immediately trust the CA certificate we generate. The playbook currently ignores TLS validation when communicating with newly-spawned services
* Kiali isn't integrated into Keycloak
* Kiali can't authenticate to Grafana
* Kiali is unable to pull traces from Jaeger
