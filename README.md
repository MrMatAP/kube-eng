# kube-eng

Create a local Kubernetes cluster suitable for local engineering.

## How to run this

Start docker, consider making customisations in `cluster.yaml`. All services
are preconfigured with an admin password stored in `.admin-password`. If not
specified it will be generated.

```shell
$ make cluster
$ sudo ./bin/cloud-provider-kind
$ ./.venv/bin/cloud-provider-mdns
$ make services
```

You should then be able to:

* Open [kiali](http://kiali.local/)
* Open [Prometheus](http://prometheus.local/)
* Open [Keycloak](http://keylocal.local/)
* Open [Grafana](http://grafana.local/)
