# kube-eng

Create a local Kubernetes cluster suitable for local engineering.

## How to run this

Start docker, consider making customisations in `cluster.yaml`. All services
are preconfigured with an admin password stored in `.admin-password`. If not
specified it will be generated.

```shell
$ make cluster
$ make host-infra
$ sudo ./bin/cloud-provider-kind
$ ./.venv/bin/cloud-provider-mdns
$ make stack
```

You should then be able to:

* Open [kiali](http://kiali.local/)
* Open [Prometheus](http://prometheus.local/)
* Open [Keycloak](http://keylocal.local/)
* Open [Grafana](http://grafana.local/)

## Limitations

* The `kube_eng.playbooks.create_host_infra.yml` playbook templates the configuration of a BIND resolver to which we   
  intend to send DNS updates to. MacOS panics when sending a DDNS update to it.
* It would be useful if the airgap-registry is a pull-through so we do not have to declare the
  container images to preheat. But the bare registry:2 from dockerhub can only have one upstream and the harbor registry uses a lot of resources.
